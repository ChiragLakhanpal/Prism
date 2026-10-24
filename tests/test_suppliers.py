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


def test_an_awarded_bidder_written_without_an_id_keeps_its_name(fixture):
    case = VALUES["notice-bidder-no-id"]  # the FY2017-19 gap's award notice, OP00044090

    found = bidders(fixture, case["notice"])

    assert [(b["name"], b["step_supplier_id"], b["individual_consultant"]) for b in found] == [
        (case["value"], None, False)]
