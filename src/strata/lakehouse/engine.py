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
values. Each call runs one statement, because a SQL task divides a file into statements at every
semicolon (docs/PLAN.md section 12).
"""

from __future__ import annotations

import datetime as dt
import decimal
import http.client
import json
import re
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


class RowTooLarge(EngineError):
    """One row's values pass the limit the Statement Execution API puts on a statement's parameters."""


class PermissionDenied(EngineError):
    """The token cannot read what the statement asks for: a grant is missing, or the workspace refused the
    token itself. The app runs as each viewer (ADR 0003), so this is the viewer's own permission."""


# How the warehouse says a grant is missing: Unity Catalog's error class, the API's error code, or the
# SQL standard's state for an insufficient privilege.
PERMISSION_MARKERS = ("INSUFFICIENT_PERMISSIONS", "PERMISSION_DENIED", "SQLSTATE: 42501")


@dataclass(frozen=True)
class Result:
    """The columns and rows one statement returned."""

    columns: tuple[str, ...]
    rows: tuple[tuple, ...]

    def as_text(self) -> list[tuple[str, ...]]:
        """Each value as the warehouse writes it: dates as 2016-05-16, timestamps in UTC as
        2026-10-23T23:30:00.000Z, true and false, and '' for null.

        Rows from WarehouseEngine are text already, so rows from two engines can be compared.
        `ops/bundle/check.py same-rows` compares them on the workspace.
        """
        return [tuple(_text(value) for value in row) for row in self.rows]


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:  # a TIMESTAMP_NTZ, which the warehouse writes without a zone
            return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        return value.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    if isinstance(value, dt.date):
        return value.isoformat()
    return str(value)


class Engine(Protocol):
    name: str

    def run(self, sql: str, params: Params = None) -> Result:
        """Run one statement with its named parameters bound."""

    def insert_rows(self, table: str, columns: tuple[str, ...], rows: list[tuple]) -> int:
        """Append rows that Python built to a table, by column name. Returns how many it added."""

    def table_bytes(self, table: str) -> int:
        """How many bytes a table's stored data takes."""


TABLE_NAME = re.compile(r"strata\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")
COLUMN_NAME = re.compile(r"[a-z][a-z0-9_]*")


def check_names(table: str, columns: tuple[str, ...]) -> None:
    """insert_rows puts names, never values, into SQL text, so it takes only plain three-part names."""
    if not TABLE_NAME.fullmatch(table) or not all(COLUMN_NAME.fullmatch(column) for column in columns):
        raise EngineError(f"insert_rows takes a three-part table name and plain column names, not {table} "
                          f"({', '.join(columns)}).")


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
        connection.execute(f"ATTACH ? AS strata{' (READ_ONLY)' if read_only else ''}",  # sql-lint: names only
                           [str(path) if path else ":memory:"])  # the path is bound; only the keyword is built in
        connection.execute("USE strata")
        connection.execute("SET TimeZone = 'UTC'")  # as on the warehouse, whatever this computer's zone
        return cls(connection)

    def cursor(self) -> DuckDBEngine:
        """Another connection to the same open database, for use beside this one, such as by another request:
        it sees the same catalog, and closing it leaves this one open. DuckDB refuses to attach one file twice
        in a process, so two uses at once share the database this way."""
        connection = self.connection.cursor()
        connection.execute("USE strata")
        connection.execute("SET TimeZone = 'UTC'")
        return DuckDBEngine(connection)

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

    def insert_rows(self, table: str, columns: tuple[str, ...], rows: list[tuple], chunk: int = 500) -> int:
        check_names(table, columns)
        rows = list(rows)
        for start in range(0, len(rows), chunk):
            part = rows[start:start + chunk]
            marks = ", ".join(["(" + ", ".join(["?"] * len(columns)) + ")"] * len(part))
            try:
                self.connection.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES {marks}",  # sql-lint: names only
                                        [value for row in part for value in row])
            except Exception as error:  # duckdb raises its own error classes
                raise EngineError(f"DuckDB could not add rows to {table}: {error}") from error
        return len(rows)

    def table_bytes(self, table: str) -> int:
        """The bytes of the database file's blocks that hold the table, after a checkpoint writes
        everything to the file. An in-memory database holds no blocks, so it gives 0."""
        check_names(table, ())
        try:
            self.connection.execute("CHECKPOINT strata")
        except Exception:  # noqa: BLE001 - a read-only database has nothing to write
            pass
        blocks = self.connection.execute(  # sql-lint: names only, the table name is checked above
            f"SELECT count(DISTINCT block) FROM ("
            f"SELECT block_id AS block FROM pragma_storage_info('{table}') WHERE block_id >= 0 "
            f"UNION ALL SELECT unnest(additional_block_ids) FROM pragma_storage_info('{table}') "
            f"WHERE additional_block_ids IS NOT NULL)").fetchone()[0]
        size = self.connection.execute("SELECT block_size FROM pragma_database_size() "
                                       "WHERE database_name = 'strata'").fetchone()[0]
        return int(blocks) * int(size)

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _delta_bytes(engine, table: str) -> int:
    """DESCRIBE DETAIL's sizeInBytes for a Delta table on Databricks."""
    check_names(table, ())
    result = engine.run(f"DESCRIBE DETAIL {table}")  # sql-lint: names only, the table name is checked above
    return int(dict(zip(result.columns, result.rows[0], strict=True))["sizeInBytes"])


# ── Spark, inside a Databricks job ───────────────────────────────────────

class SparkEngine:
    """spark.sql with named parameters, for code that runs as a task of a Databricks job."""

    name = "databricks"

    def __init__(self, spark):
        self.spark = spark

    def run(self, sql: str, params: Params = None) -> Result:
        frame = self.spark.sql(sql, args=dict(params) if params else None)
        return Result(tuple(frame.columns), tuple(tuple(row) for row in frame.collect()))

    def insert_rows(self, table: str, columns: tuple[str, ...], rows: list[tuple]) -> int:
        """A DataFrame typed by the table's own columns, appended by name."""
        check_names(table, columns)
        rows = list(rows)
        if rows:
            schema = self.spark.table(table).select(*columns).schema
            self.spark.createDataFrame(rows, schema).write.mode("append").saveAsTable(table)
        return len(rows)

    def table_bytes(self, table: str) -> int:
        """The bytes of the table's Delta files, as DESCRIBE DETAIL gives them."""
        return _delta_bytes(self, table)


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


def base_url(host: str) -> str:
    """The workspace's address, from DATABRICKS_HOST with or without its https://."""
    return host.rstrip("/") if host.startswith("http") else f"https://{host.rstrip('/')}"


def http_transport(host: str, token: str, timeout: int = 120) -> Transport:
    """Calls to one workspace's REST API with one token. The token stays in this closure."""
    base = base_url(host)

    def call(method: str, path: str, body: dict | None = None) -> dict:
        request = urllib.request.Request(
            base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:400]
            refused = PermissionDenied if error.code in (401, 403) else EngineError
            raise refused(f"The workspace answered {error.code} to {method} {path}: {detail}") from error
        except (OSError, http.client.HTTPException) as error:  # a reset, DNS, TLS or a read that timed out
            raise EngineError(f"I could not reach the workspace for {method} {path}: {error}") from error
        except json.JSONDecodeError as error:
            raise EngineError(f"I could not read the workspace's answer to {method} {path}: {error}") from error

    return call



# The Statement Execution API's limit on the combined size of a statement's parameters, with room
# for the parameter names and the API's own encoding.
PARAMETER_CHARACTERS = 900_000


def _characters(row: tuple) -> int:
    """How many characters a row's values take as parameters."""
    return sum(len(str(value)) for value in row if value is not None)


def _parts(rows: list[tuple], chunk: int, chunk_characters: int):
    """rows in parts of at most `chunk` rows whose values hold at most `chunk_characters` characters."""
    part, size = [], 0
    for row in rows:
        row_size = _characters(row)
        if part and (len(part) >= chunk or size + row_size > chunk_characters):
            yield part
            part, size = [], 0
        part.append(row)
        size += row_size
    if part:
        yield part

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
        # The warehouse holds the first answer at most this long: within 5 to 50 seconds, and never
        # longer than this engine waits in all, unless that is under the API's 5 second floor.
        wait = max(5, min(50, int(self.timeout_seconds)))
        reply = self.transport("POST", STATEMENTS, {
            "statement": sql,
            "warehouse_id": self.warehouse_id,
            "parameters": [_parameter(name, value) for name, value in (params or {}).items()],
            "wait_timeout": f"{wait}s",
            "on_wait_timeout": "CONTINUE",
            "format": "JSON_ARRAY",
            "disposition": "INLINE",
        })
        waited = float(wait)  # a reply that is still running means the warehouse held the call this long
        while reply.get("status", {}).get("state") in WAITING:
            if waited >= self.timeout_seconds:
                raise EngineError(f"The warehouse took longer than {waited:.0f} seconds, "
                                  f"so I stopped waiting for statement {reply.get('statement_id')}.")
            self.sleep(self.poll_seconds)
            waited += self.poll_seconds
            reply = self.transport("GET", f"{STATEMENTS}{reply['statement_id']}", None)

        status = reply.get("status", {})
        if status.get("state") != "SUCCEEDED":
            error = status.get("error", {})
            message = error.get("message", "it gave no reason")
            said = f"{error.get('error_code', '')} {message}"
            refused = PermissionDenied if any(marker in said for marker in PERMISSION_MARKERS) else EngineError
            raise refused(f"The warehouse did not run the statement. Its state was {status.get('state')}: {message}")

        return self._result(reply)

    def insert_rows(self, table: str, columns: tuple[str, ...], rows: list[tuple], chunk: int = 100,
                    chunk_characters: int = PARAMETER_CHARACTERS) -> int:
        """Rows in chunks, each one INSERT whose every value is a bound parameter.

        A chunk holds at most `chunk` rows, and its values together at most `chunk_characters`
        characters, because the Statement Execution API refuses parameters over 1,048,576 characters
        in all. A page of layout elements can run to 50,000 characters, so 100 such rows would not fit.
        """
        check_names(table, columns)
        rows = list(rows)
        for row in rows:
            size = _characters(row)
            if size > chunk_characters:
                raise RowTooLarge(f"A row for {table} holds {size:,} characters of values, and the warehouse's "
                                  f"Statement Execution API takes at most {chunk_characters:,} in one statement's "
                                  "parameters, so the row cannot be written this way.")
        for part in _parts(rows, chunk, chunk_characters):
            params = {f"v{number}_{column}": value for number, row in enumerate(part)
                      for column, value in zip(range(len(columns)), row, strict=True)}
            values = ", ".join("(" + ", ".join(f":v{number}_{column}" for column in range(len(columns))) + ")"
                               for number in range(len(part)))
            self.run(f"INSERT INTO {table} ({', '.join(columns)}) VALUES {values}", params)  # sql-lint: names only
        return len(rows)

    def table_bytes(self, table: str) -> int:
        """The bytes of the table's Delta files, as DESCRIBE DETAIL gives them."""
        return _delta_bytes(self, table)

    def _result(self, reply: dict) -> Result:
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
