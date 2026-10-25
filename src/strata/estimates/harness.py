"""The replay harness (spec, seam 5): freeze Strata at a cutoff date, run a scorer, and score the result
against what became public later.

Given a cutoff and a scorer, replay() hands the scorer two readers: one frozen at the cutoff, for
every input, and one at the outcomes date, for what happened. Each reader binds its date to every query
as the :as_of parameter and refuses any row whose public_from is later than that date, so an input
made public after the cutoff can never reach a scorer by mistake (ADR 0002). It also calls a registry
tool, such as find_comparables, with its date as the as-of date. The scorer returns its scores; the
harness logs them to the tracker (MLflow on the workspace, strata.estimates.tracking) and appends them
to strata.ops.evaluation_result under the run's id with the tracker's run id.

A scorer is any object with a name and a score(replay) method that returns a Scored. The time
estimate's backtest (strata.estimates.backtest) is the first; retrieval evaluation, the hindsight
test, per-step delay and the signals' track record plug in the same way, each with its own segments
and measures. Results are only ever appended, so a reader takes the latest run of a scorer.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from strata.config import Thresholds, load_thresholds
from strata.dbx import Viewer
from strata.lakehouse.engine import Engine

TABLE = "strata.ops.evaluation_result"
COLUMNS = ("run_id", "scorer", "model", "segment_kind", "segment", "measure", "value", "value_text", "cutoff",
           "outcomes_through", "mlflow_run_id", "ran_at", "public_from")
# Who the harness's tool calls run as: the harness itself, never a viewer.
HARNESS = Viewer(name="Strata's replay harness")

LATEST_RUN = """
SELECT run_id
FROM strata.ops.evaluation_result
WHERE scorer = :scorer
ORDER BY ran_at DESC, run_id DESC
LIMIT 1
"""

RUN_ROWS = """
SELECT run_id, scorer, model, segment_kind, segment, measure, value, value_text, cutoff, outcomes_through,
  mlflow_run_id, ran_at, public_from
FROM strata.ops.evaluation_result
WHERE run_id = :run_id
ORDER BY segment_kind, segment, measure
"""


class LeakageError(RuntimeError):
    """A scorer read a row that became public after the date it was frozen at."""


@dataclass(frozen=True)
class Window:
    """One replay: the cutoff Strata is frozen at, and the date the outcomes are read as of."""

    cutoff: dt.date
    outcomes_through: dt.date
    segment_kind: str
    segment: str


@dataclass(frozen=True)
class Score:
    """One measure of one segment. A number goes in value, a date or a list in text."""

    measure: str
    value: float | int | None = None
    text: str | None = None


@dataclass
class Scored:
    """What a scorer returns for one window: its scores, the parameters and model to log, and the model
    itself for the caller, such as a backtest year's model."""

    scores: list[Score]
    params: dict[str, Any] = field(default_factory=dict)
    model: Any = None


class Reader:
    """Every read a scorer makes, at one date: queries get it as :as_of, tools as their as-of date."""

    def __init__(self, engine: Engine, as_of: dt.date, thresholds: Thresholds):
        self.engine, self.as_of, self.thresholds = engine, as_of, thresholds

    def rows(self, sql: str, **params) -> list[dict]:
        if "as_of" in params:
            raise ValueError("The reader sets :as_of itself, to the date it was frozen at.")
        result = self.engine.run(sql, {**params, "as_of": self.as_of})
        return self.checked([dict(zip(result.columns, row)) for row in result.rows])

    def checked(self, rows: list[dict]) -> list[dict]:
        """Rows read some other way, checked like the reader's own."""
        for row in rows:
            public = _date(row.get("public_from"))
            if public is not None and public > self.as_of:
                raise LeakageError(f"A row public on {public} reached a scorer frozen at {self.as_of}: {row}")
        return rows

    def packages(self) -> list[dict]:
        """Every package Strata could measure on this date, by the past range's rules
        (strata.tools.find_comparables.every_package)."""
        from strata.tools.find_comparables import Limits, every_package

        return self.checked(every_package(self.engine, self.as_of, Limits.from_thresholds(self.thresholds)))

    def call(self, tool: str, **arguments) -> dict:
        """A registry tool, called as the harness with this reader's date as its as-of date."""
        from strata.tools import registry

        context = registry.Context(engine=self.engine, viewer=HARNESS, as_of=self.as_of, thresholds=self.thresholds)
        return registry.call(tool, arguments, context)


@dataclass(frozen=True)
class Replay:
    """What a scorer gets: the window, and a reader frozen at the cutoff and one at the outcomes date."""

    window: Window
    inputs: Reader
    outcomes: Reader
    thresholds: Thresholds


class Scorer(Protocol):
    name: str
    model: str | None

    def score(self, replay: Replay) -> Scored: ...


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def new_run_id(scorer: str, ran_at: dt.datetime) -> str:
    return f"{scorer}-{ran_at:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"


def replay(engine: Engine, scorer: Scorer, window: Window, tracker, run_id: str, ran_at: dt.datetime,
           store: Engine | None = None, thresholds: Thresholds | None = None) -> Scored:
    """Run one scorer for one window, log it to the tracker and append its scores to the results table."""
    limits = thresholds or load_thresholds()
    frozen = Replay(window, Reader(engine, window.cutoff, limits), Reader(engine, window.outcomes_through, limits),
                    limits)
    scored = scorer.score(frozen)
    params = {"scorer": scorer.name, "run_id": run_id, "cutoff": window.cutoff.isoformat(),
              "outcomes_through": window.outcomes_through.isoformat(), window.segment_kind: window.segment,
              **scored.params}
    mlflow_run = tracker.start_run(f"{scorer.name} {window.segment}", params)
    tracker.log_metrics(mlflow_run, {score.measure: score.value for score in scored.scores if score.value is not None})
    if scored.model is not None:
        tracker.log_model(mlflow_run, scored.model)
    tracker.end_run(mlflow_run)
    write(store or engine, [row(run_id, scorer, window, score, mlflow_run, ran_at) for score in scored.scores])
    return scored


def row(run_id: str, scorer: Scorer, window: Window | None, score: Score, mlflow_run: str | None,
        ran_at: dt.datetime, segment_kind: str | None = None, segment: str | None = None) -> dict:
    return {"run_id": run_id, "scorer": scorer.name, "model": scorer.model,
            "segment_kind": segment_kind or window.segment_kind, "segment": segment or window.segment,
            "measure": score.measure, "value": None if score.value is None else float(score.value),
            "value_text": score.text, "cutoff": window.cutoff if window else None,
            "outcomes_through": window.outcomes_through if window else None, "mlflow_run_id": mlflow_run,
            "ran_at": ran_at, "public_from": ran_at.astimezone(dt.UTC).date()}


def write(engine: Engine, rows: list[dict]) -> int:
    """Append rows to strata.ops.evaluation_result. Nothing is ever replaced or removed."""
    return engine.insert_rows(TABLE, COLUMNS, [tuple(item[column] for column in COLUMNS) for item in rows]) if rows else 0


def latest_run(engine: Engine, scorer: str) -> str | None:
    """The newest run of a scorer, or None when it has never run."""
    result = engine.run(LATEST_RUN, {"scorer": scorer})
    return result.rows[0][0] if result.rows else None


def run_rows(engine: Engine, run_id: str) -> list[dict]:
    result = engine.run(RUN_ROWS, {"run_id": run_id})
    return [dict(zip(result.columns, values)) for values in result.rows]


def segments(rows: list[dict]) -> dict[tuple[str, str], dict[str, Any]]:
    """A run's rows as one record per segment: each measure's number (whole when it is whole) or text,
    with the segment's dates and MLflow run id."""
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for item in rows:
        record = found.setdefault((item["segment_kind"], item["segment"]), {
            "run_id": item["run_id"], "model": item["model"], "cutoff": _date(item["cutoff"]),
            "outcomes_through": _date(item["outcomes_through"]), "mlflow_run_id": item["mlflow_run_id"],
            "ran_at": item["ran_at"]})
        value = item["value"]
        if value is None:
            record[item["measure"]] = item["value_text"]
        else:
            value = float(value)
            record[item["measure"]] = int(value) if value.is_integer() else value
    return found


def as_json(value: Mapping | list) -> str:
    return json.dumps(value, sort_keys=True, default=str)
