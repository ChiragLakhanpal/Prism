"""project_signals at seam 2, the tool contract (ticket 37).

project_signals runs seven fixed checks on one project's public records, with every threshold from
config/thresholds.toml's [signals] and [plan_check], and returns one row per check that fired, the
project's status and what it could not check. Every test is pinned to October 22, 2026, ticket 09's
as-of date, never to the wall clock: P156634 closes on October 31, 2026.

Expected values come from tests/ground_truth/values.toml (the plans' rows with their pages, the loan
history's months) and from the ticket's four lines, never from the tool's own arithmetic.
"""

import dataclasses
import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.config import load_thresholds
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
AS_OF = dt.date(2026, 10, 22)
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", user_id="ana", token="token-for-ana-only")


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as opened:
        yield opened


def signals(engine, project_id="P156634", as_of=AS_OF, thresholds=None):
    context = registry.Context(engine=engine, viewer=ANA, as_of=as_of,
                               **({"thresholds": thresholds} if thresholds else {}))
    return registry.call("project_signals", {"project_id": project_id}, context)


@pytest.fixture(scope="module")
def today(engine):
    """P156634's signals as of October 22, 2026, run once for the tests that read them."""
    return signals(engine)


def fired(result) -> dict[str, dict]:
    return {row["check"]: row for row in result["rows"]}


def with_signals(**changed):
    defaults = load_thresholds()
    return dataclasses.replace(defaults, values={**defaults.values, "signals": {**defaults.values["signals"], **changed}})


def test_p156634_needs_a_look_with_the_four_signals_of_the_following_wireframe(today):
    result = today

    assert result["status"] == "needs_a_look"
    assert sorted(fired(result)) == ["above_estimate", "closing_moves", "completion_passed", "late_direct"]
    assert result["counts"]["signals"] == 4


def test_ke_nwwda_541055_passed_its_planned_completion_with_no_signed_contract(today):
    [activity] = fired(today)["completion_passed"]["items"]

    assert activity["activity_reference_no"] == "KE-NWWDA-541055-CW-RFB"
    assert activity["planned_completion_on"] == TRUTH["plan-541055-planned-completion"]["value"].isoformat()
    assert activity["signed_on"] is None


def test_ke_nwwda_229129_was_signed_at_about_4_times_its_estimate(today):
    [contract] = fired(today)["above_estimate"]["items"]

    assert contract["activity_reference_no"] == "KE-NWWDA-229129-CW-RFB"
    assert contract["ratio"] == 4  # about 4 times: US$1,245,092.76 against US$300,000.00
    assert contract["actual_amount_usd"] == f'{TRUTH["plan-229129-actual"]["value"]:.2f}'
    assert contract["estimated_amount_usd"] == f'{TRUTH["plan-229129-estimated"]["value"]:.2f}'


def test_ke_cwsb_567630_a_us_2_6_million_direct_selection_works_activity_first_appears_in_the_august_17_plan(today):
    row = fired(today)["late_direct"]
    [activity] = row["items"]

    assert activity["activity_reference_no"] == "KE-CWSB-567630-CW-DIR"
    assert activity["estimated_amount_usd"] == TRUTH["plan-cwsb-567630-estimated"]["value"].replace(",", "")
    assert activity["amount_millions"] == "2.6"
    assert activity["section"] == "WORKS"
    assert activity["first_plan_date"] == TRUTH["plan-cwsb-567630-first-listed"]["value"].isoformat()


def test_the_closing_date_has_moved_three_times_since_2022_counted_per_project_not_per_credit(today):
    row = fired(today)["closing_moves"]

    assert row["count"] == 3
    assert row["values"]["since_year"] == 2022
    assert [item["closing_date"] for item in row["items"]] == [
        TRUTH[f"closing-p156634-move-{n}"]["value"].isoformat() for n in (1, 2, 3)]


def test_restructurings_ratings_and_disbursement_ran_and_found_nothing(today):
    result = today
    checks = {check["key"]: check for check in result["checks"]}

    for key in ("restructured", "isr_lowered", "disbursement"):
        assert checks[key]["ran"] and not checks[key]["fired"], key
    assert result["counts"]["ran"] == result["counts"]["checks"] == 7


def test_a_closed_project_is_not_checked_and_says_so(engine):
    result = signals(engine, "P130164")

    assert result["status"] == "closed"
    assert result["abstention"]["reason"] == "not_active"
    assert result["rows"] == [] and result["project"]["closing_date"] == TRUTH["project-p130164-closing"]["value"].isoformat()


def test_as_of_june_30_2024_p156634_had_one_signal_and_says_which_checks_it_could_not_run(engine):
    """Two moves by then (November 2022 and April 2024); no agency's latest plan was dated in the year before,
    and no loan snapshot was public yet, so those checks say why they could not run."""
    result = signals(engine, as_of=dt.date(2024, 6, 30))
    checks = {check["key"]: check for check in result["checks"]}

    assert result["status"] == "watch"
    assert [item["closing_date"] for item in fired(result)["closing_moves"]["items"]] == [
        TRUTH[f"closing-p156634-move-{n}"]["value"].isoformat() for n in (1, 2)]
    assert {key: checks[key]["missing"] for key in ("completion_passed", "late_direct", "disbursement")} == {
        "completion_passed": "no_recent_plans", "late_direct": "no_recent_plans", "disbursement": "no_loans"}
    assert result["coverage"]["used"] < result["coverage"]["matched"]


def test_the_mission_brief_records_hold_the_two_contracts_signed_since_isr_19_and_the_credits(engine):
    """project_records, which the mission brief writer drafts from: since ISR 19 (June 30, 2026), two contracts were
    signed, KE-CWSB-567630-CW-DIR on August 28, 2026 and KE-CWSB-565568-GO-RFQ on September 4, 2026, the first at
    US$2,432,125.50 against the plan's US$2,600,000.00; the credits are IDA60290 and IDA60300."""
    result = registry.call("project_records", {"project_id": "P156634"},
                           registry.Context(engine=engine, viewer=ANA, as_of=AS_OF))
    by_part = {}
    for row in result["rows"]:
        by_part.setdefault(row["part"], []).append({field["key"]: field["value"] for field in row["fields"]})

    assert result["isr"]["sequence"] == 19 and result["isr"]["isr_date"] == "2026-06-30"
    assert [(award["step_reference"], award["signed_on"]) for award in by_part["awards"]] == [
        ("KE-CWSB-567630-CW-DIR", TRUTH["award-567630-signed"]["value"].isoformat()),
        ("KE-CWSB-565568-GO-RFQ", TRUTH["award-565568-signed"]["value"].isoformat())]
    assert by_part["awards"][0]["signed_amount_usd"] == f'{TRUTH["award-567630-amount"]["value"]:.2f}'
    assert by_part["awards"][0]["estimated_amount_usd"] == f'{TRUTH["plan-cwsb-567630-estimated"]["value"].replace(",", "")}'
    assert sorted(loan["loan_number"] for loan in by_part["disbursement"]) == ["IDA60290", "IDA60300"]
    assert result["summary"]["totals"]["awards"]["count"] == 2
    assert result["summary"]["totals"]["closing"]["moves"] == 3


def test_raising_the_needs_a_look_count_above_four_turns_p156634_to_watch_with_no_code_change(engine):
    assert signals(engine, thresholds=with_signals(look_min=5))["status"] == "watch"
    assert signals(engine, thresholds=with_signals(look_min=5, strong=["closing_moves"]))["status"] == "needs_a_look"
