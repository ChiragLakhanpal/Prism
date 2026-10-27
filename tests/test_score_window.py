"""The score task fits the nightly window (ticket 89; seams 1 and 5).

On the paid workspace, the nightly job's score task ran alone for the job's whole 150-minute window on October 27,
2026 (run 1086916576670871), so measure_data_readiness and refresh_drafts never ran. The task does its work in
parts, in nightly.SCORE_PARTS' order. Once the night's minutes for scoring are spent (config/thresholds.toml,
nightly.score_minutes), it stops after the part it is in, records the parts it left in strata.ops.score_parts, and
ends, so the tasks after it run; the next night runs the parts left first. The two replays of the signals run once a
week (tests/test_nightly.py), read each date's projects in batches instead of two statements for each project, and
on their night check each active project once a date for both.

The clocks here are fake: each test says when its night starts and how long its first part takes.
"""

import datetime as dt
import logging
import shutil
from importlib import resources

import pytest

from strata import config
from strata.estimates import harness, hazard, signals_track
from strata.estimates.past_range import as_date
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse import catalog, nightly
from strata.lakehouse.engine import DuckDBEngine

RAN_AT = dt.datetime(2026, 10, 22, 6, 0, tzinfo=dt.UTC)

OFFLINE_PARTS = ["time_estimates", "rebidding_labels", "challenger_in_shadow", "monthly_watch", "hazard_in_shadow",
                 "signals_replays"]


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
        "hazard_in_shadow, signals_replays" in caplog.text

    # Monday runs the five parts Sunday left first, the comparison among them though Monday is not its night.
    task(engine, "score", "monday", lambda: at(monday))
    assert parts(engine, "monday") == [(part, "ran") for part in OFFLINE_PARTS[1:] + OFFLINE_PARTS[:1]]
    assert hazard.stored(engine)["run_id"] != compared


# ── The replays' reads in batches (seam 5) ───────────────────────────────
#
# The oracle: how the two replays read before ticket 89, kept here only as the answer the batched reads must give.
# Each date, every project of the cohort was checked with project_signals, which for a closed project, or one with no
# project record, reads its loan history and its record (two statements) and stops; and each counted project's later
# closing-date moves were read on their own.

ONE_PROJECT_S_MOVES = """
SELECT reported_on, closing_date, previous_closing_date, public_from
FROM strata.gold.project_closing_date
WHERE project_id = :project_id
  AND public_from <= :as_of
  AND previous_closing_date IS NOT NULL
  AND closing_date > previous_closing_date
ORDER BY reported_on
"""


def counted_one_by_one(frozen, checked=None):
    found = []
    for project in frozen.rows(signals_track.COHORT):
        result = frozen.call("project_signals", project_id=project["project_id"])
        if result["status"] in signals_track.STATUSES:
            found.append((project["project_id"], result))
    return found


class MovesOneByOne(dict):
    """Each project's later closing-date moves, read on their own each time a replay asks."""

    def __init__(self, outcomes):
        super().__init__()
        self.outcomes = outcomes

    def __missing__(self, project_id):
        return [as_date(row["reported_on"]) for row in self.outcomes.rows(ONE_PROJECT_S_MOVES, project_id=project_id)]


def one_at_a_time(monkeypatch):
    monkeypatch.setattr(signals_track, "counted", counted_one_by_one)
    monkeypatch.setattr(signals_track, "later_moves", MovesOneByOne)


def with_batches_of(projects: int):
    held = config.load_thresholds()
    return config.Thresholds(held.path, {**held.values,
                                         "signals": {**held.values["signals"], "track_record_batch_projects": projects}})


def replayed(engine, store, thresholds, checked=None) -> list[tuple]:
    """The rows both replays store for one run each, without the ids each run makes up for itself; with checked, the
    two share what project_signals found on each date, as on their night."""
    run_ids = (signals_track.backtest(engine, OfflineTracker(), store=store, thresholds=thresholds, ran_at=RAN_AT,
                                      checked=checked),
               hazard.compare(engine, OfflineTracker(), ran_at=RAN_AT, store=store, thresholds=thresholds,
                              checked=checked))
    return [tuple(value for key, value in row.items() if key not in ("run_id", "mlflow_run_id"))
            for run_id in run_ids for row in harness.run_rows(store, run_id)]


@pytest.mark.parametrize("projects", [1, 2, None])
def test_the_replays_read_in_batches_store_the_same_rows_as_one_project_at_a_time(fixture_db, monkeypatch, projects):
    """On the fixture, with batches of one project, of two, and of the thresholds file's size."""
    thresholds = config.load_thresholds() if projects is None else with_batches_of(projects)
    with DuckDBEngine.open(fixture_db, read_only=True) as engine, DuckDBEngine.open() as store:
        catalog.build(store)
        batched = replayed(engine, store, thresholds)
        shared = replayed(engine, store, thresholds, checked={})
        one_at_a_time(monkeypatch)
        before = replayed(engine, store, thresholds)

    assert batched == shared == before
    assert {row[0] for row in batched} == {signals_track.SCORER, hazard.SCORER}
    assert ("replay", "signals", "status.watch.n", 1.0) in [row[2:6] for row in batched]


class Watched:
    """The fixture's engine, which keeps each statement it is sent and the project the statement names, if any."""

    def __init__(self, engine):
        self.engine, self.projects, self.statements = engine, [], []

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def run(self, sql, params=None):
        self.projects.append((params or {}).get("project_id"))
        self.statements.append(sql)
        return self.engine.run(sql, params)


def test_a_project_the_replay_does_not_count_costs_it_no_statement_of_its_own(fixture_db, monkeypatch):
    """P130164 had closed by every replay date, and P164704 has a loan history but no project record, so the track
    record counts neither. One project at a time, each cost two statements on each date; in batches, none."""
    uncounted = {"P130164", "P164704"}
    with DuckDBEngine.open(fixture_db, read_only=True) as engine, DuckDBEngine.open() as store:
        catalog.build(store)
        batched = Watched(engine)
        signals_track.backtest(batched, OfflineTracker(), store=store, ran_at=RAN_AT)
        one_at_a_time(monkeypatch)
        before = Watched(engine)
        signals_track.backtest(before, OfflineTracker(), store=store, ran_at=RAN_AT)

    assert sorted(project for project in before.projects if project in uncounted) == \
        ["P130164"] * 6 + ["P164704"] * 6
    assert "P156634" in batched.projects and not uncounted & set(batched.projects)
    assert len(batched.projects) < len(before.projects)


def test_on_their_night_the_two_replays_check_each_project_once_a_date_for_both(fixture_db, tmp_path, monkeypatch):
    """Sunday, October 25, 2026, after the fixture's own run on Friday the 23rd: a live score task replays the signals
    for their track record and compares the hazard model with them. Both replay June 30 of 2023, 2024 and 2025, so
    P156634, the one project the record counts, is checked with project_signals once on each date, not twice."""
    from strata.estimates import tracking

    monkeypatch.setattr(tracking, "MlflowTracker", lambda experiment, mkdirs=None: OfflineTracker())
    path = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, path)
    checks = (resources.files("strata.tools") / "sql" / "project_signals" / "history.sql").read_text()
    with DuckDBEngine.open(path) as engine:
        watched = Watched(engine)
        nightly.main(["--task", "score", "--run-id", "sunday", "--src", "src"], watched,
                     clock=lambda: at(dt.date(2026, 10, 25)))  # as the job runs it: a live run
        ran_on = (signals_track.stored(engine)["ran_on"], f"{hazard.stored(engine)['ran_at']:%Y-%m-%d}")

    assert ran_on == ("2026-10-25", "2026-10-25")
    assert [project for project, sql in zip(watched.projects, watched.statements) if sql == checks] == ["P156634"] * 3
