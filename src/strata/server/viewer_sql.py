"""The shell's queries, which the app runs as the viewer: the data date and who the warehouse
says is asking.

Each request reads with the engine src/strata/server/engines.py makes for its own viewer, and
drops it when the request ends; nothing about a viewer is kept between requests (CLAUDE.md
rule 7). Each query is one file in sql/, written once in Databricks SQL.
"""

from __future__ import annotations

import datetime as dt
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import Engine

SQL = Path(__file__).resolve().parent / "sql"
# The source registry's word for a source fetched every day (config/sources.toml, cadence).
DAILY = "daily"


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
