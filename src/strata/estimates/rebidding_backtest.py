"""The rebidding models' rolling backtests, the champion, its batch scores and its natural frequency (ticket 28).

run() replays Strata at the start of each test year in config/models.toml (2021 to 2025) through the replay
harness. In each year both learners (strata.estimates.rebidding_model) learn from the packages advertised before
January 1 whose outcome the records public then gave (advertised again, or signed; strata.estimates.rebidding),
each with its features as advertised. They are tested on the packages a Procurement Plan public on January 1
listed, with their features as planned then, that were advertised during the year and whose outcome the records
gave by the outcomes date. A package still undecided then is left out and counted. Each package's baseline is the
share advertised again among its comparable packages, as rebidding_risk counted them on January 1.

What a test year stores in strata.ops.evaluation_result, one measure per row:

- training_packages and training_advertised_again; test_packages, test_advertised_again and undecided_left_out.
- For each learner and for the baseline: {name}_brier, the Brier score, and {name}_calibration_error, the expected
  calibration error over rebidding.calibration_bins bins, each to four decimals. For each learner,
  {name}_beat_baseline: 1 when its Brier score was lower than the baseline's on the same packages. A learner that
  could not learn stores {name}_abstention, a code, instead.

The champion is the better calibrated: the learner with the lower mean calibration error over the test years,
then the lower mean Brier score, then config/models.toml's order. run() trains it on every package the records
decide on the outcomes date, writes the model card, and registers it in Unity Catalog: as champion when no version
holds that alias yet, else as challenger. Its registered_model segment stores version, alias, learner, test_year
(its latest), n_test and beat_baseline there, which rebidding_risk reads. Both models stay labeled experimental.

score_packages() is the nightly job's score task: the champion's chance for every activity a Procurement Plan
lists, as planned today, written to strata.ops.rebidding_scores. natural_frequency(), in strata.estimates.rebidding
so the app's server never imports numpy or XGBoost, is what rebidding_risk returns: the champion's "about k in
10 packages like this one", shown only from past_range.min_comparables comparables and a champion that beat its baseline in its latest test year. Otherwise it says why not, by code:
too_few, no_results (no champion registered yet), not_better, or not_scored (no score for this package: the
nightly job scores the activities in Procurement Plans, and a package planned from a sentence has none).
"""

from __future__ import annotations

import datetime as dt
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from strata.config import RebiddingSettings, Thresholds, load_rebidding, load_thresholds
from strata.estimates import harness, rebidding, rebidding_model
from strata.estimates.harness import Replay, Score, Scored, Window
from strata.estimates.rebidding import BASELINE, CHAMPION, REGISTERED, SCORER, band, champion, in10, natural_frequency  # noqa: F401
from strata.estimates.rebidding_model import NoModel, RebiddingModel
from strata.estimates.tracking import MODEL_CARD

TEST_YEAR = "test_year"
CHALLENGER = "challenger"
STATE = "model_state.json"
SCORES_TABLE = "strata.ops.rebidding_scores"
SCORE_COLUMNS = ("run_id", "step_reference", "model", "version", "learner", "probability", "in10", "scored_on",
                 "public_from")


def _four(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), ROUND_HALF_UP))


def window(year: int, outcomes_through: dt.date) -> Window:
    return Window(dt.date(year, 1, 1), outcomes_through, TEST_YEAR, str(year))


# ── What the models read ─────────────────────────────────────────────────

def training_set(rows: rebidding.Rows, as_of: dt.date, thresholds: Thresholds) -> tuple[list[dict], list[bool], int]:
    """The packages advertised before the date whose outcome the records public then gave, in the order they were
    advertised, with their features as advertised and their outcomes, and how many were left out as undecided."""
    known = rebidding.labels(rows, as_of, thresholds)
    start = rebidding.as_date(thresholds.value("past_range.period_from"))
    featured = {row["step_reference"]: row for row in rows(rebidding.sql("features.sql"), period_from=start)}
    picked = [label for label in known.values() if label.notice_date < as_of and label.step_reference in featured]
    picked.sort(key=lambda label: (label.notice_date, label.step_reference))
    decided = [label for label in picked if label.decided]
    return ([rebidding_model.features_of(featured[label.step_reference]) for label in decided],
            [label.advertised_again for label in decided], len(picked) - len(decided))


def planned(rows: rebidding.Rows) -> dict[str, dict]:
    """Every activity a plan public on the reader's date lists, with its features as planned then."""
    return {row["step_reference"]: rebidding_model.features_of(row) for row in rows(rebidding.sql("planned_features.sql"))}


# ── The backtest ─────────────────────────────────────────────────────────

class RebiddingBacktest:
    """The harness's scorer for one test year of both rebidding models."""

    name = SCORER

    def __init__(self, settings: RebiddingSettings):
        self.settings, self.model = settings, settings.registered_model

    def params(self) -> dict:
        return {"learners": ",".join(self.settings.learners), "calibration_every": self.settings.calibration_every,
                **{f"{learner}.{key}": value for learner in self.settings.learners
                   for key, value in self.settings.learner_settings[learner].items()}}

    def score(self, replay: Replay) -> Scored:
        cutoff, thresholds = replay.window.cutoff, replay.thresholds
        end = dt.date(cutoff.year + 1, cutoff.month, cutoff.day)
        bins = int(thresholds.value("rebidding.calibration_bins"))
        train_rows, train_outcomes, _ = training_set(replay.inputs.rows, cutoff, thresholds)
        listed = planned(replay.inputs.rows)
        outcomes = rebidding.labels(replay.outcomes.rows, replay.window.outcomes_through, thresholds)
        test = sorted((label for ref, label in outcomes.items() if ref in listed and cutoff <= label.notice_date < end),
                      key=lambda label: (label.notice_date, label.step_reference))
        decided = [label for label in test if label.decided]
        scores = [Score("training_packages", len(train_rows)), Score("training_advertised_again", sum(train_outcomes)),
                  Score("test_packages", len(decided)), Score("test_advertised_again", sum(l.advertised_again for l in decided)),
                  Score("undecided_left_out", len(test) - len(decided))]
        if not decided:
            return Scored(scores + [Score("abstention", text="no_test_packages")], self.params())
        happened = [label.advertised_again for label in decided]
        baseline = [self._baseline(replay, label.step_reference, train_outcomes) for label in decided]
        baseline_brier = rebidding_model.brier(baseline, happened)
        scores += [Score("baseline_brier", _four(baseline_brier)),
                   Score("baseline_calibration_error", _four(rebidding_model.calibration_error(baseline, happened, bins)))]
        for learner in self.settings.learners:
            try:
                model = rebidding_model.fit(learner, train_rows, train_outcomes, self.settings)
            except NoModel as no:
                scores.append(Score(f"{learner}_abstention", text=no.reason))
                continue
            chances = model.chances([listed[label.step_reference] for label in decided])
            brier = rebidding_model.brier(chances, happened)
            scores += [Score(f"{learner}_brier", _four(brier)),
                       Score(f"{learner}_calibration_error", _four(rebidding_model.calibration_error(chances, happened, bins))),
                       Score(f"{learner}_beat_baseline", int(brier < baseline_brier))]
        return Scored(scores, self.params())

    @staticmethod
    def _baseline(replay: Replay, step_reference: str, train_outcomes: list[bool]) -> float:
        """The share advertised again among the package's comparables on the cutoff, by rebidding_risk; the training
        packages' share when it found none."""
        counted = replay.inputs.call("rebidding_risk", step_reference=step_reference)
        if counted["m"]:
            return counted["n"] / counted["m"]
        return sum(train_outcomes) / len(train_outcomes) if train_outcomes else 0.0


# ── A whole run ──────────────────────────────────────────────────────────

@dataclass
class BacktestRun:
    run_id: str
    years: dict[int, Scored]
    champion: str | None  # the better-calibrated learner, or None when neither has results
    version: int | None
    alias: str | None
    card: str


def stored_years(engine, run_id: str | None = None) -> dict[int, dict]:
    run_id = run_id or harness.latest_run(engine, SCORER)
    if run_id is None:
        return {}
    return {int(segment): record for (kind, segment), record in harness.segments(harness.run_rows(engine, run_id)).items()
            if kind == TEST_YEAR}


def choose(years: dict[int, dict], learners: tuple[str, ...]) -> str | None:
    """The better-calibrated learner: lower mean calibration error over the test years, then lower mean Brier score,
    then the order the learners are listed in."""
    ranked = []
    for place, learner in enumerate(learners):
        errors = [year[f"{learner}_calibration_error"] for year in years.values() if f"{learner}_calibration_error" in year]
        briers = [year[f"{learner}_brier"] for year in years.values() if f"{learner}_brier" in year]
        if errors:
            ranked.append((statistics.mean(errors), statistics.mean(briers), place, learner))
    return min(ranked)[3] if ranked else None


def latest_result(years: dict[int, dict], learner: str) -> tuple[int, dict] | None:
    held = [(year, record) for year, record in years.items() if f"{learner}_brier" in record]
    return max(held) if held else None


def train(engine, as_of: dt.date, learner: str, settings: RebiddingSettings, thresholds: Thresholds) -> RebiddingModel:
    """The learner trained on every package the records decide on the date."""
    rows, outcomes, _ = training_set(rebidding.engine_rows(engine, as_of), as_of, thresholds)
    return rebidding_model.fit(learner, rows, outcomes, settings)


def run(engine, tracker, *, years: tuple[int, ...] | None = None, outcomes_through: dt.date | None = None, store=None,
        settings: RebiddingSettings | None = None, thresholds: Thresholds | None = None,
        ran_at: dt.datetime | None = None) -> BacktestRun:
    """Backtest each test year, choose the better-calibrated learner, train and register it with its card, and store
    every score."""
    settings, thresholds = settings or load_rebidding(), thresholds or load_thresholds()
    store = store or engine
    ran_at = ran_at or dt.datetime.now(dt.UTC)
    through = outcomes_through or ran_at.date()
    run_id = harness.new_run_id(SCORER, ran_at)
    scorer = RebiddingBacktest(settings)
    scored = {year: harness.replay(engine, scorer, window(year, through), tracker, run_id, ran_at, store, thresholds)
              for year in (settings.test_years if years is None else years)}
    stored = stored_years(store, run_id)
    best = choose(stored, settings.learners)
    model = no_model = None
    if best is not None:
        try:
            model = train(engine, through, best, settings, thresholds)
        except NoModel as no:
            no_model = no.reason
    card = render_card(stored, best, model, no_model, settings, thresholds, through)
    mlflow_run = tracker.start_run("rebidding model", {**scorer.params(), "run_id": run_id, "champion": best,
                                                        "training_through": through.isoformat()})
    tracker.log_text(mlflow_run, card, MODEL_CARD)
    version = alias = None
    if model is not None:
        tracker.log_text(mlflow_run, model.state_json(), STATE)
        tracker.log_model(mlflow_run, model)
        year, record = latest_result(stored, best)
        version = tracker.register(mlflow_run, settings.registered_model, card, track_sentence(year, record, best),
                                   what="rebidding model (experimental)")
        alias = CHAMPION if tracker.alias_version(settings.registered_model, CHAMPION) is None else CHALLENGER
        tracker.set_alias(settings.registered_model, alias, version)
        rows = [Score("version", version), Score("alias", text=alias), Score("learner", text=best),
                Score("test_year", year), Score("n_test", record["test_packages"]),
                Score("beat_baseline", record[f"{best}_beat_baseline"]),
                Score("training_packages", model.training_packages)]
        segment = Window(through, through, REGISTERED, str(version))
        harness.write(store, [harness.row(run_id, scorer, segment, score, mlflow_run, ran_at) for score in rows])
    tracker.end_run(mlflow_run)
    return BacktestRun(run_id, scored, best, version, alias, card)


# ── The champion's scores and natural frequency ──────────────────────────

def score_packages(engine, tracker, run_id: str, clock: Callable[[], dt.datetime]) -> int:
    """The nightly job's score task: the champion's chance for every activity a plan public today lists, as planned
    today, in strata.ops.rebidding_scores. Nothing is scored before a champion is registered."""
    scored_at = clock()
    today = scored_at.astimezone(dt.UTC).date()
    rows = rebidding.engine_rows(engine, today)
    held = champion(rows)
    text = tracker.model_text(held["model"], CHAMPION, STATE) if held else None
    if text is None:
        return 0
    model = RebiddingModel.from_state(text)
    activities = planned(rows)
    references = sorted(activities)
    chances = model.chances([activities[ref] for ref in references]) if references else []
    found = [(run_id, ref, held["model"], held["version"], model.learner, float(chance), in10(chance), today, today)
             for ref, chance in zip(references, chances)]
    return engine.insert_rows(SCORES_TABLE, SCORE_COLUMNS, found) if found else 0


# ── The model card ───────────────────────────────────────────────────────

NAMES = {"gbm": "calibrated gradient boosting", "logistic": "logistic regression"}


def track_sentence(year: int, record: dict, learner: str) -> str:
    beat = "beat" if record[f"{learner}_beat_baseline"] else "did not beat"
    return (f"In {year}, on {record['test_packages']} packages it had not seen, its Brier score was "
            f"{record[f'{learner}_brier']:.4f} against {record['baseline_brier']:.4f} for the share advertised again "
            f"among their comparable packages, so it {beat} that baseline.")


def render_card(years: dict[int, dict], best: str | None, model: RebiddingModel | None, no_model: str | None,
                settings: RebiddingSettings, thresholds: Thresholds, through: dt.date) -> str:
    """The model card, kept in MLflow beside the model. Every number comes from the stored results or the model."""
    wait = thresholds.value("rebidding.no_award_after_days")
    lines = [
        "# Rebidding model (experimental): model card",
        "",
        "Experimental. No field in the World Bank's records says a package was advertised again, so Strata works the "
        "labels out from three sources, and they may miss or miscount some packages.",
        "",
        "## What it is for",
        "",
        "It gives the chance that a package like this one is advertised again, shown in the package workspace as "
        "'about k in 10 packages like this one', only from "
        f"{thresholds.value('past_range.min_comparables')} comparable packages and only when the model beat its "
        "baseline in its latest test year. It is never an input to an award or review decision.",
        "",
        "## Labels",
        "",
        f"- No award: no contract in the awards dataset and no Contract Award notice with a signature date {wait} days "
        "after the notice's bids were due.",
        "- The same STEP reference advertised again: a later notice of the same type under the same reference.",
        "- A canceled plan row: Process Status Canceled in the newest Procurement Plan public on the date, with no "
        "signed contract. Terminated is a signed contract and does not count.",
        "",
        "A package none of them names counts as not advertised again once it is signed, and is left out while it is "
        "undecided.",
        "",
        "## Features",
        "",
        f"{', '.join(rebidding_model.FEATURES)}, each from the plan row public when the package was advertised, or as "
        "planned on the day it is scored.",
        "",
        "## Leakage notes",
        "",
        "- Process Status is read from the newest plan version public on each date, never gold.package's newest, so a "
        "status published in 2025 cannot reach a 2021 cutoff.",
        "- No Process Status, Actual Amount, signed amount, later plan version or later notice is a feature.",
        "- A notice's text is kept under the notice's own date. A notice changed later to say it was cancelled, such "
        "as Invitation for Bids OP00083890, may carry words published after that date, so a reason quoted from it "
        "can look public earlier than it was. Reasons are shown, never used as features.",
        "",
        "## Backtests",
        "",
        "| Test year | Packages | Advertised again | Undecided, left out | Model | Brier | Calibration error | "
        "Beat the baseline |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for year, record in sorted(years.items()):
        for learner in (*settings.learners, "baseline"):
            if f"{learner}_brier" not in record:
                continue
            beat = "" if learner == "baseline" else ("yes" if record[f"{learner}_beat_baseline"] else "no")
            name = "share among comparables" if learner == "baseline" else NAMES[learner]
            lines.append(f"| {year} | {record['test_packages']} | {record['test_advertised_again']} | "
                         f"{record['undecided_left_out']} | {name} | {record[f'{learner}_brier']:.4f} | "
                         f"{record[f'{learner}_calibration_error']:.4f} | {beat} |")
    lines += ["", "## Champion", ""]
    if best is None:
        lines.append("Neither model has test results, so there is no champion.")
    elif model is None:
        lines.append(f"{NAMES[best].capitalize()} was better calibrated, but it could not learn from the packages "
                     f"decided by {through.isoformat()} ({no_model}).")
    else:
        year, record = latest_result(years, best)
        lines.append(f"{NAMES[best].capitalize()}, the better calibrated in the backtests, trained on "
                     f"{model.training_packages} packages decided by {through.isoformat()}, "
                     f"{model.advertised_again} of them advertised again. {track_sentence(year, record, best)}")
    return "\n".join(lines) + "\n"
