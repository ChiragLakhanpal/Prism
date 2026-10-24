"""The evidence drawer's reads and writes (ticket 14).

- read(engine, evidence_id, as_of) gives one source by its evidence id, read as the viewer, in the shape
  the answer stream's evidence event carries ({id, kind, tool, row, highlights}), so a drawer opened from
  a link shows what a drawer opened from an answer shows. READERS names the reader for each kind of
  evidence id, by the table before its colon: adding a kind is one entry there (CLAUDE.md rule 9). A
  link carries no claim, so it has no highlights.
- OpenedLog records that a viewer opened a source, one row per viewer and evidence id in
  strata.ops.evidence_opened, and says which of an answer's sources a viewer has opened. It writes as
  the app's own service principal (ticket 06's settings), as the run log does, so no viewer's token can
  write another person's row. A write that fails is logged and changes nothing the viewer sees.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from functools import cache
from pathlib import Path

from strata.agent.verifier import labels
from strata.lakehouse.engine import Engine
from strata.server import baseline, summary
from strata.tools import search_passages

log = logging.getLogger("strata.server.evidence")
SQL = Path(__file__).resolve().parent / "sql" / "evidence"
TABLE = "strata.ops.evidence_opened"


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _passage(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    row = search_passages.read_passage(engine, key, as_of)
    return None if row is None else {"kind": "passage", "row": row}


# The reader for each kind of evidence id, by the table its id names before the colon: a passage, each
# record a project's Summary cites, and an agency's baseline, which check_plan's baseline reasons cite
# (ticket 21).
READERS: dict[str, Callable[[Engine, str, dt.date], dict | None]] = {
    search_passages.TABLE: _passage,
    **summary.RECORD_READERS,
    baseline.TABLE: baseline.read_record,
}


def read(engine: Engine, evidence_id: str, as_of: dt.date) -> dict | None:
    """The source this evidence id names, as the viewer could see it on the as-of date, or None."""
    table, _, key = evidence_id.partition(":")
    reader = READERS.get(table)
    if reader is None or not key or "," in key:
        return None
    found = reader(engine, key, as_of)
    if found is None:
        return None
    return {"id": evidence_id, "kind": found["kind"], "tool": None, **labels(found["row"]), "row": found["row"],
            "highlights": []}


def _close(engine) -> None:
    close = getattr(engine, "close", None)
    if callable(close):
        close()


class OpenedLog:
    """The sources each viewer opened. engine() opens the engine that reads and writes them."""

    def __init__(self, engine: Callable[[], Engine], now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)):
        self.engine = engine
        self.now = now

    def record(self, viewer_id: str, evidence_id: str, run_id: str | None, route: str | None) -> bool:
        """Record one open. Returns whether it was written."""
        try:
            engine = self.engine()
            try:
                engine.run(_query("record_opened"), {
                    "viewer_id": viewer_id, "evidence_id": evidence_id, "opened_at": self.now(),
                    "run_id": run_id, "route": route})
            finally:
                _close(engine)
        except Exception:  # the warehouse, the network or a token: none of them may change the page
            log.exception("I could not record that %s opened %s in %s.", viewer_id, evidence_id, TABLE)
            return False
        return True

    def opened(self, viewer_id: str, evidence_ids: list[str]) -> list[str]:
        """The evidence ids this viewer has opened, in the order asked."""
        asked = [evidence_id for evidence_id in dict.fromkeys(evidence_ids) if evidence_id and "," not in evidence_id]
        if not asked:
            return []
        try:
            engine = self.engine()
            try:
                result = engine.run(_query("opened"), {"viewer_id": viewer_id, "ids": ",".join(asked)})
            finally:
                _close(engine)
        except Exception:
            log.exception("I could not read which sources %s opened from %s.", viewer_id, TABLE)
            return []
        held = {row[0] for row in result.rows}
        return [evidence_id for evidence_id in asked if evidence_id in held]
