"""Plan text read from a PDF is repaired (ticket 131): a reference that breaks STEP's form and a word the PDF split
with a space are fixed only where the project's notices or its other plan rows show what the plan says, and the
text as read stays beside the repaired text.

The Kenya rows are the ones the App showed for P156634's plan of October 9, 2026 and P161305's plans on October 29,
2026 (ticket 131): KE-NWWDA-193461-90-RF8 is the layout parser's reading on the workspace, and the descriptions are
as the screens printed them. The notices are the fixture's recorded notices for P156634.
"""

import asyncio
import json
from contextlib import contextmanager
from pathlib import Path

import httpx

from strata.lakehouse.engine import DuckDBEngine
from strata.reader import repair
from strata.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
NOTICES = ROOT / "data" / "fixture" / "recorded" / "api" / "notices" / "P156634.json"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
PLAN_SLUG = "procurement-plan-northern-water-works-development-agency-2026-10-09"  # the source view's address


def kenya_notices() -> list[repair.Notice]:
    """P156634's recorded notices, as silver.notices holds them: each one's id, reference and title."""
    records = json.loads(NOTICES.read_text())["response"]["procnotices"]
    return [repair.Notice(record["id"], record.get("bid_reference_no"), record.get("bid_description"))
            for record in records]


def test_a_reference_one_look_alike_swap_from_a_notices_reference_takes_the_notices_reference():
    notices = [repair.Notice("OP00999999", "KE-NWWDA-193461-GO-RFQ", "Supply of a vehicle")]
    found = repair.reference("KE-NWWDA-193461-G0-RFQ", repair.carried(notices))
    assert (found.written, found.as_read, found.repair, found.carried_by) == (
        "KE-NWWDA-193461-GO-RFQ", "KE-NWWDA-193461-G0-RFQ", "look_alike", "strata.silver.notices:OP00999999")


def test_the_kenya_reference_stays_as_read_and_is_flagged_when_no_record_carries_a_one_swap_repair():
    # The notices carry KE-NWWDA-199461-GO-RFB, the reference the plan's own text gives, but no one swap reaches it.
    found = repair.reference("KE-NWWDA-193461-90-RF8", repair.carried(kenya_notices()))
    assert (found.written, found.as_read, found.repair, found.carried_by) == (
        "KE-NWWDA-193461-90-RF8", "KE-NWWDA-193461-90-RF8", "reference_as_read", None)
    # A notice that carried KE-NWWDA-193461-GO-RFQ would not change it either: its kind 90 and its method RF8 both
    # break STEP's grammar, and the repair makes one swap, never three.
    with_it = repair.carried([*kenya_notices(), repair.Notice("OP00999999", "KE-NWWDA-193461-GO-RFQ", None)])
    assert repair.reference("KE-NWWDA-193461-90-RF8", with_it).repair == "reference_as_read"


def test_a_one_swap_repair_that_no_record_carries_is_not_made():
    found = repair.reference("KE-NWWDA-193461-G0-RFQ", repair.carried(kenya_notices()))
    assert (found.written, found.repair) == ("KE-NWWDA-193461-G0-RFQ", "reference_as_read")


def test_a_reference_in_steps_grammar_or_in_an_older_form_is_kept_and_one_a_notice_carries_as_read_is_flagged():
    records = repair.carried([*kenya_notices(), repair.Notice("OP00999998", "KE-NWWDA-541055-CW-RF8", None)])
    for read in ("KE-NWWDA-541055-CW-RFB", "KE-SDOR-KIHBT-563865-CW-RFB", "KE-WSTF-430946-GO-RFB-NCWSC02",
                 "NWWDA-WSDP-03-2019-2020", "MWI-WSDP-001"):
        found = repair.reference(read, records)
        assert (found.written, found.repair) == (read, None), read
    # A notice that writes the broken form keeps the row's reference as read, since STEP holds it so.
    found = repair.reference("KE-NWWDA-541055-CW-RF8", records)
    assert (found.written, found.repair, found.carried_by) == (
        "KE-NWWDA-541055-CW-RF8", "reference_as_read", "strata.silver.notices:OP00999998")


def notice_words() -> frozenset[str]:
    return repair.words(notice.title for notice in kenya_notices())


def test_the_kenya_descriptions_are_joined_where_the_notices_or_the_plans_other_rows_write_the_word_whole():
    # P156634's notices write "Boreholes" and "Sarman" (OP00474946's title), and "Nairobi" (OP00363732's).
    found = repair.description("Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n - Tarbaj Water Supply",
                               notice_words(), frozenset())
    assert found.written == "Equipping of Exploratory Boreholes Project-Lot 1- Sarman - Tarbaj Water Supply"
    assert found.as_read == "Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n - Tarbaj Water Supply"
    assert [(j.read, j.joined, j.found_in) for j in found.joins] == [
        ("Bo reholes", "Boreholes", "notices"), ("Sarma n", "Sarman", "notices")]
    assert repair.description("Kenya Institute of Highways and Building Technology (KIHBT), Nair obi Campus",
                              notice_words(), frozenset()).written == (
        "Kenya Institute of Highways and Building Technology (KIHBT), Nairobi Campus")
    # "Roads" and "Boardroom" are in no P156634 notice's title; the plan's other rows write them whole. The first is
    # P161305's recorded row KE-KENHA-346181-CS-QCBS; the second is this test's own row.
    other_rows = repair.words(["Consultancy Services for Co nstruction Supervision of bri dges including approach and "
                               "access roads at Rhamu and Mandera", "Supply of 24 No. Boardroom Chairs"])
    roads = repair.description("State Department of R oads Division", notice_words(), other_rows)
    assert (roads.written, [(j.read, j.joined, j.found_in) for j in roads.joins]) == (
        "State Department of Roads Division", [("R oads", "Roads", "plan")])
    assert repair.description("Refurbishment of the Boardro om", notice_words(), other_rows).written == (
        "Refurbishment of the Boardroom")


def test_a_split_word_that_no_notice_or_other_row_writes_whole_stays_as_read():
    # Without a notice or another row that writes "Sarman", "Sarma n" stays: it could be two words.
    without = notice_words() - {"sarman"}
    found = repair.description("Equipping of Exploratory Boreholes Project-Lot 1- Sarma n - Tarbaj Water Supply",
                               without, frozenset())
    assert (found.written, found.joins) == (
        "Equipping of Exploratory Boreholes Project-Lot 1- Sarma n - Tarbaj Water Supply", ())


def test_two_words_the_notices_use_on_their_own_are_not_joined():
    # P156634's notices write "Motor", "Cycles", "in" and "to" on their own; the other rows write the joined words.
    found = repair.description("Supply of Motor Cycles in to the counties", notice_words(),
                               repair.words(["Supply of 3 Motorcycles", "Delivery into stores"]))
    assert (found.written, found.joins) == ("Supply of Motor Cycles in to the counties", ())


def test_the_fixtures_plan_rows_keep_the_text_as_read_beside_the_repaired_text(fixture_db):
    # P156634's plan of October 9, 2026 (document 40132287), as the plan reader wrote it after the lakehouse run filled
    # silver.notices: "Nurgows" is in notice OP00456907's title and in no row of the plan.
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        rows = {row[0]: row[1:] for row in engine.run(
            "SELECT activity_reference_no, description, description_as_read, description_joins, "
            "activity_reference_no_as_read, reference_repair FROM strata.silver.plan_rows "
            "WHERE document_id = :document_id", {"document_id": "40132287"}).rows}
    description, as_read, joins, reference_as_read, reference_repair = rows["KE-NWWDA-541055-CW-RFB"]
    assert description == "Equipping of Exploratory Boreholes Project-Lot 1- Sarman - Tarbaj Water Supply"
    assert as_read == "Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n - Tarbaj Water Supply"
    assert json.loads(joins) == [{"read": "Bo reholes", "joined": "Boreholes", "found_in": "notices"},
                                 {"read": "Sarma n", "joined": "Sarman", "found_in": "notices"}]
    assert (reference_as_read, reference_repair) == ("KE-NWWDA-541055-CW-RFB", None)
    assert rows["KE-NWWDA-541061-CW-RFQ"][0] == "Equipping of Exploratory Boreholes Project - Lot 2- Nurgows Water Supply"
    # Every reference the fixture's plan reads is in STEP's grammar or in an older form: none is repaired or flagged.
    assert {row[4] for row in rows.values()} == {None}


def server_on(database: Path):
    """GET on the App's server over a database, as Ana, read-only: the answer as JSON."""
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=engine_for)

    def get(path: str) -> dict:
        async def go():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
                return await client.get(path, headers=ANA)
        response = asyncio.run(go())
        assert response.status_code == 200, (path, response.text)
        return response.json()

    return get


def test_the_plan_check_shows_the_repaired_text_and_the_source_view_and_the_drawer_show_the_pages_words(fixture_db):
    get = server_on(fixture_db)
    as_read = "Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n - Tarbaj Water Supply"
    repaired = "Equipping of Exploratory Boreholes Project-Lot 1- Sarman - Tarbaj Water Supply"
    checked = get("/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09?asof=2026-10-23")
    [row] = [row for row in checked["rows"] if row["activity_reference_no"] == "KE-NWWDA-541055-CW-RFB"]
    assert (row["description"], row["reference_as_read"]) == (repaired, False)
    package = get("/api/packages/KE-NWWDA-541055-CW-RFB?asof=2026-10-23")["package"]
    assert (package["description"], package["reference_as_read"]) == (repaired, False)

    source = get(f"/api/projects/P156634/documents/{PLAN_SLUG}?page={row['source']['pdf_page']}&asof=2026-10-23")
    assert [plan_row["description"] for plan_row in source["plan_rows"]
            if plan_row["activity_reference_no"] == "KE-NWWDA-541055-CW-RFB"] == [as_read]
    drawer = get("/api/evidence?id=strata.silver.plan_rows:40132287/KE-NWWDA-541055-CW-RFB&asof=2026-10-23")
    assert [field["value"] for field in drawer["row"]["fields"] if field["key"] == "description"] == [as_read]


def test_the_workspaces_misread_reference_is_kept_as_read_and_the_plan_check_and_package_page_say_so(fixture_db,
                                                                                                   tmp_path):
    """On the workspace, the layout parser read KE-NWWDA-199461-GO-RFB (the plan's text and notice OP00147052) as
    KE-NWWDA-193461-90-RF8. The reader's settling (ticket 78) allows two characters and this is four, and no one
    look-alike swap makes it whole, so the row keeps it as read, flagged, and the pages say so."""
    from strata.lakehouse import plans

    copy = tmp_path / "fixture.duckdb"
    copy.write_bytes(fixture_db.read_bytes())
    with DuckDBEngine.open(copy) as engine:
        engine.run("UPDATE strata.bronze.layout_pages SET tables = replace(tables, :read_well, :misread) "
                   "WHERE document_id = :document_id",
                   {"read_well": "KE-NWWDA-199461-GO-RFB", "misread": MISREAD, "document_id": "40132287"})
        plans.rewrite(engine, "P156634")
        [flagged] = engine.run("SELECT activity_reference_no, activity_reference_no_as_read, reference_repair, "
                               "description FROM strata.silver.plan_rows WHERE document_id = :document_id "
                               "AND activity_reference_no_as_read = :misread",
                               {"document_id": "40132287", "misread": MISREAD}).rows
    assert flagged == (MISREAD, MISREAD, "reference_as_read",
                       "Supply and Delivery 1 No. 4 x 4 Wheel drive, manual transmission of engine capacity 4,100 - "
                       "4,200 cc")

    get = server_on(copy)
    checked = get("/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09?asof=2026-10-23")
    assert {row["activity_reference_no"]: row["reference_as_read"] for row in checked["rows"]}[MISREAD] is True
    assert sum(row["reference_as_read"] for row in checked["rows"]) == 1
    assert get(f"/api/packages/{MISREAD}?asof=2026-10-23")["package"]["reference_as_read"] is True


MISREAD = "KE-NWWDA-193461-90-RF8"  # what ai_parse_document read on the workspace (ticket 131)
