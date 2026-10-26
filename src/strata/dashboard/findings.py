"""What the measures say, and each loop's indicators, written for the dashboard (ticket 45; the 45 design brief,
sections 2, 6.3, 7.3 and 7.4).

AI/BI titles are fixed when the dashboard is deployed, so each page's findings sit in a table at its top, written by
the job that takes the measures: one function per section, for a fixed period the sentence names, from the copy
file's templates (copy.dash.gov.find and copy.dash.ai.find). Each function reads its numbers through the dashboard's
own queries (strata.dashboard.render.query, the KPI registry's defining queries among them), so a counter, its twin
table and its sentence never disagree (CLAUDE.md rule 4), and it adds no number of its own beyond picking which
template fits (CLAUDE.md rule 1). Each loop's indicators (tile 19) are written the same way.

write() appends the rows to strata.ops.dashboard_findings and strata.ops.loop_indicators. The nightly job's
measure_data_readiness task writes every section after its measures; the daily cost pull writes Azure spend.
"""

from __future__ import annotations

import datetime as dt
import logging
import statistics
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal

from strata.config import load_kpis, load_thresholds
from strata.dashboard import render
from strata.dashboard import wording as say
from strata.lakehouse.engine import Engine

LOG = logging.getLogger(__name__)
FINDINGS = "strata.ops.dashboard_findings"
INDICATORS = "strata.ops.loop_indicators"
FINDING_COLUMNS = ("run_id", "page", "section", "position", "about", "finding", "measured_on", "written_at",
                   "public_from")
INDICATOR_COLUMNS = ("run_id", "position", "kpi", "loop", "indicator", "kind", "latest", "target", "against",
                     "measured_on", "written_at", "public_from")
EPOCH = dt.date(2000, 1, 1)  # "up to {day}": every row the store holds


def _rows(engine: Engine, name: str, date_from: dt.date | None = None, date_to: dt.date | None = None,
          **params) -> list[dict]:
    """A dataset's rows, through the query the dashboard runs."""
    sql = render.query(name)
    bound = {"date_from": date_from, "date_to": date_to, **params}
    result = engine.run(sql, {key: value for key, value in bound.items() if f":{key}" in sql})
    return [dict(zip(result.columns, row)) for row in result.rows]


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _whole(value) -> int | None:
    return None if value is None or value == "" else int(Decimal(str(value)).quantize(Decimal(1), ROUND_HALF_UP))


def _value(dotted: str):
    return load_thresholds().value(dotted)


def _none_or(number: int):
    """A count after the noun it counts, with zero as "none" ("marked none as not useful")."""
    return say.Unit(say.at("dash.none")) if number == 0 else number


def _percent(part: int, whole: int) -> int:
    return int((Decimal(part) * 100 / Decimal(whole)).quantize(Decimal(1), ROUND_HALF_UP))


# ── Governance ───────────────────────────────────────────────────────────

def runs(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """The latest nightly run: how it ended, its time, and its quality checks (section 6.3, first row)."""
    found = _rows(engine, "nightly_runs", EPOCH, today)
    if not found:
        return say.at("dash.gov.find.runs.none"), None
    run = found[0]
    night = _date(run["night"])
    tasks = int(render.expand(":nightly_tasks"))
    checks = _rows(engine, "kpi_checks_failed", night, night)[0]
    total, failed = int(checks["denominator"] or 0), int(checks["numerator"] or 0)
    slots = {"night": say.day(night, today), "tasks": tasks, "minutes": say.Unit(str(int(run["minutes"] or 0))),
             "checks": total, "passed": total - failed, "failed": failed}
    if run["stopped_label"]:
        done = int(run["tasks_done"] or 0)
        if done == 0:
            return say.fill(say.at("dash.gov.find.runs.stoppedFirst"), taskName=run["stopped_label"], **slots), night
        return say.say("dash.gov.find.runs.stopped", "done", taskName=run["stopped_label"], done=done, ran=total,
                       **slots), night
    if failed == 0:
        return say.fill(say.at("dash.gov.find.runs.allPassed"), **slots), night
    first = _rows(engine, "failed_checks", night, night)[0]
    phrase = say.Unit(say.say(f"dash.gov.check.{first['check_kind']}", "found", phrase=True, found=int(first["found_count"]),
                              table=say.Unit(first["table_name"]), min=say.Unit(f"{first['expected_min'] or 0:,}"),
                              max=say.Unit(f"{first['expected_max'] or 0:,}"), keyName=say.Unit(first["key_name"] or "")))
    key = "oneFailed" if failed == 1 else "severalFailed"
    return say.fill(say.at(f"dash.gov.find.runs.{key}"), checkPhrase=phrase, **slots), night


LATEST_PULL = """
SELECT status, pulled_at, through_day
FROM strata.ops.cost_pulls
ORDER BY pulled_at DESC
LIMIT 1
"""


def spend(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """Azure spend in the current budget period against its budget, and a pull that failed (section 6.3)."""
    period = _rows(engine, "kpi_azure_spend", budget_period="")[0]
    latest = _date(period["latest_day"])
    if latest is None:
        return say.at("dash.gov.find.spend.none"), None
    slots = {"day": say.day(latest, today), "spent": say.money(period["numerator"]),
             "budget": say.money(period["denominator"]), "periodName": say.Unit(period["period_name"])}
    over = Decimal(str(period["over"] or 0))
    text = (say.fill(say.at("dash.gov.find.spend.over"), over=say.money(over), **slots) if over > 0
            else say.fill(say.at("dash.gov.find.spend.inside"), **slots))
    pulls = engine.run(LATEST_PULL).rows
    if pulls and pulls[0][0] == "failed":
        failed_on = _date(pulls[0][1])
        text += " " + say.fill(say.at("dash.gov.find.spend.pullFailed"), failedOn=say.day(failed_on, today),
                               day=slots["day"])
    return text, latest


NOTICES = "SELECT count(*) AS notices FROM strata.gold.notice"
REMOVED_FROM = """
SELECT sum(records) AS notices, max(public_from) AS last_day
FROM strata.ops.contact_removals
WHERE kind = 'any' AND public_from <= :today
"""


def personal(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """The contact details ingestion removed up to today, by kind, and any the latest check found left (6.3)."""
    if not int(engine.run(NOTICES).rows[0][0] or 0):
        return say.at("dash.gov.find.personal.none"), None
    kinds = {row["kind"]: row for row in _rows(engine, "contact_removals", EPOCH, today)}
    labels = say.at("dash.gov.kinds")
    count = {key: int((kinds.get(labels[key]) or {}).get("removed") or 0) for key in ("names", "emails", "phones")}
    notices, last_day = engine.run(REMOVED_FROM, {"today": today}).rows[0]
    measured = _date(last_day) or today
    text = say.say("dash.gov.find.personal.removed", "notices", day=say.day(measured, today),
                   notices=int(notices or 0), **count)
    left = _rows(engine, "kpi_contacts_left", EPOCH, today)[0]
    if left["denominator"]:
        found = int(left["numerator"] or 0)
        text += " " + (say.at("dash.gov.find.personal.noneLeft") if found == 0
                       else say.say("dash.gov.find.personal.someLeft", "left", left=found))
    return text, measured


def queries(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """Who queried Strata's tables in the 7 days to today, where the workspace lets Strata read its history (6.3)."""
    try:
        found = _rows(engine, "queries", today - dt.timedelta(days=6), today)
    except Exception:  # noqa: BLE001 - no query history to read here, as on DuckDB or a workspace that hides it:
        # Spark raises AnalysisException, the warehouse and DuckDB EngineError
        return say.at("dash.gov.find.queries.notReadable"), today
    if not found:
        return say.fill(say.at("dash.gov.find.queries.none"), day=say.day(today, today)), today
    app = say.at("dash.gov.through.app")
    return say.say("dash.gov.find.queries.readable", "people", day=say.day(today, today),
                   people=len({row["person"] for row in found}), queries=sum(int(row["queries"]) for row in found),
                   appQueries=sum(int(row["queries"]) for row in found if row["through"] == app)), today


RUN_LINEAGE = """
SELECT
  r.run_id,
  count(c.call_order) AS calls,
  sum(CASE WHEN c.error IS NULL AND NOT EXISTS (
        SELECT 1 FROM strata.ops.tool_call_reads AS t WHERE t.run_id = c.run_id AND t.call_order = c.call_order
      ) THEN 1 ELSE 0 END) AS calls_without_reads
FROM strata.ops.agent_runs AS r
LEFT JOIN strata.ops.tool_calls AS c ON c.run_id = r.run_id
WHERE r.public_from BETWEEN :date_from AND :date_to
GROUP BY r.run_id
"""


def lineage(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """How many answer runs in the 7 days to today lead back to their tool calls and the tables they read (6.3)."""
    found = engine.run(RUN_LINEAGE, {"date_from": today - dt.timedelta(days=6), "date_to": today}).rows
    day = say.day(today, today)
    if not found:
        return say.fill(say.at("dash.gov.find.lineage.none"), day=day), today
    complete = sum(1 for _, _, missing in found if not missing)
    if len(found) == 1:
        key = "dash.gov.find.lineage.one" if complete else "dash.gov.find.lineage.oneIncomplete"
        return say.fill(say.at(key), day=day), today
    if complete == len(found):
        return say.fill(say.at("dash.gov.find.lineage.all"), runs=len(found), day=day), today
    return say.say("dash.gov.find.lineage.some", "missing", runs=len(found), complete=complete,
                   missing=len(found) - complete, day=day), today


# ── AI quality and adoption ──────────────────────────────────────────────

def _percent_text(share) -> say.Unit:
    return say.Unit(say.fill(say.at("dash.percent"), phrase=True, n=say.Unit(str(_whole(Decimal(str(share)) * 100)))))


def benchmark(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """The latest full gate's benchmark, its refusals and its targets (section 7.3, Benchmark)."""
    latest = _rows(engine, "kpi_benchmark_passed", EPOCH, today)[0]
    if not latest["denominator"]:
        return say.at("dash.ai.find.benchmark.none"), None
    rows = _rows(engine, "benchmark_results", EPOCH, today)
    run = [row for row in rows if row["run_id"] == rows[0]["run_id"]]
    day = _date(run[0]["run_on"])
    refusals = [row for row in run if row["kind_key"] == "must_refuse"]
    slots = {"day": say.day(day, today), "passed": int(latest["numerator"]), "total": int(latest["denominator"])}
    text = (say.fill(say.at("dash.ai.find.benchmark.firstRefused"), refused=int(refusals[0]["passed"]),
                     mustRefuse=int(refusals[0]["questions"]), **slots) if refusals
            else say.fill(say.at("dash.ai.find.benchmark.first"), **slots))
    missed = [row for row in run if not row["met"]]
    if not missed:
        return text + " " + say.at("dash.ai.find.benchmark.allMet"), day
    first = missed[0]
    target = {"targetName": say.Unit(first["kind"]), "got": _percent_text(first["share"]),
              "target": _percent_text(first["target_share"])}
    if len(missed) == 1:
        return text + " " + say.fill(say.at("dash.ai.find.benchmark.oneMissed"), **target), day
    return text + " " + say.fill(say.at("dash.ai.find.benchmark.severalMissed"), missed=len(missed), **target), day


LATEST_EVALUATION = """
SELECT max(ran_at) AS ran_at
FROM strata.ops.evaluation_result
WHERE scorer = 'foundry_evaluation' AND public_from <= :today
"""


def foundry(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """The latest Microsoft Foundry evaluation: of the answers it scored, how many met each evaluator's threshold."""
    found = {row["evaluator"]: row for row in _rows(engine, "foundry_latest", EPOCH, today)}
    if not found:
        return say.at("dash.ai.find.foundry.none"), None
    day = _date(engine.run(LATEST_EVALUATION, {"today": today}).rows[0][0])
    labels = say.at("dash.ai.evaluators")
    met = {slot: int((found.get(labels[key]) or {}).get("met") or 0)
           for slot, key in (("g", "groundedness"), ("r", "relevance"), ("t", "task_adherence"), ("u", "tool_use"))}
    scored = max(int(row["scored"] or 0) for row in found.values())
    return say.say("dash.ai.find.foundry.ran", "n", n=scored, day=say.day(day, today), **met), day


def _tied(reasons: list[dict], column: str) -> int:
    """How many reasons share the largest count, or 0 when one reason has it alone. The query sorts the largest
    first, so a tie is the first rows with the same count."""
    top = reasons[0][column]
    tied = sum(1 for row in reasons if row[column] == top)
    return tied if tied > 1 else 0


def checks(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """What my six checks removed and where I held back, in the 7 days to today (section 7.3)."""
    start = today - dt.timedelta(days=6)
    removed = _rows(engine, "kpi_sentences_removed", start, today)[0]
    held = _rows(engine, "kpi_answers_held_back", start, today)[0]
    day = say.day(today, today)
    if not held["denominator"]:
        return say.fill(say.at("dash.ai.find.checks.none"), day=day), today
    written, count = int(removed["denominator"] or 0), int(removed["numerator"] or 0)
    if count:
        reasons = _rows(engine, "removed_reasons", start, today)
        top, tied = reasons[0], _tied(reasons, "sentences")
        slots = {"day": day, "removed": count, "written": written, "topCount": int(top["sentences"])}
        text = (say.fill(say.at("dash.ai.find.checks.removedTied"), tied=tied, **slots) if tied
                else say.fill(say.at("dash.ai.find.checks.removed"), reasonLabel=say.Unit(top["reason"]), **slots))
    else:
        text = say.fill(say.at("dash.ai.find.checks.noneRemoved"), day=day, written=written)
    answers, held_count = int(held["denominator"]), int(held["numerator"] or 0)
    if held_count:
        reasons = _rows(engine, "held_reasons", start, today)
        tied = _tied(reasons, "answers")
        text += " " + (say.fill(say.at("dash.ai.find.checks.heldTied"), held=held_count, answers=answers, tied=tied)
                       if tied else
                       say.fill(say.at("dash.ai.find.checks.held"), held=held_count, answers=answers,
                                holdLabel=say.Unit(reasons[0]["reason"])))
    else:
        text += " " + say.fill(say.at("dash.ai.find.checks.noneHeld"), answers=answers)
    return text, today


WAITING = """
SELECT count(*) AS waiting
FROM strata.ops.lesson_review_items AS i
WHERE i.kind = 'new'
  AND NOT EXISTS (
    SELECT 1 FROM strata.ops.lesson_review_acts AS a WHERE a.item_id = i.item_id AND a.act = 'decide'
  )
"""


def within_limit(published: dt.date, decided: dt.date) -> bool:
    """Whether a lesson was decided within lesson_review.business_days business days of its report's publication,
    counted by the lesson review's own clock (strata.knowledge.lessons.review), which skips weekends and the
    holidays the thresholds file lists."""
    from strata.knowledge.lessons.review import business_days_between

    holidays = frozenset(dt.date.fromisoformat(str(day)) for day in _value("lesson_review.holidays"))
    days = business_days_between(published + dt.timedelta(days=1), decided, holidays)
    return days <= int(_value("lesson_review.business_days"))


def decisions(engine: Engine, start: dt.date, today: dt.date) -> dict:
    """The knowledge loop's leading indicator over a period: decisions, the median days (from the fewest cases for
    one), and how many came within the limit."""
    rows = _rows(engine, "kpi_days_to_decision", start, today)
    fewest = int(_value(load_kpis()["days_to_decision"].fewest))
    days = [int(row["days_from_publication"]) for row in rows]
    return {"n": len(rows), "median": _whole(statistics.median(days)) if len(days) >= fewest else None,
            "k": sum(within_limit(_date(row["published_on"]), _date(row["decided_on"])) for row in rows),
            "latest": _date(rows[0]["decided_on"]) if rows else None}


def knowledge(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """Lessons decided in the 90 days to today, and the hindsight test, in ticket 34's own words (section 7.3)."""
    from strata.estimates import hindsight

    found = decisions(engine, today - dt.timedelta(days=89), today)
    day = say.day(today, today)
    if found["median"] is not None:
        text = say.fill(say.at("dash.ai.find.knowledge.many"), day=day, n=found["n"],
                        median=say.Unit(str(found["median"])), k=found["k"])
    elif found["n"]:
        text = say.say("dash.ai.find.knowledge.few", "n", day=day, n=found["n"], k=found["k"])
    else:
        text = say.fill(say.at("dash.ai.find.knowledge.none"), day=day)
        waiting = int(engine.run(WAITING).rows[0][0] or 0)
        if waiting:
            text += " " + say.say("dash.ai.find.knowledge.waiting", "waiting", waiting=waiting)
    return text + " " + hindsight.report_sentence(hindsight.stored_release(engine)), today


def _held_out(engine: Engine, today: dt.date) -> tuple[dict | None, dict | None]:
    """The latest evaluation's held-out set, the one with the most queries, and the run before it."""
    rows = [row for row in _rows(engine, "kpi_precision_recall", EPOCH, today) if row["segment_kind"] == "held_out"]
    runs = list(dict.fromkeys(row["run_id"] for row in rows))

    def best(run_id):
        return max((row for row in rows if row["run_id"] == run_id), key=lambda row: row["queries"] or 0)

    return (best(runs[0]) if runs else None), (best(runs[1]) if len(runs) > 1 else None)


def last_finished_week(today: dt.date) -> dt.date:
    """The Sunday that ends the latest week the retrieval run measures in full, by today (ticket 32's weeks start on
    Monday), so "the 7 days to {day}" names a finished week and never one still under way."""
    return today - dt.timedelta(days=(today.weekday() + 1) % 7)


def retrieval(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """Precision and recall on the held-out set, and the week's passage reports (section 7.3, Retrieval loop)."""
    latest, _ = _held_out(engine, today)
    fewest = int(_value(load_kpis()["precision_recall"].fewest))
    if latest is None:
        text, measured = say.at("dash.ai.find.retrieval.none"), None
    elif (latest["queries"] or 0) < fewest:
        text, measured = say.fill(say.at("dash.ai.find.retrieval.fewQueries"), queries=int(latest["queries"] or 0)), \
            _date(latest["run_on"])
    else:
        measured = _date(latest["run_on"])
        text = say.fill(say.at("dash.ai.find.retrieval.evaluated"), day=say.day(measured, today),
                        p=say.Unit(f"{latest['precision_at_10']:.2f}"), r=say.Unit(f"{latest['recall_at_20']:.2f}"))
    end = last_finished_week(today)
    weeks = _rows(engine, "kpi_wrong_passage_rate", end - dt.timedelta(days=6), end - dt.timedelta(days=6))
    week = weeks[0] if weeks else None
    if week is None or not week["opened"]:
        text += " " + say.fill(say.at("dash.ai.find.retrieval.nothingOpened"), day=say.day(end, today))
    else:
        wrong, not_useful = int(week["wrong_passage"]), int(week["not_useful"])
        slots = {"day": say.day(end, today), "opened": int(week["opened"]), "wrong": _none_or(wrong),
                 "notUseful": _none_or(not_useful)}
        text += " " + (say.say("dash.ai.find.retrieval.feedback", "count", count=wrong,
                               rate=say.Unit(week["wrong_per_100_cell"]), **slots)
                       if week["wrong_per_100"] is not None else
                       say.say("dash.ai.find.retrieval.feedbackFew", "opened", **slots))
        measured = measured or end
    return text, measured


RETRAIN = """
SELECT raised_on
FROM strata.ops.retrain_triggers
WHERE reason = 'coverage_outside' AND raised_on BETWEEN :date_from AND :date_to
ORDER BY raised_at DESC
LIMIT 1
"""


def coverage(engine: Engine, today: dt.date) -> dict | None:
    """The estimates loop's leading indicator: the latest month's coverage, its share by DESIGN.md's rules, and how
    many months in a row it has been outside the target."""
    rows = _rows(engine, "kpi_rolling_coverage", EPOCH, today)
    if not rows:
        return None
    low, high = float(_value("time_estimate.coverage_low")), float(_value("time_estimate.coverage_high"))
    fewest, percent_from = int(_value("data_readiness.fewest_for_a_share")), int(
        _value("data_readiness.fewest_for_a_percentage"))
    outside = 0
    for row in rows:
        finished, inside = int(row["finished"] or 0), int(row["inside"] or 0)
        if finished < fewest or low <= inside / finished <= high:
            break
        outside += 1
    latest = rows[0]
    finished, inside = int(latest["finished"] or 0), int(latest["inside"] or 0)
    return {"month": _date(latest["month"]), "finished": finished, "inside": inside, "outside_months": outside,
            "pct": _percent(inside, finished) if finished >= percent_from else None,
            "in10": _whole(Decimal(inside) * 10 / Decimal(finished)) if fewest <= finished < percent_from else None,
            "enough": finished >= fewest, "low": _whole(low * 100), "high": _whole(high * 100)}


def accuracy(engine: Engine, today: dt.date) -> dict | None:
    """Plan accuracy in countries using Strata: rows dated within 14 days of a date offered against other rows."""
    rows = {row["segment"]: row for row in _rows(engine, "kpi_plan_accuracy", EPOCH, today)}
    if not rows:
        return None
    anchored, other = rows.get("anchored/using_strata") or {}, rows.get("other/using_strata") or {}
    return {"a": _whole(anchored.get("median_days")), "b": _whole(other.get("median_days")),
            "n": int(anchored.get("with_actual") or 0)}


def estimates(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """Coverage of the 8-in-10 range over 12 months, against its target, a retrain, and plan accuracy (7.3)."""
    found = coverage(engine, today)
    if found is None:
        return say.at("dash.ai.find.estimates.none"), None
    month = say.month_name(found["month"])
    slots = {"finished": found["finished"], "inside": found["inside"], "month": month}
    if found["pct"] is not None:
        text = say.fill(say.at("dash.ai.find.estimates.percent"), pct=say.Unit(str(found["pct"])), **slots)
    elif found["in10"] is not None:
        text = say.fill(say.at("dash.ai.find.estimates.inTen"), in10=say.Unit(str(found["in10"])), **slots)
    else:
        text = say.fill(say.at("dash.ai.find.estimates.few"), **slots)
    edges = {"low": say.Unit(str(found["low"])), "high": say.Unit(str(found["high"]))}
    if found["enough"]:
        text += " " + (say.fill(say.at("dash.ai.find.estimates.inside"), **edges) if not found["outside_months"]
                       else say.say("dash.ai.find.estimates.outside", "months", months=found["outside_months"],
                                    **edges))
    raised = engine.run(RETRAIN, {"date_from": today - dt.timedelta(days=45), "date_to": today}).rows
    if raised:
        months = int(_value("estimates_loop.coverage_outside_months"))
        text += " " + say.say("dash.ai.find.estimates.retrain", "months", day=say.day(_date(raised[0][0]), today),
                              months=months)
    plans = accuracy(engine, today)
    if plans is not None:
        text += " " + (say.fill(say.at("dash.ai.find.estimates.accuracy"), a=say.Unit(str(plans["a"])),
                                b=say.Unit(str(plans["b"])))
                       if plans["a"] is not None and plans["b"] is not None
                       else say.say("dash.ai.find.estimates.accuracyFew", "n", n=plans["n"]))
    return text, found["month"]


def adoption(engine: Engine, today: dt.date) -> tuple[str, dt.date | None]:
    """Who used Strata in the last full week, drafts checked and exported in 90 days, and plan rows (7.3)."""
    users = _rows(engine, "kpi_weekly_users", EPOCH, today)[0]
    week = say.day(_date(users["week_start"]), today)
    people = int(users["numerator"] or 0)
    if not people:
        return say.fill(say.at("dash.ai.find.adoption.none"), week=week), today
    weeks = _rows(engine, "use_by_week", today - dt.timedelta(days=89), today)
    text = say.say("dash.ai.find.adoption.used", "people", week=week, people=people, day=say.day(today, today),
                   checked=sum(int(row["checked"]) for row in weeks), exported=sum(int(row["exported"]) for row in weeks))
    plans = _rows(engine, "kpi_plan_rows_offered", EPOCH, today)[0]
    if plans["denominator"]:
        text += " " + say.fill(say.at("dash.ai.find.adoption.planRows"), rows=int(plans["denominator"]),
                               anchored=int(plans["numerator"] or 0))
    return text, today


# ── The sections, in each page's order ───────────────────────────────────

Section = Callable[[Engine, dt.date], tuple[str, "dt.date | None"]]
SECTIONS: dict[str, tuple[str, str, Section]] = {
    # key: (page, about's copy key, the function that writes it)
    "runs": ("governance", "dash.gov.about.runs", runs),
    "spend": ("governance", "dash.gov.about.spend", spend),
    "personal": ("governance", "dash.gov.about.personal", personal),
    "queries": ("governance", "dash.gov.about.queries", queries),
    "lineage": ("governance", "dash.gov.about.lineage", lineage),
    "benchmark": ("ai", "dash.ai.about.benchmark", benchmark),
    "foundry": ("ai", "dash.ai.about.foundry", foundry),
    "checks": ("ai", "dash.ai.about.checks", checks),
    "knowledge": ("ai", "dash.ai.about.knowledge", knowledge),
    "retrieval": ("ai", "dash.ai.about.retrieval", retrieval),
    "estimates": ("ai", "dash.ai.about.estimates", estimates),
    "adoption": ("ai", "dash.ai.about.adoption", adoption),
}


# ── Each loop's indicators (tile 19) ─────────────────────────────────────

def indicators(engine: Engine, today: dt.date) -> list[tuple[str, str, str, str, dt.date | None]]:
    """The six rows of tile 19, in loop order: (kpi, latest, target, against, measured on), each in words."""
    cells = "dash.ai.cells"
    none_set, not_compared, none_yet = (say.at(f"dash.ai.{key}") for key in ("noneSet", "notCompared", "noneYet"))
    found = []

    found_decisions = decisions(engine, today - dt.timedelta(days=89), today)
    n = found_decisions["n"]
    latest = (none_yet if not n else say.fill(say.at(f"{cells}.decisionsMany"), numerals=True, n=n,
                                              median=say.Unit(str(found_decisions["median"])))
              if found_decisions["median"] is not None else say.say(f"{cells}.decisionsFew", "n", numerals=True, n=n))
    found.append(("days_to_decision", latest, say.at(f"{cells}.decisionsTarget"),
                  say.fill(say.at(f"{cells}.decisionsAgainst"), numerals=True, k=found_decisions["k"], n=n) if n
                  else not_compared, found_decisions["latest"]))

    releases = _rows(engine, "kpi_blamed_covered", EPOCH, today)
    found.append(("blamed_covered", say.fill(say.at(f"{cells}.blamed"), numerals=True,
                                             covered=int(releases[0]["covered"] or 0),
                                             blamed=int(releases[0]["blamed"] or 0)) if releases else none_yet,
                  none_set, not_compared, _date(releases[0]["ran_on"]) if releases else None))

    weeks = _rows(engine, "kpi_wrong_passage_rate", EPOCH, today)
    if weeks:
        week = weeks[0]
        latest = (say.fill(say.at(f"{cells}.wrongMany"), numerals=True, rate=say.Unit(f"{week['wrong_per_100']:.1f}"),
                           opened=int(week["opened"]))
                  if week["wrong_per_100"] is not None else
                  say.fill(say.at(f"{cells}.wrongFew"), numerals=True, reports=int(week["wrong_passage"]),
                           opened=int(week["opened"])))
        found.append(("wrong_passage_rate", latest, none_set, not_compared, _date(week["week_start"])))
    else:
        found.append(("wrong_passage_rate", none_yet, none_set, not_compared, None))

    held_out, before = _held_out(engine, today)
    fewest = int(_value(load_kpis()["precision_recall"].fewest))
    if held_out is None:
        found.append(("precision_recall", none_yet, say.at(f"{cells}.scoresTarget"), not_compared, None))
    elif (held_out["queries"] or 0) < fewest:
        found.append(("precision_recall", say.fill(say.at(f"{cells}.scoresFew"), numerals=True,
                                                   queries=int(held_out["queries"] or 0)),
                      say.at(f"{cells}.scoresTarget"), not_compared, _date(held_out["run_on"])))
    else:
        against = not_compared if before is None or (before["queries"] or 0) < fewest else say.at(
            f"{cells}.scoresMatched" if held_out["precision_at_10"] >= before["precision_at_10"]
            and held_out["recall_at_20"] >= before["recall_at_20"] else f"{cells}.scoresLower")
        found.append(("precision_recall", say.fill(say.at(f"{cells}.scores"), numerals=True,
                                                   p=say.Unit(f"{held_out['precision_at_10']:.2f}"),
                                                   r=say.Unit(f"{held_out['recall_at_20']:.2f}")),
                      say.at(f"{cells}.scoresTarget"), against, _date(held_out["run_on"])))

    covered = coverage(engine, today)
    target = say.fill(say.at(f"{cells}.coverageTarget"), numerals=True, low=say.Unit(str(_whole(
        float(_value("time_estimate.coverage_low")) * 100))), high=say.Unit(str(_whole(
            float(_value("time_estimate.coverage_high")) * 100))))
    if covered is None:
        found.append(("rolling_coverage", none_yet, target, not_compared, None))
    else:
        slots = {"inside": covered["inside"], "finished": covered["finished"]}
        latest = (say.fill(say.at(f"{cells}.coveragePercent"), numerals=True, pct=say.Unit(str(covered["pct"])), **slots)
                  if covered["pct"] is not None else
                  say.fill(say.at(f"{cells}.coverageInTen"), numerals=True, in10=say.Unit(str(covered["in10"])), **slots)
                  if covered["in10"] is not None else say.fill(say.at(f"{cells}.coverageFew"), numerals=True, **slots))
        against = (say.at(f"{cells}.coverageTooFew") if not covered["enough"]
                   else say.at(f"{cells}.coverageInside") if not covered["outside_months"]
                   else say.say(f"{cells}.coverageOutside", "months", numerals=True, months=covered["outside_months"]))
        found.append(("rolling_coverage", latest, target, against, covered["month"]))

    plans = accuracy(engine, today)
    if plans is None:
        found.append(("plan_accuracy", none_yet, none_set, not_compared, None))
    else:
        latest = (say.fill(say.at(f"{cells}.accuracyBoth"), numerals=True, a=say.Unit(str(plans["a"])),
                           b=say.Unit(str(plans["b"])))
                  if plans["a"] is not None and plans["b"] is not None
                  else say.say(f"{cells}.accuracyFew", "n", numerals=True, n=plans["n"]))
        months = _rows(engine, "kpi_rolling_coverage", EPOCH, today)
        found.append(("plan_accuracy", latest, none_set, not_compared, _date(months[0]["month"]) if months else None))
    return found


# ── Writing ──────────────────────────────────────────────────────────────

def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def write(engine: Engine, run_id: str, clock: Callable[[], dt.datetime] = _now,
          sections: tuple[str, ...] | None = None) -> int:
    """Write each section's sentence, and with every section each loop's indicators, as of today in UTC. Returns how
    many rows it wrote."""
    written_at = clock()
    today = written_at.astimezone(dt.UTC).date()
    chosen = sections or tuple(SECTIONS)
    rows = []
    for position_key, (page, about, section) in SECTIONS.items():
        if position_key not in chosen:
            continue
        try:
            text, measured = section(engine, today)
        except Exception:  # noqa: BLE001 - one section that can't be measured must not stop the nightly task
            LOG.exception("The %s finding could not be written, so its row is left out tonight.", position_key)
            continue
        position = [key for key, entry in SECTIONS.items() if entry[0] == page].index(position_key) + 1
        rows.append((run_id, page, position_key, position, say.at(about), text, measured, written_at, today))
    count = engine.insert_rows(FINDINGS, FINDING_COLUMNS, rows) if rows else 0
    if sections is None:
        try:
            measured_indicators = indicators(engine, today)
        except Exception:  # noqa: BLE001 - as with a section, the task goes on without them
            LOG.exception("Each loop's indicators could not be written, so they are left out tonight.")
            return count
        kpis = load_kpis()
        names = say.at("dash.ai.loops")
        kinds = say.at("dash.ai.kind")
        cells = [(run_id, position, kpi, names[kpis[kpi].loop], say.at(kpis[kpi].copy_keys[0]), kinds[kpis[kpi].role],
                  latest, target, against, measured, written_at, today)
                 for position, (kpi, latest, target, against, measured) in enumerate(measured_indicators, 1)]
        count += engine.insert_rows(INDICATORS, INDICATOR_COLUMNS, cells)
    return count
