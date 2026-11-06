"""A made-up month of Prism's operations for the dashboard's tests (ticket 45).

The fixture database holds what the nightly run and the plan reader write, and nothing of what people, the full
gate, the replay harness or the cost pull do. These rows stand in for those, written into an empty catalog built
with catalog.build, so every tile can be compared with numbers known in advance. Every value here is made up, and
the expected numbers in the tests are counted from this file by hand, never by the dashboard's queries.

The day is Friday, October 23, 2026. The last full week ends on Sunday, October 18.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from strata.lakehouse import catalog, costs
from strata.lakehouse.engine import DuckDBEngine

TODAY = dt.date(2026, 10, 23)
DATES = {"date_from": dt.date(2026, 7, 25), "date_to": TODAY}  # the last 90 days
TASKS = ("fetch_by_watermark", "bronze_to_gold", "parse_and_embed", "sync_index", "relink", "propose_lessons",
         "detect_disagreements", "score", "measure_data_readiness", "refresh_drafts")
COSTS = Path(__file__).parent / "fixtures" / "azure_costs" / "query.json"


def at(day: dt.date, hour: int, minute: int = 0) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=dt.UTC)


def insert(engine, table: str, rows: list[dict]) -> None:
    columns = tuple(rows[0])
    engine.insert_rows(table, columns, [tuple(row[column] for column in columns) for row in rows])


# ── Nightly runs and quality checks ──────────────────────────────────────

def nightly(engine) -> None:
    """Three nights. October 21 finished cleanly; October 22 finished after relink was tried again, and one check
    found three duplicate rows; October 23 stopped at parse_and_embed after two tasks."""
    runs, checks = [], []

    def task(run_id, key, status, start, rows=10):
        runs.append({"run_id": run_id, "task_key": key, "status": status, "rows_changed": rows, "started_at": start,
                     "finished_at": start + dt.timedelta(minutes=3), "public_from": start.date()})

    def check(run_id, night, key, kind, table, found, passed, when, low=None, high=None, key_name=None):
        checks.append({"run_id": run_id, "night": night, "task_key": key, "check_kind": kind, "table_name": table,
                       "key_name": key_name, "found": found, "expected_min": low, "expected_max": high,
                       "passed": passed, "checked_at": when, "public_from": when.date()})

    night = dt.date(2026, 10, 21)
    for number, key in enumerate(TASKS):
        task("run-21", key, "succeeded", at(night, 7) + dt.timedelta(minutes=3 * number))
    check("run-21", night, "fetch_by_watermark", "missing_key", "strata.bronze.api_pages", 0, True, at(night, 7, 3),
          key_name="source")
    check("run-21", night, "bronze_to_gold", "row_count", "strata.silver.notices", 244, True, at(night, 7, 6), 1, 10_000)
    check("run-21", night, "bronze_to_gold", "contacts_left", "strata.silver.notices", 0, True, at(night, 7, 6))

    night = dt.date(2026, 10, 22)
    for number, key in enumerate(TASKS):
        start = at(night, 7) + dt.timedelta(minutes=3 * number)
        if key == "relink":
            task("run-22", key, "failed", start, rows=0)
            start += dt.timedelta(minutes=1)
        task("run-22", key, "succeeded", start)
    check("run-22", night, "fetch_by_watermark", "missing_key", "strata.bronze.api_pages", 0, True, at(night, 7, 3),
          key_name="source")
    check("run-22", night, "bronze_to_gold", "row_count", "strata.silver.notices", 250, True, at(night, 7, 6), 1, 10_000)
    check("run-22", night, "bronze_to_gold", "contacts_left", "strata.silver.notices", 0, True, at(night, 7, 6))
    check("run-22", night, "bronze_to_gold", "duplicates", "strata.gold.contract", 3, False, at(night, 7, 6))

    night = TODAY
    task("run-23", "fetch_by_watermark", "succeeded", at(night, 7))
    task("run-23", "bronze_to_gold", "succeeded", at(night, 7, 3))
    task("run-23", "parse_and_embed", "failed", at(night, 7, 6), rows=0)
    check("run-23", night, "fetch_by_watermark", "missing_key", "strata.bronze.api_pages", 0, True, at(night, 7, 3),
          key_name="source")
    check("run-23", night, "bronze_to_gold", "row_count", "strata.silver.notices", 251, True, at(night, 7, 6), 1, 10_000)
    check("run-23", night, "bronze_to_gold", "contacts_left", "strata.silver.notices", 0, True, at(night, 7, 6))
    insert(engine, "strata.ops.pipeline_runs", runs)
    insert(engine, "strata.ops.quality_checks", checks)


def contacts(engine) -> None:
    """Two pages of notices: the first lost 2 names, 5 emails and 4 phones from three notices, the second one email."""
    rows = []
    for page, day, kinds in (("page-1", dt.date(2026, 10, 20), {"names": (2, 2), "emails": (5, 3), "phones": (4, 2),
                                                                 "any": (11, 3)}),
                             ("page-2", dt.date(2026, 10, 21), {"emails": (1, 1), "any": (1, 1)})):
        rows += [{"source": "notices", "country_code": "KE", "page_hash": page, "kind": kind, "removed": removed,
                  "records": records, "fetched_at": at(day, 7), "public_from": day}
                 for kind, (removed, records) in kinds.items()]
    insert(engine, "strata.ops.contact_removals", rows)
    insert(engine, "strata.gold.notice", [{"notice_id": "OP-made-up", "public_from": dt.date(2026, 10, 20)}])


# ── Answers ──────────────────────────────────────────────────────────────

RUN_COLUMNS = {"scope": None, "as_of": TODAY, "language": "en", "error_code": None, "agent": "strata-orchestrator",
               "agent_version": None, "tool_rounds": 1, "tool_calls": "[]", "response_ids": "[]",
               "numbers_total": None, "numbers_matched": None, "dates_total": None, "dates_matched": None,
               "quotes_total": None, "quotes_found": None, "sources_total": None, "sources_returned": None,
               "removed": "[]", "application_insights_trace_id": None, "mlflow_trace_id": None}


def answers(engine) -> None:
    """Three answers: run-a removed one sentence and held back on too few comparables; run-b read a private upload
    and lost two sentences; run-c held back outside its model's training."""
    runs = [("run-a", dt.date(2026, 10, 21), 6, 5, 1), ("run-b", dt.date(2026, 10, 22), 8, 6, 2),
            ("run-c", dt.date(2026, 10, 22), 6, 6, 0)]
    insert(engine, "strata.ops.agent_runs", [{
        **RUN_COLUMNS, "run_id": run_id, "viewer_id": "1001@1984", "question": f"A made-up question for {run_id}",
        "view": "staff", "status": "answered", "sentences_written": written, "sentences_kept": kept,
        "sentences_removed": removed, "started_at": at(day, 14, 2 if run_id == "run-c" else 0),
        "finished_at": at(day, 14, 3 if run_id == "run-c" else 1), "public_from": day}
        for run_id, day, written, kept, removed in runs])
    insert(engine, "strata.ops.answer_removals", [
        {"run_id": run_id, "position": position, "reason": reason, "removed_at": at(day, 14, 1), "public_from": day}
        for run_id, day, position, reason in (("run-a", dt.date(2026, 10, 21), 1, "number_not_in_records"),
                                              ("run-b", dt.date(2026, 10, 22), 1, "quote_not_on_page"),
                                              ("run-b", dt.date(2026, 10, 22), 2, "not_supported"))])

    def call(run_id, day, order, tool, inputs, rows, abstention=None, private=False):
        return {"run_id": run_id, "call_order": order, "round": 1, "tool": tool, "inputs": inputs,
                "rows_returned": rows, "took_ms": 120, "evidence_ids": None, "abstention": abstention, "error": None,
                "private_upload": private, "called_at": at(day, 14), "public_from": day}

    insert(engine, "strata.ops.tool_calls", [
        call("run-a", dt.date(2026, 10, 21), 1, "search_passages", "query: rebidding", 3),
        call("run-a", dt.date(2026, 10, 21), 2, "find_comparables", "step_reference: KE-X", 4, "too_few_comparables"),
        call("run-b", dt.date(2026, 10, 22), 1, "check_plan", "upload_id: a private upload", 5, private=True),
        call("run-c", dt.date(2026, 10, 22), 1, "estimate_time", "step_reference: KE-Y", 0, "outside_training")])
    insert(engine, "strata.ops.tool_call_reads", [
        {"run_id": run_id, "call_order": order, "tool": tool, "table_name": table, "version_read": None,
         "sources": "Projects", "read_at": at(day, 14), "public_from": day}
        for run_id, day, order, tool, table in (
            ("run-a", dt.date(2026, 10, 21), 1, "search_passages", "strata.gold.passage"),
            ("run-a", dt.date(2026, 10, 21), 2, "find_comparables", "strata.gold.package"),
            ("run-b", dt.date(2026, 10, 22), 1, "check_plan", "strata.silver.plan_rows"),
            ("run-c", dt.date(2026, 10, 22), 1, "estimate_time", "strata.gold.package"))])


def use(engine) -> None:
    """People and drafts. In the week of October 12, two people opened pages and a third only called the API; in the
    week of October 19, one person did. Three drafts: one checked and exported, one checked, one only started."""
    events = [("u1", "/projects/P130164", dt.date(2026, 10, 13)), ("u1", "/api/freshness", dt.date(2026, 10, 13)),
              ("u2", "/", dt.date(2026, 10, 16)), ("u3", "/api/me", dt.date(2026, 10, 17)),
              ("u1", "/", dt.date(2026, 10, 20)), (None, "/", dt.date(2026, 10, 20))]
    insert(engine, "strata.ops.usage_events", [
        {"viewer_id": viewer, "route": route, "view": "staff", "requested_at": at(day, 9), "trace_id": None,
         "public_from": day} for viewer, route, day in events])
    insert(engine, "strata.ops.drafts", [
        {"draft_id": draft, "kind": "review_notes", "team_key": "team:kenya", "author_id": "u1", "author_name": None,
         "idempotency_key": None, "project_id": "P156634", "subject": None, "content": "{}",
         "created_at": at(day, 10), "public_from": day}
        for draft, day in (("d1", dt.date(2026, 10, 13)), ("d2", dt.date(2026, 10, 20)), ("d3", dt.date(2026, 10, 21)))])
    states = [("d1", 1, "draft", dt.date(2026, 10, 13)), ("d1", 2, "checked", dt.date(2026, 10, 14)),
              ("d1", 3, "exported", dt.date(2026, 10, 15)), ("d2", 1, "draft", dt.date(2026, 10, 20)),
              ("d2", 2, "checked", dt.date(2026, 10, 21)), ("d3", 1, "draft", dt.date(2026, 10, 21))]
    insert(engine, "strata.ops.draft_states", [
        {"draft_id": draft, "step": step, "state": state, "from_state": None, "actor_id": "u1", "actor_name": None,
         "changed_at": at(day, 11), "public_from": day} for draft, step, state, day in states])


# ── Evaluations ──────────────────────────────────────────────────────────

def _result(run_id, scorer, kind, segment, measure, value, ran_at, text=None):
    return {"run_id": run_id, "scorer": scorer, "model": None, "segment_kind": kind, "segment": segment,
            "measure": measure, "value": value, "value_text": text, "cutoff": None, "outcomes_through": None,
            "mlflow_run_id": None, "ran_at": ran_at, "public_from": ran_at.date()}


def evaluations(engine) -> None:
    """Two full gates (October 1 and 20), one Foundry evaluation of 40 answers, two retrieval evaluations and one
    hindsight test."""
    rows = []
    for run_id, day, kinds in (
            ("gate-1", dt.date(2026, 10, 1), {"all": (52, 47, 0.9038, 0.85, 0, 1)}),
            ("gate-2", dt.date(2026, 10, 20), {"sql": (20, 17, 0.85, 0.85, 0, 1), "documents": (20, 16, 0.8, 0.9, 0.1, 0),
                                              "estimates": (6, 6, 1.0, 0.8, 0, 1), "must_refuse": (6, 6, 1.0, 1.0, 0, 1),
                                              "all": (52, 45, 0.8654, 0.85, 0, 1)})):
        for segment, (questions, passed, share, target, gap, met) in kinds.items():
            rows += [_result(run_id, "benchmark", "kind", segment, measure, value, at(day, 20))
                     for measure, value in (("questions", questions), ("passed", passed), ("share", share),
                                            ("target", target), ("gap", gap), ("met", met))]
    for key, met, mean in (("groundedness", 34, 4.24), ("relevance", 36, 4.5), ("task_adherence", 30, 3.96),
                           ("tool_use", 38, 4.61)):
        rows += [_result("eval-1", "foundry_evaluation", "evaluator", key, measure, value, at(dt.date(2026, 10, 20), 21))
                 for measure, value in (("scored", 40), ("met", met), ("share", round(met / 40, 4)),
                                        ("mean_score", mean))]
    for run_id, day, precision, recall in (("retrieval-0", dt.date(2026, 9, 10), 0.6, 0.7),
                                           ("retrieval-1", dt.date(2026, 10, 10), 0.62, 0.71)):
        for kind, queries in (("query_set", 250), ("held_out", 25)):
            rows += [_result(run_id, "retrieval_evaluation", kind, "icr_review_citations", measure, value,
                             at(day, 4)) for measure, value in (("queries", queries), ("precision_at_10", precision),
                                                                 ("recall_at_20", recall), ("ndcg_at_10", 0.58))]
    release = {"projects": 12, "expected_projects": 12, "blamed": 30, "covered": 18, "shown": 14,
               "checklist_caught": 9, "interval_low": 0.25, "interval_high": 0.58, "interval_level": 0.95,
               "risks_per_package": 5, "checklist_size": 5, "min_blamed_for_share": 20, "main_packages": 3}
    rows += [_result("hindsight-1", "hindsight_test", "release", "r1", measure, value, at(dt.date(2026, 10, 15), 5))
             for measure, value in release.items()]
    rows += [_result("hindsight-1", "hindsight_test", "release", "r1", "shown_when_covered", 0.6667,
                     at(dt.date(2026, 10, 15), 5), "12 of 18"),
             _result("hindsight-1", "hindsight_test", "release", "r1", "hindsight_recall", 0.4,
                     at(dt.date(2026, 10, 15), 5), "12 of 30")]
    insert(engine, "strata.ops.evaluation_result", rows)


def loops(engine) -> None:
    """Three lesson decisions, two weeks of passage reports, two months of coverage, plan accuracy, plan rows after a
    range was shown, and one retrain the watch raised."""
    decided = [("lesson-a", dt.date(2026, 10, 2), dt.date(2026, 9, 25)), ("lesson-b", dt.date(2026, 10, 9),
                                                                          dt.date(2026, 9, 15)),
               ("lesson-c", dt.date(2026, 10, 16), dt.date(2026, 10, 10))]
    insert(engine, "strata.ops.lesson_versions", [
        {"lesson_id": lesson, "version": 1, "statement": "A made-up lesson.", "risk_factors": "[]", "stage": "planning",
         "kind": "worked", "edition_key": None, "project_id": "P130164", "state": "current", "change_kind": "added",
         "was": None, "now": None, "reason": "Made up.", "item_id": f"new-{lesson}", "decided_on": on,
         "decided_by": "lead@example.org", "decided_by_name": "A lead", "recommended_by": "spec@example.org",
         "recommended_by_name": "A specialist", "recommended_reason": "Made up.", "published_on": published,
         "days_from_publication": (on - published).days, "public_from": on} for lesson, on, published in decided])
    weekly = [(dt.date(2026, 10, 12), "wrong_passage", 3, 40, 7.5), (dt.date(2026, 10, 12), "not_useful", 2, 40, 5.0),
              (dt.date(2026, 10, 19), "wrong_passage", 1, 12, None), (dt.date(2026, 10, 19), "not_useful", 0, 12, None)]
    insert(engine, "strata.ops.retrieval_feedback_weekly", [
        {"week_start": week, "kind": kind, "reports": reports, "opened": opened, "per_100": rate,
         "computed_at": at(TODAY, 6), "public_from": TODAY} for week, kind, reports, opened, rate in weekly])

    def watch(month, measure, segment, count, denominator, value=None):
        return {"run_id": f"watch-{month:%m}", "month": month, "measure": measure, "segment": segment, "count": count,
                "denominator": denominator, "value": value, "detail": None, "reason": None,
                "measured_at": at(month + dt.timedelta(days=1), 6), "public_from": month + dt.timedelta(days=1)}

    august, september = dt.date(2026, 8, 31), dt.date(2026, 9, 30)
    insert(engine, "strata.ops.estimates_watch", [
        watch(august, "coverage", "all", 30, 40), watch(september, "coverage", "all", 52, 60),
        watch(august, "anchored_rows", "published_in_month", 30, 60),
        watch(september, "anchored_rows", "all", 4, 9), watch(september, "anchored_rows", "published_in_month", 2, 5),
        watch(september, "plan_accuracy", "anchored/using_strata", 25, 30, 12.0),
        watch(september, "plan_accuracy", "anchored/not_yet", 0, 0),
        watch(september, "plan_accuracy", "other/using_strata", 40, 44, 30.0),
        watch(september, "plan_accuracy", "other/not_yet", 22, 25, 41.0),
        watch(september, "plan_duration", "anchored/using_strata", 21, 30, 9.5),
        watch(september, "plan_duration", "anchored/not_yet", 0, 0),
        watch(september, "plan_duration", "other/using_strata", 1, 44),
        watch(september, "plan_duration", "other/not_yet", 5, 25)])
    insert(engine, "strata.ops.retrain_triggers", [
        {"run_id": "watch-09", "month": september, "reason": "coverage_outside", "edition_key": None, "detail": None,
         "model": "strata_time_estimate", "raised_on": dt.date(2026, 10, 1), "raised_at": at(dt.date(2026, 10, 1), 6),
         "public_from": dt.date(2026, 10, 1)}])


def seeded() -> DuckDBEngine:
    """An empty catalog with the made-up month in it, and the cost pull's recorded answer pulled on October 23."""
    engine = DuckDBEngine.open()
    catalog.build(engine)
    for seed in (nightly, contacts, answers, use, evaluations, loops):
        seed(engine)
    costs.pull(engine, costs.RecordedCosts(json.loads(COSTS.read_text())), "pull-1", lambda: at(TODAY, 6))
    return engine


def rows(engine, name: str, **params) -> list[dict]:
    """A dataset's rows through the query the dashboard runs, with the last 90 days unless told otherwise."""
    from strata.dashboard import render

    sql = render.query(name)
    bound = {**DATES, "budget_period": "", "run_id": "", "measure_date": TODAY, **params}
    result = engine.run(sql, {key: value for key, value in bound.items() if f":{key}" in sql})
    return [dict(zip(result.columns, row)) for row in result.rows]
