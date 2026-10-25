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

    [described] = [row for row in stored if row["as_described"]]
    # As described: the October 9, 2026 plan's Market Approach and no qualification recorded.
    assert (described["market_approach"], described["prequalification"]) == ("Open - National", None)
    # Each lever takes config/models.toml's values and the package's own, so a comparison that changes one
    # lever keeps the other as described.
    combinations = {(row["market_approach"], row["prequalification"]) for row in stored if not row["as_described"]}
    assert combinations == {(approach, qualification) for approach in ("Open - International", "Open - National")
                            for qualification in (None, "N", "Y")} - {("Open - National", None)}
    # Review type is never a lever: every row keeps the package's own (Post, in the October 9, 2026 plan).
    assert {row["review_type"] for row in stored} == {"Post"}
    assert described["abstention"] is None
    assert described["q25_days"] <= described["q50_days"] <= described["q75_days"] <= described["q80_days"]


# ── Seam 2: estimate_time ────────────────────────────────────────────────

def estimate(engine, step_reference=SIGNED_2022, as_of=SCORED_ON, view="staff", **criteria):
    """estimate_time for one package, called by name through the registry as Ana."""
    arguments = {"step_reference": step_reference, **criteria}
    if as_of is not None:
        arguments["as_of"] = as_of
    return registry.call("estimate_time", arguments, registry.Context(engine=engine, viewer=ANA, view=view))


POINTS = ("q25", "q50", "q75", "q80")


def test_estimate_time_returns_the_ranges_the_score_task_stored_for_the_package_and_each_combination(engine):
    result = estimate(engine)

    stored = {(row["market_approach"], row["prequalification"], row["as_described"]): row for row in scores(engine, SIGNED_2022)}
    [described] = [row for row in stored.values() if row["as_described"]]
    assert result["abstention"] is None
    assert {name: result["estimate"][name] for name in POINTS} == {name: described[f"{name}_months"] for name in POINTS}
    assert result["estimate"]["days"] == {name: described[f"{name}_days"] for name in POINTS}
    assert (result["estimate"]["model_version"], result["estimate"]["training_through"]) == (1, SCORED_ON.isoformat())
    # Every row is a stored cell: the package as described and each what-if combination, with its range or its reason.
    assert len(result["rows"]) == len(stored)
    for row in result["rows"]:
        cell = stored[(row["market_approach"], row["prequalification"], row["as_described"])]
        assert row["abstention"] == cell["abstention"]
        assert [row[name] for name in POINTS] == [cell[f"{name}_months"] for name in POINTS]
        assert row["evidence_id"].startswith("strata.gold.time_estimate_score:")


class Timed:
    """The fixture engine, timing each statement a tool runs on it."""

    def __init__(self, engine):
        self.engine, self.took = engine, []

    def run(self, sql, params=None):
        import time

        started = time.perf_counter()
        result = self.engine.run(sql, params)
        self.took.append((sql, time.perf_counter() - started))
        return result

    def __getattr__(self, name):
        return getattr(self.engine, name)


def test_the_stored_what_if_grid_is_read_within_100_ms(engine):
    """The chart answers every comparison from the grid estimate_time returns at once, so the one lookup a what-if
    needs is the tool's read of the package's stored combinations, which answers within 100 ms (the spec's
    performance budget). Timed as the tool makes it, through the registry."""
    timed = Timed(engine)

    result = registry.call("estimate_time", {"step_reference": SIGNED_2022, "as_of": SCORED_ON},
                           registry.Context(engine=timed, viewer=ANA))

    lookups = [took for sql, took in timed.took if "FROM strata.gold.time_estimate_score" in sql]
    assert len(lookups) == 1 and len(result["rows"]) == len(scores(engine, SIGNED_2022)) > 1
    assert lookups[0] < 0.1, f"the stored grid took {lookups[0] * 1000:.0f} ms"


def test_a_request_reads_the_champions_trees_from_the_warehouse_only_when_it_has_not_parsed_them(engine):
    """Every estimate made on a request asks which champion is public that day; only the first one for a version
    reads its trees, which hold the whole model."""
    from strata.config import load_time_estimate
    from strata.estimates import portable

    name = load_time_estimate().registered_model
    first = portable.latest(engine, name, SCORED_ON)
    timed = Timed(engine)

    again = portable.latest(timed, name, SCORED_ON)

    assert again.version == first.version and again.model is first.model
    assert len(timed.took) == 1 and "booster_json" not in timed.took[0][0]


def test_it_counts_the_same_comparable_packages_as_find_comparables_for_the_same_criteria(engine):
    for criteria in ({}, {"category": "any"}):
        found = registry.call("find_comparables", {"step_reference": SIGNED_2022, "as_of": SCORED_ON, **criteria},
                              registry.Context(engine=engine, viewer=ANA))

        assert estimate(engine, **criteria)["comparables"] == {
            "n": len(found["rows"]), "signed": found["counts"]["signed"], "still_open": found["counts"]["still_open"]}


def test_as_of_a_day_before_the_models_training_data_ended_it_gives_no_estimate(engine):
    """It names only the as-of date: the model whose training data ended later was not public that day."""
    result = estimate(engine, as_of=SCORED_ON - dt.timedelta(days=1))

    assert result["abstention"] == {"reason": "asof_before_training", "as_of": "2026-10-22"}
    assert result["rows"] == [] and result["estimate"] is None


def test_with_fewer_than_20_comparable_packages_it_gives_no_estimate_and_counts_them(engine):
    narrower = TRUTH["comparables"]

    result = estimate(engine, DEMO, review_type=narrower["narrower_review_type"])

    assert result["abstention"] == {"reason": "too_few_comparables", "count": narrower["narrower_count"],
                                    "min_comparables": 20}
    assert result["rows"] == [] and result["estimate"] is None and result["comparisons"] == []


def test_a_package_larger_than_any_the_model_learned_from_gets_no_estimate_and_says_which_feature(engine):
    result = estimate(engine, DEMO)

    assert result["abstention"]["reason"] == "outside_training"
    assert (result["abstention"]["feature"], result["abstention"]["value"]) == (
        "estimated_amount_usd", float(value("plan-541055-estimated")))
    assert result["estimate"] is None and result["plan_dates"] is None


@pytest.mark.parametrize("view", ["staff", "piu", "public"])
def test_it_answers_under_each_view_and_says_which_one(engine, view):
    result = estimate(engine, view=view)

    assert result["view"] == view
    assert result["estimate"] is not None


def test_without_an_as_of_date_it_answers_as_of_today(engine):
    result = estimate(engine, as_of=None)

    assert result["as_of"] == registry.today().isoformat()
    assert result["abstention"] is None


def test_a_package_planned_from_a_sentence_is_scored_on_the_request_as_the_batch_would_score_it(engine):
    """A package with no STEP row has no stored score, so the champion kept in strata.gold.time_estimate_model
    scores it on the request, with no XGBoost. That learner gives every stored package exactly the days the
    batch stored with XGBoost, so a score made on a request comes from the same model as a stored one."""
    from strata.config import load_time_estimate
    from strata.estimates import portable

    kept = portable.latest(engine, load_time_estimate().registered_model, SCORED_ON)
    stored = rows(engine, "SELECT step_reference, features_json, q25_days, q50_days, q75_days, q80_days "
                          "FROM strata.gold.time_estimate_score WHERE as_described AND abstention IS NULL")
    assert len(stored) > 0
    import json

    days = kept.model.days([json.loads(row["features_json"]) for row in stored])
    assert days == [{name: row[f"{name}_days"] for name in POINTS} for row in stored]

    result = registry.call("estimate_time", {
        "method": "Request for Bids", "category": "Works", "country": "KE", "described_amount_usd": 290_000,
        "described_market_approach": "Open - National", "described_review_type": "Post", "as_of": SCORED_ON},
        registry.Context(engine=engine, viewer=ANA))
    assert result["abstention"] is None
    assert result["comparables"]["n"] == TRUTH["past_range"]["comparables"]
    assert result["estimate"]["scored"] == "request"
    assert all(row["source"]["scored"] == "request" for row in result["rows"])


# ── What-ifs on fair levers only ─────────────────────────────────────────

def planned(engine, thresholds=None, **described):
    """estimate_time for a Kenya works package under Request for Bids that is not in a plan yet."""
    context = registry.Context(engine=engine, viewer=ANA, **({"thresholds": thresholds} if thresholds else {}))
    return registry.call("estimate_time", {"method": "Request for Bids", "category": "Works", "country": "KE",
                                           "as_of": SCORED_ON, **described}, context)


def test_no_what_if_ever_changes_review_type_even_when_lots_would_put_each_lot_under_the_threshold(engine):
    """A package described as Prior review, in six lots, as the sentence that asks for lots small enough to stay
    under prior review would have it (ticket 15's dividing case), stays Prior in every combination and every
    approach, because review type is computed from the whole package's estimated amount. No lever is review type."""
    result = planned(engine, described_amount_usd=290_000, described_lots=6, described_review_type="Prior",
                     described_market_approach="Open - National")

    assert len(result["rows"]) > 1
    assert {row["review_type"] for row in result["rows"]} == {"Prior"}
    assert result["options"]["review_type"] == "Prior"
    assert {comparison["lever"] for comparison in result["comparisons"]} <= {"market_approach", "lots", "prequalification"}
    from strata.config import load_what_if

    assert [lever.key for lever in load_what_if()] == ["market_approach", "lots", "prequalification"]


def test_a_lots_comparison_counts_the_comparable_packages_that_went_with_it_and_gives_no_estimate(engine):
    """The model reads no lots, so a lots comparison lights and counts the packages that went with the other
    value and gives no time estimate. Each of the 43 comparables in the awards dataset has one contract, the
    glossary's lot, so 43 of the 49 went with one lot; the other six are still open or signed only in an award
    notice, with no lots recorded."""
    comparables = TRUTH["comparables"]

    result = planned(engine, described_amount_usd=290_000, described_lots=3, described_market_approach="Open - National")

    [lots] = [comparison for comparison in result["comparisons"] if comparison["lever"] == "lots"]
    in_awards = comparables["signed"] - comparables["signed_only_in_award_notice"]
    assert (lots["value"], lots["own"], lots["k"], lots["n"]) == (1, 3, in_awards, TRUTH["past_range"]["comparables"])
    assert lots["rest"] == lots["n"] - lots["k"] and len(lots["matching_ids"]) == lots["k"]
    assert lots["estimate"] is None and lots["abstention"] == {"reason": "not_in_model", "lever": "lots"}


def test_a_market_approach_the_thresholds_rule_out_for_the_package_is_never_offered(engine, tmp_path):
    """A US$290,000 package described as open internationally is compared with the national approach its
    comparable packages went with, since the thresholds file leaves Kenya's works under US$15 million free; too
    few went with it for an estimate. With a thresholds file that sends Kenya's works of US$100,000 or more to
    international bidding, the same package is never compared with a national approach, which would
    contradict its own computed market approach (strata.packages.compute)."""
    from strata.config import load_thresholds

    text = (ROOT / "config" / "thresholds.toml").read_text()
    stricter = tmp_path / "thresholds.toml"
    stricter.write_text(text.replace("[market_approach.international_from_usd.KE]\nWorks = 15_000_000",
                                     "[market_approach.international_from_usd.KE]\nWorks = 100_000"))
    described = {"described_amount_usd": 290_000, "described_market_approach": "Open - International"}

    free = planned(engine, **described)
    ruled_out = planned(engine, thresholds=load_thresholds(stricter), **described)

    [national] = [comparison for comparison in free["comparisons"] if comparison["lever"] == "market_approach"]
    assert national["value"] == "Open - National"
    assert national["abstention"] == {"reason": "too_few_in_subgroup", "k": national["k"], "n": national["n"],
                                      "min_subgroup": 20}
    assert ruled_out["abstention"] is None
    assert [comparison for comparison in ruled_out["comparisons"] if comparison["lever"] == "market_approach"] == []
    assert all(approach["market_approach"] != "Open - National" for approach in ruled_out["options"]["approaches"])


def test_section_4_counts_the_whole_approaches_the_thresholds_rule_out_apart_from_those_never_recorded(engine):
    """Ana's rural roads package, about US$15 million in Kenya, as her sentence describes it (the package planned in
    tests/record_estimate_api.py). Three of its 49 comparable packages record their market approach, lots and
    qualification, all three Open - National, which the thresholds send to international bidding for a Kenya works
    package that large. Section 4 lists no approach, and the tool counts why: three ruled out, and the other 46
    record no whole approach, so the screen never says that none records one and never works out a count itself."""
    result = planned(engine, described_amount_usd=15_000_000, described_market_approach="Open - International",
                     described_review_type="Prior", described_prequalification="N", described_lots=2)

    options = result["options"]
    assert options["approaches"] == [] and options["count"] == 0
    assert options["n"] == TRUTH["past_range"]["comparables"]
    assert (options["recorded"], options["ruled_out"], options["unrecorded"]) == (3, 3, 46)


def test_section_4_rules_out_nothing_for_a_package_the_thresholds_leave_free(engine):
    """The demo package, US$1,230,000.00 in its plan, sits under Kenya's US$15 million line for works, so the same
    three whole approaches stand and none is ruled out."""
    options = estimate(engine, DEMO)["options"]

    assert (options["recorded"], options["ruled_out"], options["unrecorded"]) == (3, 0, 46)
    assert [(approach["market_approach"], approach["k"]) for approach in options["approaches"]] == [("Open - National", 3)]


def list_under(engine, references: list[str], market_approach: str) -> None:
    """A plan version public on October 1, 2026 that lists these packages under one market approach."""
    day = dt.date(2026, 10, 1)
    engine.insert_rows("strata.silver.plan_versions",
                       ("document_id", "project_id", "implementing_agency", "plan_date", "disclosed_on",
                        "series_order", "is_latest", "pdf_pages", "route_b_pages", "text_url", "pdf_url",
                        "public_from"),
                       [("990000001", "P156634", "Test agency", day, day, 99, True, 1, 1, "t", "p", day)])
    engine.insert_rows("strata.silver.plan_rows",
                       ("document_id", "project_id", "section", "activity_reference_no", "market_approach",
                        "pdf_page", "parser", "public_from"),
                       [("990000001", "P156634", "WORKS", reference, market_approach, 1, "test", day)
                        for reference in references])


def test_a_comparison_offers_only_a_value_the_nightly_batch_scores(fixture_db, tmp_path):
    """Limited - National is not among config/models.toml's [what_if] market approach values, so the batch never
    scores it. Even when 21 comparable packages went with it, it is not offered, since the screen could only say
    that the model never learned from it, which may be untrue."""
    import shutil

    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        found = registry.call("find_comparables", {"step_reference": SIGNED_2022, "as_of": SCORED_ON},
                              registry.Context(engine=engine, viewer=ANA))
        list_under(engine, sorted(row["step_reference"] for row in found["rows"])[:21], "Limited - National")
        result = estimate(engine)

    assert [comparison for comparison in result["comparisons"] if comparison["lever"] == "market_approach"] == []


@pytest.fixture
def went_international(fixture_db, tmp_path):
    """A copy of the fixture where a plan version public on October 1, 2026 lists 21 of KE-NWWDA-229129-CW-RFB's
    comparable packages under Open - International, and a later scoring run stored an estimate for that
    package with that approach."""
    import shutil

    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        found = registry.call("find_comparables", {"step_reference": SIGNED_2022, "as_of": SCORED_ON},
                              registry.Context(engine=engine, viewer=ANA))
        chosen = sorted(row["step_reference"] for row in found["rows"] if not row["still_open"])[:21]
        list_under(engine, chosen, "Open - International")
        later = dt.datetime(2026, 10, 23, 12, 0, tzinfo=dt.UTC)
        international = "market_approach = 'Open - International' AND prequalification IS NULL"
        points = {"q25": (200, 6.6), "q50": (300, 9.9), "q75": (400, 13.1), "q80": (450, 14.8)}
        replaced = ", ".join(
            f"CASE WHEN {international} THEN {days} ELSE {name}_days END AS {name}_days, "
            f"CASE WHEN {international} THEN {months} ELSE {name}_months END AS {name}_months"
            for name, (days, months) in points.items())
        engine.run("INSERT INTO strata.gold.time_estimate_score SELECT * REPLACE ("  # sql-lint: names only
                   f"'later' AS run_id, CAST(:later AS TIMESTAMP) AS scored_at, "
                   f"CASE WHEN {international} THEN NULL ELSE abstention END AS abstention, {replaced}) "
                   "FROM strata.gold.time_estimate_score WHERE step_reference = :reference AND run_id = 'fixture'",
                   {"later": later, "reference": SIGNED_2022})
        yield engine, chosen


def test_a_market_approach_comparison_counts_and_names_the_packages_that_went_with_it_and_takes_the_stored_estimate(
        went_international):
    engine, chosen = went_international

    result = estimate(engine)

    [international] = result["comparisons"]
    assert (international["lever"], international["value"], international["own"]) == (
        "market_approach", "Open - International", "Open - National")
    assert international["matching_ids"] == chosen
    assert (international["k"], international["rest"]) == (21, result["comparables"]["n"] - 21)
    assert international["abstention"] is None and international["estimate"]["q50"] == 9.9
    assert international["estimate"]["days"]["q50"] == 300


# ── The track record and the plan dates ──────────────────────────────────

def test_on_the_fixture_the_latest_test_year_has_too_few_unseen_packages_for_a_track_record(engine):
    result = estimate(engine)

    assert result["track_record"]["year"] == 2025
    assert result["track_record"]["abstention"]["reason"] == "too_few_unseen_packages"
    assert [year["year"] for year in result["test_years"]] == [2021, 2022, 2023, 2024, 2025]
    # The plan dates are the estimate's middle and 8-in-10 point; with no track record, no "in 10" words.
    plan_dates = result["plan_dates"]
    assert (plan_dates["middle"]["months"], plan_dates["eight_in_ten"]["months"]) == (
        result["estimate"]["q50"], result["estimate"]["q80"])
    assert plan_dates["default"] == "eight_in_ten"
    assert plan_dates["middle"]["in10"] is None and plan_dates["eight_in_ten"]["in10"] is None


def test_the_track_record_and_the_plan_dates_ran_longer_counts_come_from_the_latest_backtest_public_then(
        fixture_db, tmp_path):
    """A later backtest run, stored as the replay harness stores one, gives the track record and the plan dates'
    counts; as of a day before it was public, the fixture's own run still answers."""
    import shutil

    from strata.estimates import backtest, harness

    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    ran_at = dt.datetime(2026, 10, 30, 6, 0, tzinfo=dt.UTC)
    measures = {"n": 40, "m": 31, "expected": 32, "misses_early": 0, "misses_late": 9, "middle_ran_longer": 21,
                "middle_total": 40, "middle_in10": 5, "eight_in_ten_ran_longer": 9, "eight_in_ten_total": 40,
                "eight_in_ten_in10": 2, "error_estimate_months": 2.1, "error_past_range_months": 2.6,
                "error_plan_months": 3.4}
    scorer = backtest.TimeEstimateBacktest(backtest.load_time_estimate())
    window = harness.Window(dt.date(2025, 1, 1), dt.date(2026, 10, 30), "test_year", "2025")
    with DuckDBEngine.open(target) as engine:
        harness.write(engine, [harness.row("later-run", scorer, window, harness.Score(name, value), "mlflow-later", ran_at)
                               for name, value in measures.items()])
        later = estimate(engine, as_of=dt.date(2026, 10, 30))
        before = estimate(engine, as_of=dt.date(2026, 10, 29))

    assert {key: later["track_record"][key] for key in ("year", "n", "m", "expected", "misses", "misses_early",
                                                        "misses_late", "mlflow_run_id", "abstention")} == {
        "year": 2025, "n": 40, "m": 31, "expected": 32, "misses": 9, "misses_early": 0, "misses_late": 9,
        "mlflow_run_id": "mlflow-later", "abstention": None}
    assert later["plan_dates"]["middle"] == {"months": later["estimate"]["q50"], "ran_longer": 21, "total": 40, "in10": 5}
    assert later["plan_dates"]["eight_in_ten"] == {"months": later["estimate"]["q80"], "ran_longer": 9, "total": 40,
                                                   "in10": 2}
    assert [year["year"] for year in later["test_years"]] == [2025]
    assert later["test_years"][0]["error_past_range_months"] == 2.6
    assert before["track_record"]["abstention"]["reason"] == "too_few_unseen_packages"


class NoOpsGrant:
    """The fixture as a viewer sees it who cannot read strata.ops: every statement on it fails as the warehouse
    would refuse it."""

    def __init__(self, engine):
        self.engine = engine

    def run(self, sql, params=None):
        from strata.lakehouse.engine import EngineError

        if "strata.ops." in sql:
            raise EngineError("PERMISSION_DENIED: User does not have SELECT on schema strata.ops.")
        return self.engine.run(sql, params)

    def __getattr__(self, name):
        return getattr(self.engine, name)


def test_a_viewer_who_cannot_read_strata_ops_still_gets_the_time_estimate_and_the_step_dates(engine):
    result = registry.call("estimate_time", {"step_reference": SIGNED_2022, "as_of": SCORED_ON},
                           registry.Context(engine=NoOpsGrant(engine), viewer=ANA))

    assert result["abstention"] is None and result["estimate"] is not None
    assert result["track_record"] is None and result["test_years"] == []
    assert result["step_dates"] is not None


# ── Why the lanes differ ─────────────────────────────────────────────────

def test_the_package_size_is_the_reason_only_when_the_models_own_middle_moves_with_it(fixture_db, tmp_path):
    """The fixture's champion never splits on the estimated amount, so on the fixture no reason is given. A champion
    that learned that packages of US$3 million took 300 days and those of US$200,000 took 100 names the size of a
    US$3 million package as why its middle is later than the past range's: with the comparable packages' middle
    signed amount in its place, its own middle falls by more than half the gap. The counts are of the comparable
    packages whose signed contracts add up to less than US$3 million, out of all of them."""
    import shutil

    from strata.config import load_thresholds, load_time_estimate
    from strata.estimates import portable
    from strata.estimates.time_estimate import Package, fit

    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        assert planned(engine, described_amount_usd=290_000)["difference"]["reasons"] == []
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    features = {"method": "Request for Bids", "category": "Works", "market_approach": "Open - National",
                "review_type": "Post", "prequalification": None, "country_code": "KE",
                "region": "Eastern and Southern Africa", "planned_days": None, "agency_packages": None,
                "agency_median_days": None}
    training = [Package(f"KE-SIZE-{i}-CW-RFB", SCORED_ON, SCORED_ON - dt.timedelta(days=400 - i), True,
                        {**features, "estimated_amount_usd": 3_000_000.0 if i % 2 else 200_000.0},
                        300 if i % 2 else 100, True) for i in range(160)]
    model = fit(training, load_time_estimate(), load_thresholds(), training_through=SCORED_ON)
    with DuckDBEngine.open(target) as engine:
        portable.keep(engine, "strata.gold.time_estimate", 2, "champion", model, None,
                      dt.datetime(2026, 10, 23, 12, 0, tzinfo=dt.UTC))
        result = planned(engine, described_amount_usd=3_000_000)
        found = registry.call("find_comparables", {"method": "Request for Bids", "category": "Works", "country": "KE",
                                                   "as_of": SCORED_ON}, registry.Context(engine=engine, viewer=ANA))
        signed = {row[0]: float(row[1]) for row in engine.run(
            "SELECT step_reference, sum(contract_amount_usd) FROM strata.gold.contract "
            "WHERE source <> 'notices' GROUP BY step_reference", {}).rows}

    smaller = sum(1 for row in found["rows"] if signed.get(row["step_reference"], 3_000_000.0) < 3_000_000.0)
    assert result["difference"]["direction"] == "later"
    assert result["difference"]["reasons"] == [{"code": "size_larger", "k": smaller, "n": len(found["rows"])}]
