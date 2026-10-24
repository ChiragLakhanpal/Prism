"""The nightly job's tasks, and a run of the whole job on this computer.

The bundle (bundle/nightly.yml) is the one place that names the tasks and their order. On
Databricks, each task runs nightly_task.py, which calls main() here with the task's name and the
job run's id. Each task does its work and records its run in strata.ops.pipeline_runs.

Four tasks have their work (tickets 07, 17 and 20): fetch_by_watermark fetches each source in
config/sources.toml that it fetches page by page into bronze, for every country or for the slice's
countries as each entry says, bronze_to_gold builds silver and gold from bronze,
detect_disagreements rebuilds the assertions and the disagreements between them
(strata.knowledge.assertions), and measure_data_readiness writes the data readiness measures and
each table's size to strata.ops. The rest do nothing yet, so each records zero rows changed;
ticket 43 gives them their work, and adds the plan reader (strata.lakehouse.plans), which fetches
the documents source itself.

The fetch is the one step that differs between the workspace and this computer. On Databricks,
main() fetches from the live APIs. run_locally() reads the same job from the bundle and calls
main() for each task in order, with the parameters the bundle gives, and fetches the recorded
fixture instead. The gate builds the fixture database this way (gates/build_fixture.py).

Run the whole job on an empty DuckDB database and print its rows:

    uv run --frozen python -m strata.lakehouse.nightly
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import resources

from strata.config import Source, load_sources
from strata.lakehouse import bronze, gold, pages, readiness, silver, storage
from strata.lakehouse.engine import Engine
from strata.lakehouse.schedule import Window, daily_start

JOB = "nightly"  # the job's key under resources.jobs in the bundle

# Where a source's pages come from: the live API on the workspace, the recorded fixture here.
Fetch = Callable[[Source, Engine], Iterable[pages.Page]]


def fetch_live(source: Source, engine: Engine) -> Iterable[pages.Page]:
    from strata.fixture.record import fetch_url  # it retries when a server asks it to wait

    return pages.live_pages(source, fetch_url, lambda country: bronze.newest_held(engine, source, country))


def fetch_recorded(source: Source, engine: Engine) -> Iterable[pages.Page]:
    return pages.recorded_pages(source)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


@dataclass(frozen=True)
class Run:
    """What a task works with: the engine, the job run's id, where pages come from, and the clock
    its measures are taken by (the fixture build fixes it, so the fixture's measures never move)."""

    engine: Engine
    run_id: str
    fetch: Fetch
    clock: Callable[[], dt.datetime] = _now


def _nothing_yet(run: Run) -> int:
    """A task that has no work yet. It changes no rows."""
    return 0


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
    """Silver from bronze, the awarded bidders read from award notices, each supplier row resolved to its
    supplier, then gold. Ticket 19 resolves suppliers here, since the bundle's task list belongs to
    ticket 43 and docs/PLAN.md section 11. Only a run that fetches from the live APIs asks the live
    model about the uncertain middle of name matching; any other run uses the offline stand-in. On
    Databricks the job passes no Azure OpenAI keys until ticket 43 wires its tasks, so until then every
    pair in the middle waits for a person (no_model)."""
    from strata.knowledge.suppliers import bidders, judge, resolve

    added = sum(silver.run(run.engine, source) for source in _paged())
    added += bidders.store(run.engine)
    deciding = judge.from_environment() if run.fetch is fetch_live else judge.SameNameStandIn()
    added += resolve.run(run.engine, run.run_id, deciding, run.clock)
    return added + gold.build(run.engine)


def _detect_disagreements(run: Run) -> int:
    """The assertions of every project Strata holds documents or records for, rebuilt, and the disagreements
    between them, each decided by the evidence ladder (ticket 20). Only a run that fetches from the live APIs
    asks the live batch model to read the reports. On Databricks the job passes no Azure OpenAI keys until
    ticket 43 wires its tasks, so until then it replays the answers bronze holds from the batch role's
    deployment, such as those ops/assertions/batch_live.py asked for, and keeps what the live model read.
    Any other run replays the recorded answers."""
    from strata.knowledge import assertions, batch

    model = (batch.from_environment() or batch.HeldAnswers()) if run.fetch is fetch_live else batch.RecordedBatch()
    projects = assertions.default_projects(run.engine)
    report = assertions.run(run.engine, projects, model=model, run_id=run.run_id, clock=run.clock)
    return report.assertions + report.rejected + report.disagreements


def _measure_data_readiness(run: Run) -> int:
    """The data readiness measures of every source, how often supplier auto-merge is right on the labeled
    pairs (ticket 19), the room each table takes, and the Data readiness page built from them for the
    dashboard (strata.dashboard.snapshot)."""
    from strata.dashboard import snapshot
    from strata.knowledge.suppliers import quality

    measured = readiness.measure(run.engine, run.run_id, run.clock) + quality.measure(run.engine, run.run_id, run.clock)
    measured += storage.measure(run.engine, run.run_id, run.clock)
    return measured + snapshot.write(run.engine, run.run_id, run.clock)


# Each task's work, by the task key the bundle uses. Each returns the number of rows it changed.
TASKS: dict[str, Callable[[Run], int]] = {
    "fetch_by_watermark": _fetch_by_watermark,
    "bronze_to_gold": _bronze_to_gold,
    "parse_and_embed": _nothing_yet,
    "sync_index": _nothing_yet,
    "relink": _nothing_yet,
    "propose_lessons": _nothing_yet,
    "detect_disagreements": _detect_disagreements,
    "score": _nothing_yet,
    "measure_data_readiness": _measure_data_readiness,
    "refresh_drafts": _nothing_yet,
}


def _record_sql() -> str:
    # importlib.resources rather than __file__, which serverless Python tasks do not set for the script.
    return (resources.files("strata.lakehouse") / "sql" / "record_pipeline_run.sql").read_text()


def run_task(engine: Engine, task_key: str, run_id: str, fetch: Fetch,
             clock: Callable[[], dt.datetime] = _now) -> None:
    """Do one task's work and record it. A task that fails is recorded as failed, then raises again."""
    work = TASKS[task_key]
    started = clock()
    status, changed = "failed", 0
    try:
        changed = work(Run(engine, run_id, fetch, clock))
        status = "succeeded"
    finally:
        finished = clock()
        engine.run(_record_sql(), {
            "run_id": run_id, "task_key": task_key, "status": status, "rows_changed": changed,
            "started_at": started, "finished_at": finished, "public_from": finished.astimezone(dt.UTC).date(),
        })


def main(argv: list[str], engine: Engine, fetch: Fetch = fetch_live, clock: Callable[[], dt.datetime] = _now) -> int:
    """The entry point each task of the job calls: --task NAME --run-id ID --src FOLDER. Pages come
    from the live APIs, as on Databricks, unless fetch says otherwise; run_locally() passes the
    recorded fixture."""
    parser = argparse.ArgumentParser(prog="nightly_task.py")
    parser.add_argument("--task", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--src", help="the folder that holds the strata package; nightly_task.py uses it")
    args = parser.parse_args(argv)
    if args.task not in TASKS:
        raise SystemExit(f"The nightly job has no task called {args.task}. "
                         f"Its tasks are: {', '.join(TASKS)}.")
    run_task(engine, args.task, args.run_id, fetch, clock)
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


def window(bundle=None) -> Window:
    """When the job runs: its daily start, its time zone and how long it may run before it stops."""
    job = _job(bundle)
    return Window("Strata's nightly job", daily_start(job["schedule"]["quartz_cron_expression"]),
                  job["schedule"]["timezone_id"], int(job["timeout_seconds"]) // 60)


def run_locally(engine: Engine, bundle=None, run_id: str | None = None, fetch: Fetch = fetch_recorded,
                clock: Callable[[], dt.datetime] = _now) -> str:
    """Run every task of the job in order on engine, with the parameters the bundle gives and pages
    from the recorded fixture, each timed by clock. Returns the run id."""
    run_id = run_id or f"local-{_now():%Y%m%dT%H%M%S%f}"
    for task in job_tasks(bundle):
        argv = [part.replace("{{job.run_id}}", run_id).replace("{{task.name}}", task.key)
                for part in task.parameters]
        main(argv, engine, fetch, clock)
    return run_id


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
