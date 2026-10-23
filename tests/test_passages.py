"""The first documents read into numbered passages: seam 1, the lakehouse run over the fixture.

The gate builds the fixture database by running the passage reader over the recorded documents
(gates/build_fixture.py), so most tests read what that run wrote. Every quoted paragraph, page and
section comes from tests/ground_truth/values.toml, which quotes the documents with their PDF pages,
or from the ticket, never from Strata's code.
"""

import re
import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
ICR = "Implementation Completion and Results Report"


def value(key: str) -> dict:
    return next(entry for entry in GROUND_TRUTH["value"] if entry["id"] == key)


@pytest.fixture(scope="module")
def db(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


ICR_PARAGRAPH = """
SELECT p.*, d.pdf_pages
FROM strata.silver.passages AS p
JOIN strata.silver.documents AS d ON d.document_id = p.document_id
WHERE p.project_id = 'P130164' AND p.document_type = :document_type AND p.paragraph = :paragraph
"""


@pytest.mark.parametrize("key", ["icr-para-54", "icr-para-55", "icr-para-78"])
def test_each_showcase_icr_paragraph_is_exactly_one_passage_on_its_page_and_section_word_for_word(db, key):
    truth = value(key)

    found = rows(db, ICR_PARAGRAPH, document_type=ICR, paragraph=str(truth["paragraph"]))

    assert len(found) == 1, f"ICR ¶{truth['paragraph']} is {len(found)} passages"
    [passage] = found
    assert passage["text"] == truth["quote"] or truth["quote"] in passage["text"]
    assert (passage["pdf_page"], passage["section_path"], passage["printed_page"]) == (
        truth["pdf_page"], truth["section"], truth["printed_page"])
    assert passage["paragraph_numbered"] is True
    assert passage["pdf_pages"] == 66  # the ticket: "on PDF page 23 of 66"


def test_icr_paragraph_54_is_its_whole_paragraph_word_for_word(db):
    truth = value("icr-para-54")

    [passage] = rows(db, ICR_PARAGRAPH, document_type=ICR, paragraph="54")

    assert passage["text"] == truth["quote"]


def test_the_header_prepended_to_icr_paragraph_54_names_the_report_project_country_sector_section_and_page(db):
    [passage] = rows(db, ICR_PARAGRAPH, document_type=ICR, paragraph="54")

    assert passage["header"] == "ICR, P130164, India, roads, III.B, ¶54, p.23"  # the ticket's header, word for word


# The ten fields every passage keeps (docs/PLAN.md section 5), by their columns in silver.passages.
TEN_FIELDS = ("project_id", "document_type", "version", "public_from", "section_path", "paragraph", "pdf_page",
              "printed_page", "language", "parse_route")


def test_every_passage_has_all_ten_fields_filled(db):
    passages = rows(db, f"SELECT passage_id, {', '.join(TEN_FIELDS)} FROM strata.silver.passages")

    assert len(passages) > 0
    empty = [(p["passage_id"], name) for p in passages for name in TEN_FIELDS if p[name] in (None, "")]
    assert empty == []
    assert {p["parse_route"] for p in passages} == {"A"}
    assert {p["language"] for p in passages} == {"en"}  # the documents API lists each of them in English


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def recorded_pages(document: str, first: int, last: int) -> str:
    """The text of PDF pages first to last as the recording read them from the PDF, not as Route A did."""
    from strata.fixture import recorded as fmt

    pages = fmt.pages(ROOT / "data" / "fixture" / "recorded" / f"{document}.pages.txt")
    return " ".join(pages[first - 1:last])


def test_a_paragraph_over_500_tokens_becomes_passages_divided_at_sentence_ends_that_share_its_number(db):
    from strata.reader.passages import tokens

    start, end = value("icr-review-2020-item-10a-start"), value("icr-review-2020-item-10a-end")

    parts = rows(db, "SELECT p.* FROM strata.silver.passages AS p "
                     "JOIN strata.silver.documents AS d ON d.document_id = p.document_id "
                     "WHERE d.project_id = :project AND d.document_type = :document_type AND d.document_date = :date "
                     "AND p.paragraph = :paragraph ORDER BY p.part", project=start["project"],
                 document_type=start["document_type"], date=start["date"], paragraph=start["paragraph"])

    assert len(parts) >= 2
    assert {(p["paragraph"], p["section_path"], p["parts"]) for p in parts} == {
        (start["paragraph"], start["section"], len(parts))}
    assert [p["part"] for p in parts] == list(range(1, len(parts) + 1))
    whole = " ".join(p["text"] for p in parts)
    assert tokens(whole) > 500 and all(p["tokens"] <= 500 for p in parts)
    assert all(re.search(r"[.!?][\"'”’)]*$", p["text"]) for p in parts), "a part ends inside a sentence"
    assert whole.startswith("a. " + start["value"]) and whole.endswith(end["quote"])
    assert (parts[0]["pdf_page"], parts[-1]["last_pdf_page"]) == (start["pdf_page"], end["pdf_page"])
    # Every word between the item's heading on page 11 and its last sentence on page 12, as the PDF has them.
    page_12 = squash(recorded_pages(end["document"], end["pdf_page"], end["pdf_page"]))
    body = page_12[page_12.index(squash("The project was classified")):
                   page_12.index(squash(end["quote"])) + len(squash(end["quote"]))]
    assert squash(whole) == squash("a. " + start["value"]) + body
