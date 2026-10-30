"""Agency names that differ by a prefix are one implementing agency (ticket 133).

A project's plans and its record can write one agency two ways: P130164's plan of June 20, 2018 on the workspace
names "Public Works Department", and its projects API record names "Rajasthan State Public Works Department"
(data/fixture/recorded/api/projects/P130164.json). The pairing rule lives in strata.lakehouse.clean, and every
module that names an agency in a link or pairs two names goes through it. The Kenya names are the fixture's: P156634's
record and plans, and P161305's.
"""

import ast
import asyncio
import datetime as dt
import json
from pathlib import Path

import httpx
import pytest
from india_agency import DAY, INDIA_PLAN, INDIA_RECORD, RECORDED, app_on, give_p130164_a_plan

from strata.dbx import Viewer
from strata.lakehouse.clean import Agencies
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]

# P156634's plan versions, newest plan first, then the agencies its record names, as the Procurement tab reads them.
P156634_PLANS = ["Northern Water Works Development Agency", "Coast Water Services Board",
                 "Kilifi - Mariakani Water and Sewerage Company Ltd", "Ministry of Water and Irrigation"]
P156634_RECORD = ["Coast Water Works Development Agency", "Garissa Water and Saniation Company",
                  "Kilifi - Mariakani Water and Sewerage Company Ltd", "Kwale Water and Sewerage Company Ltd.",
                  "Malindi Water and Sewerage Company Ltd", "Ministry of Water, Sanitation and Irrigation",
                  "Mombasa Water and Sanitation Services Company", "Northern Water Works Development Agency",
                  "Tavevo Water and Sewerage Company Ltd", "Wajir Water and Sewerage Company", "Water Sector Trust Fund",
                  "Water Services Regulatory Board"]
P161305_PLANS = ["Kenya National Highways Authority"]
P161305_RECORD = ["ICT Authority (ICTA)", "Kenya National Highways Authority (KeNHA)", "Kenya Revenue Authority (KRA)",
                  "National Transport and Safety Authority (NTSA)", "State Department of Roads (SDoR)",
                  "State Department of Transport (SDoT)"]


def test_the_india_plan_and_record_name_one_agency_under_the_longer_name():
    [agency] = Agencies([INDIA_PLAN, INDIA_RECORD])

    assert agency.name == INDIA_RECORD
    assert agency.also_written_as == (INDIA_PLAN,)
    # The id is the newest plan's spelling, the one every plan row of the agency already links with.
    assert agency.agency_id == "public-works-department"


def test_names_that_differ_by_a_place_state_government_of_or_the_are_one_agency():
    for one, other in [("Government of Rajasthan Public Works Department", INDIA_RECORD),
                       ("Rajasthan Public Works Department", "Government of Rajasthan State Public Works Department"),
                       ("The National Treasury", "National Treasury"),
                       ("Kenya National Highways Authority", "National Highways Authority")]:
        assert len(list(Agencies([one, other]))) == 1, (one, other)


def test_an_agency_is_found_by_any_of_its_names_or_their_ids():
    agencies = Agencies([INDIA_PLAN, INDIA_RECORD])
    [agency] = agencies

    for asked in (INDIA_PLAN, INDIA_RECORD.upper(), "public-works-department", "rajasthan-state-public-works-department"):
        assert agencies.find(asked) == agency, asked
    # An id the project's names do not hold, written by the rule's own words, still finds the one agency it pairs with.
    assert Agencies([INDIA_PLAN]).find("rajasthan-state-public-works-department").name == INDIA_PLAN
    assert agencies.find("northern-water-works-development-agency") is None


def test_the_kenya_names_that_only_share_a_type_word_stay_apart():
    p156634 = list(Agencies(P156634_PLANS + P156634_RECORD))
    names = [agency.name for agency in p156634]

    assert names == ["Northern Water Works Development Agency", "Coast Water Services Board",
                     "Kilifi - Mariakani Water and Sewerage Company Ltd", "Ministry of Water and Irrigation",
                     "Coast Water Works Development Agency", "Garissa Water and Saniation Company",
                     "Kwale Water and Sewerage Company Ltd.", "Malindi Water and Sewerage Company Ltd",
                     "Ministry of Water, Sanitation and Irrigation", "Mombasa Water and Sanitation Services Company",
                     "Tavevo Water and Sewerage Company Ltd", "Wajir Water and Sewerage Company",
                     "Water Sector Trust Fund", "Water Services Regulatory Board"]
    assert all(agency.also_written_as == () for agency in p156634)
    # Two water companies whose names differ only by their place are two agencies.
    assert len(list(Agencies(["Kwale Water and Sewerage Company Ltd", "Wajir Water and Sewerage Company Ltd"]))) == 2


# Every module that names an implementing agency in a link, or pairs two of a project's names, by what it imports
# from the rule. A new caller is added here knowingly.
RULE = "strata.lakehouse.clean"
RULE_NAMES = {"agency_id", "Agencies", "same_agency", "Agency"}
CALLERS = {
    # The Procurement tab's headings and Packages, and what changed in a plan.
    "strata.server.projects": {"Agencies"},
    "strata.server.changes": {"Agencies", "agency_id"},
    # The plan check, which the agency track record, the drafts, Home and the project signals call.
    "strata.tools.check_plan": {"Agencies", "agency_id"},
    # A baseline is saved for the agency the plan check names.
    "strata.server.baseline": {"Agencies"},
    # Links to a plan check from one plan row: the contract trail and the package page (find_comparables), the box,
    # rebidding risk, the project's records and signals, Home, the documents list, uploads and the seeded examples.
    "strata.tools.find_comparables": {"agency_id"},
    "strata.server.lookup": {"agency_id"},
    "strata.tools.rebidding_risk": {"agency_id"},
    "strata.tools.project_records": {"agency_id"},
    "strata.tools.project_signals": {"agency_id"},
    "strata.server.home": {"agency_id"},
    "strata.server.documents": {"agency_id"},
    "strata.server.uploads": {"agency_id"},
    "strata.server.app": {"agency_id"},
    "strata.server.drafts": {"agency_id"},
    "strata.seed_examples": {"agency_id"},
    "strata.proposal.deck": {"agency_id"},
}


def _module(path: Path) -> str:
    return ".".join(path.relative_to(ROOT / "src").with_suffix("").parts)


def test_the_pairing_rule_lives_in_clean_and_every_caller_imports_it_from_there():
    found: dict[str, set[str]] = {}
    for path in sorted((ROOT / "src" / "strata").rglob("*.py")):
        source = path.read_text()
        if not any(name in source for name in (*RULE_NAMES, "agency_key")):
            continue  # a module whose text never names the rule can neither import it nor define its own
        tree = ast.parse(source, str(path))
        module = _module(path)
        imported = {alias.asname or alias.name.split(".")[0] for node in ast.walk(tree)
                    if isinstance(node, ast.Import | ast.ImportFrom) for alias in node.names}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                named = {alias.name for alias in node.names} & RULE_NAMES
                if named and node.module == RULE:
                    found.setdefault(module, set()).update(named)
                # The id may come only from the rule's module, never through another module that imported it.
                assert not ("agency_id" in named and node.module != RULE), f"{module} imports agency_id from {node.module}"
            if isinstance(node, ast.FunctionDef) and module != RULE:
                assert node.name not in ("agency_id", "agency_key", "same_agency"), f"{module} defines {node.name}"
            if (isinstance(node, ast.Attribute) and node.attr == "agency_id" and isinstance(node.value, ast.Name)
                    and node.value.id in imported):
                # Another module's agency_id reached through its name, such as upload_routes.agency_id.
                assert False, f"{module} calls {node.value.id}.agency_id"

    assert found == CALLERS


def test_p161305_s_highways_authority_keeps_its_plan_heading_apart_from_the_record_s_abbreviated_name():
    p161305 = list(Agencies(P161305_PLANS + P161305_RECORD))

    assert [agency.name for agency in p161305] == P161305_PLANS + P161305_RECORD
    assert p161305[0].agency_id == "kenya-national-highways-authority"


# ── P130164 with a plan, on a copy of the fixture (tests/india_agency.py) ─

VIEWER = Viewer(email="ana.example@worldbank.org", name="Ana Example", user_id="4021@1984", token="not-a-real-token")
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}


@pytest.fixture(scope="module")
def india(fixture_db, tmp_path_factory):
    database = give_p130164_a_plan(fixture_db, tmp_path_factory.mktemp("india"))
    return database, app_on(database)


def get(app, path):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=ANA)
    response = asyncio.run(go())
    assert response.status_code == 200, response.text
    return response.json()


def test_p130164_s_procurement_tab_shows_one_heading_with_the_plan_under_the_record_s_longer_name(india):
    _, app = india
    [agency] = get(app, f"/api/projects/P130164?{DAY}")["agencies"]

    assert agency["implementing_agency"] == INDIA_RECORD
    assert agency["also_written_as"] == [INDIA_PLAN]
    assert agency["agency_id"] == "public-works-department"
    assert [version["plan_date"] for version in agency["versions"]] == ["2026-08-17", "2026-07-31"]
    assert agency["changes"]["previous_plan_date"] == "2026-07-31"


def test_the_plan_check_the_tab_the_package_workspace_and_the_track_record_agree_on_p130164_s_agency(india):
    database, app = india
    tab = get(app, f"/api/projects/P130164?{DAY}")["agencies"][0]["agency_id"]

    # The plan check opens from the tab's id, and from the id of the record's name, and gives back the tab's id.
    for asked in (tab, "rajasthan-state-public-works-department"):
        checked = get(app, f"/api/projects/P130164/procurement/{asked}?{DAY}")
        assert checked["abstention"] is None, asked
        assert (checked["plan"]["document_id"], checked["plan"]["agency_id"]) == ("40122770", tab)
        assert checked["plan"]["implementing_agency"] == INDIA_PLAN  # as the plan writes it
        assert checked["counts"]["activities"] == 8
    changed = get(app, f"/api/projects/P130164/procurement/rajasthan-state-public-works-department/2026-08-17/changes?{DAY}")
    assert changed["plan"]["agency_id"] == tab

    # The package workspace, whose tracker dates the package's steps, and the contract trail link to the same check.
    package = get(app, f"/api/packages/KE-CWSB-567630-CW-DIR?{DAY}")["package"]
    assert package["plan"]["agency_id"] == tab
    trail = get(app, f"/api/projects/P130164/packages/KE-CWSB-567630-CW-DIR?{DAY}")
    [plan] = next(stage for stage in trail["stages"] if stage["stage"] == "plan")["records"]
    assert plan["agency_id"] == tab
    assert {row["agency_id"] for row in get(app, f"/api/projects/P130164/packages?{DAY}")["rows"]} == {tab}

    with DuckDBEngine.open(database, read_only=True) as engine:
        track = registry.call("agency_track_record", {"project_id": "P130164", "implementing_agency": INDIA_RECORD},
                              registry.Context(engine, VIEWER, "staff", dt.date(2026, 10, 23)))
    assert track["agency"] == {"agency_id": tab, "agency_name": INDIA_PLAN}
    assert track["plan"]["document_id"] == "40122770"


def test_the_procurement_tab_s_recordings_are_what_the_server_answers_on_the_copy(india):
    # The screen test serves these (web/tests/projects.spec.ts), so the screen and the server cannot drift apart.
    _, app = india
    for name, path in RECORDED.items():
        assert get(app, path) == json.loads((ROOT / "tests" / "fixtures" / "api" / name).read_text()), name


def test_the_kenya_projects_keep_their_headings_on_the_fixture(fixture_db):
    app = app_on(fixture_db)

    p156634 = get(app, f"/api/projects/P156634?{DAY}")["agencies"]
    assert [agency["implementing_agency"] for agency in p156634[:4]] == P156634_PLANS
    assert len(p156634) == 14 and all(agency["also_written_as"] == [] for agency in p156634)
    p161305 = get(app, f"/api/projects/P161305?{DAY}")["agencies"]
    assert [(agency["implementing_agency"], agency["also_written_as"]) for agency in p161305] == [
        (name, []) for name in P161305_PLANS + P161305_RECORD]
