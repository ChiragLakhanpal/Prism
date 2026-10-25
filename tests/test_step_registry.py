"""The step-label registry (ticket 27; the 27 brief, section 5): STEP's steps for each method family.

web/src/steps.ts is the registry, and src/strata/estimates/steps.json is the server's copy of it, which the lint
lane keeps equal to it (web/lint/server-copy.ts). These tests read the copy and hold it to three sources it must
not drift from: the blueprint's "Step labels taken from STEP", src/strata/reader/step.py's STEP names (so each name
is defined once, CLAUDE.md rule 4), and the step names in the fixtures' own exports for each family's table.
"""

import html
import re
from pathlib import Path

import pytest

from strata.estimates import step_dates
from strata.lakehouse.engine import DuckDBEngine
from strata.reader import step

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "docs" / "blueprint" / "strata-blueprint.html").read_text()
# The blueprint's three families, by the bold words that open each paragraph, and the registry's key for each.
BLUEPRINT_FAMILIES = {"Goods, works and non-consulting services": "goods", "Consulting firms": "firms",
                      "Individual consultants": "individuals"}


def blueprint_labels() -> dict[str, list[str]]:
    section = BLUEPRINT[BLUEPRINT.index("<h3>Step labels taken from STEP</h3>"):]
    found = {}
    for name, key in BLUEPRINT_FAMILIES.items():
        match = re.search(rf"<b>{re.escape(name)}:</b>([^<]+)</p>", section)
        found[key] = [label.strip().rstrip(".") for label in html.unescape(match.group(1)).split("→")]
    return found


def test_each_familys_labels_are_the_blueprints_step_labels_word_for_word_and_in_order():
    families = step_dates.families()

    assert {key: [entry["label"] for entry in family["steps"]] for key, family in families.items()} == blueprint_labels()


def test_each_step_name_is_one_of_steps_names_and_each_family_keeps_steps_order():
    for key, family in step_dates.families().items():
        names = [entry["step_name"] for entry in family["steps"]]
        assert set(names) <= set(step.STEPS), key
        assert names == sorted(names, key=step.STEPS.index), key


def test_the_blueprints_example_full_name_is_the_bid_evaluation_reports():
    goods = {entry["label"]: entry["step_name"] for entry in step_dates.families()["goods"]["steps"]}

    assert "Bid Evaluation Report and Recommendation for Award" in BLUEPRINT
    assert goods["Bid evaluation report"] == "Bid Evaluation Report and Recommendation for Award"


@pytest.fixture(scope="module")
def db(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def test_each_familys_full_names_are_copied_from_the_fixtures_exports_of_its_table(db):
    """STEP's full names come only from the fixtures' exports: every name a family uses appears as a step of a
    plan table of that family's kind. A family the fixtures hold no table for would fail here."""
    for key, family in step_dates.families().items():
        sections = family["sections"]
        exported = {row[0] for row in db.run(
            "SELECT DISTINCT s.step FROM strata.silver.plan_steps AS s JOIN strata.silver.plan_rows AS r"
            " ON r.document_id = s.document_id AND r.activity_reference_no = s.activity_reference_no"
            " WHERE array_contains(split(:sections, ','), r.section)", {"sections": ",".join(sections)}).rows}
        assert {entry["step_name"] for entry in family["steps"]} <= exported, key


def test_the_families_split_steps_plan_tables_so_each_table_belongs_to_exactly_one_family():
    sections = [section for family in step_dates.families().values() for section in family["sections"]]

    assert sorted(sections) == sorted(step.SECTIONS)


@pytest.mark.parametrize("section, method, family", [
    ("INDIVIDUAL CONSULTANTS", "Direct Selection", "individuals"),
    ("CONSULTING FIRMS", "Direct Selection", "firms"),
    ("NON CONSULTING SERVICES", "Direct Selection", "goods"),
    ("INDIVIDUAL CONSULTANTS", "Individual Consultant Selection", "individuals"),
])
def test_a_package_in_a_plan_takes_the_family_of_its_step_table_whatever_its_method(section, method, family):
    assert step_dates.family_for(None, method, section) == (family, None)


def test_with_no_plan_row_consultant_services_under_direct_selection_stays_with_consulting_firms():
    """A sentence cannot tell a firm from an individual, so the first family that lists the pair wins."""
    assert step_dates.family_for("Consultant Services", "Direct Selection") == ("firms", None)


@pytest.mark.parametrize("category, method, family", [
    ("Works", "Request for Bids", "goods"),
    ("Goods", "Request for Quotations", "goods"),
    ("Non-consulting Services", "Request for Bids", "goods"),
    ("Consultant Services", "Quality And Cost-Based Selection", "firms"),
    ("Consultant Services", "Individual Consultant Selection", "individuals"),
])
def test_the_family_rule_picks_a_family_from_the_category_and_the_method(category, method, family):
    assert step_dates.family_for(category, method) == (family, None)


@pytest.mark.parametrize("category, method, reason", [
    (None, "Request for Bids", "no_family"),
    ("Works", None, "no_family"),
    ("Works", "Quality Based Selection", "method_not_listed"),
])
def test_a_package_with_no_category_or_method_has_no_family_and_an_unlisted_method_is_outside_them(
        category, method, reason):
    assert step_dates.family_for(category, method) == (None, reason)


def test_every_family_ends_ran_longest_at_its_signed_contract_and_only_the_first_step_has_no_stage():
    for key, family in step_dates.families().items():
        keys = [entry["key"] for entry in family["steps"]]
        assert family["longest_through"] == "contract_signed" and "contract_signed" in keys, key
        assert [entry["stage"] is None for entry in family["steps"]] == [True] + [False] * (len(keys) - 1), key
