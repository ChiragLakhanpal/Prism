"""App state in Lakebase (ADR 0005): the same SQL that runs on DuckDB reaches Lakebase's Postgres.

Lakebase is reached through a fake of a Postgres connection, in the shape psycopg's connections and cursors
have, because the offline tests never leave this computer. The workspace step that deploys the app and
plans a package on it runs the real thing (docs/workspace-catchup.md, ticket 15).
"""

import datetime as dt

import pytest

from strata import appstate
from strata.appstate.lakebase import Lakebase, LakebaseEngine, from_environment
from strata.lakehouse.engine import EngineError, PermissionDenied

SAVED = dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC)


class Column:
    def __init__(self, name):
        self.name = name


class PostgresError(Exception):
    def __init__(self, message, sqlstate):
        super().__init__(message)
        self.sqlstate = sqlstate


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.connection.statements.append((sql, params))
        if self.connection.fail:
            raise self.connection.fail
        rows = self.connection.answer
        self.description = [Column(name) for name in rows[0]] if rows else None
        self._rows = [tuple(row.values()) for row in rows]

    def executemany(self, sql, params):
        self.connection.statements.append((sql, list(params)))

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, answer=None, fail=None):
        self.statements, self.answer, self.fail = [], answer or [], fail
        self.closed = False
        self.broken = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


def test_a_query_written_for_databricks_reaches_lakebase_in_postgres_with_its_values_bound():
    connection = FakeConnection(answer=[{"package_id": "pkg-000000000001", "saved_at": SAVED}])

    result = LakebaseEngine(connection).run(
        "SELECT package_id, saved_at FROM (SELECT package_id, saved_at, row_number() OVER (PARTITION BY package_id "
        "ORDER BY saved_at DESC) AS newest FROM strata.app.planned_package_saves WHERE package_id = :package_id) "
        "AS saved WHERE newest = 1", {"package_id": "pkg-000000000001"})

    [(sql, params)] = connection.statements
    # Two-part names: the app state database holds the schema app, and no catalog called strata.
    assert "FROM app.planned_package_saves" in sql and "strata." not in sql
    assert "package_id = %(package_id)s" in sql
    assert params == {"package_id": "pkg-000000000001"}
    assert result.columns == ("package_id", "saved_at")
    assert result.rows == (("pkg-000000000001", SAVED),)


def test_rows_are_added_by_column_name_with_every_value_bound():
    connection = FakeConnection()

    added = LakebaseEngine(connection).insert_rows("strata.app.planned_packages", ("package_id", "sentence"), [
        ("pkg-000000000001", "rural roads, Kenya, about US$15 million"), ("pkg-000000000002", "x'); DROP TABLE y; --")])

    [(sql, params)] = connection.statements
    assert sql == "INSERT INTO app.planned_packages (package_id, sentence) VALUES (%(package_id)s, %(sentence)s)"
    assert params[1] == {"package_id": "pkg-000000000002", "sentence": "x'); DROP TABLE y; --"}
    assert added == 2


def test_a_risk_selection_reaches_lakebase_as_a_merge_with_its_values_bound():
    """Ticket 30 keeps one row per viewer, package and risk, changed by a MERGE, so unselecting deletes nothing."""
    from strata.packages.store import PackageStore

    connection = FakeConnection()
    store = PackageStore(lambda: LakebaseEngine(connection))
    store._built = True
    store.select_risks("4021@1984", "planned", "pkg-000000000001", {"cost_estimates": False},
                       dt.datetime(2026, 10, 28, 9, tzinfo=dt.UTC))

    [(sql, params)] = connection.statements
    assert sql.startswith("MERGE INTO app.risk_selections AS t USING (SELECT %(viewer_id)s AS viewer_id")
    assert "DELETE" not in sql
    assert (params["risk_key"], params["selected"]) == ("cost_estimates", False)


def test_insert_rows_takes_only_plain_names():
    with pytest.raises(EngineError):
        LakebaseEngine(FakeConnection()).insert_rows("strata.app.planned_packages; DROP", ("package_id",), [("x",)])


def test_the_app_state_tables_are_made_in_postgres_types_in_the_schema_app():
    connection = FakeConnection()

    made = appstate.build(LakebaseEngine(connection))

    statements = [sql for sql, _ in connection.statements]
    assert statements[0] == "CREATE SCHEMA IF NOT EXISTS app"
    assert made == ["strata.app.plan_checks_opened", "strata.app.plan_date_choices", "strata.app.planned_package_saves",
                    "strata.app.planned_packages", "strata.app.risk_selections", "strata.app.step_start_dates"]
    saves = next(sql for sql in statements if "app.planned_package_saves" in sql)
    assert saves.startswith("CREATE TABLE IF NOT EXISTS app.planned_package_saves")
    assert "saved_at TIMESTAMPTZ NOT NULL" in saves and "criteria TEXT NOT NULL" in saves
    assert "public_from DATE NOT NULL" in saves


def test_a_refused_grant_is_a_permission_error_and_any_other_failure_an_engine_error():
    refused = FakeConnection(fail=PostgresError("permission denied for table planned_packages", "42501"))
    broken = FakeConnection(fail=PostgresError("relation app.planned_packages does not exist", "42P01"))

    with pytest.raises(PermissionDenied):
        LakebaseEngine(refused).run("SELECT package_id FROM strata.app.planned_packages")
    with pytest.raises(EngineError, match="does not exist"):
        LakebaseEngine(broken).run("SELECT package_id FROM strata.app.planned_packages")


def test_lakebase_keeps_a_connection_for_the_next_request_and_replaces_one_that_closed():
    opened = []

    def connect():
        opened.append(FakeConnection(answer=[{"one": 1}]))
        return opened[-1]

    lakebase = Lakebase(connect)
    for _ in range(3):
        engine = lakebase.engine()
        engine.run("SELECT 1 AS one")
        engine.close()
    assert len(opened) == 1
    opened[0].closed = True
    engine = lakebase.engine()
    engine.run("SELECT 1 AS one")
    engine.close()
    assert len(opened) == 2


def test_on_the_app_lakebase_is_reached_with_the_database_resource_s_settings_and_the_app_s_own_token():
    calls = []
    tokens = iter(["app-not-real-1", "app-not-real-2"])

    lakebase = from_environment({"PGHOST": "instance-1.database.cloud.databricks.com", "PGPORT": "5432",
                                 "PGDATABASE": "databricks_postgres", "PGUSER": "strata-app-client-id",
                                 "PGSSLMODE": "require"}, token=lambda: next(tokens),
                                connect=lambda **settings: calls.append(settings) or FakeConnection())
    lakebase.engine().close()

    assert calls == [{"host": "instance-1.database.cloud.databricks.com", "port": 5432, "dbname": "databricks_postgres",
                      "user": "strata-app-client-id", "password": "app-not-real-1", "sslmode": "require",
                      "autocommit": True, "connect_timeout": 10, "application_name": "strata"}]
    assert from_environment({}, token=lambda: "app-not-real") is None
