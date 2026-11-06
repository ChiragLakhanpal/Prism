"""The labeled set retrieval is measured on (ticket 32), at seam 1: the weekly retrieval run reads the silver
labels from the documents the fixture holds, the ICR Review's "ICR para N" citations and the PADs' lessons
sections, and records each query set's size.

The expected counts and pages are in tests/ground_truth/values.toml ([silver_labels]), read from the recorded
documents apart from Prism's code; the first two tests check them word for word on their pages.
"""

import re
import tomllib
from pathlib import Path

import pytest

from strata.fixture import recorded as fmt
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded"
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["silver_labels"]
CITATIONS, LESSONS = TRUTH["icr_review_citations"], TRUTH["pad_lessons"]


def page_text(document: str, number: int) -> str:
    return re.sub(r"\s+", " ", fmt.pages(RECORDED / f"{document}.pages.txt")[number - 1])


def on_page(quote: str, document: str, number: int) -> bool:
    return re.sub(r"\s+", " ", quote) in page_text(document, number)


@pytest.mark.parametrize("document", CITATIONS["documents"])
def test_both_versions_of_the_icr_review_print_each_citation_on_its_page(document):
    missing = [citation["quote"] for citation in CITATIONS["citations"]
               if not on_page(citation["quote"], document, citation["pdf_page"])]
    assert missing == []
    assert len(CITATIONS["citations"]) == CITATIONS["queries"]
    assert len({p for citation in CITATIONS["citations"] for p in citation["paragraphs"]}) == CITATIONS["labels"]


def test_each_pad_prints_its_lessons_heading_over_the_section_and_in_its_contents():
    for section in LESSONS["sections"]:
        assert on_page(section["quote"], section["document"], section["pdf_page"])
        assert on_page(section["last_quote"], section["document"], section["last_pdf_page"])
        contents = page_text(section["document"], section["contents_page"]).lower()
        assert "lessons learned and reflected in the project design" in contents and "....." in contents
    assert sum(len(section["paragraphs"]) for section in LESSONS["sections"]) == LESSONS["labels"]


def query(fixture_db, sql: str) -> list[dict]:
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run(sql, {})
        return [dict(zip(result.columns, row)) for row in result.rows]


LATEST_BUILD = "(SELECT build_id FROM strata.ops.retrieval_label_builds ORDER BY built_at DESC, build_id DESC LIMIT 1)"


def test_the_weekly_run_records_the_size_of_each_silver_query_set(fixture_db):
    sizes = {row["query_set"]: (row["queries"], row["labels"], row["documents"]) for row in query(
        fixture_db, f"SELECT * FROM strata.ops.retrieval_label_builds WHERE build_id = {LATEST_BUILD}")}

    assert sizes["icr_review_citations"] == (CITATIONS["queries"], CITATIONS["labels"], CITATIONS["reports"])
    assert sizes["pad_lessons"] == (LESSONS["queries"], LESSONS["labels"], LESSONS["reports"])


def test_each_citation_labels_the_icr_paragraphs_it_names_and_no_annex_paragraph(fixture_db):
    rows = query(fixture_db, "SELECT query_id, query_text, query_date, project_id, passage_id, grade, origin "
                             f"FROM strata.ops.retrieval_labels WHERE build_id = {LATEST_BUILD} "
                             "AND query_set = 'icr_review_citations' ORDER BY query_id, passage_id")
    by_query: dict[str, list[str]] = {}
    for row in rows:
        by_query.setdefault(row["query_id"], []).append(row["passage_id"])

    expected = sorted(sorted(f"31525018/v1/{n}" for n in citation["paragraphs"]) for citation in CITATIONS["citations"])
    assert sorted(by_query.values()) == expected
    assert {(row["grade"], row["origin"], row["project_id"]) for row in rows} == {(2, "icr_review_citation", "P130164")}
    # Dated by the first version, so the re-issue adds no second query.
    assert {row["query_date"].isoformat() for row in rows} == {"2020-03-27"}
    rebidding = next(row for row in rows if row["passage_id"] == "31525018/v1/54")
    # The citing sentence and the one before it, without the citation itself.
    assert rebidding["query_text"] == ("The works contract estimates were not based on market rate. This resulted in "
                                       "rebidding of one-third of the contracts (108 out of 328).")


def test_each_pad_lessons_section_labels_its_paragraphs_and_not_its_table_of_contents(fixture_db):
    rows = query(fixture_db, "SELECT query_id, project_id, query_date, passage_id FROM strata.ops.retrieval_labels "
                             f"WHERE build_id = {LATEST_BUILD} AND query_set = 'pad_lessons'")
    found = {(row["project_id"], row["passage_id"].split("/")[-1]) for row in rows}

    assert found == {(section["project"], str(n)) for section in LESSONS["sections"] for n in section["paragraphs"]}
    # Each PAD's query is dated the day after the PAD became public (stress_shelf.pad_disclosed and
    # pad-p156634-disclosed), the first day a search that uses only documents public before its query's date
    # can find it.
    assert {(row["project_id"], row["query_date"].isoformat()) for row in rows} == {
        ("P130164", "2013-11-07"), ("P156634", "2017-07-26")}
