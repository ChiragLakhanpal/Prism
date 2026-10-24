"""The plan-check HTTP route: the Check a plan page asks it for one plan's check, as the viewer.

The route runs check_plan through the tool registry with an engine made for the viewer who asked:
the SQL warehouse with the viewer's own token in the Databricks App (ADR 0003), or the fixture
database here. Its response for the NWWDA plan of October 9, 2026 is recorded once in
tests/fixtures/api, and the screen tests serve the same file from their mocked API.

The warehouse's answer to a token that cannot read strata is written by hand in the Statement
Execution API's shape, because the gate never reaches the workspace. The workspace step in the
ticket's report runs the real one.
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
NWWDA_PLAN = "/api/projects/P156634/procurement/northern-water-works-development-agency"
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
    "X-Forwarded-Access-Token": "token-that-cannot-read-strata",
}
NO_USE_CATALOG = {  # the shape the Statement Execution API answers with when a grant is missing
    "statement_id": "statement-not-a-real-one",
    "status": {"state": "FAILED", "error": {
        "error_code": "BAD_REQUEST",
        "message": "[INSUFFICIENT_PERMISSIONS] Insufficient privileges:\n"
                   "User does not have USE CATALOG on Catalog 'strata'. SQLSTATE: 42501"}},
}


def get(app, path, headers=None):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=headers or {})
    return asyncio.run(go())


@pytest.fixture
def viewers_seen():
    return []


@pytest.fixture
def fixture_app(fixture_db, viewers_seen):
    """The app with the fixture database, noting which viewer each engine was made for."""
    @contextmanager
    def engine_for(viewer):
        viewers_seen.append(viewer)
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for)


def warehouse_answering(reply):
    """The warehouse adapter with each viewer's own token, over a transport that answers every call with reply."""
    tokens = []

    def transport(host, token):
        tokens.append(token)
        return lambda method, path, body: reply
    return engines.warehouse_as_viewer("strata.test", "warehouse-1", transport=transport), tokens


def test_the_plan_check_route_returns_the_tools_result_for_the_viewer(fixture_app, viewers_seen):
    response = get(fixture_app, f"{NWWDA_PLAN}/2026-10-09?asof=2026-10-22", ANA)

    assert response.status_code == 200
    assert response.json() == json.loads((RECORDED / "check-plan-p156634-nwwda-2026-10-09.json").read_text())
    assert [(viewer.email, viewer.token) for viewer in viewers_seen] == [
        ("ana.example@worldbank.org", "token-for-ana-only")]
    assert "token-for-ana-only" not in response.text


@pytest.mark.parametrize("path, name", [
    ("/api/projects/P156634/procurement/wajir-water-and-sewerage-company", "check-plan-p156634-wajir-no-plan.json"),
    (f"{NWWDA_PLAN}/2026-10-10", "check-plan-p156634-nwwda-2026-10-10-not-found.json"),
])
def test_the_screens_recorded_abstentions_are_what_the_route_answers(fixture_app, path, name):
    # The Check a plan screen's empty states: an agency with no plan, and a version it never published.
    response = get(fixture_app, f"{path}?asof=2026-10-22", ANA)

    assert response.status_code == 200
    assert response.json() == json.loads((RECORDED / name).read_text())


def test_the_route_without_a_version_checks_the_agencys_latest_plan(fixture_app):
    response = get(fixture_app, f"{NWWDA_PLAN}?asof=2026-10-22", ANA)

    assert (response.json()["plan"]["plan_date"], response.json()["plan"]["is_latest"]) == ("2026-10-09", True)


def test_a_viewer_whose_token_cannot_read_strata_gets_a_permission_error_and_no_rows():
    engine_for, tokens = warehouse_answering(NO_USE_CATALOG)

    response = get(create_app(engine_for=engine_for), f"{NWWDA_PLAN}/2026-10-09?asof=2026-10-22", BEN)

    assert response.status_code == 403
    assert response.json() == {"code": "permission"}
    assert tokens == ["token-that-cannot-read-strata"]


def test_on_the_workspace_a_request_with_no_forwarded_token_gets_a_permission_error():
    engine_for, tokens = warehouse_answering(NO_USE_CATALOG)
    headers = {key: value for key, value in BEN.items() if key != "X-Forwarded-Access-Token"}

    response = get(create_app(engine_for=engine_for), f"{NWWDA_PLAN}/2026-10-09", headers)

    assert (response.status_code, response.json(), tokens) == (403, {"code": "permission"}, [])


def test_a_data_service_that_fails_gives_a_reference_and_keeps_its_details_private():
    engine_for, _ = warehouse_answering({"statement_id": "statement-not-a-real-one", "status": {
        "state": "FAILED", "error": {"message": "[TABLE_OR_VIEW_NOT_FOUND] strata.silver.plan_versions"}}})

    response = get(create_app(engine_for=engine_for), f"{NWWDA_PLAN}/2026-10-09", ANA)

    assert response.status_code == 503
    assert response.json()["code"] == "data_service"
    assert response.json()["trace_id"]
    assert "TABLE_OR_VIEW_NOT_FOUND" not in response.text


def test_a_database_file_that_cannot_be_opened_gives_a_reference_and_keeps_its_details_private(tmp_path):
    missing = tmp_path / "not-built-yet.duckdb"

    response = get(create_app(engine_for=engines.duckdb_file(missing)), f"{NWWDA_PLAN}/2026-10-09", ANA)

    assert response.status_code == 503
    assert response.json()["code"] == "data_service"
    assert response.json()["trace_id"]
    assert "not-built-yet" not in response.text


def test_a_tool_that_breaks_its_contract_gives_a_reference_and_no_rows(fixture_app, monkeypatch):
    monkeypatch.setattr("strata.tools.check_plan.check_plan", lambda call, **arguments: {"rows": []})

    response = get(fixture_app, f"{NWWDA_PLAN}/2026-10-09?asof=2026-10-22", ANA)

    assert response.status_code == 500
    assert response.json()["code"] == "tool_contract"
    assert response.json()["trace_id"]
    assert "rows" not in response.json()


def test_with_no_data_service_set_up_the_route_says_so(monkeypatch):
    for key in ("STRATA_DATABASE_FILE", "DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID"):
        monkeypatch.delenv(key, raising=False)

    response = get(create_app(), f"{NWWDA_PLAN}/2026-10-09", ANA)

    assert (response.status_code, response.json()) == (503, {"code": "no_data_service"})


@pytest.mark.parametrize("query", ["asof=October-22", "view=everyone"])
def test_a_malformed_as_of_date_or_view_is_refused(fixture_app, query):
    response = get(fixture_app, f"{NWWDA_PLAN}/2026-10-09?{query}", ANA)

    assert response.status_code == 422
