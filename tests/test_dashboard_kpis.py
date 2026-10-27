"""Every tile's number against its defining query (ticket 45, the first criterion), on a made-up month of
operations (tests/dashboard_seed.py).

Each counter shows its KPI's display string, from the KPI's one defining query (config/kpis.toml); each table and
chart shows its dataset's columns. Here every query runs on DuckDB as the dashboard file holds it, and its numbers
are compared with the counts worked out by hand from the seed. The seam is the dashboard's own queries over
strata.ops and strata.gold, which the gate also checks against the file (tests/test_dashboard_pages.py).
"""

import datetime as dt
import json

import pytest

from dashboard_seed import COSTS, TODAY, at, rows, seeded
from strata.config import Budget, load_budget
from strata.lakehouse import catalog, costs
from strata.lakehouse.engine import DuckDBEngine


@pytest.fixture(scope="module")
def engine():
    seeded_engine = seeded()
    yield seeded_engine
    seeded_engine.close()


@pytest.fixture(scope="module")
def empty():
    with DuckDBEngine.open() as found:
        catalog.build(found)
        yield found


def display(engine, kpi, **params):
    [row] = rows(engine, f"kpi_{kpi}", **params)
    return row["display"]


# ── The counters ─────────────────────────────────────────────────────────

def test_each_counter_shows_its_count_with_its_denominator_from_its_defining_query(engine):
    october_22 = {"date_from": dt.date(2026, 10, 22), "date_to": dt.date(2026, 10, 22)}

    assert display(engine, "checks_failed", **october_22) == "1 of 4"  # the duplicates check failed
    assert display(engine, "checks_failed") == "0 of 3"  # October 23's run, which stopped after two tasks
    assert display(engine, "azure_spend") == "US$8 of US$197"  # 7.80 in the free credit, in whole dollars
    assert display(engine, "contacts_left") == "0 of 251"
    assert display(engine, "benchmark_passed") == "45 of 52"  # the full gate of October 20
    assert display(engine, "sentences_removed") == "3 of 20"
    assert display(engine, "answers_held_back") == "2 of 3"  # run-a and run-c held back; run-b's upload did not
    assert display(engine, "weekly_users") == "2"  # u1 and u2 opened pages; u3 only called the API
    assert display(engine, "drafts_exported") == "1 of 3"
    assert display(engine, "plan_rows_offered") == "4 of 9"


def test_before_anything_happened_each_counter_says_none_yet_and_weekly_users_says_zero(empty):
    for kpi in ("checks_failed", "contacts_left", "benchmark_passed", "sentences_removed", "answers_held_back",
                "drafts_exported", "plan_rows_offered"):
        assert display(empty, kpi) == "None yet", kpi
    assert display(empty, "azure_spend") == "No cost data yet"
    assert display(empty, "weekly_users") == "0"


def test_a_counter_returns_one_row_whatever_the_dates(engine):
    nothing = {"date_from": dt.date(2020, 1, 1), "date_to": dt.date(2020, 1, 31)}
    for kpi in ("checks_failed", "contacts_left", "benchmark_passed", "sentences_removed", "answers_held_back",
                "weekly_users", "drafts_exported", "plan_rows_offered", "azure_spend"):
        assert len(rows(engine, f"kpi_{kpi}", **nothing)) == 1, kpi


# ── Governance ───────────────────────────────────────────────────────────

def test_the_nightly_runs_table_names_how_each_run_ended(engine):
    found = rows(engine, "nightly_runs")

    assert [(row["night"], row["outcome"], row["tasks_finished"], row["checks_passed"], row["checks_failed"])
            for row in found] == [
        (TODAY, "Stopped at Read and index new documents", "2 of 10", 3, 0),
        (dt.date(2026, 10, 22), "Rerun, finished", "10 of 10", 3, 1),
        (dt.date(2026, 10, 21), "Finished", "10 of 10", 3, 0)]
    assert found[2]["minutes"] == 30  # ten tasks three minutes apart, the last finishing three minutes after it began


def test_the_checks_chart_stacks_failures_at_the_base_of_each_night(engine):
    assert [(row["night"], row["result"], row["checks"]) for row in rows(engine, "nightly_checks")] == [
        (dt.date(2026, 10, 21), "Passed", 3), (dt.date(2026, 10, 22), "Failed", 1),
        (dt.date(2026, 10, 22), "Passed", 3), (TODAY, "Passed", 3)]


def test_a_failed_check_says_what_it_found_in_words(engine):
    [failed] = rows(engine, "failed_checks")

    assert (failed["task"], failed["check_name"], failed["found"]) == (
        "Clean and model the records", "Duplicate rows", "3 duplicate rows in strata.gold.contract")


def test_azure_spend_is_a_running_total_against_a_flat_budget_by_day_and_by_service(engine):
    days = rows(engine, "spend_by_day")

    assert [(row["charged_on"], row["spent_that_day"], row["spent_so_far"], row["budget_usd"]) for row in days] == [
        (dt.date(2026, 10, 20), 1.35, 1.35, 197.0), (dt.date(2026, 10, 21), 2.62, 3.97, 197.0),
        (dt.date(2026, 10, 22), 3.83, 7.8, 197.0)]
    assert [(row["service"], row["spent"]) for row in rows(engine, "spend_by_service")] == [
        ("Azure OpenAI", 7.5), ("Application Insights", 0.3)]
    assert [(row["resource"], row["spent"]) for row in rows(engine, "spend_by_resource")] == [
        ("wb-strata", 7.5), ("wb-strata-insights", 0.3)]
    assert [row["label"] for row in rows(engine, "budget_periods")] == ["Free credit, to Nov 10, 2026"]


def test_a_later_pull_of_the_same_day_replaces_that_day_s_charges_on_the_page():
    """Azure revises recent days, so each day comes from the newest pull that holds it."""
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        answer = json.loads(COSTS.read_text())
        costs.pull(engine, costs.RecordedCosts(answer), "pull-1", lambda: at(TODAY, 6))
        revised = json.loads(COSTS.read_text())
        revised["properties"]["rows"] = [row for row in revised["properties"]["rows"] if row[1] == 20261022]
        revised["properties"]["rows"][0][0] = 4.0  # Azure OpenAI on October 22, revised from 3.75
        costs.pull(engine, costs.RecordedCosts(revised), "pull-2", lambda: at(TODAY, 7))

        assert [row["spent_so_far"] for row in rows(engine, "spend_by_day")] == [1.35, 3.97, 8.05]


def test_contact_details_removed_are_counted_by_kind_and_by_the_notices_they_came_from(engine):
    assert [(row["kind"], row["removed"], row["notices"], row["last_removed"])
            for row in rows(engine, "contact_removals")] == [
        ("Contact names", 2, 2, dt.date(2026, 10, 20)), ("Email addresses", 6, 4, dt.date(2026, 10, 21)),
        ("Phone numbers", 4, 2, dt.date(2026, 10, 20))]


def test_the_recent_runs_list_every_answer_in_the_dates_newest_first(engine):
    assert [(row["run_id"], row["view"], row["tool_calls"], row["sentences_removed"])
            for row in rows(engine, "recent_runs")] == [
        ("run-c", "World Bank staff", 1, 0), ("run-b", "World Bank staff", 1, 2), ("run-a", "World Bank staff", 2, 1)]


def test_lineage_shows_the_latest_answer_run_when_run_id_is_empty(engine):
    [run] = rows(engine, "lineage_run")
    reads = rows(engine, "lineage_reads")

    assert (run["run_id"], run["tool_calls"], run["sentences_kept"]) == ("run-c", 1, 6)
    assert [(row["call"], row["table_name"]) for row in reads] == [("1. estimate_time", "strata.gold.package")]
    # No check names strata.gold.package, so it is the newest night whose checks ran before the call: October 22's
    # run checked its tables at 07:06, before run-c's call at 14:00.
    assert reads[0]["written_by"] == dt.date(2026, 10, 22)


def test_a_run_that_read_a_private_upload_shows_neither_its_question_nor_the_upload(engine):
    [run] = rows(engine, "lineage_run", run_id="run-b")
    [call] = rows(engine, "lineage_calls", run_id="run-b")

    assert run["question"] == "Not shown, because this run read a private upload."
    assert call["inputs"] == "upload_id: a private upload"


def test_a_run_id_that_matches_nothing_leaves_the_lineage_tables_empty(engine):
    for name in ("lineage_run", "lineage_calls", "lineage_reads"):
        assert rows(engine, name, run_id="run-that-never-was") == [], name


# ── AI quality and adoption ──────────────────────────────────────────────

def test_the_benchmark_chart_has_a_point_per_full_gate_and_its_table_says_where_each_kind_stands(engine):
    assert [(row["run_on"], row["share_percent"]) for row in rows(engine, "benchmark_shares")] == [
        (dt.date(2026, 10, 1), 90), (dt.date(2026, 10, 20), 87)]
    latest = [row for row in rows(engine, "benchmark_results") if row["run_id"] == "gate-2"]
    assert [(row["kind"], row["passed"], row["questions"], row["target"], row["against"]) for row in latest] == [
        ("SQL", 17, 20, "85%", "Met"), ("Documents", 16, 20, "90%", "Missed by 10 points"),
        ("Estimates", 6, 6, "80%", "Met"), ("Must refuse", 6, 6, "100%", "Met"), ("All", 45, 52, "85%", "Met")]


def test_foundry_s_bars_are_left_out_below_fifty_answers_and_its_table_keeps_the_counts(engine):
    """DESIGN.md section 7, rule 15: no percentage from fewer than 50 cases; 40 answers were scored."""
    chart = rows(engine, "foundry_latest")

    assert [(row["evaluator"], row["met"], row["scored"], row["share_percent"]) for row in chart] == [
        ("Groundedness", 34, 40, None), ("Relevance", 36, 40, None), ("Task adherence", 30, 40, None),
        ("Tool use", 38, 40, None)]
    assert [row["mean_score"] for row in rows(engine, "foundry_results")] == [4.2, 4.5, 4.0, 4.6]


def test_removed_sentences_and_held_back_answers_are_counted_by_reason_with_what_they_are_out_of(engine):
    assert [(row["what"], row["reason"], row["count"], row["out_of"]) for row in rows(engine, "reasons")] == [
        ("Removed sentence", "Its sources don't say this", 1, "20 sentences written"),
        ("Removed sentence", "No record supports a number or date", 1, "20 sentences written"),
        ("Removed sentence", "Quote not on the page it cites", 1, "20 sentences written"),
        ("Held-back answer", "Outside what my model learned from", 1, "3 answers"),
        ("Held-back answer", "Too few comparable packages for a range", 1, "3 answers")]


def test_each_loop_s_leading_indicator_reads_its_stored_rows(engine):
    assert [(row["decided_on"], row["days_from_publication"]) for row in rows(engine, "kpi_days_to_decision")] == [
        (dt.date(2026, 10, 16), 6), (dt.date(2026, 10, 9), 24), (dt.date(2026, 10, 2), 7)]
    assert [(row["week_start"], row["wrong_per_100"], row["not_useful_per_100"], row["wrong_per_100_cell"])
            for row in rows(engine, "kpi_wrong_passage_rate")] == [
        (dt.date(2026, 10, 19), None, None, "1 in 12"), (dt.date(2026, 10, 12), 7.5, 5.0, "7.5")]
    assert [(row["month"], row["coverage_percent"], row["coverage_cell"], row["target_low"], row["target_high"])
            for row in rows(engine, "kpi_rolling_coverage")] == [
        (dt.date(2026, 9, 30), 87, "52 of 60, 87%", 75, 85),
        (dt.date(2026, 8, 31), None, "30 of 40, about 8 in 10", 75, 85)]


def test_each_loop_s_lagging_indicator_reads_its_stored_rows(engine):
    [release] = rows(engine, "kpi_blamed_covered")
    assert (release["blamed"], release["covered"], release["shown_when_covered"], release["hindsight_recall"]) == (
        30, 18, "12 of 18", "12 of 30, about 4 in 10")
    held_out = [row for row in rows(engine, "kpi_precision_recall") if row["segment_kind"] == "held_out"]
    assert [(row["run_on"], row["held_out_precision"], row["held_out_recall"]) for row in held_out] == [
        (dt.date(2026, 10, 10), 0.62, 0.71), (dt.date(2026, 9, 10), 0.6, 0.7)]
    assert [(row["plan_rows"], row["countries"], row["median_days_cell"], row["median_months_cell"])
            for row in rows(engine, "kpi_plan_accuracy")] == [
        ("Dated within 14 days of a date I offered", "Using Strata", "12", "9.5"),
        ("Dated within 14 days of a date I offered", "Not yet using Strata", "0 rows, too few for a median",
         "0 rows, too few for a median"),
        ("Other plan rows", "Using Strata", "30", "1 row, too few for a median"),
        ("Other plan rows", "Not yet using Strata", "41", "5 rows, too few for a median")]


def test_weekly_use_and_drafts_come_from_usage_events_and_draft_states(engine):
    assert [(row["week_start"], row["people"], row["answers"], row["started"], row["checked"], row["exported"])
            for row in rows(engine, "use_by_week")] == [
        (dt.date(2026, 10, 19), 1, 3, 2, 1, 0), (dt.date(2026, 10, 12), 2, 0, 1, 1, 1)]
    assert [(row["month"], row["share"]) for row in rows(engine, "plan_rows_by_month")] == [
        (dt.date(2026, 9, 30), "2 of 5"), (dt.date(2026, 8, 31), "30 of 60, 50%")]


def test_a_spend_over_its_budget_says_by_how_much_and_a_failed_pull_says_where_the_figures_stop():
    from strata.dashboard import findings

    budget = Budget(**{**load_budget().__dict__, "credit_usd": 5})
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        costs.pull(engine, costs.RecordedCosts(json.loads(COSTS.read_text())), "pull-1", lambda: at(TODAY, 6), budget)
        engine.insert_rows(costs.PULLS, costs.PULL_COLUMNS, [("pull-2", at(TODAY, 8), "failed", TODAY, None, 0,
                                                               "unreachable", "I could not reach Azure: timed out",
                                                               TODAY)])
        [row] = rows(engine, "kpi_azure_spend")
        text, measured = findings.spend(engine, TODAY)

    assert (row["display"], row["over"]) == ("US$8 of US$5", 2.8)
    assert text == ("By October 22, the latest day with cost data, my Azure resources had cost US$7.80. That is US$2.80 "
                    "more than the US$5.00 budget for the free credit, which ends November 10, 2026. I couldn't pull "
                    "Azure costs on October 23, so these figures stop at October 22.")
    assert measured == dt.date(2026, 10, 22)


def test_a_throttled_pull_reads_as_a_day_with_no_charges_and_names_why():
    """Ticket 107: the throttled day adds no charge, so the counter and the latest day stay where they were."""
    from strata.dashboard import findings

    class Throttled:
        def charges(self, starts_on, ends_on):
            raise costs.CostError("throttled", "Azure answered 429: Too many requests. Please retry.")

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        costs.pull(engine, costs.RecordedCosts(json.loads(COSTS.read_text())), "pull-1", lambda: at(TODAY, 6))
        costs.pull(engine, Throttled(), "pull-2", lambda: at(TODAY, 8))
        [row] = rows(engine, "kpi_azure_spend")
        text, measured = findings.spend(engine, TODAY)

    assert row["display"] == "US$8 of US$197"
    assert text == ("By October 22, the latest day with cost data, my Azure resources had cost US$7.80 of the US$197.00 "
                    "budget for the free credit, which ends November 10, 2026. Azure throttled the cost pull on October "
                    "23: it had too many requests and asked me to wait. The next daily pull tries again.")
    assert measured == dt.date(2026, 10, 22)
