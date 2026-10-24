"""get_disagreements at seam 2, the tool contract (ticket 20).

The tool is called by name through the registry (config/tools.toml), as a viewer, with an optional
as-of date. For a subject it returns each disagreement with both sides in the order written, the side
Strata leans on, the ladder's rule, and what changes if you keep the other, plus the trajectories and
the count of assertions the run rejected. Expected values come from tests/ground_truth/values.toml,
never from the code.
"""

import datetime as dt
import shutil
import tomllib
from pathlib import Path

import pytest

from strata import config
from strata.dbx import Viewer
from strata.knowledge import assertions
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
ISR_7 = "strata.gold.passage:26733307/v1/s4#P130164/pdo_progress"
PARAGRAPH_78 = "strata.gold.passage:31525018/v1/78#P130164/pdo_progress"


def value(key: str):
    return TRUTH[key]["value"]


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def get_disagreements(engine, **arguments):
    return registry.call("get_disagreements", arguments, registry.Context(engine=engine, viewer=ANA))


def about(result, attribute: str) -> list[dict]:
    return [row for row in result["rows"] if row["attribute"] == attribute]


# ── The showcase disagreement ────────────────────────────────────────────

def test_isr_7_and_the_icrs_paragraph_78_come_back_as_one_disagreement_leaning_on_the_icr(engine):
    """Criterion 1: both sides in the order written, Strata leaning on the ICR under the outcome-judgment rule,
    and what changes if you keep ISR 7."""
    result = get_disagreements(engine, subject_id="P130164")

    [row] = about(result, "pdo_progress")
    isr_7, paragraph = row["sides"]
    assert [isr_7["assertion_id"], paragraph["assertion_id"]] == [ISR_7, PARAGRAPH_78]
    assert (row["lean_assertion_id"], row["other_assertion_id"], row["rule_id"]) == (PARAGRAPH_78, ISR_7, "outcome")
    assert row["evidence_id"] == f"strata.gold.disagreement:{row['disagreement_id']}"
    assert row["period"] == {"event": "mid_term_review", "start": value("mid-term-review").isoformat(),
                             "end": value("mid-term-review").isoformat()}
    # ISR 7 keeps the report's own field name and its rating, word for word.
    assert (isr_7["field_name"], isr_7["value"]) == ("Progress towards achievement of PDO", value("isr-7-rating"))
    assert (isr_7["made_at"], isr_7["evidence_tier"], isr_7["sequence"]) == (value("isr-7-date").isoformat(), "isr", 7)
    assert isr_7["evidence_id"] == "strata.gold.passage:26733307/v1/s4"
    assert isr_7["months_after_event"] == 3  # rated three months after the mid-term review (blueprint)
    assert (paragraph["quote"], paragraph["pdf_page"]) == (value("icr-para-78"), TRUTH["icr-para-78"]["pdf_page"])
    assert (paragraph["made_at"], paragraph["public_from"]) == (value("icr-date").isoformat(),
                                                                value("icr-disclosed").isoformat())
    assert (paragraph["evidence_tier"], paragraph["judgment"]) == ("icr", "unsatisfactory")
    assert row["if_you_keep"] == {"assertion_id": ISR_7, "attribute": "pdo_progress", "value": value("isr-7-rating"),
                                  "value_form": "rating", "judgment": "satisfactory",
                                  "field_name": "Progress towards achievement of PDO", "period_event": "mid_term_review"}


def test_isrs_1_to_13_come_back_as_a_trajectory_not_a_disagreement(engine):
    """Criterion 2: ISRs 1 to 9 Satisfactory, 10 and 11 Moderately Satisfactory, 12 and 13 Moderately
    Unsatisfactory."""
    result = get_disagreements(engine, subject_id="P130164")

    [trajectory] = [item for item in result["trajectories"] if item["attribute"] == "pdo_progress"]
    assert trajectory["field_name"] == "Progress towards achievement of PDO"
    assert [point["value"] for point in trajectory["points"]] == [value(f"isr-{n}-rating") for n in range(1, 14)]
    assert [(run["value"], run["first_sequence"], run["last_sequence"]) for run in trajectory["runs"]] == [
        (value("isr-1-rating"), 1, 9), (value("isr-10-rating"), 10, 11), (value("isr-12-rating"), 12, 13)]
    assert not any(side["evidence_tier"] == "isr" for row in result["rows"] for side in row["sides"]
                   if all(other["evidence_tier"] == "isr" for other in row["sides"]))


@pytest.mark.parametrize("as_of", ["2019-10-01", "2019-11-01"], ids=["before-the-icr-was-dated", "before-it-was-public"])
def test_before_the_icr_was_public_no_disagreement_comes_back_for_the_project(engine, as_of):
    """Criterion 3: the ICR is dated October 10, 2019 but became public on November 2, 2019, so as of
    either date before that, nothing disagrees with ISR 7. The ISRs' trajectory is still there."""
    result = get_disagreements(engine, subject_id="P130164", as_of=as_of)

    assert result["rows"] == []
    assert result["abstention"] is None
    assert [item["attribute"] for item in result["trajectories"] if item["attribute"] == "pdo_progress"]
    assert result["rejected"]["count"] == 0


def test_the_2023_reissue_of_the_icr_review_replaces_the_2020_version_for_current_answers(engine):
    """Criterion 6: today the efficiency disagreement rests on the re-issue (May 4, 2023), and no answer cites
    the March 27, 2020 version. As of a date between the two, the 2020 version was current, and it gave no
    efficiency rating, so nothing disagreed about efficiency."""
    today = get_disagreements(engine, subject_id="P130164")
    between = get_disagreements(engine, subject_id="P130164", as_of="2022-01-01")

    [efficiency] = about(today, "efficiency")
    assert [side["document_id"] for side in efficiency["sides"]] == ["31525018", "34056616"]
    assert efficiency["sides"][1]["made_at"] == value("icr-review-reissue-date").isoformat()
    assert efficiency["lean_assertion_id"] == efficiency["sides"][1]["assertion_id"]
    assert "31906731" not in {side["document_id"] for row in today["rows"] for side in row["sides"]}
    assert about(between, "efficiency") == []
    assert [row["attribute"] for row in between["rows"]] == ["pdo_progress"]


def test_the_rejected_assertion_is_counted_for_the_project(engine):
    """Criterion 7 at seam 2: the timeline states how many assertions the run left out (brief 23)."""
    result = get_disagreements(engine, subject_id="P130164")

    assert result["rejected"] == {"count": 1, "reasons": [{"reason": "quote_not_on_page", "count": 1}]}


def test_a_subject_strata_does_not_hold_is_an_abstention(engine):
    result = get_disagreements(engine, subject_id="P999999")

    assert result["rows"] == [] and result["trajectories"] == []
    assert result["abstention"] == {"reason": "unknown_subject", "subject_id": "P999999"}
