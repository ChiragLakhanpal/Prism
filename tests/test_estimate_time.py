"""The time estimate on screen (ticket 26) at seam 1, the lakehouse run, and seam 2, the tool contract.

The nightly job's score task scores every package Strata knows, for every what-if combination, with the
champion model the replay harness registered (ticket 25), into strata.gold.time_estimate_score, and keeps the
champion it scored with in strata.gold.time_estimate_model. On this computer no workspace registry exists, so
the task runs ticket 25's backtest first and scores with the champion it trains, as of the fixture's run day,
October 23, 2026.

estimate_time is called by name through the registry, on the fixture database. Expected values come from
tests/ground_truth/values.toml (the comparables, the narrower criteria's seven, the plan's amounts) and from the
stored batch scores the ticket names as the tool's source of truth; none is computed the way the tool computes it.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
# The demo package, estimated at US$1,230,000.00 in the October 9, 2026 plan, and the NWWDA works package
# estimated at US$300,000 that was signed on January 3, 2022 (values.toml).
DEMO = "KE-NWWDA-541055-CW-RFB"
SIGNED_2022 = "KE-NWWDA-229129-CW-RFB"
SCORED_ON = dt.date(2026, 10, 23)  # the fixture's nightly run day (gates/build_fixture.py, RUNS_START)


def value(key: str):
    return next(entry for entry in TRUTH["value"] if entry["id"] == key)["value"]


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def scores(engine, reference: str) -> list[dict]:
    return rows(engine, "SELECT * FROM strata.gold.time_estimate_score WHERE step_reference = :reference "
                        "ORDER BY market_approach, prequalification", reference=reference)


# ── Seam 1: the score task ───────────────────────────────────────────────

def test_the_score_task_keeps_the_champion_it_scored_with_and_scores_every_package_it_knows(engine):
    [champion] = rows(engine, "SELECT model, version, alias, training_through, public_from "
                              "FROM strata.gold.time_estimate_model")
    assert champion == {"model": "strata.gold.time_estimate", "version": 1, "alias": "champion",
                        "training_through": SCORED_ON, "public_from": SCORED_ON}
    # Every package the plans or the notices name has its estimate as described, scored that day by that version.
    described = rows(engine, "SELECT step_reference, model_version, training_through, public_from "
                             "FROM strata.gold.time_estimate_score WHERE as_described")
    references = {row["step_reference"] for row in described}
    assert {DEMO, SIGNED_2022} <= references
    assert len(references) == len(described)
    assert {(row["model_version"], row["training_through"], row["public_from"]) for row in described} == {
        (1, SCORED_ON, SCORED_ON)}


def test_a_package_larger_than_any_the_model_learned_from_is_stored_with_that_abstention_and_no_range(engine):
    [described] = [row for row in scores(engine, DEMO) if row["as_described"]]

    assert described["abstention"] == "outside_training"
    assert described["estimated_amount_usd"] == float(value("plan-541055-estimated"))
    assert described["q50_days"] is None and described["q80_months"] is None


def test_every_what_if_combination_of_market_approach_and_qualification_is_scored_for_a_package(engine):
    stored = scores(engine, SIGNED_2022)

    combinations = {(row["market_approach"], row["prequalification"]) for row in stored if not row["as_described"]}
    assert combinations == {(approach, qualification) for approach in ("Open - International", "Open - National")
                            for qualification in ("N", "Y")}
    [described] = [row for row in stored if row["as_described"]]
    # As described: the October 9, 2026 plan's Market Approach and no qualification recorded.
    assert (described["market_approach"], described["prequalification"]) == ("Open - National", None)
    assert described["abstention"] is None
    assert described["q25_days"] <= described["q50_days"] <= described["q75_days"] <= described["q80_days"]
