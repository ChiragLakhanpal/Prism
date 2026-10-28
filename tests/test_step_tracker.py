"""The package's steps as a tracker (ticket 115; spec, seam 3).

GET /api/packages/{step_reference}/steps marks each step done, next, planned, late or unknown, from the package's
plan in its newest version public on the page's as-of date, and gives a late step's days late and a done step's
actual date, so the screen works out no date (CLAUDE.md rule 1). The expected values are worked out by hand in
tests/ground_truth/values.toml's [step_tracker].
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


def recorded(name: str) -> dict:
    """An answer tests/record_steps_api.py recorded from the routes, which tests/test_step_routes.py holds them to."""
    import json

    return json.loads((ROOT / "tests" / "fixtures" / "api" / name).read_text())


def test_on_the_fixture_the_showcase_packages_dated_steps_are_late_and_a_package_from_a_sentence_has_no_dates():
    showcase = recorded("steps-ke-nwwda-541055.json")
    steps = showcase["step_dates"]["steps"]

    assert showcase["as_of"] == KNOWN["showcase_as_of"].isoformat()
    assert [step["state"] for step in steps] == KNOWN["showcase_states"]
    assert [step["late_days"] for step in steps if step["state"] == "late"] == KNOWN["showcase_late_days"]
    assert {step["actual_date"] for step in steps} == {None}
    sentence = recorded("steps-planned-rural-roads.json")["step_dates"]["steps"]
    assert [(step["state"], step["late_days"], step["actual_date"]) for step in sentence] == [("unknown", None, None)] * 6
