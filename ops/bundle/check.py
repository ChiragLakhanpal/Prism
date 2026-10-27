# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "splink==5.0.0", "xgboost==3.4.1; sys_platform != 'linux'",
#                 "xgboost-cpu==3.4.1; sys_platform == 'linux'", "numpy==2.5.4", "py3langid==0.3.0", "pypdf==6.20.0",
#                 "fastapi==0.161.1", "httpx==0.28.1", "fpdf2==2.8.9", "defusedxml==0.7.1",
#                 "opentelemetry-api==1.45.1"]
# ///
"""Check the deployed catalog and nightly job on the shared workspace.

Run each check from the main checkout, after the deploy (ops/bundle/deploy.py):

    uv run --script ops/bundle/check.py job-run --env-file .env
    uv run --script ops/bundle/check.py same-rows --env-file .env
    uv run --script ops/bundle/check.py readiness --env-file .env
    uv run --script ops/bundle/check.py schedules --env-file .env --write

job-run    Starts the nightly job by hand, waits for it, and checks that strata.ops.pipeline_runs
           holds one row per task for that run, in the order bundle/nightly.yml gives, that each task
           recorded its quality checks in strata.ops.quality_checks, and that the run finished inside
           the job's window. It prints each task's duration, rows changed and checks passed and failed.
           Pass --run-id to check a run that already finished instead, such as a scheduled one.
same-rows  Runs each ground-truth query marked for databricks (tests/ground_truth) on DuckDB and
           on the SQL warehouse, and checks that both return the rows the file expects. DuckDB
           reads the fixture database, or, without it, builds the catalog's tables in memory, reads
           the demo plan's recorded Procurement Plans into them and runs the nightly job's tasks
           over the recorded pages, as the fixture build does. Run it after the live plan run
           (ops/plans/run_live.py) and job-run, because some files read what they wrote.
           The inline list at the top names every package that build imports, at the project's
           versions, so it needs no --with (ops/bundle/tests/test_script_dependencies.py checks it).
readiness  Builds the Data readiness page on the SQL warehouse with data_readiness_for, as the app
           does, and checks that its awards row's rows held and contracts with a STEP reference
           match a direct query on strata.ops.data_readiness. It also prints Kenya's own measures.
schedules  Reads fairshare's nightly job and Strata's, with how long their recent runs took, and
           checks that the two never run at the same time on any day of the next year. With
           --write it records both schedules in the bundle's notes, bundle/README.md.

Each check exits 0 when it passes, 1 when it fails and 2 when it could not run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
from strata.knowledge import assertions  # noqa: E402
from strata.lakehouse import catalog, ground_truth, nightly, passages, plans, schedule  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine, EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

NOTES = REPO / "bundle" / "README.md"
FIXTURE_DB = REPO / "data" / "out" / "fixture.duckdb"
BLOCK = re.compile(r"(<!-- bundle:schedules -->\n).*?(<!-- /bundle:schedules -->)", re.S)
RUNS = """
SELECT task_key, status, started_at, finished_at, rows_changed
FROM strata.ops.pipeline_runs
WHERE run_id = :run_id
ORDER BY started_at
"""
CHECKS = """
SELECT task_key, count_if(passed) AS passed, count_if(NOT passed) AS failed
FROM strata.ops.quality_checks
WHERE run_id = :run_id
GROUP BY task_key
"""


# ── job-run ──────────────────────────────────────────────────────────────

def job_run(workspace, run_id: str | None) -> int:
    if run_id is None:
        job = nightly.job_name()
        print(f"Starting the job {job} and waiting for it to finish.")
        run_id, state, page = workspace.run_job(job)
        print(f"Run {run_id}: {page}")
        if state.startswith("still "):
            print(f"The run is {state}. When it ends, check its rows with: uv run --script ops/bundle/check.py "
                  f"job-run --env-file .env --run-id {run_id}")
            return 1
        if state != "SUCCESS":
            print(f"The run ended {state}, so it did not finish every task. Open the run's page to see why.")
            return 1
    engine = workspace.engine()
    rows = engine.run(RUNS, {"run_id": run_id}).rows
    checks = {str(task): (int(passed or 0), int(failed or 0))
              for task, passed, failed in engine.run(CHECKS, {"run_id": run_id}).rows}
    expected = [task.key for task in nightly.job_tasks()]
    for number, (task, status, started, finished, changed) in enumerate(rows, 1):
        passed, failed = checks.get(str(task), (0, 0)) if status == "succeeded" else (0, 0)
        print(f"  {number:>2}. {task}: {status}, started {started}, took {_minutes(started, finished):.1f} minutes, "
              f"{changed} rows changed, {passed} quality checks passed and {failed} failed")
    # Databricks tries a task again when it fails, and each try writes its own row. A task counts by its
    # last try, in the order of the last tries; the failed tries before it are reported, not held against it.
    last = {}
    tries = {}
    for task, status, *_ in rows:
        tries.setdefault(task, []).append(status)
        last[task] = status
    found = list(last)
    problems = [f"{task} has no row." for task in expected if task not in found]
    problems += [f"{task} has {len(tries[task])} rows, and its try before the last one succeeded."
                 for task in found if len(tries[task]) > 1 and "succeeded" in tries[task][:-1]]
    problems += [f"{task} is not a task of the job." for task in found if task not in expected]
    if not problems:
        for number, (task, wanted) in enumerate(zip(found, expected, strict=True), 1):
            if task != wanted:
                problems.append(f"Row {number} is {task}, where the bundle's order has {wanted}.")
                break
    problems += [f"{task} ended {status}." for task, status in last.items() if status != "succeeded"]
    problems += [f"{task} recorded no quality checks in strata.ops.quality_checks." for task, status in last.items()
                 if status == "succeeded" and task in expected and sum(checks.get(task, (0, 0))) == 0]
    if rows:
        took = _minutes(rows[0][2], max(row[3] for row in rows))
        allowed = nightly.window().minutes
        if took > allowed:
            problems.append(f"The run took {took:.0f} minutes, longer than the job's window of {allowed} minutes.")
    retried = [f"{task} was tried {len(tries[task])} times; the first {len(tries[task]) - 1} failed and the last succeeded."
               for task in found if len(tries[task]) > 1 and last[task] == "succeeded"
               and set(tries[task][:-1]) == {"failed"}]
    if problems:
        print(f"Run {run_id} did not record the tasks as the bundle declares them:")
        for line in problems:
            print(f"  {line}")
        return 1
    for line in retried:
        print(f"  {line}")
    print(f"Run {run_id} wrote one row per task to strata.ops.pipeline_runs, in the bundle's order"
          + (", counting each task by its last try." if retried else "."))
    passed, failed = (sum(counts[n] for counts in checks.values()) for n in (0, 1))
    print(f"Its tasks recorded {passed + failed} quality checks in strata.ops.quality_checks: {passed} passed and "
          f"{failed} failed, and it finished inside the job's window of {nightly.window().minutes} minutes.")
    return 0


def _minutes(started, finished) -> float:
    return (schedule.as_utc(finished) - schedule.as_utc(started)).total_seconds() / 60


# ── same-rows ────────────────────────────────────────────────────────────

def _table(columns, rows) -> list[str]:
    return [" | ".join(columns)] + [" | ".join(row) for row in rows]


def _local_engine() -> DuckDBEngine:
    """The fixture database the gate builds or, when it is missing, the same tables built in memory:
    the demo plan's recorded Procurement Plans, every version as the fixture build reads them (ticket 108), then the
    nightly job's tasks over the recorded pages, then the first documents read into passages, then their assertions
    and disagreements."""
    from strata.config import load_thresholds

    if FIXTURE_DB.exists():
        return DuckDBEngine.open(FIXTURE_DB, read_only=True)
    engine = DuckDBEngine.open()
    catalog.build(engine)
    plans.run_on_fixture(engine, thresholds=plans.with_plan_versions(load_thresholds(), plans.EVERY_VERSION))
    nightly.run_locally(engine, run_id="fixture", readers_for=nightly.no_documents)  # the readers run around it
    passages.run_on_fixture(engine, run_id="fixture")
    assertions.run_on_fixture(engine, run_id="fixture")
    return engine


def same_rows(workspace) -> int:
    cases = [case for case in map(ground_truth.read, sorted((REPO / "tests" / "ground_truth").glob("*.sql")))
             if "databricks" in case.engines]
    if not cases:
        print("No ground-truth file is marked to run on databricks, so there is nothing to compare.")
        return 2
    failed = 0
    with _local_engine() as duckdb:
        local_results = {case.path: duckdb.run(case.sql, case.params) for case in cases}
    for case in cases:
        name = case.path.name
        local = local_results[case.path]
        try:
            remote = workspace.engine().run(case.sql, case.params)
        except EngineError as error:
            print(f"{name}: the SQL warehouse could not run it. {error}")
            failed += 1
            continue
        local_rows = [local.columns, *local.as_text()]
        remote_rows = [remote.columns, *remote.as_text()]
        if local_rows == remote_rows == case.expected:
            print(f"{name}: DuckDB and the SQL warehouse returned the same "
                  f"{dayone.count_words(len(local.rows), 'row')}, and they are the rows the file expects.")
            for line in _table(local.columns, local.as_text()):
                print(f"  {line}")
            continue
        failed += 1
        print(f"{name}: the two engines returned different rows, or rows the file does not expect.")
        for label, rows in (("DuckDB", local_rows), ("The SQL warehouse", remote_rows),
                            ("The file expects", case.expected)):
            print(f"  {label}:")
            for line in _table(rows[0], rows[1:]):
                print(f"    {line}")
    return 1 if failed else 0


# ── readiness ────────────────────────────────────────────────────────────

# The page's reading rule, written apart from the tool: the newest measured_at of each subject and
# measure. The page shows the awards for every country (subject all); Kenya's rows are printed too.
LATEST_AWARDS = """
SELECT subject, measure, count, denominator
FROM strata.ops.data_readiness
WHERE source = 'awards' AND subject IN ('all', 'KE') AND measure IN ('coverage_rows', 'linked_step_reference')
QUALIFY row_number() OVER (PARTITION BY subject, measure ORDER BY measured_at DESC) = 1
"""


def _pair(found: tuple[int, int] | None) -> str:
    return f"{found[0]} of {found[1]}" if found else "none"


def readiness_check(workspace) -> int:
    from strata.dbx import Viewer
    from strata.tools import registry

    engine = workspace.engine()
    page = registry.call("data_readiness_for", {}, registry.Context(engine, Viewer(name="the workspace check")))
    awards = [row for row in page["sources"] if row["id"] == "awards" and row["type"] == "measured"]
    if not awards:
        reason = (page["abstention"] or {}).get("reason", "no measures for the awards")
        print(f"The Data readiness page has no awards row to compare: data_readiness_for answered {reason}.")
        return 1
    shown = {}
    for column in ("coverage", "linked"):
        index = awards[0]["cells"][column]["row"]
        shown[column] = None if index is None else (page["rows"][index]["count"], page["rows"][index]["denominator"])
    direct = {(str(subject), str(measure)): (int(count), int(denominator))
              for subject, measure, count, denominator in engine.run(LATEST_AWARDS).rows}
    whole = {"coverage": direct.get(("all", "coverage_rows")), "linked": direct.get(("all", "linked_step_reference"))}
    matches = shown == whole
    print("The Data readiness page's awards row " + ("matches" if matches else "differs from")
          + " a direct query on strata.ops.data_readiness:")
    rows_shown = shown["coverage"][0] if shown["coverage"] else "none"
    rows_direct = whole["coverage"][0] if whole["coverage"] else "none"
    print(f"  award rows held: {rows_shown} on the page, {rows_direct} in the query")
    print(f"  contracts with a STEP reference: {_pair(shown['linked'])} on the page, {_pair(whole['linked'])} in the query")
    kenya_rows, kenya_linked = direct.get(("KE", "coverage_rows")), direct.get(("KE", "linked_step_reference"))
    if kenya_rows and kenya_linked:
        print(f"Kenya's own measures, for comparison: {kenya_rows[0]} award rows; {_pair(kenya_linked)} contracts "
              "with a STEP reference.")
    return 0 if matches else 1


# ── schedules ────────────────────────────────────────────────────────────

def _when(facts: dict) -> str:
    start = schedule.daily_start(facts["quartz"])
    paused = " (paused)" if facts.get("paused") else ""
    return f"daily at {start:%H:%M} {facts['timezone']}{paused}"


def _longest(facts: dict) -> int | None:
    return math.ceil(max(facts["durations"])) if facts["durations"] else None


def _measured(facts: dict) -> str:
    took = dayone.count_words(_longest(facts), "minute")
    if len(facts["durations"]) == 1:
        return f"Its one finished run took {took}"
    return f"Its longest of the last {dayone.count_words(len(facts['durations']), 'run')} took {took}"


def schedules_block(strata: dict, fairshare: dict, today: dt.date) -> tuple[bool, list[str]]:
    """Whether the two jobs never meet, and the lines the bundle's notes record."""
    days = [today + dt.timedelta(days=n) for n in range(366)]
    strata_line = (f"- Strata's job: {strata['name']}, {_when(strata)}. {_measured(strata)}, and it stops after "
                   f"{dayone.count_words(strata['timeout_minutes'], 'minute')}.")
    measured_line = (f"- Measured: {dayone.long_date(today)}, with `uv run --script ops/bundle/check.py schedules "
                     "--env-file .env --write`.")
    if not fairshare.get("quartz"):
        return True, [f"- fairshare's job: {fairshare['name']}, with no schedule. It runs only when someone starts it.",
                      strata_line, "- Overlap: none, because fairshare's job never starts on its own.", measured_line]
    lines = [f"- fairshare's job: {fairshare['name']}, {_when(fairshare)}. {_measured(fairshare)}.", strata_line]

    def window(facts, minutes):
        return schedule.Window(facts["name"], schedule.daily_start(facts["quartz"]), facts["timezone"], minutes)

    other = window(fairshare, _longest(fairshare))
    measured = schedule.overlapping_days(window(strata, _longest(strata)), other, days)
    limit = schedule.overlapping_days(window(strata, strata["timeout_minutes"]), other, days)
    span = f"from {dayone.long_date(days[0])} to {dayone.long_date(days[-1])}"
    if measured:
        lines.append(f"- Overlap: on {len(measured)} of the 366 days {span}, starting "
                     f"{dayone.long_date(measured[0])}. Move one of the two schedules.")
    elif limit:
        lines.append(f"- Overlap: none with the measured durations, {span}. If Strata's job ran to its limit, "
                     f"the two would meet on {dayone.count_words(len(limit), 'day')}, starting "
                     f"{dayone.long_date(limit[0])}.")
    else:
        lines.append(f"- Overlap: none. With these durations the two jobs share no minute on any day {span}, "
                     "and the same holds if Strata's job runs to its limit.")
    lines.append(measured_line)
    return not measured, lines


def schedules(workspace, fairshare_job: str | None, write: bool, notes: Path, today: dt.date) -> int:
    job = nightly.job_name()
    strata = workspace.job_facts(job)
    if strata is None:
        print(f"I found no job named {job}. Deploy first: uv run --script ops/bundle/deploy.py --env-file .env")
        return 2
    if fairshare_job is None:
        names = [name for name in workspace.job_names() if "fairshare" in name.lower()]
        if len(names) != 1:
            found = ", ".join(workspace.job_names()) or "none"
            print(f"I found no job whose name contains fairshare, or more than one. The workspace's jobs are: "
                  f"{found}. Name fairshare's nightly job with --fairshare-job.")
            return 2
        fairshare_job = names[0]
    fairshare = workspace.job_facts(fairshare_job)
    if fairshare is None:
        print(f"I found no job named {fairshare_job}.")
        return 2
    for facts in (fairshare, strata):
        if facts.get("quartz") and not facts["durations"]:
            print(f"{facts['name']} has no finished runs to measure. Run it once by hand, then check again. "
                  "For Strata's job: uv run --script ops/bundle/check.py job-run --env-file .env")
            return 2
    try:
        apart, lines = schedules_block(strata, fairshare, today)
    except schedule.ScheduleError as error:
        print(error)
        return 2
    for line in lines:
        print(line)
    if write:
        text = notes.read_text()
        if not BLOCK.search(text):
            print(f"{notes} has no <!-- bundle:schedules --> block to write into.")
            return 2
        notes.write_text(BLOCK.sub(lambda match: match.group(1) + "\n".join(lines) + "\n" + match.group(2), text))
        print(f"I recorded both schedules in {notes.relative_to(REPO) if notes.is_relative_to(REPO) else notes}. "
              "Commit it on build/strata.")
    return 0 if apart else 1


# ── Command line ─────────────────────────────────────────────────────────

def parse(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line. --env-file may come before the subcommand or after it.
    docs/workspace-catchup.md, bundle/README.md, the ground-truth SQL comments and this file's own
    messages write it after. Given in both places, the later one wins."""
    shared = argparse.ArgumentParser(add_help=False)
    # SUPPRESS keeps a subcommand that was not given --env-file from writing over the one given
    # before it. The namespace below starts with None, which means the main checkout's .env.
    shared.add_argument("--env-file", type=Path, default=argparse.SUPPRESS,
                        help="The main checkout's .env, which the wizard filled. That file is the default.")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], parents=[shared])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("job-run", parents=[shared], help="Run the nightly job by hand and check its rows.")
    run.add_argument("--run-id", help="Check this finished run instead of starting one.")
    commands.add_parser("same-rows", parents=[shared],
                        help="Run the sample queries on DuckDB and on the SQL warehouse.")
    commands.add_parser("readiness", parents=[shared],
                        help="Check the Data readiness page's awards row against a direct query.")
    times = commands.add_parser("schedules", parents=[shared], help="Check fairshare's and Strata's nightly schedules.")
    times.add_argument("--fairshare-job", help="fairshare's nightly job, when its name does not contain fairshare.")
    times.add_argument("--write", action="store_true", help="Record both schedules in bundle/README.md.")
    times.add_argument("--notes", type=Path, default=NOTES, help=argparse.SUPPRESS)
    return parser.parse_args(argv, argparse.Namespace(env_file=None))


def main(argv: list[str] | None = None, workspace=None, env: dict | None = None) -> int:
    args = parse(argv)

    if env is None:
        try:
            env = load_workspace_env(args.env_file)
        except WorkspaceEnvError as error:
            print(error, file=sys.stderr)
            return 2
    if workspace is None:
        from bundle_live import LiveWorkspace

        workspace = LiveWorkspace(env)

    if args.command == "job-run":
        return job_run(workspace, args.run_id)
    if args.command == "same-rows":
        return same_rows(workspace)
    if args.command == "readiness":
        return readiness_check(workspace)
    return schedules(workspace, args.fairshare_job, args.write, args.notes, dt.date.today())


if __name__ == "__main__":
    sys.exit(main())
