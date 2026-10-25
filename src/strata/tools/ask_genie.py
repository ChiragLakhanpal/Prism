"""ask_genie: a structured question through Strata's Genie space, as the viewer (ticket 33; spec, "The tool
registry and the tools").

The registry (config/tools.toml) defines the tool; this module is its adapter. It asks the Genie space that
config/genie.toml defines with GenieClient (src/strata/genie/client.py):

- On the workspace, through the transport of the engine the app opened for the viewer, which carries the viewer's
  own token and the SQL warehouse's id (ADR 0003), and the space the environment's GENIE_SPACE_ID names. Nothing
  about the viewer outlives the call.
- On the fixture database, through FixtureGenie (src/strata/genie/fixture.py), which answers the space's benchmark
  questions from their ground-truth SQL.

Each row of the query Genie wrote and ran comes back with its values by column, typed from the result's column
types, and an evidence id made from the SQL and the row's place, strata.genie:<sha>/<n>, so the same query gives
the same ids. Decimals keep their cents as text, and dates are ISO dates.

The as-of date (ADR 0002). Genie cannot be trusted to filter on public_from, so ask_genie never asks it to.
Instead it reads the newest public_from of every table the space reads, which the rows are dated by. When the
as-of date is on or after it, no record Genie can read became public later, so Genie's answer is the answer as of
that date. When it is earlier, ask_genie gives no rows and abstains with as_of_before_records, and the agent uses
another tool. (A choice for the owner to confirm: ticket 33's report parks it.)
"""

from __future__ import annotations

import datetime as dt
import functools
import hashlib
import os
from decimal import Decimal
from typing import Any

from strata.genie import fixture as genie_fixture
from strata.genie import space as genie_space
from strata.genie.client import GenieClient, GenieError, Waits
from strata.lakehouse import catalog
from strata.lakehouse.engine import Engine
from strata.tools.registry import Call

PREFIX = "strata.genie"


def read_tables(space: genie_space.Space) -> list[str]:
    """Every gold table behind the space: each metric view's source and joins, and the tables it reads itself."""
    sources = catalog.metric_view_sources()
    found = {table for view in space.metric_views for table in sources.get(view, ())}
    return sorted(found | set(space.tables))


def records_through(engine: Engine, tables: list[str]) -> dt.date | None:
    """The newest public_from among the tables, which bounds every row Genie can return."""
    parts = " UNION ALL ".join(f"SELECT max(public_from) AS public_from FROM {table}"  # sql-lint: names only
                               for table in tables)
    result = engine.run(f"SELECT max(public_from) AS records_through FROM ({parts}) AS newest")  # sql-lint: names only
    value = result.rows[0][0] if result.rows else None
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


class Unavailable(Exception):
    """No Genie space to ask: the engine is not the warehouse, or the environment names no space."""


def genie_for(call: Call, space: genie_space.Space, environ=None) -> GenieClient:
    waits = Waits.from_thresholds(call.thresholds)
    if getattr(call.engine, "name", "") == "duckdb":
        return GenieClient(genie_fixture.FixtureGenie(call.engine, space.benchmarks), genie_fixture.SPACE,
                           genie_fixture.WAREHOUSE, waits)
    env = os.environ if environ is None else environ
    transport, warehouse = getattr(call.engine, "transport", None), getattr(call.engine, "warehouse_id", None)
    space_id = (env.get("GENIE_SPACE_ID") or "").strip()
    if not (transport and warehouse and space_id):
        raise Unavailable("The app has no Genie space to ask: GENIE_SPACE_ID is not set, or the engine is not the "
                          "SQL warehouse.")
    return GenieClient(transport, space_id, warehouse, waits)


def value(cell: Any) -> Any:
    """A typed cell as the tool returns it: numbers stay numbers, a decimal keeps its cents as text, a date is ISO."""
    if isinstance(cell, Decimal):
        return format(cell, "f")
    if isinstance(cell, dt.datetime):
        return cell.isoformat()
    if isinstance(cell, dt.date):
        return cell.isoformat()
    return cell


def _abstain(question: str, through: dt.date | None, reason: str, **detail) -> dict:
    return {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []},
            "abstention": {"reason": reason, **detail}, "question": question, "sql": None, "columns": [],
            "records_through": through.isoformat() if through else None}


@functools.lru_cache(maxsize=1)
def _space() -> tuple[genie_space.Space, tuple[str, ...]]:
    """The space and the tables behind it, read once per process: config/genie.toml, the metric views and the
    benchmark file do not change while the app runs."""
    space = genie_space.load()
    return space, tuple(read_tables(space))


def ask_genie(call: Call, question: str) -> dict:
    space, tables = _space()
    through = records_through(call.engine, list(tables))
    if through is not None and call.as_of < through:
        return _abstain(question, through, "as_of_before_records", records_through=through.isoformat())
    try:
        answer = genie_for(call, space).ask(question)
    except Unavailable as error:
        return _abstain(question, through, "genie_unavailable", detail=str(error))
    except GenieError as error:
        reason = "not_answered" if error.code == "genie_failed" else "genie_unavailable"
        return _abstain(question, through, reason, code=error.code)
    if answer.sql is None:
        return _abstain(question, through, "not_answered")
    digest = hashlib.sha256(" ".join(answer.sql.split()).encode()).hexdigest()[:16]
    dated = (through or call.as_of).isoformat()
    names = [name for name, _ in answer.columns]
    rows = [{"evidence_id": f"{PREFIX}:{digest}/{number}", "public_from": dated,
             "source": {"space": space.title, "sql": answer.sql},
             "values": {name: value(cell) for name, cell in zip(names, row, strict=True)}}
            for number, row in enumerate(answer.rows, 1)]
    limit = int(call.thresholds.value("genie.max_rows"))
    kept, left = rows[:limit], rows[limit:]
    not_used = [{"reason": "over_row_limit", "count": len(left), "evidence_ids": [row["evidence_id"] for row in left]}]
    return {"rows": kept, "coverage": {"matched": len(rows), "used": len(kept), "not_used": not_used if left else []},
            "abstention": None, "question": question, "sql": answer.sql,
            "columns": [{"name": name, "type": kind} for name, kind in answer.columns],
            "records_through": through.isoformat() if through else None}
