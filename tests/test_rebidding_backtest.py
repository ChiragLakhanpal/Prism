"""The rebidding models at seam 5: calibrated gradient boosting against logistic regression, backtested through the
replay harness, and the champion's natural frequency through rebidding_risk at seam 2.

The fixture has three packages advertised again among 52 comparables, too few for any backtest to show
calibration, so these tests run the harness on a small hand-made set whose answers are known:
tests/ground_truth/values.toml's [rebidding_backtest] says how the set is made and how each expected score was
computed, once, with scikit-learn and exact fractions, never the way the backtest computes it. MLflow and Unity
Catalog are behind the offline tracker; ops/estimates/rebidding_backtest_live.py runs the same backtests on the
workspace.
"""

import datetime as dt
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from strata.config import load_rebidding
from strata.dbx import Viewer
from strata.estimates import harness, rebidding_backtest
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
KNOWN = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["rebidding_backtest"]
DAY = dt.timedelta(days=1)
PROJECT = "P900002"
FIRST, SECOND, LATER = ("900000101", dt.date(2019, 7, 1)), ("900000102", dt.date(2020, 12, 15)), ("900000103", dt.date(2022, 3, 1))
PRIOR_AGAIN = {3, 6, 9, 12, 15, 18, 21, 27, 30, 33, 36, 39, 60}
POST_AGAIN = {1, 2, 4, 5, 7, 10, 11, 28, 52}
TESTED_AGAIN = {1, 2, 3, 6, 9, 12, 15}
UNDECIDED = "KE-R25-300025-CW-RFB"
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")


# ── The hand-made set ────────────────────────────────────────────────────

def training():
    """(STEP reference, notice date, review type, advertised again) for the 84 training packages."""
    return [(f"KE-R{i:02d}-{100000 + i}-CW-RFB", dt.date(2019, 7, 2) + 5 * (i - 1) * DAY,
             "Prior" if i % 3 == 0 else "Post", i in PRIOR_AGAIN | POST_AGAIN) for i in range(1, 85)]


def advertised_in_2021():
    """The same for the 24 packages advertised in 2021."""
    return [(f"KE-Q{j:02d}-{200000 + j}-CW-RFB", dt.date(2021, 1, 11) + 14 * (j - 1) * DAY,
             "Prior" if j % 3 == 0 else "Post", j in TESTED_AGAIN) for j in range(1, 25)]


def insert(engine, table, rows):
    columns = tuple(rows[0])
    engine.insert_rows(table, columns, [tuple(row[column] for column in columns) for row in rows])


def version(document_id, day):
    return {"document_id": document_id, "project_id": PROJECT, "implementing_agency": "Hand-made Water Agency",
            "plan_date": day, "disclosed_on": day, "series_order": int(document_id[-1]), "previous_document_id": None,
            "is_latest": False, "pdf_pages": 1, "route_b_pages": 1, "text_url": f"https://example.org/{document_id}.txt",
            "pdf_url": f"https://example.org/{document_id}.pdf", "public_from": day}


def plan_row(plan, reference, review, status="Pending Implementation", amount="1000000.00"):
    document_id, day = plan
    return {"document_id": document_id, "project_id": PROJECT, "section": "WORKS", "activity_reference_no": reference,
            "description": "Hand-made works", "review_type": review, "method": "Request for Bids",
            "market_approach": "Open - National", "prequalification": "N", "estimated_amount_usd": amount,
            "process_status": status, "pdf_page": 1, "parser": "hand-made", "public_from": day}


def notice(reference, day, notice_id=None):
    return {"notice_id": notice_id or f"N-{reference}", "notice_type": "Invitation for Bids", "notice_date": day,
            "project_id": PROJECT, "country_code": "KE", "step_reference": reference, "procurement_category": "Works",
            "procurement_method": "Request for Bids", "submission_deadline": day + 30 * DAY, "public_from": day}


def hand_made(path) -> DuckDBEngine:
    engine = DuckDBEngine.open(path)
    catalog.build(engine)
    insert(engine, "strata.gold.country", [{"country_code": "KE", "country_name": "Kenya",
                                             "region": "Eastern and Southern Africa", "public_from": dt.date(2008, 12, 10)}])
    insert(engine, "strata.gold.project", [{"project_id": PROJECT, "project_name": "Hand-made works project",
                                             "country_code": "KE", "region": "Eastern and Southern Africa",
                                             "public_from": dt.date(2018, 1, 1)}])
    insert(engine, "strata.silver.plan_versions", [version(*FIRST), version(*SECOND), version(*LATER)])
    undecided = (UNDECIDED, dt.date(2021, 12, 1), "Post", False)
    notices, contracts, packages, rows = [], [], [], []
    for group, (reference, day, review, again) in [("train", item) for item in training()] + \
            [("test", item) for item in advertised_in_2021()] + [("undecided", undecided)]:
        notices.append(notice(reference, day))
        signed = None if again or group == "undecided" else day + 60 * DAY
        if signed:
            contracts.append({"contract_id": f"C-{reference}", "source": "awards", "project_id": PROJECT,
                              "country_code": "KE", "step_reference": reference, "procurement_category": "Works",
                              "procurement_method": "Request for Bids", "review_type": review,
                              "contract_signing_date": signed, "contract_amount_usd": "900000.00",
                              "amount_basis": "US dollars", "supplier_count": 1, "joint_venture": False,
                              "public_from": signed})
        packages.append({"step_reference": reference, "project_id": PROJECT, "country_code": "KE",
                         "procurement_category": "Works", "procurement_method": "Request for Bids",
                         "first_notice_id": f"N-{reference}", "first_notice_type": "Invitation for Bids",
                         "first_notice_date": day, "bids_due": day + 30 * DAY, "contract_signed_on": signed,
                         "contract_count": 1 if signed else 0, "public_from": day})
        canceled = "Canceled" if again else "Pending Implementation"
        rows += [plan_row(FIRST, reference, review), plan_row(SECOND, reference, review, canceled if group == "train" else "Pending Implementation")]
        if group != "train":
            rows.append(plan_row(LATER, reference, review, canceled))
    insert(engine, "strata.gold.notice", notices)
    insert(engine, "strata.gold.contract", contracts)
    insert(engine, "strata.gold.package", packages)
    insert(engine, "strata.silver.plan_rows", rows)
    return engine


def run_2021(engine, tracker=None, settings=None):
    return rebidding_backtest.run(engine, tracker or OfflineTracker(), years=(2021,),
                                  outcomes_through=KNOWN["outcomes_through"], settings=settings,
                                  ran_at=dt.datetime(2022, 7, 1, 9, tzinfo=dt.UTC))


@pytest.fixture(scope="module")
def ran_2021(tmp_path_factory):
    """One 2021 backtest on the hand-made set, which the tests that only read its results share."""
    engine, tracker = hand_made(tmp_path_factory.mktemp("rebid-2021") / "hand-made.duckdb"), OfflineTracker()
    run = run_2021(engine, tracker)
    yield engine, tracker, run
    engine.close()


SCORES = ("training_packages", "training_advertised_again", "test_packages", "test_advertised_again",
          "undecided_left_out", "gbm_brier", "gbm_calibration_error", "logistic_brier", "logistic_calibration_error",
          "baseline_brier", "baseline_calibration_error")


# ── The backtest ─────────────────────────────────────────────────────────

def test_the_2021_backtest_stores_each_model_s_calibration_error_and_brier_score_and_its_baseline_s(ran_2021):
    engine, _, _ = ran_2021

    year = rebidding_backtest.stored_years(engine)[2021]
    assert {score: year[score] for score in SCORES} == {score: KNOWN[score] for score in SCORES}
    assert (year["cutoff"], year["outcomes_through"]) == (KNOWN["cutoff"], KNOWN["outcomes_through"])
    assert year["gbm_beat_baseline"] == year["logistic_beat_baseline"] == 1


def test_the_champion_is_the_better_calibrated_model_on_those_results(ran_2021):
    engine, tracker, run = ran_2021
    name = load_rebidding().registered_model

    assert run.champion == KNOWN["champion"] and run.alias == "champion"
    assert tracker.alias_version(name, "champion") == run.version
    registered = rebidding_backtest.champion(rebidding_backtest.rows_as_of(engine, KNOWN["outcomes_through"] + 1 * DAY))
    assert (registered["learner"], registered["test_year"], registered["n_test"], registered["beat_baseline"]) == (
        KNOWN["champion"], 2021, KNOWN["test_packages"], 1)
    assert registered["training_packages"] == KNOWN["champion_training_packages"]
    assert "model_card.md" in tracker.runs[tracker.models[name][0].run_id].texts


@pytest.fixture(scope="module")
def listed_the_other_way(tmp_path_factory):
    """A second 2021 backtest on a fresh hand-made set, with the learners listed in the other order, and the
    champion's scores. The test of a champion that did not beat its baseline adds a later run to it."""
    settings = load_rebidding()
    engine, tracker = hand_made(tmp_path_factory.mktemp("rebid-reversed") / "hand-made.duckdb"), OfflineTracker()
    run = run_2021(engine, tracker, settings=replace(settings, learners=tuple(reversed(settings.learners))))
    day = KNOWN["outcomes_through"] + 2 * DAY
    rebidding_backtest.score_packages(engine, tracker, "score-1", lambda: dt.datetime.combine(day, dt.time(9), dt.UTC))
    yield engine, run, day
    engine.close()


def test_the_order_the_models_are_listed_in_does_not_choose_the_champion(listed_the_other_way):
    _, run, _ = listed_the_other_way

    assert run.champion == KNOWN["champion"]


def publish_after_the_cutoff(engine):
    """Rows public after January 1, 2021, each of which would change a feature or a label if the backtest read
    it: a plan version that re-lists every package as Prior review, US$50,000,000.00, with each training package
    Canceled, and a second Invitation for Bids for a signed training package, which would make it advertised again."""
    later = ("900000104", dt.date(2021, 2, 1))
    insert(engine, "strata.silver.plan_versions", [version(*later)])
    insert(engine, "strata.silver.plan_rows", [plan_row(later, reference, "Prior", "Canceled", amount="50000000.00")
                                                for reference, _, _, _ in training()]
           + [plan_row(later, reference, "Prior", amount="50000000.00") for reference, _, _, _ in advertised_in_2021()])
    signed = next(reference for reference, _, _, again in training() if not again)
    insert(engine, "strata.gold.notice", [notice(signed, dt.date(2021, 3, 1), notice_id="N-LATE")])


def test_rows_public_after_the_cutoff_never_reach_the_models(tmp_path):
    engine = hand_made(tmp_path / "late.duckdb")
    try:
        publish_after_the_cutoff(engine)
        run_2021(engine)
        year = rebidding_backtest.stored_years(engine)[2021]
    finally:
        engine.close()

    assert {score: year[score] for score in SCORES} == {score: KNOWN[score] for score in SCORES}


# ── The natural frequency ────────────────────────────────────────────────

def rebidding(engine, as_of, **arguments):
    return registry.call("rebidding_risk", {**arguments, "as_of": as_of.isoformat()}, registry.Context(engine=engine, viewer=ANA))


@pytest.fixture(scope="module")
def scored(ran_2021):
    """The champion's scores for every package in a plan, from the nightly job's score task, the day after the run."""
    engine, tracker, run = ran_2021
    day = KNOWN["outcomes_through"] + 2 * DAY
    rebidding_backtest.score_packages(engine, tracker, "score-1", lambda: dt.datetime.combine(day, dt.time(9), dt.UTC))
    return engine, day


def test_with_20_comparables_and_a_champion_that_beat_its_baseline_the_model_gives_about_k_in_10(scored):
    """The champion is logistic regression trained on the 108 packages decided by the outcomes date: about 5 in 10
    for a Prior package and 2 in 10 for Post."""
    engine, day = scored
    prior = next(reference for reference, _, review, _ in advertised_in_2021() if review == "Prior")
    post = next(reference for reference, _, review, _ in advertised_in_2021() if review == "Post")

    for reference, k in ((prior, KNOWN["champion_in10_prior"]), (post, KNOWN["champion_in10_post"])):
        model = rebidding(engine, day, step_reference=reference)["model"]
        assert (model["shown"], model["in10"], model["band"], model["learner"]) == (True, k, "about", "logistic")
        assert model["track_record"]["n_test"] == KNOWN["test_packages"] and model["track_record"]["beat_baseline"]


def test_below_20_comparables_only_the_counts_appear(scored):
    engine, day = scored
    reference = advertised_in_2021()[-1][0]

    result = rebidding(engine, day, step_reference=reference, notice_from="2021-10-01")
    assert result["m"] < 20
    assert (result["model"]["shown"], result["model"]["in10"], result["model"]["not_shown_reason"]) == (False, None, "too_few")


def test_the_live_backtest_stops_with_one_sentence_when_there_is_no_env_file(tmp_path, capsys, monkeypatch):
    import importlib.util
    import sys

    monkeypatch.setattr(sys, "path", list(sys.path))  # the script adds ops/ folders to the path; undo that after
    path = ROOT / "ops" / "estimates" / "rebidding_backtest_live.py"
    spec = importlib.util.spec_from_file_location("rebidding_backtest_live", path)
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)

    assert live.main(["--env-file", str(tmp_path / "missing.env")]) == 2
    assert "There is no env file" in capsys.readouterr().out


def test_a_champion_that_did_not_beat_its_baseline_gives_no_natural_frequency(listed_the_other_way):
    """A later run registers a champion that did no better than its baseline: only the counts appear."""
    engine, _, day = listed_the_other_way
    reference = advertised_in_2021()[0][0]
    later = dt.datetime.combine(day, dt.time(10), dt.UTC)
    held = rebidding_backtest.champion(rebidding_backtest.rows_as_of(engine, day))
    segment = harness.Window(day, day, rebidding_backtest.REGISTERED, str(held["version"]))
    scorer = rebidding_backtest.RebiddingBacktest(load_rebidding())
    harness.write(engine, [harness.row("later-run", scorer, segment, score, None, later) for score in (
        harness.Score("alias", text="champion"), harness.Score("learner", text=held["learner"]),
        harness.Score("test_year", 2021), harness.Score("n_test", KNOWN["test_packages"]),
        harness.Score("beat_baseline", 0))])

    model = rebidding(engine, day, step_reference=reference)["model"]
    assert (model["shown"], model["in10"], model["not_shown_reason"]) == (False, None, "not_better")
    assert model["track_record"]["beat_baseline"] is False
