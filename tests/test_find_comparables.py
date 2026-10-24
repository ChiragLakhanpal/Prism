"""find_comparables at seam 2, the tool contract: the comparables and the past range for one package.

find_comparables is called by name through the registry, on the fixture database, as of October 22,
2026. The expected comparables, their dates and the Kaplan-Meier quantiles come from
tests/ground_truth/values.toml: the comparables are copied from the recorded notices and awards, and
the quantiles were computed once with lifelines and checked with statsmodels on the same dates. None
of them is computed the way the tool computes it.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata import config
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
COMPARABLES = TRUTH["comparable"]
PAST_RANGE = TRUTH["past_range"]
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
PACKAGE = "KE-NWWDA-541055-CW-RFB"
AS_OF = PAST_RANGE["as_of"]


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def find(engine, step_reference=PACKAGE, as_of=AS_OF, **criteria):
    """find_comparables for one package, called by name through the registry as Ana."""
    return registry.call("find_comparables", {"step_reference": step_reference, "as_of": as_of, **criteria},
                         registry.Context(engine=engine, viewer=ANA))


def left_out(result, reason):
    return sorted(evidence for entry in result["coverage"]["not_used"] if entry["reason"] == reason
                  for evidence in entry["evidence_ids"])


def package_id(reference):
    return f"strata.gold.package:{reference}"


def test_the_default_criteria_return_every_comparable_in_the_ground_truth_with_its_dates(engine):
    result = find(engine)

    rows = {row["step_reference"]: row for row in result["rows"]}
    kept = [c for c in COMPARABLES if "canceled_in" not in c]
    assert sorted(rows) == sorted(c["reference"] for c in kept)
    for comparable in kept:
        row = rows[comparable["reference"]]
        assert (row["notice_id"], row["notice_date"]) == (comparable["notice"], comparable["notice_date"].isoformat())
        if "signed" in comparable:
            assert (row["still_open"], row["signed_on"]) == (False, comparable["signed"].isoformat())
            assert row["source"]["contract_id"] == comparable.get("contract")
            assert row["source"]["award_notice_id"] == comparable.get("award_notice")
        else:
            assert (row["still_open"], row["signed_on"]) == (True, None)
    # The three canceled packages are not still open: the coverage line names them as left out.
    assert left_out(result, "canceled") == sorted(package_id(c["reference"]) for c in COMPARABLES if "canceled_in" in c)
    assert result["counts"] == {"comparables": 49, "signed": TRUTH["comparables"]["signed"],
                                "still_open": TRUTH["comparables"]["still_open"],
                                "canceled": TRUTH["comparables"]["canceled"], "canceled_as_still_open": False}


def test_the_past_range_is_the_kaplan_meier_quantiles_in_the_ground_truth_with_open_packages_censored(engine):
    result = find(engine)

    assert result["past_range"] == {
        "q25": PAST_RANGE["q25_months"], "q50": PAST_RANGE["q50_months"], "q75": PAST_RANGE["q75_months"],
        "q80": PAST_RANGE["q80_months"],
        "days": {name: PAST_RANGE[f"{name}_days"] for name in ("q25", "q50", "q75", "q80")}}
    assert result["abstention"] is None
    assert result["quantile_dots"] is None  # 49 comparables is not above 60


def test_the_rows_come_shortest_first_with_each_open_package_counted_so_far(engine):
    result = find(engine)

    assert [row["rank"] for row in result["rows"]] == list(range(1, 50))
    assert [(row["months"], row["step_reference"]) for row in result["rows"]] == sorted(
        (row["months"], row["step_reference"]) for row in result["rows"])
    open_rows = {row["step_reference"]: row["days"] for row in result["rows"] if row["still_open"]}
    assert open_rows == {c["reference"]: (AS_OF - c["notice_date"]).days for c in COMPARABLES
                         if "signed" not in c and "canceled_in" not in c}


def test_the_plan_s_months_and_the_comparables_signed_within_them_come_from_the_plan_row(engine):
    result = find(engine)

    assert result["plan"]["months"] == PAST_RANGE["plan_months"]
    assert result["plan"]["days"] == PAST_RANGE["plan_days"]
    assert (result["plan"]["planned_notice_on"], result["plan"]["planned_signing_on"]) == ("2026-03-10", "2026-04-24")
    assert result["plan"]["within"] == len(PAST_RANGE["signed_within_plan"])
    # 2 of 49 rounds to 0 in 10; the screen then writes "fewer than 1 in 10".
    assert result["plan"]["in10"] == 0


def test_the_narrower_criteria_give_no_range_and_no_share_and_return_every_comparable(engine):
    criteria = TRUTH["comparables"]
    result = find(engine, review_type=criteria["narrower_review_type"])

    narrower = sorted(c["reference"] for c in COMPARABLES if c.get("review_type") == criteria["narrower_review_type"])
    assert sorted(row["step_reference"] for row in result["rows"]) == narrower
    assert result["abstention"] == {"reason": "too_few_comparables", "count": criteria["narrower_count"],
                                    "min_comparables": 20}
    assert (result["past_range"], result["quantile_dots"], result["plan"]["in10"]) == (None, None, None)
    # A count of real cases is allowed below 20: none of the seven took 1.5 months or less.
    assert result["plan"]["within"] == 0
    # A package with no review type in any record is counted as not usable, never dropped unseen: the
    # two signed only in award notices, the four still open and the three canceled.
    no_review = sorted(package_id(c["reference"]) for c in COMPARABLES if "review_type" not in c)
    assert left_out(result, "no_review_type") == no_review


def test_the_coverage_line_states_the_counts_a_direct_count_over_the_fixture_gives(engine):
    from strata.lakehouse import ground_truth

    case = ground_truth.read(ROOT / "tests" / "ground_truth" / "past_range_coverage_ke_works_rfb.sql")
    counted = dict(engine.run(case.sql, case.params).as_text())
    assert case.params == {"as_of": AS_OF.isoformat(), "notice_from": "2019-07-01", "notice_to": "2026-10-09"}

    coverage = find(engine)["coverage"]

    by_reason = {entry["reason"]: str(entry["count"]) for entry in coverage["not_used"]}
    assert (str(coverage["matched"]), str(coverage["used"])) == (counted["matched"], counted["used"])
    assert by_reason == {"canceled": counted["canceled"], "no_notice": counted["no notice"],
                         "no_step_reference": counted["no STEP reference"]}


def test_with_an_as_of_date_a_package_signed_after_it_comes_back_as_still_open(engine):
    # As of June 1, 2021, KE-NWWDA-229129-CW-RFB is in the agency's plan of April 21, 2021, so the
    # period ends on that plan's date. KE-WAJWASCO-220077-CW-RFB was signed on July 27, 2021.
    as_of = dt.date(2021, 6, 1)
    result = find(engine, step_reference="KE-NWWDA-229129-CW-RFB", as_of=as_of)

    rows = {row["step_reference"]: row for row in result["rows"]}
    wajwasco = next(c for c in COMPARABLES if c["reference"] == "KE-WAJWASCO-220077-CW-RFB")
    assert wajwasco["signed"] > as_of
    assert (rows[wajwasco["reference"]]["still_open"], rows[wajwasco["reference"]]["signed_on"]) == (True, None)
    assert rows[wajwasco["reference"]]["days"] == (as_of - wajwasco["notice_date"]).days
    # The plan that marks it Canceled (March 19, 2025) was not public yet, so this package was still open then.
    assert rows["KE-KIMAWASCO-149448-CW-RFB"]["still_open"] is True
    assert all(row["public_from"] <= as_of.isoformat() for row in result["rows"])
    assert result["package"]["plan"]["plan_date"] == "2021-04-21"


def test_a_signing_known_only_from_an_award_notice_counts_from_the_day_the_notice_was_published(engine):
    # KE-GAWASCO-54771-CW-RFB was signed on April 19, 2022; its award notice OP00175878 came out on April 21.
    gawasco = next(c for c in COMPARABLES if c["reference"] == "KE-GAWASCO-54771-CW-RFB")

    def row(as_of):
        result = find(engine, step_reference="KE-NWWDA-229129-CW-RFB", as_of=as_of, notice_to=as_of)
        return next(r for r in result["rows"] if r["step_reference"] == gawasco["reference"])

    assert row(dt.date(2022, 4, 20))["still_open"] is True
    signed = row(dt.date(2022, 4, 21))
    assert (signed["signed_on"], signed["public_from"]) == (gawasco["signed"].isoformat(), "2022-04-21")


def test_only_an_abstention_the_registry_lists_as_keeping_its_rows_may_come_with_rows(engine, tmp_path):
    tool = config.load_tools()["find_comparables"]
    result = find(engine, review_type="Prior")
    assert result["abstention"]["reason"] in tool.result.abstentions_with_rows and result["rows"]

    with pytest.raises(registry.ToolContractError, match="abstained and still returned rows"):
        registry.check_contract(tool, {**result, "abstention": {"reason": "no_comparables", "matched": 7}})

    path = tmp_path / "tools.toml"
    path.write_text((ROOT / "config" / "tools.toml").read_text().replace(
        'abstentions_with_rows = ["too_few_comparables"]', 'abstentions_with_rows = ["too_few_packages"]'))
    with pytest.raises(config.ConfigError, match="too_few_packages, which abstentions does not list"):
        config.load_tools(path)


def with_past_range(**changed):
    """The thresholds file with some of its [past_range] values changed."""
    found = config.load_thresholds()
    return config.Thresholds(found.path, {**found.values, "past_range": {**found.values["past_range"], **changed}})


def test_above_the_quantile_dot_threshold_the_tool_gives_20_dots_at_the_ground_truth_quantiles(engine):
    context = registry.Context(engine=engine, viewer=ANA, thresholds=with_past_range(quantile_dots_above=40))

    result = registry.call("find_comparables", {"step_reference": PACKAGE, "as_of": AS_OF}, context)

    assert [dot["k"] for dot in result["quantile_dots"]] == list(range(1, 21))
    assert [dot["days"] for dot in result["quantile_dots"]] == PAST_RANGE["quantile_dot_days"]
    assert all(dot["reached"] for dot in result["quantile_dots"])
    assert result["thresholds"]["quantile_dots_above"] == 40


def test_a_wider_variant_with_more_than_60_comparables_gives_20_quantile_dots_and_every_row(engine):
    # Leaving the category open adds Kenya's goods packages under Request for Bids.
    result = find(engine, category="any")

    assert result["criteria"]["category"] is None
    assert len(result["rows"]) > 60
    assert len(result["quantile_dots"]) == 20
    assert result["past_range"]["q50"] is not None


def test_counting_canceled_packages_as_still_open_is_one_line_in_the_thresholds_file(engine):
    context = registry.Context(engine=engine, viewer=ANA, thresholds=with_past_range(canceled_as_still_open=True))

    result = registry.call("find_comparables", {"step_reference": PACKAGE, "as_of": AS_OF}, context)

    assert (result["counts"]["comparables"], result["counts"]["still_open"]) == (52, 7)
    assert left_out(result, "canceled") == []
    canceled = {row["step_reference"]: row for row in result["rows"] if row["step_reference"].startswith("KE-KIMAWASCO-1")}
    assert canceled["KE-KIMAWASCO-149448-CW-RFB"]["still_open"] is True


def test_a_package_with_a_limited_market_approach_has_no_notice_to_measure_from(engine):
    # KE-NWWDA-541062-CW-RFQ is a Request for Quotations with the Market Approach Limited - National.
    result = find(engine, step_reference="KE-NWWDA-541062-CW-RFQ")

    assert result["abstention"] == {"reason": "no_public_notice", "field": "Market Approach",
                                    "value": "Limited - National"}
    assert result["rows"] == []
    assert result["package"]["market_approach"] == "Limited - National"


def test_a_reference_no_public_plan_lists_is_an_unknown_package(engine):
    assert find(engine, step_reference="KE-NWWDA-000000-CW-RFB")["abstention"] == {
        "reason": "unknown_package", "step_reference": "KE-NWWDA-000000-CW-RFB"}
    # KE-NWWDA-541055-CW-RFB was first listed in the plan of March 5, 2026.
    assert find(engine, as_of=dt.date(2026, 3, 4))["abstention"]["reason"] == "unknown_package"


def test_criteria_no_package_meets_give_an_empty_answer_and_unmeasurable_ones_say_how_many_matched(engine):
    # No Indian works package under Request for Bids has a notice or a contract in the period.
    nothing = find(engine, country="IN")
    # Kenya's non-consulting services under Request for Bids were signed, but Strata holds no notice for any.
    unmeasured = find(engine, category="Non-consulting Services")

    assert nothing["abstention"] == {"reason": "no_comparables", "matched": 0}
    assert unmeasured["abstention"]["reason"] == "none_measurable"
    assert unmeasured["abstention"]["matched"] == unmeasured["coverage"]["matched"] > 0
    assert unmeasured["rows"] == nothing["rows"] == []
