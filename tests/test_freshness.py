"""The data-freshness stamp at seam 3: GET /api/freshness, driven over HTTP.

The stamp says how current the data are: the earliest day on which a daily source was last loaded
(strata.ops.data_readiness's fresh_fetched measure), so it never claims more than the stalest daily
source. The query runs as the viewer, with the token the Databricks App forwarded, on a new
engine for each request. The responses are recorded in tests/fixtures/api, and the web app's
screen tests serve the same files.
"""

import asyncio
import datetime as dt
import json
import threading
import time
from contextlib import nullcontext
from pathlib import Path

import httpx
import pytest

from strata.dbx import Viewer, viewer_from_headers
from strata.fixture import recorded as fmt
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine, EngineError, PermissionDenied, Result, WarehouseEngine
from strata.server.app import create_app
from strata.server import engines
from strata.server.engines import duckdb_file

ROOT = Path(__file__).resolve().parents[1]
RECORDED = Path(__file__).parent / "fixtures" / "api"

ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}
BEN = {
    "X-Forwarded-Email": "ben.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ben Example",
    "X-Forwarded-User": "4022@1984",
    "X-Forwarded-Access-Token": "token-for-ben-only",
}


def recorded(name):
    return json.loads((RECORDED / name).read_text())


def get(app, path, headers=None):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=headers or {})
    return asyncio.run(go())


def each_viewer_gets(engine_class):
    """An engine made for each request's viewer from engine_class(viewer)."""
    return lambda viewer: nullcontext(engine_class(viewer))


@pytest.fixture
def empty_catalog(tmp_path):
    """A catalog with every table and no rows, as a first deploy leaves it."""
    path = tmp_path / "strata.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


def measured(path, rows):
    """Data readiness rows: (source, subject, measure, as_of, cadence, measured_at)."""
    with DuckDBEngine.open(path) as engine:
        engine.insert_rows("strata.ops.data_readiness",
                           ("run_id", "source", "subject", "measure", "kind", "as_of", "detail", "measured_at",
                            "public_from"),
                           [("run-1", source, subject, measure, "fresh", as_of, cadence, at, at.date())
                            for source, subject, measure, as_of, cadence, at in rows])


def at(day):
    return dt.datetime.combine(dt.date.fromisoformat(day), dt.time(5), dt.UTC)


def test_the_stamp_gives_the_day_the_fixture_s_daily_sources_were_last_loaded(fixture_db):
    response = get(create_app(engine_for=duckdb_file(fixture_db)), "/api/freshness", ANA)

    assert response.status_code == 200
    assert response.json() == recorded("freshness.json")
    # The independent source: each recorded page of the three daily sources says when it was
    # recorded, and the fixture loads each page as fetched on that day. A source was last loaded on
    # its newest page's day, and the stamp is the stalest source's: one project record was recorded
    # a day after the rest, for ticket 18's stress shelf, and the stamp does not move with it.
    manifest = fmt.load_manifest()
    last_loaded = {}
    for entry in manifest.sources:
        if entry.dataset in ("awards", "notices", "projects") and entry.kind == "json":
            day = fmt.read(manifest.recorded / entry.file).recorded
            last_loaded[entry.dataset] = max(day, last_loaded.get(entry.dataset, day))
    assert min(last_loaded.values()) == recorded("freshness.json")["data_through"] == "2026-10-23"


def test_a_catalog_with_no_rows_loaded_gives_the_empty_stamp(empty_catalog):
    # Ticket 04's nightly job writes a run row for each task while loading nothing.
    with DuckDBEngine.open(empty_catalog) as engine:
        engine.insert_rows("strata.ops.pipeline_runs",
                           ("run_id", "task_key", "status", "rows_changed", "started_at", "finished_at", "public_from"),
                           [("run-0", "fetch_by_watermark", "succeeded", 0, at("2026-10-22"), at("2026-10-22"),
                             dt.date(2026, 10, 22))])

    response = get(create_app(engine_for=duckdb_file(empty_catalog)),
                   "/api/freshness", ANA)

    assert response.status_code == 200
    assert response.json() == recorded("freshness-empty.json")


def test_the_stamp_gives_the_stalest_daily_source_from_each_source_s_newest_measurement(empty_catalog):
    measured(empty_catalog, [
        ("awards", "KE", "fresh_fetched", dt.date(2026, 10, 21), "daily", at("2026-10-21")),
        ("notices", "KE", "fresh_fetched", dt.date(2026, 10, 20), "daily", at("2026-10-20")),
        ("notices", "KE", "fresh_fetched", dt.date(2026, 10, 19), "daily", at("2026-10-19")),
        ("projects", "KE", "fresh_fetched", dt.date(2026, 10, 21), "daily", at("2026-10-21")),
        # Not daily, and not the day a source was loaded: neither moves the stamp.
        ("ratings", "KE", "fresh_fetched", dt.date(2026, 6, 30), "yearly", at("2026-10-21")),
        ("awards", "KE", "fresh_newest_record", dt.date(2026, 10, 2), "daily", at("2026-10-21")),
    ])

    response = get(create_app(engine_for=duckdb_file(empty_catalog)),
                   "/api/freshness", ANA)

    assert response.json() == {"data_through": "2026-10-20"}


def test_with_no_forwarded_identity_the_stamp_says_so_and_runs_no_query():
    asked = []

    response = get(create_app(engine_for=lambda viewer: asked.append(viewer)), "/api/freshness")

    assert response.status_code == 401
    assert response.json() == recorded("freshness-no-identity.json")
    assert asked == []


def test_when_the_warehouse_refuses_the_viewer_the_stamp_says_they_have_no_access():
    class Refusing:
        def run(self, sql, params=None):
            raise PermissionDenied("[INSUFFICIENT_PERMISSIONS] User does not have USE CATALOG on Catalog 'strata'.")

    response = get(create_app(engine_for=each_viewer_gets(lambda viewer: Refusing())), "/api/freshness", ANA)

    assert response.status_code == 403
    assert response.json() == recorded("freshness-no-access.json")


def test_a_warehouse_that_fails_gives_an_error_and_keeps_its_reason_private():
    class Failing:
        def run(self, sql, params=None):
            raise EngineError("The warehouse did not run the statement: the secret detail")

    response = get(create_app(engine_for=each_viewer_gets(lambda viewer: Failing())), "/api/freshness", ANA)

    assert response.status_code == 502
    assert response.json() == {"code": "unreadable"}
    assert "secret detail" not in response.text


def test_a_warehouse_slower_than_the_stamp_s_timeout_gives_a_timeout():
    class Slow:
        def run(self, sql, params=None):
            time.sleep(0.2)
            return Result(("data_through",), ((None,),))

    response = get(create_app(engine_for=each_viewer_gets(lambda viewer: Slow()), stamp_timeout_seconds=0.02), "/api/freshness", ANA)

    assert response.status_code == 504
    assert response.json() == {"code": "timeout"}


def test_a_stamp_read_that_gives_up_also_stops_the_warehouse_wait_behind_it():
    # The 504 above leaves the read running in its thread, so the engine must give up too, or slow
    # reads would fill the server's threads. The warehouse is asked to hold the first answer no
    # longer than the timeout (its floor is 5 seconds), and polling stops at the timeout.
    calls = []

    def still_running(method, path, body):
        calls.append((method, body["wait_timeout"] if body else None))
        return {"statement_id": "s-1", "status": {"state": "PENDING"}}

    engine_for = engines.warehouse_as_viewer("strata.test", "wh-1", transport=lambda host, token: still_running,
                                             timeout_seconds=0)
    with pytest.raises(EngineError, match="longer than 5 seconds"), engine_for(viewer_from_headers(ANA)) as engine:
        engine.run("SELECT 1")

    assert calls == [("POST", "5s")]


def test_a_warehouse_that_held_the_first_call_for_the_whole_timeout_is_not_polled_for_as_long_again():
    # A reply that is still running means the warehouse held the call for its whole wait_timeout,
    # so that time counts, and a 30 second read gives up at 30 seconds, not 60.
    slept = []

    def still_running(method, path, body):
        return {"statement_id": "s-1", "status": {"state": "PENDING"}}

    with pytest.raises(EngineError, match="longer than 30 seconds"):
        WarehouseEngine("wh-1", still_running, timeout_seconds=30, sleep=slept.append).run("SELECT 1")

    assert slept == []


def test_the_environment_s_warehouse_gives_up_at_the_stamp_s_timeout():
    engine_for = engines.from_environment({"DATABRICKS_HOST": "strata.test", "DATABRICKS_WAREHOUSE_ID": "wh-1"},
                                          timeout_seconds=12)

    with engine_for(viewer_from_headers(ANA)) as engine:
        assert engine.timeout_seconds == 12


def test_overlapping_requests_from_two_viewers_each_run_their_query_with_their_own_token():
    running, peak, lock = [0], [0], threading.Lock()

    class AsViewer:
        """A warehouse that answers who ran the query, after a pause, so the requests overlap."""

        def __init__(self, viewer: Viewer):
            self.viewer = viewer

        def run(self, sql, params=None):
            with lock:
                running[0] += 1
                peak[0] = max(peak[0], running[0])
            time.sleep(0.05)
            with lock:
                running[0] -= 1
            owner = {"token-for-ana-only": "ana.example@worldbank.org",
                     "token-for-ben-only": "ben.example@worldbank.org"}[self.viewer.token]
            if "current_user" in sql:
                return Result(("warehouse_user",), ((owner,),))
            return Result(("data_through",), ((dt.date(2026, 10, 21),),))

    app = create_app(engine_for=each_viewer_gets(AsViewer))

    async def both():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await asyncio.gather(*[client.get(path, headers=headers) for path in ("/api/me/warehouse",
                                                                                       "/api/freshness")
                                          for headers in (ANA, BEN)])

    ana_user, ben_user, ana_stamp, ben_stamp = asyncio.run(both())

    assert ana_user.json() == {"warehouse_user": "ana.example@worldbank.org"}
    assert ben_user.json() == {"warehouse_user": "ben.example@worldbank.org"}
    assert ana_stamp.json() == ben_stamp.json() == {"data_through": "2026-10-21"}
    assert peak[0] > 1, "the requests did not overlap"
