"""The replay harness at seam 5: the time estimate's backtests, scored against what became public later.

The harness freezes Strata at a cutoff date (ADR 0002), runs a scorer and writes its scores to
strata.ops.evaluation_result and to MLflow. These tests run it on a small hand-made set whose answers
are known: tests/ground_truth/values.toml's [time_estimate_backtest] says how the set is made and how
each expected score was computed, once, with lifelines and numpy, never the way the harness computes
it. MLflow and Unity Catalog are behind the offline tracker here; ops/estimates/backtest_live.py runs
the same backtests on the workspace.
"""

import datetime as dt
import shutil
import tomllib
from pathlib import Path

import pytest

from strata.estimates import backtest, harness
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
KNOWN = TRUTH["time_estimate_backtest"]
DAY = dt.timedelta(days=1)
PROJECT = "P900001"
FIRST_VERSION, SECOND_VERSION, LATER_VERSION = "900000001", "900000002", "900000003"
CANCELED = "KE-T00-100000-CW-RFB"
NO_COMPARABLES = "KE-S25-200025-CW-RFQ"


# ── The hand-made set ────────────────────────────────────────────────────

def training_packages():
    """(STEP reference, notice date, signing date) for the 80 training packages."""
    return [(f"KE-T{i:02d}-{100000 + i}-CW-RFB", dt.date(2019, 1, 2) + 9 * (i - 1) * DAY,
             dt.date(2019, 1, 2) + (9 * (i - 1) + 30 + (7 * i * i) % 251) * DAY) for i in range(1, 81)]


def packages_advertised_in_2021():
    """(STEP reference, notice date, signing date) for the 24 packages advertised in 2021."""
    return [(f"KE-S{j:02d}-{200000 + j}-CW-RFB", dt.date(2021, 1, 11) + 14 * (j - 1) * DAY,
             dt.date(2021, 1, 11) + (14 * (j - 1) + 60 + (71 * j) % 300) * DAY) for j in range(1, 25)]


def insert(engine, table, rows):
    columns = tuple(rows[0])
    engine.insert_rows(table, columns, [tuple(row[column] for column in columns) for row in rows])


def plan_version(document_id, plan_date):
    return {"document_id": document_id, "project_id": PROJECT, "implementing_agency": "Hand-made Water Agency",
            "plan_date": plan_date, "disclosed_on": plan_date, "series_order": int(document_id[-1]),
            "previous_document_id": None, "is_latest": False, "pdf_pages": 1, "route_b_pages": 1,
            "text_url": f"https://example.org/{document_id}.txt", "pdf_url": f"https://example.org/{document_id}.pdf",
            "public_from": plan_date}


def plan_row(document_id, public_from, reference, method="Request for Bids", status="Pending Implementation",
             amount="1000000.00", review="Post", approach="Open - National", prequalification="N"):
    return {"document_id": document_id, "project_id": PROJECT, "section": "WORKS", "activity_reference_no": reference,
            "description": "Hand-made works", "review_type": review, "method": method, "market_approach": approach,
            "prequalification": prequalification, "estimated_amount_usd": amount, "process_status": status,
            "pdf_page": 1, "parser": "hand-made", "public_from": public_from}


def first_listing(document_id, public_from, reference, planned_days):
    planned_notice = dt.date(2019, 3, 1)
    return [{"document_id": document_id, "project_id": PROJECT, "activity_reference_no": reference, "step": step,
             "step_order": order, "planned_on": day, "first_planned_on": day, "first_planned_document": document_id,
             "first_planned_plan_date": public_from, "first_listing_confirmed": True, "public_from": public_from}
            for step, order, day in (("Specific Procurement Notice / Invitation", 1, planned_notice),
                                     ("Signed Contract", 2, planned_notice + planned_days * DAY))]


# Kenya's CPIA and WGI scores for 2017, as published on September 25, 2018: every package has them.
GOVERNANCE_2017 = {"GOV_WGI_GE.EST": -0.5, "IQ.CPA.IRAI.XQ": 3.2}


def governance(code, year, value, published):
    return {"country_code": "KE", "indicator_id": code, "year": year, "value": value, "public_from": published}


def package(reference, notice_on, signed_on, method="Request for Bids", status="Pending Implementation"):
    """A package's gold rows: its notice, its contract when it has one, and its package row."""
    notice = {"notice_id": f"N-{reference}", "notice_type": "Invitation for Bids", "notice_date": notice_on,
              "project_id": PROJECT, "country_code": "KE", "step_reference": reference,
              "procurement_category": "Works", "procurement_method": method, "public_from": notice_on}
    contract = None if signed_on is None else {
        "contract_id": f"C-{reference}", "source": "awards", "project_id": PROJECT, "country_code": "KE",
        "step_reference": reference, "procurement_category": "Works", "procurement_method": method,
        "review_type": "Post", "contract_signing_date": signed_on, "contract_amount_usd": "900000.00",
        "amount_basis": "US dollars", "supplier_count": 1, "joint_venture": False, "public_from": signed_on}
    row = {"step_reference": reference, "project_id": PROJECT, "country_code": "KE", "procurement_category": "Works",
           "procurement_method": method, "first_notice_id": notice["notice_id"], "first_notice_type": "Invitation for Bids",
           "first_notice_date": notice_on, "contract_signed_on": signed_on,
           "signed_in": "contract awards" if signed_on else None, "contract_count": 1 if signed_on else 0,
           "review_type": "Post" if signed_on else None, "process_status": status, "public_from": notice_on}
    return notice, contract, row


def hand_made(tmp_path) -> DuckDBEngine:
    """The hand-made set in a DuckDB file under tmp_path, with every table the catalog defines."""
    engine = DuckDBEngine.open(tmp_path / "hand-made.duckdb")
    catalog.build(engine)
    first, second = dt.date(2019, 1, 1), dt.date(2020, 12, 15)
    insert(engine, "strata.gold.country", [{"country_code": "KE", "country_name": "Kenya",
                                             "region": "Eastern and Southern Africa", "public_from": dt.date(2008, 12, 10)}])
    insert(engine, "strata.gold.project", [{"project_id": PROJECT, "project_name": "Hand-made works project",
                                             "country_code": "KE", "region": "Eastern and Southern Africa",
                                             "public_from": dt.date(2018, 1, 1)}])
    insert(engine, "strata.silver.plan_versions", [plan_version(FIRST_VERSION, first), plan_version(SECOND_VERSION, second)])
    insert(engine, "strata.gold.governance_score", [governance(code, 2017, value, dt.date(2018, 9, 25))
                                                     for code, value in GOVERNANCE_2017.items()])
    notices, contracts, packages, rows, listings = [], [], [], [], []
    everything = ([(reference, notice, signed, "Request for Bids") for reference, notice, signed in training_packages()]
                  + [(reference, notice, signed, "Request for Bids") for reference, notice, signed in packages_advertised_in_2021()]
                  + [(CANCELED, dt.date(2020, 3, 2), None, "Request for Bids"),
                     (NO_COMPARABLES, dt.date(2021, 3, 1), dt.date(2021, 5, 1), "Request for Quotations")])
    for reference, notice_on, signed_on, method in everything:
        status = "Canceled" if reference == CANCELED else "Pending Implementation"
        notice, contract, row = package(reference, notice_on, signed_on, method, status)
        notices.append(notice)
        contracts += [contract] if contract else []
        packages.append(row)
        rows += [plan_row(FIRST_VERSION, first, reference, method),
                 plan_row(SECOND_VERSION, second, reference, method, status)]
        listings += first_listing(FIRST_VERSION, first, reference, planned_days=120)
    insert(engine, "strata.gold.notice", notices)
    insert(engine, "strata.gold.contract", contracts)
    insert(engine, "strata.gold.package", packages)
    insert(engine, "strata.silver.plan_rows", rows)
    insert(engine, "strata.silver.plan_step_delays", listings)
    return engine


def run_2021(engine, tracker=None):
    return backtest.run(engine, tracker or OfflineTracker(), years=(2021,), outcomes_through=KNOWN["outcomes_through"])


@pytest.fixture(scope="module")
def ran_2021(tmp_path_factory):
    """One 2021 backtest on the hand-made set, which the tests that only read its results share."""
    engine, tracker = hand_made(tmp_path_factory.mktemp("ran-2021")), OfflineTracker()
    run = run_2021(engine, tracker)
    yield engine, tracker, run
    engine.close()


# ── The known answer ─────────────────────────────────────────────────────

KNOWN_SCORES = ("training_packages", "calibration_packages", "calibration_still_open", "e25_days", "e50_days",
                "e75_days", "e80_days", "ranges_given", "abstained", "still_open_undecided", "n", "m", "expected",
                "coverage", "width_80_months", "width_50_months", "error_packages", "error_estimate_months",
                "error_past_range_months", "error_plan_months", "middle_ran_longer", "middle_in10",
                "eight_in_ten_ran_longer", "eight_in_ten_in10")


def test_the_backtest_for_2021_stores_the_known_scores_of_the_hand_made_set(ran_2021):
    engine, _, _ = ran_2021

    year = backtest.stored_years(engine)[2021]
    assert {score: year[score] for score in KNOWN_SCORES} == {score: KNOWN[score] for score in KNOWN_SCORES}
    assert (year["cutoff"], year["outcomes_through"]) == (KNOWN["cutoff"], KNOWN["outcomes_through"])
    # Every miss of an upper 8-in-10 point is a late one; both plan-date points are counted over n.
    assert (year["misses_early"], year["misses_late"]) == (0, KNOWN["n"] - KNOWN["m"])
    assert year["middle_total"] == year["eight_in_ten_total"] == KNOWN["n"]
    assert year["training_through"] == KNOWN["cutoff"].isoformat()
    # The estimate's typical error (2.2 months) did not beat the past range's (2.0): the year records the loss.
    assert year["beat_past_range"] == 0


# ── Leakage ──────────────────────────────────────────────────────────────

def publish_after_the_cutoff(engine):
    """Rows that became public after January 1, 2021, each of which would change a feature or a label
    if the backtest read it: a plan version that re-lists every package as much larger, Prior review,
    open internationally and prequalified, with a first listing of its own planned 400 days long; CPIA
    and WGI scores for Kenya; and a second notice for a training package."""
    later = dt.date(2021, 2, 1)
    insert(engine, "strata.silver.plan_versions", [plan_version(LATER_VERSION, later)])
    references = [reference for reference, _, _ in training_packages() + packages_advertised_in_2021()]
    insert(engine, "strata.silver.plan_rows", [
        plan_row(LATER_VERSION, later, reference, amount="50000000.00", review="Prior", approach="Open - International",
                 prequalification="Y") for reference in references])
    insert(engine, "strata.silver.plan_step_delays",
           [step for reference in references for step in first_listing(LATER_VERSION, later, reference, planned_days=400)])
    insert(engine, "strata.gold.governance_score", [governance(code, 2020, value, dt.date(2021, 1, 2))
                                                     for code, value in (("GOV_WGI_GE.EST", -0.4), ("IQ.CPA.IRAI.XQ", 3.4))])
    insert(engine, "strata.gold.notice", [{
        "notice_id": "N-KE-T80-again", "notice_type": "Invitation for Bids", "notice_date": dt.date(2021, 1, 20),
        "project_id": PROJECT, "country_code": "KE", "step_reference": training_packages()[-1][0],
        "procurement_category": "Works", "procurement_method": "Request for Bids", "public_from": dt.date(2021, 1, 20)}])


def test_rows_made_public_after_the_cutoff_change_none_of_the_scores(tmp_path):
    engine = hand_made(tmp_path)
    publish_after_the_cutoff(engine)

    run_2021(engine)

    year = backtest.stored_years(engine)[2021]
    assert {score: year[score] for score in KNOWN_SCORES} == {score: KNOWN[score] for score in KNOWN_SCORES}
    # The model learned from the plan as it stood before the cutoff: one size and one planned duration.
    assert year["feature_ranges"] == harness.as_json({"estimated_amount_usd": [1000000.0, 1000000.0],
                                                      "planned_days": [120, 120]})
    # Each package keeps the governance scores published before the cutoff, not the 2020 ones published after.
    reader = harness.Reader(engine, KNOWN["cutoff"], backtest.load_thresholds())
    packages = backtest.packages_as_of(reader, backtest.load_time_estimate())
    assert {(item.features["governance:GOV_WGI_GE.EST"], item.features["governance:IQ.CPA.IRAI.XQ"])
            for item in packages.values()} == {tuple(GOVERNANCE_2017.values())}


class ReadsEveryContract:
    """A scorer that forgets to limit its query to the date it was frozen at."""

    name, model = "careless_scorer", None

    def score(self, replay):
        replay.inputs.rows("SELECT contract_id, public_from FROM strata.gold.contract")
        return harness.Scored([])


def test_the_harness_refuses_a_row_a_scorer_reads_from_after_its_cutoff(tmp_path):
    engine = hand_made(tmp_path)
    window = harness.Window(KNOWN["cutoff"], KNOWN["outcomes_through"], "test_year", "2021")

    with pytest.raises(harness.LeakageError, match="frozen at 2021-01-01"):
        harness.replay(engine, ReadsEveryContract(), window, OfflineTracker(), "run-1",
                       dt.datetime(2026, 10, 24, tzinfo=dt.UTC))
    assert harness.latest_run(engine, ReadsEveryContract.name) is None


# ── MLflow, Unity Catalog and the model card ─────────────────────────────

MODEL = "strata.gold.time_estimate"


def test_each_test_year_is_logged_to_mlflow_and_stored_with_that_run_id(ran_2021):
    engine, tracker, _ = ran_2021

    year = backtest.stored_years(engine)[2021]
    logged = tracker.runs[year["mlflow_run_id"]]
    assert (logged.params["test_year"], logged.params["cutoff"], logged.params["outcomes_through"]) == (
        "2021", "2021-01-01", "2022-06-30")
    assert {key: logged.metrics[key] for key in ("n", "m", "expected", "width_80_months", "error_estimate_months")} == {
        key: KNOWN[key] for key in ("n", "m", "expected", "width_80_months", "error_estimate_months")}
    assert logged.model is not None and logged.ended


def test_the_model_is_registered_as_champion_with_a_card_from_the_stored_results(ran_2021):
    engine, tracker, run = ran_2021

    assert (run.version, run.alias, tracker.alias_version(MODEL, "champion")) == (1, "champion", 1)
    card = tracker.models[MODEL][0].card
    assert card == run.card == tracker.runs[tracker.models[MODEL][0].run_id].texts["model_card.md"]
    for section in ("## Data", "## Features", "## What it never reads", "## Backtests", "## Coverage",
                    "## Track record", "## When it gives no range"):
        assert section in card
    year = backtest.stored_years(engine)[2021]
    assert (f"| 2021 | {KNOWN['n']} | {KNOWN['m']} | {KNOWN['expected']} | {KNOWN['width_80_months']:.1f} | "
            f"{KNOWN['width_50_months']:.1f} | {KNOWN['error_estimate_months']:.1f} | "
            f"{KNOWN['error_past_range_months']:.1f} | {KNOWN['error_plan_months']:.1f} | {year['mlflow_run_id']} |") in card
    # 14 of 23 is 61 percent, under the 75 to 85 percent band: the card says so and why.
    assert (f"2021: {KNOWN['m']} of {KNOWN['n']} finished inside the 8-in-10 range (61 percent), outside the band. "
            "Shortfall: 14 percentage points. A likely cause:") in card
    assert "Fewer than 20 comparable packages, subgroups included" in card
    assert "Signed amounts" in card and "ICR" in card and "Revised dates" in card and "Later ratings" in card


def test_a_second_run_is_appended_and_its_model_waits_as_challenger(tmp_path):
    engine, tracker = hand_made(tmp_path), OfflineTracker()
    first = run_2021(engine, tracker)

    second = run_2021(engine, tracker)

    assert (second.version, second.alias) == (2, "challenger")
    assert tracker.alias_version(MODEL, "champion") == 1
    assert harness.latest_run(engine, backtest.SCORER) == second.run_id
    assert harness.run_rows(engine, first.run_id) and first.run_id != second.run_id


# ── The track record ─────────────────────────────────────────────────────

def store_a_test_year(engine, year, n, m, ran_at=dt.datetime(2030, 1, 1, tzinfo=dt.UTC)):
    """A run's stored counts for one test year, written as any scorer's results are."""
    window = harness.Window(dt.date(year, 1, 1), dt.date(year + 1, 6, 30), "test_year", str(year))
    scores = [harness.Score("n", n), harness.Score("m", m), harness.Score("expected", round(0.8 * n)),
              harness.Score("misses_early", 0), harness.Score("misses_late", n - m)]
    harness.write(engine, [harness.row(f"run-{ran_at:%Y}", backtest.TimeEstimateBacktest(backtest.load_time_estimate()),
                                       window, score, f"mlflow-run-{ran_at:%Y}", ran_at) for score in scores])


def test_the_track_record_comes_from_the_stored_backtest(ran_2021):
    engine, _, run = ran_2021

    assert "Of 23 packages from 2021 that Strata had not seen, 14 finished inside its 8-in-10 range" in run.card
    assert backtest.track_record(engine) == {
        "year": 2021, "n": KNOWN["n"], "m": KNOWN["m"], "expected": KNOWN["expected"], "misses_early": 0,
        "misses_late": KNOWN["n"] - KNOWN["m"], "ran_on": backtest.stored_years(engine)[2021]["ran_at"].date(),
        "mlflow_run_id": backtest.stored_years(engine)[2021]["mlflow_run_id"], "abstention": None}


def test_the_track_record_is_read_from_the_latest_stored_run_never_typed(tmp_path):
    engine = hand_made(tmp_path)
    store_a_test_year(engine, 2024, n=40, m=30)

    store_a_test_year(engine, 2025, n=31, m=25, ran_at=dt.datetime(2031, 1, 1, tzinfo=dt.UTC))

    record = backtest.track_record(engine)
    assert (record["year"], record["n"], record["m"], record["mlflow_run_id"]) == (2025, 31, 25, "mlflow-run-2031")
    assert backtest.track_record_sentence(engine) == (
        "Of 31 packages from 2025 that Strata had not seen, 25 finished inside its 8-in-10 range, where a "
        "well-sized range catches about 25.")


def test_the_track_record_abstains_when_the_latest_test_year_has_fewer_than_20_unseen_packages(tmp_path):
    engine = hand_made(tmp_path)
    store_a_test_year(engine, 2025, n=19, m=15)

    assert backtest.track_record(engine) == {"year": 2025, "abstention": {
        "reason": "too_few_unseen_packages", "n": 19, "min_unseen_packages": 20}}
    assert backtest.track_record_sentence(engine) == (
        "Strata has fewer than 20 packages from 2025 that it had not seen, so it gives no track record yet.")


# ── When the time estimate abstains ──────────────────────────────────────

def frozen_2021(engine):
    """The model the 2021 backtest learned, and the package features as of its cutoff."""
    settings, thresholds = backtest.load_time_estimate(), backtest.load_thresholds()
    model = backtest.train(engine, KNOWN["cutoff"], settings, thresholds)
    reader = harness.Reader(engine, KNOWN["cutoff"], thresholds)
    return model, backtest.packages_as_of(reader, settings), thresholds


def test_a_package_with_fewer_than_20_comparables_or_a_subgroup_under_20_gets_an_abstention(tmp_path):
    model, packages, thresholds = frozen_2021(hand_made(tmp_path))
    features, cutoff = packages["KE-S01-200001-CW-RFB"].features, KNOWN["cutoff"]

    assert model.estimate(features, 19, cutoff, thresholds)["abstention"] == {
        "reason": "too_few_comparables", "count": 19, "min_comparables": 20}
    assert model.estimate(features, 40, cutoff, thresholds, went_with=19)["abstention"] == {
        "reason": "too_few_in_subgroup", "k": 19, "count": 40, "min_subgroup": 20}
    for given in (model.estimate(features, 20, cutoff, thresholds), model.estimate(features, 40, cutoff, thresholds, went_with=20)):
        assert given["abstention"] is None
        assert (given["q25"], given["q50"], given["q75"], given["q80"]) == (
            KNOWN["e25_months"], KNOWN["e50_months"], KNOWN["e75_months"], KNOWN["e80_months"])


def test_the_time_estimate_abstains_before_its_training_date_and_outside_what_it_learned_from(tmp_path):
    model, packages, thresholds = frozen_2021(hand_made(tmp_path))
    features = packages["KE-S01-200001-CW-RFB"].features

    assert model.estimate(features, 40, dt.date(2020, 12, 31), thresholds)["abstention"] == {
        "reason": "asof_before_training", "as_of": "2020-12-31", "training_through": "2021-01-01"}
    larger = {**features, "estimated_amount_usd": 5_000_000.0}
    assert model.estimate(larger, 40, KNOWN["cutoff"], thresholds)["abstention"] == {
        "reason": "outside_training", "feature": "estimated_amount_usd", "value": 5_000_000.0,
        "low": 1_000_000.0, "high": 1_000_000.0}


# ── The fixture ──────────────────────────────────────────────────────────

def test_the_backtests_for_2021_to_2025_run_on_the_fixture_and_hold_back_its_track_record(fixture_db, tmp_path):
    shutil.copyfile(fixture_db, tmp_path / "fixture.duckdb")
    engine, tracker = DuckDBEngine.open(tmp_path / "fixture.duckdb"), OfflineTracker()

    run = backtest.run(engine, tracker, outcomes_through=TRUTH["past_range"]["as_of"])

    years = backtest.stored_years(engine)
    assert sorted(years) == [2021, 2022, 2023, 2024, 2025]
    assert len({record["mlflow_run_id"] for record in years.values()}) == 5
    for year, record in years.items():
        assert (record["cutoff"], record["training_through"]) == (dt.date(year, 1, 1), f"{year}-01-01")
    # Each year's model learned from more packages than the year before: all those measurable by its cutoff.
    learned = [years[year]["training_packages"] for year in sorted(years)]
    assert learned == sorted(set(learned))
    # The fixture holds a few plans, so no test year has 20 packages it had not seen: no track record.
    assert all(record["n"] < 20 for record in years.values())
    assert backtest.track_record(engine)["abstention"]["reason"] == "too_few_unseen_packages"
    assert (run.version, run.alias) == (1, "champion")
    engine.close()
