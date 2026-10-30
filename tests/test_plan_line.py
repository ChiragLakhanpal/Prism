"""Section 1's plan line and the step tracker read the plan's dates the same way (ticket 139; spec, seam 2).

Section 1 of the package workspace (GET /api/packages/{step_reference}/comparables, find_comparables) draws the plan
line from the plan's planned notice date to its planned signing date. The step tracker above section 2 (GET
/api/packages/{step_reference}/steps, ticket 115) shows each step's planned date in the package's newest plan version.
Both read the plan's step dates: the bid invitation's and the signed contract's planned dates are the plan line's two
ends, so section 1 draws a line exactly when the tracker shows both, and names the dates the tracker shows when it
cannot draw one.

Three rows of the showcase package KE-NWWDA-541055-CW-RFB: as the fixture holds it, with both dates (the Procurement
Plan of October 9, 2026: plan-541055-planned-notice and plan-541055-planned-signing in tests/ground_truth/values.toml);
on a copy whose plan gives no planned date for the bid invitation, as the walkthrough's KE-SDOR-KIHBT-563865-CW-RFB
read on the workspace; and on a copy whose plan dates neither.
"""

import shutil
import tomllib
from pathlib import Path

import pytest
from test_step_routes import ANA, call, make_app

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
VALUES = {entry["id"]: entry["value"] for entry in tomllib.loads(
    (ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
PACKAGE = "KE-NWWDA-541055-CW-RFB"
NOTICE = VALUES["plan-541055-planned-notice"].isoformat()
SIGNING = VALUES["plan-541055-planned-signing"].isoformat()
INVITATION, SIGNED = "Specific Procurement Notice / Invitation", "Signed Contract"

# Each statement names its rows with a WHERE (CLAUDE.md rule 5), and runs on a copy, never on the fixture itself. The
# plan reader writes a step's planned date to both tables, so a plan that gives none leaves it out of both.
UNDATED = tuple(f"UPDATE strata.silver.{table} SET planned_on = NULL "
                "WHERE activity_reference_no = :reference AND step = :step"
                for table in ("plan_steps", "plan_step_delays"))


def copy_without(fixture_db: Path, folder: Path, steps: tuple[str, ...]) -> Path:
    """A copy of the fixture database whose plans give the showcase package no planned date for these steps."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        for step in steps:
            for statement in UNDATED:
                engine.run(statement, {"reference": PACKAGE, "step": step})
    return target


@pytest.fixture(scope="module")
def plans(fixture_db, tmp_path_factory):
    """The showcase package's page on three plans: with both dates, with the signing only, and with neither."""
    folder = tmp_path_factory.mktemp("plan-line")
    (folder / "both").mkdir()
    return {"both": make_app(fixture_db, folder / "both"),
            "signing_only": make_app(copy_without(fixture_db, folder / "signing", (INVITATION,)), folder / "signing"),
            "neither": make_app(copy_without(fixture_db, folder / "neither", (INVITATION, SIGNED)), folder / "neither")}


def section_1(app) -> dict:
    answer = call(app, "GET", f"/api/packages/{PACKAGE}/comparables", ANA)
    assert answer.status_code == 200, answer.text
    return answer.json()


def tracker(app) -> dict[str, str | None]:
    """The planned date the tracker shows for each step, by its key."""
    answer = call(app, "GET", f"/api/packages/{PACKAGE}/steps", ANA)
    assert answer.status_code == 200, answer.text
    return {step["step_key"]: step["plan_latest_date"] for step in answer.json()["step_dates"]["steps"]}


@pytest.mark.parametrize(("row", "notice", "signing"), [
    ("both", NOTICE, SIGNING),
    ("signing_only", None, SIGNING),
    ("neither", None, None),
])
def test_section_1_reads_the_plan_line_s_two_dates_where_the_tracker_shows_them(plans, row, notice, signing):
    result, shown = section_1(plans[row]), tracker(plans[row])

    assert (shown["bid_invitation"], shown["contract_signed"]) == (notice, signing)
    assert (result["package"]["planned_notice_on"], result["package"]["planned_signing_on"]) == (notice, signing)
    if notice and signing:
        assert (result["plan"]["planned_notice_on"], result["plan"]["planned_signing_on"]) == (notice, signing)
    else:
        assert result["plan"] is None
