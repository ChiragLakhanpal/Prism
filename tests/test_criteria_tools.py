"""The check-your-criteria tools at seam 2, the tool contract (ticket 31): compare_cost_estimates, rejected_bids and
compare_criteria, each called by name through the registry on the fixture database.

Each tool is given the comparable packages find_comparables returned, so the reference class is defined once.
Expected values come from tests/ground_truth/values.toml (plan-541055-estimated, plan-229129-estimated,
plan-229129-actual, award-229129-signed and awkward.joint_venture) and from direct counts over the fixture
database written here, never the way the tools compute them.
"""

import datetime as dt
import re
import tomllib
from decimal import Decimal
from pathlib import Path

import pytest

from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
PACKAGE = "KE-NWWDA-541055-CW-RFB"
AS_OF = "2026-10-22"


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def call(engine, tool, **arguments):
    return registry.call(tool, {"as_of": AS_OF, **arguments}, registry.Context(engine=engine, viewer=ANA))


@pytest.fixture(scope="module")
def comparables(engine):
    """The comparable packages of KE-NWWDA-541055-CW-RFB with the default criteria, as find_comparables gives them."""
    result = call(engine, "find_comparables", step_reference=PACKAGE)
    return [row["step_reference"] for row in result["rows"]]


def scalar(engine, sql, **params):
    return engine.run(sql, params).rows[0][0]


# ── compare_cost_estimates ───────────────────────────────────────────────

@pytest.fixture(scope="module")
def cost(engine, comparables):
    return call(engine, "compare_cost_estimates", comparables=",".join(comparables), step_reference=PACKAGE)


def with_both_amounts(engine, references) -> int:
    """How many of the packages have an Estimated Amount in a public plan version and a contract in the awards data."""
    return scalar(engine, """
        SELECT count(DISTINCT r.activity_reference_no)
        FROM strata.silver.plan_rows AS r
        JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
        JOIN strata.gold.contract AS c ON c.step_reference = r.activity_reference_no
        WHERE array_contains(split(:refs, ','), r.activity_reference_no)
          AND r.estimated_amount_usd IS NOT NULL AND v.public_from <= CAST(:as_of AS DATE)
          AND c.contract_amount_usd IS NOT NULL AND c.public_from <= CAST(:as_of AS DATE)
    """, refs=",".join(references), as_of=AS_OF)


def test_the_cost_estimate_abstains_below_twenty_comparables_and_lists_every_package_with_both_amounts(engine, comparables,
                                                                                                    cost):
    both = with_both_amounts(engine, comparables)

    assert 0 < both < 20
    assert len(cost["rows"]) == both
    assert cost["abstention"] == {"reason": "too_few_comparables", "count": both, "min_comparables": 20}
    assert cost["summary"]["quartiles"] is None
    counts = cost["summary"]["counts"]
    assert counts["m"] == both and counts["total"] == len(comparables)
    assert counts["above"] + counts["below"] + counts["at"] == both
    assert counts["above"] == sum(1 for row in cost["rows"] if row["diff_pct"] > 0)
    assert counts["m"] + counts["open"] + counts["no_estimate"] + counts["no_usd"] == counts["total"]


def test_the_package_s_own_cost_estimate_is_its_plan_row_s_estimated_amount(cost):
    assert Decimal(cost["package"]["estimated_amount_usd"]) == Decimal(str(VALUES["plan-541055-estimated"]["value"]))


def test_a_comparable_s_row_holds_its_cost_estimate_and_its_signed_amount_from_the_awards_data(cost):
    row = {row["step_reference"]: row for row in cost["rows"]}["KE-NWWDA-229129-CW-RFB"]

    assert Decimal(row["estimated_amount_usd"]) == Decimal(str(VALUES["plan-229129-estimated"]["value"]))
    # The plan's Actual Amount and the awards dataset agree (award-229129-signed), at US$1,245,092.76.
    assert Decimal(row["signed_amount_usd"]) == Decimal(str(VALUES["plan-229129-actual"]["value"]))
    assert "1,245,092.76" in VALUES["award-229129-signed"]["says"]
    assert row["diff_pct"] > 100 and row["diff_pct"] == int(row["diff_pct"])  # no decimals above 100
    assert row["evidence_id"] and row["source"]["plan"]["plan_date"]


def test_a_joint_venture_s_contract_counts_once_at_its_contract_amount(cost):
    joint = TRUTH["awkward"]["joint_venture"]
    rows = {row["step_reference"]: row for row in cost["rows"]}

    row = rows["KE-KIMAWASCO-158691-CW-RFB"]
    assert Decimal(row["signed_amount_usd"]) == 2 * Decimal(str(joint["amount_per_member_usd"]))
    assert [contract["contract_id"] for contract in row["contracts"]] == [joint["contract"]]


def test_packages_signed_only_in_a_local_currency_award_notice_are_left_out_and_counted(cost):
    left_out = {evidence for entry in cost["coverage"]["not_used"] for evidence in entry["evidence_ids"]}
    shown = {row["step_reference"] for row in cost["rows"]}

    for reference in ("KE-GAWASCO-54771-CW-RFB", "KE-GAWASCO-111742-CW-RFB"):
        assert reference not in shown
        assert f"strata.gold.package:{reference}" in left_out


def test_each_difference_keeps_one_decimal_up_to_100_and_none_above(cost):
    for row in cost["rows"]:
        written = str(row["diff_pct"])
        if abs(row["diff_pct"]) >= 100:
            assert float(row["diff_pct"]).is_integer()
        else:
            assert re.fullmatch(r"-?\d+(\.\d)?", written), written


def test_as_of_a_date_before_any_contract_was_signed_no_package_has_both_amounts(engine, comparables):
    result = registry.call("compare_cost_estimates", {"comparables": ",".join(comparables), "as_of": "2019-01-01"},
                           registry.Context(engine=engine, viewer=ANA))

    assert result["rows"] == []
    assert result["abstention"]["reason"] == "none_with_both_amounts"
    assert dt.date.fromisoformat(result["as_of"]) == dt.date(2019, 1, 1)
