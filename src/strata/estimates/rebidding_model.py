"""The two rebidding models (ticket 28): the chance that a package like this one is advertised again.

- logistic: logistic regression with an L2 penalty on every weight but the intercept (config/models.toml,
  rebidding.logistic.l2), fitted by Newton's method in numpy.
- gbm: calibrated gradient boosting. XGBoost's binary logistic booster learns from the training packages but every
  calibration_every-th in the order they were advertised; those calibrate its margin with Platt scaling (a
  one-feature logistic regression), so its chances are calibrated on packages it did not learn from.

Both read the same features (FEATURES), each as the package stood when it was advertised, or as planned on the
day it is scored (sql/rebidding/features.sql and planned_features.sql). A feature with one value among the
training packages says nothing and is left out. A categorical feature is one-hot coded over the values the
training packages had, so a value the model never saw codes as none of them. The estimated amount is read as its
base-10 logarithm: z-scored for logistic regression, with a missing amount at the mean and a flag, and as it is
for the booster, which sends a missing value its own way.

brier() and calibration_error() score a model's chances against what happened: the mean squared difference, and
the expected calibration error over rebidding.calibration_bins equal bins from 0 to 1.

XGBoost is imported only when the booster is fitted or used, so the app's server never needs it.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from strata.tools.find_comparables import CATEGORIES

CATEGORICAL = ("method", "category", "market_approach", "review_type", "prequalification", "country_code", "region")
NUMERIC = ("estimated_amount_usd",)
FEATURES = CATEGORICAL + NUMERIC
PLATT_L2 = 1e-8  # a touch of penalty, so Platt scaling stays finite when the margins split its packages cleanly


class NoModel(Exception):
    """A model could not learn: its packages were all advertised again, or none was."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def features_of(row: dict) -> dict[str, Any]:
    """A feature query's row as the models read it: the plan table a row sits in names its category."""
    amount = row.get("estimated_amount_usd")
    return {"method": row.get("method"),
            "category": CATEGORIES.get(row["section"]) if row.get("section") else row.get("notice_category"),
            "market_approach": row.get("market_approach"), "review_type": row.get("review_type"),
            "prequalification": row.get("prequalification"), "country_code": row.get("country_code"),
            "region": row.get("region"),
            "estimated_amount_usd": None if amount is None or float(amount) <= 0 else math.log10(float(amount))}


# ── The features as numbers ──────────────────────────────────────────────

@dataclass
class Encoder:
    levels: dict[str, list[str]] = field(default_factory=dict)  # each categorical feature kept, with its values
    numeric: dict[str, dict] = field(default_factory=dict)  # each numeric feature kept: mean, scale, missing flag

    @classmethod
    def fit(cls, rows: list[dict]) -> Encoder:
        encoder = cls()
        for name in CATEGORICAL:
            values = sorted({str(row[name]) for row in rows if row[name] is not None})
            if len(values) + any(row[name] is None for row in rows) >= 2:
                encoder.levels[name] = values
        for name in NUMERIC:
            values = [row[name] for row in rows if row[name] is not None]
            missing = len(values) < len(rows)
            if len(set(values)) >= 2 or (values and missing):
                mean = float(np.mean(values))
                scale = float(np.std(values)) or 1.0
                encoder.numeric[name] = {"mean": mean, "scale": scale, "missing": missing}
        return encoder

    def matrix(self, rows: list[dict], trees: bool = False) -> np.ndarray:
        columns = []
        for name, values in self.levels.items():
            for value in values:
                columns.append([1.0 if row[name] is not None and str(row[name]) == value else 0.0 for row in rows])
        for name, kept in self.numeric.items():
            if trees:
                columns.append([math.nan if row[name] is None else row[name] for row in rows])
                continue
            columns.append([0.0 if row[name] is None else (row[name] - kept["mean"]) / kept["scale"] for row in rows])
            if kept["missing"]:
                columns.append([1.0 if row[name] is None else 0.0 for row in rows])
        return np.array(columns, dtype=float).T if columns else np.zeros((len(rows), 0))

    def state(self) -> dict:
        return {"levels": self.levels, "numeric": self.numeric}


# ── Logistic regression ──────────────────────────────────────────────────

def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def fit_logistic(x: np.ndarray, y: np.ndarray, l2: float, iterations: int = 200) -> np.ndarray:
    """The weights, intercept first, that minimize the log loss plus l2 / 2 times the squared weights, the
    intercept unpenalized, by Newton's method."""
    design = np.column_stack([np.ones(len(y)), x])
    rate = min(max(float(np.mean(y)), 1e-6), 1 - 1e-6)
    weights = np.zeros(design.shape[1])
    weights[0] = math.log(rate / (1 - rate))
    penalty = np.eye(design.shape[1]) * l2
    penalty[0, 0] = 0.0
    for _ in range(iterations):
        chance = _sigmoid(design @ weights)
        gradient = design.T @ (chance - y) + penalty @ weights
        hessian = design.T @ (design * (chance * (1 - chance))[:, None]) + penalty
        step = np.linalg.solve(hessian + np.eye(len(weights)) * 1e-12, gradient)
        weights = weights - step
        if np.max(np.abs(step)) < 1e-12:
            break
    return weights


def predict_logistic(weights: np.ndarray, x: np.ndarray) -> np.ndarray:
    return _sigmoid(weights[0] + x @ weights[1:])


# ── The models ───────────────────────────────────────────────────────────

@dataclass
class RebiddingModel:
    """A fitted model: its learner, its encoder and what it learned. chances() gives each package's chance."""

    learner: str
    encoder: Encoder
    weights: np.ndarray | None = None  # logistic regression's, intercept first
    booster: Any = None  # XGBoost's, for gbm
    platt: np.ndarray | None = None  # Platt scaling's intercept and slope on the booster's margin
    training_packages: int = 0
    advertised_again: int = 0
    calibration_packages: int = 0

    def chances(self, rows: list[dict]) -> list[float]:
        if self.learner == "logistic":
            return [float(p) for p in predict_logistic(self.weights, self.encoder.matrix(rows))]
        import xgboost

        margin = self.booster.predict(xgboost.DMatrix(self.encoder.matrix(rows, trees=True)), output_margin=True)
        return [float(p) for p in predict_logistic(self.platt, margin.reshape(-1, 1))]

    def state_json(self) -> str:
        """Everything the model needs to give a chance again, as JSON, for MLflow's model_state.json."""
        state = {"learner": self.learner, "encoder": self.encoder.state(),
                 "training_packages": self.training_packages, "advertised_again": self.advertised_again,
                 "calibration_packages": self.calibration_packages}
        if self.learner == "logistic":
            state["weights"] = [float(w) for w in self.weights]
        else:
            state["booster"] = bytes(self.booster.save_raw("json")).decode()
            state["platt"] = [float(w) for w in self.platt]
        return json.dumps(state, sort_keys=True)

    def pyfunc_inputs(self):
        """One package's features as MLflow's input example, for the model's signature in Unity Catalog."""
        import pandas

        return pandas.DataFrame([{name: None for name in FEATURES} | {"estimated_amount_usd": 6.0}])

    @classmethod
    def from_state(cls, text: str) -> RebiddingModel:
        state = json.loads(text)
        encoder = Encoder(state["encoder"]["levels"], state["encoder"]["numeric"])
        model = cls(state["learner"], encoder, training_packages=state["training_packages"],
                    advertised_again=state["advertised_again"], calibration_packages=state["calibration_packages"])
        if model.learner == "logistic":
            model.weights = np.array(state["weights"])
        else:
            import xgboost

            model.booster = xgboost.Booster()
            model.booster.load_model(bytearray(state["booster"].encode()))
            model.platt = np.array(state["platt"])
        return model


def _labels(rows: list[dict], outcomes: list[bool]) -> np.ndarray:
    y = np.array([1.0 if again else 0.0 for again in outcomes])
    if not len(rows) or y.min() == y.max():
        raise NoModel("one_outcome")
    return y


def fit_logistic_model(rows: list[dict], outcomes: list[bool], settings: dict) -> RebiddingModel:
    y = _labels(rows, outcomes)
    encoder = Encoder.fit(rows)
    weights = fit_logistic(encoder.matrix(rows), y, float(settings["l2"]))
    return RebiddingModel("logistic", encoder, weights=weights, training_packages=len(rows),
                          advertised_again=int(y.sum()))


def fit_gbm_model(rows: list[dict], outcomes: list[bool], settings: dict, calibration_every: int) -> RebiddingModel:
    """rows come in the order the packages were advertised; every calibration_every-th calibrates."""
    import xgboost

    y = _labels(rows, outcomes)
    calibrating = [index for index in range(len(rows)) if (index + 1) % calibration_every == 0]
    learning = [index for index in range(len(rows)) if (index + 1) % calibration_every]
    if y[calibrating].min(initial=1) == y[calibrating].max(initial=0) or y[learning].min() == y[learning].max():
        raise NoModel("one_outcome_in_calibration")
    encoder = Encoder.fit(rows)
    x = encoder.matrix(rows, trees=True)
    params = {key: value for key, value in settings.items() if key != "num_boost_round"}
    booster = xgboost.train({"objective": "binary:logistic", **params}, xgboost.DMatrix(x[learning], label=y[learning]),
                            num_boost_round=int(settings["num_boost_round"]))
    margin = booster.predict(xgboost.DMatrix(x[calibrating]), output_margin=True).reshape(-1, 1)
    platt = fit_logistic(margin, y[calibrating], PLATT_L2)
    return RebiddingModel("gbm", encoder, booster=booster, platt=platt, training_packages=len(rows),
                          advertised_again=int(y.sum()), calibration_packages=len(calibrating))


def fit(learner: str, rows: list[dict], outcomes: list[bool], settings, ) -> RebiddingModel:
    """One learner's model from its training packages, in the order they were advertised."""
    if learner == "logistic":
        return fit_logistic_model(rows, outcomes, settings.learner_settings[learner])
    if learner == "gbm":
        return fit_gbm_model(rows, outcomes, settings.learner_settings[learner], settings.calibration_every)
    raise ValueError(f"There is no rebidding learner {learner}. The learners are gbm and logistic.")


# ── Scores ───────────────────────────────────────────────────────────────

def brier(chances: list[float], outcomes: list[bool]) -> float:
    p, y = np.array(chances), np.array([1.0 if again else 0.0 for again in outcomes])
    return float(np.mean((p - y) ** 2))


def calibration_error(chances: list[float], outcomes: list[bool], bins: int) -> float:
    """The expected calibration error: in each of bins equal bins from 0 to 1, the gap between the mean chance and
    the share advertised again, weighted by the bin's share of the packages."""
    p, y = np.array(chances), np.array([1.0 if again else 0.0 for again in outcomes])
    index = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum((index == b).sum() / len(p) * abs(p[index == b].mean() - y[index == b].mean())
                     for b in range(bins) if (index == b).any()))
