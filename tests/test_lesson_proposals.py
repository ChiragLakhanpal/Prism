"""Proposed lessons at seam 1, the lakehouse run over the fixture (ticket 29).

The nightly job's propose_lessons task sends each current ICR, ICR Review and PPAR of the slice to the
batch model (gpt-5.4-nano on Global Batch; offline, its recorded answers in
tests/fixtures/azure/lesson_batch.json), reads back the lessons it proposes, and keeps a proposal only
when its quote is word for word on the page it cites. The check rejects and never repairs. An ICR
Review's restatement of an ICR's lesson attaches as a second piece of evidence, and each passing
proposal waits in the review queue.

Expected values come from tests/ground_truth/values.toml, which quotes the documents with their
pages, and from the 29 design brief's section 13.
"""

import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
ICR_54 = "31525018/v1/54"
REVIEW_10B = "34056616/v2/10.b"


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def proposal(engine, passage_id: str) -> dict:
    [found] = rows(engine, "SELECT * FROM strata.silver.lesson_proposals WHERE passage_id = :passage_id",
                   passage_id=passage_id)
    return found


def test_extraction_proposes_the_rebidding_lesson_from_icr_paragraph_54_on_page_23_with_its_quote(engine):
    paragraph = VALUES["icr-para-54"]
    found = proposal(engine, ICR_54)

    assert found["statement"] == "Base works estimates on market rates to avoid rebidding"
    assert found["cited_page"] == paragraph["pdf_page"] == 23
    assert paragraph["value"] in found["quote"]
    assert found["quote_check"] == "passed"
    assert found["project_id"] == paragraph["project"]
    assert found["risk_factors"] == '["cost_estimates"]'
    assert (found["stage"], found["kind"]) == ("procurement_planning", "did_not_work")


def test_the_icr_review_s_restatement_attaches_as_a_second_piece_of_evidence_restated_by_ieg(engine):
    restatement = VALUES["icr-review-2023-restates-para-54"]
    lesson = proposal(engine, ICR_54)

    evidence = rows(engine, "SELECT * FROM strata.silver.lesson_evidence WHERE proposal_id = :proposal_id "
                            "ORDER BY role DESC", proposal_id=lesson["proposal_id"])

    assert [(row["role"], row["passage_id"], row["cited_page"]) for row in evidence] == [
        ("source", ICR_54, 23), ("restatement", REVIEW_10B, restatement["pdf_page"])]
    assert evidence[1]["quote"] == restatement["quote"]
    assert evidence[1]["report_number"] == VALUES["icr-review-number-2023"]["value"]
    assert [row["restated_by_ieg"] for row in evidence] == [False, True]


def test_a_proposal_whose_quote_is_not_on_its_cited_page_is_rejected_and_its_text_is_kept_as_written(engine):
    """The recorded batch answer cites ICR paragraph 78 on page 23, but its words are on page 27
    (values.toml, icr-para-78). The check rejects the proposal; it never moves the page or the quote."""
    paragraph = VALUES["icr-para-78"]
    found = proposal(engine, "31525018/v1/78")

    assert found["quote_check"] == "quote_not_on_page"
    assert found["cited_page"] == 23 != paragraph["pdf_page"]
    assert found["quote"] == paragraph["value"]
    assert rows(engine, "SELECT * FROM strata.silver.lesson_evidence WHERE proposal_id = :proposal_id",
                proposal_id=found["proposal_id"]) == []


def test_the_quote_check_is_counted_with_its_denominator_as_the_lessons_verified_measure(engine):
    [measure] = rows(engine, "SELECT count, denominator, kind FROM strata.ops.data_readiness "
                             "WHERE source = 'documents' AND subject = 'P130164' AND measure = 'lessons_verified'")

    assert (measure["count"], measure["denominator"]) == (3, 4)


def test_each_passing_proposal_waits_in_the_review_queue_for_its_project_s_region(engine):
    queued = rows(engine, "SELECT p.passage_id, i.kind, i.region, i.entered_on "
                          "FROM strata.ops.lesson_review_items AS i "
                          "JOIN strata.silver.lesson_proposals AS p ON p.proposal_id = i.proposal_id "
                          "ORDER BY p.passage_id")

    assert [row["passage_id"] for row in queued] == ["31525018/v1/54", "31525018/v1/55", "34056616/v2/12"]
    assert {row["kind"] for row in queued} == {"new"}
    assert {row["region"] for row in queued} == {"South Asia"}


def test_each_proposal_carries_the_edition_of_the_rules_its_project_s_pad_names(engine):
    """P130164's PAD names the January 2011 Guidelines (values.toml, pad-procurement-guidelines)."""
    assert proposal(engine, ICR_54)["edition_key"] == "guidelines_2011"
