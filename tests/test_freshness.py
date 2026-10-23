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
from pathlib import Path

import httpx
import pytest

from strata.dbx import Viewer
from strata.fixture import recorded as fmt
from strata.lakehouse import catalog
from strata.lakehouse.engine import AccessDenied, DuckDBEngine, EngineError, Result
from strata.server.app import create_app

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


def fixture_engine(fixture_db):
    """The fixture database, opened read-only for each request, whoever the viewer is."""
    return lambda viewer: DuckDBEngine.open(fixture_db, read_only=True)


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
    response = get(create_app(sql_as=fixture_engine(fixture_db)), "/api/freshness", ANA)

    assert response.status_code == 200
    assert response.json() == recorded("freshness.json")
    # The independent source: each recorded page of the three daily sources says when it was
    # recorded, and the fixture loads each page as fetched on that day.
    manifest = fmt.load_manifest()
    days = {fmt.read(manifest.recorded / entry.file).recorded for entry in manifest.sources
            if entry.dataset in ("awards", "notices", "projects") and entry.kind == "json"}
    assert days == {recorded("freshness.json")["data_through"]}


def test_a_catalog_with_no_rows_loaded_gives_the_empty_stamp(empty_catalog):
    # Ticket 04's nightly job writes a run row for each task while loading nothing.
    with DuckDBEngine.open(empty_catalog) as engine:
        engine.insert_rows("strata.ops.pipeline_runs",
                           ("run_id", "task_key", "status", "rows_changed", "started_at", "finished_at", "public_from"),
                           [("run-0", "fetch_by_watermark", "succeeded", 0, at("2026-10-22"), at("2026-10-22"),
                             dt.date(2026, 10, 22))])

    response = get(create_app(sql_as=lambda viewer: DuckDBEngine.open(empty_catalog, read_only=True)),
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

    response = get(create_app(sql_as=lambda viewer: DuckDBEngine.open(empty_catalog, read_only=True)),
                   "/api/freshness", ANA)

    assert response.json() == {"data_through": "2026-10-20"}


def test_with_no_forwarded_identity_the_stamp_says_so_and_runs_no_query():
    asked = []

    response = get(create_app(sql_as=lambda viewer: asked.append(viewer)), "/api/freshness")

    assert response.status_code == 401
    assert response.json() == recorded("freshness-no-identity.json")
    assert asked == []


def test_when_the_warehouse_refuses_the_viewer_the_stamp_says_they_have_no_access():
    class Refusing:
        def run(self, sql, params=None):
            raise AccessDenied("[INSUFFICIENT_PERMISSIONS] User does not have USE CATALOG on Catalog 'strata'.")

    response = get(create_app(sql_as=lambda viewer: Refusing()), "/api/freshness", ANA)

    assert response.status_code == 403
    assert response.json() == recorded("freshness-no-access.json")


def test_a_warehouse_that_fails_gives_an_error_and_keeps_its_reason_private():
    class Failing:
        def run(self, sql, params=None):
            raise EngineError("The warehouse did not run the statement: the secret detail")

    response = get(create_app(sql_as=lambda viewer: Failing()), "/api/freshness", ANA)

    assert response.status_code == 502
    assert response.json() == {"code": "unreadable"}
    assert "secret detail" not in response.text


def test_a_warehouse_slower_than_the_stamp_s_timeout_gives_a_timeout():
    class Slow:
        def run(self, sql, params=None):
            time.sleep(0.5)
            return Result(("data_through",), ((None,),))

    response = get(create_app(sql_as=lambda viewer: Slow(), stamp_timeout_seconds=0.05), "/api/freshness", ANA)

    assert response.status_code == 504
    assert response.json() == {"code": "timeout"}


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

    app = create_app(sql_as=AsViewer)

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
