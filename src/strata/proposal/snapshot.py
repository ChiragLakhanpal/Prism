"""The measures snapshot (ticket 46; the 46 brief, section 20; the 47 brief, section 6.1).

pull() runs every query in the results register through the engine adapter, on the workspace's SQL warehouse
(WarehouseEngine) or on a DuckDB file (DuckDBEngine.open(path, read_only=True)), and returns one dated snapshot: each
result's numbers, the day it was measured and the run that measured it. The build fills the proposal from it, and the
deck (ticket 47) reads the same file by the same keys, so the two cannot disagree and neither queries the warehouse
when it is shown.

A result whose query finds nothing is kept with "measured": false, so the build can say which one is missing. Every
query binds its values as parameters; the pull adds today, the 90 days to today (date_from and date_to, as the
dashboard's pages default to), measure_date, an empty budget_period and run_id, and the fewest cases for a share and
for a percentage from config/thresholds.toml.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from importlib import resources
from pathlib import Path

from strata.config import load_thresholds
from strata.lakehouse.engine import Engine
from strata.proposal.register import Result, load_results

SNAPSHOT_FILE = Path(__file__).resolve().parents[3] / "docs" / "proposal" / "snapshot.json"
DAYS = 90


def _sql(name: str) -> str:
    return (resources.files("strata.proposal") / "sql" / name).read_text()


def _query(result: Result) -> str:
    if result.query.startswith("dashboard:"):
        from strata.dashboard import render

        return render.query(result.query.split(":", 1)[1])
    return _sql(result.query)


def _plain(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return value


def _rows(engine: Engine, sql: str, params: dict) -> list[dict]:
    bound = {key: value for key, value in params.items() if f":{key}" in sql}
    result = engine.run(sql, bound)
    return [{column: _plain(value) for column, value in zip(result.columns, row)} for row in result.rows]


def _bindings(today: dt.date) -> dict:
    thresholds = load_thresholds()
    return {"today": today, "date_from": today - dt.timedelta(days=DAYS), "date_to": today, "measure_date": today,
            "budget_period": "", "run_id": "",
            "fewest_for_a_share": int(thresholds.value("data_readiness.fewest_for_a_share")),
            "fewest_for_a_percentage": int(thresholds.value("data_readiness.fewest_for_a_percentage"))}


def _none_yet() -> str:
    """The words the dashboard's loop table shows before an indicator has a value."""
    from strata.dashboard import wording

    return wording.at("dash.ai.noneYet")


def _chosen(rows: list[dict], row: dict | None) -> dict | None:
    for found in rows:
        if all(found.get(column) == wanted for column, wanted in (row or {}).items()):
            return found
    return None


def measure(engine: Engine, result: Result, today: dt.date) -> dict:
    """One result's values, as its query returns them, with when it was measured and in which run."""
    params = {**_bindings(today), **result.params}
    rows = _rows(engine, _query(result), params)
    if result.form == "series":
        meta = _rows(engine, _sql(result.meta), params)[0] if result.meta else (rows[0] if rows else {})
        series = [{key: value for key, value in row.items() if key not in ("run_id", "measured_on")} for row in rows]
        # A series of zeros, such as test years with no package of known outcome, measured nothing.
        counted = any(isinstance(value, int | float) and not isinstance(value, bool) and value > 0
                      for row in series for key, value in row.items() if key not in ("label", "fiscal_year"))
        return {"measured": counted and bool(meta.get("measured_on")), "series": series, "run_id": meta.get("run_id"),
                "measured_on": meta.get("measured_on")}
    found = _chosen(rows, result.row)
    if result.query.startswith("dashboard:") and found is not None:
        names = {"n": "numerator", "d": "denominator", "value": "value", **result.columns}
        found = {key: found.get(column) for key, column in names.items()}
        if result.meta:
            meta = _rows(engine, _sql(result.meta), params)
            found |= {key: meta[0].get(key) for key in ("run_id", "measured_on")} if meta else {}
        if "measured_on" not in found or found.get("measured_on") is None:
            found["measured_on"] = found.get("latest") or found.get("month")
    if found is None:
        return {"measured": False}
    values = {key: value for key, value in found.items() if value is not None}
    measured = any(values.get(key) is not None for key in ("n", "value", "text", "low", "paragraph"))
    if result.form == "text" and values.get("text") in (None, "", _none_yet()):
        measured = False
    if result.form in ("ratio",) and not values.get("d"):
        measured = False
    return {"measured": measured and bool(values.get("measured_on")), **values}


def pull(engine: Engine, today: dt.date, results: dict[str, Result] | None = None, source: str = "") -> dict:
    """The snapshot: every result in the register, measured on the engine as of today."""
    results = load_results() if results is None else results
    return {"pulled_on": today.isoformat(), "source": source,
            "results": {key: measure(engine, result, today) for key, result in results.items()}}


def write(snapshot: dict, path: Path = SNAPSHOT_FILE) -> Path:
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=False) + "\n")
    return path


def read(path: Path = SNAPSHOT_FILE) -> dict:
    return json.loads(path.read_text())
