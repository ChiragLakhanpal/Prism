"""Assertions and disagreements at seam 1, the lakehouse run over the fixture (ticket 20).

Ratings, dates and amounts from records and documents become dated assertions in strata.gold.assertion,
and the run finds the disagreements between them in strata.gold.disagreement, with the assertion the
evidence ladder (config/evidence_ladder.toml) leans on. Expected values come from
tests/ground_truth/values.toml, which quotes each ISR, the ICR and the ICR Reviews with their pages,
never from the code.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
ISR = "Implementation Status and Results Report"


def value(key: str):
    return TRUTH[key]["value"]


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def isr_assertions(engine, attribute="pdo_progress") -> list[dict]:
    return rows(engine, "SELECT * FROM strata.gold.assertion WHERE subject_id = :subject AND attribute = :attribute "
                        "AND document_type = :isr ORDER BY made_at", subject="P130164", attribute=attribute, isr=ISR)


# ── Assertions ───────────────────────────────────────────────────────────

def test_each_isr_rates_progress_for_the_period_since_the_isr_before_it(engine):
    found = isr_assertions(engine)

    assert [row["value"] for row in found] == [value(f"isr-{n}-rating") for n in range(1, 14)]
    assert [row["made_at"] for row in found] == [value(f"isr-{n}-date") for n in range(1, 14)]
    assert [row["sequence"] for row in found] == list(range(1, 14))
    isr_7 = found[6]
    assert isr_7["field_name"] == "Progress towards achievement of PDO"
    assert (isr_7["period_start"], isr_7["period_end"]) == (value("isr-6-date") + dt.timedelta(days=1),
                                                            value("isr-7-date"))
    assert isr_7["public_from"] == value("isr-7-date")
    assert (isr_7["evidence_tier"], isr_7["form"]) == ("isr", "rating_field")
    # The passage ticket 18 issued for ISR 7's overall ratings, on its first page, which a claim cites.
    assert isr_7["evidence_id"] == "strata.gold.passage:26733307/v1/s4"
    assert isr_7["pdf_page"] == TRUTH["isr-7-rating"]["pdf_page"]


def by_document(engine, document_id: str) -> dict[str, dict]:
    return {row["attribute"]: row for row in rows(
        engine, "SELECT * FROM strata.gold.assertion WHERE document_id = :document_id", document_id=document_id)}


def test_the_icrs_account_of_the_mid_term_review_is_an_assertion_about_that_moment(engine):
    """The batch model read paragraph 78 (tests/fixtures/azure/batch_assertions.json); its quote was found
    word for word on PDF page 27, and the mid-term review's date comes from the ISRs' key dates."""
    paragraph = by_document(engine, "31525018")["pdo_progress"]

    assert (paragraph["subject_kind"], paragraph["subject_id"]) == ("project", "P130164")
    assert (paragraph["value_form"], paragraph["judgment"]) == ("judgment", "unsatisfactory")
    assert paragraph["period_event"] == "mid_term_review"
    assert paragraph["period_start"] == paragraph["period_end"] == value("isr-7-mid-term-review")
    assert value("mid-term-review") == value("isr-7-mid-term-review")
    assert paragraph["made_at"] == value("icr-date")
    assert paragraph["public_from"] == value("icr-disclosed")
    assert (paragraph["evidence_tier"], paragraph["form"]) == ("icr", "narrative")
    assert paragraph["evidence_id"] == "strata.gold.passage:31525018/v1/78"
    assert paragraph["pdf_page"] == TRUTH["icr-para-78"]["pdf_page"]
    assert paragraph["quote"] == value("icr-para-78")
    assert paragraph["read_by"].startswith("gpt-5.4-nano")


def test_an_extracted_assertion_whose_quote_is_not_on_its_cited_page_is_rejected_and_counted(engine):
    """The recording plants one outcome rating whose words are not in paragraph 45. It never becomes an
    assertion, and the run counts it with its reason in strata.ops.assertion_rejections."""
    rejected = rows(engine, "SELECT * FROM strata.ops.assertion_rejections WHERE project_id = :project_id",
                    project_id="P130164")
    outcome = rows(engine, "SELECT value, quote FROM strata.gold.assertion WHERE document_id = :document_id "
                           "AND attribute = :attribute", document_id="31525018", attribute="outcome")

    assert [(row["document_id"], row["passage_id"], row["reason"]) for row in rejected] == [
        ("31525018", "31525018/v1/45", "quote_not_on_page")]
    assert rejected[0]["quote"] == "the overall outcome is rated Moderately Satisfactory"
    assert rejected[0]["public_from"] == value("icr-disclosed")
    assert outcome == [{"value": "Moderately Unsatisfactory",
                        "quote": "the overall outcome is rated Moderately Unsatisfactory"}]


def test_each_version_of_the_icr_review_keeps_its_ratings_and_the_reissue_replaces_the_first(engine):
    """Both ICR Reviews are report ICRR0021929. The re-issue of May 4, 2023 replaces the version of March 27,
    2020 from the day it became public (ticket 11's rule), and the first version's "Efficiency Rating ---"
    is no rating."""
    first, reissue = by_document(engine, "31906731"), by_document(engine, "34056616")

    assert set(first) == {"outcome", "bank_performance", "me_quality"}
    assert set(reissue) == {"outcome", "bank_performance", "me_quality", "efficiency"}
    assert reissue["efficiency"]["value"] == value("icr-review-efficiency-2023")
    assert {row["replaced_on"] for row in first.values()} == {value("icr-review-reissue-date")}
    assert {row["replaced_on"] for row in reissue.values()} == {None}
    assert {(row["report_number"], row["version"], row["evidence_tier"]) for row in first.values()} == {
        (value("icr-review-number-2020"), 1, "ieg")}
    assert {(row["report_number"], row["version"]) for row in reissue.values()} == {(value("icr-review-number-2023"), 2)}
    assert {row["made_at"] for row in reissue.values()} == {value("icr-review-reissue-date")}


def test_the_ieg_ratings_dataset_gives_iegs_ratings_of_the_whole_project_and_agrees_with_the_icr_review(engine):
    """The IEG ratings dataset repeats IEG's ratings, so its row is in the ieg tier, a rating in its own field
    with the dataset's field name. It gives no date, so it is public from June 30 of its evaluation year
    (ticket 17). Its ratings match the ICR Review's, so it is in no disagreement."""
    found = {row["attribute"]: row for row in rows(
        engine, "SELECT * FROM strata.gold.assertion WHERE source_key = :source AND subject_id = :subject",
        source="ieg_ratings", subject="P130164")}

    assert {key: row["value"] for key, row in found.items()} == {
        "outcome": value("ieg-outcome-p130164"), "bank_performance": value("ieg-bank-performance-p130164"),
        "me_quality": value("ieg-me-quality-p130164")}
    outcome = found["outcome"]
    assert (outcome["field_name"], outcome["evidence_tier"], outcome["form"]) == ("outcome", "ieg", "rating_field")
    assert outcome["evidence_id"] == "strata.gold.ieg_rating:P130164/ICRR/2020"
    assert outcome["made_at"] == outcome["public_from"] == dt.date(value("ieg-evaluation-fy-p130164"), 6, 30)
    assert outcome["period_event"] == "whole_project"
    icr = by_document(engine, "31525018")["outcome"]
    assert (outcome["period_start"], outcome["period_end"]) == (icr["period_start"], icr["period_end"])
    sides = rows(engine, "SELECT a.assertion_id FROM strata.gold.disagreement AS d JOIN strata.gold.assertion AS a "
                         "ON a.assertion_id IN (d.first_assertion_id, d.second_assertion_id) WHERE a.source_key = :source",
                 source="ieg_ratings")
    assert sides == []


def test_the_run_reads_the_records_of_every_project_it_holds_records_for(engine):
    """A project's records are read whether or not Strata has read its documents."""
    with_records = {row["project_id"] for row in rows(
        engine, "SELECT DISTINCT project_id FROM strata.gold.contract WHERE step_reference IS NOT NULL "
                "AND contract_signing_date IS NOT NULL AND source <> :notices", notices="notices")}
    asserted = {row["project_id"] for row in rows(
        engine, "SELECT DISTINCT project_id FROM strata.gold.assertion WHERE form = :form", form="contract_record")}

    assert len(with_records) > 1
    assert with_records <= asserted


# ── Disagreements ────────────────────────────────────────────────────────

ISR_7 = "strata.gold.passage:26733307/v1/s4#P130164/pdo_progress"
PARAGRAPH_78 = "strata.gold.passage:31525018/v1/78#P130164/pdo_progress"


def disagreements(engine, subject_id: str) -> list[dict]:
    return rows(engine, "SELECT * FROM strata.gold.disagreement WHERE subject_id = :subject_id "
                        "ORDER BY attribute, public_from", subject_id=subject_id)


def test_isr_7_and_the_icrs_paragraph_78_are_one_disagreement_and_the_ladder_leans_on_the_icr(engine):
    """Criterion 1 at seam 1: the mid-term review (May 16, 2016) falls in ISR 7's period, the day after ISR 6
    to August 26, 2016, and in no other ISR's. Satisfactory and "part of the PDO was compromised" cannot both
    be true, and progress towards the PDO is an outcome judgment, so the ICR outranks the ISR."""
    found = [row for row in disagreements(engine, "P130164") if row["attribute"] == "pdo_progress"]

    assert [(row["first_assertion_id"], row["second_assertion_id"]) for row in found] == [(ISR_7, PARAGRAPH_78)]
    [paragraph] = found
    assert (paragraph["lean_assertion_id"], paragraph["rule_id"]) == (PARAGRAPH_78, "outcome")
    assert paragraph["period_event"] == "mid_term_review"
    assert paragraph["period_start"] == paragraph["period_end"] == value("mid-term-review")
    assert paragraph["public_from"] == value("icr-disclosed")
    assert paragraph["replaced_on"] is None


def test_isr_ratings_of_successive_periods_never_disagree_with_each_other(engine):
    """Criterion 2 at seam 1: ISRs 1 to 13 rate successive periods, so a changed rating is a trajectory."""
    between_isrs = rows(engine, "SELECT d.disagreement_id FROM strata.gold.disagreement AS d "
                                "JOIN strata.gold.assertion AS a ON a.assertion_id = d.first_assertion_id "
                                "JOIN strata.gold.assertion AS b ON b.assertion_id = d.second_assertion_id "
                                "WHERE a.evidence_tier = :isr AND b.evidence_tier = :isr", isr="isr")

    assert len(isr_assertions(engine)) == 13
    assert between_isrs == []


def test_the_reissued_icr_reviews_efficiency_rating_disagrees_with_the_icrs_and_ieg_outranks_the_icr(engine):
    """The ICR rated efficiency Substantial (paragraph 44); the 2023 re-issue of the ICR Review rated it Modest.
    The 2020 version gave no efficiency rating, so it is in no disagreement."""
    [efficiency] = [row for row in disagreements(engine, "P130164") if row["attribute"] == "efficiency"]

    assert efficiency["first_assertion_id"] == "strata.gold.passage:31525018/v1/44#P130164/efficiency"
    assert efficiency["second_assertion_id"] == "strata.gold.passage:34056616/v2/5#P130164/efficiency"
    assert (efficiency["lean_assertion_id"], efficiency["rule_id"]) == (efficiency["second_assertion_id"], "outcome")
    assert efficiency["public_from"] == value("icr-review-reissue-date")


def test_every_assertion_has_its_subject_attribute_value_period_dates_source_and_evidence_tier(engine):
    """Criterion 8: the schema every assertion keeps (spec, "The knowledge model")."""
    required = ("assertion_id", "subject_kind", "subject_id", "project_id", "attribute", "attribute_kind",
                "field_name", "value", "value_form", "period_event", "period_start", "period_end", "made_at",
                "public_from", "evidence_tier", "form", "source_key", "document_id", "passage_id", "evidence_id",
                "read_by")
    found = rows(engine, "SELECT * FROM strata.gold.assertion")

    assert len(found) > 13
    missing = [(row["assertion_id"], column) for row in found for column in required if row[column] in (None, "")]
    assert missing == []
    assert {row["evidence_tier"] for row in found} <= {"pad", "isr", "icr", "ieg", "record"}
    assert {row["subject_kind"] for row in found} <= {"project", "package"}
    assert all(row["period_start"] <= row["period_end"] for row in found)
    assert len({row["assertion_id"] for row in found}) == len(found)
