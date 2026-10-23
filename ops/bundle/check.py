# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Check the deployed catalog and nightly job on the shared workspace.

Run each check from the main checkout, after the deploy (ops/bundle/deploy.py):

    uv run --script ops/bundle/check.py job-run --env-file .env
    uv run --script ops/bundle/check.py same-rows --env-file .env
    uv run --script ops/bundle/check.py schedules --env-file .env --write

job-run    Starts the nightly job by hand, waits for it, and checks that strata.ops.pipeline_runs
           holds one row per task for that run, in the order bundle/nightly.yml gives. Pass
           --run-id to check a run that already finished instead.
same-rows  Runs each ground-truth query marked for databricks (tests/ground_truth) on DuckDB and
           on the SQL warehouse, and checks that both return the rows the file expects. DuckDB
           reads the fixture database, or, without it, builds the catalog's tables in memory, reads
           the demo plan's recorded Procurement Plans into them and runs the nightly job's tasks
           over the recorded pages, as the fixture build does. Run it after the live plan run
           (ops/plans/run_live.py) and job-run, because some files read what they wrote.
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
from strata.lakehouse import catalog, ground_truth, nightly, plans, schedule  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine, EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

NOTES = REPO / "bundle" / "README.md"
FIXTURE_DB = REPO / "data" / "out" / "fixture.duckdb"
BLOCK = re.compile(r"(<!-- bundle:schedules -->\n).*?(<!-- /bundle:schedules -->)", re.S)
RUNS = """
SELECT task_key, status, started_at
FROM strata.ops.pipeline_runs
WHERE run_id = :run_id
ORDER BY started_at
"""


# ── job-run ──────────────────────────────────────────────────────────────

def job_run(workspace, run_id: str | None) -> int:
    if run_id is None:
        job = nightly.job_name()
        print(f"Starting the job {job} and waiting for it to finish.")
        run_id, state, page = workspace.run_job(job)
        print(f"Run {run_id}: {page}")
        if state != "SUCCESS":
            print(f"The run ended {state}, so it did not finish every task. Open the run's page to see why.")
            return 1
    rows = workspace.engine().run(RUNS, {"run_id": run_id}).as_text()
    expected = [task.key for task in nightly.job_tasks()]
    found = [task for task, _, _ in rows]
    for number, (task, status, started) in enumerate(rows, 1):
        print(f"  {number:>2}. {task}: {status}, started {started}")
    problems = [f"{task} has no row." for task in expected if task not in found]
    problems += [f"{task} has {found.count(task)} rows." for task in expected if found.count(task) > 1]
    problems += [f"{task} is not a task of the job." for task in found if task not in expected]
    if not problems:
        for number, (task, wanted) in enumerate(zip(found, expected, strict=True), 1):
            if task != wanted:
                problems.append(f"Row {number} is {task}, where the bundle's order has {wanted}.")
                break
    problems += [f"{task} ended {status}." for task, status, _ in rows if status != "succeeded"]
    if problems:
        print(f"Run {run_id} did not record the tasks as the bundle declares them:")
        for line in problems:
            print(f"  {line}")
        return 1
    print(f"Run {run_id} wrote one row per task to strata.ops.pipeline_runs, in the bundle's order.")
    return 0


# ── same-rows ────────────────────────────────────────────────────────────

def _table(columns, rows) -> list[str]:
    return [" | ".join(columns)] + [" | ".join(row) for row in rows]


def _local_engine() -> DuckDBEngine:
    """The fixture database the gate builds or, when it is missing, the same tables built in memory:
    the demo plan's recorded Procurement Plans, then the nightly job's tasks over the recorded pages."""
    if FIXTURE_DB.exists():
        return DuckDBEngine.open(FIXTURE_DB, read_only=True)
    engine = DuckDBEngine.open()
    catalog.build(engine)
    plans.run_on_fixture(engine)
    nightly.run_locally(engine, run_id="fixture")
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

def main(argv: list[str] | None = None, workspace=None, env: dict | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's .env, which the wizard filled. That file is the default.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("job-run", help="Run the nightly job by hand and check its rows.")
    run.add_argument("--run-id", help="Check this finished run instead of starting one.")
    commands.add_parser("same-rows", help="Run the sample queries on DuckDB and on the SQL warehouse.")
    times = commands.add_parser("schedules", help="Check fairshare's and Strata's nightly schedules.")
    times.add_argument("--fairshare-job", help="fairshare's nightly job, when its name does not contain fairshare.")
    times.add_argument("--write", action="store_true", help="Record both schedules in bundle/README.md.")
    times.add_argument("--notes", type=Path, default=NOTES, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

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
    return schedules(workspace, args.fairshare_job, args.write, args.notes, dt.date.today())


if __name__ == "__main__":
    sys.exit(main())
