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


REPORTS = """
SELECT d.project_id, d.document_type, d.document_date, d.text_paged, d.pdf_pages
FROM strata.silver.documents AS d
"""


def test_the_fixture_run_reads_twenty_documents_through_route_a_and_routes_a_scan_to_route_b(db):
    documents = rows(db, REPORTS)
    read = [d for d in documents if d["text_paged"]]
    dated = {(d["project_id"], d["document_type"], d["document_date"]) for d in read}

    assert len(read) == 20  # the ticket: twenty documents, text-based (Route A)
    for key, document_type in [("icr-date", ICR), ("icr-review-date", "Implementation Completion Report Review"),
                               ("icr-review-reissue-date", "Implementation Completion Report Review"),
                               ("isr-7-date", "Implementation Status and Results Report"),
                               ("isr-12-date", "Implementation Status and Results Report")]:
        assert ("P130164", document_type, value(key)["value"]) in dated, key
    assert sum(d["document_type"] == "Implementation Status and Results Report" and d["project_id"] == "P130164"
               for d in read) == 13  # every ISR of P130164, all published as text
    assert ("P156634", "Project Appraisal Document") in {(d["project_id"], d["document_type"]) for d in read}
    [scan] = [d for d in documents if not d["text_paged"]]
    assert (scan["project_id"], scan["document_type"]) == ("P130164", "Project Appraisal Document")
    routes = rows(db, "SELECT route, count(*) AS pages FROM strata.silver.document_page_routes "
                      "WHERE project_id = 'P130164' AND document_id = (SELECT document_id FROM strata.silver.documents "
                      "WHERE NOT text_paged) GROUP BY route")
    assert routes == [{"route": "B", "pages": scan["pdf_pages"]}]


def measured(engine, subject: str) -> dict[str, dict]:
    found = rows(engine, "SELECT * FROM strata.ops.data_readiness WHERE run_id = 'fixture' AND source = 'documents' "
                         "AND subject = :subject", subject=subject)
    return {row["measure"]: row for row in found}


def test_strata_ops_shows_pages_per_route_and_the_share_whose_paragraph_numbering_was_found(db):
    for project_id in ("P130164", "P156634"):
        found = measured(db, project_id)
        pages = rows(db, "SELECT sum(pdf_pages) AS n FROM strata.silver.documents WHERE project_id = :p",
                     p=project_id)[0]["n"]

        route_a, route_b = found["pages_route_a"], found["pages_route_b"]
        assert route_a["denominator"] == route_b["denominator"] == pages
        assert route_a["count"] + route_b["count"] == pages
        numbering = found["pages_paragraph_numbering_found"]
        assert 0 < numbering["count"] < numbering["denominator"] <= route_a["count"]
        assert all(row["detail"] for row in found.values())
    # P130164's 100-page PAD is a scan, so every one of its pages waits for Route B.
    assert measured(db, "P130164")["pages_route_b"]["count"] >= 100


def test_strata_ops_shows_the_documents_read_the_passages_linked_to_a_project_and_how_fresh_they_are(db):
    found = measured(db, "P130164")

    assert (found["documents_read_route_a"]["count"], found["documents_read_route_a"]["denominator"]) == (16, 17)
    linked = found["passages_linked_to_project"]
    assert linked["count"] == linked["denominator"] > 0  # gold.project holds P130164
    assert found["documents_fresh"]["as_of"] == value("icr-review-reissue-date")["value"]
    assert found["document_contacts_stripped"]["kind"] == "stripped"


def test_every_passage_has_a_stored_prompt_shields_result(db):
    found = rows(db, "SELECT p.passage_id, s.shield, s.attack_detected FROM strata.silver.passages AS p "
                     "LEFT JOIN strata.silver.passage_shields AS s ON s.text_hash = p.text_hash")

    assert found and all(row["attack_detected"] is not None and row["shield"] for row in found)
    for project_id in ("P130164", "P156634"):
        screened, hits = (measured(db, project_id)[name] for name in ("passages_screened",
                                                                       "passages_prompt_shields_hit"))
        assert screened["count"] == screened["denominator"] == hits["denominator"] > 0
        assert (hits["kind"], hits["count"]) == ("screened", 0)


@pytest.fixture
def fresh():
    from strata.lakehouse import catalog

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


class FlagsParagraph54:
    """A shield that finds an attack in the ICR's paragraph 54 and nowhere else."""

    name = "test shield"

    def scan(self, texts):
        from strata.knowledge.shields import Scan

        return [Scan(value("icr-para-54")["quote"] in text, "flagged by the test") for text in texts]


def test_a_prompt_shields_hit_is_kept_with_its_result_and_counted_in_data_readiness(fresh):
    from strata.config import load_thresholds
    from strata.lakehouse import passages

    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 3  # the ICR Reviews and the ICR: enough for paragraph 54
    report = passages.run_on_fixture(fresh, projects=["P130164"], thresholds=limits, shield=FlagsParagraph54())

    flagged = rows(fresh, "SELECT p.paragraph, p.document_type, s.attack_detected, s.detail "
                          "FROM strata.silver.passages AS p JOIN strata.silver.passage_shields AS s "
                          "ON s.text_hash = p.text_hash WHERE s.attack_detected")
    assert flagged == [{"paragraph": "54", "document_type": ICR, "attack_detected": True,
                        "detail": "flagged by the test"}]
    hits = rows(fresh, "SELECT count, denominator FROM strata.ops.data_readiness WHERE run_id = :run_id "
                       "AND measure = 'passages_prompt_shields_hit'", run_id=report.run_id)
    assert hits == [{"count": 1, "denominator": report.passages}]


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
