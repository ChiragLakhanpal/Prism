"""The one box's lookups (ticket 14): what Enter will do with a loan number or a STEP reference.

The box's intent rules run in the browser. Its two lookups run here, as the viewer and as of the page's
date: a loan number in any of its forms names the project it finances, and a STEP reference names the
latest published Procurement Plan that lists it, so the box can open that plan's check with the row in
view. Their answers for IDA-60290 and KE-NWWDA-541055-CW-RFB are recorded once in tests/fixtures/api,
and the screen tests serve the same files.

Expected values come from the records (tests/ground_truth/values.toml): P156634's project record lists
IDA-60290 and IDA-60300, and the October 9, 2026 Procurement Plan of the Northern Water Works Development
Agency lists KE-NWWDA-541055-CW-RFB.
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
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
       "X-Forwarded-Access-Token": "token-for-ana-only"}


@pytest.fixture
def app(fixture_db):
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for)


def get(app, path, **params):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=ANA, params=params)
    return asyncio.run(go())


@pytest.mark.parametrize("written", ["IDA60290", "IDA-60290", "60290", "IDA / 60290", "ida-60290", " IDA 60290 "])
def test_a_loan_number_in_any_of_its_forms_names_the_project_it_finances(app, written):
    response = get(app, "/api/lookup/loan", q=written)

    assert response.status_code == 200
    assert response.json() == json.loads((RECORDED / "lookup-loan-ida-60290.json").read_text())
    assert (response.json()["loan_number"], response.json()["project_id"]) == ("IDA60290", "P156634")


@pytest.mark.parametrize("written", ["IDA-99999", "99999", "not a loan"])
def test_a_loan_number_no_project_record_lists_is_not_found(app, written):
    response = get(app, "/api/lookup/loan", q=written)

    assert (response.status_code, response.json()) == (404, {"code": "unknown_loan"})


def test_a_loan_number_is_not_found_before_its_project_record_was_public(app):
    # P156634's record is public from March 1, 2017.
    assert get(app, "/api/lookup/loan", q="IDA-60290", asof="2016-12-31").status_code == 404


def test_a_step_reference_names_the_latest_published_plan_that_lists_it(app):
    response = get(app, "/api/lookup/activity", q="KE-NWWDA-541055-CW-RFB")

    assert response.status_code == 200
    found = response.json()
    assert found == json.loads((RECORDED / "lookup-activity-ke-nwwda-541055-cw-rfb.json").read_text())
    assert (found["project_id"], found["agency_id"], found["plan_date"], found["is_latest"]) == (
        "P156634", "northern-water-works-development-agency", "2026-10-09", True)
    assert found["implementing_agency"] == "Northern Water Works Development Agency"


def test_a_step_reference_typed_in_lower_case_names_the_same_plan(app):
    assert get(app, "/api/lookup/activity", q="ke-nwwda-541055-cw-rfb").json()["plan_date"] == "2026-10-09"


def test_a_step_reference_no_published_plan_lists_is_not_found(app):
    response = get(app, "/api/lookup/activity", q="KE-NWWDA-000000-CW-RFB")

    assert (response.status_code, response.json()) == (404, {"code": "unknown_activity"})


def test_a_step_reference_is_found_only_in_plans_public_on_the_page_s_date(app):
    # On October 1, 2026 the agency's latest public plan was the one of March 5, 2026, which lists it too.
    found = get(app, "/api/lookup/activity", q="KE-NWWDA-541055-CW-RFB", asof="2026-10-01").json()

    assert (found["plan_date"], found["is_latest"]) == ("2026-03-05", True)
