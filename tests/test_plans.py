"""P156634's Procurement Plans read into STEP rows: seam 1, the lakehouse run over the fixture.

The gate builds the fixture database by running the plan reader over the recorded plans
(gates/build_fixture.py), so most tests read what that run wrote. Every value quoted from a plan
comes from tests/ground_truth/values.toml, which quotes the plans with their PDF pages, never from
Strata's code. The cap test's stopping page follows from how many table pages each recorded plan has.
"""

import datetime as dt
import re
import tomllib
from decimal import Decimal
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
NWWDA = "Northern Water Works Development Agency"
DEMO_PLAN = dt.date(2026, 10, 9)


def value(key: str) -> dict:
    return next(entry for entry in GROUND_TRUTH["value"] if entry["id"] == key)


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", ""))


def squash(text: str) -> str:
    """values.toml's quotes match ignoring whitespace, because a PDF cell drops the space where it wraps."""
    return re.sub(r"\s+", "", text)


@pytest.fixture(scope="module")
def db(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


DEMO_ROWS = """
SELECT r.*
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
WHERE v.implementing_agency = :agency AND v.plan_date = :plan_date
"""


def test_the_october_9_plans_eight_activities_match_the_check_a_plan_wireframe(db):
    found = {row["activity_reference_no"]: row for row in rows(db, DEMO_ROWS, agency=NWWDA, plan_date=DEMO_PLAN)}

    expected = GROUND_TRUTH["plan_row"]
    assert len(expected) == 8
    assert set(found) == {row["reference"] for row in expected} | set(GROUND_TRUTH["plan"]["also_lists"])
    for row in expected:
        got = found[row["reference"]]
        assert squash(got["description"]) == squash(row["description"]), row["reference"]
        assert (got["method"], got["market_approach"], got["review_type"], got["process_status"]) == (
            row["method"], row["market_approach"], row["review_type"], row["process_status"]), row["reference"]
        assert got["estimated_amount_usd"] == amount(row["estimated_amount_usd"]), row["reference"]
        assert got["actual_amount_usd"] == amount(row["actual_amount_usd"]), row["reference"]
        assert got["pdf_page"] == GROUND_TRUTH["plan"]["pdf_page"]


DEMO_STEP = """
SELECT d.*, r.actual_amount_usd, r.process_status
FROM strata.silver.plan_step_delays AS d
JOIN strata.silver.plan_versions AS v ON v.document_id = d.document_id
JOIN strata.silver.plan_rows AS r
  ON r.document_id = d.document_id AND r.activity_reference_no = d.activity_reference_no
WHERE v.implementing_agency = :agency AND v.plan_date = :plan_date
  AND d.activity_reference_no = :reference AND d.step = :step
"""


def demo_step(engine, reference: str, step: str) -> dict:
    found = rows(engine, DEMO_STEP, agency=NWWDA, plan_date=DEMO_PLAN, reference=reference, step=step)
    assert len(found) == 1, (reference, step)
    return found[0]


def test_ke_nwwda_229129_was_signed_186_days_after_its_first_published_planned_date(db):
    signed = demo_step(db, "KE-NWWDA-229129-CW-RFB", "Signed Contract")

    first = value("plan-229129-first-planned-signing")
    assert signed["actual_on"] == value("plan-229129-signed")["value"]
    assert (signed["first_planned_on"], signed["first_planned_plan_date"]) == (first["value"], first["date"])
    assert signed["delay_days"] == value("plan-229129-days-late")["value"]
    assert signed["actual_amount_usd"] == Decimal(str(value("plan-229129-actual")["value"]))


def measured(engine, run_id: str | None = None, subject: str = "P156634") -> dict:
    """Each data readiness measure of a plan run for the project (the latest when run_id is None), as
    (count, denominator). The nightly job writes its own sources' measures to the same table, and the
    passage reader writes the documents source's too, so a plan run is one that measured the plan
    versions it read. The fixture's plan reader also reads the stress shelf's plan, for P161305."""
    found = rows(engine, """
        SELECT run_id, measure, count, denominator FROM strata.ops.data_readiness WHERE source = 'documents'
          AND subject = :subject
          AND run_id IN (SELECT run_id FROM strata.ops.data_readiness WHERE measure = 'plan_versions_read')
        ORDER BY measured_at""", subject=subject)
    run_id = run_id or found[-1]["run_id"]
    return {r["measure"]: (r["count"], r["denominator"]) for r in found if r["run_id"] == run_id}


def test_older_listed_versions_the_fixture_never_recorded_leave_each_first_listing_unconfirmed(db):
    """The documents API lists far more plan versions than the fixture records, many of them older
    than the version that first lists each activity here. Delay is still measured from that version,
    and the row says its first listing is not confirmed."""
    signed = demo_step(db, "KE-NWWDA-229129-CW-RFB", "Signed Contract")
    count, denominator = measured(db)["latest_activities_with_confirmed_first_listing_read"]

    assert signed["delay_days"] == value("plan-229129-days-late")["value"]
    assert signed["first_listing_confirmed"] is False
    assert count == 0 < denominator


def test_ke_nwwda_541055_plans_completion_on_july_31_2026_and_shows_no_signed_contract(db):
    completion = demo_step(db, "KE-NWWDA-541055-CW-RFB", "Contract Completion")
    signed = demo_step(db, "KE-NWWDA-541055-CW-RFB", "Signed Contract")

    assert completion["planned_on"] == value("plan-541055-planned-completion")["value"]
    assert signed["actual_on"] is None and signed["delay_days"] is None
    assert signed["process_status"] == value("plan-541055-status")["value"]


def test_the_october_9_plan_has_a_data_note_for_the_method_and_for_each_actual_amount_of_zero(db):
    notes = rows(db, """
        SELECT n.activity_reference_no, n.note, n.reference_method_code, n.method, n.actual_amount_usd
        FROM strata.silver.plan_data_notes AS n
        JOIN strata.silver.plan_versions AS v ON v.document_id = n.document_id
        WHERE v.implementing_agency = :agency AND v.plan_date = :plan_date
        ORDER BY n.activity_reference_no""", agency=NWWDA, plan_date=DEMO_PLAN)

    zero = Decimal(str(value("plan-503455-actual-zero")["value"]))
    assert [(n["activity_reference_no"], n["note"]) for n in notes] == [
        ("KE-NWWDA-199461-GO-RFB", "method_differs_from_reference"),
        ("KE-NWWDA-503455-CW-RFQ", "actual_amount_zero"),
        ("KE-NWWDA-541061-CW-RFQ", "actual_amount_zero"),
    ]
    assert (notes[0]["reference_method_code"], notes[0]["method"]) == (
        value("plan-199461-reference-method")["value"], value("plan-199461-method-column")["value"])
    assert notes[1]["actual_amount_usd"] == notes[2]["actual_amount_usd"] == zero


def test_each_method_the_method_note_names_is_one_of_steps_methods_word_for_word():
    """A misspelt method in the note's list would quietly stop the note for that method."""
    from strata.lakehouse import plans
    from strata.reader import step

    listed = re.findall(r"\('([A-Z]+)', '([^']+)'\)", plans._sql("plan_data_notes.sql"))

    assert ("RFB", "Request for Bids") in listed
    assert {method for _, method in listed} <= set(step.VALUES["method"])


RECORDED = ROOT / "data" / "fixture" / "recorded" / "documents"
PLAN_TEXTS = sorted(RECORDED.glob("*/procurement-plan-*.txt"))  # each plan's text and its page texts
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@pytest.mark.parametrize("file", PLAN_TEXTS, ids=lambda file: file.name)
def test_taking_contact_details_out_of_a_procurement_plan_keeps_every_step_reference_and_date(file):
    """A plan's table runs a date in one column into the next column's digits, and cuts a reference at
    a column's edge, so a run of digits there is no phone number. Bronze keeps the plan as published."""
    from strata.lakehouse import contacts
    from strata.reader import step

    published = file.read_text()

    kept, removed = contacts.strip_text(published)

    assert (kept, removed) == (published, 0)
    assert step.references_in(kept) == step.references_in(published)
    assert DATE.findall(kept) == DATE.findall(published)


def test_bronze_keeps_every_procurement_plan_as_published_and_the_demo_plan_lists_the_wajir_consultancy(db):
    marked = rows(db, """
        SELECT count(*) AS n FROM strata.bronze.document_texts AS t
        WHERE t.document_id IN (SELECT document_id FROM strata.silver.plan_versions)
          AND (t.text LIKE '%contact removed%' OR EXISTS (
            SELECT 1 FROM strata.bronze.document_pages AS p
            WHERE p.document_id = t.document_id AND p.text LIKE '%contact removed%'))""")
    listed = rows(db, """
        SELECT l.activity_reference_no FROM strata.silver.plan_listings AS l
        JOIN strata.silver.plan_versions AS v ON v.document_id = l.document_id
        WHERE v.implementing_agency = :agency AND v.plan_date = :plan_date""", agency=NWWDA, plan_date=DEMO_PLAN)

    assert marked == [{"n": 0}]
    assert value("plan-wsdp-03-first-listed")["first_lists"] in {row["activity_reference_no"] for row in listed}


def test_each_plan_version_is_public_from_its_disclosure_date_and_in_its_agencys_series(db):
    versions = rows(db, """
        SELECT plan_date, implementing_agency, series_order, is_latest, public_from
        FROM strata.silver.plan_versions WHERE implementing_agency = :agency ORDER BY plan_date""", agency=NWWDA)

    first_listed = [value("plan-229129-first-planned-signing")["date"], value("plan-541055-first-listed")["value"]]
    assert all(v["public_from"] == v["plan_date"] for v in versions)  # each was disclosed on its own date
    assert set(first_listed) <= {v["plan_date"] for v in versions}
    assert [v["series_order"] for v in versions] == list(range(1, len(versions) + 1))
    assert [v["is_latest"] for v in versions] == [False] * (len(versions) - 1) + [True]
    assert versions[-1]["plan_date"] == DEMO_PLAN


# ── Runs on a fresh database: each page parsed once, under the daily page cap ──

def clock(day: dt.date):
    """A clock that starts at noon UTC on a day and moves a second each time it is read. A test moves
    it to another day through now.state["day"]."""
    state = {"day": day, "ticks": 0}

    def now():
        state["ticks"] += 1
        return dt.datetime.combine(state["day"], dt.time(12), dt.UTC) + dt.timedelta(seconds=state["ticks"])

    now.state = state
    return now


@pytest.fixture
def fresh():
    from strata.lakehouse import catalog

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


def plan_run(engine, now, thresholds=None):
    from strata.lakehouse import plans

    return plans.run_on_fixture(engine, "P156634", clock=now, **({"thresholds": thresholds} if thresholds else {}))


def counts(engine) -> dict:
    tables = ("bronze.document_lists", "bronze.document_texts", "bronze.document_pages", "bronze.layout_pages")
    return {table: engine.run(f"SELECT count(*) AS n FROM strata.{table}").rows[0][0] for table in tables}


def test_a_second_run_parses_no_new_pages_and_strata_ops_shows_the_pages_read_by_each_route(fresh):
    now = clock(dt.date(2026, 10, 23))
    first = plan_run(fresh, now)
    before = counts(fresh)
    second = plan_run(fresh, now)

    assert counts(fresh) == before  # nothing fetched twice, and no page parsed twice
    runs = rows(fresh, "SELECT run_id, pages_parsed, stopped_at_cap FROM strata.ops.parse_runs ORDER BY started_at")
    assert [(r["run_id"], r["pages_parsed"], r["stopped_at_cap"]) for r in runs] == [
        (first.run_id, before["bronze.layout_pages"], False), (second.run_id, 0, False)]
    found = measured(fresh, second.run_id)
    route_a, route_b = found["pages_read_route_a"], found["pages_read_route_b"]
    assert route_b[0] == route_b[1] == before["bronze.layout_pages"] > 0
    assert route_a[0] == route_a[1] > 0  # every page left to Route A has text
    assert route_a[1] + route_b[1] == before["bronze.document_pages"]


def test_the_step_reader_finds_a_reference_in_every_table_row_and_knows_every_column(fresh):
    report = plan_run(fresh, clock(dt.date(2026, 10, 23)))

    count, denominator = measured(fresh, report.run_id)["step_rows_with_reference"]
    assert count == denominator > 0
    assert report.unknown_columns == ()


class OnlyRecordedPlans:
    """The recorded documents, with a document list that names only the Procurement Plans the fixture
    records, as if the documents API listed nothing older."""

    def __init__(self, manifest):
        from strata.reader.documents import RecordedDocuments
        from strata.reader.layout import https

        self.recorded = RecordedDocuments(manifest)
        self.texts = {https(source.text_url) for source in manifest.sources if source.kind == "document"}
        self.text, self.pages = self.recorded.text, self.recorded.pages

    def listing(self, url):
        from strata.reader.documents import Fetched
        from strata.reader.layout import https

        fetched = self.recorded.listing(url)
        kept = {key: document for key, document in fetched.body["documents"].items()
                if not isinstance(document, dict) or document.get("docty") != "Procurement Plan"
                or https(document.get("txturl", "")) in self.texts}
        return Fetched(url, {**fetched.body, "documents": kept}, fetched.fetched_at)


def test_when_every_listed_version_is_read_each_first_listing_is_confirmed(fresh):
    from strata.fixture import recorded as fmt
    from strata.lakehouse import plans
    from strata.reader.layout import RecordedLayout

    manifest = fmt.load_manifest()
    report = plans.run(fresh, OnlyRecordedPlans(manifest), RecordedLayout(manifest), "P156634",
                       clock=clock(dt.date(2026, 10, 23)))
    signed = demo_step(fresh, "KE-NWWDA-229129-CW-RFB", "Signed Contract")
    found = measured(fresh, report.run_id)

    versions, listed = found["plan_versions_read"]
    count, denominator = found["latest_activities_with_confirmed_first_listing_read"]
    assert versions == listed > 0
    assert count == denominator > 0
    assert signed["first_listing_confirmed"] is True
    assert signed["delay_days"] == value("plan-229129-days-late")["value"]


def cap(tmp_path, pages: int):
    from strata.config import CONFIG_DIR, load_thresholds

    text = (CONFIG_DIR / "thresholds.toml").read_text()
    assert "daily_page_cap = 500" in text
    path = tmp_path / "thresholds.toml"
    path.write_text(text.replace("daily_page_cap = 500", f"daily_page_cap = {pages}"))
    return load_thresholds(path)


def test_a_lower_daily_page_cap_stops_the_run_at_the_cap_and_records_where_it_stopped(fresh, tmp_path):
    now = clock(dt.date(2026, 10, 23))
    plan_run(fresh, now, cap(tmp_path, 4))
    plan_run(fresh, now, cap(tmp_path, 4))  # the same day: the cap is spent
    day_one = demo_step(fresh, "KE-NWWDA-229129-CW-RFB", "Signed Contract")
    now.state["day"] = dt.date(2026, 10, 24)
    plan_run(fresh, now, cap(tmp_path, 4))  # the next day: four more pages
    day_two = demo_step(fresh, "KE-NWWDA-229129-CW-RFB", "Signed Contract")

    runs = rows(fresh, """
        SELECT p.pages_parsed, p.parsed_earlier_today, p.stopped_at_cap, p.stopped_at_pdf_page, v.plan_date
        FROM strata.ops.parse_runs AS p
        LEFT JOIN strata.silver.plan_versions AS v ON v.document_id = p.stopped_at_document_id
        ORDER BY p.started_at""")
    # Newest versions first: October 9, August 17 and July 31, 2026 and March 5, 2026 fill day one,
    # so the run stops at page 3 of the July 21, 2025 plan; day two starts there.
    assert [(r["pages_parsed"], r["parsed_earlier_today"], r["stopped_at_cap"]) for r in runs] == [
        (4, 0, True), (0, 4, True), (4, 0, True)]
    assert (runs[0]["plan_date"], runs[0]["stopped_at_pdf_page"]) == (dt.date(2025, 7, 21), 3)
    assert runs[1]["plan_date"] == dt.date(2025, 7, 21)
    assert fresh.run("SELECT count(*) FROM strata.bronze.layout_pages").rows[0][0] == 8
    # On day one the plan that first lists KE-NWWDA-229129-CW-RFB, of April 21, 2021, waits, so its
    # delay stays empty rather than being measured from a later plan; on day two it is read.
    assert day_one["actual_on"] == value("plan-229129-signed")["value"]
    assert day_one["first_planned_on"] is None and day_one["delay_days"] is None
    assert day_two["delay_days"] == value("plan-229129-days-late")["value"]


class FirstPageFails:
    """The recorded layout parser, except that the first page it is given always fails, as a page
    ai_parse_document cannot read would. Pages go newest first, so that page heads every run's queue."""

    def __init__(self, manifest):
        from strata.reader.layout import RecordedLayout

        self.recorded = RecordedLayout(manifest)
        self.name = self.recorded.name
        self.tried, self.failing = [], None

    def parse(self, page):
        from strata.reader.layout import ParseFailed

        self.tried.append((page.document_id, page.pdf_page))
        self.failing = self.failing or self.tried[-1]
        if self.tried[-1] == self.failing:
            raise ParseFailed(f"ai_parse_document returned nothing for page {page.pdf_page}.")
        return self.recorded.parse(page)


def test_a_page_the_layout_parser_cannot_read_is_recorded_and_waits_for_the_next_day(fresh):
    from strata.fixture import recorded as fmt
    from strata.lakehouse import plans
    from strata.reader.documents import RecordedDocuments

    manifest = fmt.load_manifest()
    layout, now = FirstPageFails(manifest), clock(dt.date(2026, 10, 23))
    for day in (dt.date(2026, 10, 23), dt.date(2026, 10, 23), dt.date(2026, 10, 24)):
        now.state["day"] = day
        plans.run(fresh, RecordedDocuments(manifest), layout, "P156634", clock=now)

    runs = rows(fresh, """
        SELECT pages_parsed, pages_failed, first_failed_document_id, first_failed_pdf_page, parsed_earlier_today
        FROM strata.ops.parse_runs ORDER BY started_at""")
    tried_on_day_one = len(layout.tried) - 1
    assert [(r["pages_parsed"], r["pages_failed"]) for r in runs] == [(tried_on_day_one - 1, 1), (0, 0), (0, 1)]
    assert (runs[0]["first_failed_document_id"], runs[0]["first_failed_pdf_page"]) == layout.failing
    assert runs[1]["parsed_earlier_today"] == tried_on_day_one  # the failed attempt counts against the cap
    assert layout.tried[tried_on_day_one:] == [layout.failing]  # tried again only the next day
    assert fresh.run("SELECT count(*) FROM strata.ops.parse_failures").rows[0][0] == 2


LATER_PLAN = dt.date(2021, 12, 1)  # made up, like the re-dated step


@pytest.mark.parametrize("first_public_from, delay_public_from", [
    (dt.date(2021, 4, 21), LATER_PLAN),
    # Disclosed after the later plan (ticket 08's verification, F2): the delay row rests on the
    # first plan's date, so it cannot be public before that plan is.
    (dt.date(2021, 12, 15), dt.date(2021, 12, 15)),
], ids=["first-plan-disclosed-first", "first-plan-disclosed-after-the-later-one"])
def test_a_later_version_that_re_dates_a_step_does_not_move_its_first_published_planned_date(
        fresh, first_public_from, delay_public_from):
    """No recorded plan re-dates a step, so this test writes two versions of one activity by hand.
    The first plans the signed contract on the date the April 21, 2021 plan gives. The later one
    re-dates it to November 1, 2021, a made-up date, and shows the actual signing date. The delay
    row is public only once both plans are (ADR 0002)."""
    from strata.lakehouse import plans

    first, signed = value("plan-229129-first-planned-signing"), value("plan-229129-signed")["value"]
    later = LATER_PLAN
    reference, project = "KE-NWWDA-229129-CW-RFB", "P156634"
    plans.insert(fresh, "strata.silver.plan_versions",
                 ("document_id", "project_id", "implementing_agency", "plan_date", "series_order", "is_latest",
                  "pdf_pages", "route_b_pages", "text_url", "pdf_url", "public_from"),
                 [("first", project, NWWDA, first["date"], 1, False, 1, 1, "first.txt", "first.pdf", first_public_from),
                  ("later", project, NWWDA, later, 2, True, 1, 1, "later.txt", "later.pdf", later)])
    plans.insert(fresh, "strata.silver.plan_listings",
                 ("document_id", "project_id", "activity_reference_no", "is_first_listing",
                  "first_listing_confirmed", "public_from"),
                 [("first", project, reference, True, True, first_public_from),
                  ("later", project, reference, False, True, later)])
    plans.insert(fresh, "strata.silver.plan_steps",
                 ("document_id", "project_id", "activity_reference_no", "step", "step_order", "planned_on",
                  "actual_on", "public_from"),
                 [("first", project, reference, "Signed Contract", 1, first["value"], None, first["date"]),
                  ("later", project, reference, "Signed Contract", 1, dt.date(2021, 11, 1), signed, later)])

    fresh.run(plans._sql("plan_step_delays.sql"), {"project_id": project})

    [row] = rows(fresh, "SELECT * FROM strata.silver.plan_step_delays WHERE document_id = 'later'")
    assert (row["planned_on"], row["first_planned_on"]) == (dt.date(2021, 11, 1), first["value"])
    assert row["delay_days"] == value("plan-229129-days-late")["value"]
    assert row["public_from"] == delay_public_from


# ── The live layout parser, through the same port ──

AI_PARSE_DOCUMENT = {  # the shape of ai_parse_document's version 2.0 output, written by hand: the gate
    "document": {  # cannot reach the workspace, and the live plan run (ops/plans/run_live.py) reads the real one
        "pages": [{"id": 0}],
        "elements": [
            {"id": 0, "type": "section_header", "content": "WORKS", "bbox": [{"coord": [15, 112, 33, 117], "page_id": 0}]},
            {"id": 1, "type": "table", "bbox": [{"coord": [15, 118, 792, 160], "page_id": 0}], "content": (
                "<table><tr><th rowspan='2'>Activity Reference No. / Description</th><th rowspan='2'>Method</th>"
                "<th rowspan='2'>Actual Amount (US$)</th><th rowspan='2'>Process Status</th>"
                "<th colspan='2'>Signed Contract</th><th>Contract Completion</th></tr>"
                "<tr><th>Planned</th><th>Actual</th><th>Planned</th></tr>"
                "<tr><td>KE-NWWDA-229129-CW-RFB / Drilling of 4 Number Exploratory Boreholes In Wajir County</td>"
                "<td>Request for Bids</td><td>1,245,092.76</td><td>Signed</td><td>2021-07-01</td><td>2022-01-03</td>"
                "<td>2021-10-15</td></tr></table>")},
        ],
    },
    "metadata": {"version": "2.0"},
}


def test_the_live_layout_parser_sends_one_page_to_ai_parse_document_and_reads_its_tables_as_step_rows():
    import io
    import json

    from pypdf import PdfReader, PdfWriter

    from strata.lakehouse.engine import Result
    from strata.reader import step
    from strata.reader.layout import AiParseDocument, Page

    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=792, height=612)
    pdf = io.BytesIO()
    writer.write(pdf)
    uploaded, statements = {}, []

    class Warehouse:
        def run(self, sql, params=None):
            statements.append((sql, params))
            return Result(("parsed",), ((json.dumps(AI_PARSE_DOCUMENT),),))

    parser = AiParseDocument(Warehouse(), upload=uploaded.__setitem__, fetch=lambda url: pdf.getvalue())
    tables = parser.parse(Page("40132287", "http://documents.worldbank.org/plan.pdf", 3)).tables
    reading = step.plan_rows([(3, tables)])

    path = "/Volumes/strata/bronze/files/layout/40132287/page-3.pdf"
    assert list(uploaded) == [path] and len(PdfReader(io.BytesIO(uploaded[path])).pages) == 1
    assert "ai_parse_document" in statements[0][0] and statements[0][1] == {"path": path}
    [row] = reading.rows
    signed = next(s for s in row.steps if s.step == "Signed Contract")
    assert (row.section, row.activity_reference_no, row.fields["method"], row.fields["process_status"]) == (
        "WORKS", "KE-NWWDA-229129-CW-RFB", "Request for Bids", "Signed")
    assert row.fields["actual_amount_usd"] == Decimal(str(value("plan-229129-actual")["value"]))
    assert (signed.planned_on, signed.actual_on) == (value("plan-229129-first-planned-signing")["value"],
                                                     value("plan-229129-signed")["value"])


def test_a_page_ai_parse_document_answers_with_nothing_fails_as_that_one_page():
    import io

    from pypdf import PdfWriter

    from strata.lakehouse.engine import Result
    from strata.reader.layout import AiParseDocument, Page, ParseFailed

    writer = PdfWriter()
    writer.add_blank_page(width=792, height=612)
    pdf = io.BytesIO()
    writer.write(pdf)

    class Warehouse:
        def run(self, sql, params=None):
            return Result(("parsed",), ())

    parser = AiParseDocument(Warehouse(), upload=lambda path, data: None, fetch=lambda url: pdf.getvalue())

    with pytest.raises(ParseFailed, match="returned nothing"):
        parser.parse(Page("40132287", "http://documents.worldbank.org/plan.pdf", 1))
    with pytest.raises(ParseFailed, match="could not cut page 2"):
        parser.parse(Page("40132287", "http://documents.worldbank.org/plan.pdf", 2))


@pytest.mark.parametrize("rejoin", [False, True], ids=["as-the-pdf-gives-them", "rejoined"])
def test_words_a_cell_wrapped_at_its_edge_read_as_the_pdf_gives_them_unless_the_flag_rejoins_them(fresh, rejoin):
    """Parked decision 8 (tickets 08, 10 and 18): a STEP cell wraps "Exploratory" as "Explor" then
    "atory". config/models.toml's [layout] rejoin_split_words, false until the user decides, joins
    such a word; the plan's own words are values.toml's."""
    from strata.fixture import recorded as fmt
    from strata.lakehouse import plans
    from strata.reader.documents import RecordedDocuments
    from strata.reader.layout import RecordedLayout

    manifest = fmt.load_manifest()
    plans.run(fresh, RecordedDocuments(manifest), RecordedLayout(manifest, rejoin_split_words=rejoin), "P156634")

    [found] = rows(fresh, DEMO_ROWS + " AND r.activity_reference_no = :reference", agency=NWWDA, plan_date=DEMO_PLAN,
                   reference="KE-NWWDA-229129-CW-RFB")
    expected = next(row for row in GROUND_TRUTH["plan_row"] if row["reference"] == "KE-NWWDA-229129-CW-RFB")
    assert (found["description"] == expected["description"]) is rejoin
    assert squash(found["description"]) == squash(expected["description"])
