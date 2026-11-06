"""Procurement Plan pages as the paid workspace stores them, read by the plan reader as a rewrite reads them (ticket 141).

P155350's plan of June 10, 2024. On October 29, 2026 the Procurement tab of P155350 (Sindh Resilience, Pakistan) showed
no amount for any of the plan's rows and "Request for Bids" on the rows whose references end in -RFP. The page's
published text (the PDF's own words) shows what the plan prints: its WORKS table has an Actual Amount (US$) column and no
Estimated Amount (US$) column, and its Method column names Request for Bids on every row, the -RFP rows among them. The
project's notices name Request for Bids for those packages too. So the reader keeps the Method column, and the
reference's code, RFP for Request for Proposals, is kept beside it as a data note.

ai_parse_document read the page's WORKS table with two faults the plan reader now reads through:
- it cut the amount column's label to "Actual Am ount (US$", so the reader did not know the column and wrote no amount;
- it folded the table's first row, PK-SID-2961-CW-RFP, into a second copy of the header, the row's cells after the
  header's twelve labels, so the reader found no reference in that row and left it out.

tests/fixtures/layout/P155350-34337516-page-4.json is the stored page, read with SELECT only: what ai_parse_document
read (strata.bronze.layout_pages), the page's published text (strata.bronze.document_pages) and the references the
plan's text lists. Each value below is copied from that text, and the first test checks each one is printed there.

Three readings of ai_parse_document's stay as it read them and are not checked here: it read PK-SID-2960-CW-RFP as
PK-SID-2969-CW-RFP (which the plan lists on its next page), PK-SID-69711-CW-RFB as PK-SID-69713-CW-RFB (one character
from both 69711 and 69710, so the plan's text settles neither), and PK-SID-29086-CW-RFB's amount 4,924,242.94 as
4,324,242.94.

P156634's plan of October 9, 2026, the demo plan. ai_parse_document folded its CONSULTING FIRMS table's only row,
NWWDA-WSDP-03-2019-2020, into the header the same way, so the workspace held eight of the plan's nine activities, while
the fixture's own reading of the plan (from the PDF's words) holds all nine. tests/fixtures/layout/
P156634-40132287-page-3.json is that stored page.
"""

import datetime as dt
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

PAGES = Path(__file__).resolve().parent / "fixtures" / "layout"
STORED = json.loads((PAGES / "P155350-34337516-page-4.json").read_text())
DEMO = json.loads((PAGES / "P156634-40132287-page-3.json").read_text())

# Each row of the page as its published text prints it: Method, Actual Amount (US$), Process Status and words of its
# description that ai_parse_document read as printed (it read "Toe" as "Tee" and "Recoupment" as "Reconnuement", and
# a word's capital as it liked). PK-SID-2961-CW-RFP is the row ai_parse_document folded into the header.
PRINTED = {
    "PK-SID-2961-CW-RFP": ("Request for Bids", "5,024,100.36", "Signed", "Providing stone pitching between BU Bund"),
    "PK-SID-2963-CW-RFP": ("Request for Bids", "0.00", "Canceled", "CONSTRUCTION OF BHANSAR"),
    "PK-SID-2964-CW-RFP": ("Request for Bids", "0.00", "Canceled", "CONSTRUCTION OF SABUSAN"),
    "PK-SID-2965-CW-RFP": ("Request for Bids", "0.00", "Canceled", "CONSTRUCTION OF SANKAR"),
    "PK-SID-2967-CW-RFP": ("Request for Bids", "0.00", "Canceled", "CONSTRUCTION OF KONKAR"),
    "PK-SID-2968-CW-RFP": ("Request for Bids", "0.00", "Canceled", "CONSTRUCTION OF KARMATIANI"),
    "PK-SID-2962-CW-RFP": ("Request for Bids", "0.00", "Canceled", "Stone pitching and"),
    "PK-SID-20260-CW-RFB": ("Request for Bids", "3,557,787.46", "Signed", "Providing Stone Pitching along M"),
    "PK-SID-29036-CW-RFB": ("Request for Bids", "4,146,864.03", "Completed", "Providing Stone Pitching along PB Bund"),
    "PK-SID-29042-CW-RFB": ("Request for Bids", "791,521.35", "Signed", "Earthwork & Repair Damaged Stone"),
    "PK-SID-29051-CW-RFB": ("Request for Bids", "6,072,151.77", "Signed", "Providing Stone Pitching along M"),
    "PK-SID-29055-CW-RFB": ("Request for Bids", "969,963.22", "Signed", "Providing Stone Pitching along BU Bund"),
    "PK-SID-37707-CW-RFB": ("Request for Bids", "0.00", "Canceled", "Earth Work along SM Bund"),
}
FOLDED = "PK-SID-2961-CW-RFP"


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def printed_block(reference: str) -> str:
    """The page's published text for one row: from its reference to the next row's."""
    text = STORED["text"]
    start = text.index(f"{reference} /")
    following = text.find(" PK-SID-", start + 1)
    return text[start:following if following > 0 else len(text)]


def write_stored(stored: dict) -> tuple[dict, list[dict]]:
    """The plan rows and data notes the plan reader writes from a stored page, as a rewrite writes them on the
    workspace (strata.lakehouse.plans.write_rows, ticket 122's path): the page as bronze holds it, and the plan's
    listed references as its text gives them."""
    from strata.config import load_thresholds
    from strata.lakehouse import catalog, plans

    thresholds = load_thresholds()
    public_from = dt.date.fromisoformat(stored["public_from"])
    version = plans.Version(
        plans.Entry(stored["document_id"], dt.date.fromisoformat(stored["plan_date"]),
                    dt.date.fromisoformat(stored["disclosed_on"]), stored["text_url"], stored["pdf_url"]),
        public_from, stored["implementing_agency"], stored["listed"],
        [plans.PdfPage(stored["pdf_page"], stored["page_hash"], True, True)], is_latest=True)
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        plans.insert(engine, "strata.bronze.layout_pages",
                     ("document_id", "project_id", "pdf_page", "page_hash", "parser", "tables", "text", "figures",
                      "parsed_at", "run_id", "public_from"),
                     [(stored["document_id"], stored["project_id"], stored["pdf_page"], stored["page_hash"],
                       stored["parser"], stored["tables"], "", 0, dt.datetime(2026, 10, 28, 8, 56, 52), "ticket-141",
                       public_from)])
        plans.write_rows(engine, stored["project_id"], [version],
                         int(thresholds.value("ingestion.reference_misread_characters")),
                         plans.inline_result_bytes(thresholds))

        def read(sql):
            result = engine.run(sql, {"project_id": stored["project_id"]})
            return [dict(zip(result.columns, row)) for row in result.rows]

        rows = {row["activity_reference_no"]: row for row in read(
            "SELECT * FROM strata.silver.plan_rows WHERE project_id = :project_id")}
        return rows, read("SELECT * FROM strata.silver.plan_data_notes WHERE project_id = :project_id")


@pytest.fixture(scope="module")
def written():
    return write_stored(STORED)


def test_each_value_this_file_expects_is_printed_on_the_page_for_its_row():
    """The values above come from the page's published text, not from Prism's code."""
    for reference, (method, amount, status, words) in PRINTED.items():
        block = printed_block(reference)
        assert squash(f"{method} ") in squash(block), reference
        assert re.search(rf"(?<![\d,.]){re.escape(amount)} {status}\b", " ".join(block.split())), reference
        assert squash(words) in squash(block.partition(" / ")[2]), reference


def test_the_plan_prints_an_actual_amount_column_and_no_estimated_amount_column():
    text = " ".join(STORED["text"].split())
    assert "Actual Amount (US$)" in text and "Estimated" not in text


def test_each_row_reads_the_actual_amount_its_table_prints_and_no_estimate(written):
    rows, _ = written
    for reference, (_, amount, status, _) in PRINTED.items():
        if reference == FOLDED:
            continue
        row = rows[reference]
        assert (row["actual_amount_usd"], row["process_status"]) == (Decimal(amount.replace(",", "")), status), (
            reference)
        assert row["estimated_amount_usd"] is None, reference


def test_the_first_row_ai_parse_document_folded_into_the_header_is_read_with_its_own_cells(written):
    rows, _ = written
    method, amount, status, words = PRINTED[FOLDED]
    row = rows[FOLDED]

    assert (row["method"], row["actual_amount_usd"], row["process_status"]) == (
        method, Decimal(amount.replace(",", "")), status)
    assert row["description"].startswith(words)
    assert (row["review_type"], row["loan_credit_no"], row["estimated_amount_usd"]) == ("Prior", "IDA / 58880", None)


def test_each_row_keeps_the_method_its_column_prints_and_its_description(written):
    rows, _ = written
    for reference, (method, _, _, words) in PRINTED.items():
        assert rows[reference]["method"] == method, reference
        assert squash(words).lower() in squash(rows[reference]["description"]).lower(), reference


def test_an_rfp_reference_whose_method_column_names_request_for_bids_is_kept_as_a_data_note(written):
    """The reference's code is a check that disagrees in the row's data, never a value that replaces the column."""
    rows, notes = written
    differs = {note["activity_reference_no"]: note for note in notes if note["note"] == "method_differs_from_reference"}

    for reference in PRINTED:
        if reference.endswith("-RFP"):
            note = differs[reference]
            assert (note["reference_method_code"], note["reference_method"], note["method"]) == (
                "RFP", "Request for Proposals", "Request for Bids")
            assert rows[reference]["method"] == "Request for Bids"
        else:
            assert reference not in differs


def test_the_demo_plans_stored_page_reads_the_consultancy_ai_parse_document_folded_into_the_header(fixture_db):
    """The row reads as the fixture's own reading of the plan's PDF words gives it, and the other rows read as the
    workspace wrote them before (ticket 131's repair keeps KE-NWWDA-193461-9O-RF8 as read there)."""
    rows, _ = write_stored(DEMO)
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run("SELECT * FROM strata.silver.plan_rows WHERE document_id = :document_id "
                            "AND activity_reference_no = :reference",
                            {"document_id": DEMO["document_id"], "reference": "NWWDA-WSDP-03-2019-2020"})
        [fixture] = [dict(zip(result.columns, row)) for row in result.rows]

    compared = ("section", "method", "market_approach", "review_type", "estimated_amount_usd", "actual_amount_usd",
                "process_status", "pdf_page")
    assert {key: rows["NWWDA-WSDP-03-2019-2020"][key] for key in compared} == {key: fixture[key] for key in compared}
    assert sorted(rows) == sorted([*(reference for reference in DEMO["listed"] if reference != "KE-NWWDA-199461-GO-RFB"),
                                   "KE-NWWDA-193461-9O-RF8"])
