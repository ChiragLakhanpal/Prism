"""The package's steps as a tracker (ticket 115; spec, seam 3).

GET /api/packages/{step_reference}/steps marks each step done, next, planned, late or unknown, from the package's
plan in its newest version public on the page's as-of date, its contract's signing public by then, and the plan's
Process Status, and gives a late step's days late and a done step's actual date and its record, so the screen works
out no date (CLAUDE.md rule 1). The expected values are worked out by hand in tests/ground_truth/values.toml's
[step_tracker].
"""

import tomllib
from pathlib import Path

import pytest
import step_set
from test_step_routes import ANA, call, make_app

ROOT = Path(__file__).resolve().parents[1]
KNOWN = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["step_tracker"]


@pytest.fixture(scope="module")
def hand_made(tmp_path_factory):
    folder = tmp_path_factory.mktemp("tracker")
    step_set.build(folder / "set.duckdb").close()
    return make_app(folder / "set.duckdb", folder)


def tracked(app, reference: str, as_of) -> list[dict]:
    answer = call(app, "GET", f"/api/packages/{reference}/steps?asof={as_of.isoformat()}", ANA)
    assert answer.status_code == 200, answer.text
    return answer.json()["step_dates"]["steps"]


@pytest.mark.parametrize("moment", ["before", "late", "signed", "overdue"])
def test_each_step_is_marked_from_the_plan_public_on_the_pages_date(hand_made, moment):
    steps = tracked(hand_made, step_set.TARGET, KNOWN[f"hand_made_{moment}_as_of"])

    assert [step["state"] for step in steps] == KNOWN[f"hand_made_{moment}_states"]
    assert [step["late_days"] for step in steps if step["state"] == "late"] == KNOWN[f"hand_made_{moment}_late_days"]
    assert all(step["late_days"] is None for step in steps if step["state"] != "late")


def test_a_done_step_carries_the_actual_date_its_plan_gives_and_no_other_step_has_one(hand_made):
    steps = tracked(hand_made, step_set.TARGET, KNOWN["hand_made_overdue_as_of"])

    assert [step["actual_date"] for step in steps] == [day.isoformat() if day else None for day in step_set.TARGET_ACTUAL]


def test_a_step_the_plan_left_blank_behind_a_done_step_is_unknown_and_never_late(tmp_path):
    step_set.build(tmp_path / "gap.duckdb", bidding_document_unrecorded=True).close()
    app = make_app(tmp_path / "gap.duckdb", tmp_path)

    steps = tracked(app, KNOWN["gap_reference"], KNOWN["gap_as_of"])

    assert [step["state"] for step in steps] == KNOWN["gap_states"]
    assert [step["late_days"] for step in steps] == [None] * 6


@pytest.fixture(scope="module")
def on_the_fixture(fixture_db, tmp_path_factory):
    return make_app(fixture_db, tmp_path_factory.mktemp("tracker-fixture"))


def test_a_signing_in_the_contract_awards_marks_the_signed_contract_done_once_it_is_public(on_the_fixture):
    """The showcase's plan of October 9, 2026 gives no actual date, but World Bank contract awards data hold its
    contract signed on June 22, 2026: the signing is done, and the steps before it are unknown, never late."""
    reference = "KE-NWWDA-541055-CW-RFB"
    after = tracked(on_the_fixture, reference, KNOWN["showcase_as_of"])
    before = tracked(on_the_fixture, reference, KNOWN["showcase_before_signing_as_of"])

    assert [step["state"] for step in after] == KNOWN["showcase_states"]
    assert [step["late_days"] for step in after if step["state"] == "late"] == KNOWN["showcase_late_days"]
    signed = after[4]
    assert (signed["step_key"], signed["actual_date"], signed["actual_source"]) == (
        "contract_signed", KNOWN["showcase_signed_on"].isoformat(), "contract_awards")
    assert {step["actual_source"] for step in after if step["step_key"] != "contract_signed"} == {None}
    # Before the contract was signed and public, the signing is late against the plan of March 5, 2026.
    assert (before[4]["state"], before[4]["late_days"], before[4]["actual_date"]) == (
        "late", KNOWN["showcase_before_signing_late_days"], None)


def test_a_contract_from_a_record_the_tracker_does_not_name_leaves_the_plans_own_dates(on_the_fixture, monkeypatch):
    """A new source in strata.gold.contract, one tracker.CONTRACT_SOURCES does not name yet, must not fail the steps
    route, which section 2 shares: the signing keeps the plan's own dates, so the showcase's completion and signing
    stand as the plan gives them. Here the contract awards datasets play the new source."""
    from strata.server import tracker

    monkeypatch.setattr(tracker, "CONTRACT_SOURCES", {"notices": tracker.NOTICE})
    answer = call(on_the_fixture, "GET", f"/api/packages/KE-NWWDA-541055-CW-RFB/steps"
                  f"?asof={KNOWN['showcase_as_of'].isoformat()}", ANA)

    assert answer.status_code == 200, answer.text
    signed = answer.json()["step_dates"]["steps"][4]
    assert (signed["step_key"], signed["actual_date"], signed["actual_source"]) == ("contract_signed", None, None)


@pytest.mark.parametrize("status", ["completed", "canceled"])
def test_an_activity_the_plan_says_ended_has_no_late_step_and_says_why(on_the_fixture, status):
    answer = call(on_the_fixture, "GET", f"/api/packages/{KNOWN[f'{status}_reference']}/steps"
                  f"?asof={KNOWN['showcase_as_of'].isoformat()}", ANA).json()["step_dates"]

    assert [step["state"] for step in answer["steps"]] == KNOWN[f"{status}_states"]
    assert {step["late_days"] for step in answer["steps"]} == {None}
    assert answer["status_reason"] == status.capitalize()


def test_a_signed_contracts_steps_up_to_the_signing_are_unknown_without_a_date_and_its_completion_can_be_late():
    """STEP's Process Status Signed says the steps up to the signing happened, so one the plan left without an
    actual date is unknown; the completion is still owed, so its planned date can pass. Dates made up for the case:
    June 30, 2026 to October 28, 2026 is 120 days."""
    import datetime as dt

    from strata.server import tracker

    names = ["Specific Procurement Notice / Invitation", "Bidding Documents as Issued",
             "Proposal Submission / Opening / Minutes", "Bid Evaluation Report and Recommendation for Award",
             "Signed Contract", "Contract Completion"]
    planned = [dt.date(2026, 3, day) for day in (1, 8, 15, 22)] + [dt.date(2026, 3, 31), dt.date(2026, 6, 30)]
    steps = [(day, None, None) for day in planned]

    marked = tracker.marks(steps, dt.date(2026, 10, 28), tracker.settled_through("Signed", names))

    assert [mark["state"] for mark in marked] == ["unknown"] * 5 + ["late"]
    assert marked[5]["late_days"] == 120


def recorded(name: str) -> dict:
    """An answer tests/record_steps_api.py recorded from the routes, which tests/test_step_routes.py holds them to."""
    import json

    return json.loads((ROOT / "tests" / "fixtures" / "api" / name).read_text())


def test_the_recorded_showcase_is_signed_and_late_to_complete_and_a_package_from_a_sentence_has_no_dates():
    showcase = recorded("steps-ke-nwwda-541055.json")
    steps = showcase["step_dates"]["steps"]

    assert showcase["as_of"] == KNOWN["showcase_as_of"].isoformat()
    assert [step["state"] for step in steps] == KNOWN["showcase_states"]
    assert [step["late_days"] for step in steps if step["state"] == "late"] == KNOWN["showcase_late_days"]
    assert [step["actual_date"] for step in steps] == [None] * 4 + [KNOWN["showcase_signed_on"].isoformat(), None]
    sentence = recorded("steps-planned-rural-roads.json")["step_dates"]["steps"]
    assert [(step["state"], step["late_days"], step["actual_date"]) for step in sentence] == [("unknown", None, None)] * 6


def test_the_recorded_consulting_firms_package_has_nine_steps_and_its_completed_plan_leaves_one_unknown():
    """The nine-step tracker the screen tests and the gallery draw (the design review's R2-B1) is the route's own
    answer for a consulting firm's package on the fixture."""
    firms = recorded("steps-ke-cwsb-224323.json")
    dates = firms["step_dates"]

    assert dates["family"] == "firms"
    assert [step["state"] for step in dates["steps"]] == KNOWN["firms_states"]
    assert {step["late_days"] for step in dates["steps"]} == {None}
    assert dates["status_reason"] == "Completed"
