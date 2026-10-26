"""The proposal's measures snapshot (ticket 46; the 46 brief, section 20): each result in docs/proposal/results.toml,
measured by its query through the engine adapter, with the day it was measured and its run.

Expected values come from tests/ground_truth/values.toml and from the made-up rows in tests/dashboard_seed.py and
tests/proposal_seed.py, never from the queries under test.
"""

import tomllib
from pathlib import Path

import pytest

from proposal_seed import merged
from strata.lakehouse.engine import DuckDBEngine
from strata.proposal import snapshot
from dashboard_seed import TODAY

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pulled(fixture_db):
    return merged(fixture_db)


def values():
    with open(ROOT / "tests" / "ground_truth" / "values.toml", "rb") as handle:
        return tomllib.load(handle)


def test_a_data_readiness_measure_comes_from_the_newest_run_with_its_day_and_run(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        found = snapshot.pull(engine, TODAY)["results"]["supplier-ids"]
    # values.toml, [counts.supplier_ids]: 157 awarded bidders are named the same way on their award rows, and 128 of
    # those carry the same ID.
    counted = values()["counts"]["supplier_ids"]
    assert (found["n"], found["d"]) == (counted["same_name_agrees"], counted["same_name"])
    assert found["measured"] and found["measured_on"] and found["run_id"]


def test_a_result_the_fixture_never_measured_is_kept_as_not_measured(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        found = snapshot.pull(engine, TODAY)["results"]
    assert found["benchmark-passed"] == {"measured": False}
    assert found["hindsight-caught"] == {"measured": False}


def test_kpis_come_through_the_dashboards_own_queries(pulled):
    found = pulled["results"]
    # tests/dashboard_seed.py: the October 20 gate passed 45 of 52 questions and 6 of 6 must-refuse questions.
    assert (found["benchmark-passed"]["n"], found["benchmark-passed"]["d"]) == (45, 52)
    assert (found["must-refuse"]["n"], found["must-refuse"]["d"]) == (6, 6)
    assert found["benchmark-passed"]["run_id"] == "gate-2"
    # The newer retrieval run, October 10: precision at 10 of 0.62 on the full query set.
    assert found["retrieval-precision"]["value"] == pytest.approx(0.62)
    assert found["retrieval-precision"]["measured_on"] == "2026-10-10"


def test_the_hindsight_test_gives_its_catch_the_checklists_and_its_interval_in_whole_percents(pulled):
    found = pulled["results"]
    assert (found["hindsight-caught"]["n"], found["hindsight-caught"]["d"]) == (14, 30)
    assert (found["hindsight-checklist"]["n"], found["hindsight-checklist"]["d"]) == (9, 30)
    assert found["hindsight-interval"]["measured"] is False  # 30 blamed risks is under the 50 a percentage needs


def test_the_backtest_adds_its_test_years_and_holds_back_a_percent_below_the_fewest_cases(pulled):
    found = pulled["results"]
    # tests/proposal_seed.py: 31 + 43 + 9 + 47 + 21 of 40 + 52 + 12 + 60 + 25.
    assert (found["backtest-coverage"]["n"], found["backtest-coverage"]["d"]) == (151, 189)
    years = {row["label"]: row for row in found["backtest-years"]["series"]}
    assert (years["2023"]["n"], years["2023"]["d"], years["2023"]["percent"]) == (9, 12, None)
    assert years["2024"]["percent"] == 78


def test_every_result_in_the_register_has_a_measured_value_in_the_test_snapshot(pulled):
    assert [key for key, found in pulled["results"].items() if not found["measured"]] == ["hindsight-interval"]
