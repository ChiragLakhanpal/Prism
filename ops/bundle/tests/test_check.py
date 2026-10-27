"""The workspace checks: a manual run of the nightly job, the sample query on both engines, and
the two nightly schedules against their measured durations.

Fakes stand in for the workspace. Their job runs the real tasks on DuckDB, and their warehouse is
DuckDB, so the checks read real rows. docs/workspace-catchup.md runs each check for real.
"""

import contextlib
import functools
import re
import shlex
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "bundle"))

import check  # noqa: E402

from strata.knowledge import assertions  # noqa: E402
from strata.lakehouse import catalog, nightly, passages, plans  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine, Result  # noqa: E402

FIXTURE_DB = Path(__file__).resolve().parents[3] / "data" / "out" / "fixture.duckdb"


def refused(source, engine):
    raise RuntimeError("HTTP Error 417: Expectation Failed")


class FakeWorkspace:
    def __init__(self, order=None, state="SUCCESS", jobs=None, warehouse=None, failed_first=()):
        self.duckdb = DuckDBEngine.open()
        catalog.build(self.duckdb)
        self.order, self.state, self.failed_first = order, state, failed_first
        self.jobs = jobs or {}
        self.warehouse = warehouse

    def engine(self):
        return self.warehouse or self.duckdb

    def run_job(self, name):
        run_id = "880001"
        for key in self.order or [task.key for task in nightly.job_tasks()]:
            if key in self.failed_first:  # Databricks tries a failed task again; each try writes a row
                with contextlib.suppress(RuntimeError):
                    nightly.run_task(self.duckdb, key, run_id, fetch=refused)
            nightly.run_task(self.duckdb, key, run_id, fetch=lambda source, engine: ())  # no pages to fetch
        return run_id, self.state, "https://dbc-1.cloud.databricks.com/jobs/1/runs/880001"

    def job_names(self):
        return sorted(self.jobs)

    def job_facts(self, name):
        return self.jobs.get(name)


def checked(argv, workspace, capsys):
    code = check.main(argv, workspace=workspace, env={"DATABRICKS_HOST": "https://dbc-1"})
    return code, capsys.readouterr().out


def test_an_env_file_with_no_way_to_sign_in_stops_before_the_workspace(tmp_path, capsys):
    env = tmp_path / "strata.env"
    env.write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\nDATABRICKS_WAREHOUSE_ID='wh-1'\n")

    code = check.main(["--env-file", str(env), "job-run"], workspace=FakeWorkspace())

    assert code == 2
    assert "DATABRICKS_TOKEN (or DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET)" in capsys.readouterr().err


# ── A manual run of the nightly job ──────────────────────────────────────

def test_a_run_that_records_every_task_in_plan_order_passes(capsys):
    code, out = checked(["job-run"], FakeWorkspace(), capsys)

    assert code == 0
    assert "Run 880001 wrote one row per task to strata.ops.pipeline_runs, in the bundle's order." in out
    assert "10. refresh_drafts" in out


def test_the_check_shows_each_task_s_duration_rows_changed_and_quality_checks(capsys):
    """Ticket 43: strata.ops records each task's duration, rows changed and quality checks passed and failed."""
    code, out = checked(["job-run"], FakeWorkspace(), capsys)

    assert code == 0
    line = next(line for line in out.splitlines() if line.strip().startswith("2. bronze_to_gold"))
    assert re.search(r"took \d+\.\d minutes, \d+ rows changed, \d+ quality checks passed and \d+ failed$", line)
    assert re.search(r"Its tasks recorded (\d+) quality checks in strata.ops.quality_checks: \d+ passed and \d+ "
                     r"failed, and it finished inside the job's window of 150 minutes.", out)


def test_a_task_that_recorded_no_quality_checks_fails(capsys, monkeypatch):
    monkeypatch.setattr("strata.lakehouse.quality.check", lambda engine, task_key: [])

    code, out = checked(["job-run"], FakeWorkspace(), capsys)

    assert code == 1
    assert "refresh_drafts recorded no quality checks in strata.ops.quality_checks." in out


def test_a_run_longer_than_the_window_fails(capsys, monkeypatch):
    from strata.lakehouse.schedule import Window

    monkeypatch.setattr(check.nightly, "window", lambda bundle=None: Window("Strata's nightly job", None, "UTC", -1))

    code, out = checked(["job-run"], FakeWorkspace(), capsys)

    assert code == 1
    assert "longer than the job's window of -1 minutes" in out


def test_a_run_whose_rows_come_out_of_order_fails_and_names_the_first_difference(capsys):
    order = [task.key for task in nightly.job_tasks()]
    order[1], order[2] = order[2], order[1]

    code, out = checked(["job-run"], FakeWorkspace(order=order), capsys)

    assert code == 1
    assert "Row 2 is parse_and_embed, where the bundle's order has bronze_to_gold." in out


def test_a_task_databricks_tried_again_counts_by_its_last_try(capsys):
    """Run 626310583145231 on October 24, 2026: fetch_by_watermark failed on HTTP 417 from a World Bank host,
    Databricks tried it again, and the second try succeeded. Each try writes a row to pipeline_runs."""
    code, out = checked(["job-run"], FakeWorkspace(failed_first=("fetch_by_watermark",)), capsys)

    assert code == 0
    assert "fetch_by_watermark was tried 2 times; the first 1 failed and the last succeeded." in out
    assert "in the bundle's order, counting each task by its last try." in out


def test_a_task_whose_last_try_failed_still_fails_the_run(capsys):
    code, out = checked(["job-run"], FakeWorkspace(order=["fetch_by_watermark"] * 2 + [task.key for task in nightly.job_tasks()][1:],
                                                 failed_first=()), capsys)

    assert code == 1
    assert "fetch_by_watermark has 2 rows, and its try before the last one succeeded." in out


def test_a_run_that_skipped_a_task_fails(capsys):
    order = [task.key for task in nightly.job_tasks()][:-1]

    code, out = checked(["job-run"], FakeWorkspace(order=order), capsys)

    assert code == 1
    assert "refresh_drafts has no row" in out


def test_a_run_still_going_when_the_wait_ends_says_how_to_check_it_later(capsys):
    code, out = checked(["job-run"], FakeWorkspace(state="still running after 160 minutes"), capsys)

    assert code == 1
    assert "The run is still running after 160 minutes." in out
    assert "job-run --env-file .env --run-id 880001" in out


def test_a_run_that_did_not_succeed_fails(capsys):
    code, out = checked(["job-run"], FakeWorkspace(state="FAILED"), capsys)

    assert code == 1
    assert "The run ended FAILED" in out


# ── The sample query on both engines ─────────────────────────────────────

@functools.cache
def deployed_warehouse():
    """A SQL warehouse after the deploy, the live plan run, one run of the nightly job and the live
    passage run: the fixture database the gate's python lane builds first, from the recorded plans,
    pages and documents, opened read-only, since the tests only read it. Building it again here took
    each worker a few seconds once the passage run read the whole document slice (review r2 P14)."""
    if FIXTURE_DB.exists():
        return DuckDBEngine.open(FIXTURE_DB, read_only=True)
    engine = DuckDBEngine.open()
    catalog.build(engine)
    plans.run_on_fixture(engine)
    nightly.run_locally(engine, readers_for=nightly.no_documents)  # the readers run around it, as in the build
    passages.run_on_fixture(engine)
    assertions.run_on_fixture(engine)
    return engine


class Changed:
    """A warehouse whose answer differs from DuckDB's in the last cell of the first row."""

    name = "databricks"

    def __init__(self):
        self.engine = deployed_warehouse()

    def run(self, sql, params=None):
        result = self.engine.run(sql, params)
        rows = [list(row) for row in result.as_text()]
        if rows:
            rows[0][-1] = "2017"
        return Result(result.columns, tuple(tuple(row) for row in rows))


def test_the_sample_queries_return_the_same_rows_on_duckdb_and_the_warehouse(capsys):
    code, out = checked(["same-rows"], FakeWorkspace(warehouse=deployed_warehouse()), capsys)

    assert code == 0
    assert ("showcase_fiscal_years.sql: DuckDB and the SQL warehouse returned the same four rows, "
            "and they are the rows the file expects.") in out
    assert ("pipeline_runs_columns.sql: DuckDB and the SQL warehouse returned the same seven rows, "
            "and they are the rows the file expects.") in out
    assert ("delay_from_first_published_planned_date.sql: DuckDB and the SQL warehouse returned the same "
            "one row, and they are the rows the file expects.") in out
    assert ("data_notes_actual_amount_zero.sql: DuckDB and the SQL warehouse returned the same two rows, "
            "and they are the rows the file expects.") in out


def test_without_the_fixture_database_the_duckdb_side_builds_the_catalog_in_memory(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(check, "FIXTURE_DB", tmp_path / "missing.duckdb")

    code, out = checked(["same-rows"], FakeWorkspace(warehouse=deployed_warehouse()), capsys)

    assert code == 0
    assert "pipeline_runs_columns.sql: DuckDB and the SQL warehouse returned the same seven rows" in out


def test_a_warehouse_that_returns_other_rows_fails_and_shows_both(capsys):
    code, out = checked(["same-rows"], FakeWorkspace(warehouse=Changed()), capsys)

    assert code == 1
    assert "returned different rows" in out
    assert "Mid-term review | 2016-05-16 | 2016 | 2017" in out


# ── The two schedules ────────────────────────────────────────────────────

def facts(name, quartz, zone, durations, timeout_minutes=None, paused=False):
    return {"name": name, "quartz": quartz, "timezone": zone, "paused": paused,
            "timeout_minutes": timeout_minutes, "durations": durations}


STRATA = facts("strata nightly", "0 0 5 * * ?", "America/New_York", [4, 6, 5], timeout_minutes=150)


def test_schedules_that_never_meet_pass_and_the_notes_record_both(tmp_path, capsys):
    notes = tmp_path / "README.md"
    shutil.copy(REPO / "bundle" / "README.md", notes)
    jobs = {"strata nightly": STRATA, "fairshare nightly": facts("fairshare nightly", "0 0 2 * * ?", "UTC", [20, 35])}

    code, out = checked(["schedules", "--write", "--notes", str(notes)], FakeWorkspace(jobs=jobs), capsys)

    assert code == 0
    block = notes.read_text()
    assert "- fairshare's job: fairshare nightly, daily at 02:00 UTC. Its longest of the last two runs took " \
           "35 minutes." in block
    assert "- Strata's job: strata nightly, daily at 05:00 America/New_York. Its longest of the last three " \
           "runs took six minutes, and it stops after 150 minutes." in block
    assert "- Overlap: none." in block
    assert block.count("<!-- bundle:schedules -->") == 1
    assert "Not measured yet" not in block


def test_a_job_with_one_finished_run_is_described_as_one_run(tmp_path, capsys):
    """The catch-up runs the job once before it writes the notes, so one run is the common case."""
    notes = tmp_path / "README.md"
    shutil.copy(REPO / "bundle" / "README.md", notes)
    jobs = {"strata nightly": facts("strata nightly", "0 0 5 * * ?", "America/New_York", [2], timeout_minutes=150),
            "fairshare nightly": facts("fairshare nightly", "0 0 2 * * ?", "UTC", [20])}

    code, _ = checked(["schedules", "--write", "--notes", str(notes)], FakeWorkspace(jobs=jobs), capsys)

    assert code == 0
    block = notes.read_text()
    assert "- fairshare's job: fairshare nightly, daily at 02:00 UTC. Its one finished run took 20 minutes." in block
    assert "- Strata's job: strata nightly, daily at 05:00 America/New_York. Its one finished run took two " \
           "minutes, and it stops after 150 minutes." in block
    assert "the last one run" not in block


def test_a_fairshare_run_that_reaches_into_strata_s_window_fails(capsys):
    jobs = {"strata nightly": STRATA,
            "fairshare nightly": facts("fairshare nightly", "0 30 4 * * ?", "America/New_York", [60])}

    code, out = checked(["schedules"], FakeWorkspace(jobs=jobs), capsys)

    assert code == 1
    assert "- Overlap: on 366 of the 366 days" in out


def test_without_a_fairshare_job_the_check_lists_the_jobs_it_found(capsys):
    jobs = {"strata nightly": STRATA, "airline refresh": facts("airline refresh", "0 0 3 * * ?", "UTC", [10])}

    code, out = checked(["schedules"], FakeWorkspace(jobs=jobs), capsys)

    assert code == 2
    assert "I found no job whose name contains fairshare" in out
    assert "airline refresh" in out


def test_a_fairshare_job_with_no_finished_runs_cannot_be_measured(capsys):
    jobs = {"strata nightly": STRATA,
            "fairshare nightly": facts("fairshare nightly", "0 0 2 * * ?", "UTC", [])}

    code, out = checked(["schedules", "--fairshare-job", "fairshare nightly"], FakeWorkspace(jobs=jobs), capsys)

    assert code == 2  # could not run, as the docstring says, rather than a failed check
    assert "has no finished runs to measure" in out


def test_a_fairshare_job_with_no_schedule_cannot_overlap_and_the_notes_say_so(tmp_path, capsys):
    notes = tmp_path / "README.md"
    shutil.copy(REPO / "bundle" / "README.md", notes)
    jobs = {"strata nightly": STRATA, "fairshare refresh": facts("fairshare refresh", None, None, [12])}

    code, out = checked(["schedules", "--write", "--notes", str(notes)], FakeWorkspace(jobs=jobs), capsys)

    assert code == 0
    assert "- fairshare's job: fairshare refresh, with no schedule. It runs only when someone starts it." \
           in notes.read_text()
    assert "- Overlap: none, because fairshare's job never starts on its own." in out


def test_a_schedule_that_is_not_daily_is_named_rather_than_guessed(capsys):
    jobs = {"strata nightly": STRATA,
            "fairshare nightly": facts("fairshare nightly", "0 0 2 ? * MON-FRI", "UTC", [20])}

    code, out = checked(["schedules"], FakeWorkspace(jobs=jobs), capsys)

    assert code == 2
    assert "only schedules that run once a day" in out


# ── The command line ─────────────────────────────────────────────────────
# docs/workspace-catchup.md, bundle/README.md, check.py's own messages and the ground-truth SQL
# comments write --env-file after the subcommand. The top parser takes it before the subcommand.
# Both orders must give the same arguments. Parsing reads no env file, so these paths need not exist.

@pytest.mark.parametrize(("after", "before"), [
    (["job-run", "--env-file", "{env}"], ["--env-file", "{env}", "job-run"]),
    (["same-rows", "--env-file", "{env}"], ["--env-file", "{env}", "same-rows"]),
    (["schedules", "--env-file", "{env}", "--write"], ["--env-file", "{env}", "schedules", "--write"]),
], ids=["job-run", "same-rows", "schedules"])
def test_the_env_file_may_come_before_or_after_the_subcommand(tmp_path, after, before):
    env = tmp_path / "strata.env"

    written = vars(check.parse([part.format(env=env) for part in after]))
    top = vars(check.parse([part.format(env=env) for part in before]))

    assert written == top
    assert written["env_file"] == env


def test_each_subcommand_parses_to_its_own_arguments(tmp_path):
    env = tmp_path / "strata.env"

    assert vars(check.parse(["job-run", "--env-file", str(env)])) == \
        {"env_file": env, "command": "job-run", "run_id": None}
    assert vars(check.parse(["same-rows", "--env-file", str(env)])) == {"env_file": env, "command": "same-rows"}
    assert vars(check.parse(["schedules", "--env-file", str(env), "--write"])) == \
        {"env_file": env, "command": "schedules", "fairshare_job": None, "write": True, "notes": check.NOTES}
    assert vars(check.parse(["schedules", "--write", "--env-file", str(env)])) == \
        vars(check.parse(["schedules", "--env-file", str(env), "--write"]))


def test_an_env_file_given_before_and_after_the_subcommand_uses_the_later_one(tmp_path):
    first, later = tmp_path / "first.env", tmp_path / "later.env"

    assert check.parse(["--env-file", str(first), "job-run", "--env-file", str(later)]).env_file == later
    assert check.parse(["--env-file", str(first), "same-rows"]).env_file == first


def test_without_an_env_file_the_check_reads_the_main_checkout_s():
    assert check.parse(["job-run"]).env_file is None
    assert check.parse(["schedules", "--write"]).env_file is None


SIX_FORMS = [["job-run", "--env-file", "{env}"], ["--env-file", "{env}", "job-run"],
             ["same-rows", "--env-file", "{env}"], ["--env-file", "{env}", "same-rows"],
             ["schedules", "--env-file", "{env}", "--write"], ["--env-file", "{env}", "schedules", "--write"]]


def test_each_form_stops_at_a_missing_env_file_with_the_same_sentence(tmp_path, capsys):
    missing = tmp_path / "missing.env"
    nothing = object()  # stands in for the workspace, which the check must not reach

    for form in SIX_FORMS:
        code = check.main([part.format(env=missing) for part in form], workspace=nothing)

        assert code == 2, form
        assert capsys.readouterr().err == \
            f"There is no env file at {missing}. Run the wizard first: bash ops/wizard/strata-setup.sh\n", form


@pytest.mark.parametrize("argv", [["job-run", "--nope"], ["--nope", "same-rows"], ["job-run", "--write"],
                                  ["same-rows", "--run-id", "880001"], ["--write", "schedules"]],
                         ids=["unknown-after", "unknown-before", "write-on-job-run", "run-id-on-same-rows",
                              "write-before-schedules"])
def test_a_wrong_option_still_exits_with_code_2(argv, capsys):
    with pytest.raises(SystemExit) as stopped:
        check.main(argv, workspace=object(), env={})

    assert stopped.value.code == 2
    assert "error:" in capsys.readouterr().err


# A command ends at a backtick, a closing parenthesis, the end of its line, or a double quote that
# closes nothing on that line, such as the end of the Python string that holds it. A double-quoted
# argument, such as "<main checkout>/.env", is read whole (ticket 80).
COMMAND = re.compile(r'uv run --script ops/bundle/check\.py ((?:[^`"\n)]|"[^`"\n]*")*)')


def commands_in(text):
    """Each check.py command in text, split into arguments the way the shell splits them."""
    for match in COMMAND.finditer(text):
        yield shlex.split(match.group(1))


def written_commands():
    """Each check.py command line the repo writes for a person to run: in the docs, the bundle's
    notes, the scripts and their messages, and the ground-truth SQL comments."""
    places = [REPO / "README.md", *(REPO / "docs").rglob("*.md"), REPO / "bundle" / "README.md",
              *(REPO / "ops").rglob("*.py"), *(REPO / "tests" / "ground_truth").glob("*.sql")]
    for path in places:
        text = path.read_text()
        if path.suffix == ".py":
            text = re.sub(r"\"\s*\n\s*f?\"", "", text)  # a message Python splits over two string literals
        for argv in commands_in(text):
            yield path.relative_to(REPO).as_posix(), argv


# Joined here, so the scan above never reads these examples as commands this file writes.
CHECK_PY = "uv run --script ops/bundle/" + "check.py"


@pytest.mark.parametrize("text", [
    f'    {CHECK_PY} same-rows --env-file "<main checkout>/.env"\n',
    f'Run `{CHECK_PY} same-rows --env-file "<main checkout>/.env"` after the deploy.\n',
], ids=["code-block", "backticks"])
def test_a_double_quoted_argument_in_a_written_command_is_one_argument(text):
    """Ticket 76's merge gate cut `--env-file "<main checkout>/.env"` at the quote; the shell reads it whole."""
    assert list(commands_in(text)) == [["same-rows", "--env-file", "<main checkout>/.env"]]
    assert check.parse(next(commands_in(text))).env_file == Path("<main checkout>/.env")


def test_a_command_inside_a_python_string_ends_at_the_string_s_closing_quote():
    text = f'print("When it ends, run {CHECK_PY} job-run --env-file .env")\n'

    assert list(commands_in(text)) == [["job-run", "--env-file", ".env"]]


def test_every_check_command_the_repo_writes_parses_as_written(capsys):
    commands = list(written_commands())
    unparsed = []
    for place, argv in commands:
        try:
            args = check.parse(argv)
        except SystemExit:
            unparsed.append(f"{place}: {' '.join(argv)}. {capsys.readouterr().err.splitlines()[-1]}")
            continue
        if "--env-file" in argv:
            assert args.env_file == Path(argv[argv.index("--env-file") + 1]), (place, argv)

    assert unparsed == []
    places = {place for place, _ in commands}
    assert {"docs/workspace-catchup.md", "ops/bundle/check.py", "bundle/README.md"} <= places
    assert any(place.startswith("tests/ground_truth/") for place in places)
    assert ("ops/bundle/check.py", ["schedules", "--env-file", ".env", "--write"]) in commands


# ── readiness ────────────────────────────────────────────────────────────

def fixture_warehouse():
    """The SQL warehouse after the nightly job, the plan run and the passage run: the fixture database,
    which the gate builds before this lane's tests."""
    return DuckDBEngine.open(check.FIXTURE_DB, read_only=True)


def test_the_data_readiness_page_s_award_rows_and_link_rate_match_a_direct_query(capsys):
    """Ticket 16: on the workspace, a direct query on strata.ops matches the page's numbers."""
    code, out = checked(["readiness"], FakeWorkspace(warehouse=fixture_warehouse()), capsys)

    assert code == 0
    assert "The Data readiness page's awards row matches a direct query on strata.ops.data_readiness:" in out
    assert "  award rows held: 632 on the page, 632 in the query" in out
    assert "  contracts with a STEP reference: 528 of 603 on the page, 528 of 603 in the query" in out
    assert "Kenya's own measures, for comparison: 632 award rows; 528 of 603 contracts with a STEP reference." in out


def test_a_page_with_no_measures_fails_the_readiness_check_and_says_why(capsys):
    code, out = checked(["readiness"], FakeWorkspace(), capsys)

    assert code == 1
    assert "The Data readiness page has no awards row to compare: data_readiness_for answered no_measures." in out
