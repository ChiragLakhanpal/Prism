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

A page's reads go as one batch (ticket 125): run_many(engine, statements) posts them to the warehouse at once and
waits once (each statement cost the statements API about two seconds, so a page that ran six one after another took
twelve), and read_together(engine, statements) gives a page an engine that answers each of its reads from that batch.
How the warehouse engine waits is config/thresholds.toml's [warehouse].

The warehouse returns a statement's result inline only up to warehouse.statement_result_bytes, and refuses a larger
one. A read that grows with the workspace goes through read_in_parts (ticket 135), which measures the rows first and
asks for them in parts that fit; on DuckDB and Spark, which have no such limit, it is one statement as before.
"""

from __future__ import annotations

import contextvars
import datetime as dt
import decimal
import functools
import http.client
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

Params = Mapping[str, Any] | None
log = logging.getLogger("strata.lakehouse.engine")


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

        Every engine's rows hold typed values (WarehouseEngine reads the warehouse's text by the manifest's types),
        and this writes them back the way the warehouse does, so rows from two engines can be compared.
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


# ── A page's reads, run together (ticket 125) ────────────────────────────

Statement = tuple[str, Params]  # one statement's SQL and its named parameters


def run_many(engine, statements: Sequence[Statement], return_exceptions: bool = False) -> list[Result | Exception]:
    """The statements' results in order: in one batch on an engine that sends a batch at once (the SQL warehouse's
    WarehouseEngine.run_many), and one after another on any other. The first statement that failed raises its error,
    or, with return_exceptions, each failed statement's error stands in its place, as asyncio.gather gives them."""
    statements = list(statements)
    many = getattr(engine, "run_many", None)
    if callable(many):
        return many(statements, return_exceptions=return_exceptions)
    return _each(engine.run, statements, return_exceptions)


def _each(run: Callable[[str, Params], Result], statements: Sequence[Statement],
          return_exceptions: bool) -> list[Result | Exception]:
    """Each statement run in turn, with each error in its place when return_exceptions holds them."""
    out: list[Result | Exception] = []
    for sql, params in statements:
        try:
            out.append(run(sql, params))
        except Exception as error:
            if not return_exceptions:
                raise
            out.append(error)
    return out


def _key(sql: str, params: Params) -> tuple:
    """A statement as a batch finds it again: its text and its parameters, by name."""
    def held(value):
        try:
            hash(value)
        except TypeError:
            return repr(value)
        return value
    return sql, tuple(sorted((name, held(value)) for name, value in (params or {}).items()))


class ReadTogether:
    """An engine that answers a page's reads from one batch it sent first (ticket 125). A page names every statement
    it will run, read_together sends them at once, and the page's own code then runs each as before and gets its
    result from the batch. A statement the batch does not hold runs alone, as it did before, and is listed in missed,
    so a test can show that a page needs one round trip.

    A statement that failed in the batch keeps its error, and the page meets that error only when it runs that
    statement, as it did when each statement ran alone: so a page that reads on past a failed read (the Timeline draws
    its marks when get_disagreements fails) still does. errors lists each error the page met, so the App does not keep
    a page read past one (src/strata/server/page_cache.py)."""

    def __init__(self, engine, statements: Sequence[Statement]):
        self.engine = engine
        self.held: dict[tuple, Result | Exception] = {}
        self.missed: list[str] = []
        self.errors: list[Exception] = []
        self.add(statements)

    def add(self, statements: Sequence[Statement]) -> None:
        """Send one more batch, of the statements this one does not hold yet: for a page whose later reads depend
        on what its first batch found."""
        unique = list({key: (sql, params) for sql, params in statements
                       if (key := _key(sql, params)) not in self.held}.items())
        if unique:
            results = run_many(self.engine, [statement for _, statement in unique], return_exceptions=True)
            self.held.update({key: result for (key, _), result in zip(unique, results, strict=True)})

    def run(self, sql: str, params: Params = None) -> Result:
        found = self.held.get(_key(sql, params))
        if isinstance(found, Exception):
            self.errors.append(found)
            raise found
        if found is not None:
            return found
        self.missed.append(sql)
        log.warning("A page ran a statement its batch did not hold, so it took one more round trip: %s",
                    sql.strip().splitlines()[0] if sql.strip() else sql)
        try:
            return self.engine.run(sql, params)
        except Exception as error:
            self.errors.append(error)
            raise

    def run_many(self, statements: Sequence[Statement], return_exceptions: bool = False) -> list[Result | Exception]:
        """These statements' results from this batch, after one more batch of those it does not hold yet, so a page
        that runs a batch of its own keeps to one round trip for it."""
        statements = list(statements)
        self.add(statements)
        return _each(self.run, statements, return_exceptions)

    def __getattr__(self, name: str):
        return getattr(self.engine, name)


def read_together(engine, statements: Sequence[Statement]) -> ReadTogether:
    """An engine whose answers to these statements come from one batch, sent now: on an engine that already reads a
    page's statements together (the one the App reads each page through), one more of its batches."""
    if isinstance(engine, ReadTogether):
        engine.add(statements)
        return engine
    return ReadTogether(engine, statements)


def read_ahead(engine, statements: Sequence[Statement]) -> None:
    """Send these statements as one more batch when the engine reads a page's statements together; any other engine
    runs each one when it is asked for, as before."""
    if isinstance(engine, ReadTogether):
        engine.add(statements)


# ── Reads within the warehouse's result limit (tickets 123 and 135) ────────

# The characters JSON writes with a backslash: the control characters, the quote mark and the backslash itself. Each
# takes two to six bytes in the warehouse's result where the text holds one.
ESCAPED = "".join(chr(code) for code in range(1, 32)) + '"\\'
# What one value takes in a result beside its text: its quote marks and comma, and room for a value the warehouse
# writes longer than CAST(... AS STRING) gives it, such as a timestamp with its T and milliseconds, or a null.
VALUE_BYTES = 16


def json_bytes(text: str) -> str:
    """The SQL for the most bytes a text column's value can take in the warehouse's JSON result: six bytes for each
    character JSON may write as an escape (a quote mark, a backslash, a control character such as a line break, or a
    letter outside ASCII, as \\u00e9), and the text's own bytes for the rest. It binds :escaped (ESCAPED). text is a
    column name or a SQL expression, never a value."""
    return (f"5 * octet_length(encode({text}, 'UTF-8')) - 4 * length({text}) "
            f"+ 5 * (length({text}) - length(translate({text}, :escaped, '')))")


@functools.cache
def statement_result_bytes() -> int:
    """The most bytes one statement's result may hold on the SQL warehouse (config/thresholds.toml,
    warehouse.statement_result_bytes)."""
    from strata.config import load_thresholds

    return int(load_thresholds().value("warehouse.statement_result_bytes"))


@dataclass(frozen=True)
class Parts:
    """What read_in_parts read: every part's rows as one result, and the keys whose own rows pass the limit, which it
    left out."""

    result: Result
    left_out: tuple[str, ...] = ()


@functools.lru_cache(maxsize=256)
def _measure(sql: str, key: str) -> tuple[str, tuple[str, ...]]:
    """The statement that measures sql's result key by key, as the most bytes each key's rows can take in the
    warehouse's JSON (json_bytes for each value, and VALUE_BYTES a value), and the columns sql returns. It is sql
    itself, with its WITH clause kept and its ORDER BY left out, inside a SELECT that adds up each key's rows."""
    import sqlglot

    tree = sqlglot.parse_one(sql, read="databricks")
    with_key = "with_" if "with_" in type(tree).arg_types else "with"
    ctes = tree.args.get(with_key)
    body = tree.copy()
    body.set(with_key, None)
    body.set("order", None)
    columns = tuple(body.named_selects)
    if key not in columns:
        raise EngineError(f"read_in_parts reads by a column the statement returns, and {key} is not one of "
                          f"{', '.join(columns)}.")
    values = " + ".join(json_bytes(f"coalesce(CAST(part_rows.{column} AS STRING), '')") for column in columns)
    measure = (f"SELECT part_rows.{key} AS part_key, sum({values} + :part_row_bytes) AS part_bytes "  # sql-lint: names only
               f"FROM ({body.sql(dialect='databricks', comments=False)}) AS part_rows GROUP BY part_rows.{key}")
    return (f"{ctes.sql(dialect='databricks', comments=False)} {measure}" if ctes else measure), columns


def read_in_parts(engine, sql: str, params: Params, key: str, part: Callable[[list[str]], dict],
                  keys: Sequence[str] | None = None) -> Parts:
    """sql's rows, read in statements whose results fit the engine's limit on one statement's result (its
    result_bytes; the SQL warehouse's is config/thresholds.toml's warehouse.statement_result_bytes), so no statement
    of the read can pass it, whatever the workspace holds. An engine with no such limit, as DuckDB and Spark have
    none, runs sql once, as before.

    It measures first, with one statement that gives the most bytes each key's rows can take (key is a column sql
    returns, such as project_id). When every row fits together it runs sql once with params, unchanged. When they do
    not, it reads only the keys asked for (keys, or every key), in parts of as many keys as fit, in their order: each
    part is sql with params and part(the part's keys), the parameters that limit sql to those keys. Each key's rows
    come in one part, in sql's own order. A key whose own rows pass the limit is left out, with a warning, and named
    in what it returns. On October 29, 2026 the assertions pass read every project's records in one statement, and
    the warehouse refused it: "Inline byte limit exceeded" (ticket 135)."""
    cap = getattr(engine, "result_bytes", None)
    if not cap:
        return Parts(engine.run(sql, params))
    measure, columns = _measure(sql, key)
    sizes = {str(found): int(size or 0) for found, size in engine.run(measure, {
        **(params or {}), "escaped": ESCAPED, "part_row_bytes": VALUE_BYTES * len(columns) + 2}).rows}
    if sum(sizes.values()) <= cap:
        return Parts(engine.run(sql, params))
    wanted = [found for found in dict.fromkeys(str(one) for one in keys) if found in sizes] if keys is not None \
        else list(sizes)
    left_out = tuple(found for found in wanted if sizes[found] > cap)
    for found in left_out:
        log.warning("I left %s %s out of my read: its rows can take up to %s bytes, and the SQL warehouse returns at "
                    "most %s in one statement (config/thresholds.toml, warehouse.statement_result_bytes).", key,
                    found, f"{sizes[found]:,}", f"{cap:,}")
    parts: list[list[str]] = [[]]
    held = 0
    for found in (found for found in wanted if found not in left_out):
        if parts[-1] and held + sizes[found] > cap:
            parts.append([])
            held = 0
        parts[-1].append(found)
        held += sizes[found]
    rows: list[tuple] = []
    for keys_of_part in (one for one in parts if one):
        result = engine.run(sql, {**(params or {}), **part(keys_of_part)})
        columns = result.columns
        rows += result.rows
    return Parts(Result(tuple(columns), tuple(rows)), left_out)


TABLE_NAME = re.compile(r"strata\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")
COLUMN_NAME = re.compile(r"[a-z][a-z0-9_]*")


def check_names(table: str, columns: tuple[str, ...]) -> None:
    """insert_rows puts names, never values, into SQL text, so it takes only plain three-part names."""
    if not TABLE_NAME.fullmatch(table) or not all(COLUMN_NAME.fullmatch(column) for column in columns):
        raise EngineError(f"insert_rows takes a three-part table name and plain column names, not {table} "
                          f"({', '.join(columns)}).")


# ── DuckDB, for the offline gate ─────────────────────────────────────────

@functools.lru_cache(maxsize=4096)
def transpile(sql: str) -> str:
    """The one transpile step: a single Databricks SQL statement, rewritten for DuckDB.

    It fails on anything DuckDB cannot express, such as a column comment, instead of dropping it.
    It keeps each rewrite it made, because the fixture build and the tests run the same statements
    thousands of times and rewriting took most of the time a catalog build takes (ticket 55). The
    values are bound parameters, never part of the text, so the same statement always has the same
    text. A refusal is not kept: bad SQL is refused each time it runs.
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


# Databricks SQL functions DuckDB lacks, as macros with the same name and meaning, for what the transpile step leaves
# as it is. format_number(x, d) writes a number with commas and d decimals (1,234.50), as the dashboard's counters
# and tables show numbers (ticket 45).
DUCKDB_MACROS = (
    "CREATE OR REPLACE TEMP MACRO format_number(x, d) AS CASE WHEN d = 0 THEN format('{:,}', CAST(round(x) AS BIGINT)) "
    "ELSE format('{:,.' || CAST(d AS VARCHAR) || 'f}', CAST(x AS DOUBLE)) END",
)


THREADS = "STRATA_DUCKDB_THREADS"


def duckdb_config() -> dict[str, int]:
    """DuckDB's settings for a new connection: the number of threads STRATA_DUCKDB_THREADS names, if any."""
    threads = os.environ.get(THREADS, "").strip()
    if not threads:
        return {}
    if not threads.isdigit() or int(threads) < 1:
        raise EngineError(f"{THREADS} must be a whole number of threads, such as 1, not {threads!r}.")
    return {"threads": int(threads)}


def _session(connection) -> None:
    connection.execute("USE strata")
    connection.execute("SET TimeZone = 'UTC'")  # as on the warehouse, whatever this computer's zone
    for macro in DUCKDB_MACROS:
        connection.execute(macro)


class DuckDBEngine:
    """A DuckDB database attached as the catalog `strata`, so three-part names work as on Databricks."""

    name = "duckdb"

    def __init__(self, connection):
        self.connection = connection

    @classmethod
    def open(cls, path: Path | str | None = None, read_only: bool = False) -> DuckDBEngine:
        """A database file attached as `strata`, or an empty one in memory when path is None.

        DuckDB runs each query on every processor unless STRATA_DUCKDB_THREADS names fewer threads. The gate's
        python lanes set it to 1 (gates/steps.toml), since their 16 pytest-xdist workers already keep every
        processor busy (ticket 119)."""
        import duckdb

        connection = duckdb.connect(config=duckdb_config())
        try:
            connection.execute(f"ATTACH ? AS strata{' (READ_ONLY)' if read_only else ''}",  # sql-lint: names only
                               [str(path) if path else ":memory:"])  # the path is bound; only the keyword is built in
        except duckdb.Error as error:
            # Such as a file this process has attached already, which DuckDB refuses to attach twice, or one another
            # process holds: the caller's data service error, not a crash (ticket 35's verification round 4, F3).
            connection.close()
            raise EngineError(f"DuckDB could not open the database file {path}: {error}") from error
        _session(connection)
        return cls(connection)

    def cursor(self) -> DuckDBEngine:
        """Another connection to the same open database, for use beside this one, such as by another request:
        it sees the same catalog, and closing it leaves this one open. DuckDB refuses to attach one file twice
        in a process, so two uses at once share the database this way."""
        connection = self.connection.cursor()
        _session(connection)
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

    def run_many(self, statements: Sequence[Statement], return_exceptions: bool = False) -> list[Result | Exception]:
        """One batch, as the warehouse takes it, run here one statement after another on the one connection."""
        return _each(self.run, statements, return_exceptions)

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



def _outcome(future: Future, return_exceptions: bool) -> Result | Exception:
    """A statement's result, or its error in its place when return_exceptions holds them."""
    error = future.exception()
    if error is None:
        return future.result()
    if return_exceptions and isinstance(error, Exception):
        return error
    raise error


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

# The Statement Execution API names a column's type in type_name (LONG, SHORT, BYTE) and in type_text (BIGINT,
# SMALLINT, TINYINT); these are both spellings.
WHOLE = ("BYTE", "SHORT", "INT", "INTEGER", "LONG", "BIGINT", "TINYINT", "SMALLINT")
FRACTION = ("FLOAT", "DOUBLE", "REAL")


def typed(value: str | None, type_name: str | None) -> Any:
    """One value the warehouse wrote as text, read as its column's type, so it reaches the caller as DuckDB gives
    the same column (ticket 128): BIGINT, INT, SMALLINT and TINYINT as int; DECIMAL as Decimal; DOUBLE and FLOAT as
    float; BOOLEAN as bool; DATE as date; TIMESTAMP as a datetime in UTC and TIMESTAMP_NTZ as one with no zone.
    STRING and every other type stay as written, null stays None, and text that does not read as its type stays as
    written. This is the one place Strata reads the warehouse's text; Genie's results come through it too."""
    if value is None:
        return None
    kind = (type_name or "STRING").upper().split("(")[0].strip()
    try:
        if kind in WHOLE:
            return int(value)
        if kind in FRACTION:
            return float(value)
        if kind == "DECIMAL":
            return decimal.Decimal(value)
        if kind == "BOOLEAN":
            return value.lower() == "true"
        if kind == "DATE":
            return dt.date.fromisoformat(value[:10])
        if kind == "TIMESTAMP":
            moment = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return moment.replace(tzinfo=dt.UTC) if moment.tzinfo is None else moment.astimezone(dt.UTC)
        if kind == "TIMESTAMP_NTZ":
            return dt.datetime.fromisoformat(value)
    except (ValueError, decimal.InvalidOperation):
        return value
    return value


@dataclass(frozen=True)
class Waits:
    """How the warehouse engine waits on the statements API: config/thresholds.toml's [warehouse], the one place they
    are tuned (ticket 125). wait_seconds is how long the API holds a statement's POST for its answer, poll_seconds the
    first wait before asking about a statement still running after that, each later wait twice the one before up to
    poll_max_seconds, and statements_at_once the most statements of one batch posted at once."""

    wait_seconds: float
    poll_seconds: float
    poll_max_seconds: float
    statements_at_once: int

    @classmethod
    @functools.cache
    def from_thresholds(cls) -> Waits:
        from strata.config import load_thresholds

        value = load_thresholds().value
        return cls(value("warehouse.wait_seconds"), value("warehouse.poll_seconds"),
                   value("warehouse.poll_max_seconds"), int(value("warehouse.statements_at_once")))


class WarehouseEngine:
    """The workspace's SQL warehouse, run as whoever owns the token. Its rows hold Python values typed from the
    statement's manifest, as DuckDBEngine's and SparkEngine's do (typed()). result_bytes is the most bytes one
    statement's result may hold, which read_in_parts keeps to (config/thresholds.toml, warehouse.statement_result_bytes)."""

    name = "databricks"

    def __init__(self, warehouse_id: str, transport: Transport, timeout_seconds: float = 600, sleep=time.sleep,
                 waits: Waits | None = None, result_bytes: int | None = None):
        self.warehouse_id, self.transport = warehouse_id, transport
        self.timeout_seconds, self.sleep = timeout_seconds, sleep
        self.waits = waits or Waits.from_thresholds()
        self.result_bytes = result_bytes or statement_result_bytes()

    @classmethod
    def connect(cls, host: str, token: str, warehouse_id: str) -> WarehouseEngine:
        return cls(warehouse_id, http_transport(host, token))

    def run_many(self, statements: Sequence[tuple[str, Params]],
                 return_exceptions: bool = False) -> list[Result | Exception]:
        """A page's statements posted at once, each on its own thread, with one wait for them all (ticket 125): on the
        workspace a statement costs the statements API about two seconds, so six run one after another took twelve.
        The results come back in the statements' order; the first statement that failed raises its error, or, with
        return_exceptions, each failed statement's error stands in its place."""
        statements = list(statements)
        if len(statements) < 2:
            return _each(self.run, statements, return_exceptions)
        at_once = max(1, min(len(statements), self.waits.statements_at_once))
        with ThreadPoolExecutor(max_workers=at_once, thread_name_prefix="strata-statement") as pool:
            # Each statement runs in its own copy of the caller's context (one context cannot be entered by two
            # threads at once), so the request's trace span is its parent in Application Insights.
            running = [pool.submit(contextvars.copy_context().run, self.run, sql, params) for sql, params in statements]
            return [_outcome(future, return_exceptions) for future in running]

    def run(self, sql: str, params: Params = None) -> Result:
        # The warehouse holds the first answer at most this long: the thresholds' wait, within the API's 5 to 50
        # seconds, and never longer than this engine waits in all, unless that is under the API's 5 second floor.
        wait = max(5, min(50, int(self.waits.wait_seconds), int(self.timeout_seconds)))
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
        poll = self.waits.poll_seconds  # soon at first, then twice as long each time, up to the longest
        while reply.get("status", {}).get("state") in WAITING:
            if waited >= self.timeout_seconds:
                self._cancel(reply.get("statement_id"))
                raise EngineError(f"The warehouse took longer than {waited:.0f} seconds, "
                                  f"so I stopped waiting for statement {reply.get('statement_id')}.")
            self.sleep(poll)
            waited += poll
            poll = min(poll * 2, self.waits.poll_max_seconds)
            reply = self.transport("GET", f"{STATEMENTS}{reply['statement_id']}", None)

        status = reply.get("status", {})
        if status.get("state") != "SUCCEEDED":
            error = status.get("error", {})
            message = error.get("message", "it gave no reason")
            said = f"{error.get('error_code', '')} {message}"
            refused = PermissionDenied if any(marker in said for marker in PERMISSION_MARKERS) else EngineError
            raise refused(f"The warehouse did not run the statement. Its state was {status.get('state')}: {message}")

        return self._result(reply)

    def _cancel(self, statement: str | None) -> None:
        """Ask the warehouse to stop a statement this engine gave up on, so it does not keep running there (ticket
        06's review round 3, P2). A cancel that fails is logged and changes nothing: the caller still gets the
        error that it gave up."""
        if not statement:
            return
        try:
            self.transport("POST", f"{STATEMENTS}{statement}/cancel", None)
        except Exception as error:  # noqa: BLE001 - the workspace or the network; the read failed either way
            log.warning("I could not cancel statement %s on the warehouse: %s", statement, error)

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
        # format JSON_ARRAY writes every value as text, so each is read by its column's type (ticket 128).
        kinds = [column.get("type_name") or column.get("type_text") for column in columns]
        return Result(tuple(column["name"] for column in columns),
                      tuple(tuple(typed(value, kinds[at]) if at < len(kinds) else value for at, value in enumerate(row))
                            for row in rows))
