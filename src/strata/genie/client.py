"""The Genie conversation API, asked as one viewer (ticket 33; ADR 0003; PLAN.md section 12, "Genie stalls on a
cold warehouse").

GenieClient asks one question of one Genie space with a transport that carries one person's token: in the app,
the viewer's own, from the engine the request opened (src/strata/server/engines.py); in the full gate, the env
file's. It keeps nothing about the viewer after the call. Written from ticket 33's description of fairshare's
_genie_ask and warm_warehouse, because fairshare could not be read on the build machine. In order:

1. It starts the warehouse first. Free Edition stops it after 10 idle minutes, and Genie then sits in
   PENDING_WAREHOUSE far longer than a direct start takes. A viewer who may not start a warehouse, but may use it,
   wakes it with a one-row query instead, which starts a stopped warehouse too. It waits at most
   [genie] warehouse_start_seconds.
2. It asks Genie. Genie answers too many questions in a minute with 429, so the client waits and asks again,
   starting at backoff_first_seconds and doubling, never longer than backoff_max_seconds at once.
3. It polls the message until Genie is done, at most answer_seconds from when it asked.
4. It reads the query attachment's result in every chunk, and types each cell from its column's type. Genie
   returns every cell as text, and the verifier's first check matches a sentence's numbers against typed values.

An answer with no query, such as Genie asking which country you mean, comes back with its text and no rows.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from strata.config import Thresholds
from strata.lakehouse.engine import EngineError, PermissionDenied, Transport

GENIE = "/api/2.0/genie/spaces"
WAREHOUSES = "/api/2.0/sql/warehouses"
STATEMENTS = "/api/2.0/sql/statements/"
DONE = ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED")
WHOLE = ("BYTE", "SHORT", "INT", "INTEGER", "LONG", "BIGINT", "TINYINT", "SMALLINT")
FRACTION = ("FLOAT", "DOUBLE", "REAL")


class GenieError(RuntimeError):
    """Genie gave no answer, with a code: warehouse_cold, genie_slow, genie_failed or rate_limited."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code


@dataclass(frozen=True)
class Waits:
    """How long the client waits, from config/thresholds.toml's [genie]."""

    warehouse_start_seconds: float
    answer_seconds: float
    poll_seconds: float
    backoff_first_seconds: float
    backoff_max_seconds: float

    @classmethod
    def from_thresholds(cls, thresholds: Thresholds) -> Waits:
        return cls(*(float(thresholds.value(f"genie.{name}")) for name in (
            "warehouse_start_seconds", "answer_seconds", "poll_seconds", "backoff_first_seconds",
            "backoff_max_seconds")))


@dataclass
class Answer:
    """What Genie answered: its message, the SQL it wrote and ran, the columns with their types, the typed rows,
    and any text it wrote beside them."""

    conversation_id: str
    message_id: str
    sql: str | None
    columns: list[tuple[str, str]] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    text: str | None = None


def typed(value: str | None, type_name: str) -> Any:
    """One cell of a Genie result as its column's type says."""
    if value is None:
        return None
    kind = (type_name or "STRING").upper().split("(")[0]
    try:
        if kind in WHOLE:
            return int(value)
        if kind in FRACTION:
            return float(value)
        if kind == "DECIMAL":
            return Decimal(value)
        if kind == "BOOLEAN":
            return value.lower() == "true"
        if kind == "DATE":
            return dt.date.fromisoformat(value[:10])
        if kind in ("TIMESTAMP", "TIMESTAMP_NTZ"):
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, InvalidOperation):
        return value
    return value


class GenieClient:
    def __init__(self, transport: Transport, space_id: str, warehouse_id: str, waits: Waits,
                 sleep: Callable[[float], None] | None = None, clock: Callable[[], float] | None = None):
        self.transport, self.space_id, self.warehouse_id, self.waits = transport, space_id, warehouse_id, waits
        self.sleep, self.clock = sleep or time.sleep, clock or time.monotonic

    # ── 1. The warehouse ─────────────────────────────────────────────────

    def warm_warehouse(self) -> None:
        """Start the warehouse and wait until it runs, or stop at warehouse_start_seconds."""
        started = self.clock()
        path = f"{WAREHOUSES}/{self.warehouse_id}"
        if self.transport("GET", path, None).get("state") == "RUNNING":
            return
        try:
            self.transport("POST", f"{path}/start", {})
        except PermissionDenied:
            return self._wake_with_a_query(started)
        while self.transport("GET", path, None).get("state") != "RUNNING":
            if self.clock() - started >= self.waits.warehouse_start_seconds:
                raise GenieError("warehouse_cold", f"The SQL warehouse did not start within "
                                                   f"{self.waits.warehouse_start_seconds:.0f} seconds.")
            self.sleep(self.waits.poll_seconds)

    def _wake_with_a_query(self, started: float) -> None:
        reply = self.transport("POST", STATEMENTS, {"statement": "SELECT 1", "warehouse_id": self.warehouse_id,
                                                    "wait_timeout": "0s", "on_wait_timeout": "CONTINUE"})
        while (reply.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
            if self.clock() - started >= self.waits.warehouse_start_seconds:
                raise GenieError("warehouse_cold", f"The SQL warehouse did not start within "
                                                   f"{self.waits.warehouse_start_seconds:.0f} seconds.")
            self.sleep(self.waits.poll_seconds)
            reply = self.transport("GET", f"{STATEMENTS}{reply['statement_id']}", None)

    # ── 2 and 3. The question ────────────────────────────────────────────

    def _start(self, question: str, asked: float) -> dict:
        wait = self.waits.backoff_first_seconds
        while True:
            try:
                return self.transport("POST", f"{GENIE}/{self.space_id}/start-conversation", {"content": question})
            except EngineError as error:
                if " 429 " not in str(error):
                    raise
                if self.clock() - asked + wait > self.waits.answer_seconds:
                    raise GenieError("rate_limited", "Genie kept answering 429, too many questions, past the wait "
                                                     "the thresholds file allows.") from error
                self.sleep(wait)
                wait = min(wait * 2, self.waits.backoff_max_seconds)

    def ask(self, question: str) -> Answer:
        self.warm_warehouse()
        asked = self.clock()
        started = self._start(question, asked)
        conversation, message_id = started["conversation_id"], started["message_id"]
        path = f"{GENIE}/{self.space_id}/conversations/{conversation}/messages/{message_id}"
        message = started.get("message") or {}
        while message.get("status") not in DONE:
            if self.clock() - asked >= self.waits.answer_seconds:
                raise GenieError("genie_slow", f"Genie did not answer within {self.waits.answer_seconds:.0f} seconds; "
                                               f"its status was {message.get('status')}.")
            self.sleep(self.waits.poll_seconds)
            message = self.transport("GET", path, None)
        if message["status"] != "COMPLETED":
            detail = (message.get("error") or {}).get("error") or message["status"]
            raise GenieError("genie_failed", f"Genie did not answer: {detail}")
        texts = [part["text"]["content"] for part in message.get("attachments") or []
                 if (part.get("text") or {}).get("content")]
        queries = [part for part in message.get("attachments") or [] if (part.get("query") or {}).get("query")]
        answer = Answer(conversation, message_id, None, text=" ".join(texts) or None)
        if queries:
            attachment = queries[0]
            answer.sql = attachment["query"]["query"]
            answer.columns, answer.rows = self._result(f"{path}/attachments/{attachment['attachment_id']}/query-result")
        return answer

    # ── 4. The result ────────────────────────────────────────────────────

    def _result(self, path: str) -> tuple[list[tuple[str, str]], list[list[Any]]]:
        statement = self.transport("GET", path, None).get("statement_response") or {}
        columns = sorted((statement.get("manifest") or {}).get("schema", {}).get("columns", []),
                         key=lambda column: column.get("position", 0))
        result = statement.get("result") or {}
        cells = list(result.get("data_array") or [])
        link = result.get("next_chunk_internal_link")
        while link:
            chunk = self.transport("GET", link, None)
            cells += chunk.get("data_array") or []
            link = chunk.get("next_chunk_internal_link")
        types = [column.get("type_name") or "STRING" for column in columns]
        return ([(column["name"], kind) for column, kind in zip(columns, types, strict=True)],
                [[typed(value, kind) for value, kind in zip(row, types, strict=True)] for row in cells])
