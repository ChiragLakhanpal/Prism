"""The engine adapter: one plain SQL query runs unchanged on Databricks and on DuckDB.

Strata writes its SQL once, in Databricks SQL, because that is where it runs for real. Three
engines run it, and all three take the same text and the same parameters:

- WarehouseEngine runs it on the workspace's SQL warehouse through the Statement Execution API,
  with the token it is given (the viewer's, in the app).
- SparkEngine runs it with spark.sql inside a Databricks job.
- DuckDBEngine runs it on a local DuckDB database in the offline gate, after one transpile step
  (sqlglot, from Databricks SQL to DuckDB SQL).

The SQL names tables in three parts (strata.<schema>.<table>) and takes values only as named
parameters (`:name`), which every engine binds from Python values. No engine builds SQL from
values. Each call runs one statement, which keeps clear of the trap where SQL tasks divide a file
at every semicolon (docs/PLAN.md section 12).
"""

from __future__ import annotations

import datetime as dt
import decimal
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

Params = Mapping[str, Any] | None


class EngineError(RuntimeError):
    """A statement an engine could not run, with the reason the engine gave."""


@dataclass(frozen=True)
class Result:
    """The columns and rows one statement returned."""

    columns: tuple[str, ...]
    rows: tuple[tuple, ...]

    def as_text(self) -> list[tuple[str, ...]]:
        """Each value as the warehouse writes it: dates as 2016-05-16, true and false, and '' for null.

        Rows from WarehouseEngine are text already, so rows from two engines can be compared.
        """
        return [tuple(_text(value) for value in row) for row in self.rows]


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dt.date | dt.datetime):
        return value.isoformat()
    return str(value)


class Engine(Protocol):
    name: str

    def run(self, sql: str, params: Params = None) -> Result:
        """Run one statement with its named parameters bound."""


def read_sql(path: Path) -> str:
    return Path(path).read_text()


# ── DuckDB, for the offline gate ─────────────────────────────────────────

def transpile(sql: str) -> str:
    """The one transpile step: a single Databricks SQL statement, rewritten for DuckDB.

    It fails on anything DuckDB cannot express, such as a column comment, instead of dropping it.
    """
    import sqlglot
    from sqlglot.errors import ErrorLevel, ParseError, UnsupportedError

    try:
        statements = [s for s in sqlglot.parse(sql, read="databricks") if s is not None]
        if len(statements) != 1:
            raise EngineError(f"Each call runs one statement, and this SQL holds {len(statements)}. "
                              "Split it into one call per statement.")
        return statements[0].sql(dialect="duckdb", unsupported_level=ErrorLevel.RAISE)
    except (ParseError, UnsupportedError) as error:
        raise EngineError(f"The transpile step could not rewrite this SQL for DuckDB: {error}") from error


class DuckDBEngine:
    """A DuckDB database attached as the catalog `strata`, so three-part names work as on Databricks."""

    name = "duckdb"

    def __init__(self, connection):
        self.connection = connection

    @classmethod
    def open(cls, path: Path | str | None = None, read_only: bool = False) -> DuckDBEngine:
        """A database file attached as `strata`, or an empty one in memory when path is None."""
        import duckdb

        connection = duckdb.connect()
        connection.execute(f"ATTACH ? AS strata{' (READ_ONLY)' if read_only else ''}",
                           [str(path) if path else ":memory:"])
        connection.execute("USE strata")
        return cls(connection)

    def run(self, sql: str, params: Params = None) -> Result:
        try:
            cursor = self.connection.execute(transpile(sql), dict(params) if params else None)
        except EngineError:
            raise
        except Exception as error:  # duckdb raises its own error classes
            raise EngineError(f"DuckDB could not run the statement: {error}") from error
        if cursor.description is None:
            return Result((), ())
        return Result(tuple(column[0] for column in cursor.description), tuple(cursor.fetchall()))

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ── Spark, inside a Databricks job ───────────────────────────────────────

class SparkEngine:
    """spark.sql with named parameters, for code that runs as a task of a Databricks job."""

    name = "databricks"

    def __init__(self, spark):
        self.spark = spark

    def run(self, sql: str, params: Params = None) -> Result:
        frame = self.spark.sql(sql, args=dict(params) if params else None)
        return Result(tuple(frame.columns), tuple(tuple(row) for row in frame.collect()))


# ── The SQL warehouse, through the Statement Execution API ───────────────

Transport = Callable[[str, str, dict | None], dict]
STATEMENTS = "/api/2.0/sql/statements/"
WAITING = ("PENDING", "RUNNING")


def _parameter(name: str, value) -> dict:
    """One named parameter as the Statement Execution API takes it: its value as text, with its type."""
    if value is None:
        return {"name": name}
    if isinstance(value, bool):
        return {"name": name, "value": "true" if value else "false", "type": "BOOLEAN"}
    if isinstance(value, int):
        return {"name": name, "value": str(value), "type": "BIGINT"}
    if isinstance(value, float):
        return {"name": name, "value": repr(value), "type": "DOUBLE"}
    if isinstance(value, decimal.Decimal):
        return {"name": name, "value": str(value), "type": "DECIMAL(38, 18)"}
    if isinstance(value, dt.datetime):
        return {"name": name, "value": value.isoformat(), "type": "TIMESTAMP"}
    if isinstance(value, dt.date):
        return {"name": name, "value": value.isoformat(), "type": "DATE"}
    if isinstance(value, str):
        return {"name": name, "value": value, "type": "STRING"}
    raise EngineError(f"I cannot bind the parameter {name}, a {type(value).__name__}.")


def http_transport(host: str, token: str, timeout: int = 120) -> Transport:
    """Calls to one workspace's REST API with one token. The token stays in this closure."""
    base = host.rstrip("/") if host.startswith("http") else f"https://{host.rstrip('/')}"

    def call(method: str, path: str, body: dict | None = None) -> dict:
        request = urllib.request.Request(
            base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:400]
            raise EngineError(f"The workspace answered {error.code} to {method} {path}: {detail}") from error

    return call


class WarehouseEngine:
    """The workspace's SQL warehouse, run as whoever owns the token."""

    name = "databricks"

    def __init__(self, warehouse_id: str, transport: Transport, poll_seconds: float = 2,
                 timeout_seconds: float = 600, sleep=time.sleep):
        self.warehouse_id, self.transport = warehouse_id, transport
        self.poll_seconds, self.timeout_seconds, self.sleep = poll_seconds, timeout_seconds, sleep

    @classmethod
    def connect(cls, host: str, token: str, warehouse_id: str) -> WarehouseEngine:
        return cls(warehouse_id, http_transport(host, token))

    def run(self, sql: str, params: Params = None) -> Result:
        reply = self.transport("POST", STATEMENTS, {
            "statement": sql,
            "warehouse_id": self.warehouse_id,
            "parameters": [_parameter(name, value) for name, value in (params or {}).items()],
            "wait_timeout": "50s",
            "on_wait_timeout": "CONTINUE",
            "format": "JSON_ARRAY",
            "disposition": "INLINE",
        })
        waited = 0.0
        while reply.get("status", {}).get("state") in WAITING:
            if waited >= self.timeout_seconds:
                raise EngineError(f"The warehouse took longer than {self.timeout_seconds:.0f} seconds, "
                                  f"so I stopped waiting for statement {reply.get('statement_id')}.")
            self.sleep(self.poll_seconds)
            waited += self.poll_seconds
            reply = self.transport("GET", f"{STATEMENTS}{reply['statement_id']}", None)

        status = reply.get("status", {})
        if status.get("state") != "SUCCEEDED":
            message = status.get("error", {}).get("message", "it gave no reason")
            raise EngineError(f"The warehouse did not run the statement. Its state was {status.get('state')}: "
                              f"{message}")

        columns = sorted(reply.get("manifest", {}).get("schema", {}).get("columns", []),
                         key=lambda column: column.get("position", 0))
        result = reply.get("result") or {}
        rows = list(result.get("data_array") or [])
        link = result.get("next_chunk_internal_link")
        while link:
            chunk = self.transport("GET", link, None)
            rows += chunk.get("data_array") or []
            link = chunk.get("next_chunk_internal_link")
        return Result(tuple(column["name"] for column in columns), tuple(tuple(row) for row in rows))
