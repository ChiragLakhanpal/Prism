"""Batch scoring (ticket 26): the nightly job's score task.

It scores every package Strata knows, as of the run's day, with the champion model the replay harness
registered (ticket 25), for the package as described and for every combination of the what-if levers the
model reads (config/models.toml's [what_if]: market approach and qualification), and appends the rows to
strata.gold.time_estimate_score under the run's id. estimate_time then answers from stored rows, so the
chart answers within 100 ms (strata.tools.estimate_time).

- Where the champion comes from. strata.gold.time_estimate_model keeps each version the harness registered
  (strata.estimates.portable), so the task needs no MLflow: it scores with the newest champion public that
  day. On Databricks the live backtest registers it (ops/estimates/backtest_live.py). On this computer no
  workspace registry exists, so a run that reads the recorded fixture runs ticket 25's backtest first, with
  the offline tracker, and scores with the champion it trains. A live run with no champion scores nothing.
- What a row abstains for. A package whose estimated amount or planned duration lies outside what the model
  learned from abstains as described and in every combination (outside_training). A combination whose lever
  takes a value the model never learned from abstains too (value_not_learned): to the model that value is
  missing, so its estimate would only repeat the estimate with nothing recorded. The comparable-count rules
  (time_estimate.min_comparables, what_if.min_subgroup) depend on the criteria a page asks with, so
  estimate_time applies them when it answers.
"""

from __future__ import annotations

import datetime as dt
import itertools
import json

from strata.config import Lever, Thresholds, TimeEstimateSettings, load_thresholds, load_time_estimate, load_what_if
from strata.estimates import portable
from strata.estimates.harness import Reader
from strata.estimates.past_range import months
from strata.estimates.time_estimate import Package, packages_as_of

TABLE = "strata.gold.time_estimate_score"
COLUMNS = ("step_reference", "run_id", "as_described", "market_approach", "prequalification", "review_type",
           "estimated_amount_usd", "feature_date", "q25_days", "q50_days", "q75_days", "q80_days", "q25_months",
           "q50_months", "q75_months", "q80_months", "abstention", "abstention_detail", "model", "model_version",
           "model_alias", "training_through", "scored_at", "public_from")
POINTS = ("q25", "q50", "q75", "q80")


def combinations(levers: tuple[Lever, ...]) -> list[dict[str, str]]:
    """Every combination of the scored levers' values, as {feature: value}, in the levers' order."""
    scored = [lever for lever in levers if lever.feature]
    return [dict(zip((lever.feature for lever in scored), values))
            for values in itertools.product(*(lever.values for lever in scored))]


def cell(model, features: dict, described: dict) -> dict:
    """One combination's abstention, when it has one: outside the training range, or a lever's value the
    model never learned from. None when the model can score it."""
    outside = model.outside(features)
    if outside is not None:
        return {"abstention": "outside_training", "detail": outside}
    for feature, value in features.items():
        if feature in model.vocabularies and value != described.get(feature) and not model.learned(feature, value):
            return {"abstention": "value_not_learned", "detail": {"feature": feature, "value": value}}
    return {"abstention": None, "detail": None}


def scored(model, packages: list[Package], levers: tuple[Lever, ...]) -> list[dict]:
    """Each package as described and in each combination, with its points in days where the model can
    score it. The model scores every such row at once."""
    found = []
    for package in packages:
        described = package.features
        found.append({"package": package, "as_described": True, "features": described, **cell(model, described, described)})
        for combination in combinations(levers):
            features = {**described, **combination}
            found.append({"package": package, "as_described": False, "features": features,
                          **cell(model, features, described)})
    ready = [row for row in found if row["abstention"] is None]
    for row, days in zip(ready, model.days([row["features"] for row in ready]) if ready else []):
        row["days"] = days
    return found


def _row(item: dict, run_id: str, kept: portable.Kept, scored_at: dt.datetime) -> tuple:
    features, days = item["features"], item.get("days")
    amount = features.get("estimated_amount_usd")
    values = {
        "step_reference": item["package"].step_reference, "run_id": run_id, "as_described": item["as_described"],
        "market_approach": features.get("market_approach"), "prequalification": features.get("prequalification"),
        "review_type": features.get("review_type"), "estimated_amount_usd": None if amount is None else float(amount),
        "feature_date": item["package"].feature_date,
        **{f"{name}_days": None if days is None else days[name] for name in POINTS},
        **{f"{name}_months": None if days is None else float(months(days[name])) for name in POINTS},
        "abstention": item["abstention"],
        "abstention_detail": None if item["detail"] is None else json.dumps(item["detail"], sort_keys=True),
        "model": kept.name, "model_version": kept.version, "model_alias": kept.alias,
        "training_through": kept.model.training_through, "scored_at": scored_at, "public_from": scored_at.date()}
    return tuple(values[column] for column in COLUMNS)


def score(engine, run_id: str, scored_at: dt.datetime, kept: portable.Kept, settings: TimeEstimateSettings,
          thresholds: Thresholds, levers: tuple[Lever, ...]) -> int:
    """Score every package Strata knows on the run's day and append the rows. Returns how many it wrote."""
    day = scored_at.astimezone(dt.UTC).date()
    known = packages_as_of(Reader(engine, day, thresholds), settings)
    rows = [_row(item, run_id, kept, scored_at) for item in scored(kept.model, [known[key] for key in sorted(known)], levers)]
    return engine.insert_rows(TABLE, COLUMNS, rows) if rows else 0


def run(engine, run_id: str, scored_at: dt.datetime, train_here: bool) -> int:
    """The score task's work: score with the newest champion public on the run's day. train_here, for a run
    on the recorded fixture, runs ticket 25's backtest first when no champion is kept yet."""
    from strata.estimates import backtest
    from strata.estimates.tracking import OfflineTracker

    settings, thresholds, levers = load_time_estimate(), load_thresholds(), load_what_if()
    day = scored_at.astimezone(dt.UTC).date()
    kept = portable.latest(engine, settings.registered_model, day, learner="xgboost")
    if kept is None and train_here:
        backtest.run(engine, OfflineTracker(), outcomes_through=day, settings=settings, thresholds=thresholds,
                     ran_at=scored_at)
        kept = portable.latest(engine, settings.registered_model, day, learner="xgboost")
    if kept is None:
        return 0
    return score(engine, run_id, scored_at, kept, settings, thresholds, levers)
