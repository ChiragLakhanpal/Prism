"""The discrete-time hazard model for project delay early warning, in shadow (ticket 44; docs/PLAN.md section 7:
"Project delay early warning uses fixed signals now, with a discrete-time hazard model in shadow until it beats them on
the hindsight comparison").

The model is a logistic regression on person-period rows (a discrete-time hazard model): one row for each open project
every estimates_loop.hazard_period_months, from its loan history (strata.gold.project_closing_date), with three
values: how many times its closing date had moved, the years left to its closing date, and the years since its last
move (each at most five). The outcome is the one the fixed signals' track record uses (brief 37): the loan history
showed the closing date moved later within signals.track_record_window_months after the row's date. A row counts only
once its window had ended by the day the model is trained on, and the model is shrunk toward no effect by
estimates_loop.hazard_ridge. With fewer than signals.track_record_min rows, or only one outcome among them, it
abstains (too_few_periods, one_outcome).

- score_in_shadow() is the nightly score task's: it trains the model as of the night and scores every open project
  with a loan history into strata.ops.hazard_scores.
- compare() is the replay harness's model-backtest adapter for it (the spec's seam 5): on each of the signals' track
  record dates it freezes Strata at that date, runs project_signals and the model trained then on every project the
  track record counts, lets the model pick as many projects as the signals did (Needs a look or Watch), and counts the
  projects each caught among those whose closing date then moved later. The model beats the signals only with at
  least track_record_min projects, more caught, and McNemar's exact test on the discordant projects below
  estimates_loop.hazard_beats_alpha. The counts go to strata.ops.evaluation_result (scorer hazard_vs_signals) and
  MLflow.

Nothing here is shown: no registry tool, no route and no copy key reads a hazard score (brief 37: Following shows
signals with their reasons and track record, never a score).
"""

from __future__ import annotations

import datetime as dt
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from importlib import resources

from strata.config import Thresholds, load_thresholds
from strata.estimates import harness
from strata.estimates.harness import Reader, Replay, Score, Scored, Window
from strata.estimates.past_range import as_date
from strata.lakehouse.engine import Engine

SCORER = "hazard_vs_signals"
MODEL = "strata.estimates.hazard"
SEGMENT_KIND, SEGMENT = "replay", "hazard"
TABLE = "strata.ops.hazard_scores"
COLUMNS = ("project_id", "run_id", "scored_on", "hazard", "abstention", "model", "features", "scored_at", "public_from")
CAP_YEARS = 5.0
LOOK_STATUSES = ("needs_a_look", "watch")  # the statuses that pick a project out for a look


def _sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "hazard" / f"{name}.sql").read_text()


@dataclass(frozen=True)
class Settings:
    window_months: int
    period_months: int
    ridge: float
    least: int
    alpha: float

    @classmethod
    def read(cls, thresholds: Thresholds) -> Settings:
        value = thresholds.value
        return cls(int(value("signals.track_record_window_months")), int(value("estimates_loop.hazard_period_months")),
                   float(value("estimates_loop.hazard_ridge")), int(value("signals.track_record_min")),
                   float(value("estimates_loop.hazard_beats_alpha")))


# ── Rows from the loan history ───────────────────────────────────────────

def histories(reader: Reader) -> dict[str, list[dict]]:
    """Each project's loan history as public on the reader's date, oldest month first."""
    found: dict[str, list[dict]] = defaultdict(list)
    for row in reader.rows(_sql("history")):
        found[row["project_id"]].append({**row, "reported_on": as_date(row["reported_on"]),
                                         "closing_date": as_date(row["closing_date"]),
                                         "previous_closing_date": as_date(row["previous_closing_date"])})
    return found


def _years(start: dt.date, end: dt.date) -> float:
    return min(max((end - start).days / 365.25, 0.0), CAP_YEARS)


def features(history: list[dict], day: dt.date) -> dict | None:
    """A project's values on a day, from the months its loan history had reported by then, or None when it had
    reported none or its closing date had passed."""
    known = [row for row in history if row["reported_on"] <= day]
    if not known or known[-1]["closing_date"] < day:
        return None
    moves = known[1:]
    return {"moves": len(moves), "years_to_close": round(_years(day, known[-1]["closing_date"]), 6),
            "years_since_move": round(_years(moves[-1]["reported_on"], day), 6) if moves else CAP_YEARS}


def extended(history: list[dict], after: dt.date, through: dt.date) -> bool:
    """Whether the loan history shows the closing date moved later after a day and by another."""
    return any(row["previous_closing_date"] is not None and row["closing_date"] > row["previous_closing_date"]
               and after < row["reported_on"] <= through for row in history)


def _vector(values: dict) -> list[float]:
    return [1.0, float(values["moves"]), float(values["years_to_close"]), float(values["years_since_move"])]


def periods(history: list[dict], day: dt.date, settings: Settings) -> list[tuple[dict, bool]]:
    """The project's rows the model may learn from on a day: every period_months from its first month, whose
    follow-up window had ended by that day, while it was open, each with its outcome."""
    from strata.tools.project_signals import months_after

    found = []
    if not history:
        return found
    period = history[0]["reported_on"]
    while months_after(period, settings.window_months) <= day:
        values = features(history, period)
        if values is not None:
            found.append((values, extended(history, period, months_after(period, settings.window_months))))
        period = months_after(period, settings.period_months)
    return found


# ── The model ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HazardModel:
    """A fitted logistic regression on the rows' values, trained through a day."""

    weights: tuple[float, ...]
    trained_through: dt.date
    rows: int

    @property
    def name(self) -> str:
        return f"hazard-{self.trained_through.isoformat()}"

    def chance(self, values: dict) -> float:
        margin = sum(weight * value for weight, value in zip(self.weights, _vector(values)))
        if margin < 0:  # the same sigmoid, written so a large margin either way never overflows
            return math.exp(margin) / (1.0 + math.exp(margin))
        return 1.0 / (1.0 + math.exp(-margin))


def fit(found: dict[str, list[dict]], day: dt.date, settings: Settings) -> HazardModel | str:
    """The model trained on every project's rows whose window ended by day, or its abstention's code."""
    import numpy as np

    rows = [row for history in found.values() for row in periods(history, day, settings)]
    if len(rows) < settings.least:
        return "too_few_periods"
    outcomes = np.array([1.0 if outcome else 0.0 for _, outcome in rows])
    if outcomes.min() == outcomes.max():
        return "one_outcome"
    values = np.array([_vector(row) for row, _ in rows])
    shrink = np.diag([0.0] + [settings.ridge] * (values.shape[1] - 1))
    weights = np.zeros(values.shape[1])
    for _ in range(100):  # Newton's method on the penalized log-likelihood
        chances = 1.0 / (1.0 + np.exp(-values @ weights))
        gradient = values.T @ (outcomes - chances) - shrink @ weights
        hessian = values.T @ (values * (chances * (1 - chances))[:, None]) + shrink
        step = np.linalg.solve(hessian, gradient)
        weights = weights + step
        if np.abs(step).max() < 1e-10:
            break
    return HazardModel(tuple(float(weight) for weight in weights), day, len(rows))


# ── In shadow, nightly ───────────────────────────────────────────────────

def score_in_shadow(engine: Engine, run_id: str, now: dt.datetime, thresholds: Thresholds | None = None) -> int:
    """Train the model as of tonight and score every open project with a loan history. Returns the rows written."""
    thresholds = thresholds or load_thresholds()
    settings = Settings.read(thresholds)
    day = now.astimezone(dt.UTC).date()
    found = histories(Reader(engine, day, thresholds))
    model = fit(found, day, settings)
    name = model.name if isinstance(model, HazardModel) else f"hazard-{day.isoformat()}"
    rows = []
    for project, history in sorted(found.items()):
        values = features(history, day)
        if values is None:
            continue
        chance = round(model.chance(values), 6) if isinstance(model, HazardModel) else None
        rows.append((project, run_id, day, chance, None if isinstance(model, HazardModel) else model, name,
                     json.dumps(values, sort_keys=True), now, day))
    return engine.insert_rows(TABLE, COLUMNS, rows) if rows else 0


# ── Against the fixed signals, through the replay harness ───────────────

class HazardVsSignals:
    """The replay harness's scorer: the hazard model against the fixed signals on each replay date."""

    name = SCORER
    model = MODEL

    def __init__(self, dates: tuple[dt.date, ...], settings: Settings):
        self.dates, self.settings = dates, settings

    def score(self, replay: Replay) -> Scored:
        from strata.estimates import signals_track
        from strata.estimates.hindsight import mcnemar
        from strata.tools.project_signals import months_after

        totals = defaultdict(int)
        used, without_model = [], []
        moves = signals_track.later_moves(replay.outcomes)
        for day in (day for day in self.dates if day <= replay.window.cutoff):
            frozen = Reader(replay.inputs.engine, day, replay.thresholds)
            found = histories(frozen)
            model = fit(found, day, self.settings)
            later = months_after(day, self.settings.window_months)
            entries = []
            # The projects the signals' track record counts on the day, read in batches as it reads them.
            for pid, result in signals_track.counted(frozen):
                status = result["status"]
                values = features(found.get(pid, []), day)
                if values is None:
                    continue
                moved = any(day < moved_on <= later for moved_on in moves[pid])
                chance = model.chance(values) if isinstance(model, HazardModel) else None
                entries.append({"project": pid, "picked": status in LOOK_STATUSES, "chance": chance, "extended": moved})
            used.append(day.isoformat())
            if not isinstance(model, HazardModel):
                without_model.append({"date": day.isoformat(), "reason": model})
            budget = sum(entry["picked"] for entry in entries)
            ranked = sorted((entry for entry in entries if entry["chance"] is not None),
                            key=lambda entry: (-entry["chance"], entry["project"]))
            chosen = {entry["project"] for entry in ranked[:budget]}
            for entry in entries:
                by_model = entry["project"] in chosen
                totals["cohort"] += 1
                totals["signals_picked"] += entry["picked"]
                totals["extended"] += entry["extended"]
                if entry["extended"]:
                    totals["signals_caught"] += entry["picked"]
                    totals["hazard_caught"] += by_model
                    totals["signals_only"] += entry["picked"] and not by_model
                    totals["hazard_only"] += by_model and not entry["picked"]
        p_value = mcnemar(totals["signals_only"], totals["hazard_only"])
        beats = (totals["cohort"] >= self.settings.least and totals["hazard_caught"] > totals["signals_caught"]
                 and p_value < self.settings.alpha)
        scores = [Score(measure, totals[measure]) for measure in
                  ("cohort", "signals_picked", "extended", "signals_caught", "hazard_caught", "signals_only", "hazard_only")]
        scores += [Score("mcnemar_p", round(p_value, 6)), Score("beats", int(beats)),
                   Score("window_months", self.settings.window_months), Score("min_projects", self.settings.least),
                   Score("dates", text=json.dumps(used)), Score("dates_without_model", text=json.dumps(without_model))]
        return Scored(scores, {"dates": len(used), "window_months": self.settings.window_months,
                               "period_months": self.settings.period_months, "ridge": self.settings.ridge})


def compare(engine: Engine, tracker, *, ran_at: dt.datetime, dates: tuple[dt.date, ...] | None = None,
            store: Engine | None = None, thresholds: Thresholds | None = None) -> str:
    """Replay the hazard model against the fixed signals on the signals' track record dates (or the dates given),
    store the counts and return the run's id. Outcomes are read as of the last date plus the window, or the day it
    runs when that is earlier, as the signals' track record reads them."""
    from strata.tools.project_signals import months_after

    thresholds = thresholds or load_thresholds()
    settings = Settings.read(thresholds)
    dates = tuple(sorted(dates or (as_date(day) for day in thresholds.value("signals.track_record_dates"))))
    through = min(months_after(dates[-1], settings.window_months), ran_at.astimezone(dt.UTC).date())
    run_id = harness.new_run_id(SCORER, ran_at)
    harness.replay(engine, HazardVsSignals(dates, settings), Window(dates[-1], through, SEGMENT_KIND, SEGMENT),
                   tracker, run_id, ran_at, store or engine, thresholds)
    return run_id


def stored(engine: Engine) -> dict | None:
    """The latest stored comparison, or None before the first."""
    run_id = harness.latest_run(engine, SCORER)
    if run_id is None:
        return None
    record = harness.segments(harness.run_rows(engine, run_id)).get((SEGMENT_KIND, SEGMENT))
    return None if record is None else {**record, "run_id": run_id}
