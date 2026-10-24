"""Suppliers resolved on STEP supplier IDs first and names second (ticket 19), over the fixture (seam 1).

The gate builds data/out/fixture.duckdb with the nightly job's own run, so these tests read what the
run wrote: the awarded bidders it read from award notices, the candidate pairs name matching found
for rows without a STEP supplier ID, how each pair was routed, the suppliers gold holds and the
measures in strata.ops. A test that changes a threshold, a label or a decision runs on its own copy
of the database. Expected values come from tests/ground_truth/values.toml, where each one names its
recorded record, never from the code under test.
"""

import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}


@pytest.fixture(scope="module")
def fixture(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql, **params):
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def bidders(engine, notice_id):
    return rows(engine, "SELECT position, name, step_supplier_id, country, individual_consultant "
                        "FROM strata.silver.notice_bidders WHERE notice_id = :notice_id ORDER BY position",
                notice_id=notice_id)


# ── Awarded bidders, read from award notices ─────────────────────────────

def test_an_award_notice_lists_each_awarded_bidder_with_the_step_supplier_id_it_carries(fixture):
    venture = TRUTH["awkward"]["joint_venture"]  # award notice OP00125855 lists both members
    first, second = VALUES["notice-bidder-503708"], VALUES["notice-bidder-503711"]

    found = bidders(fixture, venture["notice"])

    assert [(b["name"], b["step_supplier_id"], b["country"]) for b in found] == [
        (first["name"], first["value"], "Kenya"), (second["name"], second["value"], "Kenya")]
    assert [b["step_supplier_id"] for b in found] == venture["supplier_ids"]


def test_a_consultant_award_lists_each_firm_and_keeps_no_registry_id_or_score_as_a_bidder(fixture):
    # Award notice OP00192301 lists two firms, with a Registry ID line between them and the
    # evaluation scores after them. Neither line is a bidder.
    first, second = VALUES["notice-firm-636626"], VALUES["notice-firm-637051"]

    found = bidders(fixture, first["notice"])

    assert [(b["name"], b["step_supplier_id"]) for b in found] == [(first["name"], first["value"]),
                                                                   (second["name"], second["value"])]


def test_an_individual_consultant_awarded_in_a_notice_is_never_named(fixture):
    case = VALUES["notice-individual-consultant"]

    found = bidders(fixture, case["notice"])

    assert [(b["name"], b["step_supplier_id"], b["individual_consultant"]) for b in found] == [(None, None, True)]


def measures(engine, subject):
    return {row["measure"]: (row["count"], row["denominator"]) for row in rows(
        engine, "SELECT measure, count, denominator FROM strata.ops.data_readiness WHERE run_id = 'fixture' "
                "AND source = 'notices' AND subject = :subject "
                "AND measure IN ('awarded_bidder_id_on_award', 'awarded_bidder_id_same_name')", subject=subject)}


@pytest.mark.parametrize("subject", ["KE", "all"])  # every awarded bidder with an ID in the fixture is Kenya's
def test_strata_ops_counts_how_often_an_award_notice_carries_the_supplier_id_the_awards_give(fixture, subject):
    counted = TRUTH["counts"]["supplier_ids"]

    assert measures(fixture, subject) == {
        "awarded_bidder_id_on_award": (counted["agrees"], counted["on_award"]),
        "awarded_bidder_id_same_name": (counted["same_name_agrees"], counted["same_name"]),
    }


@pytest.mark.parametrize("firm", ["tradecon", "jedel", "geoscintex"])
def test_an_award_notice_can_give_a_firm_another_step_supplier_id_than_the_awards_give_it(fixture, firm):
    """The blueprint's "7 of 7" does not hold over every award notice: these three firms carry one ID in
    their award notice and another in the awards dataset, on the same STEP reference."""
    in_notice, in_awards = VALUES[f"supplier-id-{firm}-notice"], VALUES[f"supplier-id-{firm}-award"]

    bidder = rows(fixture, "SELECT b.name, b.step_supplier_id, n.step_reference FROM strata.silver.notice_bidders AS b "
                           "JOIN strata.gold.notice AS n ON n.notice_id = b.notice_id WHERE b.notice_id = :notice",
                  notice=in_notice["notice"])
    contract = rows(fixture, "SELECT c.step_reference, c.supplier_id, s.name FROM strata.gold.contract AS c "
                             "JOIN strata.gold.supplier AS s ON s.supplier_id = c.supplier_id WHERE c.contract_id = :id",
                    id=in_awards["contract"])

    assert bidder == [{"name": in_notice["name"], "step_supplier_id": in_notice["value"],
                       "step_reference": contract[0]["step_reference"]}]
    assert contract[0]["name"] == in_notice["name"] and contract[0]["supplier_id"] == in_awards["value"]


def test_an_awarded_bidder_written_without_an_id_keeps_its_name(fixture):
    case = VALUES["notice-bidder-no-id"]  # the FY2017-19 gap's award notice, OP00044090

    found = bidders(fixture, case["notice"])

    assert [(b["name"], b["step_supplier_id"], b["individual_consultant"]) for b in found] == [
        (case["value"], None, False)]


# ── Name matching, on plain rows ─────────────────────────────────────────
# The matching function takes plain rows and returns plain rows, so the nightly task calls it the
# same way on DuckDB and on Databricks (spec, "Data and the lakehouse run"). These rows are written
# by hand, because the fixture holds few rows without an ID.

def record(key, name, country, projects=("P000001",), has_id=False, group=None):
    from strata.knowledge.suppliers.matching import Record

    return Record(key=key, name=name, country=country, projects=tuple(projects), has_id=has_id,
                  group=group if group is not None or has_id else key.split("/")[0])


def match(*records):
    from strata.config import load_supplier_matching
    from strata.knowledge.suppliers.matching import candidate_pairs

    return candidate_pairs(list(records), load_supplier_matching(), floor=0.01)


def test_a_row_with_a_step_supplier_id_never_enters_name_matching():
    """Two suppliers with IDs are never compared by name, however alike their names. Only the row with no
    ID is matched, and it may join either of them."""
    pairs = match(record("1001211", "CHINA INTERNATIONAL WATER AND ELECTRIC CORPORATION", "China", has_id=True),
                  record("534460", "China International Water & Electric Corporation", "China", has_id=True),
                  record("1513001/1", "CHINA INTERNATIONAL WATER & ELECTRIC CORP.", "China"))

    assert sorted((pair.left, pair.right) for pair in pairs) == [("1513001/1", "1001211"), ("1513001/1", "534460")]


def test_names_are_compared_without_legal_forms_accents_or_punctuation():
    pairs = match(record("1/1", "M/S Société Générale d'Études S.A.", "France"),
                  record("2/1", "SOCIETE GENERALE D ETUDES", "France"),
                  record("3/1", "ROAD & BRIDGE WORKS (K) PVT. LTD.", "Kenya"),
                  record("4/1", "Road and Bridge Works K Private Limited", "Kenya"))

    assert sorted((pair.left, pair.right, pair.name_level) for pair in pairs) == [
        ("1/1", "2/1", "same_name"), ("3/1", "4/1", "same_name")]


def test_rows_are_compared_only_within_one_country():
    assert match(record("1/1", "EGIS INTERNATIONAL", "France"), record("2/1", "EGIS INTERNATIONAL", "Kenya")) == []


def test_the_members_of_one_joint_venture_row_are_never_paired_with_each_other():
    pairs = match(record("1536431/1", "ECORYS NEDERLAND B.V.", "India"),
                  record("1536431/2", "ECORYS INDIA PVT. LTD.", "India"))

    assert pairs == []


def test_a_project_in_common_makes_the_same_name_likelier_to_be_one_supplier():
    shared = match(record("1/1", "LANDMARK HOLDINGS LIMITED", "Kenya", ["P124109"]),
                   record("2/1", "LANDMARK HOLDINGS LTD", "Kenya", ["P124109"]))
    apart = match(record("1/1", "LANDMARK HOLDINGS LIMITED", "Kenya", ["P124109"]),
                  record("2/1", "LANDMARK HOLDINGS LTD", "Kenya", ["P156634"]))

    assert shared[0].probability > apart[0].probability
    assert (shared[0].projects_level, apart[0].projects_level) == ("shared", "none_shared")


# ── Each supplier, resolved over the fixture ─────────────────────────────

def contract_supplier(engine, contract_id):
    found = rows(engine, "SELECT c.supplier_id, s.name, s.kind, s.resolved_on FROM strata.gold.contract AS c "
                         "LEFT JOIN strata.gold.supplier AS s ON s.supplier_id = c.supplier_id "
                         "WHERE c.contract_id = :contract_id", contract_id=contract_id)
    assert len(found) == 1, f"gold.contract holds {len(found)} rows for {contract_id}"
    return found[0]


def pair(engine, left_name, right_name):
    found = rows(engine, "SELECT * FROM strata.ops.supplier_pairs WHERE (left_name = :one AND right_name = :other) "
                         "OR (left_name = :other AND right_name = :one)", one=left_name, other=right_name)
    return found


def test_rows_with_no_step_supplier_id_named_alike_in_one_country_on_one_project_are_one_supplier(fixture):
    first, second = VALUES["fy2001-thales-1326397"], VALUES["fy2001-thales-1326726"]

    one, other = contract_supplier(fixture, first["contract"]), contract_supplier(fixture, second["contract"])

    assert one["supplier_id"] is not None and one["supplier_id"] == other["supplier_id"]
    assert (one["name"], one["kind"], one["resolved_on"]) == (first["value"], "firm", "name")
    [found] = [p for p in pair(fixture, first["value"], second["value"]) if p["left_key"].startswith(first["contract"])
               or p["right_key"].startswith(first["contract"])]
    assert (found["route"], found["outcome"], found["decided_by"]) == ("auto_merge", "merge", "threshold")
