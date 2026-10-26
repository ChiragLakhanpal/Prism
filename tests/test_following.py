"""Following at seam 3: follows saved per viewer, and who may read and write them, through the HTTP routes (ticket 37,
criterion 5).

PUT and DELETE /api/projects/{project_id}/follow follow and unfollow a project, saved per viewer in strata.ops as the
app's own service principal (a DuckDB file here). GET /api/following runs project_signals on each project the viewer
follows and answers only to viewers with the World Bank staff role, which the roles file's [staff] names by workspace
group. tests/test_mission_brief.py walks the whole story; these tests take the edges. Each test is its own viewer, so
they share one app state. The fixture database is opened read-only, and today is October 22, 2026.
"""

import asyncio
import datetime as dt
import json
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.config import load_roles
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.server.following import FollowStore

TODAY = dt.date(2026, 10, 22)
RECORDED = Path(__file__).resolve().parent / "fixtures" / "api"
TRUTH = {entry["id"]: entry["value"] for entry in
         tomllib.loads((Path(__file__).resolve().parent / "ground_truth" / "values.toml").read_text())["value"]}


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"50{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN, CY, DEE = viewer(1, "Ana"), viewer(2, "Ben"), viewer(3, "Cy"), viewer(4, "Dee")
# Ana, Ben and Dee are in the workspace's users group, which the roles file names as World Bank staff; Cy is in none.
GROUPS = {"501@1984": ["users"], "502@1984": ["users", "strata-team-kenya-water"], "503@1984": [], "504@1984": ["users"]}


def call(app, method, path, headers=None, **options):
    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


@pytest.fixture(scope="module")
def app(fixture_db, tmp_path_factory):
    state_db = tmp_path_factory.mktemp("following") / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        catalog.build(engine)

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    moments = iter(dt.datetime(2026, 10, 22, 14, minute, tzinfo=dt.UTC) for minute in range(60))
    return create_app(engine_for=reading, follows=FollowStore(lambda: DuckDBEngine.open(state_db)),
                      access=Access(load_roles(), StaticGroups(GROUPS)), today=lambda: TODAY, now=lambda: next(moments))


def test_follows_are_kept_per_viewer_and_unfollowing_takes_a_project_off_the_list(app):
    call(app, "PUT", "/api/projects/P156634/follow", DEE)
    call(app, "PUT", "/api/projects/P130164/follow", DEE)

    assert call(app, "GET", "/api/projects/P156634/follow", BEN).json() == {"following": False}
    assert call(app, "DELETE", "/api/projects/P156634/follow", DEE).json() == {"following": False}
    [left] = call(app, "GET", "/api/following", DEE).json()["projects"]
    assert left["project"]["project_id"] == "P130164" and left["status"] == "closed"
    assert call(app, "PUT", "/api/projects/P999999/follow", DEE).json()["code"] == "unknown_project"


def test_the_following_route_and_follows_refuse_a_viewer_without_the_world_bank_staff_role(app):
    refused = call(app, "GET", "/api/following", CY)

    assert (refused.status_code, refused.json()) == (403, json.loads((RECORDED / "following-not-staff.json").read_text()))
    assert call(app, "PUT", "/api/projects/P156634/follow", CY).json()["code"] == "not_staff"
    assert call(app, "GET", "/api/me", ANA).json()["staff"] is True
    assert call(app, "GET", "/api/me", CY).json()["staff"] is False


def test_a_preview_reads_no_following_list_and_writes_no_follow(app):
    # No preview keeps Following (the roles file's [views], ticket 40): the page is not in that view.
    assert call(app, "GET", "/api/following?view=piu", ANA).json()["code"] == "not_in_view"
    assert call(app, "PUT", "/api/projects/P156634/follow?view=public", ANA).status_code == 403


def test_a_plan_signals_record_shows_the_fields_that_set_off_its_check_highlighted(app):
    """The drawer behind "passed its planned completion (July 31, 2026)" shows that date, as first published in the
    plan of March 5, 2026, and the one behind "about 4 times its estimate" the signed amount and the Estimated Amount
    (the 37 brief, section 4.3; values.toml)."""
    call(app, "PUT", "/api/projects/P156634/follow", ANA)
    events = {event["id"]: event for event in call(app, "GET", "/api/following", ANA).json()["evidence"]}

    def highlighted(evidence_id):
        fields = events[evidence_id]["row"]["fields"]
        return {field["key"]: field["value"] for field in fields if field.get("highlight")}, {field["key"]: field["value"] for field in fields}

    marked, fields = highlighted("strata.silver.plan_rows:40132287/KE-NWWDA-541055-CW-RFB")
    assert marked == {"planned_completion_on": TRUTH["plan-541055-planned-completion"].isoformat()}
    assert fields["planned_completion_plan_date"] == TRUTH["plan-541055-first-listed"].isoformat()
    assert fields["process_status"] == TRUTH["plan-541055-status"]
    marked, _ = highlighted("strata.silver.plan_rows:40132287/KE-NWWDA-229129-CW-RFB")
    assert marked == {"actual_amount_usd": f'{TRUTH["plan-229129-actual"]:.2f}',
                      "estimated_amount_usd": f'{TRUTH["plan-229129-estimated"]:.2f}'}
    marked, _ = highlighted("strata.silver.plan_rows:40122770/KE-CWSB-567630-CW-DIR")
    assert marked == {"estimated_amount_usd": TRUTH["plan-cwsb-567630-estimated"].replace(",", ""),
                      "first_plan_date": TRUTH["plan-cwsb-567630-first-listed"].isoformat()}


def test_following_says_how_many_checks_ran_and_which_sources_they_read_from_the_registries(app):
    """The page names "the seven checks" and links to Data readiness for the checks' sources: both come from the
    server, from project_signals' checks and config/tools.toml, so the browser keeps no copy of either."""
    from strata.config import load_tools

    answer = call(app, "GET", "/api/following", BEN).json()

    assert answer["checks"] == 7
    assert answer["sources"] == list(load_tools()["project_signals"].sources)
    # The completion check's amount, as a sentence writes a whole million (DESIGN.md rule 11).
    assert answer["thresholds"]["completion_passed_min_millions"] == "1"


def test_a_viewer_without_the_world_bank_staff_role_cannot_start_a_mission_brief(app):
    started = call(app, "POST", "/api/drafts", CY, json={"kind": "mission_brief", "project_id": "P156634"})

    assert (started.status_code, started.json()["code"]) == (403, "not_staff")
