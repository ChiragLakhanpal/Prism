"""The time estimate's rolling backtests, the champion model and the track record.

run() replays Strata at the start of each test year in config/models.toml (2021 to 2025) through the
replay harness. Each year's model learns only from packages Strata could measure by January 1 of that
year, and is scored on the packages a Procurement Plan public then listed and that were advertised in
the next 12 months, against their outcomes as of the outcomes date. Then it trains the champion on
everything Strata can measure on the outcomes date, writes the model card from the stored results
(strata.estimates.model_card), and registers the model in Unity Catalog: as champion when no version
holds that alias yet, else as challenger, which must win its backtest before it replaces the champion.

What a test year stores in strata.ops.evaluation_result, one measure per row (the 26 design brief,
section 6.6):

- training_packages, calibration_packages, calibration_still_open, training_through and
  feature_ranges, for the model the year learned; or abstention, a code, when it could not size ranges.
- ranges_given and abstained: the test packages that got a range, and those that got an abstention
  instead (fewer than time_estimate.min_comparables comparables, outside the training range).
- n, the packages it had not seen that it gave a range and whose outcome is known: signed by the
  outcomes date, or still open then and already past their 8-in-10 point. still_open_undecided counts
  the packages still open short of it, which are left out. m: those signed within their 8-in-10 point.
  expected: what a well-sized range catches, 8 in 10 of n, whole. coverage, m / n to three decimals,
  and in_band, 1 when it falls in the thresholds file's coverage band.
- e25_days to e80_days: the middle of each point over the ranges given; width_80_months, the middle
  8-in-10 point, since the range runs from the notice to it; width_50_months, the middle half's width.
- error_estimate_months, error_past_range_months and error_plan_months: the median distance from each
  package's outcome to the estimate's middle, the past range's middle (find_comparables as of the
  cutoff) and the plan's planned duration in its first listing, over the same error_packages: those
  signed with all three. Half of the packages were closer than each.
- middle_ran_longer and eight_in_ten_ran_longer, each with its total (n) and in10, for the plan-date
  choice; misses_early (always 0, as the 8-in-10 point is an upper point) and misses_late.

Every number here is a count or a median the harness worked out; nothing is typed in.
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from strata.config import Thresholds, TimeEstimateSettings, load_thresholds, load_time_estimate
from strata.estimates import harness, model_card
from strata.estimates.harness import Reader, Replay, Score, Scored, Window
from strata.estimates.past_range import QUARTERS, months
from strata.estimates.time_estimate import NoModel, Package, fit, packages_as_of
from strata.estimates.tracking import MODEL_CARD

SCORER = "time_estimate_backtest"
TEST_YEAR = "test_year"
REGISTERED = "registered_model"
CHAMPION, CHALLENGER = "champion", "challenger"


def _whole(value: Fraction) -> int:
    return int((Decimal(value.numerator) / Decimal(value.denominator)).quantize(Decimal(1), ROUND_HALF_UP))


def _share(value: Fraction) -> float:
    return float((Decimal(value.numerator) / Decimal(value.denominator)).quantize(Decimal("0.001"), ROUND_HALF_UP))


def _months(days) -> float:
    return float(months(Decimal(str(days))))


def window(year: int, outcomes_through: dt.date) -> Window:
    """The test year's replay: frozen on January 1, scored on outcomes as of outcomes_through."""
    return Window(dt.date(year, 1, 1), outcomes_through, TEST_YEAR, str(year))


def _model_scores(model) -> list[Score]:
    return [Score("training_packages", model.training_packages), Score("calibration_packages", model.calibration_packages),
            Score("calibration_still_open", model.calibration_still_open),
            Score("training_through", text=model.training_through.isoformat()),
            Score("feature_ranges", text=harness.as_json(model.feature_ranges))]


def _no_model_scores(training: list[Package], no: NoModel) -> list[Score]:
    return [Score("training_packages", len(training)), Score("abstention", text=no.reason),
            *(Score(name, value) for name, value in no.counts.items() if isinstance(value, int))]


class TimeEstimateBacktest:
    """The harness's scorer for one test year of the time estimate."""

    name = SCORER

    def __init__(self, settings: TimeEstimateSettings):
        self.settings, self.model = settings, settings.registered_model

    def params(self) -> dict:
        return {"learner": self.settings.learner, "calibration_every": self.settings.calibration_every,
                **{f"{self.settings.learner}.{key}": value for key, value in self.settings.learner_settings.items()}}

    def score(self, replay: Replay) -> Scored:
        cutoff, thresholds = replay.window.cutoff, replay.thresholds
        end = dt.date(cutoff.year + 1, cutoff.month, cutoff.day)
        known = packages_as_of(replay.inputs, self.settings)
        training = [item for item in known.values()
                    if item.notice_date is not None and item.notice_date < cutoff and item.days is not None]
        try:
            model = fit(training, self.settings, thresholds, training_through=cutoff)
        except NoModel as no:
            return Scored(_no_model_scores(training, no), self.params())
        outcomes = {row["step_reference"]: row for row in replay.outcomes.packages()}
        unseen = sorted((item for item in known.values()
                         if item.listed and (item.notice_date is None or item.notice_date >= cutoff)
                         and item.step_reference in outcomes
                         and cutoff <= dt.date.fromisoformat(outcomes[item.step_reference]["notice_date"]) < end),
                        key=lambda item: item.step_reference)
        return Scored(_model_scores(model) + _test_scores(model, unseen, outcomes, replay, thresholds),
                      self.params(), model)


def _test_scores(model, unseen: list[Package], outcomes: dict, replay: Replay, thresholds: Thresholds) -> list[Score]:
    cutoff = replay.window.cutoff
    given, abstained, undecided, n, m, ran_longer_middle, errors = [], 0, 0, 0, 0, 0, []
    for item in unseen:
        found = replay.inputs.call("find_comparables", step_reference=item.step_reference)
        estimate = model.estimate(item.features, len(found["rows"]), cutoff, thresholds)
        if estimate["abstention"]:
            abstained += 1
            continue
        days, outcome = estimate["days"], outcomes[item.step_reference]
        given.append(days)
        if outcome["still_open"]:
            if outcome["days"] > days["q80"]:  # still open past its 8-in-10 point: a known miss
                n, ran_longer_middle = n + 1, ran_longer_middle + 1
            else:
                undecided += 1
            continue
        actual = outcome["days"]
        n, m, ran_longer_middle = n + 1, m + (actual <= days["q80"]), ran_longer_middle + (actual > days["q50"])
        past = ((found.get("past_range") or {}).get("days") or {}).get("q50")
        planned = item.features["planned_days"]
        if past is not None and planned is not None:
            errors.append((abs(actual - days["q50"]), abs(actual - past), abs(actual - planned)))
    fewest = int(thresholds.value("time_estimate.min_unseen_packages"))
    scores = [Score("ranges_given", len(given)), Score("abstained", abstained), Score("still_open_undecided", undecided),
              Score("n", n), Score("m", m), Score("expected", _whole(QUARTERS["q80"] * n)),
              Score("misses_early", 0), Score("misses_late", n - m),
              Score("middle_ran_longer", ran_longer_middle), Score("middle_total", n),
              Score("eight_in_ten_ran_longer", n - m), Score("eight_in_ten_total", n),
              Score("error_packages", len(errors))]
    if n:
        coverage = _share(Fraction(m, n))
        low, high = (float(thresholds.value("time_estimate.coverage_low")),
                     float(thresholds.value("time_estimate.coverage_high")))
        scores += [Score("coverage", coverage), Score("in_band", int(low <= coverage <= high))]
    if n >= fewest:
        scores += [Score("middle_in10", _whole(Fraction(10 * ran_longer_middle, n))),
                   Score("eight_in_ten_in10", _whole(Fraction(10 * (n - m), n)))]
    if given:
        scores += [Score(f"e{name[1:]}_days", statistics.median(point[name] for point in given)) for name in QUARTERS]
        scores += [Score("width_80_months", _months(statistics.median(point["q80"] for point in given))),
                   Score("width_50_months", _months(statistics.median(point["q75"] - point["q25"] for point in given)))]
    if errors:
        scores += [Score(f"error_{name}_months", _months(statistics.median(error[k] for error in errors)))
                   for k, name in enumerate(("estimate", "past_range", "plan"))]
    return scores


# ── A whole run ──────────────────────────────────────────────────────────

@dataclass
class BacktestRun:
    run_id: str
    years: dict[int, Scored]
    version: int | None  # the model version registered, or None when no champion could be trained
    alias: str | None
    card: str


def train(engine, as_of: dt.date, settings: TimeEstimateSettings, thresholds: Thresholds):
    """The model trained on every package Strata can measure as of a date, frozen at that date."""
    known = packages_as_of(Reader(engine, as_of, thresholds), settings)
    training = [item for item in known.values() if item.notice_date is not None and item.days is not None]
    return fit(training, settings, thresholds, training_through=as_of)


def run(engine, tracker, *, years: tuple[int, ...] | None = None, outcomes_through: dt.date | None = None,
        store=None, settings: TimeEstimateSettings | None = None, thresholds: Thresholds | None = None,
        ran_at: dt.datetime | None = None) -> BacktestRun:
    """Backtest each test year, train and register the model with its card, and store every score."""
    settings, thresholds = settings or load_time_estimate(), thresholds or load_thresholds()
    store = store or engine
    ran_at = ran_at or dt.datetime.now(dt.UTC)
    through = outcomes_through or ran_at.date()
    run_id = harness.new_run_id(SCORER, ran_at)
    scorer = TimeEstimateBacktest(settings)
    scored = {year: harness.replay(engine, scorer, window(year, through), tracker, run_id, ran_at, store, thresholds)
              for year in years or settings.test_years}
    try:
        champion, no_model = train(engine, through, settings, thresholds), None
    except NoModel as no:
        champion, no_model = None, no
    card = model_card.render(stored_years(store, run_id), champion, no_model, settings, thresholds, through)
    mlflow_run = tracker.start_run("time_estimate model", {**scorer.params(), "run_id": run_id,
                                                           "training_through": through.isoformat()})
    tracker.log_text(mlflow_run, card, MODEL_CARD)
    version = alias = None
    if champion is not None:
        tracker.log_model(mlflow_run, champion)
        version = tracker.register(mlflow_run, settings.registered_model, card)
        alias = CHAMPION if tracker.alias_version(settings.registered_model, CHAMPION) is None else CHALLENGER
        tracker.set_alias(settings.registered_model, alias, version)
        rows = [Score("version", version), Score("alias", text=alias), *_model_scores(champion)]
        segment = Window(through, through, REGISTERED, str(version))
        harness.write(store, [harness.row(run_id, scorer, segment, score, mlflow_run, ran_at) for score in rows])
    tracker.end_run(mlflow_run)
    return BacktestRun(run_id, scored, version, alias, card)


# ── Reading the stored results ───────────────────────────────────────────

def stored_years(engine, run_id: str | None = None) -> dict[int, dict]:
    """Each test year's stored scores, from one run or the latest, keyed by year."""
    run_id = run_id or harness.latest_run(engine, SCORER)
    if run_id is None:
        return {}
    return {int(segment): record for (kind, segment), record in harness.segments(harness.run_rows(engine, run_id)).items()
            if kind == TEST_YEAR}


def track_record(engine, thresholds: Thresholds | None = None) -> dict | None:
    """The latest test year's track record from the latest run, or an abstention when that year had
    fewer than time_estimate.min_unseen_packages packages the model had not seen. None before any run."""
    thresholds = thresholds or load_thresholds()
    years = stored_years(engine)
    if not years:
        return None
    year = max(years)
    record = years[year]
    fewest = int(thresholds.value("time_estimate.min_unseen_packages"))
    if record.get("n", 0) < fewest:
        return {"year": year, "abstention": {"reason": "too_few_unseen_packages", "n": record.get("n", 0),
                                             "min_unseen_packages": fewest}}
    return {"year": year, "n": record["n"], "m": record["m"], "expected": record["expected"],
            "misses_early": record["misses_early"], "misses_late": record["misses_late"],
            "ran_on": record["ran_at"].date() if isinstance(record["ran_at"], dt.datetime) else record["ran_at"],
            "mlflow_run_id": record["mlflow_run_id"], "abstention": None}
