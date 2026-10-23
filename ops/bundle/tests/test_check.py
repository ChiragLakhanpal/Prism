"""The workspace checks: a manual run of the nightly job, the sample query on both engines, and
the two nightly schedules against their measured durations.

Fakes stand in for the workspace. Their job runs the real tasks on DuckDB, and their warehouse is
DuckDB, so the checks read real rows. docs/workspace-catchup.md runs each check for real.
"""

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "bundle"))

import check  # noqa: E402

from strata.lakehouse import catalog, nightly  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine, Result  # noqa: E402


class FakeWorkspace:
    def __init__(self, order=None, state="SUCCESS", jobs=None, warehouse=None):
        self.duckdb = DuckDBEngine.open()
        catalog.build(self.duckdb)
        self.order, self.state = order, state
        self.jobs = jobs or {}
        self.warehouse = warehouse

    def engine(self):
        return self.warehouse or self.duckdb

    def run_job(self, name):
        run_id = "880001"
        for key in self.order or [task.key for task in nightly.job_tasks()]:
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


def test_a_run_whose_rows_come_out_of_order_fails_and_names_the_first_difference(capsys):
    order = [task.key for task in nightly.job_tasks()]
    order[1], order[2] = order[2], order[1]

    code, out = checked(["job-run"], FakeWorkspace(order=order), capsys)

    assert code == 1
    assert "Row 2 is parse_and_embed, where the bundle's order has bronze_to_gold." in out


def test_a_run_that_skipped_a_task_fails(capsys):
    order = [task.key for task in nightly.job_tasks()][:-1]

    code, out = checked(["job-run"], FakeWorkspace(order=order), capsys)

    assert code == 1
    assert "refresh_drafts has no row" in out


def test_a_run_that_did_not_succeed_fails(capsys):
    code, out = checked(["job-run"], FakeWorkspace(state="FAILED"), capsys)

    assert code == 1
    assert "The run ended FAILED" in out


# ── The sample query on both engines ─────────────────────────────────────

def deployed_warehouse():
    """A SQL warehouse after the deploy and one run of the nightly job: DuckDB with the catalog's
    tables built and filled, here from the recorded pages."""
    engine = DuckDBEngine.open()
    catalog.build(engine)
    nightly.run_locally(engine)
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
