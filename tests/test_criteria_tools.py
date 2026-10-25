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


# ── rejected_bids ────────────────────────────────────────────────────────

def award_notice_texts(engine, references) -> dict[str, str]:
    """Each comparable's award notices' text, newest copy, read straight from silver.notices."""
    rows = engine.run("""
        SELECT n.notice_id, n.notice_text
        FROM strata.silver.notices AS n
        JOIN strata.gold.notice AS g ON g.notice_id = n.notice_id
        WHERE g.notice_type = 'Contract Award' AND array_contains(split(:refs, ','), g.step_reference)
          AND g.public_from <= CAST(:as_of AS DATE)
        QUALIFY row_number() OVER (PARTITION BY n.notice_id ORDER BY n.fetched_at DESC) = 1
    """, {"refs": ",".join(references), "as_of": AS_OF}).rows
    return {notice_id: text or "" for notice_id, text in rows}


@pytest.fixture(scope="module")
def rejected(engine, comparables):
    return call(engine, "rejected_bids", comparables=",".join(comparables))


def test_rejected_bids_count_the_comparable_packages_whose_award_notices_rejected_bids(engine, comparables, rejected):
    with_notice = scalar(engine, """
        SELECT count(DISTINCT step_reference) FROM strata.gold.notice
        WHERE notice_type = 'Contract Award' AND array_contains(split(:refs, ','), step_reference)
          AND public_from <= CAST(:as_of AS DATE)
    """, refs=",".join(comparables), as_of=AS_OF)
    with_rejection = scalar(engine, """
        SELECT count(DISTINCT g.step_reference)
        FROM strata.gold.notice AS g
        JOIN strata.silver.notices AS n ON n.notice_id = g.notice_id
        WHERE g.notice_type = 'Contract Award' AND array_contains(split(:refs, ','), g.step_reference)
          AND g.public_from <= CAST(:as_of AS DATE)
          AND regexp_matches(n.notice_text, :reason_given)
    """, refs=",".join(comparables), as_of=AS_OF, reason_given=r"Reason for Rejection[ \t]*\n[ \t]*\S")

    counts = rejected["summary"]["counts"]
    assert (counts["n"], counts["m"], counts["total"]) == (with_rejection, with_notice, len(comparables))
    assert 0 < with_rejection < with_notice < len(comparables)
    assert len({row["step_reference"] for row in rejected["rows"]}) == with_rejection


def test_each_reason_is_quoted_word_for_word_from_its_award_notice_with_its_notice_id(engine, comparables, rejected):
    texts = award_notice_texts(engine, comparables)

    assert rejected["rows"]
    for row in rejected["rows"]:
        assert row["notice_id"] in texts
        assert f"Reason for Rejection\n{row['reason']['quote']}" in texts[row["notice_id"]]
        assert row["evidence_id"].startswith(f"strata.gold.notice:{row['notice_id']}/")
        assert row["reason"]["lang"] == "en"


def test_the_rejected_bids_never_name_a_bidder(engine, comparables, rejected):
    import json

    names = [name for (name,) in engine.run("""
        SELECT DISTINCT b.name FROM strata.silver.notice_bidders AS b
        JOIN strata.gold.notice AS g ON g.notice_id = b.notice_id
        WHERE array_contains(split(:refs, ','), g.step_reference) AND b.name IS NOT NULL
    """, {"refs": ",".join(comparables)}).rows]
    shown = json.dumps(rejected)

    assert names
    assert [name for name in names if name in shown] == []
    assert all(set(row) == {"evidence_id", "public_from", "source", "step_reference", "country_name", "notice_id",
                            "notice_date", "item_key", "reason", "bids", "rank"} for row in rejected["rows"])


def test_reasons_are_grouped_by_the_item_they_concerned_most_packages_first_and_other_reasons_last(engine, comparables,
                                                                                                rejected):
    """A Pareto list keeps its catch-all last, whatever its count, so a group that names a cause leads (design-lead,
    31 design review F17)."""
    groups = rejected["summary"]["groups"]
    bid_security = scalar(engine, """
        SELECT count(DISTINCT g.step_reference)
        FROM strata.gold.notice AS g JOIN strata.silver.notices AS n ON n.notice_id = g.notice_id
        WHERE g.notice_type = 'Contract Award' AND array_contains(split(:refs, ','), g.step_reference)
          AND n.notice_text LIKE '%Bid Security not Provided%'
    """, refs=",".join(comparables))

    by_key = {group["item_key"]: group for group in groups}
    assert by_key["bid_security"]["count"] == bid_security
    named = [group for group in groups if group["item_key"] != "other"]
    assert groups[-1]["item_key"] == "other" and len(named) == len(groups) - 1
    assert by_key["other"]["count"] > named[0]["count"]
    assert [group["count"] for group in named] == sorted((group["count"] for group in named), reverse=True)
    assert all(row["item_key"] in by_key for row in rejected["rows"])
    # A short code such as "Non Responsive" names no item, so it falls under other reasons.
    assert any(row["reason"]["quote"] == "Non Responsive" and row["item_key"] == "other" for row in rejected["rows"])


# ── compare_criteria ─────────────────────────────────────────────────────

# The ticket's input, "similar experience of two contracts of US$10 million", as the criteria reader reads it
# into the item registry's parts (tests/fixtures/agent/recorded/criteria-similar-experience.json).
SIMILAR_EXPERIENCE = [{"item_key": "similar_experience",
                       "parts": {"contracts": 2, "amount": {"value": "10000000", "currency": "USD"}}}]
# The fixture's works comparables publish no qualification criteria, so the comparison runs on a consultant
# services package whose comparables' Requests for Expression of Interest state their short-listing criteria.
CONSULTANT = "KE-CWSB-224323-CS-QCBS"


@pytest.fixture(scope="module")
def consultant_comparables(engine):
    return [row["step_reference"] for row in call(engine, "find_comparables", step_reference=CONSULTANT)["rows"]]


@pytest.fixture(scope="module")
def criteria(engine, consultant_comparables):
    import json

    return call(engine, "compare_criteria", comparables=",".join(consultant_comparables),
                items=json.dumps(SIMILAR_EXPERIENCE))


def signed_notices_saying(engine, references, phrases) -> set[str]:
    """The signed comparables whose specific procurement notice holds any of the phrases, read straight from the
    notices' text."""
    clause = " OR ".join(f"lower(n.notice_text) LIKE :p{index}" for index in range(len(phrases)))
    return {ref for (ref,) in engine.run(f"""
        SELECT DISTINCT p.step_reference
        FROM strata.gold.package AS p
        JOIN strata.silver.notices AS n ON n.notice_id = p.first_notice_id
        JOIN strata.gold.contract AS c ON c.step_reference = p.step_reference
        WHERE array_contains(split(:refs, ','), p.step_reference) AND ({clause})
    """, {"refs": ",".join(references), **{f"p{i}": f"%{phrase}%" for i, phrase in enumerate(phrases)}}).rows}  # sql-lint: names only


def test_the_comparison_counts_the_comparable_notices_that_asked_for_similar_experience_and_how_many_asked_less(
        engine, consultant_comparables, criteria):
    [item] = criteria["summary"]["items"]
    stating = [row for row in criteria["rows"] if "similar_experience" in row["relations"]]
    asking = signed_notices_saying(engine, consultant_comparables,
                                   ["similar assignment", "similar nature", "similar projects"])

    assert item["item_key"] == "similar_experience"
    assert {row["step_reference"] for row in stating} == asking
    assert item["stated"] == len(stating) > 0
    relations = [row["relations"]["similar_experience"] for row in stating]
    assert item["same_or_less"] == relations.count("less") + relations.count("same")
    assert item["compared"] == item["same_or_less"] + relations.count("more")
    assert item["not_stated"] == criteria["summary"]["counts"]["n"] - item["stated"]
    # None of these notices asked for more than two contracts or for an amount, so each asked for the same or less.
    assert item["same_or_less"] == item["stated"]


def test_each_counted_notice_cites_the_notice_passage_that_holds_its_requirement_word_for_word(engine, criteria):
    for row in criteria["rows"]:
        for requirement in row["requirements"]:
            passage_id = requirement["passage_id"]
            [(text, kind, document)] = engine.run(
                "SELECT text, kind, document_id FROM strata.gold.passage WHERE passage_id = :id", {"id": passage_id}).rows
            assert requirement["evidence_id"] == f"strata.gold.passage:{passage_id}"
            assert (kind, document) == ("notice_text", row["notice_id"])
            assert requirement["requirement"]["text"] in text
            assert text[requirement["requirement"]["start"]:requirement["requirement"]["end"]] == \
                requirement["requirement"]["text"]


def test_a_notice_that_asked_for_two_similar_assignments_and_no_amount_asked_for_less_than_two_of_us_10_million(criteria):
    """"at least two (2) similar assignments" sets as many contracts as yours and no amount, so it asked for less."""
    twos = [row for row in criteria["rows"] for requirement in row["requirements"]
            if requirement["item_key"] == "similar_experience"
            and "at least two (2) similar assignments" in requirement["requirement"]["text"]]

    assert twos
    assert {row["relations"]["similar_experience"] for row in twos} == {"less"}


def test_packages_still_open_are_never_compared_and_the_coverage_line_names_them(engine, comparables, criteria):
    """KE-ICTA-571738-CW-RFB's notice names criteria, but its bids were due after the plan's date: a live tender."""
    import json

    works = call(engine, "compare_criteria", comparables=",".join(comparables), items=json.dumps(SIMILAR_EXPERIENCE))
    open_ones = {evidence for entry in works["coverage"]["not_used"] if entry["reason"] == "still_open"
                 for evidence in entry["evidence_ids"]}

    assert "strata.gold.package:KE-ICTA-571738-CW-RFB" in open_ones
    assert "KE-ICTA-571738-CW-RFB" not in {row["step_reference"] for row in works["rows"]}
    assert works["abstention"] == {"reason": "none_public", "total": len(comparables)}
    assert works["summary"]["counts"]["n"] == 0


def test_without_your_items_the_tool_counts_the_packages_whose_criteria_are_public(engine, consultant_comparables, criteria):
    alone = call(engine, "compare_criteria", comparables=",".join(consultant_comparables))

    assert alone["summary"]["counts"] == criteria["summary"]["counts"]
    assert alone["summary"]["items"] == []
    assert all(row["relations"] == {} for row in alone["rows"])


def test_an_item_the_registry_does_not_hold_is_refused(engine, consultant_comparables):
    import json

    with pytest.raises(registry.ToolError):
        call(engine, "compare_criteria", comparables=",".join(consultant_comparables),
             items=json.dumps([{"item_key": "price", "parts": {}}]))


# ── One records date for the whole section ───────────────────────────────

def test_every_tool_of_the_section_states_the_day_the_records_run_through_as_find_comparables_does(
        engine, comparables, consultant_comparables):
    """A source line's "Records run through {date}" is one measure (CLAUDE.md rule 4), defined by find_comparables:
    the newest notice or contract award public by the as-of date. It is never the newest award notice among the
    comparable packages, which would make one section give two dates for the same records."""
    for package, refs in ((PACKAGE, comparables), (CONSULTANT, consultant_comparables)):
        through = call(engine, "find_comparables", step_reference=package)["records_through"]
        joined = ",".join(refs)

        assert through
        assert call(engine, "rejected_bids", comparables=joined)["records_through"] == through
        assert call(engine, "compare_criteria", comparables=joined)["records_through"] == through
        assert call(engine, "compare_cost_estimates", comparables=joined)["records_through"] == through
