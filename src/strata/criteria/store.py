"""Where "Check your criteria" keeps its runs: strata.app.criteria_checks in the app state store, Lakebase on the
App (ADR 0005; src/strata/appstate), written as the app's own service principal (ticket 31).

A person's pasted qualification criteria are treated like an upload (CLAUDE.md rule 8): every read names the
owner it is for, bound per request from the viewer the App forwarded (src/strata/dbx.py), and the query filters
on it, so no route can read one person's text for another. Rows are only added (CLAUDE.md rule 5). The first use
makes the tables, as PackageStore does.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from importlib import resources
from threading import Lock

from strata import appstate
from strata.drafts.store import moment
from strata.lakehouse.engine import Engine

TABLE = "strata.app.criteria_checks"
COLUMNS = ("check_id", "owner_id", "package_key", "kind", "pasted_text", "status", "result", "comparables_signature",
           "records_through", "created_at", "public_from")
PACKAGE_RUN, COMPARISON = "package_run", "comparison"


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.criteria") / "sql" / f"{name}.sql").read_text()


def _day(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


@dataclass(frozen=True)
class Run:
    check_id: str
    kind: str
    pasted_text: str | None
    status: str
    result: dict | None
    comparables_signature: str | None
    records_through: dt.date | None
    created_at: dt.datetime


class CriteriaStore:
    """The runs in the app state store. engine() opens the engine that reads and writes them: the app's own."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine
        self._built = False
        self._building = Lock()

    @contextmanager
    def _open(self) -> Iterator[Engine]:
        engine = self.engine()
        try:
            if not self._built:
                with self._building:
                    if not self._built:
                        appstate.build(engine)
                        self._built = True
            yield engine
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                close()

    def save(self, check_id: str, owner_id: str, package_key: str, kind: str, status: str, at: dt.datetime,
             pasted_text: str | None = None, result: dict | None = None, signature: str | None = None,
             records_through: dt.date | None = None) -> None:
        """Add one row: a run's start or its end."""
        with self._open() as engine:
            engine.insert_rows(TABLE, COLUMNS, [(
                check_id, owner_id, package_key, kind, pasted_text, status,
                json.dumps(result, ensure_ascii=False, default=str) if result is not None else None, signature,
                records_through, at, at.date())])

    def latest(self, owner_id: str, package_key: str, kind: str) -> Run | None:
        """The owner's newest run of this kind on this package, or None. Nobody else's row is ever read."""
        if not owner_id:
            return None
        with self._open() as engine:
            result = engine.run(_sql("latest"), {"owner_id": owner_id, "package_key": package_key, "kind": kind})
        if not result.rows:
            return None
        row = dict(zip(result.columns, result.rows[0], strict=True))
        return Run(row["check_id"], row["kind"], row["pasted_text"], row["status"],
                   json.loads(row["result"]) if row["result"] else None, row["comparables_signature"] or None,
                   _day(row["records_through"]), moment(row["created_at"]))
