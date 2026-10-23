"""search_passages at seam 2, the tool contract: called by name through the registry, as the viewer, with
and without an as-of date, on the fixture database and its fixture search over the recorded vectors.

Expected passages, pages and dates come from tests/ground_truth/values.toml and from the ticket, never
from the tool's own code.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
ICR = "Implementation Completion and Results Report"
ICR_REVIEW = "Implementation Completion Report Review"
REBIDDING = "works estimates market rates rebidding"  # the ticket's query, word for word


def value(key: str):
    return next(entry for entry in TRUTH["value"] if entry["id"] == key)


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def search(engine, view="staff", page_as_of=None, **arguments):
    context = registry.Context(engine=engine, viewer=ANA, view=view, as_of=page_as_of)
    return registry.call("search_passages", arguments, context)


def test_the_rebidding_query_filtered_to_p130164_returns_icr_paragraph_54_in_its_top_three(engine):
    truth = value("icr-para-54")

    result = search(engine, query=REBIDDING, project_id="P130164")

    top = result["rows"][:3]
    found = [row for row in top if (row["document_type"], row["paragraph"]) == (ICR, str(truth["paragraph"]))]
    assert len(found) == 1, [(row["document_type"], row["paragraph"]) for row in top]
    [row] = found
    assert row["text"] == truth["quote"]
    assert (row["pdf_page"], row["section_path"], row["printed_page"]) == (
        truth["pdf_page"], truth["section"], truth["printed_page"])
    assert row["evidence_id"].startswith("strata.gold.passage:") and row["source"]["pdf_pages"] == 66
    assert {r["project_id"] for r in result["rows"]} == {"P130164"}
    assert result["coverage"]["used"] == len(result["rows"]) > 0
    assert result["coverage"]["matched"] >= result["coverage"]["used"]


def documents_found(result) -> set[tuple[str, str]]:
    return {(row["document_type"], row["source"]["document_date"]) for row in result["rows"]}


def test_as_of_october_1_2019_no_icr_passage_from_p130164_is_returned(engine):
    result = search(engine, query=REBIDDING, project_id="P130164", as_of="2019-10-01")

    assert result["rows"], "the ISRs public by then still answer"
    assert not {kind for kind, _ in documents_found(result)} & {ICR, ICR_REVIEW}
    assert all(row["public_from"] <= "2019-10-01" for row in result["rows"])


def test_as_of_january_1_2021_icr_review_passages_come_from_the_march_27_2020_version(engine):
    result = search(engine, query="forest clearances awarding contracts", project_id="P130164",
                    document_type=ICR_REVIEW, as_of="2021-01-01")

    assert documents_found(result) == {(ICR_REVIEW, value("icr-review-date")["value"].isoformat())}


def test_with_no_as_of_date_icr_review_passages_come_from_the_may_4_2023_re_issue(engine):
    result = search(engine, query="forest clearances awarding contracts", project_id="P130164",
                    document_type=ICR_REVIEW)

    assert documents_found(result) == {(ICR_REVIEW, value("icr-review-reissue-date")["value"].isoformat())}
    assert {row["version"] for row in result["rows"]} == {2}


def test_the_page_as_of_date_applies_too_and_the_earlier_date_wins(engine):
    result = search(engine, page_as_of=dt.date(2021, 1, 1), query="forest clearances awarding contracts",
                    project_id="P130164", document_type="ICR Review", as_of="2024-01-01")

    assert result["as_of"] == "2021-01-01"
    assert documents_found(result) == {(ICR_REVIEW, value("icr-review-date")["value"].isoformat())}


@pytest.mark.parametrize("filters, project", [({"country": "KE"}, "P156634"), ({"country": "IN"}, "P130164"),
                                               ({"sector": "water"}, "P156634"), ({"sector": "transport"}, "P130164")],
                         ids=["kenya", "india", "water", "transport"])
def test_country_and_sector_filters_keep_only_their_projects_passages(engine, filters, project):
    result = search(engine, query="procurement delays contracts", **filters)

    assert result["rows"] and {row["project_id"] for row in result["rows"]} == {project}


def test_a_document_type_filter_takes_the_short_name_and_keeps_only_that_type(engine):
    result = search(engine, query="implementation progress rating", document_type="ISR", project_id="P156634")

    assert result["rows"] and {row["document_type"] for row in result["rows"]} == {
        "Implementation Status and Results Report"}
    assert result["filters"]["document_type"] == "Implementation Status and Results Report"


def test_a_published_date_filter_keeps_only_passages_public_in_its_window(engine):
    result = search(engine, query="road works completed", project_id="P130164", published_from="2016-01-01",
                    published_until="2016-12-31")

    assert result["rows"] and all("2016-01-01" <= row["public_from"] <= "2016-12-31" for row in result["rows"])


def test_limit_caps_the_rows_and_the_coverage_line_says_how_many_more_matched(engine):
    result = search(engine, query=REBIDDING, project_id="P130164", limit=3)

    assert len(result["rows"]) == 3
    below = [entry for entry in result["coverage"]["not_used"] if entry["reason"] == "ranked_below_limit"]
    assert below and below[0]["count"] == result["coverage"]["matched"] - 3


@pytest.mark.parametrize("arguments, reason", [
    ({"document_type": "Board Report"}, "unknown_document_type"),
    ({"sector": "energy"}, "unknown_sector"),
    ({"project_id": "P999999"}, "no_match"),
], ids=["document-type", "sector", "nothing-matches"])
def test_an_unknown_filter_or_no_match_abstains_with_its_reason(engine, arguments, reason):
    result = search(engine, query=REBIDDING, **arguments)

    assert result["rows"] == [] and result["abstention"]["reason"] == reason


@pytest.fixture
def flagged():
    """A fresh run over P130164's ICR Reviews and ICR, with a shield that flags the ICR's paragraph 54."""
    from strata.config import load_thresholds
    from strata.knowledge.shields import Scan
    from strata.lakehouse import catalog, passages

    class FlagsParagraph54:
        name = "test shield"

        def scan(self, texts):
            return [Scan(value("icr-para-54")["quote"] in text, "flagged by the test") for text in texts]

    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 3
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        passages.run_on_fixture(engine, projects=["P130164"], thresholds=limits, shield=FlagsParagraph54())
        yield engine


def test_a_passage_prompt_shields_flagged_is_left_out_and_the_coverage_line_says_why(flagged):
    result = search(flagged, query=REBIDDING, project_id="P130164")

    assert all(row["paragraph"] != "54" or row["document_type"] != ICR for row in result["rows"])
    [held_back] = [entry for entry in result["coverage"]["not_used"] if entry["reason"] == "prompt_shields_hit"]
    assert held_back["count"] == 1 and held_back["evidence_ids"][0].endswith("/v1/54")
