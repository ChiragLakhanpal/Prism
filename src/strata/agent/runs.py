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
import re
from collections.abc import Callable

from strata.agent.verifier import Verdict
from strata.config import load_sources, load_tools
from strata.dashboard import wording
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


# ── Lineage (ticket 45) ──────────────────────────────────────────────────
# Beside the run's row, the run log writes each tool call, each table each call read and each removed sentence's
# reason, so the dashboard's Governance page traces an answer's run ID to its tool calls and the tables they read
# (the 45 brief, section 6.2, tiles 24 to 26), and its AI quality page counts removed sentences by reason.

CALLS, READS, REMOVALS = "strata.ops.tool_calls", "strata.ops.tool_call_reads", "strata.ops.answer_removals"
CALL_COLUMNS = ("run_id", "call_order", "round", "tool", "inputs", "rows_returned", "took_ms", "evidence_ids",
                "abstention", "error", "private_upload", "called_at", "public_from")
READ_COLUMNS = ("run_id", "call_order", "tool", "table_name", "version_read", "sources", "read_at", "public_from")
REMOVAL_COLUMNS = ("run_id", "position", "reason", "removed_at", "public_from")
UPLOAD = re.compile(r"upload", re.I)  # an argument that names a private upload, such as upload_id (CLAUDE.md rule 8)
HISTORY = "DESCRIBE HISTORY {table} LIMIT 50"


def _inputs(arguments) -> tuple[str, bool]:
    """A call's arguments as name: value pairs, with a private upload's ID written in words, and whether it named one."""
    if not isinstance(arguments, dict):
        return str(arguments or ""), False
    private = wording.at("dash.gov.privateUpload")
    named = [name for name in arguments if UPLOAD.search(name)]
    pairs = [f"{name}: {private if name in named else value}" for name, value in arguments.items()]
    return "; ".join(pairs), bool(named)


def _when(value) -> dt.datetime | None:
    return dt.datetime.fromisoformat(value) if isinstance(value, str) and value else None


def _source_names(tool: str) -> str | None:
    tools, sources = load_tools(), load_sources()
    if tool not in tools:
        return None
    return "; ".join(sources[key].dataset_name for key in tools[tool].sources if key in sources) or None


def lineage_rows(row: dict) -> tuple[list[tuple], list[tuple], list[tuple]]:
    """The run's tool calls, the tables each read, and its removed sentences' reasons, as rows."""
    day = row["public_from"]
    calls, reads = [], []
    for order, note in enumerate(json.loads(row["tool_calls"] or "[]"), 1):
        inputs, private = _inputs(note.get("arguments"))
        called_at = _when(note.get("called_at"))
        calls.append((row["run_id"], order, note.get("round"), note.get("tool") or "", inputs, note.get("rows"),
                      note.get("took_ms"), ", ".join(note.get("evidence_ids") or []) or None, note.get("abstention"),
                      note.get("error") or (note.get("reason") if not note.get("ran", True) else None), private,
                      called_at, day))
        names = _source_names(note.get("tool") or "")
        reads += [(row["run_id"], order, note.get("tool") or "", table, None, names, called_at, day)
                  for table in note.get("reads") or []]
    removals = [(row["run_id"], position, item["reason"], row["finished_at"], day)
                for position, item in enumerate(json.loads(row["removed"] or "[]"), 1)]
    return calls, reads, removals


def version_read(engine: Engine, table: str, at: dt.datetime | None) -> int | None:
    """The table's Delta version when it was read: the newest one in its history committed by then. DuckDB keeps no
    versions, so there it is None, as it is whenever the history can't be read."""
    if at is None:
        return None
    try:
        history = engine.run(HISTORY.format(table=table))  # sql-lint: names only, a table name a query named
    except Exception:  # noqa: BLE001 - DuckDB has no DESCRIBE HISTORY, and a reader may lack the right to it
        return None
    columns = list(history.columns)
    if "version" not in columns or "timestamp" not in columns:
        return None
    found = []
    for values in history.rows:
        when = values[columns.index("timestamp")]
        when = when if isinstance(when, dt.datetime) else dt.datetime.fromisoformat(str(when).replace("Z", "+00:00"))
        when = when if when.tzinfo else when.replace(tzinfo=dt.UTC)
        if when <= at:
            found.append(int(values[columns.index("version")]))
    return max(found) if found else None


class RunLog:
    """Runs on their way to strata.ops.agent_runs. engine() opens the engine that writes them."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    def record(self, row: dict) -> bool:
        """Write one run's row, then its lineage. Returns whether the run's row was written. Lineage that fails is
        logged and leaves the run's row in place."""
        try:
            engine = self.engine()
            try:
                engine.insert_rows(TABLE, COLUMNS, [tuple(row[column] for column in COLUMNS)])
                self._lineage(engine, row)
            finally:
                close = getattr(engine, "close", None)
                if callable(close):
                    close()
        except Exception:  # the warehouse, the network or a token: none of them may change an answer
            log.exception("I could not write run %s to %s.", row.get("run_id"), TABLE)
            return False
        return True

    def _lineage(self, engine: Engine, row: dict) -> None:
        try:
            calls, reads, removals = lineage_rows(row)
            versions = {}
            reads = [(*read[:4], versions.setdefault((read[3], read[6]), version_read(engine, read[3], read[6])),
                      *read[5:]) for read in reads]
            for table, columns, rows in ((CALLS, CALL_COLUMNS, calls), (READS, READ_COLUMNS, reads),
                                         (REMOVALS, REMOVAL_COLUMNS, removals)):
                if rows:
                    engine.insert_rows(table, columns, rows)
        except Exception:  # noqa: BLE001 - lineage must never cost the run its row
            log.exception("I could not write the lineage of run %s.", row.get("run_id"))
