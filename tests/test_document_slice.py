"""The document slice, the page router's Route B and the stress shelf (ticket 18): seam 1, the lakehouse
run over the fixture.

The gate builds the fixture database by running the document slice over the recorded documents
(gates/build_fixture.py), so these tests read what that run wrote. Every count and page they expect
comes from tests/ground_truth/values.toml ([stress_shelf]), which quotes the recorded documents with
their PDF pages, never from Strata's code.
"""

import datetime as dt
import itertools
import json
import shutil
import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
SHELF = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["stress_shelf"]


@pytest.fixture(scope="module")
def db(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


# ── The stress shelf's Procurement Plan ──────────────────────────────────

def test_the_stress_shelf_procurement_plan_yields_one_step_row_for_every_activity_reference_in_its_text(db):
    """P161305's plan of September 24, 2026 lists 212 activities in its published text, over twelve
    pages of STEP tables, most of them continued from the page before without a header."""
    plan = SHELF["long_plan"]
    found = rows(db, "SELECT activity_reference_no, count(*) AS n FROM strata.silver.plan_rows "
                     "WHERE document_id = :document_id GROUP BY activity_reference_no", document_id=plan["document_id"])

    assert len(found) == plan["activity_references"]
    assert all(row["n"] == 1 for row in found)
    assert sum(row["activity_reference_no"].endswith("-2") for row in found) == plan["with_a_second_issue"]


# ── The slice ────────────────────────────────────────────────────────────

def test_the_slice_counts_the_projects_its_criteria_select_and_records_how_that_differs_from_plan_md(db):
    """Criterion 1. The count comes from strata.gold.project at run time (tests/ground_truth/slice_projects.sql
    counts it again in plain SQL), and the measure's detail records the difference from PLAN.md's 128
    with its reason: the fixture holds no project of Bangladesh, Vietnam or Pakistan."""
    case = SHELF["slice_projects"]
    [measure] = rows(db, "SELECT count, denominator, detail FROM strata.ops.data_readiness "
                         "WHERE run_id = 'fixture' AND source = 'documents' AND subject = 'all' "
                         "AND measure = 'slice_projects'")
    selected = {row["project_id"] for row in rows(db, "SELECT DISTINCT project_id FROM strata.silver.documents")}

    assert measure["count"] == case["count"] == len(case["projects"])
    assert measure["denominator"] is None  # PLAN.md's figure is a plan, not a denominator
    assert f"planned {case['planned']}, {case['planned'] - case['count']} fewer" in measure["detail"]
    assert "Kenya 17, Bangladesh 0, Vietnam 0, Pakistan 0" in measure["detail"]
    assert "holds no such project for Bangladesh, Vietnam and Pakistan" in measure["detail"]
    # The run read the documents of each selected project whose list the fixture records, and the named
    # ones: the showcase (India) and the French report's project (Haiti) are outside the criteria.
    assert selected == {"P130164", "P156634", "P127203"}


DOCUMENTS_READ = """
SELECT documents, pdf_pages, pages_route_a, pages_route_b, pages_read_well_route_a, pages_read_well_route_b
FROM strata.ops.documents_read WHERE run_id = 'fixture' AND document_type = :document_type AND fiscal_year = :year
"""


def test_strata_ops_shows_documents_per_type_and_fiscal_year_with_pages_and_read_well_per_route(db):
    """Criterion 2. The P130164 PAD, disclosed in fiscal 2014, is a scan: every one of its 100 pages goes to
    the layout parser, which reads all but the three whose text layer is empty."""
    annex = SHELF["pad_risk_annex"]
    [pad] = rows(db, DOCUMENTS_READ, document_type="Project Appraisal Document",
                 year=SHELF["pad_disclosed"]["fiscal_year"])

    assert pad == {"documents": 1, "pdf_pages": annex["pdf_pages"], "pages_route_a": 0,
                   "pages_route_b": annex["pdf_pages"], "pages_read_well_route_a": 0,
                   "pages_read_well_route_b": annex["pdf_pages"] - len(annex["empty_pages"])}
    measures = {row["measure"]: row for row in rows(
        db, "SELECT measure, count, denominator FROM strata.ops.data_readiness WHERE run_id = 'fixture' "
            "AND source = 'documents' AND subject = 'P130164'")}
    assert (measures["document_pages_read_route_b"]["count"], measures["document_pages_read_route_b"]["denominator"]) == (
        annex["pdf_pages"] - len(annex["empty_pages"]), measures["document_pages_route_b"]["count"])
    assert {"document_pages_route_a", "document_pages_route_b", "document_pages_read_route_a"} <= set(measures)


@pytest.fixture
def copied(fixture_db, tmp_path):
    """A copy of the fixture database that a test may run the readers on again."""
    path = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, path)
    with DuckDBEngine.open(path) as engine:
        yield engine


def later_that_day():
    """The fixture's runs read and measure on October 23, 2026 (gates/build_fixture.py); this clock reads
    the same day, an hour later."""
    ticks = itertools.count()
    return lambda: dt.datetime(2026, 10, 23, 10, 0, tzinfo=dt.UTC) + dt.timedelta(milliseconds=next(ticks))


def test_a_second_run_of_the_slice_parses_no_pages(copied):
    """Criterion 2. Every Route B page of the first run is in bronze.layout_pages, keyed by its document, PDF
    page and text hash, or failed today, so a second run the same day parses none, for either reader."""
    from strata.lakehouse import passages, plans

    plans.run_on_fixture(copied, "P161305", clock=later_that_day(), run_id="plans-second")
    report = passages.run_on_fixture(copied, clock=later_that_day(), run_id="second")

    runs = rows(copied, "SELECT run_id, project_id, pages_waiting, pages_parsed, pages_failed FROM strata.ops.parse_runs "
                        "WHERE run_id IN ('plans-second', 'second')")
    assert {row["project_id"] for row in runs} >= {"P161305", "P130164"}
    assert all((row["pages_waiting"], row["pages_parsed"], row["pages_failed"]) == (0, 0, 0) for row in runs)
    assert report.embedded == 0  # no passage changed, so none is embedded again


def test_a_low_daily_page_cap_stops_the_layout_parser_and_the_shelf_says_where_reading_stopped(tmp_path):
    """Criterion 2. The cap counts every page the parser tried that day, across both readers."""
    from strata.config import load_thresholds
    from strata.lakehouse import catalog, passages

    limits = load_thresholds()
    limits.values["ingestion"]["daily_page_cap"] = 30
    with DuckDBEngine.open(tmp_path / "capped.duckdb") as engine:
        catalog.build(engine)
        passages.run_on_fixture(engine, projects=["P130164"], thresholds=limits, clock=later_that_day(), run_id="capped")
        again = passages.run_on_fixture(engine, projects=["P130164"], thresholds=limits, clock=later_that_day(),
                                        run_id="capped-again")
        tried = rows(engine, "SELECT (SELECT count(*) FROM strata.bronze.layout_pages) "
                             "+ (SELECT count(*) FROM strata.ops.parse_failures) AS n")[0]["n"]
        [first, second] = rows(engine, "SELECT pages_parsed + pages_failed AS tried, stopped_at_cap FROM "
                                       "strata.ops.parse_runs ORDER BY started_at")
        [pad] = [row for row in again.shelf if row.shelf_key == "p130164_pad"]

    assert tried == 30
    assert (first["tried"], first["stopped_at_cap"]) == (30, True)
    assert (second["tried"], second["stopped_at_cap"]) == (0, True)
    assert (pad.state, pad.daily_page_cap, pad.pdf_pages) == ("stopped_at_cap", 30, SHELF["pad_risk_annex"]["pdf_pages"])
    assert pad.read_pages < pad.pdf_pages


# ── The stress shelf ─────────────────────────────────────────────────────

def shelf(engine) -> dict[str, dict]:
    return {row["shelf_key"]: row for row in rows(engine, "SELECT * FROM strata.ops.stress_shelf WHERE run_id = 'fixture'")}


def test_the_shelf_records_one_outcome_for_each_of_its_five_entries_in_the_slice_file_order(db):
    found = rows(db, "SELECT shelf_key, kind, position FROM strata.ops.stress_shelf WHERE run_id = 'fixture' "
                     "ORDER BY position")

    assert [row["kind"] for row in found] == ["scan_annex", "longest_pad", "large_plan", "other_language",
                                             "over_parser_limit"]


def test_the_p130164_pad_risk_annex_recovers_each_rated_risk_on_its_page_and_counts_them_against_the_hand_count(db):
    """Criterion 3. The annex is set in two columns that the scan's text layer runs together, so the page
    router sends it to the layout parser as a risk table, which recovers one row per rated risk."""
    annex = SHELF["pad_risk_annex"]
    risk_rows = rows(db, "SELECT pdf_page, cells FROM strata.silver.passages WHERE document_id = :document_id "
                         "AND kind = 'table_row' ORDER BY table_row", document_id=annex["document_id"])
    outcome = shelf(db)["p130164_pad"]

    found = [(dict(json.loads(row["cells"]))["Risk"], dict(json.loads(row["cells"]))["Rating"], row["pdf_page"])
             for row in risk_rows]
    assert found == [(rating["risk"], rating["rating"], rating["pdf_page"]) for rating in annex["ratings"]]
    assert (outcome["count"], outcome["denominator"], outcome["denominator_from"]) == (
        len(annex["ratings"]), annex["risks"], "hand_count")
    assert (outcome["counted_on"], outcome["hard_page"], outcome["unreadable"]) == (
        annex["counted_on"], annex["first_pdf_page"], False)
    assert outcome["parser_pages"] == annex["pdf_pages"]  # a scan: every page goes to the layout parser
    routes = rows(db, "SELECT pdf_page FROM strata.silver.document_page_routes WHERE document_id = :document_id "
                      "AND reason = 'risk_table' ORDER BY pdf_page", document_id=annex["document_id"])
    assert [row["pdf_page"] for row in routes] == list(range(annex["first_pdf_page"], annex["last_pdf_page"] + 1))


def test_the_risk_annex_has_one_summary_passage_which_the_verifier_never_lets_back_a_number(db):
    annex = SHELF["pad_risk_annex"]
    [summary] = rows(db, "SELECT passage_id, text, parse_route FROM strata.silver.passages "
                         "WHERE document_id = :document_id AND kind = 'table_summary'", document_id=annex["document_id"])

    assert summary["passage_id"] == f"{annex['document_id']}/v1/table{annex['first_pdf_page']}"
    assert "not the document's own words" in summary["text"]
    assert all(rating["risk"] in summary["text"] for rating in annex["ratings"])


def test_the_scanned_pad_keeps_its_numbered_paragraphs_with_their_pages_as_the_layout_parser_read_them(db):
    annex = SHELF["pad_risk_annex"]
    paragraphs = rows(db, "SELECT paragraph, pdf_page, scanned, parse_route FROM strata.silver.passages "
                          "WHERE document_id = :document_id AND kind = 'paragraph' AND paragraph_numbered",
                      document_id=annex["document_id"])

    assert len(paragraphs) > 100
    assert {(row["scanned"], row["parse_route"]) for row in paragraphs} == {(True, "B")}
    assert not any(row["pdf_page"] in annex["empty_pages"] for row in paragraphs)


def test_the_longest_pad_is_chosen_at_run_time_and_counts_its_pages_read_well_against_its_pdf(db):
    longest = SHELF["longest_pad"]
    outcome = shelf(db)["longest_pad"]

    assert (outcome["document_id"], outcome["pdf_pages"], outcome["denominator"]) == (
        longest["document_id"], longest["pdf_pages"], longest["pdf_pages"])
    assert outcome["denominator_from"] == "pdf_pages"
    assert 0 < outcome["count"] <= outcome["pdf_pages"]


def test_the_stress_shelf_plan_outcome_counts_its_activities_that_became_step_rows(db):
    plan = SHELF["long_plan"]
    outcome = shelf(db)["long_plan"]

    assert (outcome["count"], outcome["denominator"], outcome["denominator_from"]) == (
        plan["activity_references"], plan["activity_references"], "text_references")
    assert (outcome["hard_page"], outcome["pdf_pages"]) == (plan["table_starts"]["pdf_page"], plan["pdf_pages"])


def test_every_passage_from_the_french_completion_report_carries_the_language_fr(db):
    """Criterion 5. The report is read with French headings (src/strata/reader/templates.py, ICR_FR)."""
    report = SHELF["french_report"]
    passages = rows(db, "SELECT language, paragraph, paragraph_numbered, pdf_page, text FROM strata.silver.passages "
                        "WHERE document_id = :document_id ORDER BY pdf_page, paragraph", document_id=report["document_id"])
    outcome = shelf(db)["french_report"]

    assert len(passages) > 100
    assert {row["language"] for row in passages} == {"fr"}
    first = next(row for row in passages if row["paragraph_numbered"])
    assert (first["paragraph"], first["pdf_page"]) == ("1", report["first_paragraph"]["pdf_page"])
    assert first["text"].startswith(report["first_paragraph"]["quote"])
    assert (outcome["count"], outcome["denominator"], outcome["language"]) == (len(passages), len(passages), "fr")
    assert outcome["hard_page"] == report["first_paragraph"]["pdf_page"]


def test_with_no_document_over_the_parsers_limit_the_shelf_records_that_and_the_longest_page_count(db):
    """Criterion 6, as the fixture stands: no recorded document has more than 500 pages."""
    outcome = shelf(db)["over_parser_limit"]

    assert (outcome["state"], outcome["document_id"]) == ("no_document", None)
    assert (outcome["parser_limit_pages"], outcome["longest_pages"]) == (500, SHELF["over_parser_limit"]["longest_pages"])


def test_a_document_over_the_parsers_limit_is_read_in_parts_and_keeps_its_pages_in_the_whole_pdf(tmp_path):
    """Criterion 6, with the limit lowered to 40 pages so that the 100-page P130164 PAD is over it: it is
    read in three parts, each page's part is recorded, the risk rows keep their pages in the whole PDF,
    and the shelf counts the pages whose number matches the PDF."""
    from strata.config import load_thresholds
    from strata.lakehouse import catalog, passages

    annex = SHELF["pad_risk_annex"]
    limits = load_thresholds()
    limits.values["ingestion"]["parser_part_pages"] = 40
    with DuckDBEngine.open(tmp_path / "parts.duckdb") as engine:
        catalog.build(engine)
        report = passages.run_on_fixture(engine, projects=["P130164"], thresholds=limits, clock=later_that_day(),
                                         run_id="parts")
        [document] = rows(engine, "SELECT parse_parts FROM strata.silver.documents WHERE document_id = :document_id",
                          document_id=annex["document_id"])
        parts = {row["pdf_page"]: row["part"] for row in rows(
            engine, "SELECT pdf_page, part FROM strata.silver.document_page_routes WHERE document_id = :document_id",
            document_id=annex["document_id"])}
        risk_pages = [row["pdf_page"] for row in rows(
            engine, "SELECT pdf_page FROM strata.silver.passages WHERE document_id = :document_id "
                    "AND kind = 'table_row' ORDER BY table_row", document_id=annex["document_id"])]
    [outcome] = [row for row in report.shelf if row.kind == "over_parser_limit"]

    assert document["parse_parts"] == 3
    assert (parts[1], parts[40], parts[41], parts[80], parts[81], parts[100]) == (1, 1, 2, 2, 3, 3)
    assert risk_pages == [rating["pdf_page"] for rating in annex["ratings"]]  # pages 65 to 70, in part 2
    assert (outcome.document_id, outcome.parts, outcome.hard_page) == (annex["document_id"], 3, 41)
    # The parser read every page but the three whose text layer is empty, each as the page with its number.
    assert (outcome.count, outcome.denominator) == (annex["pdf_pages"] - len(annex["empty_pages"]), annex["pdf_pages"])


# ── The ISR rating history, the documents' keys and the header's sector word ──

TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())


def value(key: str) -> dict:
    return next(entry for entry in TRUTH["value"] if entry["id"] == key)


def test_the_isr_rating_history_is_read_from_the_isrs_themselves_one_row_per_rating(db):
    """The projects API keeps only the latest ratings, so the history comes from each ISR's own table:
    ISR 7 rated progress towards the PDO Satisfactory and ISR 12 Moderately Unsatisfactory
    (values.toml, isr-7-rating and isr-12-rating)."""
    history = {(row["isr_date"], row["sequence"]): row for row in rows(
        db, "SELECT isr_date, sequence, previous_rating, current_rating FROM strata.silver.isr_ratings "
            "WHERE project_id = 'P130164' AND rating_name = 'Progress towards achievement of PDO'")}
    isrs = rows(db, "SELECT count(*) AS n FROM strata.silver.documents WHERE project_id = 'P130164' "
                    "AND document_type = 'Implementation Status and Results Report'")[0]["n"]

    assert len(history) == isrs == 13
    for key, sequence in (("isr-7", 7), ("isr-12", 12)):
        [row] = [found for (day, _), found in history.items() if day == value(f"{key}-date")["value"]]
        assert (row["current_rating"], row["sequence"]) == (value(f"{key}-rating")["value"], sequence)


def test_each_document_has_a_key_named_for_its_type_and_date(db):
    """Ticket 21's addresses name a document by its key: icr-2019-10-10 for the showcase ICR."""
    found = rows(db, "SELECT document_id, project_id, document_type, doc_key FROM strata.silver.documents")
    keys = {row["document_id"]: row["doc_key"] for row in found}
    [icr] = [row["doc_key"] for row in found if (row["project_id"], row["document_type"]) == (
        "P130164", "Implementation Completion and Results Report")]

    assert icr == f"icr-{value('icr-date')['value'].isoformat()}"
    assert keys[SHELF["pad_risk_annex"]["document_id"]] == "pad-2013-10-01"
    assert len({(row["project_id"], row["doc_key"]) for row in found}) == len(found)


def test_the_header_names_each_project_s_sector_in_the_projects_api_s_own_words(db):
    """Ticket 17's verification found the header's word wrong for some codes; the table now follows the
    names the projects API gives each code (FY17 - Rural and Inter-Urban Roads for TI, FY17 - Sanitation
    for WA), read here from the recorded projects."""
    from strata.knowledge.sectors import SECTORS

    names = {}
    for path in (ROOT / "data" / "fixture" / "recorded" / "api" / "projects").glob("*.json"):
        for project in json.loads(path.read_text())["response"].get("projects", {}).values():
            for major in project.get("major_sectors") or []:
                for sector in major["major_sector"].get("sectors") or []:
                    names[sector["sector_code"]] = sector["sector_name"].removeprefix("FY17 - ").strip()
    recorded = {code: name for code, name in names.items() if code in SECTORS}
    assert len(recorded) >= 10
    assert {code: SECTORS[code].name for code in recorded} == recorded
    [header] = [row["header"] for row in rows(db, "SELECT header FROM strata.silver.passages "
                                                  "WHERE passage_id = '31525018/v1/54'")]
    assert header == "ICR, P130164, India, roads, III.B, ¶54, p.23"
