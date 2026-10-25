"""The hindsight test at seam 5 (ticket 34): Strata frozen at a closed project's approval date, its top risks per
package against the risks the completion report later blamed.

The replay harness (src/strata/estimates/harness.py) freezes Strata at each project's approval date, runs the
risk-table builder (ticket 30) for the main packages of the project's first Procurement Plan, and stores what it
showed beside the risks two coders found the ICR blamed. These tests run it two ways:

- On a copy of the fixture database, for the showcase project P130164, with the fixture's three proposed lessons
  decided by two people (tests/lesson_scenario.py). The fixture records none of P130164's Procurement Plans, so a
  hand-made first plan with three works packages stands in for it. ICR paragraphs 54 and 55 are its blamed risks
  (values.toml icr-para-54 and icr-para-55). These tests prove the freeze: nothing public after the approval date
  (values.toml approval-p130164) reaches the frozen risk tables, and the same items do reach them from a later
  cutoff.
- On a small hand-made set of pilot projects in an in-memory database, whose answers are known, for the coding
  tool, the gate set, the report sentence and the release gate. Statistical expectations (the 95 percent interval
  and McNemar's test) were computed once with SciPy and are stored as literals in values.toml's [hindsight].
"""

import datetime as dt
import json
import tomllib
from pathlib import Path

import pytest

import lesson_scenario as scenario
from strata.estimates import harness, hindsight
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}
APPROVED = VALUES["approval-p130164"]["value"]
# The day after the re-issued ICR Review (values.toml icr-review-reissue-date): the ICR and both ICR Reviews are
# public by then, and no lesson had been decided yet.
LATER = VALUES["icr-review-reissue-date"]["value"] + dt.timedelta(days=1)
DECIDED = dt.date(2026, 10, 24)  # after the fixture's proposals (October 23, 2026)
RAN_AT = dt.datetime(2026, 10, 26, 6, tzinfo=dt.UTC)
SHOWCASE = "P130164"
PAD = "18381488"  # values.toml pad-disclosed: public on November 6, 2013, a week after approval
ICR_54 = "strata.gold.passage:31525018/v1/54"
ICR_55 = "strata.gold.passage:31525018/v1/55"
ICR_REVIEW_10B = "strata.gold.passage:34056616/v2/10.b"
# A hand-made first plan for P130164: three works packages under Request for Bids and one smaller goods package.
FIRST_PLAN = "900130164"
PACKAGES = [("IN-HANDMADE-1-CW-RFB", "WORKS", "Upgrading of state highway works", "Request for Bids", "30000000.00"),
            ("IN-HANDMADE-2-CW-RFB", "WORKS", "Road widening works", "Request for Bids", "20000000.00"),
            ("IN-HANDMADE-3-CW-RFB", "WORKS", "Bridge and culvert works", "Request for Bids", "10000000.00"),
            ("IN-HANDMADE-4-GO-RFQ", "GOODS", "Office equipment", "Request for Quotations", "50000.00")]


def insert(engine, table, rows):
    columns = tuple(rows[0])
    engine.insert_rows(table, columns, [tuple(row[column] for column in columns) for row in rows])


def first_plan(engine, project_id, document_id, plan_date, packages):
    insert(engine, "strata.silver.plan_versions", [{
        "document_id": document_id, "project_id": project_id, "implementing_agency": "Hand-made agency",
        "plan_date": plan_date, "disclosed_on": plan_date, "series_order": 1, "previous_document_id": None,
        "is_latest": False, "pdf_pages": 1, "route_b_pages": 0, "text_url": f"https://example.org/{document_id}.txt",
        "pdf_url": f"https://example.org/{document_id}.pdf", "public_from": plan_date}])
    insert(engine, "strata.silver.plan_rows", [{
        "document_id": document_id, "project_id": project_id, "section": section, "activity_reference_no": reference,
        "description": description, "method": method, "estimated_amount_usd": amount, "process_status": "Signed",
        "pdf_page": 1, "parser": "hand-made", "public_from": plan_date}
        for reference, section, description, method, amount in packages])


@pytest.fixture(scope="module")
def showcase(fixture_db, tmp_path_factory):
    """A copy of the fixture with the rebidding, permits and IEG lessons decided, and P130164's hand-made first plan."""
    database = scenario.copy_of(fixture_db, tmp_path_factory.mktemp("hindsight-showcase"))
    for passage in (scenario.REBIDDING, scenario.PERMITS, scenario.IEG_LESSON):
        scenario.decide(database, passage, DECIDED)
    with DuckDBEngine.open(database) as engine:
        first_plan(engine, SHOWCASE, FIRST_PLAN, dt.date(2017, 2, 8), PACKAGES)
    return database


def replay_showcase(database, cutoff, builder=None):
    """One replay of P130164, frozen at cutoff, with its blamed risks from ICR paragraphs 54 and 55."""
    case = hindsight.Case(SHOWCASE, cutoff, "transport", blamed=("cost_estimates", "permits_before_award"), checklist=())
    scorer = hindsight.HindsightScorer({SHOWCASE: case}, **({"builder": builder} if builder else {}))
    window = harness.Window(cutoff, RAN_AT.date(), "project", SHOWCASE)
    with DuckDBEngine.open(database) as engine:
        run_id = harness.new_run_id(scorer.name, RAN_AT)
        harness.replay(engine, scorer, window, OfflineTracker(), run_id, RAN_AT)
        return harness.segments(harness.run_rows(engine, run_id))[("project", SHOWCASE)]


def test_frozen_at_approval_no_passage_lesson_or_record_public_later_reaches_the_risk_tables(showcase):
    frozen = replay_showcase(showcase, APPROVED)
    packages = json.loads(frozen["package_tables"])

    # The three largest packages of the first plan, by estimated amount, each with its own risk table.
    assert [package["step_reference"] for package in packages] == [reference for reference, *_ in PACKAGES[:3]]
    assert dt.date.fromisoformat(frozen["inputs_through"]) <= APPROVED
    every_source = [source for package in packages for row in package["rows"] for source in row["sources"]]
    assert all(dt.date.fromisoformat(source["public_from"]) <= APPROVED for source in every_source)
    assert not any(PAD in source["evidence_id"] for source in every_source)
    assert (frozen["blamed"], frozen["covered"], frozen["shown"]) == (2, 0, 0)

    later = replay_showcase(showcase, LATER)
    shown_later = json.loads(later["package_tables"])
    sources = {source["evidence_id"] for package in shown_later for row in package["rows"] for source in row["sources"]}

    # The same items do reach the tables from a later cutoff, so the freeze is what kept them out.
    assert dt.date.fromisoformat(later["inputs_through"]) > APPROVED
    assert {ICR_54, ICR_55, ICR_REVIEW_10B} <= sources
    assert json.loads(later["shown_keys"]) == ["cost_estimates", "permits_before_award"]
    assert (later["blamed"], later["covered"], later["shown"]) == (2, 2, 2)


def test_a_row_public_after_the_cutoff_stops_the_replay(showcase):
    """A builder that let a later row through would be caught by the harness's frozen reader."""
    from strata.harness.facts import Facts
    from strata.packages.risks import RiskTable

    def leaking(engine, viewer, *, as_of, criteria, words=None, thresholds=None, decided_by=None):
        facts = Facts()
        facts.record(ICR_54, {"evidence_id": ICR_54, "public_from": VALUES["icr-disclosed"]["value"].isoformat()})
        return RiskTable({"rows": [], "empty_reason": "no_lessons", "verifier": None}, facts, None)

    with pytest.raises(harness.LeakageError):
        replay_showcase(showcase, APPROVED, builder=leaking)
