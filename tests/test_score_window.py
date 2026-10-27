"""The score task fits the nightly window (ticket 89; seams 1 and 5).

On the paid workspace, the nightly job's score task ran alone for the job's whole 150-minute window on October 27,
2026 (run 1086916576670871), so measure_data_readiness and refresh_drafts never ran. The task does its work in
parts, in nightly.SCORE_PARTS' order. Once the night's minutes for scoring are spent (config/thresholds.toml,
nightly.score_minutes), it stops after the part it is in, records the parts it left in strata.ops.score_parts, and
ends, so the tasks after it run; the next night runs the parts left first. The two replays of the signals run once a
week (tests/test_nightly.py), and read each date's projects in batches instead of two statements for each project.

The clocks here are fake: each test says when its night starts and how long its first part takes.
"""

import datetime as dt
import logging

import pytest

from strata import config
from strata.estimates import hazard
from strata.lakehouse import catalog, nightly
from strata.lakehouse.engine import DuckDBEngine

OFFLINE_PARTS = ["time_estimates", "rebidding_labels", "challenger_in_shadow", "monthly_watch", "hazard_in_shadow",
                 "hazard_replay"]


@pytest.fixture
def engine():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


def no_pages(source, engine):
    return ()


def at(day: dt.date) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(7), tzinfo=dt.UTC)  # 03:00 in Washington


def first_part_takes(minutes: float, start: dt.datetime):
    """A night's clock: the task starts at start, and every later reading is minutes on, so the first part of the
    score task ends minutes after the task started."""
    readings = iter(range(10**6))
    return lambda: start if next(readings) == 0 else start + dt.timedelta(minutes=minutes)


def task(engine, key, run_id, clock):
    nightly.main(["--task", key, "--run-id", run_id, "--src", "src"], engine, no_pages, clock)


def parts(engine, run_id):
    return list(engine.run("SELECT part, state FROM strata.ops.score_parts WHERE run_id = :run_id ORDER BY position",
                           {"run_id": run_id}).rows)


def status(engine, run_id, key):
    return list(engine.run("SELECT status FROM strata.ops.pipeline_runs WHERE run_id = :run_id AND task_key = :key",
                           {"run_id": run_id, "key": key}).rows)


def test_the_score_task_stops_after_the_part_that_spends_its_minutes_and_the_next_night_runs_what_it_left(
        engine, caplog):
    minutes = config.load_thresholds().value("nightly.score_minutes")
    saturday, sunday, monday = dt.date(2026, 10, 31), dt.date(2026, 11, 1), dt.date(2026, 11, 2)
    task(engine, "score", "saturday", lambda: at(saturday))  # a whole night: the hazard model's comparison is stored
    assert parts(engine, "saturday") == [(part, "ran") for part in OFFLINE_PARTS]
    compared = hazard.stored(engine)["run_id"]

    # Sunday, the replays' night of the week: the time estimates take the night's minutes and one more.
    sunday_clock = first_part_takes(minutes + 1, at(sunday))
    with caplog.at_level(logging.WARNING, logger="strata.lakehouse.nightly"):
        task(engine, "score", "sunday", sunday_clock)
    for later in ("measure_data_readiness", "refresh_drafts"):
        task(engine, later, "sunday", sunday_clock)

    assert minutes == 45
    assert parts(engine, "sunday") == [("time_estimates", "ran")] + [(part, "left") for part in OFFLINE_PARTS[1:]]
    assert [status(engine, "sunday", key) for key in ("score", "measure_data_readiness", "refresh_drafts")] == \
        [[("succeeded",)]] * 3
    assert hazard.stored(engine)["run_id"] == compared  # left for Monday
    assert "5 parts left for the next night: rebidding_labels, challenger_in_shadow, monthly_watch, " \
        "hazard_in_shadow, hazard_replay" in caplog.text

    # Monday runs the five parts Sunday left first, the comparison among them though Monday is not its night.
    task(engine, "score", "monday", lambda: at(monday))
    assert parts(engine, "monday") == [(part, "ran") for part in OFFLINE_PARTS[1:] + OFFLINE_PARTS[:1]]
    assert hazard.stored(engine)["run_id"] != compared
