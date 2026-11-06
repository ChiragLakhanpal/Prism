"""The planned dates' per-step backtests through the replay harness (spec, seam 5; ticket 27, criterion 1).

Each test year freezes Prism on January 1, dates each step first planned in that year from the comparables
public then, and scores it against the actual dates public by the outcomes date: how many came on or before the
cautious and the middle date, and the typical error against each and against the plan. The known answer is
tests/ground_truth/values.toml's [step_dates], on the hand-made set tests/step_set.py builds. MLflow is behind the
offline tracker here; ops/estimates/step_backtest_live.py runs the same backtests on the workspace.
"""

import dataclasses
import datetime as dt
import tomllib
from pathlib import Path

import pytest
import step_set

from strata.config import load_thresholds
from strata.dbx import Viewer
from strata.estimates import harness, step_dates
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
KNOWN = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["step_dates"]
RAN_AT = dt.datetime(2022, 7, 1, 6, 0, tzinfo=dt.UTC)
SCORED = ("bid_invitation", "bidding_document_issued", "bid_opening", "bid_evaluation_report", "contract_signed")


def run_2021(engine, tracker=None, store=None):
    return step_dates.backtest(engine, tracker or OfflineTracker(), years=(2021,),
                               outcomes_through=KNOWN["backtest_outcomes_through"], store=store, ran_at=RAN_AT)


@pytest.fixture(scope="module")
def ran_2021(tmp_path_factory):
    engine, tracker = step_set.build(tmp_path_factory.mktemp("step-backtest") / "set.duckdb"), OfflineTracker()
    run_2021(engine, tracker)
    yield engine, tracker
    engine.close()


def test_the_backtest_for_2021_stores_the_known_scores_of_the_hand_made_set(ran_2021):
    engine, _ = ran_2021

    year = step_dates.stored_years(engine)[2021]

    assert (year["cutoff"], year["outcomes_through"]) == (KNOWN["backtest_cutoff"], KNOWN["backtest_outcomes_through"])
    assert (year["steps_total"], year["steps_inside_cautious"], year["steps_inside_middle"]) == (
        KNOWN["backtest_total"], KNOWN["backtest_inside_cautious"], KNOWN["backtest_inside_middle"])
    assert (year["error_cautious_days"], year["error_middle_days"], year["error_plan_days"]) == (
        KNOWN["backtest_error_cautious_days"], KNOWN["backtest_error_middle_days"], KNOWN["backtest_error_plan_days"])
    # The middle date's typical error (9 days) beat the plan's own (20): the year records it.
    assert year["beat_plan"] == 1


def test_each_step_has_its_own_coverage_and_error_against_the_plan_with_the_years_mlflow_run(ran_2021):
    engine, tracker = ran_2021

    year = step_dates.stored_years(engine)[2021]

    assert [year[f"goods.{key}.n"] for key in SCORED] == [1] * 5
    assert [year[f"goods.{key}.inside_cautious"] for key in SCORED] == [1, 0, 1, 1, 1]
    assert year["goods.bidding_document_issued.error_plan_days"] == 22
    assert year["mlflow_run_id"] in tracker.runs and tracker.runs[year["mlflow_run_id"]].ended
    assert tracker.runs[year["mlflow_run_id"]].metrics["goods.contract_signed.inside_cautious"] == 1.0


def test_rows_made_public_after_the_cutoff_change_none_of_the_scores(tmp_path):
    """A plan of February 1, 2021 lists every comparable again with each step on its planned day. Read at the
    cutoff it would shrink every delay to nothing; the backtest never sees it."""
    engine = step_set.build(tmp_path / "set.duckdb")
    later = dt.date(2021, 2, 1)
    step_set.insert(engine, "strata.silver.plan_versions", [step_set.version("910000009", later, 9, False)])
    rows, dated = [], []
    for i in range(1, 26):
        planned, _ = step_set.comparable_dates(i)
        rows.append(step_set.plan_row("910000009", later, step_set.comparable(i), "Signed"))
        dated += step_set.steps("910000009", later, step_set.comparable(i), planned, planned)
    step_set.insert(engine, "strata.silver.plan_rows", rows)
    step_set.insert(engine, "strata.silver.plan_steps", dated)
    step_set.insert(engine, "strata.silver.plan_step_delays", [
        {**row, "first_planned_on": row["planned_on"], "first_planned_document": step_set.FIRST,
         "first_planned_plan_date": step_set.FIRST_ON, "first_listing_confirmed": True,
         "delay_days": 0 if row["planned_on"] else None} for row in dated])

    run_2021(engine)

    year = step_dates.stored_years(engine)[2021]
    engine.close()
    assert (year["steps_total"], year["steps_inside_cautious"], year["steps_inside_middle"]) == (
        KNOWN["backtest_total"], KNOWN["backtest_inside_cautious"], KNOWN["backtest_inside_middle"])


def test_on_the_fixture_each_step_and_test_year_from_2021_to_2025_has_its_scores_and_mlflow_run(fixture_db):
    """The fixture's plans give few steps 20 comparables, so the steps mostly abstain, but every step of every
    family has its row for every test year, each with the year's MLflow run id."""
    tracker = OfflineTracker()
    with DuckDBEngine.open(fixture_db, read_only=True) as engine, DuckDBEngine.open() as store:
        catalog.build(store)
        step_dates.backtest(engine, tracker, outcomes_through=dt.date(2026, 10, 22), store=store, ran_at=RAN_AT)
        stored = step_dates.stored_years(store)

    assert sorted(stored) == [2021, 2022, 2023, 2024, 2025]
    for year, scores in stored.items():
        assert scores["mlflow_run_id"] in tracker.runs, year
        for family, entry in step_dates.families().items():
            for step in entry["steps"]:
                assert f"{family}.{step['key']}.n" in scores, (year, family, step["key"])


def test_estimate_time_gives_each_choices_track_record_from_the_latest_stored_backtest(ran_2021):
    engine, tracker = ran_2021
    year = step_dates.stored_years(engine)[2021]
    viewer = Viewer(name="Ana Example")
    defaults = load_thresholds()
    # Five steps scored is short of the 20 a track record needs, so the floor is lowered here to read it.
    lowered = dataclasses.replace(defaults, values={**defaults.values, "time_estimate": {
        **defaults.values["time_estimate"], "min_unseen_packages": KNOWN["backtest_total"]}})

    def track(thresholds, as_of):
        context = registry.Context(engine=engine, viewer=viewer, thresholds=thresholds)
        return registry.call("estimate_time", {"step_reference": KNOWN["target"], "as_of": as_of},
                             context)["step_dates"]["track_record"]

    found = track(lowered, RAN_AT.date())
    assert found["cautious"] == {"year": 2021, "total": KNOWN["backtest_total"], "inside": KNOWN["backtest_inside_cautious"],
                                 "run_id": year["mlflow_run_id"], "catch_in10": 8}
    assert (found["middle"]["inside"], found["middle"]["catch_in10"]) == (KNOWN["backtest_inside_middle"], 5)
    # Before the run was stored there was no track record, and with the file's own floor there is none either.
    assert track(lowered, RAN_AT.date() - dt.timedelta(days=1)) is None
    assert track(defaults, RAN_AT.date()) is None


def test_the_live_step_backtest_stops_with_one_sentence_when_there_is_no_env_file(tmp_path, capsys, monkeypatch):
    import importlib.util
    import sys

    monkeypatch.setattr(sys, "path", list(sys.path))  # the script adds ops/ folders to the path; undo that after
    spec = importlib.util.spec_from_file_location("step_backtest_live", ROOT / "ops" / "estimates" / "step_backtest_live.py")
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)

    assert live.main(["--env-file", str(tmp_path / "missing.env")]) == 2
    assert "There is no env file" in capsys.readouterr().out
