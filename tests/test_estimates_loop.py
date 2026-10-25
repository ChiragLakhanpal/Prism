"""The estimates loop (ticket 44; docs/PLAN.md section 11) at seam 1: the monthly watch reads the exposure log, the
plan rows and the packages, and writes to strata.ops the plan rows dated within 14 days of a date Strata offered,
plan accuracy and duration by group, rolling coverage, and the retrains it raised.

Every planned and actual date comes from tests/ground_truth/values.toml, with where it was read. The fixture's
plans are all Kenya's, so a test that needs countries using Strata names Kenya in its own slice.
"""

import dataclasses
import datetime as dt
import json
import shutil
import tomllib
from pathlib import Path

import pytest

from strata.config import Onboarded, load_slice, load_thresholds
from strata.estimates import exposures, watch
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
LIMITS = load_thresholds()
WITHIN = dt.timedelta(days=LIMITS.value("estimates_loop.anchored_within_days"))
DAY = dt.timedelta(days=1)
DEMO, SIGNED_2022 = "KE-NWWDA-541055-CW-RFB", "KE-NWWDA-229129-CW-RFB"
# The October 9, 2026 plan's row for KE-NWWDA-541055-CW-RFB: its last two dates are the Signed Contract Planned date
# (April 24, 2026) and the Contract Completion Planned date (values.toml plan-541055-no-signed-contract, page 3).
DEMO_PLAN = VALUES["plan-541055-no-signed-contract"]
DEMO_PLANNED = dt.date.fromisoformat(DEMO_PLAN["quote"].split()[-2])
DEMO_SIGNED = VALUES["award-541055-signed"]["value"]
# The April 21, 2021 plan, the first to list KE-NWWDA-229129-CW-RFB, planned its signing for July 1, 2021.
FIRST_PLAN = VALUES["plan-229129-first-planned-signing"]
SIGNED_2022_PLANNED = FIRST_PLAN["value"]
WATCHED = dt.date(2026, 10, 31)  # the month after the fixture's newest plan, of October 9, 2026
RAN_AT = dt.datetime(2026, 11, 1, 6, tzinfo=dt.UTC)


def offered(step_reference: str, shown_on: dt.date, eight_in_ten_on: dt.date) -> tuple:
    """An exposure in the staff view, made on shown_on, whose 8-in-10 point fell on eight_in_ten_on."""
    row = {column: None for column in exposures.COLUMNS}
    row.update(exposure_id=f"exposure-{step_reference}", shown_at=dt.datetime.combine(shown_on, dt.time(12), dt.UTC),
               exposed_on=shown_on, viewer_id="4021@1984", view="staff", route="/api/packages/{step_reference}/estimate",
               as_of=shown_on, step_reference=step_reference, project_id="P156634", country_code="KE",
               shown="time_estimate", range_shown="{}", option_chosen="eight_in_ten", option_saved=False,
               offered_eight_in_ten_on=eight_in_ten_on, public_from=shown_on)
    return tuple(row[column] for column in exposures.COLUMNS)


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, values)) for values in result.rows]


@pytest.fixture(scope="module")
def watched(fixture_db, tmp_path_factory):
    """A copy of the fixture with two exposures, watched once as of October 31, 2026, with Kenya using Strata from
    January 1, 2026. The day before each plan was published, Strata offered KE-NWWDA-541055-CW-RFB a date exactly
    14 days after the planned signing date the plan then gave, and KE-NWWDA-229129-CW-RFB one 15 days after."""
    path = tmp_path_factory.mktemp("estimates-loop") / "fixture.duckdb"
    shutil.copy(fixture_db, path)
    chosen = dataclasses.replace(load_slice(), onboarded=(Onboarded("KE", dt.date(2026, 1, 1)),))
    with DuckDBEngine.open(path) as engine:
        engine.insert_rows(exposures.TABLE, exposures.COLUMNS, [
            offered(DEMO, DEMO_PLAN["date"] - DAY, DEMO_PLANNED + WITHIN),
            offered(SIGNED_2022, FIRST_PLAN["date"] - DAY, SIGNED_2022_PLANNED + WITHIN + DAY)])
        watch.measure(engine, WATCHED, "watch-1", RAN_AT, chosen=chosen)
    return path


def test_of_two_plan_rows_the_one_within_14_days_of_a_date_offered_is_marked_and_the_other_is_not(watched):
    with DuckDBEngine.open(watched, read_only=True) as engine:
        marked = {(row["step_reference"], row["published_on"]): row for row in rows(
            engine, "SELECT * FROM strata.ops.anchored_plan_rows WHERE run_id = :run_id", run_id="watch-1")}

    demo, first = marked[(DEMO, DEMO_PLAN["date"])], marked[(SIGNED_2022, FIRST_PLAN["date"])]
    assert (demo["planned_signing_on"], demo["days_from_offered"], demo["anchored"]) == (DEMO_PLANNED, 14, True)
    assert (first["planned_signing_on"], first["days_from_offered"], first["anchored"]) == (SIGNED_2022_PLANNED, 15, False)
    # The actual signing dates come from the package's records, never a plan's Actual column.
    assert demo["days_from_plan"] == (DEMO_SIGNED - DEMO_PLANNED).days
    assert first["days_from_plan"] == VALUES["plan-229129-days-late"]["value"]
    # Only rows published after an exposure of their package are marked at all: the March 5, 2026 plan's row for
    # KE-NWWDA-541055-CW-RFB came before Strata showed its range.
    assert all(row["published_on"] > row["exposed_on"] for row in marked.values())
    assert (DEMO, VALUES["plan-541055-estimated-2026-03-05"]["date"]) not in marked


def test_plan_accuracy_and_duration_are_reported_for_each_group_and_each_kind_of_country(watched):
    with DuckDBEngine.open(watched, read_only=True) as engine:
        found = {(row["measure"], row["segment"]): row for row in rows(
            engine, "SELECT * FROM strata.ops.estimates_watch WHERE run_id = :run_id", run_id="watch-1")}
        every_row = rows(engine, "SELECT count(*) AS n FROM strata.silver.plan_steps "
                                 "WHERE step = 'Signed Contract' AND planned_on IS NOT NULL")[0]["n"]

    segments = [f"{group}/{country}" for group in ("anchored", "other") for country in ("using_strata", "not_yet")]
    for measure in ("plan_accuracy", "plan_duration"):
        assert {segment for kind, segment in found if kind == measure} == set(segments)
        # Every plan row falls in exactly one of the four groups.
        assert sum(found[(measure, segment)]["denominator"] for segment in segments) == every_row
    # One row was dated within 14 days of a date offered: the October 9, 2026 plan's row for KE-NWWDA-541055-CW-RFB,
    # published after Kenya started using Strata. Its package signed on June 22, 2026, so it has an actual date, and
    # one row is too few for a median: only the counts are kept.
    anchored = found[("plan_accuracy", "anchored/using_strata")]
    assert (anchored["count"], anchored["denominator"], anchored["value"], anchored["reason"]) == (1, 1, None, "too_few_cases")
    assert found[("plan_accuracy", "anchored/not_yet")]["denominator"] == 0
    # Of the rows published after an exposure, one of five was dated within 14 days of a date offered: the
    # KE-NWWDA-229129-CW-RFB rows of the four plans from April 21, 2021 on were 15 days away.
    assert (found[("anchored_rows", "all")]["count"], found[("anchored_rows", "all")]["denominator"]) == (1, 5)
    assert all(row["count"] <= row["denominator"] for row in found.values())


# ── The retrain triggers, each on a seeded series ────────────────────────

SEP, OCT = dt.date(2026, 9, 30), dt.date(2026, 10, 31)
TRAINED_THROUGH = dt.date(2026, 1, 1)
MODEL = "strata.gold.time_estimate"  # config/models.toml's registered_model


def at(month: dt.date) -> dt.datetime:
    """When the watch of a month runs: early on the first day of the next month."""
    return dt.datetime.combine(month + DAY, dt.time(6), dt.UTC)


@pytest.fixture(scope="module")
def empty_catalog(tmp_path_factory):
    """Every table the catalog defines, empty, built once for the seeded series."""
    from strata.lakehouse import catalog

    path = tmp_path_factory.mktemp("empty-catalog") / "empty.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


@pytest.fixture
def seeded(empty_catalog, tmp_path):
    """A copy of the empty catalog with the champion the watch compares against, trained through January 1, 2026."""
    path = tmp_path / "seeded.duckdb"
    shutil.copy(empty_catalog, path)
    with DuckDBEngine.open(path) as engine:
        insert(engine, "strata.gold.time_estimate_model", [{
            "model": MODEL, "version": 1, "alias": "champion", "training_through": TRAINED_THROUGH,
            "booster_json": "{}", "state_json": "{}", "mlflow_run_id": "offline-run-0001",
            "registered_at": dt.datetime(2026, 1, 2, tzinfo=dt.UTC), "public_from": dt.date(2026, 1, 2)}])
    return path


def insert(engine, table, items):
    columns = tuple(items[0])
    engine.insert_rows(table, columns, [tuple(item[column] for column in columns) for item in items])


def package(reference, notice_on, signed_on=None, category="Works", method="Request for Bids", review="Prior"):
    return {"step_reference": reference, "project_id": "P900044", "country_code": "KE", "procurement_category": category,
            "procurement_method": method, "first_notice_date": notice_on, "contract_signed_on": signed_on,
            "contract_count": 1 if signed_on else 0, "review_type": review, "public_from": notice_on}


def score(reference, scored_on, q50_days, q80_days):
    return {"step_reference": reference, "run_id": f"score-{scored_on}", "as_described": True, "q50_days": q50_days,
            "q80_days": q80_days, "model": MODEL, "model_version": 1, "model_alias": "champion",
            "training_through": TRAINED_THROUGH, "scored_at": dt.datetime.combine(scored_on, dt.time(9), dt.UTC),
            "public_from": scored_on}


def triggers(engine) -> list[tuple]:
    return [(row["month"], row["reason"]) for row in rows(
        engine, "SELECT month, reason FROM strata.ops.retrain_triggers ORDER BY month, reason")]


def test_coverage_outside_75_to_85_percent_for_two_months_in_a_row_raises_a_retrain(seeded):
    # Twenty packages advertised in December 2025 each signed 100 days later. Before each notice I gave ten of them an
    # 8-in-10 point of 120 days, which they finished inside, and ten one of 80 days, which they ran past: 10 of 20.
    with DuckDBEngine.open(seeded) as engine:
        notices = [dt.date(2025, 12, 1) + n * DAY for n in range(20)]
        insert(engine, "strata.gold.package", [package(f"KE-W-{n}", day, day + 100 * DAY) for n, day in enumerate(notices)])
        insert(engine, "strata.gold.time_estimate_score", [score(f"KE-W-{n}", dt.date(2025, 11, 15), 60, 120 if n < 10 else 80)
                                                           for n in range(20)])
        watch.watch_month(engine, SEP, "watch-sep", at(SEP))
        after_one = triggers(engine)
        watch.watch_month(engine, OCT, "watch-oct", at(OCT))
        coverage = rows(engine, "SELECT month, count, denominator, value FROM strata.ops.estimates_watch "
                                "WHERE measure = 'coverage' ORDER BY month")
        assert triggers(engine) == [(OCT, "coverage_outside")]
    assert after_one == []
    assert [(row["count"], row["denominator"], row["value"]) for row in coverage] == [(10, 20, None), (10, 20, None)]


def test_the_nightly_watch_measures_each_month_once_and_catches_up_on_months_it_missed(seeded):
    with DuckDBEngine.open(seeded) as engine:
        watch.run(engine, "nightly-1", at(SEP))  # the first night watches only the last whole month
        watch.run(engine, "nightly-2", at(SEP) + DAY)  # a rerun the next day watches nothing again
        watch.run(engine, "nightly-3", at(dt.date(2026, 12, 31)))  # after two months off, both are watched
        watched_months = rows(engine, "SELECT month, run_id FROM strata.ops.estimates_watch "
                                      "WHERE measure = 'coverage' ORDER BY month")
    assert [(row["month"], row["run_id"]) for row in watched_months] == [
        (SEP, "nightly-1"), (OCT, "nightly-3"), (dt.date(2026, 11, 30), "nightly-3"), (dt.date(2026, 12, 31), "nightly-3")]


def test_a_retrain_is_due_each_quarter_and_after_a_raised_trigger(seeded):
    with DuckDBEngine.open(seeded) as engine:
        # The champion was registered on January 2, 2026.
        in_march = watch.retrain_due(engine, dt.date(2026, 3, 31))
        in_april = watch.retrain_due(engine, dt.date(2026, 4, 2))
        seed_errors(engine, SEP, "watch-sep", 3.4, 3.0)
        insert(engine, "strata.gold.time_estimate_model", [{
            "model": MODEL, "version": 2, "alias": "challenger", "training_through": dt.date(2026, 9, 1),
            "booster_json": "{}", "state_json": "{}", "mlflow_run_id": None,
            "registered_at": dt.datetime(2026, 9, 1, tzinfo=dt.UTC), "public_from": dt.date(2026, 9, 1)}])
        after_the_retrain = watch.retrain_due(engine, dt.date(2026, 9, 30))
        watch.decide(engine, SEP, "watch-sep", at(SEP))
        after_a_trigger = watch.retrain_due(engine, at(SEP).date())
    assert (in_march, in_april, after_the_retrain, after_a_trigger) == (None, "quarterly", None, "trigger")


def test_coverage_under_20_finished_packages_raises_nothing(seeded):
    with DuckDBEngine.open(seeded) as engine:
        notices = [dt.date(2025, 12, 1) + n * DAY for n in range(19)]
        insert(engine, "strata.gold.package", [package(f"KE-W-{n}", day, day + 100 * DAY) for n, day in enumerate(notices)])
        insert(engine, "strata.gold.time_estimate_score", [score(f"KE-W-{n}", dt.date(2025, 11, 15), 60, 80)
                                                           for n in range(19)])
        for month, run_id in ((SEP, "watch-sep"), (OCT, "watch-oct")):
            watch.watch_month(engine, month, run_id, at(month))
        reasons = rows(engine, "SELECT DISTINCT reason FROM strata.ops.estimates_watch WHERE measure = 'coverage'")
        assert triggers(engine) == []
    assert reasons == [{"reason": "too_few_cases"}]


def seed_errors(engine, month, run_id, estimate_months, past_range_months, cases=20):
    """The two typical errors a watch measured in a month, as its measure step stores them."""
    insert(engine, watch.WATCH_TABLE, [
        {"run_id": run_id, "month": month, "measure": measure, "segment": "all", "count": cases, "denominator": cases,
         "value": value, "detail": None, "reason": None, "measured_at": at(month), "public_from": at(month).date()}
        for measure, value in (("error_estimate", estimate_months), ("error_past_range", past_range_months))])


def test_an_error_more_than_10_percent_behind_the_past_range_raises_a_retrain_and_10_percent_does_not(seeded):
    with DuckDBEngine.open(seeded) as engine:
        seed_errors(engine, SEP, "watch-sep", 3.3, 3.0)  # 10 percent behind: not more than 10 percent
        seed_errors(engine, OCT, "watch-oct", 3.4, 3.0)
        watch.decide(engine, SEP, "watch-sep", at(SEP))
        watch.decide(engine, OCT, "watch-oct", at(OCT))
        detail = json.loads(rows(engine, "SELECT detail FROM strata.ops.retrain_triggers")[0]["detail"])
        assert triggers(engine) == [(OCT, "error_trails_past_range")]
    assert detail == {"error_estimate_months": 3.4, "error_past_range_months": 3.0, "packages": 20}


def test_a_drifting_input_mix_raises_a_retrain_with_the_statistics_an_independent_library_gave(seeded):
    # The champion learned from 100 packages advertised before January 1, 2026; 25 were advertised in October 2026.
    # Their categories differ: 60, 30 and 10 against 5, 10 and 10. Their methods are in the same proportion, and their
    # review types nearly so. The statistics and p-values are scipy.stats.chi2_contingency's (correction=False) on
    # these tables, computed once and kept as literals.
    learned = ([("Works", "Request for Bids", "Prior")] * 50 + [("Works", "Request for Bids", "Post")] * 10
               + [("Goods", "Request for Bids", "Post")] * 20 + [("Goods", "Request for Quotations", "Post")] * 10
               + [("Consultant Services", "Request for Quotations", "Post")] * 10)
    october = ([("Works", "Request for Bids", "Prior")] * 5 + [("Goods", "Request for Bids", "Prior")] * 7
               + [("Goods", "Request for Bids", "Post")] * 3 + [("Consultant Services", "Request for Bids", "Post")] * 5
               + [("Consultant Services", "Request for Quotations", "Post")] * 5)
    with DuckDBEngine.open(seeded) as engine:
        insert(engine, "strata.gold.package",
               [package(f"KE-L-{n}", dt.date(2025, 6, 1) + n * DAY, None, *values) for n, values in enumerate(learned)]
               + [package(f"KE-O-{n}", dt.date(2026, 10, 1) + n * DAY, None, *values) for n, values in enumerate(october)])
        watch.watch_month(engine, OCT, "watch-oct", at(OCT))
        mix = {row["segment"]: row for row in rows(engine, "SELECT * FROM strata.ops.estimates_watch "
                                                           "WHERE measure = 'input_mix'")}
        assert triggers(engine) == [(OCT, "input_mix_drift")]
    category, method, review = (mix[name] for name in ("procurement_category", "procurement_method", "review_type"))
    assert (category["count"], category["denominator"]) == (25, 100)
    assert category["value"] == pytest.approx(18.028846153846153, rel=1e-9)
    assert json.loads(category["detail"])["p_value"] == pytest.approx(0.0001216426296701689, rel=1e-6)
    assert json.loads(category["detail"])["degrees_of_freedom"] == 2
    assert method["value"] == pytest.approx(0.0) and json.loads(method["detail"])["p_value"] == pytest.approx(1.0)
    assert review["value"] == pytest.approx(0.03200204813108039, rel=1e-9)
    assert json.loads(review["detail"])["p_value"] == pytest.approx(0.8580231619125281, rel=1e-6)


def lesson(lesson_id, edition_key, state="current", version=1):
    """One version of a lesson in the library, as a lead's decision writes it (ticket 29)."""
    return {"lesson_id": lesson_id, "version": version, "statement": f"{lesson_id} helped.", "risk_factors": "[]",
            "stage": "planning", "kind": "helped", "edition_key": edition_key, "project_id": "P900044", "state": state,
            "change_kind": "added", "reason": "Two reports say so.", "item_id": f"new-{lesson_id}",
            "decided_on": dt.date(2026, 3, 2), "decided_by": "lead.example@worldbank.org", "decided_by_name": "Lead",
            "recommended_by": "aps.example@worldbank.org", "recommended_by_name": "Specialist",
            "recommended_reason": "Quoted on its page.", "public_from": dt.date(2026, 3, 2)}


def test_a_new_edition_taking_effect_marks_lessons_and_the_model_as_being_re_checked_then_raises_a_retrain(seeded):
    from strata.config import Edition, Editions, load_editions
    from strata.knowledge.lessons.review import ITEM_COLUMNS

    old = load_editions().editions[0]
    # An edition that takes effect on October 15, 2026, in the watched month. The tests make it up; the real next
    # edition joins config/editions.toml with its effective_from when it is issued.
    new = Edition("regulations_test", "the Procurement Regulations, a test edition", ("Test edition",),
                  "Procurement Regulations, test edition", effective_from=dt.date(2026, 10, 15))
    with DuckDBEngine.open(seeded) as engine:
        insert(engine, "strata.gold.project", [{"project_id": "P900044", "project_name": "Hand-made project",
                                                 "country_code": "KE", "region": "Eastern and Southern Africa",
                                                 "public_from": dt.date(2015, 1, 1)}])
        insert(engine, "strata.ops.lesson_versions", [
            lesson("lesson-old", old.key), lesson("lesson-untagged", None), lesson("lesson-new", new.key),
            lesson("lesson-retired", old.key), {**lesson("lesson-retired", old.key, "retired_outdated", 2),
                                                 "change_kind": "retired"},
            lesson("lesson-open", old.key)])
        # lesson-open already has a re-check a reviewer asked for, which the edition does not repeat.
        open_item = {"item_id": "recheck-open", "kind": "recheck", "proposal_id": None, "lesson_id": "lesson-open",
                     "version": 1, "decided_item_id": None, "project_id": "P900044",
                     "region": "Eastern and Southern Africa", "decided_region": None, "origin": "asked",
                     "origin_by": "lead.example@worldbank.org", "origin_by_name": "Lead", "origin_reason": "Unclear.",
                     "origin_item_id": None, "entered_on": dt.date(2026, 10, 1), "due_on": None,
                     "created_at": dt.datetime(2026, 10, 1, tzinfo=dt.UTC), "public_from": dt.date(2026, 10, 1)}
        engine.insert_rows("strata.ops.lesson_review_items", ITEM_COLUMNS, [tuple(open_item[c] for c in ITEM_COLUMNS)])

        watch.decide(engine, SEP, "watch-sep", at(SEP), editions=Editions((old, new)))
        watch.decide(engine, OCT, "watch-oct", at(OCT), editions=Editions((old, new)))
        items = rows(engine, "SELECT * FROM strata.ops.lesson_review_items WHERE origin = 'edition' ORDER BY lesson_id")
        states = rows(engine, "SELECT model, version, state, reason, edition_key FROM strata.ops.model_states")
        raised = rows(engine, "SELECT month, reason, edition_key FROM strata.ops.retrain_triggers")

    assert [(item["lesson_id"], item["kind"], item["version"], item["region"], item["entered_on"]) for item in items] == [
        ("lesson-old", "recheck", 1, "Eastern and Southern Africa", at(OCT).date()),
        ("lesson-untagged", "recheck", 1, "Eastern and Southern Africa", at(OCT).date())]
    assert all(item["origin_reason"] == new.key for item in items)
    assert states == [{"model": MODEL, "version": 1, "state": "rechecking", "reason": "new_edition",
                       "edition_key": new.key}]
    assert raised == [{"month": OCT, "reason": "new_edition", "edition_key": new.key}]
