"""The time estimate: Prism's own model of how long one package's procurement cycle takes, from its
specific procurement notice to its signed contract, with ranges for the middle half and 8 in 10.

The model is XGBoost's survival model (accelerated failure time), and its ranges are conformal:

- What it learns from. Every package Prism can measure as of the training date, by the past range's
  own rules (strata.tools.find_comparables.every_package): signed packages with their days, packages
  still open with their days so far, kept as censored, and canceled packages counted the way
  config/thresholds.toml's past_range.canceled_as_still_open says, so lane 1 and lane 2 censor the
  same packages.
- Its features, each as the package stood when it was advertised, or as planned on the training date
  for a package not yet advertised (sql/time_estimate/features.sql): method, category, market
  approach, review type, prequalification and estimated amount from the plan version public then;
  the plan's own planned duration from the package's first listing; country and region; the CPIA and
  WGI scores public that day, through ticket 17's lagged join (strata.lakehouse.governance); and the
  implementing agency's history, its packages signed by that day. No signed amount, Process Status,
  Actual Amount, revised plan date, later rating or ICR is read.
- Its ranges. Every config/models.toml calibration_every-th training package, in the order they were
  advertised, is kept out of the fit and sizes the ranges. Each point (a quarter, half, three quarters
  and 8 in 10 signed) is the split-conformal upper bound at its level, ceil((n + 1) p) / n: the
  Kaplan-Meier quantile of the calibration packages' log residuals, so packages still open count as
  censored, the past range's own Kaplan-Meier (strata.estimates.past_range). A package's point is its
  middle times exp(that quantile), in whole days, and in months to one decimal.
- When it abstains (estimate): as of a date before its training date (asof_before_training); with
  fewer than time_estimate.min_comparables comparables (too_few_comparables); for a what-if option
  fewer than what_if.min_subgroup comparables went with (too_few_in_subgroup); and for a package whose
  estimated amount or planned duration lies outside what it learned from (outside_training).

XGBoost is imported only when a model is fitted or used, so the app's server never needs it.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import statistics
from dataclasses import dataclass, field
from fractions import Fraction
from importlib import resources
from typing import Any

from strata.config import Thresholds, TimeEstimateSettings
from strata.estimates.past_range import QUARTERS, Observation, as_date, months, quantile, survival, whole
from strata.lakehouse import governance
from strata.tools.find_comparables import CATEGORIES

# The model's features, in its column order. A categorical feature is coded by the values it learned
# from; a value it never saw is missing to it.
CATEGORICAL = ("method", "category", "market_approach", "review_type", "prequalification", "country_code", "region")
NUMERIC = ("estimated_amount_usd", "planned_days", "agency_packages", "agency_median_days")


def _sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "time_estimate" / name).read_text()


def agency(step_reference: str) -> str:
    """The implementing agency's part of a STEP reference, with its country: KE-NWWDA."""
    return "-".join(step_reference.split("-")[:2])


# ── The packages as of a date ────────────────────────────────────────────

@dataclass
class Package:
    """One package as the model sees it: its features as of its feature date, and, when Prism could
    measure it on the reader's date, its days and whether it was signed."""

    step_reference: str
    feature_date: dt.date
    notice_date: dt.date | None
    listed: bool  # a plan version public on the feature date lists it
    features: dict[str, Any]
    days: int | None = None
    signed: bool | None = None


def packages_as_of(reader, settings: TimeEstimateSettings, only: str | None = None) -> dict[str, Package]:
    """Every package Prism knew of on the reader's date, with its features and, where it could be
    measured then, its days. The reader is the replay harness's (strata.estimates.harness.Reader), so
    nothing public after its date can reach the model. only keeps one package, by its STEP reference."""
    measured = {row["step_reference"]: row for row in reader.packages()}
    histories: dict[str, list[tuple[dt.date, int]]] = {}
    for row in measured.values():
        if not row["still_open"]:
            histories.setdefault(agency(row["step_reference"]), []).append((as_date(row["public_from"]), row["days"]))
    scores = _Governance(reader, settings.governance_indicators)
    found = {}
    for row in reader.rows(_sql("features.sql"), only=only):
        reference, day = row["step_reference"], as_date(row["feature_date"])
        history = [days for public, days in histories.get(agency(reference), []) if public <= day]
        notice_on, signing_on = as_date(row["planned_notice_on"]), as_date(row["planned_signing_on"])
        planned = (signing_on - notice_on).days if notice_on and signing_on and signing_on >= notice_on else None
        amount = row["estimated_amount_usd"]
        features = {
            "method": row["method"],
            "category": CATEGORIES.get(row["section"]) if row["section"] else row["notice_category"],
            "market_approach": row["market_approach"],
            "review_type": row["review_type"],
            "prequalification": row["prequalification"],
            "country_code": row["country_code"],
            "region": row["region"],
            "estimated_amount_usd": None if amount is None else float(amount),
            "planned_days": planned,
            "agency_packages": len(history),
            "agency_median_days": float(statistics.median(history)) if history else None,
            **{f"governance:{code}": scores.on(row["country_code"], code, day) for code in settings.governance_indicators},
        }
        package = Package(reference, day, as_date(row["notice_date"]), row["plan_document_id"] is not None, features)
        if reference in measured:
            package.days, package.signed = measured[reference]["days"], not measured[reference]["still_open"]
        found[reference] = package
    return found


def described_features(reader, values: dict[str, Any], settings: TimeEstimateSettings) -> dict[str, Any]:
    """The features of a package described by its criteria rather than a plan row, such as a package planned
    from a sentence (ticket 26): the Method, category, Market Approach, Review Type, Prequalification,
    estimated amount and country it was described with. It has no plan dates and no implementing agency yet,
    so those features are missing to the model, and its country's region and governance scores are those
    public on the reader's date."""
    country = values.get("country_code")
    regions = reader.rows(_sql("region.sql"), country_code=country) if country else []
    scores = _Governance(reader, settings.governance_indicators)
    amount = values.get("estimated_amount_usd")
    return {
        "method": values.get("method"), "category": values.get("category"),
        "market_approach": values.get("market_approach"), "review_type": values.get("review_type"),
        "prequalification": values.get("prequalification"), "country_code": country,
        "region": regions[0]["region"] if regions else None,
        "estimated_amount_usd": None if amount is None else float(amount), "planned_days": None,
        "agency_packages": None, "agency_median_days": None,
        **{f"governance:{code}": scores.on(country, code, reader.as_of) for code in settings.governance_indicators},
    }


class _Governance:
    """The CPIA and WGI scores public on a day, through ticket 17's one lagged join. A score can change
    only on a day the API published a version, so each package asks for the latest such day before its
    own, and each of those days is asked once."""

    def __init__(self, reader, indicators: tuple[str, ...]):
        self.reader, self.cache = reader, {}
        self.days: dict[tuple[str, str], list[dt.date]] = {}
        if indicators:
            for row in reader.rows(_sql("governance_dates.sql")):
                if row["indicator_id"] in indicators:
                    self.days.setdefault((row["country_code"], row["indicator_id"]), []).append(as_date(row["public_from"]))

    def on(self, country: str | None, indicator: str, day: dt.date) -> float | None:
        changes = [change for change in self.days.get((country, indicator), []) if change <= day]
        if not changes:
            return None
        key = (country, indicator, max(changes))
        if key not in self.cache:
            score = governance.score_as_of(self.reader.engine, country, indicator, key[2])
            self.cache[key] = None if score is None else float(self.reader.checked([score])[0]["value"])
        return self.cache[key]


# ── The learner ──────────────────────────────────────────────────────────

class XGBoostAFT:
    """XGBoost's accelerated failure time model: it learns log days from the features, with a package
    still open as an interval from its days so far to forever. It gives the middle in days."""

    name = "xgboost_aft"

    def __init__(self, settings: dict, feature_names: tuple[str, ...], feature_types: tuple[str, ...]):
        self.settings, self.feature_names, self.feature_types = dict(settings), feature_names, feature_types
        self.booster = None

    def _matrix(self, columns):
        import numpy as np
        import xgboost

        return xgboost.DMatrix(np.asarray(columns, dtype=float), feature_names=list(self.feature_names),
                               feature_types=list(self.feature_types), enable_categorical=True)

    def fit(self, columns, lower: list[float], upper: list[float]) -> XGBoostAFT:
        import numpy as np
        import xgboost

        matrix = self._matrix(columns)
        matrix.set_float_info("label_lower_bound", np.asarray(lower, dtype=float))
        matrix.set_float_info("label_upper_bound", np.asarray(upper, dtype=float))
        settings = dict(self.settings)
        rounds = int(settings.pop("num_boost_round"))
        signed = [low for low, high in zip(lower, upper) if low == high] or lower
        params = {"objective": "survival:aft", "eval_metric": "aft-nloglik", "tree_method": "hist",
                  "base_score": float(statistics.median(signed)), **settings}
        self.booster = xgboost.train(params, matrix, num_boost_round=rounds)
        return self

    def predict(self, columns) -> list[float]:
        return [float(value) for value in self.booster.predict(self._matrix(columns))]


LEARNERS = {XGBoostAFT.name: XGBoostAFT}


# ── The model ────────────────────────────────────────────────────────────

class NoModel(Exception):
    """The training data cannot give a model with ranges; reason is a code the model card explains."""

    def __init__(self, reason: str, **counts):
        super().__init__(reason)
        self.reason, self.counts = reason, counts


def conformal_level(n: int, share: Fraction) -> Fraction:
    """The split-conformal level for an upper bound at share p from n calibration packages."""
    return Fraction(math.ceil((n + 1) * share), n)


@dataclass
class TimeEstimateModel:
    """A fitted time estimate: the learner, the ranges' offsets and what it learned from."""

    learner: XGBoostAFT
    vocabularies: dict[str, list[str]]
    offsets: dict[str, float]  # each point's log offset from the middle, q25 to q80
    training_through: dt.date
    feature_ranges: dict[str, list[float] | None]
    training_packages: int
    calibration_packages: int
    calibration_still_open: int
    feature_names: tuple[str, ...] = field(default=())
    listed_packages: int = 0  # training packages a Procurement Plan listed by their feature date
    governance_packages: int = 0  # training packages with a governance score public by their feature date
    proper_packages: int = 0  # training packages the learner learned from: those that did not size the ranges
    # The day by which half of the calibration packages were signed (Kaplan-Meier, the still-open ones
    # counted as not signed yet), which the model card compares with the packages it had not seen.
    calibration_middle_days: int | None = None

    def columns(self, features: dict[str, Any]) -> list[float]:
        row = []
        for name in self.feature_names:
            value = features.get(name)
            if name in self.vocabularies:
                codes = self.vocabularies[name]
                value = codes.index(str(value)) if value is not None and str(value) in codes else None
            row.append(math.nan if value is None else float(value))
        return row

    def days(self, features: list[dict[str, Any]]) -> list[dict[str, int]]:
        """Each package's points in whole days."""
        middles = self.learner.predict([self.columns(item) for item in features])
        return [{name: max(0, whole(middle * math.exp(offset))) for name, offset in self.offsets.items()}
                for middle in middles]

    def example_inputs(self):
        import numpy as np

        return np.asarray([self.columns({})], dtype=float)

    def state_json(self) -> str:
        return json.dumps({"vocabularies": self.vocabularies, "offsets": self.offsets,
                           "training_through": self.training_through.isoformat(), "feature_ranges": self.feature_ranges,
                           "feature_names": list(self.feature_names), "training_packages": self.training_packages,
                           "calibration_packages": self.calibration_packages}, sort_keys=True)

    @classmethod
    def from_state(cls, state_json: str, booster_json: str, learner: str = "portable") -> TimeEstimateModel:
        """A registered model as strata.gold.time_estimate_model keeps it (ticket 26). The portable learner
        scores with no XGBoost, as the app does (strata.estimates.portable); learner="xgboost" loads the same
        JSON into XGBoost, which the nightly score task uses for every package at once."""
        from strata.estimates.portable import PortableLearner

        state = json.loads(state_json)
        names = tuple(state["feature_names"])
        if learner == "xgboost":
            import xgboost

            fitted = XGBoostAFT({}, names, tuple("c" if name in state["vocabularies"] else "q" for name in names))
            fitted.booster = xgboost.Booster()
            fitted.booster.load_model(bytearray(booster_json.encode()))
        else:
            fitted = PortableLearner(booster_json)
        return cls(fitted, state["vocabularies"], state["offsets"], dt.date.fromisoformat(state["training_through"]),
                   state["feature_ranges"], state["training_packages"], state["calibration_packages"], 0, names)

    def learned(self, feature: str, value) -> bool:
        """Whether the model learned from a package with this value of a categorical feature."""
        return value is not None and str(value) in self.vocabularies.get(feature, [])

    def outside(self, features: dict[str, Any]) -> dict | None:
        for name, bounds in self.feature_ranges.items():
            value = features.get(name)
            if bounds is not None and value is not None and not bounds[0] <= value <= bounds[1]:
                return {"feature": name, "value": value, "low": bounds[0], "high": bounds[1]}
        return None

    def estimate(self, features: dict[str, Any], comparables: int, as_of: dt.date, thresholds: Thresholds,
                 went_with: int | None = None) -> dict:
        """One package's time estimate, or an abstention with its reason and counts. went_with is the
        number of comparables that went with a what-if option, when the estimate is for that option."""
        fewest, fewest_in_subgroup = (int(thresholds.value("time_estimate.min_comparables")),
                                      int(thresholds.value("what_if.min_subgroup")))
        abstention = None
        if as_of < self.training_through:
            abstention = {"reason": "asof_before_training", "as_of": as_of.isoformat(),
                          "training_through": self.training_through.isoformat()}
        elif comparables < fewest:
            abstention = {"reason": "too_few_comparables", "count": comparables, "min_comparables": fewest}
        elif went_with is not None and went_with < fewest_in_subgroup:
            abstention = {"reason": "too_few_in_subgroup", "k": went_with, "count": comparables,
                          "min_subgroup": fewest_in_subgroup}
        elif (outside := self.outside(features)) is not None:
            abstention = {"reason": "outside_training", **outside}
        if abstention:
            return {"abstention": abstention}
        days = self.days([features])[0]
        return {"abstention": None, "days": days, **{name: float(months(value)) for name, value in days.items()},
                "training_through": self.training_through.isoformat()}


def _ranges(packages: list[Package], names: tuple[str, ...]) -> dict[str, list[float] | None]:
    found = {}
    for name in names:
        values = [item.features.get(name) for item in packages if item.features.get(name) is not None]
        found[name] = [min(values), max(values)] if values else None
    return found


def fit(training: list[Package], settings: TimeEstimateSettings, thresholds: Thresholds,
        training_through: dt.date) -> TimeEstimateModel:
    """A model fitted on the packages Prism could measure by training_through, its ranges sized on
    every calibration_every-th of them. Raises NoModel when the ranges cannot be sized."""
    ordered = sorted(training, key=lambda item: (item.notice_date, item.step_reference))
    every = settings.calibration_every
    calibration = ordered[every - 1::every]
    proper = [item for position, item in enumerate(ordered, 1) if position % every]
    fewest = int(thresholds.value("time_estimate.min_calibration_packages"))
    if len(calibration) < fewest:
        raise NoModel("too_few_calibration_packages", calibration_packages=len(calibration), min_calibration_packages=fewest)
    names = CATEGORICAL + NUMERIC + tuple(f"governance:{code}" for code in settings.governance_indicators)
    vocabularies = {name: sorted({str(item.features[name]) for item in ordered if item.features.get(name) is not None})
                    for name in CATEGORICAL}
    learner = LEARNERS[settings.learner](settings.learner_settings, names,
                                         tuple("c" if name in vocabularies else "q" for name in names))
    model = TimeEstimateModel(learner, vocabularies, {}, training_through, _ranges(ordered, settings.range_checked),
                              len(ordered), len(calibration), sum(1 for item in calibration if not item.signed), names,
                              sum(1 for item in ordered if item.listed),
                              sum(1 for item in ordered if any(item.features.get(f"governance:{code}") is not None
                                                               for code in settings.governance_indicators)),
                              len(proper),
                              quantile(survival([Observation(item.days, bool(item.signed)) for item in calibration]),
                                       QUARTERS["q50"]))
    lower = [float(max(item.days, 1)) for item in proper]
    learner.fit([model.columns(item.features) for item in proper], lower,
                [low if item.signed else math.inf for low, item in zip(lower, proper)])
    middles = learner.predict([model.columns(item.features) for item in calibration])
    residuals = [math.log(max(item.days, 1)) - math.log(middle) for item, middle in zip(calibration, middles)]
    # Kaplan-Meier over the residuals' ranks, which keeps their order and ties exactly.
    values = sorted(set(residuals))
    ranks = {value: rank for rank, value in enumerate(values)}
    curve = survival([Observation(ranks[residual], bool(item.signed)) for residual, item in zip(residuals, calibration)])
    for name, share in QUARTERS.items():
        level = conformal_level(len(calibration), share)
        rank = quantile(curve, level) if level <= 1 else None
        if rank is None:
            raise NoModel("range_not_reached", point=name, calibration_packages=len(calibration),
                          calibration_still_open=model.calibration_still_open)
        model.offsets[name] = values[rank]
    return model
