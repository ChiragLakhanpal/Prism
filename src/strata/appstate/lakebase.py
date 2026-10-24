"""Lakebase, the app state store on the App (ADR 0005): a Postgres database the app reaches as itself.

LakebaseEngine runs Strata's SQL, written once in Databricks SQL with three-part names and :name parameters,
on Lakebase: one transpile step (sqlglot, from Databricks SQL to Postgres) rewrites each statement, leaves
out its comments, drops the catalog part (the app state database holds the schema app, and no catalog
called strata), and turns each :name into a bound psycopg parameter. No value is ever written into the SQL
text.

Lakebase keeps a few open connections for the next request, because opening one takes a TLS handshake and a
sign-in. A connection that closed or broke is replaced. Every connection signs in as the app's own service
principal: the user the app's database resource names (PGUSER) and the app's OAuth token as the password, as
Databricks documents for a Databricks App with a Lakebase database. No viewer's token reaches Lakebase.

psycopg is imported only when the environment names a database (PGHOST), so the server starts without it on
this computer; ops/app/requirements.txt installs it on the App.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from threading import Lock
from typing import Any

from strata.lakehouse.engine import EngineError, Params, PermissionDenied, Result, _names

# Postgres's SQLSTATE for a missing privilege.
INSUFFICIENT_PRIVILEGE = "42501"
# How many idle connections Lakebase keeps for the next request. The App runs one server process with a few
# threads, and the smallest Lakebase instance takes many more connections than this.
KEEP = 4
DEFAULT_DATABASE = "databricks_postgres"


def for_postgres(sql: str) -> str:
    """One Databricks SQL statement, rewritten for Lakebase's Postgres, in two-part names."""
    import sqlglot
    from sqlglot import exp
    from sqlglot.errors import ErrorLevel, ParseError, UnsupportedError

    try:
        statements = [s for s in sqlglot.parse(sql, read="databricks") if s is not None]
        if len(statements) != 1:
            raise EngineError(f"Each call runs one statement, and this SQL holds {len(statements)}.")
        statement = statements[0]
        for table in statement.find_all(exp.Table):
            if table.catalog == "strata":
                table.set("catalog", None)
        return statement.sql(dialect="postgres", unsupported_level=ErrorLevel.RAISE, comments=False)
    except (ParseError, UnsupportedError) as error:
        raise EngineError(f"The transpile step could not rewrite this SQL for Postgres: {error}") from error


def _failure(error: Exception) -> EngineError:
    message = " ".join(str(error).split()) or type(error).__name__
    if getattr(error, "sqlstate", None) == INSUFFICIENT_PRIVILEGE:
        return PermissionDenied(f"Lakebase refused the app: {message}")
    return EngineError(f"Lakebase could not run the statement: {message}")


def _is_database_error(error: Exception) -> bool:
    return hasattr(error, "sqlstate") or type(error).__module__.split(".")[0] == "psycopg"


class LakebaseEngine:
    """One statement at a time on one Lakebase connection. close() gives the connection back to Lakebase."""

    name = "lakebase"

    def __init__(self, connection, release: Callable[[Any], None] | None = None):
        self.connection = connection
        self._release = release

    def run(self, sql: str, params: Params = None) -> Result:
        text = for_postgres(sql)
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(text, dict(params or {}))
                if cursor.description is None:
                    return Result((), ())
                columns = tuple(getattr(column, "name", None) or column[0] for column in cursor.description)
                return Result(columns, tuple(tuple(row) for row in cursor.fetchall()))
        except Exception as error:
            if not _is_database_error(error):
                raise
            raise _failure(error) from error

    def insert_rows(self, table: str, columns: tuple[str, ...], rows: list[tuple]) -> int:
        _names(table, columns)
        if not rows:
            return 0
        statement = for_postgres(  # sql-lint: names only, checked by _names
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(':' + column for column in columns)})")
        try:
            with self.connection.cursor() as cursor:
                cursor.executemany(statement, [dict(zip(columns, row)) for row in rows])
        except Exception as error:
            if not _is_database_error(error):
                raise
            raise _failure(error) from error
        return len(rows)

    def table_bytes(self, table: str) -> int:
        _names(table, ())
        # psycopg sends a text value untyped, so Postgres reads the name as the table it names.
        found = self.run("SELECT pg_total_relation_size(:table) AS size", {"table": table.removeprefix("strata.")})
        return int(found.rows[0][0] or 0)

    def close(self) -> None:
        if self._release is not None:
            release, self._release = self._release, None
            release(self.connection)


class Lakebase:
    """The app state database: an engine per use, on a connection kept from an earlier use when one is open."""

    def __init__(self, connect: Callable[[], Any], keep: int = KEEP):
        self._connect = connect
        self._keep = keep
        self._idle: list = []
        self._lock = Lock()

    def engine(self) -> LakebaseEngine:
        with self._lock:
            while self._idle:
                connection = self._idle.pop()
                if not (getattr(connection, "closed", False) or getattr(connection, "broken", False)):
                    return LakebaseEngine(connection, self._give_back)
        try:
            connection = self._connect()
        except Exception as error:
            if not _is_database_error(error):
                raise
            raise _failure(error) from error
        return LakebaseEngine(connection, self._give_back)

    def __call__(self) -> LakebaseEngine:
        return self.engine()

    def _give_back(self, connection) -> None:
        usable = not (getattr(connection, "closed", False) or getattr(connection, "broken", False))
        with self._lock:
            if usable and len(self._idle) < self._keep:
                self._idle.append(connection)
                return
        if usable:
            connection.close()


def _psycopg_connect(**settings):
    import psycopg

    return psycopg.connect(**settings)


def from_environment(environ: Mapping[str, str], token: Callable[[], str],
                     connect: Callable[..., Any] | None = None) -> Lakebase | None:
    """Lakebase as the app's database resource names it (PGHOST, PGPORT, PGDATABASE, PGUSER and PGSSLMODE, which
    the platform sets), signed in with the app's own token, or None when the app has no database."""
    host, user = environ.get("PGHOST", "").strip(), environ.get("PGUSER", "").strip()
    if not host or not user:
        return None
    settings = {"host": host, "port": int(environ.get("PGPORT", "").strip() or 5432),
                "dbname": environ.get("PGDATABASE", "").strip() or DEFAULT_DATABASE, "user": user}
    sslmode = environ.get("PGSSLMODE", "").strip() or "require"
    connect = connect or (lambda **given: _psycopg_connect(**given))
    return Lakebase(lambda: connect(**settings, password=token(), sslmode=sslmode, autocommit=True,
                                    connect_timeout=10, application_name="strata"))
