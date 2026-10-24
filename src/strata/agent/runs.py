"""The run log: one row in strata.ops.agent_runs for each run of the answer stream.

The stream writes the row once the done event is sent, so no answer waits for the warehouse. A write
that fails is logged and never changes what the viewer saw. A row keeps the viewer's user id, never
their email, because every account user can read strata.ops. On the Databricks App the engine is the
app's own service principal (ticket 06's settings), so no viewer's token can write another person's
row; in the tests it is a DuckDB file.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from collections.abc import Callable

from strata.agent.verifier import Verdict
from strata.harness.turn import Turn
from strata.lakehouse.engine import Engine

log = logging.getLogger("strata.agent.runs")
TABLE = "strata.ops.agent_runs"
COLUMNS = ("run_id", "viewer_id", "question", "scope", "as_of", "view", "language", "status", "error_code", "agent",
           "agent_version", "tool_rounds", "tool_calls", "response_ids", "sentences_written", "sentences_kept",
           "sentences_removed", "numbers_total", "numbers_matched", "dates_total", "dates_matched", "quotes_total",
           "quotes_found", "sources_total", "sources_returned", "removed", "application_insights_trace_id",
           "mlflow_trace_id", "started_at", "finished_at", "public_from")


def run_row(turn: Turn, verdict: Verdict | None, error_code: str | None, started_at: dt.datetime,
            finished_at: dt.datetime) -> dict:
    """The run's row: what was asked, what the agent did and what the verifier found."""
    counts = verdict.counts() if verdict is not None else None

    def count(group: str, key: str) -> int | None:
        return counts[group][key] if counts else None

    trace = turn.trace
    return {
        "run_id": turn.run_id, "viewer_id": turn.viewer.user_id, "question": turn.question, "scope": turn.scope.chip,
        "as_of": min(turn.notes.as_of or turn.scope.as_of or finished_at.date(), finished_at.date()),
        "view": turn.scope.view,
        "language": turn.scope.language, "status": "failed" if error_code else "answered", "error_code": error_code,
        "agent": turn.notes.agent, "agent_version": turn.notes.agent_version, "tool_rounds": turn.notes.tool_rounds,
        "tool_calls": json.dumps(turn.notes.tool_calls, ensure_ascii=False, default=str),
        "response_ids": json.dumps(turn.notes.response_ids),
        "sentences_written": count("sentences", "written"), "sentences_kept": count("sentences", "kept"),
        "sentences_removed": count("sentences", "removed"),
        "numbers_total": count("numbers", "total"), "numbers_matched": count("numbers", "matched"),
        "dates_total": count("dates", "total"), "dates_matched": count("dates", "matched"),
        "quotes_total": count("quotes", "total"), "quotes_found": count("quotes", "found"),
        "sources_total": count("sources", "total"), "sources_returned": count("sources", "returned"),
        "removed": json.dumps([{"sentence": sentence.claim.sentence, "reason": sentence.reasons[0].code}
                               for sentence in (verdict.removed if verdict else [])], ensure_ascii=False),
        "application_insights_trace_id": trace.application_insights if trace else None,
        "mlflow_trace_id": trace.mlflow if trace else None,
        "started_at": started_at, "finished_at": finished_at, "public_from": finished_at.astimezone(dt.UTC).date(),
    }


class RunLog:
    """Runs on their way to strata.ops.agent_runs. engine() opens the engine that writes them."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    def record(self, row: dict) -> bool:
        """Write one run's row. Returns whether it was written."""
        try:
            engine = self.engine()
            try:
                engine.insert_rows(TABLE, COLUMNS, [tuple(row[column] for column in COLUMNS)])
            finally:
                close = getattr(engine, "close", None)
                if callable(close):
                    close()
        except Exception:  # the warehouse, the network or a token: none of them may change an answer
            log.exception("I could not write run %s to %s.", row.get("run_id"), TABLE)
            return False
        return True
