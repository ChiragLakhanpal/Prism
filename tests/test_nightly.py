"""The nightly job (seam 1): the bundle's tasks run in docs/PLAN.md section 11's order, and each
one records its run in strata.ops.pipeline_runs.

The local run reads the job from the bundle and calls the same entry point the job calls on
Databricks, with the same parameters, against DuckDB. The workspace step
`ops/bundle/check.py job-run` checks the same rows after a manual run on the workspace.
"""

import datetime as dt
from pathlib import Path

import pytest

from strata.lakehouse import bundle, catalog, nightly, schedule
from strata.lakehouse.engine import DuckDBEngine

# docs/PLAN.md section 11, "Nightly job", in its order: fetch by watermark, bronze to gold, parse and
# embed only what changed, sync the index, re-link, propose lessons, detect disagreements, score,
# measure data readiness, and refresh drafts that cite changed lessons.
PLAN_ORDER = [
    "fetch_by_watermark",
    "bronze_to_gold",
    "parse_and_embed",
    "sync_index",
    "relink",
    "propose_lessons",
    "detect_disagreements",
    "score",
    "measure_data_readiness",
    "refresh_drafts",
]

WASHINGTON = "America/New_York"


@pytest.fixture
def engine():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


def runs(engine, run_id):
    return engine.run("SELECT task_key, status, rows_changed, started_at, finished_at, public_from "
                      "FROM strata.ops.pipeline_runs WHERE run_id = :run_id ORDER BY started_at",
                      {"run_id": run_id}).rows


def test_the_job_runs_its_tasks_one_after_another_in_plan_order():
    tasks = nightly.job_tasks()

    assert [task.key for task in tasks] == PLAN_ORDER
    assert [task.depends_on for task in tasks] == [()] + [(key,) for key in PLAN_ORDER[:-1]]
    assert set(nightly.TASKS) == set(PLAN_ORDER)


def test_a_run_of_the_job_writes_one_pipeline_run_row_per_task_in_plan_order(engine):
    run_id = nightly.run_locally(engine)

    rows = runs(engine, run_id)
    assert [row[0] for row in rows] == PLAN_ORDER
    assert {(status, changed) for _, status, changed, *_ in rows} == {("succeeded", 0)}
    for _, _, _, started, finished, public_from in rows:
        assert started <= finished
        assert public_from == finished.astimezone(dt.UTC).date()


def test_two_runs_keep_their_rows_apart(engine):
    first, second = nightly.run_locally(engine), nightly.run_locally(engine)

    assert first != second
    assert len(runs(engine, first)) == len(runs(engine, second)) == len(PLAN_ORDER)


def test_a_task_the_job_does_not_have_is_refused(engine):
    with pytest.raises(SystemExit, match="no task called polish_gold"):
        nightly.main(["--task", "polish_gold", "--run-id", "42", "--src", "/tmp/src"], engine)

    assert engine.run("SELECT count(*) AS n FROM strata.ops.pipeline_runs").as_text() == [("0",)]


def test_the_bundle_syncs_the_config_files_beside_the_package():
    # strata.config.CONFIG_DIR finds config/ beside src/, so the tasks read the source registry there.
    assert {"src", "config"} <= set(bundle.load().data["sync"]["paths"])


def test_the_jobs_entry_script_does_without_a_file_location():
    """Serverless Python tasks have no __file__ (docs/PLAN.md section 12), so the job passes --src."""
    script = Path(nightly.__file__).with_name("nightly_task.py").read_text()

    assert "__file__" not in script.replace('"__file__"', "")
    assert all("--src" in task.parameters for task in nightly.job_tasks())


# ── The window ───────────────────────────────────────────────────────────

def days_of_a_year():
    start = dt.date(2026, 10, 23)
    return [start + dt.timedelta(days=n) for n in range(366)]


def test_the_window_starts_at_five_in_the_morning_in_washington_and_lasts_two_and_a_half_hours():
    window = nightly.window()

    assert (window.start, window.timezone, window.minutes) == (dt.time(5, 0), WASHINGTON, 150)


@pytest.mark.parametrize("hour", [18, 19, 20, 21, 22, 23, 0])
def test_the_window_misses_a_four_hour_job_that_starts_any_evening_hour_in_washington(hour):
    """Midnight included: on the night the clocks go forward, four hours from midnight end at 05:00."""
    other = schedule.Window("an evening job", dt.time(hour, 0), WASHINGTON, 240)

    assert schedule.overlapping_days(nightly.window(), other, days_of_a_year()) == []


def test_the_window_misses_a_four_hour_job_that_starts_at_midnight_utc():
    other = schedule.Window("a midnight UTC job", dt.time(0, 0), "UTC", 240)

    assert schedule.overlapping_days(nightly.window(), other, days_of_a_year()) == []


def test_the_window_ends_before_review_hours_in_washington():
    review_hours = schedule.Window("review hours", dt.time(8, 0), WASHINGTON, 600)

    assert schedule.overlapping_days(nightly.window(), review_hours, days_of_a_year()) == []


def test_a_job_that_runs_into_the_window_is_caught():
    other = schedule.Window("an eight-hour evening job", dt.time(23, 0), WASHINGTON, 480)

    assert len(schedule.overlapping_days(nightly.window(), other, days_of_a_year())) == 366


def test_midnight_utc_moves_against_washington_time_and_the_check_follows_it():
    """Midnight UTC is 20:00 in Washington in summer and 19:00 in winter; check both sides of the change.

    A nine-and-a-half-hour job from midnight UTC ends at 05:30 in summer, inside the window, and
    at 04:30 in winter, before it.
    """
    days = [dt.date(2026, 10, 30), dt.date(2026, 11, 2)]
    seven = schedule.Window("a seven-hour job at midnight UTC", dt.time(0, 0), "UTC", 7 * 60)
    longer = schedule.Window("a nine-and-a-half-hour job at midnight UTC", dt.time(0, 0), "UTC", 570)

    assert schedule.overlapping_days(nightly.window(), seven, days) == []
    assert schedule.overlapping_days(nightly.window(), longer, days) == [dt.date(2026, 10, 30)]
