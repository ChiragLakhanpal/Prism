"""The estimates loop's monthly watch (ticket 44; docs/PLAN.md section 11, "Three loops" and "Retraining").

Once a month, from the nightly job's score task, the watch measures how Strata's ranges are doing and what they do
to the plans they inform, as of the last day of the month, and stores every measure as a count with its denominator
in strata.ops (the 45 design brief, sections 7.3 and 7.4):

- Plan rows dated within estimates_loop.anchored_within_days of a date Strata offered. A plan row is one Signed
  Contract Planned date in one plan version. It counts when its version was published after an exposure of its
  package (strata.ops.exposures, ticket 44's one definition of an exposure), and it is dated within the window when
  its planned signing date is that close to the middle or the 8-in-10 point that exposure offered. Each such row
  goes to strata.ops.anchored_plan_rows, with the nearest offered date.
- Plan accuracy and duration, for four groups: rows dated within the window of a date offered and all other rows,
  each split by whether the row's country was using Strata when its plan was published (config/slice.toml's
  [[onboarded]]). Plan accuracy is the median days between a row's planned signing date and the package's actual
  one, early or late; duration is the median months from the package's first notice to its signing (procurement
  cycle time). The actual dates come from strata.gold.package, never from a plan's Actual column.
- Rolling coverage: of the packages that finished in the estimates_loop.coverage_window_months to the month, those
  inside the 8-in-10 range Strata gave them before their first notice (the champion's batch score), out of those it
  gave one; and on the same packages the typical error of the time estimate's middle and of the past range's middle
  as find_comparables gave it on the notice's day.
- The input mix: for each input in estimates_loop.drift_inputs, Pearson's chi-square test of the mix the champion
  learned from against the packages advertised in the month.

Every median, statistic and share is kept only from estimates_loop.min_cases cases; below that the row keeps its
counts and says too_few_cases (the 45 design brief, decision 14).

decide() then raises a retrain, with a reason code, in strata.ops.retrain_triggers: coverage outside the band for
coverage_outside_months months in a row, the error more than error_trail_share behind the past range's, an input's
mix drifting, or a new edition of the procurement rules taking effect in the month (config/editions.toml's
effective_from), which first starts a re-check of each current lesson of another edition (ticket 29's being
re-checked state) and marks the champion as being re-checked (strata.ops.model_states). run() is the score task's:
it watches each whole month not watched yet, so a rerun watches nothing twice. retrain_due() says when the score task
retrains, quarterly or after a trigger.
"""

from __future__ import annotations

import datetime as dt
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from importlib import resources

from strata.config import Edition, Editions, Slice, Thresholds, load_slice, load_thresholds
from strata.estimates.past_range import months
from strata.lakehouse.engine import Engine

WATCH_TABLE = "strata.ops.estimates_watch"
WATCH_COLUMNS = ("run_id", "month", "measure", "segment", "count", "denominator", "value", "detail", "reason",
                 "measured_at", "public_from")
MARKS_TABLE = "strata.ops.anchored_plan_rows"
MARKS_COLUMNS = ("run_id", "month", "document_id", "project_id", "step_reference", "published_on",
                 "planned_signing_on", "exposure_id", "exposed_on", "offered_on", "days_from_offered", "anchored",
                 "country_code", "using_strata", "contract_signed_on", "days_from_plan", "measured_at", "public_from")
TRIGGERS_TABLE = "strata.ops.retrain_triggers"
TRIGGERS_COLUMNS = ("run_id", "month", "reason", "edition_key", "detail", "model", "raised_on", "raised_at",
                    "public_from")
STATES_TABLE = "strata.ops.model_states"
STATES_COLUMNS = ("model", "version", "state", "reason", "edition_key", "run_id", "since", "marked_at", "public_from")
RECHECKING = "rechecking"  # ticket 29's word for a lesson being re-checked, used for a model too
TOO_FEW = "too_few_cases"
GROUPS = ("anchored", "other")
COUNTRIES = ("using_strata", "not_yet")
CHAMPION = "champion"
# The columns of strata.gold.package whose mix the drift test may compare (estimates_loop.drift_inputs).
INPUTS = ("procurement_category", "procurement_method", "review_type")


def _sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "loop" / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


@dataclass(frozen=True)
class Settings:
    """The watch's settings, from config/thresholds.toml's [estimates_loop]."""

    within_days: int
    min_cases: int
    coverage_window_months: int
    coverage_outside_months: int
    error_trail_share: float
    drift_alpha: float
    drift_inputs: tuple[str, ...]

    @classmethod
    def read(cls, thresholds: Thresholds) -> Settings:
        value = thresholds.value
        inputs = tuple(value("estimates_loop.drift_inputs"))
        unknown = [name for name in inputs if name not in INPUTS]
        if unknown or not inputs:
            raise ValueError(f"estimates_loop.drift_inputs must name some of {', '.join(INPUTS)}, "
                             f"not {', '.join(unknown) or 'none'}.")
        return cls(int(value("estimates_loop.anchored_within_days")), int(value("estimates_loop.min_cases")),
                   int(value("estimates_loop.coverage_window_months")),
                   int(value("estimates_loop.coverage_outside_months")),
                   float(value("estimates_loop.error_trail_share")), float(value("estimates_loop.drift_alpha")),
                   inputs)


# ── Plan rows and the dates Strata offered ──────────────────────────────

def marked_rows(engine: Engine, month: dt.date, settings: Settings, chosen: Slice) -> list[dict]:
    """Every plan row public by month, each with the nearest date an earlier exposure of its package offered (or
    none), whether it is dated within the window of it, its country's onboarding and its days from plan."""
    from strata.tools.check_plan import SIGNING

    offers: dict[str, list[dict]] = defaultdict(list)
    for exposure in _rows(engine, "exposures", as_of=month):
        for column in ("offered_middle_on", "offered_eight_in_ten_on"):
            if exposure[column] is not None:
                offers[exposure["step_reference"]].append({"exposure_id": exposure["exposure_id"],
                                                           "exposed_on": _date(exposure["exposed_on"]),
                                                           "offered_on": _date(exposure[column])})
    found = []
    for row in _rows(engine, "plan_rows", as_of=month, signed_step=SIGNING):
        planned, published = _date(row["planned_signing_on"]), _date(row["published_on"])
        signed, notice = _date(row["contract_signed_on"]), _date(row["first_notice_date"])
        earlier = [offer for offer in offers.get(row["step_reference"], []) if offer["exposed_on"] < published]
        nearest = min(earlier, key=lambda offer: (abs((planned - offer["offered_on"]).days), offer["exposed_on"],
                                                  offer["exposure_id"]), default=None)
        apart = None if nearest is None else abs((planned - nearest["offered_on"]).days)
        found.append({**row, "planned_signing_on": planned, "published_on": published, "contract_signed_on": signed,
                      "first_notice_date": notice, "offer": nearest, "days_from_offered": apart,
                      "anchored": apart is not None and apart <= settings.within_days,
                      "using_strata": chosen.using_strata(row["country_code"], published),
                      "days_from_plan": None if signed is None else abs((signed - planned).days),
                      "cycle_days": None if signed is None or notice is None or signed < notice
                      else (signed - notice).days})
    return found


def _median_measure(run_id: str, month: dt.date, measure: str, segment: str, values: list, denominator: int,
                    settings: Settings, measured_at: dt.datetime, detail: dict | None = None) -> tuple:
    enough = len(values) >= settings.min_cases
    middle = float(statistics.median(values)) if enough else None
    return _watch_row(run_id, month, measure, segment, len(values), denominator, middle, detail,
                      None if enough else TOO_FEW, measured_at)


def _watch_row(run_id, month, measure, segment, count, denominator, value, detail, reason, measured_at) -> tuple:
    return (run_id, month, measure, segment, count, denominator, value,
            None if detail is None else json.dumps(detail, sort_keys=True, default=str), reason, measured_at,
            measured_at.astimezone(dt.UTC).date())


def plan_measures(run_id: str, month: dt.date, marked: list[dict], settings: Settings,
                  measured_at: dt.datetime) -> list[tuple]:
    """Plan accuracy and duration for each group and country, and the share of rows after an exposure that were
    dated within the window of a date offered, overall and among rows published in the month."""
    found = []
    for group in GROUPS:
        for country in COUNTRIES:
            segment = [row for row in marked if (row["anchored"]) == (group == "anchored")
                       and row["using_strata"] == (country == "using_strata")]
            name = f"{group}/{country}"
            found.append(_median_measure(run_id, month, "plan_accuracy", name,
                                         [row["days_from_plan"] for row in segment if row["days_from_plan"] is not None],
                                         len(segment), settings, measured_at, {"unit": "days"}))
            found.append(_median_measure(run_id, month, "plan_duration", name,
                                         [float(months(row["cycle_days"])) for row in segment
                                          if row["cycle_days"] is not None],
                                         len(segment), settings, measured_at, {"unit": "months"}))
    after = [row for row in marked if row["offer"] is not None]
    start = month.replace(day=1)
    for segment, chosen in (("all", after), ("published_in_month", [row for row in after
                                                                   if start <= row["published_on"] <= month])):
        found.append(_watch_row(run_id, month, "anchored_rows", segment, sum(row["anchored"] for row in chosen),
                                len(chosen), None, None, None, measured_at))
    return found


def _mark_row(run_id: str, month: dt.date, row: dict, measured_at: dt.datetime) -> tuple:
    offer = row["offer"]
    values = {"run_id": run_id, "month": month, "document_id": row["document_id"], "project_id": row["project_id"],
              "step_reference": row["step_reference"], "published_on": row["published_on"],
              "planned_signing_on": row["planned_signing_on"], "exposure_id": offer["exposure_id"],
              "exposed_on": offer["exposed_on"], "offered_on": offer["offered_on"],
              "days_from_offered": row["days_from_offered"], "anchored": row["anchored"],
              "country_code": row["country_code"], "using_strata": row["using_strata"],
              "contract_signed_on": row["contract_signed_on"], "days_from_plan": row["days_from_plan"],
              "measured_at": measured_at, "public_from": measured_at.astimezone(dt.UTC).date()}
    return tuple(values[column] for column in MARKS_COLUMNS)


# ── Coverage and error, on the packages that finished ───────────────────

def champion(engine: Engine, as_of: dt.date) -> dict | None:
    """The time estimate's champion as public on a day, without its trees, or None before the first."""
    from strata.config import load_time_estimate

    found = _rows(engine, "champion", model=load_time_estimate().registered_model, alias=CHAMPION, as_of=as_of)
    return found[0] if found else None


def finished_measures(engine: Engine, run_id: str, month: dt.date, settings: Settings, thresholds: Thresholds,
                      measured_at: dt.datetime) -> list[tuple]:
    """Rolling coverage of the 8-in-10 range, and the typical errors of the time estimate's middle and the past
    range's middle, on the packages that finished in the coverage window to month and got a range before their
    first notice. The past range is find_comparables' as Strata would have shown it on that notice's day, through a
    reader frozen there (the replay harness's, so nothing published later reaches it)."""
    from strata.estimates.harness import Reader
    from strata.tools.project_signals import months_before

    window_start = months_before(month, settings.coverage_window_months)
    finished = _rows(engine, "finished", window_start=window_start, as_of=month, alias=CHAMPION)
    given = [row for row in finished if row["q80_days"] is not None]
    inside = 0
    errors: list[tuple[float, float]] = []
    for row in given:
        notice, signed = _date(row["first_notice_date"]), _date(row["contract_signed_on"])
        days = (signed - notice).days
        inside += days <= int(row["q80_days"])
        past = Reader(engine, notice, thresholds).call("find_comparables", step_reference=row["step_reference"])
        middle = ((past.get("past_range") or {}).get("days") or {}).get("q50")
        if middle is not None and row["q50_days"] is not None:
            errors.append((float(months(abs(days - int(row["q50_days"])))), float(months(abs(days - int(middle))))))
    enough = len(given) >= settings.min_cases
    detail = {"window_start": window_start.isoformat(), "finished": len(finished), "given": len(given)}
    found = [_watch_row(run_id, month, "coverage", "all", inside, len(given), None, detail,
                        None if enough else TOO_FEW, measured_at)]
    for index, measure_name in enumerate(("error_estimate", "error_past_range")):
        found.append(_median_measure(run_id, month, measure_name, "all", [pair[index] for pair in errors],
                                     len(given), settings, measured_at, {"unit": "months"}))
    return found


# ── The input mix ────────────────────────────────────────────────────────

def _regularized_upper_gamma(a: float, x: float) -> float:
    """Q(a, x), the regularized upper incomplete gamma function, by its series below a + 1 and its continued
    fraction above (Press and others, Numerical Recipes, section 6.2). The chi-square p-value is Q(dof / 2, x / 2)."""
    import math

    if x <= 0:
        return 1.0
    log_front = -x + a * math.log(x) - math.lgamma(a)
    if x < a + 1:
        term = total = 1.0 / a
        n = a
        while abs(term) > abs(total) * 1e-15:
            n += 1
            term *= x / n
            total += term
        return max(0.0, 1.0 - total * math.exp(log_front))
    tiny = 1e-300
    b, c, d = x + 1 - a, 1 / tiny, 1 / (x + 1 - a)
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        step = d * c
        h *= step
        if abs(step - 1) < 1e-15:
            break
    return min(1.0, math.exp(log_front) * h)


def chi_square(learned: dict[str, int], recent: dict[str, int]) -> tuple[float, int, float]:
    """Pearson's chi-square test of homogeneity of two count vectors over the same categories, with no continuity
    correction: the statistic, its degrees of freedom and its p-value."""
    categories = [key for key in sorted(set(learned) | set(recent)) if learned.get(key, 0) + recent.get(key, 0) > 0]
    rows = [[learned.get(key, 0) for key in categories], [recent.get(key, 0) for key in categories]]
    total = sum(map(sum, rows))
    statistic = 0.0
    for row in rows:
        for column, observed in enumerate(row):
            expected = sum(row) * (rows[0][column] + rows[1][column]) / total
            statistic += (observed - expected) ** 2 / expected
    freedom = len(categories) - 1
    return statistic, freedom, _regularized_upper_gamma(freedom / 2, statistic / 2) if freedom > 0 else 1.0


def mix_measures(engine: Engine, run_id: str, month: dt.date, settings: Settings,
                 measured_at: dt.datetime) -> list[tuple]:
    """For each input in estimates_loop.drift_inputs, the champion's training mix (packages advertised before its
    training date) against the mix of packages advertised in the month, by Pearson's chi-square test."""
    held = champion(engine, month)
    packages = _rows(engine, "input_mix", as_of=month)
    start = month.replace(day=1)
    found = []
    for name in settings.drift_inputs:
        if held is None:
            found.append(_watch_row(run_id, month, "input_mix", name, None, None, None, None, "no_model", measured_at))
            continue
        trained = _date(held["training_through"])
        learned, recent = defaultdict(int), defaultdict(int)
        for row in packages:
            notice, value = _date(row["first_notice_date"]), row[name]
            if value is None:
                continue
            if notice < trained:
                learned[str(value)] += 1
            elif start <= notice <= month:
                recent[str(value)] += 1
        count, denominator = sum(recent.values()), sum(learned.values())
        if count < settings.min_cases or denominator < settings.min_cases:
            found.append(_watch_row(run_id, month, "input_mix", name, count, denominator, None, None, TOO_FEW,
                                    measured_at))
            continue
        statistic, freedom, p_value = chi_square(learned, recent)
        found.append(_watch_row(run_id, month, "input_mix", name, count, denominator, statistic,
                                {"degrees_of_freedom": freedom, "p_value": p_value, "learned": dict(learned),
                                 "recent": dict(recent), "model_version": int(held["version"])}, None, measured_at))
    return found


# ── The watch ────────────────────────────────────────────────────────────

def measure(engine: Engine, month: dt.date, run_id: str, measured_at: dt.datetime, *,
            thresholds: Thresholds | None = None, chosen: Slice | None = None) -> int:
    """Measure one month, as of its last day, and append the rows. Returns how many it wrote."""
    thresholds = thresholds or load_thresholds()
    settings = Settings.read(thresholds)
    chosen = chosen or load_slice()
    marked = marked_rows(engine, month, settings, chosen)
    marks = [_mark_row(run_id, month, row, measured_at) for row in marked if row["offer"] is not None]
    measures = (plan_measures(run_id, month, marked, settings, measured_at)
                + finished_measures(engine, run_id, month, settings, thresholds, measured_at)
                + mix_measures(engine, run_id, month, settings, measured_at))
    written = engine.insert_rows(MARKS_TABLE, MARKS_COLUMNS, marks) if marks else 0
    return written + engine.insert_rows(WATCH_TABLE, WATCH_COLUMNS, measures)


# ── The retrain triggers ─────────────────────────────────────────────────

def _month_before(month: dt.date) -> dt.date:
    return month.replace(day=1) - dt.timedelta(days=1)


def _outside(row: dict, low: Fraction, high: Fraction, least: int) -> bool:
    """Whether a month's coverage, from enough packages, fell outside the band."""
    if row is None or row["denominator"] is None or int(row["denominator"]) < least:
        return False
    share = Fraction(int(row["count"]), int(row["denominator"]))
    return not low <= share <= high


def triggered(series: dict[dt.date, dict[tuple[str, str], dict]], month: dt.date, settings: Settings,
              thresholds: Thresholds) -> list[tuple[str, dict]]:
    """The retrain triggers the watched months' measures raise for month, each with its reason code and the
    counts behind it: coverage outside the band for coverage_outside_months months in a row, the estimate's error
    more than error_trail_share behind the past range's, and an input whose mix drifted."""
    found = []
    low = Fraction(str(thresholds.value("time_estimate.coverage_low")))
    high = Fraction(str(thresholds.value("time_estimate.coverage_high")))
    months_in_a_row, day = [], month
    for _ in range(settings.coverage_outside_months):
        months_in_a_row.append((series.get(day) or {}).get(("coverage", "all")))
        day = _month_before(day)
    if all(_outside(row, low, high, settings.min_cases) for row in months_in_a_row):
        found.append(("coverage_outside", {"months": [{"month": row["month"], "inside": int(row["count"]),
                                                       "finished": int(row["denominator"])} for row in months_in_a_row]}))
    current = series.get(month) or {}
    estimate, past = current.get(("error_estimate", "all")), current.get(("error_past_range", "all"))
    if estimate and past and estimate["value"] is not None and past["value"] is not None:
        share = Fraction(str(settings.error_trail_share))
        if Fraction(str(estimate["value"])) > Fraction(str(past["value"])) * (1 + share):
            found.append(("error_trails_past_range", {"error_estimate_months": estimate["value"],
                                                      "error_past_range_months": past["value"],
                                                      "packages": int(estimate["count"])}))
    cut_off = settings.drift_alpha / len(settings.drift_inputs)
    drifted = [{"input": segment, "statistic": row["value"], **json.loads(row["detail"])}
               for (measure_name, segment), row in sorted(current.items())
               if measure_name == "input_mix" and row["value"] is not None
               and json.loads(row["detail"])["p_value"] < cut_off]
    if drifted:
        found.append(("input_mix_drift", {"cut_off": cut_off, "inputs": [
            {key: item[key] for key in ("input", "statistic", "degrees_of_freedom", "p_value")} for item in drifted]}))
    return found


def _series(engine: Engine, month: dt.date) -> dict[dt.date, dict[tuple[str, str], dict]]:
    series: dict[dt.date, dict[tuple[str, str], dict]] = defaultdict(dict)
    for row in _rows(engine, "watched", month=month):
        series[_date(row["month"])][(row["measure"], row["segment"])] = {**row, "month": _date(row["month"]).isoformat()}
    return series


def recheck_lessons(engine: Engine, edition: Edition, run_id: str, at: dt.datetime) -> list[str]:
    """Start a re-check (ticket 29's being re-checked state, origin edition) of every current lesson tagged with
    another edition or with none, unless one is already open. Returns the lessons it marked."""
    from strata.knowledge.lessons.propose import item_id
    from strata.knowledge.lessons.review import ITEM_COLUMNS, Store

    store = Store(engine)
    regions = {row["project_id"]: row["region"] for row in _rows(engine, "project_regions")}
    day = at.astimezone(dt.UTC).date()
    marked, items = [], []
    for lesson_id in sorted(store.versions):
        latest = store.latest(lesson_id)
        key = item_id("recheck", f"{lesson_id}|edition|{edition.key}")
        if (latest["state"] != "current" or latest["edition_key"] == edition.key or store.open_recheck(lesson_id)
                or key in store.items):
            continue
        project = latest["project_id"]
        region = (store.projects.get(project) or {}).get("region") or regions.get(project)
        if region is None:  # no region's reviewers could act on it; the next watch tries again
            continue
        item = {"item_id": key, "kind": "recheck", "proposal_id": None, "lesson_id": lesson_id,
                "version": int(latest["version"]), "decided_item_id": None, "project_id": project, "region": region,
                "decided_region": None, "origin": "edition", "origin_by": None, "origin_by_name": None,
                "origin_reason": edition.key, "origin_item_id": None, "entered_on": day, "due_on": None,
                "created_at": at, "public_from": day}
        items.append(tuple(item[column] for column in ITEM_COLUMNS))
        marked.append(lesson_id)
    if items:
        engine.insert_rows("strata.ops.lesson_review_items", ITEM_COLUMNS, items)
    return marked


def recheck_model(engine: Engine, edition: Edition, month: dt.date, run_id: str, at: dt.datetime) -> dict | None:
    """Mark the time estimate's champion as being re-checked for an edition, or None when there is no champion."""
    held = champion(engine, month)
    if held is None:
        return None
    day = at.astimezone(dt.UTC).date()
    engine.insert_rows(STATES_TABLE, STATES_COLUMNS, [(held["model"], int(held["version"]), RECHECKING, "new_edition",
                                                       edition.key, run_id, day, at, day)])
    return {"model": held["model"], "version": int(held["version"])}


def decide(engine: Engine, month: dt.date, run_id: str, raised_at: dt.datetime, *,
           thresholds: Thresholds | None = None, editions: Editions | None = None) -> int:
    """Raise the retrains the watched months' measures call for in month, one row each in
    strata.ops.retrain_triggers. A new edition of the procurement rules that took effect in the month first marks
    the affected lessons and the champion as being re-checked. Returns how many retrains it raised."""
    from strata.config import load_editions, load_time_estimate

    thresholds = thresholds or load_thresholds()
    editions = editions or load_editions()
    settings = Settings.read(thresholds)
    model = load_time_estimate().registered_model
    raised = [(reason, None, detail) for reason, detail in triggered(_series(engine, month), month, settings, thresholds)]
    for edition in editions.editions:
        if edition.effective_from is not None and month.replace(day=1) <= edition.effective_from <= month:
            lessons = recheck_lessons(engine, edition, run_id, raised_at)
            held = recheck_model(engine, edition, month, run_id, raised_at)
            raised.append(("new_edition", edition.key, {"effective_from": edition.effective_from.isoformat(),
                                                        "lessons_rechecking": lessons, "model": held}))
    day = raised_at.astimezone(dt.UTC).date()
    rows = [(run_id, month, reason, key, json.dumps(detail, sort_keys=True, default=str), model, day, raised_at, day)
            for reason, key, detail in raised]
    return engine.insert_rows(TRIGGERS_TABLE, TRIGGERS_COLUMNS, rows) if rows else 0


def watch_month(engine: Engine, month: dt.date, run_id: str, at: dt.datetime, *,
                thresholds: Thresholds | None = None, chosen: Slice | None = None,
                editions: Editions | None = None) -> int:
    """Measure one month and raise the retrains it calls for. Returns the rows written."""
    thresholds = thresholds or load_thresholds()
    written = measure(engine, month, run_id, at, thresholds=thresholds, chosen=chosen)
    return written + decide(engine, month, run_id, at, thresholds=thresholds, editions=editions)


LAST_WATCHED = "SELECT max(w.month) AS month FROM strata.ops.estimates_watch AS w"
MOST_MONTHS = 12  # a watch that was off longer catches up on the last year only


def months_to_watch(engine: Engine, today: dt.date) -> list[dt.date]:
    """The months not watched yet, up to the last whole month before today: each month after the newest one
    watched, or only the last whole month when none was."""
    last = today.replace(day=1) - dt.timedelta(days=1)
    held = _date(engine.run(LAST_WATCHED).rows[0][0])
    found, month = [], last
    while (held is None and not found) or (held is not None and month > held):
        found.insert(0, month)
        month = _month_before(month)
    return found[-MOST_MONTHS:]


def retrain_due(engine: Engine, today: dt.date, thresholds: Thresholds | None = None) -> str | None:
    """Why the time estimate should be retrained today, or None: quarterly, when no version was registered in the
    last estimates_loop.retrain_every_months, or trigger, when the watch raised a retrain after the newest version."""
    from strata.config import load_time_estimate
    from strata.tools.project_signals import months_after

    every = int((thresholds or load_thresholds()).value("estimates_loop.retrain_every_months"))
    found = _rows(engine, "last_retrain", model=load_time_estimate().registered_model, as_of=today)[0]
    registered, raised = found["registered_at"], found["raised_at"]
    if registered is None:
        return None  # nothing trained yet: the first backtest registers the champion (ticket 25)
    registered, raised = _moment(registered), _moment(raised) if raised is not None else None
    if raised is not None and raised > registered:
        return "trigger"
    return "quarterly" if months_after(registered.date(), every) <= today else None


def _moment(value) -> dt.datetime:
    """A stored time in UTC: DuckDB gives it without a zone, the SQL warehouse as text."""
    if not isinstance(value, dt.datetime):
        value = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=dt.UTC)


def run(engine: Engine, run_id: str, now: dt.datetime, **options) -> int:
    """The nightly score task's watch: every month not watched yet, in order. A rerun on the same day watches
    nothing again. Returns the rows written."""
    return sum(watch_month(engine, month, run_id, now, **options)
               for month in months_to_watch(engine, now.astimezone(dt.UTC).date()))
