"""The signals' track record through the replay harness (spec, seam 5; ticket 37, criterion 4).

The signals_track_record scorer replays project_signals as of each of the thresholds file's track record dates
(June 30 of 2023, 2024 and 2025), each through a reader frozen at that date, and counts for each status and check
how many projects had it and how many of them saw their closing date move later within 12 months. The known
answer comes from the loan history recorded in the fixture, read by hand:

- P156634 (tests/ground_truth/values.toml, closing-p156634-move-1 to move-3): its closing date first moved in
  November 2022, again in April 2024 and again in November 2025. On June 30, 2023 it had moved once, so no check
  fired (No signals), and it moved again within 12 months. On June 30, 2024 and 2025 it had moved twice, which
  the closing date check counts (Watch); after 2025 it moved within 12 months, after 2024 it did not.
- P130164 had closed in 2018, so it is not counted, and P164704's loan history is recorded with no project
  record, so the checks cannot run on it.

The Following page reads the latest stored run and states those counts; it never counts them itself.
"""

import asyncio
import datetime as dt
import shutil
from contextlib import contextmanager

import httpx

from strata.config import load_roles
from strata.estimates import harness, signals_track
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.server.following import FollowStore

RAN_AT = dt.datetime(2026, 10, 22, 6, 0, tzinfo=dt.UTC)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "601@1984",
       "X-Forwarded-Access-Token": "token-for-ana-only"}


def test_the_replay_counts_the_projects_with_each_status_and_check_and_those_that_later_extended(fixture_db):
    tracker = OfflineTracker()
    with DuckDBEngine.open(fixture_db, read_only=True) as engine, DuckDBEngine.open() as store:
        catalog.build(store)
        run_id = signals_track.backtest(engine, tracker, store=store, ran_at=RAN_AT)
        found = signals_track.stored(store)

    assert found["run_id"] == run_id and found["mlflow_run_id"] in tracker.runs
    assert found["dates"] == ["2023-06-30", "2024-06-30", "2025-06-30"] and found["window_months"] == 12
    assert found["cohort"] == 1
    assert found["status"]["needs_a_look"] == {"n": 0, "k": 0, "few": True}
    assert found["status"]["watch"] == {"n": 1, "k": 1, "few": True}
    assert found["status"]["no_signals"] == {"n": 1, "k": 1, "few": True}
    assert found["checks"]["closing_moves"] == {"n": 1, "k": 1, "few": True}
    assert found["checks"]["completion_passed"] == {"n": 0, "k": 0, "few": True}


def test_the_following_page_states_the_latest_stored_track_record_and_says_when_none_is_stored(fixture_db, tmp_path):
    database = tmp_path / "with-a-replay.duckdb"
    shutil.copy(fixture_db, database)
    state_db = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state_db) as state:
        catalog.build(state)

    def app_on(path):
        @contextmanager
        def reading(viewer):
            with DuckDBEngine.open(path, read_only=True) as engine:
                yield engine
        return create_app(engine_for=reading, follows=FollowStore(lambda: DuckDBEngine.open(state_db)),
                          access=Access(load_roles(), StaticGroups({"601@1984": ["users"]})),
                          today=lambda: dt.date(2026, 10, 22))

    def track(app):
        async def go():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
                return (await client.get("/api/following", headers=ANA)).json()["track_record"]
        return asyncio.run(go())

    assert track(app_on(fixture_db)) is None  # never replayed
    with DuckDBEngine.open(database) as engine:
        run_id = signals_track.backtest(engine, OfflineTracker(), ran_at=RAN_AT)
        expected = signals_track.stored(engine)
        assert harness.latest_run(engine, signals_track.SCORER) == run_id

    assert track(app_on(database)) == expected
