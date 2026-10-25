"""The nightly job's quality checks (seam 1; ticket 43; the 45 brief, section 6): each task, when it finishes,
checks the tables config/quality_checks.toml names for it (row counts against config/thresholds.toml's
ranges, missing keys, missing Disclosed dates, duplicate rows, and contact details left in notices) and keeps
every result in strata.ops.quality_checks with the night, the task, the check, the table and the count found.

Each test runs one task as the job runs it, on a writable copy of the fixture database the gate built.
"""

import datetime as dt
import shutil

import pytest

from strata import config
from strata.lakehouse import catalog, nightly
from strata.lakehouse.engine import DuckDBEngine

NIGHT = dt.datetime(2026, 10, 24, 7, 0, tzinfo=dt.UTC)  # 03:00 in Washington, when the job starts


@pytest.fixture
def fixture_copy(fixture_db, tmp_path):
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        yield engine


def clock(start=NIGHT):
    ticks = iter(range(10**6))
    return lambda: start + dt.timedelta(seconds=next(ticks))


def run(engine, task, run_id="night-2", when=NIGHT):
    nightly.main(["--task", task, "--run-id", run_id, "--src", "src"], engine, fetch=lambda s, e: (),
                 clock=clock(when))


def checks(engine, run_id="night-2", task=None):
    rows = engine.run("SELECT night, task_key, check_kind, table_name, key_name, found, expected_min, expected_max, "
                      "passed FROM strata.ops.quality_checks WHERE run_id = :run_id "
                      "AND (:task = '' OR task_key = :task) ORDER BY checked_at, table_name, check_kind, key_name",
                      {"run_id": run_id, "task": task or ""}).rows
    return [dict(zip(("night", "task", "check", "table", "key", "found", "min", "max", "passed"), row)) for row in rows]


def test_every_task_of_the_job_checks_at_least_one_table_and_every_table_checked_is_in_the_catalog():
    registry = config.load_quality_checks()
    defined = {d.full_name for d in catalog.table_definitions()}

    assert {task.key for task in nightly.job_tasks()} == {entry.task for entry in registry}
    assert {entry.table for entry in registry} <= defined


def test_a_task_records_each_check_with_its_night_task_table_and_count_and_the_fixture_passes_them_all(fixture_copy):
    run(fixture_copy, "bronze_to_gold")

    found = checks(fixture_copy)
    assert {row["night"] for row in found} == {dt.date(2026, 10, 24)}
    assert {row["task"] for row in found} == {"bronze_to_gold"}
    assert [row for row in found if not row["passed"]] == []
    project = {(row["check"], row["key"]): row for row in found if row["table"] == "strata.gold.project"}
    assert set(project) == {("row_count", None), ("missing_key", "project_id"), ("missing_public_from", None),
                            ("duplicates", None)}
    assert project[("row_count", None)]["found"] == 93  # the fixture's projects
    assert (project[("row_count", None)]["min"], project[("duplicates", None)]["found"]) == (1, 0)
    notices = [row for row in found if row["table"] == "strata.silver.notices"]
    assert {row["check"] for row in notices} == {"row_count", "missing_public_from", "contacts_left"}
    assert [row["found"] for row in notices if row["check"] == "contacts_left"] == [0]


def test_a_notice_still_carrying_an_email_fails_the_contacts_check(fixture_copy):
    fixture_copy.run("INSERT INTO strata.silver.notices (notice_id, notice_text, contact_details_removed, page_hash, "
                     "fetched_at, public_from) VALUES ('OP-TEST-1', 'Write to tenders@example.org by Friday.', false, "
                     "'planted', TIMESTAMP '2026-10-23 09:00:00', DATE '2026-10-23')")

    run(fixture_copy, "bronze_to_gold")

    left = [row for row in checks(fixture_copy) if row["check"] == "contacts_left"]
    assert [(row["table"], row["found"], row["passed"]) for row in left] == [("strata.silver.notices", 1, False)]


def test_a_repeated_key_fails_the_duplicates_check_with_the_rows_it_repeats(fixture_copy):
    fixture_copy.run("INSERT INTO strata.ops.lesson_review_items SELECT * FROM strata.ops.lesson_review_items "
                     "ORDER BY item_id LIMIT 1")

    run(fixture_copy, "propose_lessons")

    items = {row["check"]: row for row in checks(fixture_copy) if row["table"] == "strata.ops.lesson_review_items"}
    assert (items["duplicates"]["found"], items["duplicates"]["passed"]) == (1, False)
    assert items["row_count"]["found"] == 4


def test_a_table_outside_its_expected_range_fails_the_row_count_check(fixture_copy, monkeypatch):
    real = config.load_thresholds()
    values = {**real.values, "quality_checks": {**real.values["quality_checks"],
                                                "row_counts": {"strata.gold.assertion": [1, 100]}}}
    monkeypatch.setattr("strata.lakehouse.quality.load_thresholds", lambda: config.Thresholds(real.path, values))

    run(fixture_copy, "detect_disagreements")

    counted = {row["table"]: row for row in checks(fixture_copy) if row["check"] == "row_count"}
    assert (counted["strata.gold.assertion"]["min"], counted["strata.gold.assertion"]["max"]) == (1, 100)
    assert (counted["strata.gold.assertion"]["found"], counted["strata.gold.assertion"]["passed"]) == (784, False)
    assert counted["strata.gold.disagreement"]["passed"]


def test_a_task_that_fails_records_no_checks(fixture_copy, monkeypatch):
    def broken(run):
        raise RuntimeError("The task broke.")

    monkeypatch.setitem(nightly.TASKS, "relink", broken)

    with pytest.raises(RuntimeError):
        run(fixture_copy, "relink")

    assert checks(fixture_copy) == []
