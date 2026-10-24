"""The project routes at seam 3: the All projects list and one project's page, which the Projects tab,
the project page and its Procurement tab ask for, as the viewer.

GET /api/projects lists every project Strata holds records for, active ones first and then by name.
GET /api/projects/{project_id} gives the project page's header (name, country, status and implementing
agencies, from the projects API's record) and the Procurement tab: each implementing agency's
Procurement Plan versions, newest first, with how many activities each read version lists. Each route
answers with only what was public on or before the page's ?asof= date (ADR 0002), and the screen
counts and sorts nothing itself.

Their responses are recorded once in tests/fixtures/api, where the screen tests serve them from their
mocked API. The values below are copied from the recorded sources in data/fixture/recorded: the
projects API's record for P156634 and P130164, and the documents API's list of P156634's
Procurement Plans.
"""

import asyncio
import json
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.lakehouse.engine import DuckDBEngine
from strata.server import engines
from strata.server.app import create_app

RECORDED = Path(__file__).parent / "fixtures" / "api"
NWWDA = "Northern Water Works Development Agency"
ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}
NO_USE_CATALOG = {
    "statement_id": "statement-not-a-real-one",
    "status": {"state": "FAILED", "error": {
        "error_code": "BAD_REQUEST",
        "message": "[INSUFFICIENT_PERMISSIONS] Insufficient privileges:\n"
                   "User does not have USE CATALOG on Catalog 'strata'. SQLSTATE: 42501"}},
}


def get(app, path, headers=ANA):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=headers)
    return asyncio.run(go())


@pytest.fixture
def fixture_app(fixture_db):
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for)


def recorded(name):
    return json.loads((RECORDED / name).read_text())


def test_all_projects_lists_active_projects_first_then_by_name(fixture_app):
    response = get(fixture_app, "/api/projects?asof=2026-10-23")

    assert response.status_code == 200
    body = response.json()
    assert body == recorded("projects.json")
    # Every page, in order: ticket 21 shows them 20 at a time.
    rows = [row for page in range(1, body["pages"] + 1)
            for row in get(fixture_app, f"/api/projects?asof=2026-10-23&page={page}").json()["rows"]]
    assert body["total"] == len(rows)
    assert {"project_id": "P156634", "project_name": "Water and Sanitation Development Project", "country": "Kenya",
            "status": "Active"} in rows
    assert {"project_id": "P130164", "project_name": "Rajasthan Road Sector Modernization Project", "country": "India",
            "status": "Closed"} in rows
    active = [row["status"] == "Active" for row in rows]
    assert active == sorted(active, reverse=True)
    names = [row["project_name"] for row in rows if row["status"] == "Active"]
    assert names == sorted(names)
    assert body["records_through"] == "2026-10-23"


def test_a_project_page_gives_its_header_and_each_agency_s_plan_versions_newest_first(fixture_app):
    response = get(fixture_app, "/api/projects/P156634?asof=2026-10-22")

    assert response.status_code == 200
    body = response.json()
    assert body == recorded("project-p156634.json")
    project = body["project"]
    assert (project["project_id"], project["project_name"], project["country"], project["status"]) == (
        "P156634", "Water and Sanitation Development Project", "Kenya", "Active")
    # The projects API joins the agencies with a bare comma; a comma and a space sits inside a name.
    assert NWWDA in project["implementing_agencies"]
    assert "Ministry of Water, Sanitation and Irrigation" in project["implementing_agencies"]
    assert len(project["implementing_agencies"]) == 12

    first = body["agencies"][0]
    assert (first["implementing_agency"], first["agency_id"]) == (NWWDA, "northern-water-works-development-agency")
    assert [version["plan_date"] for version in first["versions"]] == [
        "2026-10-09", "2026-03-05", "2025-07-21", "2021-04-21", "2020-12-07"]
    latest = first["versions"][0]
    assert (latest["is_latest"], latest["read"], latest["activities"], latest["disclosed_on"]) == (
        True, True, 9, "2026-10-09")
    assert not any(version["is_latest"] for version in first["versions"][1:])
    # The route counts each agency's versions, so the screen's "Showing all 5 versions" counts nothing.
    counts = {agency["agency_id"]: agency["version_count"] for agency in body["agencies"]}
    assert counts["northern-water-works-development-agency"] == 5
    assert counts["kilifi-mariakani-water-and-sewerage-company-ltd"] == 1
    # An agency the project record names that has published no plan is listed with no versions.
    assert {"implementing_agency": "Water Sector Trust Fund", "agency_id": "water-sector-trust-fund",
            "versions": [], "baseline": None, "changes": None, "version_count": 0, "shown_count": 0} in body["agencies"]
    assert body["documents_through"] == "2026-10-22"


def test_a_version_disclosed_after_the_as_of_date_is_left_out(fixture_app):
    body = get(fixture_app, "/api/projects/P156634?asof=2026-06-01").json()

    nwwda = next(agency for agency in body["agencies"] if agency["agency_id"] == "northern-water-works-development-agency")
    assert [version["plan_date"] for version in nwwda["versions"]] == ["2026-03-05", "2025-07-21", "2021-04-21", "2020-12-07"]
    assert nwwda["versions"][0]["is_latest"] is True


def test_a_project_with_no_record_is_not_found(fixture_app):
    response = get(fixture_app, "/api/projects/P999999")

    assert (response.status_code, response.json()) == (404, {"code": "unknown_project"})


@pytest.mark.parametrize("path", ["/api/projects", "/api/projects/P156634"])
def test_a_viewer_whose_token_cannot_read_strata_gets_a_permission_error(path):
    engine_for = engines.warehouse_as_viewer(
        "strata.test", "warehouse-1", transport=lambda host, token: lambda method, address, body: NO_USE_CATALOG)

    response = get(create_app(engine_for=engine_for), path)

    assert (response.status_code, response.json()) == (403, {"code": "permission"})


def test_each_read_version_lists_as_many_activities_as_check_plan_checks(fixture_app):
    """The Procurement tab's "9" and the plan check's "9 activities checked" are one count."""
    body = get(fixture_app, "/api/projects/P156634?asof=2026-10-22").json()
    nwwda = next(agency for agency in body["agencies"] if agency["agency_id"] == "northern-water-works-development-agency")

    read = [version for version in nwwda["versions"] if version["read"]]
    assert read
    for version in read:
        path = f"/api/projects/P156634/procurement/northern-water-works-development-agency/{version['plan_date']}"
        checked = get(fixture_app, f"{path}?asof=2026-10-22").json()
        assert version["activities"] == checked["counts"]["activities"], version["plan_date"]
