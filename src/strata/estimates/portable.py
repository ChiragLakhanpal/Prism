"""The time estimate's model, read from XGBoost's JSON with no XGBoost (ticket 26).

The app answers a package planned from a sentence a moment ago, which the nightly batch has not scored, by
scoring it on the request. The app installs no XGBoost (ops/app/requirements.txt), so PortableLearner walks the
trees of XGBoost's own JSON model (Booster.save_raw("json")) the way XGBoost's predictor does: each tree from
its root, a numeric split sending a value below its condition left, a categorical split sending the
categories it lists right, a missing value its default way, and the leaves summed in single precision from
the base margin, then exp() for the accelerated failure time model. tests/test_estimate_time.py checks that
it gives XGBoost's own middle for every package in the fixture.

The nightly job's score task scores with the same learner, so a stored score and a score made on a request
come from one piece of code (src/strata/estimates/scoring.py).
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass


def _single(value: float) -> float:
    """A number as XGBoost holds it: single precision."""
    return struct.unpack("f", struct.pack("f", value))[0]


@dataclass(frozen=True)
class _Tree:
    left: tuple[int, ...]
    right: tuple[int, ...]
    feature: tuple[int, ...]
    condition: tuple[float, ...]
    default_left: tuple[bool, ...]
    categorical: tuple[bool, ...]
    categories: dict[int, frozenset[int]]

    @classmethod
    def read(cls, tree: dict) -> _Tree:
        categories = {node: frozenset(tree["categories"][start:start + size])
                      for node, start, size in zip(tree["categories_nodes"], tree["categories_segments"],
                                                   tree["categories_sizes"])}
        return cls(tuple(tree["left_children"]), tuple(tree["right_children"]), tuple(tree["split_indices"]),
                   tuple(_single(value) for value in tree["split_conditions"]),
                   tuple(bool(value) for value in tree["default_left"]),
                   tuple(kind == 1 for kind in tree["split_type"]), categories)

    def leaf(self, row: list[float]) -> float:
        node = 0
        while self.left[node] != -1:
            value = row[self.feature[node]]
            if math.isnan(value):
                go_left = self.default_left[node]
            elif self.categorical[node]:
                go_left = int(value) not in self.categories.get(node, frozenset())
            else:
                go_left = value < self.condition[node]
            node = self.left[node] if go_left else self.right[node]
        return self.condition[node]


class PortableLearner:
    """XGBoost's accelerated failure time model, read from its JSON: it gives the middle in days, as
    strata.estimates.time_estimate.XGBoostAFT.predict does."""

    name = "xgboost_aft"

    def __init__(self, booster_json: str):
        document = json.loads(booster_json)
        learner = document["learner"]
        objective = learner["objective"]["name"]
        if objective != "survival:aft":
            raise ValueError(f"The time estimate's model must be XGBoost's survival:aft, not {objective}.")
        base = float(str(learner["learner_model_param"]["base_score"]).strip("[]"))
        self.margin = _single(math.log(base))
        self.trees = [_Tree.read(tree) for tree in learner["gradient_booster"]["model"]["trees"]]
        self.booster_json = booster_json

    def predict(self, columns) -> list[float]:
        found = []
        for row in columns:
            values = [_single(float(value)) if not math.isnan(float(value)) else math.nan for value in row]
            margin = self.margin
            for tree in self.trees:
                margin = _single(margin + tree.leaf(values))
            found.append(_single(math.exp(margin)))
        return found


def booster_json(learner) -> str:
    """A fitted learner's model as XGBoost's JSON: an XGBoost learner's booster, or a portable one's own."""
    if isinstance(learner, PortableLearner):
        return learner.booster_json
    return bytes(learner.booster.save_raw("json")).decode()


# ── strata.gold.time_estimate_model ──────────────────────────────────────

TABLE = "strata.gold.time_estimate_model"
COLUMNS = ("model", "version", "alias", "training_through", "booster_json", "state_json", "mlflow_run_id",
           "registered_at", "public_from")

# Which version is the newest public one: asked on every request, so it leaves out the trees.
LATEST = """
SELECT model, version, alias, training_through, mlflow_run_id, registered_at, public_from
FROM strata.gold.time_estimate_model
WHERE model = :model AND alias = :alias AND public_from <= :as_of
ORDER BY registered_at DESC, version DESC
LIMIT 1
"""

# That version's trees and state, which hold the whole model: read only when it has not been parsed yet.
TREES = """
SELECT booster_json, state_json
FROM strata.gold.time_estimate_model
WHERE model = :model AND version = :version AND alias = :alias AND public_from <= :as_of
ORDER BY registered_at DESC
LIMIT 1
"""


@dataclass(frozen=True)
class Kept:
    """One registered version, as the table keeps it, with its model ready to score."""

    name: str
    version: int
    alias: str
    model: object  # strata.estimates.time_estimate.TimeEstimateModel with a PortableLearner
    mlflow_run_id: str | None


def keep(engine, name: str, version: int, alias: str, model, mlflow_run_id: str | None, registered_at) -> None:
    """Keep a version the harness just registered, so the score task and the app can score with it."""
    engine.insert_rows(TABLE, COLUMNS, [(name, version, alias, model.training_through, booster_json(model.learner),
                                         model.state_json(), mlflow_run_id, registered_at, registered_at.date())])


def version_on(engine, name: str, as_of, alias: str = "champion") -> int | None:
    """The newest version registered with an alias and public on a day, without reading its trees, or None."""
    result = engine.run(LATEST, {"model": name, "alias": alias, "as_of": as_of})
    return int(dict(zip(result.columns, result.rows[0]))["version"]) if result.rows else None


def latest(engine, name: str, as_of, alias: str = "champion", learner: str = "portable") -> Kept | None:
    """The newest version registered with an alias and public on a day, or None when there is none. The app
    scores with the portable learner; the score task asks for XGBoost's (TimeEstimateModel.from_state)."""
    from strata.estimates.time_estimate import TimeEstimateModel

    result = engine.run(LATEST, {"model": name, "alias": alias, "as_of": as_of})
    if not result.rows:
        return None
    row = dict(zip(result.columns, result.rows[0]))
    key = (name, row["version"], str(row["registered_at"]), learner)
    model = _MODELS.get(key)
    if model is None:
        trees = engine.run(TREES, {"model": name, "version": row["version"], "alias": alias, "as_of": as_of})
        kept = dict(zip(trees.columns, trees.rows[0]))
        model = TimeEstimateModel.from_state(kept["state_json"], kept["booster_json"], learner)
        if len(_MODELS) > 2:  # the newest versions are kept: an older one is read again if asked for
            _MODELS.clear()
        _MODELS[key] = model
    return Kept(name, row["version"], row["alias"], model, row["mlflow_run_id"])


# The model last read, by its name, version and registration time, so a request does not parse its trees
# again. It holds nothing about a viewer: every viewer scores with the same champion.
_MODELS: dict[tuple, object] = {}
