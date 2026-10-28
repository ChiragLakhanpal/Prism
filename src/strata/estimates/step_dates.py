"""A planned date for each STEP step (ticket 27): delay against the Procurement Plan, one survival model per step.

The steps come from the step-label registry (web/src/steps.ts, read here from its server copy steps.json): each
method family's steps in STEP's order, matched to the plan's tables by STEP's step name, never by a step's place
in a table, which moves when a table has prequalification columns.

How a step is dated, with its thresholds in config/thresholds.toml's [time_estimate] (CLAUDE.md rule 9):

- Each comparable package (find_comparables' rows for the same criteria) is read in its newest plan version
  public on the as-of date (sql/step_dates/steps.sql). Delay is never worked out here: it is
  silver.plan_step_delays' delay_days, the days from the step's first published planned date to its actual date,
  defined once in src/strata/lakehouse/sql/plans/plan_step_delays.sql (ticket 08).
- Basis. A package from a STEP row whose plan gives first published dates is dated on the delay basis: each
  step's date is the plan's first published date for it plus the comparables' delay at that step. A package from
  a sentence, or a STEP row whose plan gives no dates, is dated on the duration basis: its first step is the
  anchor, whose date the person gives (start_date), and each later step counts from the one before by the days
  that stretch took in the comparables, from their actual dates.
- The survival model. At each step, each comparable is one observation: its delay (or its days since the step
  before) when its plan recorded the step, or, still open, the days so far, counted as not reached yet
  (censored), so the dates do not look earlier than they were. A comparable whose plan left the step blank while
  a later step has an actual date, or that was canceled, or that has no start to count from, gives no
  observation. The curve is Kaplan-Meier (src/strata/estimates/past_range.py). The middle date is the point by
  which step_middle_share of the comparables had reached the step, the cautious date step_cautious_share. Each
  point comes with how many comparables ran later than it, and about how many in 10.
- Abstention. A step with fewer than min_comparables observations gets no date (few_comparables); one whose
  curve never reaches a point, because too many are still open, gets none either (not_reached); on the delay
  basis, a step the package's plan gives no date gets none (not_in_plan). On the duration basis a step after one
  with no date cannot be dated (needs_earlier_step), though it keeps its own days. Below min_comparables
  comparables in all, no step gets a date (abstain_all) and each keeps its count.
- Ran longest: of the comparables whose plans recorded an actual date for every step up to the family's
  longest_through step, the stage (the work leading up to a step) that took the most days in the most of them.
- No actual date of the package itself ever leaves this module: it counts the steps STEP records actual dates
  for (actual_steps_count), for the activity page that shows them.

Every number is a count or a day count at its rounding here, and every date is worked out here, so the screen
adds no days and divides nothing (CLAUDE.md rule 1).
"""

from __future__ import annotations

import datetime as dt
import json
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from functools import cache
from importlib import resources

from strata.config import Thresholds, load_thresholds, load_time_estimate
from strata.estimates import harness
from strata.estimates.harness import Replay, Score, Scored, Window
from strata.estimates.past_range import Observation, as_date, quantile, survival, whole

DELAY, DURATION = "delay", "duration"
CHOICES = ("middle", "cautious")
FEW, EARLIER, NOT_REACHED, NOT_IN_PLAN = "few_comparables", "needs_earlier_step", "not_reached", "not_in_plan"
CANCELED = "Canceled"
ENDED = (CANCELED, "Terminated")  # STEP's Process Status for an activity that stopped before its end
NO_PLAN_DATES = "no_plan_dates"
# A comparable package planned in another STEP table, whose steps differ, so it dates none of these (ticket 63).
OTHER_FAMILY = "other_family"

# A function that runs one of this module's queries as of a date: the engine's, or a replay reader's, which binds
# its own date and refuses any row made public after it (strata.estimates.harness.Reader.rows).
Rows = Callable[..., list[dict]]


@cache
def families() -> dict[str, dict]:
    """The step-label registry's families, by key, from its server copy."""
    return json.loads((resources.files("strata.estimates") / "steps.json").read_text())["families"]


def family_for(category: str | None, method: str | None, section: str | None = None) -> tuple[str | None, str | None]:
    """The registry's family for a package, as (family, None), or (None, why). A package from a plan row belongs to
    the family whose sections hold its STEP table, because STEP splits individual consultants from consulting
    firms by table and the same Method can sit in either. With no plan row, the procurement category and Method
    decide: no_family when either is missing, method_not_listed when no family lists the pair."""
    if section:
        for key, family in families().items():
            if section in family["sections"]:
                return key, None
    if not category or not method:
        return None, "no_family"
    for key, family in families().items():
        if category in family["categories"] and method in family["methods"]:
            return key, None
    return None, "method_not_listed"


def sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "step_dates" / name).read_text()


@dataclass(frozen=True)
class Settings:
    min_comparables: int
    shares: dict[str, Fraction]  # the choice's share of comparables that had reached the step by its date
    start_days_before: int
    start_days_after: int
    min_unseen: int  # a track record needs at least this many steps the backtest had not seen

    @classmethod
    def read(cls, thresholds: Thresholds) -> Settings:
        value = thresholds.value
        return cls(int(value("time_estimate.min_comparables")),
                   {"middle": Fraction(str(value("time_estimate.step_middle_share"))),
                    "cautious": Fraction(str(value("time_estimate.step_cautious_share")))},
                   int(value("time_estimate.step_start_days_before")), int(value("time_estimate.step_start_days_after")),
                   int(value("time_estimate.min_unseen_packages")))

    def in10(self, choice: str) -> int:
        """About how many in 10 comparables ran later than the choice's date, by the share it stands for."""
        return whole(10 * (1 - self.shares[choice]))

    def start_range(self, as_of: dt.date) -> dict:
        return {"from": (as_of - dt.timedelta(days=self.start_days_before)).isoformat(),
                "to": (as_of + dt.timedelta(days=self.start_days_after)).isoformat()}


@dataclass(frozen=True)
class StepRow:
    planned_on: dt.date | None
    actual_on: dt.date | None
    first_planned_on: dt.date | None
    first_planned_plan_date: dt.date | None
    delay_days: int | None


@dataclass
class Activity:
    """One activity in its newest plan version public on the as-of date, with each step's dates by STEP's name."""

    reference: str
    section: str | None
    process_status: str | None
    plan_date: dt.date | None
    steps: dict[str, StepRow] = field(default_factory=dict)
    # Whether its first listing is confirmed as the first published one (strata.silver.plan_step_delays): False when
    # an earlier plan version of its agency was listed but not read.
    first_listing_confirmed: bool | None = None


def activities(rows: Rows, references: list[str]) -> dict[str, Activity]:
    """The named activities' steps, each as its newest plan version public on the reader's date gives them."""
    if not references:
        return {}
    found: dict[str, Activity] = {}
    for row in rows(sql("steps.sql"), references=",".join(references)):
        activity = found.setdefault(row["activity_reference_no"], Activity(
            row["activity_reference_no"], row["section"], row["process_status"], as_date(row["plan_date"]),
            first_listing_confirmed=row.get("first_listing_confirmed")))
        activity.steps.setdefault(row["step"], StepRow(
            as_date(row["planned_on"]), as_date(row["actual_on"]), as_date(row["first_planned_on"]),
            as_date(row["first_planned_plan_date"]), None if row["delay_days"] is None else int(row["delay_days"])))
    return found


def observe(activity: Activity, names: list[str], k: int, basis: str, as_of: dt.date) -> tuple[int, bool] | None:
    """One comparable's observation at step k: (days, reached), or None when it gives none."""
    row = activity.steps.get(names[k])
    if basis == DELAY:
        start = row.first_planned_on if row else None
        if start is None:
            return None
        if row.actual_on is not None:
            return (row.delay_days, True) if row.delay_days is not None else None
    else:
        before = activity.steps.get(names[k - 1]) if k else None
        start = before.actual_on if before else None
        if start is None:
            return None
        if row is not None and row.actual_on is not None:
            return (row.actual_on - start).days, True
    # Not reached by its newest plan: still open, unless a later step has an actual date (the plan left this one
    # blank) or the activity was canceled, which never reaches it.
    if any(activity.steps.get(later) and activity.steps[later].actual_on for later in names[k + 1:]):
        return None
    if activity.process_status == CANCELED:
        return None
    return (as_of - start).days, False


@dataclass
class StepFit:
    """One step's survival model over the comparables: its observations, shortest first, and each choice's point
    (its days, how many ran later and about how many in 10), or why it has none."""

    observed: list[tuple[str, int, bool]]  # (STEP reference, days, reached)
    points: dict[str, dict] | None
    reason: str | None

    @property
    def n(self) -> int:
        return len(self.observed)


def fit_step(observed: list[tuple[str, int, bool]], settings: Settings) -> StepFit:
    if len(observed) < settings.min_comparables:
        return StepFit(observed, None, FEW)
    curve = survival([Observation(days, reached) for _, days, reached in observed])
    points = {}
    for choice in CHOICES:
        day = quantile(curve, settings.shares[choice])
        if day is None:
            return StepFit(observed, None, NOT_REACHED)
        longer = sum(1 for _, days, _ in observed if days > day)
        points[choice] = {"days": day, "longer": longer, "in10": whole(Fraction(10 * longer, len(observed)))}
    return StepFit(observed, points, None)


def fit(comparables: dict[str, Activity], family: dict, basis: str, as_of: dt.date, settings: Settings) -> list[StepFit | None]:
    """Each step's model, in STEP's order; the duration basis's anchor has none."""
    names = [entry["step_name"] for entry in family["steps"]]
    fits: list[StepFit | None] = []
    for k in range(len(names)):
        if basis == DURATION and k == 0:
            fits.append(None)
            continue
        observed = [(reference, *seen) for reference, activity in comparables.items()
                    if (seen := observe(activity, names, k, basis, as_of)) is not None]
        fits.append(fit_step(sorted(observed, key=lambda item: (item[1], item[0])), settings))
    return fits


def longest(comparables: dict[str, Activity], family: dict) -> dict | None:
    """The stage that ran longest in the most comparables whose plans recorded every step up to longest_through,
    with how many (n) of how many (m), and each of them with its longest stage, for the evidence drawer: grouped by
    stage, the most common first, then by days, longest first. None when no comparable recorded them all."""
    keys = [entry["key"] for entry in family["steps"]]
    through = keys.index(family["longest_through"])
    names = [entry["step_name"] for entry in family["steps"]][:through + 1]
    found = []
    for reference, activity in comparables.items():
        dates = [activity.steps[name].actual_on if name in activity.steps else None for name in names]
        if any(day is None for day in dates):
            continue
        stages = [(dates[k] - dates[k - 1]).days for k in range(1, len(dates))]
        k = stages.index(max(stages)) + 1  # the earlier stage wins a tie
        found.append((reference, keys[k], stages[k - 1]))
    if not found:
        return None
    counts = {key: sum(1 for _, stage, _ in found if stage == key) for key in keys}
    best = max(keys, key=lambda key: (counts[key], -keys.index(key)))
    found.sort(key=lambda item: (-counts[item[1]], keys.index(item[1]), -item[2], item[0]))
    return {"step_key": best, "n": counts[best], "m": len(found),
            "entries": [{"step_reference": reference, "evidence_id": f"strata.gold.package:{reference}",
                         "stage_step_key": stage, "days": days} for reference, stage, days in found]}


def _choice(planned: dt.date | None = None, days: int | None = None, relation: str | None = None,
            point: dict | None = None) -> dict:
    return {"planned_date": planned.isoformat() if planned else None, "days": days, "days_relation": relation,
            "longer": point["longer"] if point else None, "in10": point["in10"] if point else None}


def _relation(days: int) -> str:
    return "after_plan" if days > 0 else "on_plan" if days == 0 else "before_plan"


def _plan_fields(own: Activity | None, name: str) -> dict:
    """The package's own plan dates for a step: as first published, and in its newest plan version."""
    row = own.steps.get(name) if own else None
    return {"plan_first_date": row.first_planned_on.isoformat() if row and row.first_planned_on else None,
            "plan_first_version_date": (row.first_planned_plan_date.isoformat()
                                        if row and row.first_planned_on and row.first_planned_plan_date else None),
            "plan_latest_date": row.planned_on.isoformat() if row and row.planned_on else None,
            "plan_latest_version_date": own.plan_date.isoformat() if row and row.planned_on and own.plan_date else None}


def _dated_step(entry: dict, k: int, fitted: StepFit | None, basis: str, own: Activity | None,
                previous: dict, chain: list[bool], start_date: dt.date | None) -> dict:
    """One step's reason and its two choices; previous and chain carry the duration basis from step to step."""
    if basis == DURATION and k == 0:
        return {"abstain_reason": None, **{choice: _choice(start_date) for choice in CHOICES}}
    if basis == DELAY:
        row = own.steps.get(entry["step_name"]) if own else None
        first = row.first_planned_on if row else None
        reason = fitted.reason or (NOT_IN_PLAN if first is None else None)
        if reason:
            return {"abstain_reason": reason, **{choice: _choice() for choice in CHOICES}}
        return {"abstain_reason": None, **{
            choice: _choice(first + dt.timedelta(days=point["days"]), abs(point["days"]), _relation(point["days"]), point)
            for choice, point in fitted.points.items()}}
    if fitted.reason:
        chain[0] = False
        for choice in CHOICES:
            previous[choice] = None
        return {"abstain_reason": fitted.reason, **{choice: _choice() for choice in CHOICES}}
    choices = {}
    for choice, point in fitted.points.items():
        before = previous[choice] if chain[0] else None
        planned = before + dt.timedelta(days=point["days"]) if before else None
        choices[choice] = _choice(planned, point["days"], "after_previous", point)
        previous[choice] = planned
    return {"abstain_reason": None if chain[0] else EARLIER, **choices}


def step_dates(rows: Rows, *, category: str | None, method: str | None, package_reference: str | None,
               comparables: list[str], as_of: dt.date, start_date: dt.date | None, settings: Settings,
               track: dict | None, sources: list[str], own: Activity | None = None) -> dict:
    """Section 2's planned date for each step of one package, with both choices, as estimate_time returns it. The
    package's own plan row, when it has one, picks its family by its STEP table; otherwise its category and
    Method do. own, given, is the package's own plan instead of its newest public version: an implementing agency's
    upload (ticket 38), whose dates are the baseline the steps are dated from."""
    shared = {"min_comparables": settings.min_comparables, "middle_in10": settings.in10("middle"),
              "cautious_in10": settings.in10("cautious"), "start_range": settings.start_range(as_of), "method": method}
    total = len(comparables)
    if own is None:
        own = activities(rows, [package_reference]).get(package_reference) if package_reference else None
    family_key, family_reason = family_for(category, method, own.section if own else None)
    if family_key is None:
        return {**shared, **_counts([]), "family": None, "family_reason": family_reason, "basis": None,
                "needs_start_date": False,
                "start_date": None, "steps": [], "longest": None, "abstain_all": None, "actual_steps_count": None,
                "track_record": None, "coverage": _coverage(total, total, sources)}
    family = families()[family_key]
    names = [entry["step_name"] for entry in family["steps"]]
    # A comparable planned in another STEP table has other steps, even under the same Method (a firm and an
    # individual consultant both hired by Direct Selection), so it dates none of this family's steps.
    listed = activities(rows, comparables)
    other = {reference for reference, found in listed.items()
             if found.section is not None and found.section not in family["sections"]}
    found = {reference: activity for reference, activity in listed.items() if reference not in other}
    basis = DELAY if own and any(name in own.steps and own.steps[name].first_planned_on for name in names) else DURATION
    fits = fit(found, family, basis, as_of, settings)
    abstain_all = {"n": total} if total < settings.min_comparables else None
    previous, chain, steps = {choice: start_date for choice in CHOICES}, [True], []
    for k, entry in enumerate(family["steps"]):
        fitted = fits[k]
        item = {"step_key": entry["key"], "is_anchor": basis == DURATION and k == 0,
                "comparables_n": fitted.n if fitted else None,
                "reached_n": sum(1 for _, _, reached in fitted.observed if reached) if fitted else None,
                "comparables": [{"step_reference": reference, "evidence_id": f"strata.gold.package:{reference}",
                                 "days": days, "still_open": not reached}
                                for reference, days, reached in (fitted.observed if fitted else [])],
                **_plan_fields(own, entry["step_name"])}
        if abstain_all:
            item |= {"abstain_reason": None, "middle": None, "cautious": None}
        else:
            item |= _dated_step(entry, k, fitted, basis, own, previous, chain, start_date)
        steps.append(item)
    used = {reference for fitted in fits if fitted for reference, _, _ in fitted.observed}
    unconfirmed = sum(1 for reference in used if found[reference].first_listing_confirmed is False)
    actual = None
    if own is not None:
        actual = sum(1 for name in names if name in own.steps and own.steps[name].actual_on is not None)
    return {**shared, **_counts(steps), "family": family_key, "family_reason": None, "basis": basis,
            "needs_start_date": basis == DURATION and start_date is None,
            "start_date": start_date.isoformat() if start_date and basis == DURATION else None,
            "steps": steps, "longest": None if abstain_all else longest(found, family), "abstain_all": abstain_all,
            "actual_steps_count": actual, "track_record": track if basis == DELAY else None,
            "coverage": _coverage(total, len(used & set(comparables)), sources, len(other), unconfirmed),
            "not_used": [{"step_reference": reference, "reason": OTHER_FAMILY if reference in other else NO_PLAN_DATES}
                         for reference in sorted(set(comparables) - used)]}


def _counts(steps: list[dict]) -> dict:
    """The counts a screen's sentences need, so it counts nothing itself: the steps that can take a date (all but
    the anchor), how many each choice dated, how many have no date and why (few_n of them for too few comparable
    packages), and none_dated when no step has a date or days in either choice, so the choice changes nothing."""
    later = [step for step in steps if not step["is_anchor"]]
    return {"dateable_n": len(later),
            "dated_n": {choice: sum(1 for step in later if step[choice] and step[choice]["planned_date"])
                        for choice in CHOICES},
            "undated_n": sum(1 for step in later if step["abstain_reason"]),
            "few_n": sum(1 for step in later if step["abstain_reason"] == FEW),
            "none_dated": not any(step[choice] and step[choice]["days"] is not None
                                  for step in later for choice in CHOICES)}


def _coverage(total: int, used: int, sources: list[str], other_family: int = 0, unconfirmed: int = 0) -> dict:
    """The comparable packages behind the steps: how many, how many dated a step, how many had no dates for these
    steps in their published plans (missing), how many were planned in another STEP table (other_family), and how many
    of those used have a first listing that is not confirmed as the first published one (unconfirmed)."""
    return {"total": total, "used": used, "missing": total - used - other_family, "other_family": other_family,
            "unconfirmed": unconfirmed, "reason": NO_PLAN_DATES, "sources": sources}


# ── The track record, from the stored backtests ──────────────────────────

SCORER = "step_dates_backtest"
TEST_YEAR = "test_year"


def track_record(engine, as_of: dt.date, settings: Settings) -> dict | None:
    """Each choice's track record from the latest backtest run public on the as-of date: of the steps first planned
    in the latest test year that started before the as-of date, how many the backtest scored, how many came on or
    before that choice's date, the year's MLflow run id, and what a well-sized date catches, in 10. None before
    any run, or when that year scored fewer steps than min_unseen."""
    result = engine.run(sql("track_record.sql"), {"scorer": SCORER, "segment_kind": TEST_YEAR, "as_of": as_of})
    stored = [dict(zip(result.columns, values)) for values in result.rows]
    if not stored:
        return None
    latest = max(stored, key=lambda row: (row["ran_at"], row["run_id"]))["run_id"]
    years: dict[int, dict] = {}
    for row in stored:
        if row["run_id"] == latest and as_date(row["cutoff"]) < as_of and row["value"] is not None:
            years.setdefault(int(row["segment"]), {"run_id": row["mlflow_run_id"]})[row["measure"]] = int(row["value"])
    if not years:
        return None
    year = max(years)
    scores = years[year]
    total = scores.get("steps_total", 0)
    if total < settings.min_unseen:
        return None
    return {choice: {"year": year, "total": total, "inside": scores.get(f"steps_inside_{choice}", 0),
                     "run_id": scores["run_id"], "catch_in10": 10 - settings.in10(choice)} for choice in CHOICES}


# ── The per-step backtests, through the replay harness ───────────────────
#
# What a test year stores in strata.ops.evaluation_result, one measure per row, under the segment test_year:
#
# - For each step of each family, as "<family>.<step>.<measure>": n, the steps first planned in the year that the
#   backtest dated and whose outcome is known (reached by the outcomes date, or still open then and already past
#   its cautious date); inside_cautious and inside_middle, those that came on or before each date; abstained,
#   those it gave no date; undecided, those still open short of their cautious date, which are left out;
#   coverage_cautious, inside_cautious / n to three decimals; and error_cautious_days, error_middle_days and
#   error_plan_days, the median distance in days from each reached step's actual date to each date and to the
#   plan's first published date.
# - The same over every step: steps_total, steps_inside_cautious, steps_inside_middle, steps_abstained,
#   steps_undecided and the three errors, and beat_plan, 1 when the middle date's typical error was smaller than
#   the plan's own.
#
# Each year is one replay, so each row carries the year's MLflow run id. Every number is a count or a median the
# backtest worked out; nothing is typed in.
#
# A test year scores only the steps that the plans public at its cutoff, January 1, had first planned for that
# year (sql/step_dates/pending.sql). A package first listed later in the year is not scored, so the backtest never
# sees a plan from after its cutoff, and the track record covers fewer steps than every step planned in the year.
# Its tooltip says so ("steps that plans published before {year} had planned for {year}").

MEASURES = ("n", "inside_cautious", "inside_middle", "abstained", "undecided")


def _median(values: list[int]) -> float | int:
    found = statistics.median(values)
    return int(found) if float(found).is_integer() else float(found)


def _measures(prefix: str, counts: dict, errors: list[tuple[int, int, int]]) -> list[Score]:
    scores = [Score(f"{prefix}{measure}", counts[measure]) for measure in MEASURES]
    if counts["n"]:
        scores.append(Score(f"{prefix}coverage_cautious", round(counts["inside_cautious"] / counts["n"], 3)))
    if errors:
        scores += [Score(f"{prefix}error_{name}_days", _median([error[k] for error in errors]))
                   for k, name in enumerate(("cautious", "middle", "plan"))]
    return scores


class StepDatesBacktest:
    """The harness's scorer for one test year of the planned dates, on the delay basis: the plan is the baseline."""

    name = SCORER
    model = "strata.estimates.step_dates"

    def __init__(self, settings: Settings):
        self.settings = settings

    def score(self, replay: Replay) -> Scored:
        cutoff, through = replay.window.cutoff, replay.window.outcomes_through
        pending: dict[str, dict] = {}
        for row in replay.inputs.rows(sql("pending.sql"), year_from=cutoff, year_to=dt.date(cutoff.year + 1, 1, 1)):
            entry = pending.setdefault(row["activity_reference_no"], {"section": row["section"], "method": row["method"],
                                                                      "steps": {}})
            entry["steps"].setdefault(row["step"], as_date(row["first_planned_on"]))
        outcomes = activities(replay.outcomes.rows, sorted(pending))
        counts = {f"{family}.{step['key']}": dict.fromkeys(MEASURES, 0)
                  for family, entry in families().items() for step in entry["steps"]}
        errors: dict[str, list[tuple[int, int, int]]] = {key: [] for key in counts}
        for reference in sorted(pending):
            entry = pending[reference]
            family_key, _ = family_for(None, entry["method"], entry["section"])
            if family_key is None:
                continue
            family = families()[family_key]
            found = replay.inputs.call("find_comparables", step_reference=reference)
            comparables = activities(replay.inputs.rows, [row["step_reference"] for row in found["rows"]])
            fits = fit(comparables, family, DELAY, cutoff, self.settings)
            names = [step["step_name"] for step in family["steps"]]
            for k, step in enumerate(family["steps"]):
                first = entry["steps"].get(step["step_name"])
                if first is None:
                    continue
                key, fitted = f"{family_key}.{step['key']}", fits[k]
                if fitted.points is None:
                    counts[key]["abstained"] += 1
                    continue
                _outcome(counts[key], errors[key], fitted, outcomes.get(reference), names, k, first, through)
        scores = [score for key in counts for score in _measures(f"{key}.", counts[key], errors[key])]
        total = {measure: sum(found[measure] for found in counts.values()) for measure in MEASURES}
        every = [error for found in errors.values() for error in found]
        scores += [Score(f"steps_{'total' if name == 'n' else name}", total[name]) for name in MEASURES]
        if every:
            typical = [_median([error[k] for error in every]) for k in range(3)]
            scores += [Score(f"error_{name}_days", value) for name, value in zip(("cautious", "middle", "plan"), typical)]
            scores.append(Score("beat_plan", int(typical[1] < typical[2])))
        return Scored(scores, {"middle_share": float(self.settings.shares["middle"]),
                               "cautious_share": float(self.settings.shares["cautious"]),
                               "min_comparables": self.settings.min_comparables})


def _outcome(counts: dict, errors: list, fitted: StepFit, outcome: Activity | None, names: list[str], k: int,
             first: dt.date, through: dt.date) -> None:
    """Score one dated step against what its plans showed by the outcomes date."""
    cautious, middle = fitted.points["cautious"]["days"], fitted.points["middle"]["days"]
    row = outcome.steps.get(names[k]) if outcome else None
    if row is not None and row.actual_on is not None and row.delay_days is not None:
        delay = row.delay_days
        counts["n"] += 1
        counts["inside_cautious"] += delay <= cautious
        counts["inside_middle"] += delay <= middle
        errors.append((abs(delay - cautious), abs(delay - middle), abs(delay)))
        return
    recorded_later = outcome is not None and any(
        outcome.steps.get(later) and outcome.steps[later].actual_on for later in names[k + 1:])
    canceled = outcome is not None and outcome.process_status == CANCELED
    if not recorded_later and not canceled and (through - first).days > cautious:
        counts["n"] += 1  # still open past its cautious date: a known miss of both dates
    else:
        counts["undecided"] += 1


def backtest(engine, tracker, *, years: tuple[int, ...] | None = None, outcomes_through: dt.date | None = None,
             store=None, thresholds: Thresholds | None = None, ran_at: dt.datetime | None = None) -> str:
    """Backtest each test year in config/models.toml (2021 to 2025), store every score and return the run's id."""
    thresholds = thresholds or load_thresholds()
    ran_at = ran_at or dt.datetime.now(dt.UTC)
    through = outcomes_through or ran_at.date()
    run_id = harness.new_run_id(SCORER, ran_at)
    scorer = StepDatesBacktest(Settings.read(thresholds))
    for year in years or load_time_estimate().test_years:
        harness.replay(engine, scorer, Window(dt.date(year, 1, 1), through, TEST_YEAR, str(year)), tracker, run_id,
                       ran_at, store or engine, thresholds)
    return run_id


def stored_years(engine, run_id: str | None = None) -> dict[int, dict]:
    """Each test year's stored scores, from one run or the latest, keyed by year."""
    run_id = run_id or harness.latest_run(engine, SCORER)
    if run_id is None:
        return {}
    return {int(segment): record for (kind, segment), record in harness.segments(harness.run_rows(engine, run_id)).items()
            if kind == TEST_YEAR}
