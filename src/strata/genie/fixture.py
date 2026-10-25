"""The fixture's stand-in for a workspace's Genie space and SQL warehouse (ticket 33; spec, seam 2's offline adapter).

Genie writes SQL from words, which nothing offline can do. FixtureGenie answers the REST calls GenieClient makes,
so the client's whole path runs in the gate: the warehouse's state, the conversation, the message's status, the
query attachment, its result in chunks of two rows, and every cell as text with its column's type, as Genie sends
them. It answers a question it holds word for word, the Genie space's benchmark questions in evals/benchmark.yaml,
by running that question's ground-truth SQL on the fixture database. Any other question gets the text-only
answer Genie gives when it asks what you mean, with no query, so ask_genie says Genie did not answer it.

It is not Genie: it never writes SQL, and its rows are right by construction. What it proves is everything around
Genie: the client's reading of the API, the typing of text cells, ask_genie's rows with their evidence ids and its
as-of rule. The live space is checked by the full gate's Genie benchmark (strata.evals.genie_benchmark).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from strata.lakehouse.engine import Engine

SPACE = "fixture"
WAREHOUSE = "fixture"
CHUNK_ROWS = 2


def words(question: str) -> str:
    return " ".join(question.lower().split())


def type_name(values: list[Any]) -> str:
    """The Statement Execution API's type name for a column, from its first value that is not null."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            return "BOOLEAN"
        if isinstance(value, int):
            return "LONG"
        if isinstance(value, Decimal):
            return "DECIMAL"
        if isinstance(value, float):
            return "DOUBLE"
        if isinstance(value, dt.datetime):
            return "TIMESTAMP"
        if isinstance(value, dt.date):
            return "DATE"
        return "STRING"
    return "STRING"


class FixtureGenie:
    """A transport that answers GenieClient's calls from the fixture database."""

    def __init__(self, engine: Engine, benchmarks, chunk_rows: int = CHUNK_ROWS):
        self.engine, self.chunk_rows = engine, chunk_rows
        self.known = {words(item.question): item.case for item in benchmarks}
        self.messages: dict[str, dict] = {}
        self.results: dict[str, tuple[list[dict], list[list[str | None]]]] = {}

    def __call__(self, method: str, path: str, body: dict | None = None) -> dict:
        if path == f"/api/2.0/sql/warehouses/{WAREHOUSE}":
            return {"id": WAREHOUSE, "state": "RUNNING"}
        if path == f"/api/2.0/genie/spaces/{SPACE}/start-conversation":
            return self._ask(body["content"])
        if "/messages/" in path and "/attachments/" not in path:
            return self.messages[path.rsplit("/", 1)[1]]
        if path.endswith("/query-result"):
            statement = path.split("/attachments/")[1].split("/")[0]
            columns, _ = self.results[statement]
            return {"statement_response": {"statement_id": statement, "status": {"state": "SUCCEEDED"},
                                           "manifest": {"schema": {"columns": columns},
                                                        "total_chunk_count": self._chunks(statement)},
                                           "result": self._chunk(statement, 0)}}
        if "/result/chunks/" in path:
            statement = path.split("/api/2.0/sql/statements/")[1].split("/")[0]
            return self._chunk(statement, int(path.rsplit("/", 1)[1]))
        raise LookupError(f"The fixture's Genie has no answer for {method} {path}.")

    def _ask(self, question: str) -> dict:
        number = len(self.messages) + 1
        message_id, conversation_id, statement = f"message-{number}", f"conversation-{number}", f"statement-{number}"
        case = self.known.get(words(question))
        if case is None:
            attachments = [{"attachment_id": f"text-{number}",
                            "text": {"content": "I can answer only the space's benchmark questions offline."}}]
        else:
            result = self.engine.run(case.sql, case.params)
            columns = [{"name": name, "type_name": type_name([row[i] for row in result.rows]), "position": i}
                       for i, name in enumerate(result.columns)]
            cells = [[None if value is None else text for value, text in zip(raw, row, strict=True)]
                     for raw, row in zip(result.rows, result.as_text(), strict=True)]
            self.results[statement] = (columns, cells)
            from strata.genie.space import sql_only

            attachments = [{"attachment_id": statement,
                            "query": {"query": sql_only(case.sql), "statement_id": statement}}]
        message = {"id": message_id, "conversation_id": conversation_id, "status": "COMPLETED",
                   "attachments": attachments, "error": None}
        self.messages[message_id] = message
        return {"conversation_id": conversation_id, "message_id": message_id, "message": message}

    def _chunks(self, statement: str) -> int:
        return max(1, -(-len(self.results[statement][1]) // self.chunk_rows))

    def _chunk(self, statement: str, index: int) -> dict:
        cells = self.results[statement][1]
        part = {"chunk_index": index, "data_array": cells[index * self.chunk_rows:(index + 1) * self.chunk_rows]}
        if index + 1 < self._chunks(statement):
            part["next_chunk_index"] = index + 1
            part["next_chunk_internal_link"] = f"/api/2.0/sql/statements/{statement}/result/chunks/{index + 1}"
        return part
