"""Keeping the other report of a disagreement (ticket 23; the 23 brief, section 5.5).

A person who reads a disagreement under an answer or in a draft can keep the side Prism does not lean on, with a
reason, and later go back to Prism's choice. Each choice is one new row in strata.ops.disagreement_choices, which
the evidence pack (ticket 35) reads: the latest row per viewer, disagreement and answer or draft, with every reason
given. Nothing is changed or deleted (CLAUDE.md rule 5), and the answer or draft is never rewritten: Prism states
only what its tools returned.

ChoiceLog writes and reads those rows as the app's own service principal, as the evidence drawer's OpenedLog does,
so no viewer's token can write another person's row; the viewer is the one the Databricks App forwarded for the
request (src/strata/server/app.py, current_viewer), never a module global. sides() reads the disagreement as the
viewer, so a route accepts only one of its own two sides.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from collections.abc import Callable
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import Engine

log = logging.getLogger("strata.server.choices")
SQL = Path(__file__).resolve().parent / "sql" / "choices"
TABLE = "strata.ops.disagreement_choices"
REASON_LIMIT = 500  # the reason field's limit (the 23 brief, section 5.5; the shared Reason field)


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _close(engine) -> None:
    close = getattr(engine, "close", None)
    if callable(close):
        close()


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.astimezone(dt.UTC).isoformat() if value.tzinfo else value.replace(tzinfo=dt.UTC).isoformat()
    return str(value)


def sides(engine: Engine, disagreement_id: str) -> dict | None:
    """The disagreement's two sides and the one Prism leans on, read as the viewer, or None."""
    result = engine.run(_query("disagreement"), {"disagreement_id": disagreement_id})
    if not result.rows:
        return None
    row = dict(zip(result.columns, result.rows[0]))
    return {"sides": (row["first_assertion_id"], row["second_assertion_id"]), "leaned": row["lean_assertion_id"]}


def new_choice_id() -> str:
    return f"choice-{uuid.uuid4().hex[:16]}"


class ChoiceLog:
    """The choices people made. engine() opens the engine that reads and writes them as the app itself."""

    def __init__(self, engine: Callable[[], Engine], now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC),
                 new_id: Callable[[], str] = new_choice_id):
        self.engine = engine
        self.now = now
        self.new_id = new_id

    def record(self, viewer: str, disagreement_id: str, kept: str, leaned: str, reason: str | None,
               run_id: str | None, draft_id: str | None) -> dict | None:
        """Add one choice. Returns it as the route answers with it, or None when it could not be written."""
        choice = {"choice_id": self.new_id(), "viewer": viewer, "disagreement_id": disagreement_id,
                  "kept_assertion_id": kept, "leaned_assertion_id": leaned, "reason": reason or None,
                  "run_id": run_id or None, "draft_id": draft_id or None, "made_at": self.now()}
        try:
            engine = self.engine()
            try:
                engine.run(_query("record"), choice)
            finally:
                _close(engine)
        except Exception:  # the warehouse, the network or a token: the page says the save failed
            log.exception("I could not record %s's choice on disagreement %s in %s.", viewer, disagreement_id, TABLE)
            return None
        return self._shown(choice)

    def latest(self, viewer: str, disagreement_id: str, run_id: str | None, draft_id: str | None) -> dict | None:
        """The latest choice this viewer made on the disagreement for the answer or the draft, or None."""
        engine = self.engine()
        try:
            result = engine.run(_query("latest"), {"viewer": viewer, "disagreement_id": disagreement_id,
                                                   "run_id": run_id or "", "draft_id": draft_id or ""})
        finally:
            _close(engine)
        return self._shown(dict(zip(result.columns, result.rows[0]))) if result.rows else None

    @staticmethod
    def _shown(choice: dict) -> dict:
        return {"choice_id": choice["choice_id"], "kept_assertion_id": choice["kept_assertion_id"],
                "leaned_assertion_id": choice["leaned_assertion_id"], "reason": choice["reason"],
                "run_id": choice["run_id"], "draft_id": choice["draft_id"], "made_at": _iso(choice["made_at"]),
                "kept_other": choice["kept_assertion_id"] != choice["leaned_assertion_id"]}
