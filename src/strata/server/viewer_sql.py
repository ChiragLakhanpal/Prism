"""The queries the app runs as the viewer, and the engine each one runs on.

Strata acts as each viewer (ADR 0003). A request that reads data builds a new engine for its own
viewer, through a SqlAs function, and drops it when the request ends; nothing about a viewer is
kept between requests (CLAUDE.md rule 7). On the Databricks App that engine is the SQL warehouse,
called with the token the App forwarded for this viewer. The token goes straight into the
request's Authorization header, so the App's own credentials, which it also exports, never stand
in for a viewer (docs/PLAN.md section 12's trap: ask for personal-access-token authentication
explicitly). Each query is one file in sql/, written once in Databricks SQL.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import TypeVar

from strata.dbx import Viewer
from strata.lakehouse.engine import Engine, WarehouseEngine, http_transport

SQL = Path(__file__).resolve().parent / "sql"
# The source registry's word for a source fetched every day (config/sources.toml, cadence).
DAILY = "daily"

SqlAs = Callable[[Viewer], Engine]
T = TypeVar("T")


@cache
def query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _day(value) -> dt.date | None:
    """A date from DuckDB, or the text the warehouse writes it as."""
    if value is None or isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def data_through(engine: Engine) -> dt.date | None:
    """The data-freshness stamp's day, or None when no daily source has loaded anything yet."""
    rows = engine.run(query("data_through"), {"cadence": DAILY}).rows
    return _day(rows[0][0]) if rows else None


def warehouse_user(engine: Engine) -> str | None:
    """The user the warehouse says ran the query."""
    rows = engine.run(query("warehouse_user")).rows
    return str(rows[0][0]) if rows and rows[0][0] is not None else None


def run_as(sql_as: SqlAs, viewer: Viewer, read: Callable[[Engine], T]) -> T:
    """Build the viewer's own engine, read with it, and close it."""
    engine = sql_as(viewer)
    try:
        return read(engine)
    finally:
        close = getattr(engine, "close", None)
        if callable(close):
            close()


def warehouse_as_viewer(host: str, warehouse_id: str, timeout_seconds: float) -> SqlAs:
    """The SQL warehouse, called with each viewer's forwarded token."""
    def engine_for(viewer: Viewer) -> Engine:
        if not viewer.token:
            raise ValueError("A viewer with no forwarded token cannot query the warehouse.")
        transport = http_transport(host, viewer.token, timeout=max(1, round(timeout_seconds)))
        return WarehouseEngine(warehouse_id, transport, poll_seconds=1, timeout_seconds=timeout_seconds)
    return engine_for
