"""The stress shelf on the Data readiness page (ticket 18; the 18 design brief, sections 4 to 6), at seam 2:
data_readiness_for, called by name through the registry, returns the shelf with the other measures.

Expected values come from tests/ground_truth/values.toml ([stress_shelf]), from the slice file, or from
hand-made catalogs whose rows each test writes, never from the way the tool computes them.
"""

import datetime as dt
import shutil
import tomllib
from pathlib import Path

import pytest

from strata.dbx import Viewer
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.lakehouse.stress_shelf import COLUMNS as SHELF_COLUMNS
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
SHELF = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["stress_shelf"]
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
DAY = dt.date(2026, 10, 23)
WHEN = dt.datetime(2026, 10, 23, 9, tzinfo=dt.UTC)
KINDS = ["scan_annex", "longest_pad", "large_plan", "other_language", "over_parser_limit"]


def readiness(engine, **arguments):
    return registry.call("data_readiness_for", {"as_of": DAY.isoformat(), **arguments},
                         registry.Context(engine=engine, viewer=ANA))


def text(segments) -> str:
    """A sentence's segments as the page writes them, numbers in words up to nine."""
    from strata.tools.data_readiness_for import text_of

    return text_of(segments)


@pytest.fixture(scope="module")
def fixture(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield readiness(engine), readiness(engine, sources="awards,notices", from_tool="find_comparables"), \
            readiness(engine, sources="documents,projects", from_tool="check_plan")


def test_the_page_lists_the_five_hardest_documents_in_the_slice_file_order_with_their_recorded_outcomes(fixture):
    result, *_ = fixture
    shelf = result["stress_shelf"]
    annex = SHELF["pad_risk_annex"]

    assert [entry["kind"] for entry in shelf] == KINDS
    pad = shelf[0]
    assert (pad["state"], pad["document"]["document_id"], pad["document"]["project_id"]) == (
        "read", annex["document_id"], annex["project"])
    assert (pad["document"]["document_type"], pad["document"]["pdf_pages"], pad["hard_page"]) == (
        "Project Appraisal Document", annex["pdf_pages"], annex["first_pdf_page"])
    assert pad["document"]["project_name"] == "Rajasthan Road Sector Modernization Project"
    outcome = result["rows"][pad["outcome_row"]]
    assert (outcome["count"], outcome["denominator"]) == (annex["risks"], annex["risks"])
    assert (pad["denominator_from"], pad["counted_on"], pad["status"]) == ("hand_count", annex["counted_on"].isoformat(),
                                                                         None)
    parser = result["rows"][pad["parser_row"]]
    assert (parser["count"], parser["denominator"]) == (annex["pdf_pages"], annex["pdf_pages"])
    assert {result["rows"][entry["outcome_row"]]["source"]["counted_in"] for entry in shelf if entry["outcome_row"]
            is not None} == {"strata.ops.stress_shelf"}
    french = shelf[3]
    assert (french["document"]["language"], french["hard_page"]) == ("fr", SHELF["french_report"]["first_paragraph"]["pdf_page"])
    last = shelf[4]
    assert (last["state"], last["document"], last["parser_limit_pages"]) == ("no_document", None, 500)
    assert result["rows"][last["longest_row"]]["count"] == SHELF["over_parser_limit"]["longest_pages"]


def test_a_filtered_view_shows_only_the_shelf_rows_on_its_sources_and_none_when_none_are(fixture):
    _, comparables, plan_check = fixture

    assert comparables["stress_shelf"] == []
    assert [entry["kind"] for entry in plan_check["stress_shelf"]] == ["large_plan"]


# ── Hand-made catalogs ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def empty_catalog(tmp_path_factory):
    path = tmp_path_factory.mktemp("shelf") / "strata.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
        # One measure, so the page has something measured to show beside the shelf.
        engine.insert_rows("strata.ops.data_readiness", (
            "run_id", "source", "subject", "measure", "kind", "count", "denominator", "as_of", "detail", "measured_at",
            "public_from"), [("run-1", "documents", "P130164", "passages_embedded", "coverage", 10, 10, None, None, WHEN,
                              DAY)])
    return path


def outcome(key, kind, position, state="read", count=8, denominator=8, unreadable=False, document="18381488",
            document_type="Project Appraisal Document", part=None):
    row = dict.fromkeys(SHELF_COLUMNS)
    return row | {"run_id": "run-1", "shelf_key": key, "kind": kind, "position": position, "state": state,
                  "document_id": document, "project_id": "P130164", "document_type": document_type,
                  "document_date": dt.date(2013, 10, 1), "pdf_pages": 100, "pdf_url": "https://example.org/pad.pdf",
                  "language": "en", "part": part, "hard_page": 65, "parser_pages": 100, "count": count,
                  "denominator": denominator, "denominator_from": "hand_count", "unreadable": unreadable,
                  "parser": "test parser", "parser_limit_pages": 500, "longest_pages": 103, "read_pages": 97,
                  "daily_page_cap": 500, "measured_at": WHEN, "public_from": DAY}


@pytest.fixture
def written(empty_catalog, tmp_path):
    def write(*outcomes):
        path = tmp_path / "strata.duckdb"
        shutil.copy(empty_catalog, path)
        with DuckDBEngine.open(path) as engine:
            engine.insert_rows("strata.ops.stress_shelf", SHELF_COLUMNS,
                               [tuple(row[column] for column in SHELF_COLUMNS) for row in outcomes])
        with DuckDBEngine.open(path, read_only=True) as engine:
            return readiness(engine)
    return write


def holds(result, kind) -> list[str]:
    [found] = [entry for entry in result["kinds"] if entry["kind"] == kind]
    return [text(sentence) for sentence in found["holds_back"]]


def test_an_unreadable_part_is_a_gap_that_adds_one_sentence_to_what_holds_document_answers_back(written):
    result = written(outcome("p130164_pad", "scan_annex", 1, count=0, part="risk_annex", unreadable=True))

    [pad] = [entry for entry in result["stress_shelf"] if entry["kind"] == "scan_annex"]
    assert pad["status"] == "gap"
    sentence = "I couldn't read the risk annex in the Project Appraisal Document for P130164, one of the hardest documents I read."
    assert sentence in holds(result, "document_search")
    assert sentence not in holds(result, "plan_check")  # the PAD is not a source of the plan check
    [segments] = [s for entry in result["kinds"] if entry["kind"] == "document_search" for s in entry["holds_back"]
                  if text(s) == sentence]
    assert {"link": "the hardest documents I read", "href": "#hardest-documents"} in segments
    assert {"mono": "P130164"} in segments


def test_two_gaps_name_how_many_documents_and_one_of_them(written):
    result = written(outcome("p130164_pad", "scan_annex", 1, count=0, part="risk_annex"),
                     outcome("longest_pad", "longest_pad", 2, count=0, denominator=103, document="27348420"))

    assert ("I couldn't read parts of two of the hardest documents I read, such as the risk annex in the Project "
            "Appraisal Document for P130164.") in holds(result, "document_search")


def test_an_outcome_under_the_read_well_threshold_is_partial_and_adds_no_sentence(written):
    result = written(outcome("p130164_pad", "scan_annex", 1, count=5, part="risk_annex"))

    [pad] = [entry for entry in result["stress_shelf"] if entry["kind"] == "scan_annex"]
    assert pad["status"] == "partial"
    assert not any("hardest documents" in sentence for sentence in holds(result, "document_search"))


def test_with_no_hand_count_the_outcome_has_nothing_to_check_against_and_no_badge(written):
    result = written(outcome("p130164_pad", "scan_annex", 1, count=6, denominator=None, part="risk_annex"))

    [pad] = [entry for entry in result["stress_shelf"] if entry["kind"] == "scan_annex"]
    assert (pad["status"], result["rows"][pad["outcome_row"]]["denominator"]) == (None, None)


def test_before_the_first_document_run_every_entry_is_not_read_yet_in_the_slice_file_order(written):
    result = written()

    assert [(entry["kind"], entry["state"], entry["document"]) for entry in result["stress_shelf"]] == [
        (kind, "not_read", None) for kind in KINDS]
