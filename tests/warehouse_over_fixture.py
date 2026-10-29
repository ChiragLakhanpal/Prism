"""The SQL warehouse, played by the fixture database (ticket 128).

On October 29, 2026 the workspace answered /projects/P156634/timeline with its error page while the local copy
answered in 0.4 seconds: the Statement Execution API writes every value as text, so a report's version came back as
"1" and `(row["version"] or 1) > 1` failed. The fixture's DuckDB gives the same column as 1, so no test saw it.

WarehouseOverFixture is a transport for WarehouseEngine that runs each statement on the fixture database and
answers as the Statement Execution API answers with format JSON_ARRAY and disposition INLINE: the manifest names
each column's type_name and type_text, and the result writes every value as text, or null. A route run on
WarehouseEngine over it reads the fixture's rows as the workspace serves them, so it must answer what it answers on
DuckDB. It keeps every reply it gave, so a test can show what the engine was sent.
"""

from __future__ import annotations

import datetime as dt
import decimal
import json
from contextlib import contextmanager
from pathlib import Path

from strata.lakehouse.engine import STATEMENTS, DuckDBEngine, Result, WarehouseEngine, transpile

# A result column's type in DuckDB, and the type_name the Statement Execution API gives the same column. A DECIMAL,
# a list, a struct and a map are matched by how their name starts or ends, below.
TYPE_NAMES = {
    "BIGINT": "LONG", "HUGEINT": "LONG", "UBIGINT": "LONG", "UINTEGER": "LONG", "INTEGER": "INT", "USMALLINT": "INT",
    "SMALLINT": "SHORT", "UTINYINT": "SHORT", "TINYINT": "BYTE", "DOUBLE": "DOUBLE", "FLOAT": "FLOAT",
    "BOOLEAN": "BOOLEAN", "DATE": "DATE", "TIMESTAMP WITH TIME ZONE": "TIMESTAMP", "TIMESTAMP": "TIMESTAMP_NTZ",
    "VARCHAR": "STRING", "BLOB": "BINARY", '"NULL"': "NULL",
}

# A bound parameter's type, as WarehouseEngine sends it, and how DuckDB takes its text back.
PARAMETERS = {"BIGINT": int, "DOUBLE": float, "DECIMAL": decimal.Decimal, "BOOLEAN": lambda text: text == "true",
              "DATE": dt.date.fromisoformat, "TIMESTAMP": dt.datetime.fromisoformat, "STRING": str}


def type_name(duckdb_type: str) -> str:
    if duckdb_type.startswith("DECIMAL"):
        return "DECIMAL"
    if duckdb_type.endswith("]"):
        return "ARRAY"
    if duckdb_type.startswith(("STRUCT", "MAP")):
        return duckdb_type.split("(")[0]
    return TYPE_NAMES.get(duckdb_type, "STRING")


def written(value) -> str | None:
    """A value as the warehouse writes it in a JSON_ARRAY result: text, JSON text for an array, a struct or a map,
    and null for null."""
    if value is None:
        return None
    if isinstance(value, list | dict):
        return json.dumps(value, default=str)
    return Result((), ((value,),)).as_text()[0][0]


def bound(parameter: dict):
    if "value" not in parameter:
        return None
    return PARAMETERS[parameter["type"].split("(")[0]](parameter["value"])


class WarehouseOverFixture:
    def __init__(self, database: Path | str):
        self.database = database
        self.replies: list[dict] = []

    @contextmanager
    def engine_for(self, _viewer=None):
        """create_app's engine_for: a WarehouseEngine whose warehouse is the fixture database, opened read-only."""
        with DuckDBEngine.open(self.database, read_only=True) as fixture:
            yield WarehouseEngine("fixture", lambda method, path, body: self.answer(fixture, method, path, body))

    def answer(self, fixture: DuckDBEngine, method: str, path: str, body: dict | None) -> dict:
        if (method, path) != ("POST", STATEMENTS):
            raise AssertionError(f"The fixture's warehouse answers only new statements, not {method} {path}.")
        params = {parameter["name"]: bound(parameter) for parameter in body["parameters"]}
        try:
            cursor = fixture.connection.execute(transpile(body["statement"]), params or None)
        except Exception as error:  # noqa: BLE001 - the warehouse reports a failed statement in its reply
            return {"statement_id": f"s-{len(self.replies)}", "status": {"state": "FAILED", "error": {"message": str(error)}}}
        described = cursor.description or []
        columns = [{"name": name, "type_text": str(kind), "type_name": type_name(str(kind)), "position": at}
                   for at, (name, kind, *_) in enumerate(described)]
        rows = [[written(value) for value in row] for row in cursor.fetchall()] if described else []
        reply = {"statement_id": f"s-{len(self.replies)}", "status": {"state": "SUCCEEDED"},
                 "manifest": {"format": "JSON_ARRAY", "schema": {"column_count": len(columns), "columns": columns}},
                 "result": {"data_array": rows}}
        self.replies.append({"statement": body["statement"], "reply": reply})
        return reply

    def values_written(self, column: str) -> list[tuple[str, str | None]]:
        """Every value the warehouse wrote in a column of this name, with the column's type_name."""
        found = []
        for answered in self.replies:
            columns = answered["reply"]["manifest"]["schema"]["columns"]
            for at, described in enumerate(columns):
                if described["name"] == column:
                    found += [(described["type_name"], row[at]) for row in answered["reply"]["result"]["data_array"]]
        return found
