"""Every route reads the app's clock (ticket 65).

create_app takes today, the clock a page's as-of date is read by when the page names none, and the wall clock
(registry.today) is only its default. A recorder gives create_app a fixed today, so its recorded answers must not
change when the wall clock moves past midnight UTC. Here the wall clock says October 27, 2026, the app's clock says
October 23, and each route must answer as of October 23.
"""

import asyncio
import datetime as dt
from contextlib import contextmanager

import httpx
import pytest

from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app
from strata.tools import registry

APP_TODAY, WALL_CLOCK = dt.date(2026, 10, 23), dt.date(2026, 10, 27)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
       "X-Forwarded-Access-Token": "token-for-ana-only"}
CONSULTANT = "KE-CWSB-224323-CS-QCBS"
# Each route that reads a page's as-of date, with no ?asof=, so it falls back to the clock.
ROUTES = ["/api/projects", "/api/projects/P156634", "/api/projects/P156634/packages", f"/api/packages/{CONSULTANT}",
          f"/api/packages/{CONSULTANT}/comparables", f"/api/packages/{CONSULTANT}/rebidding", "/api/data/readiness"]


@pytest.fixture
def app_on_its_own_clock(fixture_db, monkeypatch):
    monkeypatch.setattr(registry, "today", lambda: WALL_CLOCK)

    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for, today=lambda: APP_TODAY)


def get(app, path):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=ANA)
    return asyncio.run(go())


@pytest.mark.parametrize("path", ROUTES)
def test_a_route_with_no_asof_answers_as_of_the_apps_today_not_the_wall_clock(app_on_its_own_clock, path):
    response = get(app_on_its_own_clock, path)

    assert response.status_code == 200, response.text
    assert response.json()["as_of"] == "2026-10-23"


def test_a_page_asof_later_than_the_apps_today_is_read_as_of_the_apps_today(app_on_its_own_clock):
    """The as-of rule (ADR 0002): never later than today, and today is the app's clock."""
    response = get(app_on_its_own_clock, "/api/projects/P156634/packages?asof=2026-10-26")

    assert response.json()["as_of"] == "2026-10-23"


NWWDA_PLAN = "/api/projects/P156634/procurement/northern-water-works-development-agency"
# Each route that reads a page's as-of date, with an ?asof= after the app's today (ticket 12's verification round 11,
# V1): KE-KAJIADO COUNTY-567787-CW-RFB was "still open after 108 days" as of 2027-01-01, time that had not passed.
LATER = [f"/api/packages/{CONSULTANT}", f"/api/packages/{CONSULTANT}/comparables",
         f"/api/packages/{CONSULTANT}/rebidding", "/api/rebidding?category=Works&country=KE&method=Request%20for%20Bids",
         NWWDA_PLAN, f"{NWWDA_PLAN}/2025-07-21", "/api/projects", "/api/projects/P156634", "/api/data/readiness",
         "/api/comparables?category=Works&country=KE&method=Request%20for%20Bids"]


@pytest.mark.parametrize("path", LATER)
def test_an_asof_after_the_apps_today_is_read_as_of_the_apps_today(app_on_its_own_clock, path):
    """A date after today is read as today (ADR 0002; STATUS decision 15 keeps "as of today" over HTTP 422)."""
    response = get(app_on_its_own_clock, f"{path}{'&' if '?' in path else '?'}asof=2030-01-01")

    assert response.status_code == 200, response.text
    assert response.json()["as_of"] == "2026-10-23"
