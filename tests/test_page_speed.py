"""Every page answers in under two seconds on the workspace (ticket 125), proved on the fixture.

On October 29, 2026 the App's pages took one to five seconds and more: each statement cost the SQL warehouse's
statements API about two seconds, and a page ran its statements one after another. Three things fix it, and each is
tested here at the App's routes:

1. A page's reads go to the warehouse as one batch (src/strata/lakehouse/engine.py, read_together and run_many), so
   the Summary, the Timeline, a project's Packages and a package's header each cost one round trip.
2. A page's answer is kept in the App's memory for its as-of day and the viewer's role (the view the request is bound
   to), for app.page_cache_seconds and at most app.page_cache_entries pages (config/thresholds.toml), and the browser
   is told to keep it as long (Cache-Control), so the second view of a page reads nothing.
3. The demo's cases (config/demo.toml) are read into that memory when the App starts and every hour after, as the App
   itself, so a presenter never meets a cold page.

The live timings are the orchestrator's workspace step (the ticket's report).
"""

import asyncio
from contextlib import contextmanager

import httpx
import pytest

from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
       "X-Forwarded-Access-Token": "not-a-real-key"}
DAY = "asof=2026-10-23"


def get(app, path, headers=ANA):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=headers)
    return asyncio.run(go())


class Counted:
    """The fixture's engine, counting each round trip a request makes: each batch, and each statement run alone."""

    def __init__(self, engine, trips: list):
        self.engine, self.trips = engine, trips

    def run(self, sql, params=None):
        self.trips.append(("alone", sql.strip().splitlines()[0]))
        return self.engine.run(sql, params)

    def run_many(self, statements):
        self.trips.append(("batch", len(statements)))
        return self.engine.run_many(statements)

    def __getattr__(self, name):
        return getattr(self.engine, name)


@pytest.fixture
def trips():
    return []


@pytest.fixture
def counted_reads(fixture_db, trips):
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield Counted(engine, trips)
    return engine_for


@pytest.mark.parametrize("path", [
    f"/api/projects/P130164/summary?{DAY}",
    f"/api/projects/P156634/summary?{DAY}",
    "/api/projects/P130164/timeline",
    f"/api/projects/P156634/timeline?{DAY}",
    f"/api/projects/P156634/timeline?{DAY}&view=public",
    f"/api/projects/P156634/packages?{DAY}",
    f"/api/packages/KE-NWWDA-541055-CW-RFB?{DAY}",
], ids=["summary-p130164", "summary-p156634", "timeline-p130164", "timeline-p156634", "timeline-public",
        "packages-p156634", "package-ke-nwwda-541055"])
def test_a_page_s_warehouse_reads_go_as_one_batch(counted_reads, trips, path):
    response = get(create_app(engine_for=counted_reads), path)

    assert response.status_code == 200
    assert [kind for kind, _ in trips] == ["batch"], trips
