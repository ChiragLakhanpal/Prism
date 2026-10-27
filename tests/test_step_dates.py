"""estimate_time's planned date for each STEP step (ticket 27), through the tool registry (spec, seam 2).

The expected values come from tests/ground_truth/values.toml: [step_dates] for the hand-made set that
tests/step_set.py builds, where every step can be dated, and the plan-229129 values for the re-dated step. On
the fixture every step abstains, because no step has 20 comparable packages whose plans recorded it.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest
import step_set

from strata.config import load_thresholds
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
KNOWN = TRUTH["step_dates"]
VALUES = {entry["id"]: entry for entry in TRUTH["value"]}
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
GOODS = ["bid_invitation", "bidding_document_issued", "bid_opening", "bid_evaluation_report", "contract_signed",
         "contract_completed"]


def call(engine, thresholds=None, **arguments) -> dict:
    context = registry.Context(engine=engine, viewer=ANA, **({"thresholds": thresholds} if thresholds else {}))
    return registry.call("estimate_time", arguments, context)


def by_key(result) -> dict[str, dict]:
    return {entry["step_key"]: entry for entry in result["step_dates"]["steps"]}


@pytest.fixture(scope="module")
def hand_made(tmp_path_factory):
    engine = step_set.build(tmp_path_factory.mktemp("step-set") / "set.duckdb")
    yield engine
    engine.close()


@pytest.fixture(scope="module")
def target(hand_made):
    return call(hand_made, step_reference=KNOWN["target"], as_of=KNOWN["as_of"])


def test_a_package_from_a_step_row_dates_every_step_from_its_plan_and_its_comparables_delay(target):
    steps = target["step_dates"]
    assert (steps["family"], steps["basis"], steps["needs_start_date"]) == ("goods", "delay", False)
    assert [entry["step_key"] for entry in steps["steps"]] == GOODS
    dated = steps["steps"][:5]
    assert [entry["cautious"]["planned_date"] for entry in dated] == [day.isoformat() for day in KNOWN["cautious_dates"]]
    assert [entry["middle"]["planned_date"] for entry in dated] == [day.isoformat() for day in KNOWN["middle_dates"]]
    assert [entry["cautious"]["days"] for entry in dated] == KNOWN["cautious_days"]
    assert [entry["middle"]["days"] for entry in dated] == KNOWN["middle_days"]
    assert {entry["cautious"]["days_relation"] for entry in dated} == {"after_plan"}
    assert [entry["comparables_n"] for entry in dated] == [KNOWN["comparables"]] * 5
    assert {entry["abstain_reason"] for entry in dated} == {None}


def test_each_date_names_how_many_comparable_packages_ran_later_than_it(target):
    signed = by_key(target)["contract_signed"]

    assert (signed["cautious"]["longer"], signed["cautious"]["in10"]) == (KNOWN["cautious_longer"], KNOWN["cautious_in10"])
    assert (signed["middle"]["longer"], signed["middle"]["in10"]) == (KNOWN["middle_longer"], KNOWN["middle_in10"])
    assert (target["step_dates"]["cautious_in10"], target["step_dates"]["middle_in10"]) == (KNOWN["cautious_in10"], 5)


def test_a_step_no_comparable_package_planned_abstains_in_its_own_row(target):
    completion = by_key(target)["contract_completed"]

    assert (completion["comparables_n"], completion["abstain_reason"]) == (0, "few_comparables")
    assert completion["cautious"]["planned_date"] is None and completion["middle"]["planned_date"] is None
    assert target["step_dates"]["min_comparables"] == load_thresholds().value("time_estimate.min_comparables")


def test_ran_longest_counts_the_stage_that_ran_longest_up_to_the_signed_contract(target):
    assert target["step_dates"]["longest"]["step_key"] == KNOWN["longest_step"]
    assert (target["step_dates"]["longest"]["n"], target["step_dates"]["longest"]["m"]) == (KNOWN["longest_n"], KNOWN["longest_m"])
    entries = target["step_dates"]["longest"]["entries"]
    assert len(entries) == KNOWN["longest_m"]
    assert sum(1 for entry in entries if entry["stage_step_key"] == KNOWN["longest_step"]) == KNOWN["longest_n"]


def test_each_step_lists_its_comparable_packages_shortest_first_for_the_evidence_drawer(target):
    opening = by_key(target)["bid_opening"]["comparables"]

    assert [entry["step_reference"] for entry in opening] == [step_set.comparable(i) for i in range(1, 26)]
    assert [entry["days"] for entry in opening] == sorted(entry["days"] for entry in opening)
    assert {entry["still_open"] for entry in opening} == {False}
    assert opening[0]["evidence_id"] == f"strata.gold.package:{step_set.comparable(1)}"


def test_the_tool_counts_the_steps_it_dated_and_could_not_date_so_the_screen_counts_nothing(target):
    """The summary's and the caption's counts are the tool's (CLAUDE.md rule 1): five dated steps in each choice,
    one, the completion, that no comparable package planned, out of six it could date."""
    steps = target["step_dates"]
    dated = len(KNOWN["cautious_dates"])

    assert steps["dated_n"] == {"middle": dated, "cautious": dated}
    assert (steps["undated_n"], steps["few_n"], steps["dateable_n"]) == (1, 1, len(GOODS))
    assert steps["none_dated"] is False


def test_the_coverage_line_counts_the_comparable_packages_whose_plans_dated_these_steps(target):
    assert target["step_dates"]["coverage"] == {"total": KNOWN["comparables"], "used": KNOWN["comparables"], "missing": 0,
                                                "other_family": 0, "unconfirmed": 0, "reason": "no_plan_dates",
                                                "sources": ["notices", "awards", "documents", "projects"]}


def test_a_comparable_from_another_step_table_is_left_out_of_the_steps_and_counted_as_another_family():
    """Ticket 27's review, follow-up 4. A firm and an individual consultant can both be hired by Direct Selection, but
    STEP plans them in two tables with different steps, so an individual consultant's signed-contract delay never
    counts a firm's package. The firm is counted as other_family; and a comparable whose first listing is not
    confirmed is counted too, so section 2 can say so (ticket 27's verify, finding 2). Made-up plan rows."""
    from strata.estimates import step_dates as steps

    signed = "Signed Contract"

    def row(reference, section, confirmed):
        return {"activity_reference_no": reference, "section": section, "process_status": "Signed",
                "plan_date": dt.date(2021, 1, 1), "step": signed, "step_order": 4, "planned_on": dt.date(2021, 3, 1),
                "actual_on": dt.date(2021, 3, 20), "first_planned_on": dt.date(2021, 3, 1),
                "first_planned_plan_date": dt.date(2021, 1, 1), "delay_days": 19, "first_listing_confirmed": confirmed,
                "public_from": dt.date(2021, 1, 1)}

    plan = {"KE-HAND-1-CS-CDS": row("KE-HAND-1-CS-CDS", "INDIVIDUAL CONSULTANTS", True),  # the package itself
            "KE-HAND-2-CS-CDS": row("KE-HAND-2-CS-CDS", "INDIVIDUAL CONSULTANTS", False),
            "KE-HAND-3-CS-CDS": row("KE-HAND-3-CS-CDS", "CONSULTING FIRMS", True)}

    def rows(_sql, references):
        return [plan[reference] for reference in references.split(",") if reference in plan]

    dated = steps.step_dates(rows, category="Consultant Services", method="Direct Selection",
                             package_reference="KE-HAND-1-CS-CDS", comparables=["KE-HAND-2-CS-CDS", "KE-HAND-3-CS-CDS"],
                             as_of=dt.date(2022, 1, 1), start_date=None, settings=steps.Settings.read(load_thresholds()),
                             track=None, sources=["documents"])

    [contract] = [step for step in dated["steps"] if step["step_key"] == "contract_signed"]
    assert dated["family"] == "individuals"
    assert [found["step_reference"] for found in contract["comparables"]] == ["KE-HAND-2-CS-CDS"]
    assert {key: dated["coverage"][key] for key in ("total", "used", "missing", "other_family", "unconfirmed")} == {
        "total": 2, "used": 1, "missing": 0, "other_family": 1, "unconfirmed": 1}
    assert dated["not_used"] == [{"step_reference": "KE-HAND-3-CS-CDS", "reason": "other_family"}]


def test_strata_never_writes_an_actual_date_into_a_step(hand_made):
    """Once the target's own actual dates are public, the result counts them for the activity page and holds none
    of them, under any name."""
    later = call(hand_made, step_reference=KNOWN["target"], as_of=dt.date(2022, 6, 30))
    actual = {day.isoformat() for day in step_set.TARGET_ACTUAL if day}

    assert later["step_dates"]["actual_steps_count"] == len(actual)

    def walk(value, path=""):
        if isinstance(value, dict):
            for key, inner in value.items():
                assert "actual" not in key or key == "actual_steps_count", f"{path}.{key}"
                walk(inner, f"{path}.{key}")
        elif isinstance(value, list):
            for inner in value:
                walk(inner, path)
        else:
            assert value not in actual, path

    walk(later["step_dates"])
    assert later["step_dates"]["steps"][0]["plan_first_date"] == step_set.TARGET_PLANNED[0].isoformat()


def test_below_20_comparable_packages_the_whole_section_gives_counts_and_no_dates(hand_made):
    narrowed = call(hand_made, step_reference=KNOWN["target"], as_of=KNOWN["as_of"], notice_to=dt.date(2019, 12, 1))
    steps = narrowed["step_dates"]

    assert steps["abstain_all"]["n"] < 20
    assert all(entry["middle"] is None and entry["cautious"] is None for entry in steps["steps"])
    assert all(entry["comparables_n"] <= steps["abstain_all"]["n"] for entry in steps["steps"])


PLANNED = {"category": "Works", "method": "Request for Bids", "country": "KE"}


def test_a_package_from_a_sentence_asks_for_its_first_steps_date_and_shows_each_steps_days_until_then(hand_made):
    undated = call(hand_made, as_of=KNOWN["as_of"], **PLANNED)["step_dates"]

    assert (undated["family"], undated["basis"], undated["needs_start_date"]) == ("goods", "duration", True)
    anchor, *later = undated["steps"]
    assert anchor["is_anchor"] and anchor["comparables_n"] is None
    assert [entry["cautious"]["days"] for entry in later[:4]] == KNOWN["duration_cautious_days"]
    assert {entry["cautious"]["days_relation"] for entry in later[:4]} == {"after_previous"}
    assert {entry["cautious"]["planned_date"] for entry in later} == {None}


def test_from_a_start_date_each_later_step_counts_from_the_one_before(hand_made):
    dated = call(hand_made, as_of=KNOWN["as_of"], start_date=KNOWN["duration_start"], **PLANNED)["step_dates"]
    anchor, *later = dated["steps"]

    assert (dated["needs_start_date"], dated["start_date"]) == (False, KNOWN["duration_start"].isoformat())
    assert anchor["cautious"]["planned_date"] == anchor["middle"]["planned_date"] == KNOWN["duration_start"].isoformat()
    assert [entry["cautious"]["planned_date"] for entry in later[:4]] == [day.isoformat() for day in KNOWN["duration_cautious_dates"]]
    assert [entry["middle"]["planned_date"] for entry in later[:4]] == [day.isoformat() for day in KNOWN["duration_middle_dates"]]
    assert [entry["middle"]["days"] for entry in later[:4]] == KNOWN["duration_middle_days"]
    # Every comparable was still open at its completion, so the curve never reached half: no date, said in the row.
    assert (later[4]["comparables_n"], later[4]["abstain_reason"]) == (KNOWN["comparables"], "not_reached")
    assert later[4]["reached_n"] == 0 and later[3]["reached_n"] == KNOWN["comparables"]
    # The anchor is the person's date: of the five later steps, four are dated and the completion is not.
    assert (dated["dated_n"], dated["undated_n"], dated["few_n"], dated["dateable_n"]) == (
        {"middle": 4, "cautious": 4}, 1, 0, 5)


def test_a_step_after_one_that_abstains_cannot_be_dated_and_keeps_its_own_days(tmp_path):
    """A later plan records no bidding document for any comparable, as the fixture's plans never do: the bidding
    document and the opening after it have no comparables, and the report and the signing, which have 25, say
    they need an earlier step's date."""
    engine = step_set.build(tmp_path / "set.duckdb", bidding_document_unrecorded=True)

    steps = {entry["step_key"]: entry for entry in call(engine, as_of=KNOWN["as_of"], start_date=KNOWN["duration_start"],
                                                         **PLANNED)["step_dates"]["steps"]}
    engine.close()

    assert [steps[key]["abstain_reason"] for key in GOODS[1:5]] == ["few_comparables", "few_comparables",
                                                                    "needs_earlier_step", "needs_earlier_step"]
    assert steps["bid_evaluation_report"]["cautious"]["days"] == KNOWN["duration_cautious_days"][2]
    assert steps["bid_evaluation_report"]["cautious"]["planned_date"] is None


# ── Delay from the first published planned date (criterion 2) ───────────

LATER_PLAN, RE_DATED = dt.date(2021, 12, 1), dt.date(2021, 11, 1)  # made up: no recorded plan re-dates a step
OTHER = "KE-HAND-000001-CW-RFB"


@pytest.fixture
def re_dated(tmp_path):
    """KE-NWWDA-229129-CW-RFB as the April 21, 2021 plan first listed it, then a later plan that re-dates its
    signed contract and records the signing, and a second works package in the later plan that has it as its one
    comparable, as tests/test_plans.py's re-dating test writes them."""
    from strata.lakehouse import catalog, plans

    first, signed = VALUES["plan-229129-first-planned-signing"], VALUES["plan-229129-signed"]["value"]
    reference, project = "KE-NWWDA-229129-CW-RFB", "P156634"
    engine = DuckDBEngine.open(tmp_path / "re-dated.duckdb")
    catalog.build(engine)
    step_set.insert(engine, "strata.gold.country", [{"country_code": "KE", "country_name": "Kenya",
                                                      "region": "Eastern and Southern Africa", "public_from": dt.date(2008, 12, 10)}])
    step_set.insert(engine, "strata.gold.project", [{"project_id": project, "project_name": "Water project",
                                                      "country_code": "KE", "region": "Eastern and Southern Africa",
                                                      "public_from": dt.date(2016, 1, 1)}])
    versions = [step_set.version("first", first["date"], 1, False), step_set.version("later", LATER_PLAN, 2, True)]
    for row in versions:
        row["project_id"] = project
    step_set.insert(engine, "strata.silver.plan_versions", versions)
    rows = [step_set.plan_row("first", first["date"], reference, "Pending Implementation"),
            step_set.plan_row("later", LATER_PLAN, reference, "Signed"),
            step_set.plan_row("later", LATER_PLAN, OTHER, "Pending Implementation")]
    for row in rows:
        row["project_id"] = project
    step_set.insert(engine, "strata.silver.plan_rows", rows)
    plans.insert(engine, "strata.silver.plan_listings",
                 ("document_id", "project_id", "activity_reference_no", "is_first_listing", "first_listing_confirmed",
                  "public_from"),
                 [("first", project, reference, True, True, first["date"]), ("later", project, reference, False, True, LATER_PLAN),
                  ("later", project, OTHER, True, True, LATER_PLAN)])
    plans.insert(engine, "strata.silver.plan_steps",
                 ("document_id", "project_id", "activity_reference_no", "step", "step_order", "planned_on", "actual_on",
                  "public_from"),
                 [("first", project, reference, "Signed Contract", 1, first["value"], None, first["date"]),
                  ("later", project, reference, "Signed Contract", 1, RE_DATED, signed, LATER_PLAN),
                  ("later", project, OTHER, "Signed Contract", 1, dt.date(2022, 3, 1), None, LATER_PLAN)])
    engine.run(plans._sql("plan_step_delays.sql"), {"project_id": project})
    notice, contract, package = step_set.package(reference, dt.date(2021, 5, 26), signed)
    for row in (notice, contract, package):
        row["project_id"] = project
    step_set.insert(engine, "strata.gold.notice", [notice])
    step_set.insert(engine, "strata.gold.contract", [contract])
    step_set.insert(engine, "strata.gold.package", [package])
    yield engine
    engine.close()


def test_a_step_a_later_plan_re_dated_keeps_its_first_published_date_and_names_the_move(re_dated):
    first = VALUES["plan-229129-first-planned-signing"]

    signed = by_key(call(re_dated, step_reference="KE-NWWDA-229129-CW-RFB", as_of=dt.date(2022, 6, 30)))["contract_signed"]

    assert (signed["plan_first_date"], signed["plan_first_version_date"]) == (first["value"].isoformat(), first["date"].isoformat())
    assert (signed["plan_latest_date"], signed["plan_latest_version_date"]) == (RE_DATED.isoformat(), LATER_PLAN.isoformat())


def test_a_comparable_re_dated_in_a_later_plan_counts_its_delay_from_the_earlier_date(re_dated):
    result = call(re_dated, step_reference=OTHER, as_of=dt.date(2022, 6, 30))
    signed = by_key(result)["contract_signed"]

    assert [(entry["step_reference"], entry["days"]) for entry in signed["comparables"]] == [
        ("KE-NWWDA-229129-CW-RFB", VALUES["plan-229129-days-late"]["value"])]
    # One comparable package in all: the whole section gives counts and no dates.
    assert (signed["comparables_n"], result["step_dates"]["abstain_all"]) == (1, {"n": 1})


# ── The fixture ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fixture(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def test_on_the_fixture_every_step_of_the_demo_package_abstains_and_no_stage_ran_longest(fixture):
    """The fixture's plans record few comparables' steps, and never the bidding document, so no step has 20
    comparable packages and no comparable recorded every step up to the signed contract. Section 1's 49
    comparables keep the whole section from abstaining."""
    result = call(fixture, step_reference="KE-NWWDA-541055-CW-RFB", as_of=dt.date(2026, 10, 22))
    steps = result["step_dates"]

    assert (steps["family"], steps["basis"]) == ("goods", "delay")
    assert steps["abstain_all"] is None and steps["coverage"]["total"] == TRUTH["past_range"]["comparables"]
    assert all(entry["comparables_n"] < 20 for entry in steps["steps"])
    assert {entry["abstain_reason"] for entry in steps["steps"]} <= {"few_comparables", "not_in_plan"}
    assert steps["longest"] is None
    # No step has a date or days in either choice, so the screen offers no choice of dates.
    assert (steps["none_dated"], steps["dated_n"], steps["undated_n"]) == (True, {"middle": 0, "cautious": 0}, 6)


def test_an_individual_consultant_hired_by_direct_selection_gets_the_individual_consultants_steps(fixture):
    """The plan's table decides the family: KE-KENHA-496786-CS-CDS sits in STEP's INDIVIDUAL CONSULTANTS table
    under Direct Selection, a Method the consulting firms' family lists too, so its category and Method alone
    would date it as a consulting firm and drop its invitation."""
    invitation = VALUES["plan-496786-planned-invitation"]

    result = call(fixture, step_reference="KE-KENHA-496786-CS-CDS", as_of=dt.date(2026, 10, 22))
    steps = by_key(result)

    assert result["step_dates"]["family"] == "individuals"
    assert list(steps) == ["terms_of_reference", "invitation", "draft_negotiated_contract", "contract_signed",
                           "contract_completed"]
    assert steps["invitation"]["plan_first_date"] == invitation["value"].isoformat()
    assert steps["draft_negotiated_contract"]["plan_first_date"] is None
