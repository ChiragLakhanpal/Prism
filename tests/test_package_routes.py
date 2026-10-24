"""The package workspace's HTTP routes: the package's facts, and find_comparables for its section 1.

GET /api/packages/{step_reference} gives the package as its newest public plan row states it, and GET
/api/packages/{step_reference}/comparables runs find_comparables through the tool registry, both as the
viewer. Their answers on the fixture, as of October 22, 2026, are recorded once in tests/fixtures/api,
and the screen tests serve the same files from their mocked API, so the screen and the server can
never drift apart.
"""

import asyncio
import json
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

RECORDED = Path(__file__).parent / "fixtures" / "api"
ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}
ROUTES = [
    ("/api/packages/KE-NWWDA-541055-CW-RFB", "package-ke-nwwda-541055.json"),
    ("/api/packages/KE-NWWDA-541055-CW-RFB/comparables", "comparables-ke-nwwda-541055.json"),
    # The fixture's narrower criteria: fewer than 20 comparables, so no range.
    ("/api/packages/KE-NWWDA-541055-CW-RFB/comparables?review_type=Prior", "comparables-ke-nwwda-541055-prior.json"),
    # More than 60 comparables, so 20 quantile dots.
    ("/api/packages/KE-NWWDA-541055-CW-RFB/comparables?category=any", "comparables-ke-nwwda-541055-any-category.json"),
    # No comparable package matched, and packages matched that could not be measured.
    ("/api/packages/KE-NWWDA-541055-CW-RFB/comparables?country=IN", "comparables-ke-nwwda-541055-india.json"),
    ("/api/packages/KE-NWWDA-541055-CW-RFB/comparables?category=Non-consulting%20Services",
     "comparables-ke-nwwda-541055-non-consulting.json"),
    # A Request for Quotations with a Limited market approach: no public notice to measure from.
    ("/api/packages/KE-NWWDA-541062-CW-RFQ", "package-ke-nwwda-541062.json"),
    ("/api/packages/KE-NWWDA-541062-CW-RFQ/comparables", "comparables-ke-nwwda-541062.json"),
]


def get(app, path, headers=None):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=headers or {})
    return asyncio.run(go())


def with_as_of(path: str) -> str:
    return f"{path}{'&' if '?' in path else '?'}asof=2026-10-22"


@pytest.fixture
def viewers_seen():
    return []


@pytest.fixture
def fixture_app(fixture_db, viewers_seen):
    @contextmanager
    def engine_for(viewer):
        viewers_seen.append(viewer)
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for)


@pytest.mark.parametrize("path, name", ROUTES, ids=[name for _, name in ROUTES])
def test_each_recorded_answer_is_what_the_route_gives_the_viewer_on_the_fixture(fixture_app, viewers_seen, path, name):
    response = get(fixture_app, with_as_of(path), ANA)

    assert response.status_code == 200
    assert response.json() == json.loads((RECORDED / name).read_text())
    assert [viewer.token for viewer in viewers_seen] == ["token-for-ana-only"]
    assert "token-for-ana-only" not in response.text


def test_the_comparables_route_runs_find_comparables_through_the_registry_with_the_page_s_as_of_date(fixture_app):
    body = get(fixture_app, "/api/packages/KE-NWWDA-541055-CW-RFB/comparables?asof=2026-10-22&view=staff", ANA).json()

    assert (body["tool"], body["as_of"], body["view"]) == ("find_comparables", "2026-10-22", "staff")
    assert len(body["rows"]) == 49


def test_a_reference_no_plan_lists_is_not_found(fixture_app):
    response = get(fixture_app, "/api/packages/KE-NWWDA-000000-CW-RFB?asof=2026-10-22", ANA)

    assert (response.status_code, response.json()) == (404, {"code": "unknown_package"})


def test_a_criterion_the_tool_does_not_take_is_a_bad_request(fixture_app):
    response = get(fixture_app, "/api/packages/KE-NWWDA-541055-CW-RFB/comparables?size_from_usd=lots", ANA)

    assert response.status_code == 422
