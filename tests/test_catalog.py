"""The strata catalog (seam 1): what the bundle declares, and the table definitions that build
the same tables on DuckDB in the gate and on the workspace.

Every table keeps the date it became public in its public_from column (ADR 0002). The fixture
build stops when a table lacks one, and so does the gate.
"""

from pathlib import Path

import pytest

from strata.lakehouse import catalog
from strata.lakehouse.catalog import CatalogError
from strata.lakehouse.engine import DuckDBEngine

GOOD = "CREATE TABLE IF NOT EXISTS strata.{schema}.{table} (id STRING NOT NULL, public_from DATE NOT NULL)\n"


def definitions(tmp_path, **files):
    """A folder of table definitions: each keyword is schema__table and its SQL."""
    folder = tmp_path / "tables"
    for name, sql in files.items():
        schema, table = name.split("__")
        (folder / schema).mkdir(parents=True, exist_ok=True)
        (folder / schema / f"{table}.sql").write_text(sql.format(schema=schema, table=table))
    return folder


def tables(engine):
    result = engine.run("SELECT table_schema, table_name FROM system.information_schema.tables "
                        "WHERE table_catalog = 'strata' ORDER BY table_schema, table_name")
    return result.as_text()


def test_the_bundle_declares_the_catalog_its_four_schemas_and_the_bronze_files_volume():
    declared = catalog.declared()

    assert declared.catalog == "strata"
    assert declared.schemas == ("bronze", "silver", "gold", "ops")
    assert declared.volumes == ("bronze.files",)


def test_only_the_bundle_names_the_catalog():
    """Strata's SQL says strata. directly, so a setting that renamed the catalog would name one the deploy never makes."""
    repo = Path(__file__).resolve().parents[1]
    for path in (".env.example", "ops/wizard/strata-setup.sh"):
        assert "STRATA_CATALOG" not in (repo / path).read_text(), path


def test_the_bundle_grants_the_apps_users_read_access_to_the_catalog():
    readers = catalog.declared().grants

    assert readers["strata"] == {"account users": ("USE_CATALOG",)}
    for schema in ("bronze", "silver", "gold", "ops"):
        assert readers[f"strata.{schema}"] == {"account users": ("USE_SCHEMA", "SELECT")}
    assert readers["strata.bronze.files"] == {"account users": ("READ_VOLUME",)}


def test_the_table_definitions_build_on_duckdb_in_the_four_schemas():
    with DuckDBEngine.open() as engine:
        built = catalog.build(engine)
        schemas = engine.run("SELECT schema_name FROM system.information_schema.schemata "
                             "WHERE catalog_name = 'strata' ORDER BY schema_name").as_text()

        assert "strata.ops.pipeline_runs" in built
        assert ("ops", "pipeline_runs") in tables(engine)
    assert {("bronze",), ("silver",), ("gold",), ("ops",)} <= set(schemas)


def test_building_twice_keeps_the_rows_a_table_holds():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        engine.run("INSERT INTO strata.ops.pipeline_runs VALUES ('r1', 'score', 'succeeded', 0, "
                   "TIMESTAMP '2026-10-23 08:00:00', TIMESTAMP '2026-10-23 08:00:01', DATE '2026-10-23')")
        catalog.build(engine)

        assert engine.run("SELECT count(*) AS n FROM strata.ops.pipeline_runs").as_text() == [("1",)]


def test_every_table_in_the_fixture_database_keeps_its_public_from_date(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        assert ("ops", "pipeline_runs") in tables(engine)
        catalog.check_public_from(engine, skip=("recorded",))


def test_a_table_definition_without_public_from_stops_the_build(tmp_path):
    folder = definitions(tmp_path, ops__pipeline_runs=GOOD,
                         gold__supplier="CREATE TABLE IF NOT EXISTS strata.{schema}.{table} (id STRING)\n")

    with DuckDBEngine.open() as engine, pytest.raises(CatalogError, match=r"strata\.gold\.supplier.*public_from"):
        catalog.build(engine, folder)


def test_the_check_skips_only_the_schemas_its_caller_names():
    """The fixture database also holds recorded.files, its copy of the sources (ticket 05), which is
    not a catalog layer, so the fixture build skips `recorded`. Every other schema is checked,
    including one the bundle does not declare, such as the `main` schema a workspace can make."""
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        engine.run("CREATE SCHEMA strata.recorded")
        engine.run("CREATE TABLE strata.recorded.files (file STRING, recorded DATE)")

        catalog.check_public_from(engine, skip=("recorded",))

        engine.run("CREATE SCHEMA IF NOT EXISTS strata.main")
        engine.run("CREATE TABLE strata.main.notes (id STRING)")
        with pytest.raises(CatalogError, match=r"strata\.main\.notes") as stopped:
            catalog.check_public_from(engine, skip=("recorded",))
        assert "recorded" not in str(stopped.value)


def test_a_public_from_column_that_is_not_a_date_stops_the_build(tmp_path):
    folder = definitions(tmp_path, ops__pipeline_runs=GOOD,
                         gold__supplier="CREATE TABLE IF NOT EXISTS strata.{schema}.{table} (id STRING, public_from STRING)\n")

    with DuckDBEngine.open() as engine, pytest.raises(CatalogError, match=r"strata\.gold\.supplier"):
        catalog.build(engine, folder)


def test_a_view_needs_no_public_from_column_of_its_own(tmp_path):
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        engine.run("CREATE VIEW strata.gold.task_names AS SELECT DISTINCT task_key FROM strata.ops.pipeline_runs")

        catalog.check_public_from(engine)


def test_a_definition_that_could_replace_a_table_is_refused(tmp_path):
    folder = definitions(tmp_path, ops__pipeline_runs=GOOD.replace("IF NOT EXISTS", "").replace(
        "CREATE TABLE", "CREATE OR REPLACE TABLE"))

    with pytest.raises(CatalogError, match="CREATE TABLE IF NOT EXISTS strata.ops.pipeline_runs"):
        catalog.table_definitions(folder)


def test_a_definition_must_create_the_table_its_file_names(tmp_path):
    folder = definitions(tmp_path, ops__pipeline_runs=GOOD.replace("{table}", "runs"))

    with pytest.raises(CatalogError, match="strata.ops.pipeline_runs"):
        catalog.table_definitions(folder)


def test_a_definition_in_a_folder_that_is_not_a_schema_is_refused(tmp_path):
    folder = definitions(tmp_path, platinum__scores=GOOD)

    with pytest.raises(CatalogError, match="platinum.*bronze, silver, gold, ops"):
        catalog.table_definitions(folder)


def test_every_shipped_definition_sits_in_a_declared_schema_keeps_public_from_and_is_defined_once():
    """Adding a table is one file, so this checks the rule each file follows, not the list of files."""
    definitions = catalog.table_definitions()
    names = [definition.full_name for definition in definitions]

    assert "strata.ops.pipeline_runs" in names
    assert len(names) == len(set(names))
    for definition in definitions:
        assert definition.schema in catalog.declared().schemas, definition.path.name
        assert "public_from DATE" in definition.sql, definition.full_name


def test_the_view_definitions_build_after_the_tables():
    """A view is defined once too, in views/<schema>/<view>.sql beside the tables folder."""
    with DuckDBEngine.open() as engine:
        built = catalog.build(engine)
        kinds = dict(((schema, name), kind) for schema, name, kind in engine.run(
            "SELECT table_schema, table_name, table_type FROM system.information_schema.tables "
            "WHERE table_catalog = 'strata'").as_text())

    assert "strata.silver.awards_current" in built
    assert kinds["silver", "awards_current"] == "VIEW"


def views(tmp_path, **files):
    """A tables folder with one table, and a views folder beside it: each keyword is schema__view and its SQL."""
    folder = definitions(tmp_path, ops__pipeline_runs=GOOD)
    for name, sql in files.items():
        schema, view = name.split("__")
        (tmp_path / "views" / schema).mkdir(parents=True, exist_ok=True)
        (tmp_path / "views" / schema / f"{view}.sql").write_text(sql.format(schema=schema, view=view))
    return folder


def test_a_view_definition_must_replace_the_view_its_file_names(tmp_path):
    folder = views(tmp_path, ops__run_days="CREATE VIEW strata.{schema}.{view} AS SELECT 1 AS one\n")

    with DuckDBEngine.open() as engine, pytest.raises(
            CatalogError, match=r"CREATE OR REPLACE VIEW strata\.ops\.run_days AS"):
        catalog.build(engine, folder)


def test_a_view_in_a_folder_that_is_not_a_schema_is_refused(tmp_path):
    folder = views(tmp_path, platinum__scores="CREATE OR REPLACE VIEW strata.{schema}.{view} AS SELECT 1 AS one\n")

    with DuckDBEngine.open() as engine, pytest.raises(CatalogError, match="platinum.*bronze, silver, gold, ops"):
        catalog.build(engine, folder)
