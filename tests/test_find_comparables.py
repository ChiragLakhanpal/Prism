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


def test_each_package_left_out_is_named_by_its_step_reference_beside_its_evidence_id(engine):
    """Ticket 28's review, follow-up 12: a caller such as rebidding_risk reads which packages were left out without
    taking their evidence ids apart."""
    result = find(engine)

    [canceled] = [entry for entry in result["coverage"]["not_used"] if entry["reason"] == "canceled"]
    assert canceled["step_references"] == [c["reference"] for c in COMPARABLES if "canceled_in" in c]
    assert canceled["evidence_ids"] == [package_id(reference) for reference in canceled["step_references"]]


def test_the_drawer_says_a_package_is_left_out_as_canceled_by_the_caller_s_rule_or_else_the_file_s(engine):
    """Ticket 15's review round 3, R6: read_comparable follows _select's canceled rule with the caller's
    canceled_as_still_open, and reads the thresholds file only when the caller gives none."""
    from strata.tools.find_comparables import read_comparable

    [first] = [c["reference"] for c in COMPARABLES if "canceled_in" in c][:1]

    assert read_comparable(engine, first, AS_OF)["canceled"] is True  # the file counts none as still open
    assert read_comparable(engine, first, AS_OF, canceled_as_still_open=True)["canceled"] is False
    assert read_comparable(engine, first, AS_OF, canceled_as_still_open=False)["canceled"] is True


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
    # two signed only in award notices and the four still open, which no plan Strata holds lists.
    no_review = sorted(package_id(c["reference"]) for c in COMPARABLES if "review_type" not in c and "canceled_in" not in c)
    assert left_out(result, "no_review_type") == no_review
    # The three canceled packages have no contract, but their plan rows state Post, so none matches Prior.
    canceled = {package_id(c["reference"]) for c in COMPARABLES if "canceled_in" in c}
    assert canceled.isdisjoint(evidence for entry in result["coverage"]["not_used"] for evidence in entry["evidence_ids"])
    assert (result["coverage"]["matched"], result["coverage"]["used"]) == (
        criteria["narrower_count"] + len(no_review), criteria["narrower_count"])


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


def test_adding_a_criterion_never_lets_more_packages_match(engine):
    """A package with no value for one criterion still has to meet every criterion it does have a value for."""
    size = find(engine, size_to_usd=1)
    both = find(engine, size_to_usd=1, market_approach="Open - National")

    assert both["coverage"]["matched"] <= size["coverage"]["matched"]
    # A contract with no STEP reference is held to every criterion too: each signed for more than US$1.
    assert left_out(both, "no_step_reference") == left_out(size, "no_step_reference") == []


def test_a_criterion_matches_whatever_its_case_because_the_agent_writes_the_arguments_itself(engine):
    """"post", "works", "open - national" and "ke" are STEP's Post, Works, Open - National and KE. A
    criterion read case for case would match nothing, and a wrong "nothing matched" has no number for the
    verifier to catch."""
    def seen(result):
        return result["coverage"], [row["step_reference"] for row in result["rows"]]

    assert seen(find(engine, review_type="post")) == seen(find(engine, review_type="Post"))
    assert seen(find(engine, market_approach="open - national")) == seen(find(engine, market_approach="Open - National"))
    assert seen(find(engine, category="works", method="request for bids", country="ke")) == seen(find(engine))


def test_a_canceled_package_is_named_as_canceled_and_counted_only_where_the_coverage_line_names_it(engine):
    canceled = sorted(package_id(c["reference"]) for c in COMPARABLES if "canceled_in" in c)
    # A canceled package was never signed, so it has no signed amount either; canceled is the reason given.
    size = find(engine, size_to_usd=1)
    assert left_out(size, "canceled") == canceled
    for result in (find(engine), size, find(engine, review_type="Prior")):
        assert result["counts"]["canceled"] == len(left_out(result, "canceled"))


@pytest.mark.parametrize("criterion, criteria", [
    ("Open - National", {"market_approach": "Open - National"}),
    ("1M to 2M US$", {"size_from_usd": 1_000_000, "size_to_usd": 2_000_000}),
], ids=["market approach", "size band"])
def test_a_market_approach_or_a_size_band_returns_the_packages_a_direct_count_finds(engine, criterion, criteria):
    from strata.lakehouse import ground_truth

    case = ground_truth.read(ROOT / "tests" / "ground_truth" / "past_range_criteria_ke_works_rfb.sql")
    expected = sorted(reference for name, reference in case.expected[1:] if name == criterion)

    result = find(engine, **criteria)

    assert sorted(row["step_reference"] for row in result["rows"]) == expected


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


def test_the_derived_figures_come_back_as_one_citable_summary_record(engine, tmp_path):
    result = find(engine, review_type="Prior")

    summary = result["summary"]
    assert summary["evidence_id"] == f"strata.tools.find_comparables:{PACKAGE}@{AS_OF.isoformat()}?review_type=Prior"
    assert (summary["public_from"], summary["source"]["tool"]) == (AS_OF.isoformat(), "find_comparables")
    assert (summary["plan"], summary["counts"], summary["coverage"]) == (result["plan"], result["counts"],
                                                                        result["coverage"])
    with pytest.raises(registry.ToolContractError, match="summary is public from"):
        registry.check_contract(config.load_tools()["find_comparables"],
                                {**result, "summary": {**summary, "public_from": "2026-10-23"}})

    path = tmp_path / "tools.toml"
    path.write_text((ROOT / "config" / "tools.toml").read_text().replace(
        'summary_fields = ["past_range", "plan", "frequencies", "counts", "coverage"]',
        'summary_fields = ["past_range", "ranges"]'))
    with pytest.raises(config.ConfigError, match="ranges, which fields does not list"):
        config.load_tools(path)


def test_the_numbers_each_frequency_phrase_states_come_back_with_its_words_so_the_agent_can_cite_them(engine):
    """"8 in 10 were signed within 9.1 months" states 8 and 10, and "2 of 49, fewer than 1 in 10" states
    1 and 10, so the tool returns them (CLAUDE.md rule 1). The plan's share also says which words go
    with its numbers, because "about 1 in 10" and "fewer than 1 in 10" state the same two. Below the
    floor there is no frequency at all."""
    result = find(engine)
    prior = find(engine, review_type=TRUTH["comparables"]["narrower_review_type"])

    # 2 of 49 rounds to 0 in 10, which the screen writes as "fewer than 1 in 10".
    assert result["frequencies"] == {"q80": [8, 10], "plan": {"words": "fewer_than", "states": [1, 10]}}
    assert result["summary"]["frequencies"] == result["frequencies"]
    assert prior["frequencies"] is None


def test_the_plan_s_share_says_about_when_it_rounds_to_between_1_and_9_in_10(engine):
    """With review type Post, values.toml's signed Post comparables hold both packages signed within
    the plan's 1.5 months. 2 of 36 is 0.56 in 10, which rounds to about 1 in 10."""
    post = [c["reference"] for c in COMPARABLES if c.get("review_type") == "Post"]
    within = [reference for reference in post if reference in PAST_RANGE["signed_within_plan"]]

    result = find(engine, review_type="Post")

    assert (result["counts"]["comparables"], result["plan"]["within"]) == (len(post), len(within))
    assert len(within) == len(PAST_RANGE["signed_within_plan"])
    assert result["frequencies"]["plan"] == {"words": "about", "states": [1, 10]}


def block(text: str, *keys: str) -> str:
    """The body of the object at keys in a TypeScript file, found by its braces, so a formatter that
    changes the indentation changes nothing here."""
    import re

    for key in keys:
        found = re.search(rf"\b{key}: \{{", text)
        assert found, f"no {key} in the copy file"
        depth, end = 1, found.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            end += 1
        text = text[found.end():end - 1]
    return text


def top_level_keys(body: str) -> set[str]:
    import re

    keys, depth = set(), 0
    for found in re.finditer(r"[{}]|\b(\w+):", body):
        if found.group(0) in "{}":
            depth += 1 if found.group(0) == "{" else -1
        elif depth == 0:
            keys.add(found.group(1))
    return keys


def test_the_screen_s_copy_file_has_a_phrase_for_every_reason_and_the_abstention_s_sentence():
    """A reason code added to the registry without its phrase would leave a gap in the coverage line."""
    copy = (ROOT / "web" / "src" / "copy.ts").read_text()
    past_range = block(copy, "pastRange")

    phrases = top_level_keys(block(past_range, "reasons"))

    assert set(config.load_tools()["find_comparables"].result.reasons) - phrases == set()
    # The spec's sentence for fewer than 20 comparables, with N filled from the rows on screen.
    assert "I'm not giving a range: only {n} comparable packages. Here are all {n}." in past_range


def test_the_screen_s_floor_for_about_n_in_10_is_the_thresholds_file_s():
    """web/src/lib/format.ts writes the floor below which no screen says "about N in 10", because the
    Node test runner cannot read the thresholds file. It must be past_range.min_comparables (rules 4 and 9)."""
    import re

    format_ts = (ROOT / "web" / "src" / "lib" / "format.ts").read_text()
    [written] = re.findall(r"export const FEWEST_FOR_A_FREQUENCY = (\d+);", format_ts)

    assert int(written) == config.load_thresholds().value("past_range.min_comparables")


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


def test_each_quantile_dot_names_the_packages_it_stands_for_with_their_shortest_and_longest_months(engine):
    """A quantile dot opens the evidence drawer at the packages it stands for (ticket 15), so the tool names
    them: the lists in values.toml were worked out by hand from the comparables' dates."""
    context = registry.Context(engine=engine, viewer=ANA, thresholds=with_past_range(quantile_dots_above=40))

    result = registry.call("find_comparables", {"step_reference": PACKAGE, "as_of": AS_OF}, context)

    dots = result["quantile_dots"]
    assert [dot["step_references"] for dot in dots] == PAST_RANGE["quantile_dot_packages"]
    assert [dot["count"] for dot in dots] == [len(names) for names in PAST_RANGE["quantile_dot_packages"]]
    assert all(dot["still_open"] == 0 for dot in dots)
    # Dot 2 sits at 85 days (2.8 months) among packages signed in 82, 85 and 89 days.
    assert (dots[1]["low_months"], dots[1]["high_months"]) == (2.7, 2.9)
    # Dots 3 and 4 both sit at 89 days, and each stands for two of the five packages signed then.
    assert (dots[2]["low_months"], dots[2]["high_months"], dots[3]["low_months"], dots[3]["high_months"]) == (2.9, 2.9, 2.9, 2.9)
    assert (dots[19]["low_months"], dots[19]["high_months"]) == (17.4, 17.7)


def test_a_wider_variant_with_more_than_60_comparables_gives_20_quantile_dots_and_every_row(engine):
    # Leaving the category open adds Kenya's goods packages under Request for Bids.
    result = find(engine, category="any")

    assert result["criteria"]["category"] is None
    assert len(result["rows"]) > 60
    assert len(result["quantile_dots"]) == 20
    assert result["past_range"]["q50"] is not None


def test_with_packages_still_open_at_the_end_the_last_dot_stands_for_them_and_every_dot_for_its_own_packages(engine):
    """With the category open, four goods packages were still open after the last signing (539 days), and the
    curve never reaches 39 in 40, so the last dot is hollow. Kaplan-Meier leaves them the share the last
    signings did not take, about 4 in 100, and KE-MOWI-47509-CW-RFB, the last signed, holds the share just
    before theirs, so the last dot stands for those five. The four packages that left the risk set within
    37 days, before most signings, pass their share on and no dot stands for them."""
    result = find(engine, category="any")
    rows = {row["step_reference"]: row for row in result["rows"]}
    dots = result["quantile_dots"]

    last = dots[-1]
    assert (last["reached"], last["step_references"]) == (False, [
        "KE-MOWI-47509-CW-RFB", "KE-MOWASCO-285253-GO-RFB", "KE-WASREB-187622-GO-RFB", "KE-WAJWASCO-154021-GO-RFB",
        "KE-KWAWASCO-63985-GO-RFB"])
    assert (last["count"], last["still_open"], last["low_months"], last["high_months"]) == (5, 4, 17.7, 87.4)
    named = [reference for dot in dots for reference in dot["step_references"]]
    early = {"KE-MIGORI COUNTY-532367-CW-RFB", "KE-ICTA-571738-CW-RFB", "KE-UASIN GISHU COUNTY-571338-CW-RFB",
             "KE-KAJIADO COUNTY-567787-CW-RFB"}
    assert sorted(named) == sorted(set(rows) - early)
    for dot in dots:
        days = [rows[reference]["days"] for reference in dot["step_references"]]
        assert min(days) <= dot["days"] <= max(days), dot["k"]


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
    # The empty state names the country it looked in, as the World Bank lists it.
    assert (nothing["criteria"]["country"], nothing["criteria"]["country_name"]) == ("IN", "India")
    assert unmeasured["abstention"]["reason"] == "none_measurable"
    assert unmeasured["abstention"]["matched"] == unmeasured["coverage"]["matched"] > 0
    assert unmeasured["rows"] == nothing["rows"] == []
