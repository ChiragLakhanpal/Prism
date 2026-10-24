"""The project page as the hub (ticket 21) at seam 3: the routes All projects, a project's Summary, its
Procurement tab, its Documents and the source view ask for, as the viewer and as of the page's ?asof=.

The values below are copied from the recorded sources in data/fixture/recorded and from
tests/ground_truth/values.toml, never worked out the way the routes work them out.
"""

import asyncio
import datetime as dt
import shutil
from contextlib import contextmanager

import httpx
import pytest

from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}


def call(app, method, path, headers=ANA, body=None):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers, json=body)
    return asyncio.run(go())


def get(app, path, headers=ANA):
    return call(app, "GET", path, headers)


SAVED_AT = dt.datetime(2026, 10, 23, 15, 30, tzinfo=dt.UTC)


def app_on(database, read_only=True):
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(database, read_only=read_only) as engine:
            yield engine
    return create_app(engine_for=engine_for, now=lambda: SAVED_AT)


@pytest.fixture(scope="module")
def hub(fixture_db):
    return app_on(fixture_db)


# ── All projects ─────────────────────────────────────────────────────────

def test_all_projects_gives_one_page_of_20_with_the_range_it_shows(hub):
    body = get(hub, "/api/projects?asof=2026-10-23").json()

    # The fixture holds 93 project records: Kenya's from fiscal 2012 to 2025, and the showcase's.
    assert (body["total"], body["page"], body["pages"], body["first"], body["last"]) == (93, 1, 5, 1, 20)
    assert len(body["rows"]) == 20
    last = get(hub, "/api/projects?asof=2026-10-23&page=5").json()
    assert (last["page"], last["first"], last["last"], len(last["rows"])) == (5, 81, 93, 13)


def test_a_page_past_the_last_gives_the_last_page(hub):
    body = get(hub, "/api/projects?asof=2026-10-23&page=40").json()

    assert (body["page"], body["first"], body["last"]) == (5, 81, 93)


def test_all_projects_finds_a_project_by_part_of_its_name_its_id_or_its_country(hub):
    by_country = get(hub, "/api/projects?asof=2026-10-23&q=india").json()
    assert (by_country["total"], [row["project_id"] for row in by_country["rows"]]) == (1, ["P130164"])
    assert by_country["query"] == "india"

    by_name = get(hub, "/api/projects?asof=2026-10-23&q=RAJAST").json()
    assert [row["project_id"] for row in by_name["rows"]] == ["P130164"]

    # An ID matches with or without its P, and an exact ID comes first.
    for asked in ("p156634", "156634"):
        rows = get(hub, f"/api/projects?asof=2026-10-23&q={asked}").json()["rows"]
        assert rows[0]["project_id"] == "P156634", asked

    nothing = get(hub, "/api/projects?asof=2026-10-23&q=atlantis").json()
    assert (nothing["total"], nothing["rows"], nothing["page"], nothing["pages"]) == (0, [], 1, 0)


def test_the_search_ignores_case_and_accents(tmp_path):
    database = tmp_path / "accents.duckdb"
    with DuckDBEngine.open(database) as engine:
        catalog.build(engine)
        engine.insert_rows("strata.gold.country", ("country_code", "country_name", "public_from"),
                           [("TR", "Türkiye", "2020-01-01"), ("EG", "Egypt, Arab Rep.", "2020-01-01")])
        engine.insert_rows("strata.gold.project", ("project_id", "project_name", "country_code", "status",
                                                   "public_from"),
                           [("P000001", "Izmir Water", "TR", "Active", "2020-01-01"),
                            ("P000002", "Cairo Roads", "EG", "Active", "2020-01-01")])
    app = app_on(database)

    assert [row["project_id"] for row in get(app, "/api/projects?q=turkiye").json()["rows"]] == ["P000001"]
    assert [row["project_id"] for row in get(app, "/api/projects?q=egypt").json()["rows"]] == ["P000002"]


# ── The Summary's records ────────────────────────────────────────────────

def test_silver_keeps_each_project_s_sector_shares_and_environmental_assessment_category(fixture_db):
    """Seam 1: the projects API record's sectors with their shares and its Environmental Assessment
    Category, which the Summary shows (data/fixture/recorded/api/projects/P130164.json: major_sectors and
    envassesmentcategorycode)."""
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        sectors = engine.run("SELECT sector_code, sector_name, share_percent, major_sector_code "
                             "FROM strata.silver.project_sectors WHERE project_id = :pid ORDER BY sector_code",
                             {"pid": "P130164"}).rows
        category = engine.run("SELECT ea_category FROM strata.silver.project_environment WHERE project_id = :pid",
                              {"pid": "P130164"}).rows
    assert [(code, name, float(share), major) for code, name, share, major in sectors] == [
        ("TF", "FY17 - Public Administration - Transportation", 3.0, "TX"),
        ("TI", "FY17 - Rural and Inter-Urban Roads", 97.0, "TX")]
    assert list(category) == [("B",)]


ESF_FIELD = "esrc_ovrl_risk_rate"  # the projects API's overall risk rating under the ESF


def test_a_record_fetched_with_the_projects_endpoint_s_fields_gives_the_same_silver_rows_as_the_full_record():
    """Seam 1: the nightly fetch asks the projects API for only the fields its endpoint names
    (config/sources.toml), so each field the silver transform reads must be among them, or a Summary row
    is empty on the workspace though it shows on the fixture, whose showcase records are fetched whole.
    P130164 predates the ESF, so a copy of its record with a risk rating stands in for a newer project."""
    import json
    from pathlib import Path
    from urllib.parse import parse_qs, urlsplit

    from strata.config import load_sources
    from strata.lakehouse.silver import projects as silver_projects

    recorded = Path(__file__).parents[1] / "data" / "fixture" / "recorded" / "api" / "projects" / "P130164.json"
    full = json.loads(recorded.read_text())["response"]
    full["projects"]["P000009"] = {**full["projects"]["P130164"], "id": "P000009", ESF_FIELD: "Substantial"}
    asked = parse_qs(urlsplit(load_sources()["projects"].endpoint).query)["fl"][0].split(",")
    fetched = {"projects": {pid: {field: value for field, value in record.items() if field in asked}
                            for pid, record in full["projects"].items()}}
    at = dt.datetime(2026, 10, 23, tzinfo=dt.UTC)

    assert silver_projects.parse(fetched, "page", at) == silver_projects.parse(full, "page", at)


def test_silver_keeps_a_project_s_risk_rating_under_the_environmental_and_social_framework():
    """Seam 1: a project approved under the Environmental and Social Framework (ESF) has an overall
    environmental and social risk rating in its record, and often no Environmental Assessment Category.
    No recorded project has one (P130164 and P156634 predate the ESF, and the Kenya list was fetched
    without the field), so these records are written by hand, in the API's shape."""
    from strata.lakehouse.silver import projects as silver_projects

    at = dt.datetime(2026, 10, 23, tzinfo=dt.UTC)
    body = {"projects": {
        "P000009": {"id": "P000009", "boardapprovaldate": "2021-06-15T00:00:00Z", ESF_FIELD: "Substantial"},
        "P000008": {"id": "P000008", "boardapprovaldate": "2015-06-15T00:00:00Z", "envassesmentcategorycode": "A"},
        "P000007": {"id": "P000007", "boardapprovaldate": "2015-06-15T00:00:00Z"},
    }}

    rows = silver_projects.parse(body, "page", at)["strata.silver.project_environment"]

    assert [(pid, category, risk) for pid, category, risk, *_ in rows] == [
        ("P000009", None, "Substantial"), ("P000008", "A", None)]


def facts(summary):
    """Every value the Summary shows, by its key: the fact tables' rows and the history's."""
    rows = [row for group in ("dates", "money", "ratings", "who") for row in summary[group]]
    return {row["key"]: row for row in rows}


def test_a_project_s_header_reads_its_display_name_country_status_and_agency(hub):
    project = get(hub, "/api/projects/P130164?asof=2026-10-23").json()["project"]

    # The display name leaves out the record's final "Project" (values.toml, project-p130164-name).
    assert ground_truth("project-p130164-name") == f"{project['display_name']} Project"
    assert (project["country"], project["status"], project["implementing_agencies"]) == (
        ground_truth("project-p130164-country"), ground_truth("project-p130164-status"),
        [ground_truth("project-p130164-agency")])


def test_p130164_s_summary_gives_every_value_with_its_source_in_one_small_answer(hub):
    response = get(hub, "/api/projects/P130164/summary?asof=2026-10-23")
    summary = response.json()

    assert len(response.content) <= 15_000  # the 21 brief's budget for the Summary's one request
    found = facts(summary)
    assert found["approval_date"]["value"] == str(ground_truth("project-p130164-approval"))
    assert found["closing_date"]["value"] == str(ground_truth("project-p130164-closing"))
    # The ICR data sheet and every monthly history row give one closing date, so the date never moved.
    assert "original_closing_date" not in found
    assert (summary["history"]["known"], summary["history"]["rows"]) == (True, [])
    # "The closing date did not change after approval." cites the monthly history it reads, from the first
    # month the history holds (October 2013, the month the credit was approved).
    assert summary["history"]["source"] == {"evidence_id": "strata.gold.project_closing_date:P130164/2013-10-31",
                                            "kind": "loan_history", "date": "2013-10-31"}
    assert "strata.gold.project_closing_date:P130164/2013-10-31" in {event["id"] for event in summary["sources"]}
    # US$ millions to one decimal, from the credit's record (credit-ida53100-*): 160,000,000,
    # 121,630,912.89 and 30,696,577.26.
    assert [found[key]["value"] for key in ("commitment", "disbursed", "canceled")] == ["160.0", "121.6", "30.7"]
    assert summary["lead"] == {"kind": "closed", "closing_date": "2018-12-31", "moves": 0, "commitment": "160.0",
                               "disbursed": "121.6", "canceled": "30.7", "disbursed_as_of": "2026-09-30"}
    assert found["pdo"]["value"] == ground_truth("isr-13-rating")
    assert found["pdo"]["source"]["evidence_id"] == "strata.gold.passage:30730274/v1/s3"
    assert found["ieg_outcome"]["value"] == ground_truth("ieg-outcome-p130164")
    assert found["ea_category"]["value"] == "B"
    assert found["region"]["value"] == "South Asia"
    assert found["agencies"]["values"] == [ground_truth("project-p130164-agency")]
    assert found["sectors"]["value"] == "Transportation"
    assert found["sectors"]["values"] == ["Rural and Inter-Urban Roads: 97%", "Public Administration - Transportation: 3%"]

    # Every value has a source, and every source the facts name comes with the answer, so its marker
    # opens the evidence drawer at once.
    held = {source["id"] for source in summary["sources"]}
    for key, row in found.items():
        assert row["source"]["evidence_id"] in held, key


def test_a_project_s_summary_as_of_a_date_uses_only_what_was_public_then(hub):
    summary = get(hub, "/api/projects/P156634/summary?asof=2023-01-01").json()

    found = facts(summary)
    # P156634's closing date moved once by then: from October 31, 2022 to April 30, 2024, first shown in
    # the month that ended November 30, 2022 (values.toml, closing-p156634-original and -move-1).
    original, moved = str(ground_truth("closing-p156634-original")), str(ground_truth("closing-p156634-move-1"))
    assert summary["lead"]["moves"] == 1
    assert [(row["before"], row["after"], row["first_recorded"]) for row in summary["history"]["rows"]] == [
        (original, moved, "2022-11-30")]
    assert found["original_closing_date"]["value"] == original
    assert found["closing_date"]["value"] == moved  # the record of today was not public then, so the history's
    assert get(hub, "/api/projects/P999999/summary").status_code == 404


def test_a_project_with_a_risk_rating_under_the_esf_shows_it_in_place_of_its_environmental_assessment_category(
        fixture_db, tmp_path):
    # No recorded project has an ESF rating, so a copy of the fixture gives P130164's record one by hand.
    database = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, database)
    with DuckDBEngine.open(database) as engine:
        engine.run("UPDATE strata.silver.project_environment SET esf_risk = :risk WHERE project_id = :pid",
                   {"risk": "Substantial", "pid": "P130164"})

    found = facts(get(app_on(database), "/api/projects/P130164/summary?asof=2026-10-23").json())

    assert found["esf_rating"]["value"] == "Substantial"
    assert "ea_category" not in found
    # It is a value of the projects API's record, cited as that record, like the region.
    assert found["esf_rating"]["source"] == found["region"]["source"]


# ── Packages ─────────────────────────────────────────────────────────────

def test_packages_list_every_activity_in_each_agency_s_latest_plan_a_page_at_a_time(hub):
    body = get(hub, "/api/projects/P156634/packages?asof=2026-10-23").json()

    # NWWDA-WSDP-03-2019-2020 is in two agencies' latest plans, so 46 rows hold 45 references.
    assert (body["total"], body["pages"], len(body["rows"])) == (46, 3, 20)
    everything = [row for page in (1, 2, 3) for row in
                  get(hub, f"/api/projects/P156634/packages?asof=2026-10-23&page={page}").json()["rows"]]
    assert len({row["activity_reference_no"] for row in everything}) == 45
    assert len({(row["agency_id"], row["activity_reference_no"]) for row in everything}) == 46
    first = body["rows"][0]
    assert (first["implementing_agency"], first["plan_date"]) == ("Northern Water Works Development Agency", "2026-10-09")

    found = get(hub, "/api/projects/P156634/packages?asof=2026-10-23&q=ke-nwwda-541055").json()["rows"]
    assert [(row["activity_reference_no"], row["estimated_amount_usd"]) for row in found] == [
        ("KE-NWWDA-541055-CW-RFB", f"{ground_truth('plan-541055-estimated'):.2f}")]
    # Descriptions keep the PDF's wrap spaces ("Exploratory Bo reholes"), which the search ignores.
    holes = get(hub, "/api/projects/P156634/packages?asof=2026-10-23&q=boreholes").json()
    assert holes["total"] >= 1 and all("reholes" in row["description"] for row in holes["rows"])
    assert get(hub, "/api/projects/P156634/packages?q=atlantis").json()["total"] == 0


# ── Documents and the source view ────────────────────────────────────────

def test_p130164_s_documents_list_each_type_in_project_cycle_order_with_its_dates(hub):
    body = get(hub, "/api/projects/P130164/documents?asof=2026-10-23").json()

    groups = {group["type"]: group for group in body["groups"]}
    assert [group["type"] for group in body["groups"]] == ["pad", "isr", "procurement_plan", "icr", "icr_review", "other"]
    [pad] = groups["pad"]["documents"]
    assert (pad["document_date"], pad["disclosed_on"], pad["doc_key"]) == (
        str(ground_truth("pad-date")), str(ground_truth("pad-disclosed")), "pad-2013-10-01")
    [icr] = groups["icr"]["documents"]
    assert (icr["document_date"], icr["disclosed_on"]) == (str(ground_truth("icr-date")), str(ground_truth("icr-disclosed")))
    # The ICR's PDF has 66 pages (values.toml, icr-pdf-pages); I read all but four data sheet pages, whose
    # words the fixture does not record, and three pages with no text.
    assert (icr["pages_read"], icr["pdf_pages"], icr["partial"]) == (59, ground_truth("icr-pdf-pages"), True)
    # The re-issue under the same report number replaces the first version, in one row.
    [review] = groups["icr_review"]["documents"]
    assert (review["document_date"], review["reissue"]["document_date"]) == (
        str(ground_truth("icr-review-reissue-date")), str(ground_truth("icr-review-date")))
    assert (review["doc_key"], review["reissue"]["doc_key"]) == ("icr-review-2023-05-04", "icr-review-2020-03-27")
    # 13 ISRs, newest first, the newest five shown before "Show all", and Procurement Plans the fixture
    # holds no text for, listed but not read.
    isrs = groups["isr"]
    assert (isrs["count"], isrs["shown_count"]) == (13, 5)
    assert isrs["documents"][0]["sequence"] == 13 and isrs["documents"][0]["document_date"] == "2018-12-28"
    assert not any(plan["read"] for plan in groups["procurement_plan"]["documents"])
    assert body["total"] == 61  # 62 listed, the ICR Review's first version folded into its re-issue

    before = get(hub, "/api/projects/P130164/documents?asof=2021-01-01").json()
    [first] = {group["type"]: group for group in before["groups"]}["icr_review"]["documents"]
    assert (first["document_date"], first["reissue"]) == (str(ground_truth("icr-review-date")), None)


def test_documents_say_whether_a_project_is_in_the_set_whose_documents_i_fetch(hub):
    # config/slice.toml names P130164 as the showcase. P117635, Kenya Water Security and Climate Resilience,
    # is a Kenya water project with a Board date in fiscal 2013, so the slice's criteria select it, though
    # the fixture holds no list of its documents. P120014, KE Electricity Modernization, is an energy
    # project, so its documents are never fetched (data/fixture/recorded/api/projects/kenya-fy2012-2025.json).
    shown = get(hub, "/api/projects/P130164/documents?asof=2026-10-23").json()
    waiting = get(hub, "/api/projects/P117635/documents?asof=2026-10-23").json()
    outside = get(hub, "/api/projects/P120014/documents?asof=2026-10-23").json()

    assert (shown["in_document_set"], shown["total"] > 0) == (True, True)
    assert (waiting["in_document_set"], waiting["groups"]) == (True, [])
    assert (outside["in_document_set"], outside["groups"]) == (False, [])


SOURCE = "/api/projects/P130164/documents"


def test_the_source_view_opens_the_icr_at_page_23_with_paragraph_54_highlighted(hub):
    body = get(hub, f"{SOURCE}/icr-2019-10-10?page=23&para=54&asof=2026-10-23").json()

    assert (body["state"], body["page"], body["correction"]) == ("page", 23, None)
    assert body["document"]["pdf_pages"] == 66
    assert body["highlight"] == {"passage_id": "31525018/v1/54", "para": "54"}
    texts = {passage["passage_id"]: passage["text"] for passage in body["passages"]}
    assert ground_truth("icr-para-54") in texts["31525018/v1/54"]
    assert "31525018/v1/55" in texts


def test_the_source_view_corrects_a_wrong_page_paragraph_or_address(hub):
    moved = get(hub, f"{SOURCE}/icr-2019-10-10?page=22&para=54").json()
    assert (moved["page"], moved["correction"]) == (23, {"kind": "moved", "para": "54", "page": 23})

    found = get(hub, f"{SOURCE}/icr-2019-10-10?para=54").json()
    assert (found["page"], found["correction"]) == (23, None)

    missing = get(hub, f"{SOURCE}/icr-2019-10-10?page=23&para=999").json()
    assert (missing["page"], missing["highlight"], missing["correction"]["kind"]) == (23, None, "no_para")

    past = get(hub, f"{SOURCE}/icr-2019-10-10?page=80").json()
    assert (past["page"], past["correction"]["kind"]) == (66, "page_range")

    short = get(hub, f"{SOURCE}/icr?page=23&para=54").json()
    assert (short["state"], short["canonical"], short["page"]) == ("page", "icr-2019-10-10", 23)
    by_id = get(hub, f"{SOURCE}/31525018?page=23").json()
    assert by_id["canonical"] == "icr-2019-10-10"

    many = get(hub, f"{SOURCE}/isr").json()
    assert (many["state"], many["ambiguous"]) == ("ambiguous", {"type": "isr", "count": 13})
    assert get(hub, f"{SOURCE}/not-a-document").json()["state"] == "not_found"
    early = get(hub, f"{SOURCE}/icr-2019-10-10?page=23&asof=2019-10-01").json()
    assert (early["state"], early["disclosed_on"]) == ("not_public", str(ground_truth("icr-disclosed")))
    # A page the layout parser could not read, and a document listed but not read.
    assert get(hub, f"{SOURCE}/icr-2019-10-10?page=5").json()["page_state"] == "unread"
    assert get(hub, f"{SOURCE}/30152361").json()["state"] == "doc_unread"


def test_each_hardest_document_s_page_opens_in_the_source_view(hub):
    """The Data readiness page's hardest documents link "Open at page" to the source view by each
    document's id (ticket 21 repoints ticket 18's link): each lands on its page, read or not."""
    shelf = get(hub, "/api/data/readiness?asof=2026-10-23").json()["stress_shelf"]
    landed = {}
    for entry in shelf:
        document = entry["document"]
        if not document or entry["hard_page"] is None:
            continue
        body = get(hub, f"/api/projects/{document['project_id']}/documents/{document['document_id']}"
                        f"?page={entry['hard_page']}&asof=2026-10-23").json()
        landed[entry["key"]] = (body["state"], body["page"], body["page_state"])
    assert landed == {"p130164_pad": ("page", 65, "read"), "longest_pad": ("page", 6, "unread"),
                      "long_plan": ("page", 3, "read"), "french_report": ("page", 13, "read")}


# ── What changed between a plan and the version before it ────────────────

NWWDA_PLAN = "/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09"


def ground_truth(value_id):
    import tomllib
    from pathlib import Path

    values = tomllib.loads((Path(__file__).parent / "ground_truth" / "values.toml").read_text())["value"]
    return next(value["value"] for value in values if value["id"] == value_id)


def test_the_nwwda_plan_of_october_9_2026_re_estimated_two_activities_since_the_plan_of_march_5(hub, fixture_db):
    body = get(hub, f"{NWWDA_PLAN}/changes?asof=2026-10-23").json()

    assert body["state"] == "compared"
    assert (body["plan"]["plan_date"], body["previous"]["plan_date"]) == ("2026-10-09", "2026-03-05")
    assert body["counts"] == {"added": 0, "dropped": 0, "redated": 0, "reestimated": 2}
    assert (body["added"], body["dropped"], body["redated"]) == ([], [], [])
    found = {row["activity_reference_no"]: (row["was"], row["now"], row["change"], row["direction"])
             for row in body["reestimated"]}
    # values.toml quotes each estimate from page 3 of each version.
    assert found == {
        "KE-NWWDA-541055-CW-RFB": (f"{ground_truth('plan-541055-estimated-2026-03-05'):.2f}",
                                   f"{ground_truth('plan-541055-estimated'):.2f}", "30000.00", "more"),
        "KE-NWWDA-541062-CW-RFQ": (f"{ground_truth('plan-541062-estimated-2026-03-05'):.2f}",
                                   f"{ground_truth('plan-541062-estimated'):.2f}", "15000.00", "more"),
    }

    # A direct comparison of the two versions' rows, as the ticket asks: the same references, and only
    # these two estimates and no planned date differ between them.
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        rows = engine.run(
            "SELECT coalesce(a.activity_reference_no, b.activity_reference_no), a.estimated_amount_usd, "
            "b.estimated_amount_usd FROM (SELECT * FROM strata.silver.plan_rows WHERE document_id = :was) AS a "
            "FULL OUTER JOIN (SELECT * FROM strata.silver.plan_rows WHERE document_id = :now) AS b "
            "ON a.activity_reference_no = b.activity_reference_no", {"was": "40090127", "now": "40132287"}).rows
        steps = engine.run(
            "SELECT count(*) FROM strata.silver.plan_steps AS a JOIN strata.silver.plan_steps AS b "
            "ON a.activity_reference_no = b.activity_reference_no AND a.step = b.step "
            "WHERE a.document_id = :was AND b.document_id = :now AND a.planned_on IS DISTINCT FROM b.planned_on",
            {"was": "40090127", "now": "40132287"}).rows
    assert all(was is not None and now is not None for _, was, now in rows)
    assert sorted(ref for ref, was, now in rows if was != now) == sorted(found)
    assert steps[0][0] == 0


def plan_series(tmp_path):
    """Versions of a hand-written plan, as ticket 08's test writes them, since no recorded plan adds, drops
    or re-dates an activity; and a last one whose version before it was listed but not read."""
    database = tmp_path / "series.duckdb"
    agency = "Test Water Agency"
    versions = [("D1", "2026-01-10", 1, None, "first listing"), ("D2", "2026-02-10", 2, "D1", "the version before"),
                ("D9", "2026-02-20", 3, "D2", None), ("D3", "2026-03-10", 4, "D9", "the latest")]
    rows = [("D1", "A", "100.00"), ("D1", "B", "200.00"), ("D1", "C", "300.00"), ("D1", "E", None),
            ("D2", "A", "150.00"), ("D2", "B", "200.00"), ("D2", "D", "400.00"), ("D2", "E", "50.00"),
            ("D3", "A", "150.00")]
    steps = [("D1", "A", "Signed Contract", 4, "2026-05-01"), ("D1", "A", "Contract Completion", 5, "2026-08-01"),
             ("D1", "B", "Signed Contract", 4, "2026-06-01"), ("D1", "B", "Contract Completion", 5, None),
             ("D2", "A", "Signed Contract", 4, "2026-05-21"), ("D2", "A", "Contract Completion", 5, "2026-08-01"),
             ("D2", "B", "Signed Contract", 4, None), ("D2", "B", "Contract Completion", 5, "2026-09-01"),
             ("D3", "A", "Signed Contract", 4, "2026-05-21"), ("D3", "A", "Contract Completion", 5, "2026-08-11")]
    public = {doc: day for doc, day, *_ in versions}
    with DuckDBEngine.open(database) as engine:
        catalog.build(engine)
        engine.insert_rows(
            "strata.silver.plan_versions",
            ("document_id", "project_id", "implementing_agency", "plan_date", "disclosed_on", "series_order",
             "previous_document_id", "is_latest", "pdf_pages", "route_b_pages", "parse_reason", "text_url", "pdf_url",
             "public_from"),
            [(doc, "P000001", agency, day, day, order, before, doc == "D3", 3, 1, reason, f"https://t/{doc}.txt",
              f"https://t/{doc}.pdf", day) for doc, day, order, before, reason in versions])
        engine.insert_rows(
            "strata.silver.plan_rows",
            ("document_id", "project_id", "section", "activity_reference_no", "description", "method",
             "market_approach", "estimated_amount_usd", "process_status", "pdf_page", "parser", "public_from"),
            [(doc, "P000001", "WORKS", f"KE-T-{ref}", f"Works {ref}", "Request for Bids", "Open - National", amount,
              "Pending Implementation", 3, "test", public[doc]) for doc, ref, amount in rows])
        engine.insert_rows(
            "strata.silver.plan_steps",
            ("document_id", "project_id", "activity_reference_no", "step", "step_order", "planned_on", "public_from"),
            [(doc, "P000001", f"KE-T-{ref}", step, order, day, public[doc]) for doc, ref, step, order, day in steps])
    return database


SERIES = "/api/projects/P000001/procurement/test-water-agency"


def test_a_version_lists_the_activities_it_added_dropped_re_dated_and_re_estimated(tmp_path):
    body = get(app_on(plan_series(tmp_path)), f"{SERIES}/2026-02-10/changes").json()

    assert body["state"] == "compared"
    assert body["counts"] == {"added": 1, "dropped": 1, "redated": 2, "reestimated": 1}
    assert [row["activity_reference_no"] for row in body["added"]] == ["KE-T-D"]
    assert body["added"][0]["estimated_amount_usd"] == "400.00"
    assert [row["activity_reference_no"] for row in body["dropped"]] == ["KE-T-C"]
    redated = {row["activity_reference_no"]: row["steps"] for row in body["redated"]}
    # A date moved 20 days later, and a date the new version takes away; a date it gives for the first
    # time is not a re-dating.
    assert redated == {
        "KE-T-A": [{"step": "Signed Contract", "was": "2026-05-01", "now": "2026-05-21", "days": 20,
                    "direction": "later"}],
        "KE-T-B": [{"step": "Signed Contract", "was": "2026-06-01", "now": None, "days": None, "direction": None}],
    }
    # An estimate the new version gives for the first time is not a re-estimate.
    assert [(row["activity_reference_no"], row["was"], row["now"], row["change"], row["direction"])
            for row in body["reestimated"]] == [("KE-T-A", "100.00", "150.00", "50.00", "more")]


def test_the_earliest_version_and_a_version_after_one_not_read_say_why_they_list_no_changes(tmp_path):
    app = app_on(plan_series(tmp_path))

    earliest = get(app, f"{SERIES}/2026-01-10/changes").json()
    assert (earliest["state"], earliest["previous"], earliest["counts"]) == ("earliest", None, None)

    unread = get(app, f"{SERIES}/2026-03-10/changes").json()
    assert (unread["state"], unread["previous"]["plan_date"], unread["counts"]) == (
        "previous_not_read", "2026-02-20", None)

    assert get(app, f"{SERIES}/2026-04-01/changes").status_code == 404


# ── The baseline ─────────────────────────────────────────────────────────

NWWDA = "/api/projects/P156634/procurement/northern-water-works-development-agency"
REASONS = {"KE-NWWDA-229129-CW-RFB": "signed_late_over_estimate", "KE-NWWDA-541055-CW-RFB": "completion_passed_no_contract"}


@pytest.fixture
def writable(fixture_db, tmp_path):
    """A copy of the fixture database the test may write to. In it, the agency's plan of July 21, 2025 plans
    KE-NWWDA-229129-CW-RFB's signing for August 1, 2021, a re-dating written by hand, since no recorded
    version moves a planned date: so the baseline's delay differs from the delay from the first published
    planned date, July 1, 2021 (values.toml, plan-229129-first-planned-signing)."""
    database = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, database)
    with DuckDBEngine.open(database) as engine:
        engine.run("UPDATE strata.silver.plan_steps SET planned_on = DATE '2021-08-01' WHERE document_id = :doc "
                   "AND activity_reference_no = :ref AND step = :step",
                   {"doc": "40031468", "ref": "KE-NWWDA-229129-CW-RFB", "step": "Signed Contract"})
    return app_on(database, read_only=False)


def reasons(check):
    return {row["activity_reference_no"]: reason for row in check["rows"] for mark in row["marks"]
            for reason in mark["reasons"] if reason["code"] == REASONS.get(row["activity_reference_no"])}


def test_a_check_after_saving_the_baseline_gives_delay_from_the_baseline_and_from_the_first_published_date(writable):
    saved = call(writable, "PUT", f"{NWWDA}/baseline", body={"plan_date": "2025-07-21"})

    assert saved.status_code == 200
    assert saved.json()["baseline"] == {
        "plan_date": "2025-07-21", "document_id": "40031468", "saved_by": "Ana Example", "saved_on": "2026-10-23",
        "evidence_id": "strata.ops.plan_baselines:P156634/northern-water-works-development-agency",
        "public_from": "2026-10-23"}

    check = get(writable, f"{NWWDA}/2026-10-09?asof=2026-10-23").json()
    assert check["baseline"]["plan_date"] == "2025-07-21"
    found = reasons(check)
    signed = found["KE-NWWDA-229129-CW-RFB"]
    # 186 days from the first published planned date (values.toml, plan-229129-days-late), and 155 days
    # from August 1, 2021, the baseline's date, to the signing on January 3, 2022 (plan-229129-signed).
    assert signed["days_late"] == 186
    assert signed["baseline"] == {"state": "late", "planned_on": "2021-08-01", "days": 155, "plan_date": "2025-07-21"}
    # The plan of March 5, 2026 first listed KE-NWWDA-541055-CW-RFB, after the baseline.
    assert found["KE-NWWDA-541055-CW-RFB"]["baseline"] == {
        "state": "not_in_baseline", "planned_on": None, "days": None, "plan_date": "2025-07-21"}

    # The Procurement tab marks the baseline among the agency's versions.
    page = get(writable, "/api/projects/P156634?asof=2026-10-23").json()
    nwwda = next(agency for agency in page["agencies"] if agency["agency_id"] == "northern-water-works-development-agency")
    assert nwwda["baseline"]["plan_date"] == "2025-07-21"
    assert [version["plan_date"] for version in nwwda["versions"] if version["is_baseline"]] == ["2025-07-21"]


def test_the_baseline_shows_without_its_saver_to_an_agency_and_not_to_the_public_or_before_it_was_saved(writable):
    call(writable, "PUT", f"{NWWDA}/baseline", body={"plan_date": "2025-07-21"})

    agency = get(writable, f"{NWWDA}/2026-10-09?asof=2026-10-23&view=piu").json()
    assert (agency["baseline"]["plan_date"], agency["baseline"]["saved_by"]) == ("2025-07-21", None)
    public = get(writable, f"{NWWDA}/2026-10-09?asof=2026-10-23&view=public").json()
    assert public["baseline"] is None and all("baseline" not in reason for reason in reasons(public).values())
    before = get(writable, f"{NWWDA}/2026-10-09?asof=2026-10-22").json()
    assert before["baseline"] is None


def test_removing_the_baseline_leaves_delay_from_the_first_published_date_alone(writable):
    call(writable, "PUT", f"{NWWDA}/baseline", body={"plan_date": "2025-07-21"})
    removed = call(writable, "DELETE", f"{NWWDA}/baseline")

    assert (removed.status_code, removed.json()) == (200, {"baseline": None})
    check = get(writable, f"{NWWDA}/2026-10-09?asof=2026-10-23").json()
    assert check["baseline"] is None
    assert "baseline" not in reasons(check)["KE-NWWDA-229129-CW-RFB"]


def test_only_a_signed_in_viewer_in_the_staff_view_can_save_a_read_version_as_the_baseline(writable):
    preview = call(writable, "PUT", f"{NWWDA}/baseline?view=piu", body={"plan_date": "2025-07-21"})
    assert (preview.status_code, preview.json()) == (403, {"code": "preview"})
    nobody = call(writable, "PUT", f"{NWWDA}/baseline", headers={}, body={"plan_date": "2025-07-21"})
    assert (nobody.status_code, nobody.json()) == (401, {"code": "no_identity"})
    unknown = call(writable, "PUT", f"{NWWDA}/baseline", body={"plan_date": "2024-01-01"})
    assert (unknown.status_code, unknown.json()) == (404, {"code": "unknown_plan"})
    assert get(writable, f"{NWWDA}/2026-10-09?asof=2026-10-23").json()["baseline"] is None


# ── The recordings the screen tests serve ────────────────────────────────

def recorder():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("record_api", Path(__file__).parent / "record_api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECORDER = recorder()
RECORDED = RECORDER.OUT


def recorded(name):
    import json

    return json.loads((RECORDED / name).read_text())


@pytest.mark.parametrize("name", sorted(RECORDER.HUB))
def test_each_project_page_recording_is_what_the_server_answers_on_the_fixture(hub, name):
    assert get(hub, RECORDER.HUB[name]).json() == recorded(name)


def test_the_baseline_recordings_are_what_the_server_answers_after_ana_saves_it(fixture_db, tmp_path):
    database, saved = RECORDER.with_baseline(tmp_path, fixture_db)

    assert saved == recorded("baseline-saved.json")
    app = app_on(database)
    for name, path in RECORDER.BASELINE.items():
        assert get(app, path).json() == recorded(name), name


def test_the_recorded_model_routes_are_the_routes_the_server_tags_as_calling_a_model():
    from strata.server.app import model_routes

    routes = model_routes(create_app(engine_for=None))
    assert {"method": "POST", "path": "/api/ask"} in routes
    assert recorded("model-routes.json") == {"routes": routes}
