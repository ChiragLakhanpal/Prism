"""The nightly job's tasks, and a run of the whole job on this computer.

The bundle (bundle/nightly.yml) is the one place that names the tasks and their order. On
Databricks, each task runs nightly_task.py, which calls main() here with the task's name and the
job run's id. Each task does its work, runs its quality checks (strata.lakehouse.quality) and records
its run in strata.ops.pipeline_runs.

Every task has its work (tickets 07, 17, 19, 20, 22, 26, 28, 29 and 43), in docs/PLAN.md section 11's order:

1. fetch_by_watermark fetches each source in config/sources.toml that it fetches page by page into bronze,
   for every country or for the slice's countries as each entry says, from its watermark on.
2. bronze_to_gold builds silver and gold from bronze, with the suppliers resolved (ticket 19).
3. parse_and_embed runs the plan reader and the passage reader over only the documents bronze does not
   hold yet, and embeds only passages whose text changed (strata.lakehouse.readers).
4. sync_index syncs strata.gold.passage and, on the workspace, the AI Search index.
5. relink rebuilds the edge table and scores each contract against its project's report paragraphs
   (strata.knowledge.links).
6. propose_lessons has the batch model propose lessons from the evaluation reports the passage reader
   holds; a document is sent once, and those whose quotes pass the check wait in the review queue
   (strata.knowledge.lessons.propose).
7. detect_disagreements rebuilds the assertions and the disagreements between them (strata.knowledge.assertions).
8. score scores every package's time estimate and its what-ifs with the champion model (ticket 26;
   strata.estimates.scoring), counts the rebidding labels from each source and, on the workspace, scores every
   planned activity with the rebidding champion (strata.estimates.rebidding) and replays the signals for their
   track record once a week (strata.estimates.signals_track).
9. measure_data_readiness writes the data readiness measures and each table's size to strata.ops.
10. refresh_drafts marks each open draft row that cites a lesson at a version a lead has since changed or
    retired (strata.knowledge.lessons.notices). It never changes a draft.

Where pages and documents come from is the one thing that differs between the workspace and this
computer. On Databricks, main() fetches from the live APIs and the World Bank's document host.
run_locally() reads the same job from the bundle and calls main() for each task in order, with the
parameters the bundle gives, over the recorded fixture instead. The gate builds the fixture database
this way (gates/build_fixture.py), and repair_locally() reruns a run that stopped, as a Databricks
repair run does.

A rerun changes nothing that the first run already wrote: bronze keeps a page or a document once, by
its hash or id; silver reads a page only once all its tables hold it; gold and the edge table are
made equal to their queries with one MERGE; the readers parse and embed only what is new; and a
document is sent to the batch model once. What a run adds every time is its own record, under its own
run id (RUN_LOGS), and a fresh try of a request or a page that failed before.

Run the whole job on an empty DuckDB database and print its rows:

    uv run --frozen python -m strata.lakehouse.nightly
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections.abc import Callable, Iterable, MutableMapping
from dataclasses import dataclass
from importlib import resources

from strata.config import Source, load_sources
from strata.lakehouse import bronze, gold, pages, quality, readers, readiness, silver, storage
from strata.lakehouse.engine import Engine
from strata.lakehouse.schedule import Window, as_utc, daily_start

JOB = "nightly"  # the job's key under resources.jobs in the bundle

# The tables in which every run adds rows of its own, under its own run id, whether anything changed or not: the
# record of what each run did and measured. Every other table a rerun leaves as it was. bronze.lesson_batches and
# ops.parse_failures also keep each try of a request or a page that failed before, which a later night tries again.
RUN_LOGS = ("strata.ops.pipeline_runs", "strata.ops.quality_checks", "strata.ops.data_readiness",
            "strata.ops.table_sizes", "strata.ops.readiness_snapshot", "strata.ops.parse_runs",
            "strata.ops.documents_read", "strata.ops.stress_shelf", "strata.ops.rebidding_labels",
            "strata.ops.supplier_match_quality", "strata.ops.evaluation_result", "strata.gold.time_estimate_score",
            # Each document run's sample of passages checked against the language detector (ticket 42).
            "strata.ops.passage_language_checks",
            # The challenger's and the hazard model's nightly scores in shadow (ticket 44).
            "strata.ops.time_estimate_shadow", "strata.ops.hazard_scores")

# Where a source's pages come from: the live API on the workspace, the recorded fixture here.
Fetch = Callable[[Source, Engine], Iterable[pages.Page]]


def fetch_live(source: Source, engine: Engine) -> Iterable[pages.Page]:
    from strata.fixture.record import fetch_url  # it retries when a server asks it to wait

    return pages.live_pages(source, fetch_url, lambda country: bronze.newest_held(engine, source, country))


def fetch_recorded(source: Source, engine: Engine) -> Iterable[pages.Page]:
    return pages.recorded_pages(source)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


# The document readers a run uses (strata.lakehouse.readers), given the engine, or None for no document reader.
ReadersFor = Callable[[Engine], "readers.Readers | None"]


def no_documents(engine: Engine) -> None:
    """No document reader: parse_and_embed reads nothing. The fixture build reads the documents itself, before
    and after the job, so its measures keep the runs they always had (gates/build_fixture.py)."""
    return None


@dataclass(frozen=True)
class Run:
    """What a task works with: the engine, the job run's id, where pages come from, the clock its
    measures are taken by (the fixture build fixes it, so the fixture's measures never move), and
    where documents come from. By default the documents follow the pages: the live readers when pages
    come from the live APIs, the recorded fixture's when they come from the recorded fixture, and none
    for any other source of pages, such as a test's, unless readers_for names some."""

    engine: Engine
    run_id: str
    fetch: Fetch
    clock: Callable[[], dt.datetime] = _now
    readers_for: ReadersFor | None = None
    search_endpoint: str | None = None  # the AI Search endpoint the bundle names; the live readers sync its index

    def document_readers(self) -> readers.Readers | None:
        if self.readers_for is not None:
            return self.readers_for(self.engine)
        if self.fetch is fetch_live:
            return readers.live(self.engine, search_endpoint=self.search_endpoint)
        return readers.recorded() if self.fetch is fetch_recorded else None


def _paged() -> list[Source]:
    """The sources this job fetches page by page. The documents source has its own reader."""
    return [source for source in load_sources().values() if source.paged]


def _fetch_by_watermark(run: Run) -> int:
    """Each source's new pages into bronze. A frozen source no longer changes, so once bronze holds
    its pages from a fetch task that finished, it is not asked for again. A fetch that stopped
    partway does not count, so the next run asks for the pages it missed."""
    added = 0
    for source in _paged():
        if source.cadence == "frozen" and bronze.holds_a_finished_fetch(run.engine, source):
            continue
        added += bronze.store(run.engine, source, run.fetch(source, run.engine))
    return added


def _bronze_to_gold(run: Run) -> int:
    """Silver from bronze, the awarded bidders and every bid (ticket 22) read from award notices, each supplier row resolved to its
    supplier, then gold. Ticket 19 resolves suppliers here, since the bundle's task list belongs to
    ticket 43 and docs/PLAN.md section 11. Only a run that fetches from the live APIs asks the live
    model about the uncertain middle of name matching; any other run uses the offline stand-in. On
    Databricks each task reads the Azure OpenAI keys from the job's secret scope (keys_from_scope); without
    them every pair in the middle waits for a person (no_model)."""
    from strata.knowledge.suppliers import bidders, judge, resolve

    added = sum(silver.run(run.engine, source) for source in _paged())
    added += bidders.store(run.engine) + bidders.store_bids(run.engine)
    deciding = judge.from_environment() if run.fetch is fetch_live else judge.SameNameStandIn()
    added += resolve.run(run.engine, run.run_id, deciding, run.clock)
    return added + gold.build(run.engine)


def _parse_and_embed(run: Run) -> int:
    """The plan reader and the passage reader, over only the documents bronze does not hold and the pages and
    passages they have not read (strata.lakehouse.readers). A refusal from the document host ends the reading
    for the night with a data readiness note, and the task still finishes."""
    found = run.document_readers()
    return 0 if found is None else readers.read(run.engine, found, run.run_id, run.clock)


def _sync_index(run: Run) -> int:
    """strata.gold.passage made equal to the passages and, on the workspace, the AI Search index synced from it."""
    return readers.sync_index(run.engine, run.document_readers())


def _relink(run: Run) -> int:
    """The edge table rebuilt: every keyed link between strata, and each contract scored against the paragraphs
    of its own project's reports, keeping the pairs that reach links.threshold as "appeared together" links
    (ticket 22; strata.knowledge.links). It needs no model, so it runs the same on the workspace and here."""
    from strata.knowledge import links

    return links.relink(run.engine, run.run_id, run.clock)


def _detect_disagreements(run: Run) -> int:
    """The assertions of every project Strata holds documents or a Procurement Plan for, rebuilt, and the
    disagreements between them, each decided by the evidence ladder (ticket 20). Only a run that fetches from the live APIs
    asks the live batch model to read the reports, with the keys the task reads from the job's secret scope.
    Without them it replays the answers bronze holds from the batch role's deployment, such as those
    ops/assertions/batch_live.py asked for, and keeps what the live model read. Any other run replays the
    recorded answers."""
    from strata.knowledge import assertions, batch

    model = (batch.from_environment() or batch.HeldAnswers()) if run.fetch is fetch_live else batch.RecordedBatch()
    projects = assertions.default_projects(run.engine)
    report = assertions.run(run.engine, projects, model=model, run_id=run.run_id, clock=run.clock)
    return report.changed


def _propose_lessons(run: Run) -> int:
    """Lessons proposed from the evaluation reports the passage reader holds, then the lesson review writer's
    note on each open item of the review queue (ticket 29). Only a run that fetches from the live APIs sends
    them to the live batch model and the live writer, with the keys the task reads from the job's secret scope;
    any other run replays their recorded answers. Each document is sent once: tonight's batch is submitted,
    and the answers of earlier nights' batches are collected, so a rerun never sends a document twice. Without
    the keys the task proposes nothing and changes no rows."""
    import os

    from strata.agent.runner import lesson_writer_from_environment
    from strata.config import load_thresholds
    from strata.knowledge.lessons import batch, propose, writer

    if run.fetch is not fetch_live:
        return propose.run_on_fixture(run.engine, run.run_id, run.clock)
    model = batch.from_environment()
    changed = 0 if model is None else propose.run(run.engine, model, run.run_id, run.clock)
    # The review-proposed-lessons workflow, with the live lesson review writer when the job can reach Foundry.
    agent = lesson_writer_from_environment(os.environ)()
    if agent is not None:
        most = int(load_thresholds().value("lesson_review.likely_repeats_max"))
        changed += writer.run(run.engine, lambda item, subject: agent, run.clock, most)
    return changed


def _score(run: Run) -> int:
    """The time estimate of every package Strata knows, and of every what-if combination, scored with the
    champion model into strata.gold.time_estimate_score (ticket 26; strata.estimates.scoring). A run on the
    recorded fixture has no workspace registry, so it runs ticket 25's backtest first and scores with the
    champion that trains; a live run scores with the champion the live backtest registered, or with none.

    Then how many packages each rebidding label source names, in strata.ops.rebidding_labels, and, on a run that
    fetches from the live APIs, the rebidding champion's chance for every activity a Procurement Plan lists, in
    strata.ops.rebidding_scores (ticket 28), and the signals' track record (ticket 37).

    Then the estimates loop (ticket 44): every package scored in shadow with the challenger, when one newer than the
    champion is kept (strata.estimates.promotion, which no tool reads); the monthly watch of each whole month not
    watched yet, which marks plan rows dated near a date Strata offered, measures plan accuracy and rolling coverage
    and raises the retrains they call for (strata.estimates.watch); and, on a run that fetches from the live APIs,
    the retrain itself when one is due, quarterly or after a raised trigger, which registers a challenger.

    Last, the discrete-time hazard model for project delay early warning, in shadow beside the fixed signals: every
    open project's score in strata.ops.hazard_scores, and, once a week, its replay against the signals
    (strata.estimates.hazard). Nothing shows either."""
    from strata.estimates import hazard, promotion, rebidding, scoring, watch

    changed = scoring.run(run.engine, run.run_id, run.clock(), train_here=run.fetch is not fetch_live)
    changed += rebidding.record_label_counts(run.engine, run.run_id, run.clock)
    changed += promotion.score_in_shadow(run.engine, run.run_id, run.clock())
    if run.fetch is fetch_live:
        changed += _score_packages(run) + _replay_signals(run)
    changed += watch.run(run.engine, run.run_id, run.clock())
    if run.fetch is fetch_live:
        changed += _retrain(run)
    return changed + hazard.score_in_shadow(run.engine, run.run_id, run.clock()) + _compare_hazard(run)


def _compare_hazard(run: Run) -> int:
    """The hazard model replayed against the fixed signals (strata.estimates.hazard.compare), when the stored
    comparison is signals.track_record_every_days old or there is none, on the signals' own cadence. A live run logs
    it to MLflow, or skips it when MLflow is missing; any other run uses the offline tracker. Returns the rows stored
    in strata.ops.evaluation_result."""
    from strata.config import load_thresholds, load_time_estimate
    from strata.estimates import harness, hazard
    from strata.estimates.tracking import OfflineTracker

    now = run.clock()
    held = hazard.stored(run.engine)
    every = int(load_thresholds().value("signals.track_record_every_days"))
    if held is not None and (now.astimezone(dt.UTC).date() - as_utc(held["ran_at"]).date()).days < every:
        return 0
    tracker = _tracker(load_time_estimate().experiment) if run.fetch is fetch_live else OfflineTracker()
    if tracker is None:
        return 0
    return len(harness.run_rows(run.engine, hazard.compare(run.engine, tracker, ran_at=now)))


def _retrain(run: Run) -> int:
    """Ticket 25's backtest, which trains the time estimate and registers it as the challenger while a champion holds
    the alias, when the watch says a retrain is due (strata.estimates.watch.retrain_due). Returns the rows it stored
    in strata.ops.evaluation_result."""
    from strata.config import load_time_estimate
    from strata.estimates import backtest, harness, watch

    now = run.clock()
    if watch.retrain_due(run.engine, now.astimezone(dt.UTC).date()) is None:
        return 0
    tracker = _tracker(load_time_estimate().experiment)
    if tracker is None:
        return 0
    return len(harness.run_rows(run.engine, backtest.run(run.engine, tracker, ran_at=now).run_id))


def _tracker(experiment: str):
    """MLflow on the workspace, or None when MLflow is missing or not signed in: the counts stand, and nothing that
    needs MLflow runs tonight."""
    from strata.estimates.tracking import MlflowTracker

    try:
        return MlflowTracker(experiment)
    except Exception:  # noqa: BLE001 - MLflow raises its own errors, and the import may fail
        return None


def _score_packages(run: Run) -> int:
    """The rebidding champion's chance for every planned activity, once a backtest has registered a champion."""
    from strata.config import load_rebidding
    from strata.estimates import rebidding_backtest

    tracker = _tracker(load_rebidding().experiment)
    return 0 if tracker is None else rebidding_backtest.score_packages(run.engine, tracker, run.run_id, run.clock)


def _replay_signals(run: Run) -> int:
    """The signals' checks replayed on their track record dates (strata.estimates.signals_track.backtest), for the
    Following page, when the stored record is signals.track_record_every_days old or there is none. Returns the
    rows the replay stored in strata.ops.evaluation_result."""
    from strata.config import load_thresholds, load_time_estimate
    from strata.estimates import harness, signals_track

    now = run.clock()
    held = signals_track.stored(run.engine)
    every = int(load_thresholds().value("signals.track_record_every_days"))
    if held is not None and (now.astimezone(dt.UTC).date() - dt.date.fromisoformat(held["ran_on"])).days < every:
        return 0
    tracker = _tracker(load_time_estimate().experiment)
    if tracker is None:
        return 0
    return len(harness.run_rows(run.engine, signals_track.backtest(run.engine, tracker, ran_at=now)))


def _measure_data_readiness(run: Run) -> int:
    """The data readiness measures of every source, how often supplier auto-merge is right on the labeled
    pairs (ticket 19), the room each table takes, and the Data readiness page built from them for the
    dashboard (strata.dashboard.snapshot)."""
    from strata.dashboard import snapshot
    from strata.knowledge.suppliers import quality

    measured = readiness.measure(run.engine, run.run_id, run.clock) + quality.measure(run.engine, run.run_id, run.clock)
    measured += storage.measure(run.engine, run.run_id, run.clock)
    return measured + snapshot.write(run.engine, run.run_id, run.clock)


def _refresh_drafts(run: Run) -> int:
    """A version notice for each open draft row that cites a lesson at a version a lead has since changed or
    retired (strata.knowledge.lessons.notices). It marks drafts and never changes one (the 39 brief, section 9)."""
    from strata.knowledge.lessons import notices

    return notices.mark(run.engine, run.run_id, run.clock)


# Each task's work, by the task key the bundle uses. Each returns the number of rows it changed.
TASKS: dict[str, Callable[[Run], int]] = {
    "fetch_by_watermark": _fetch_by_watermark,
    "bronze_to_gold": _bronze_to_gold,
    "parse_and_embed": _parse_and_embed,
    "sync_index": _sync_index,
    "relink": _relink,
    "propose_lessons": _propose_lessons,
    "detect_disagreements": _detect_disagreements,
    "score": _score,
    "measure_data_readiness": _measure_data_readiness,
    "refresh_drafts": _refresh_drafts,
}


def _record_sql() -> str:
    # importlib.resources rather than __file__, which serverless Python tasks do not set for the script.
    return (resources.files("strata.lakehouse") / "sql" / "record_pipeline_run.sql").read_text()


FIRST_STARTED = "SELECT min(started_at) AS started FROM strata.ops.pipeline_runs WHERE run_id = :run_id"


def night_of(engine: Engine, run_id: str, started: dt.datetime) -> dt.date:
    """The night a run belongs to: the day, in the job's time zone, its first task started. A rerun of a task on
    a later day keeps the night of the run it finishes."""
    from zoneinfo import ZoneInfo

    first = as_utc(engine.run(FIRST_STARTED, {"run_id": run_id}).rows[0][0])
    when = min(started, first) if first else started
    return when.astimezone(ZoneInfo(window().timezone)).date()


def run_task(engine: Engine, task_key: str, run_id: str, fetch: Fetch,
             clock: Callable[[], dt.datetime] = _now, readers_for: ReadersFor | None = None,
             search_endpoint: str | None = None) -> None:
    """Do one task's work, run its quality checks (strata.lakehouse.quality) and record it. A task that fails is
    recorded as failed, with no checks, then raises again."""
    work = TASKS[task_key]
    started = clock()
    status, changed = "failed", 0
    try:
        changed = work(Run(engine, run_id, fetch, clock, readers_for, search_endpoint))
        quality.record(engine, quality.check(engine, task_key), run_id, night_of(engine, run_id, started), task_key,
                       clock())
        status = "succeeded"
    finally:
        finished = clock()
        engine.run(_record_sql(), {
            "run_id": run_id, "task_key": task_key, "status": status, "rows_changed": changed,
            "started_at": started, "finished_at": finished, "public_from": finished.astimezone(dt.UTC).date(),
        })


# The keys the tasks read from their environment, which on Databricks the job reads from its secret scope
# (bundle variable secret_scope; ops/app/deploy_app.py and the wizard save them there under these names). The AI
# Search endpoint is no secret, so it comes as the --search-endpoint parameter (bundle variable ai_search_endpoint).
SCOPE_KEYS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "FOUNDRY_PROJECT_ENDPOINT", "FOUNDRY_TENANT_ID",
              "FOUNDRY_CLIENT_ID", "FOUNDRY_CLIENT_SECRET")


def keys_from_scope(get: Callable[[str, str], str], scope: str, environ: MutableMapping[str, str]) -> list[str]:
    """Each key the tasks read, from the job's secret scope into the task's environment, unless the environment
    already holds it, so the key never travels with the job's parameters. A key the scope lacks is left out, and
    the task runs without it. Returns the names of the keys it set, never their values."""
    found = []
    for key in SCOPE_KEYS:
        if (environ.get(key) or "").strip():
            continue
        try:
            value = get(scope, key)
        except Exception:  # noqa: BLE001 - dbutils raises its own error for a key the scope does not hold
            continue
        if value:
            environ[key] = value
            found.append(key)
    return found


def main(argv: list[str], engine: Engine, fetch: Fetch = fetch_live, clock: Callable[[], dt.datetime] = _now,
         readers_for: ReadersFor | None = None) -> int:
    """The entry point each task of the job calls: --task NAME --run-id ID --src FOLDER. Pages and
    documents come from the live APIs, as on Databricks, unless fetch and readers_for say otherwise;
    run_locally() passes the recorded fixture."""
    parser = argparse.ArgumentParser(prog="nightly_task.py")
    parser.add_argument("--task", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--src", help="the folder that holds the strata package; nightly_task.py uses it")
    parser.add_argument("--secret-scope", help="the scope nightly_task.py reads the tasks' keys from")
    parser.add_argument("--search-endpoint", help="the AI Search endpoint whose index sync_index syncs")
    args = parser.parse_args(argv)
    if args.task not in TASKS:
        raise SystemExit(f"The nightly job has no task called {args.task}. "
                         f"Its tasks are: {', '.join(TASKS)}.")
    run_task(engine, args.task, args.run_id, fetch, clock, readers_for, args.search_endpoint)
    return 0


# ── The job as the bundle declares it ────────────────────────────────────

@dataclass(frozen=True)
class Task:
    key: str
    depends_on: tuple[str, ...]
    parameters: tuple[str, ...]


def _job(bundle=None) -> dict:
    from strata.lakehouse import bundle as bundle_files

    return (bundle or bundle_files.load()).resources("jobs")[JOB]


def job_name(bundle=None) -> str:
    """The job's name in the workspace, as bundle/nightly.yml gives it."""
    return _job(bundle)["name"]


def job_tasks(bundle=None) -> list[Task]:
    """The job's tasks in the order they run: each after every task it depends on, ties in file order."""
    declared = [Task(entry["task_key"], tuple(dep["task_key"] for dep in entry.get("depends_on", [])),
                     tuple(entry["spark_python_task"]["parameters"]))
                for entry in _job(bundle)["tasks"]]
    ordered: list[Task] = []
    waiting = list(declared)
    while waiting:
        ready = [task for task in waiting if all(dep in [done.key for done in ordered] for dep in task.depends_on)]
        if not ready:
            raise ValueError("The nightly job's tasks depend on each other in a circle.")
        ordered.append(ready[0])
        waiting.remove(ready[0])
    return ordered


LAST_FINISHED = """
SELECT max(finished_at) AS finished FROM strata.ops.pipeline_runs WHERE task_key = :task_key AND status = 'succeeded'
"""


@dataclass(frozen=True)
class Freshness:
    """When the nightly job last finished every task, with its checks, and whether that is too long ago."""

    finished_at: dt.datetime | None
    stale: bool


def freshness(engine: Engine, now: dt.datetime, bundle=None) -> Freshness:
    """When a run of the job last finished its last task, after every check before it, and whether more than
    nightly.stale_after_hours have passed since (config/thresholds.toml), for the freshness stamp's stale marker
    and the stale alerts (briefs 06, 37 and 41). No finished run is stale. Nothing reads it yet: no ticket owns
    drawing the stale marker (a parked decision from brief 06), and ticket 41's briefing is the first ticket
    whose brief names the stale alerts."""
    from strata.config import load_thresholds

    found = as_utc(engine.run(LAST_FINISHED, {"task_key": job_tasks(bundle)[-1].key}).rows[0][0])
    hours = float(load_thresholds().value("nightly.stale_after_hours"))
    return Freshness(found, found is None or now - found > dt.timedelta(hours=hours))


def most_at_once(bundle=None) -> int:
    """The most tasks the job can run at the same moment: the largest set of tasks none of which waits on another,
    times the runs the job allows at once (max_concurrent_runs). The workspace runs at most five job tasks at once,
    shared with fairshare (config/thresholds.toml, nightly.max_concurrent_tasks)."""
    from itertools import combinations

    tasks = job_tasks(bundle)
    waits_on = {task.key: set(task.depends_on) for task in tasks}
    for task in tasks:  # in run order, so each task's own waits are complete before a later task reads them
        for dep in list(waits_on[task.key]):
            waits_on[task.key] |= waits_on[dep]

    def apart(a: str, b: str) -> bool:
        return a not in waits_on[b] and b not in waits_on[a]

    keys = [task.key for task in tasks]
    widest = max(size for size in range(1, len(keys) + 1)
                 if any(all(apart(a, b) for a, b in combinations(group, 2)) for group in combinations(keys, size)))
    return widest * int(_job(bundle).get("max_concurrent_runs", 1))


def window(bundle=None) -> Window:
    """When the job runs: its daily start, its time zone and how long it may run before it stops."""
    job = _job(bundle)
    return Window("Strata's nightly job", daily_start(job["schedule"]["quartz_cron_expression"]),
                  job["schedule"]["timezone_id"], int(job["timeout_seconds"]) // 60)


def _argv(task: Task, run_id: str) -> list[str]:
    return [part.replace("{{job.run_id}}", run_id).replace("{{task.name}}", task.key) for part in task.parameters]


def run_locally(engine: Engine, bundle=None, run_id: str | None = None, fetch: Fetch = fetch_recorded,
                clock: Callable[[], dt.datetime] = _now, readers_for: ReadersFor | None = None) -> str:
    """Run every task of the job in order on engine, with the parameters the bundle gives and pages
    and documents from the recorded fixture, each timed by clock. A task that fails stops the run, as
    on Databricks, where every later task depends on it. Returns the run id."""
    run_id = run_id or f"local-{_now():%Y%m%dT%H%M%S%f}"
    for task in job_tasks(bundle):
        main(_argv(task, run_id), engine, fetch, clock, readers_for)
    return run_id


LAST_TRIES = """
SELECT task_key, status FROM strata.ops.pipeline_runs WHERE run_id = :run_id ORDER BY started_at, finished_at
"""


def repair_locally(engine: Engine, run_id: str, bundle=None, fetch: Fetch = fetch_recorded,
                   clock: Callable[[], dt.datetime] = _now, readers_for: ReadersFor | None = None) -> list[str]:
    """Rerun a run that stopped, as a Databricks repair run does: under the same run id, every task from the
    first one whose last try did not succeed, in order. Each try keeps its own row in strata.ops.pipeline_runs.
    Returns the tasks it ran."""
    last = dict(engine.run(LAST_TRIES, {"run_id": run_id}).rows)
    tasks = job_tasks(bundle)
    first = next((n for n, task in enumerate(tasks) if last.get(task.key) != "succeeded"), len(tasks))
    for task in tasks[first:]:
        main(_argv(task, run_id), engine, fetch, clock, readers_for)
    return [task.key for task in tasks[first:]]


def _print_local_run() -> int:
    from strata.lakehouse import catalog
    from strata.lakehouse.engine import DuckDBEngine

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_id = run_locally(engine)
        result = engine.run("SELECT task_key, status, rows_changed, started_at FROM strata.ops.pipeline_runs "
                            "WHERE run_id = :run_id ORDER BY started_at", {"run_id": run_id})
    print(f"Run {run_id} wrote {len(result.rows)} rows to strata.ops.pipeline_runs, in this order:")
    for number, (task, status, changed, started) in enumerate(result.as_text(), 1):
        print(f"  {number:>2}. {task}: {status}, {changed} rows changed, started {started}")
    return 0


if __name__ == "__main__":
    sys.exit(_print_local_run())
