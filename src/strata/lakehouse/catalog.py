"""The strata catalog: what the bundle declares, and the table definitions both engines build.

The bundle (databricks.yml and bundle/catalog.yml) declares the catalog, its four schemas and the
bronze files volume. A bundle does not declare tables, so each table is defined once, as one
`CREATE TABLE IF NOT EXISTS strata.<schema>.<table>` statement in tables/<schema>/<table>.sql.
build() runs those definitions through any engine: DuckDB for the fixture database in the gate,
the SQL warehouse for the deploy. IF NOT EXISTS means a deploy never replaces a table that holds
rows (CLAUDE.md rule 5); a change to a table's columns needs its own ALTER TABLE.

Every table keeps the date it became public in a public_from DATE column (ADR 0002).
check_public_from() looks at every table in the catalog, whatever made it, and stops when one
lacks the column or gives it another type. Views hold no rows of their own, so it skips plain
views and the metric views that Genie reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from strata.lakehouse import bundle as bundle_files
from strata.lakehouse.engine import Engine

CATALOG = "strata"
TABLES = Path(__file__).resolve().parent / "tables"
COMMENT_LINE = re.compile(r"^\s*--.*$", re.M)

MISSING_PUBLIC_FROM = """
SELECT t.table_schema, t.table_name
FROM system.information_schema.tables AS t
WHERE t.table_catalog = :catalog
  AND t.table_schema <> 'information_schema'
  AND t.table_type NOT IN ('VIEW', 'METRIC_VIEW')
  AND NOT EXISTS (
    SELECT 1
    FROM system.information_schema.columns AS c
    WHERE c.table_catalog = t.table_catalog
      AND c.table_schema = t.table_schema
      AND c.table_name = t.table_name
      AND c.column_name = 'public_from'
      AND c.data_type = 'DATE'
  )
ORDER BY t.table_schema, t.table_name
"""


class CatalogError(ValueError):
    """A table definition or a table that breaks the catalog's rules, with the fix."""


@dataclass(frozen=True)
class Declared:
    """The catalog as the bundle declares it."""

    catalog: str
    schemas: tuple[str, ...]
    volumes: tuple[str, ...]  # each as schema.volume
    grants: dict[str, dict[str, tuple[str, ...]]]  # securable -> principal -> privileges


def _grants(entry: dict) -> dict[str, tuple[str, ...]]:
    return {grant["principal"]: tuple(grant["privileges"]) for grant in entry.get("grants", [])}


def declared(bundle: bundle_files.Bundle | None = None) -> Declared:
    bundle = bundle or bundle_files.load()
    catalogs = [bundle.resolve(entry) for entry in bundle.resources("catalogs").values()]
    if [entry["name"] for entry in catalogs] != [CATALOG]:
        raise CatalogError(f"The bundle must declare one catalog, {CATALOG}.")
    schemas = [bundle.resolve(entry) for entry in bundle.resources("schemas").values()]
    volumes = [bundle.resolve(entry) for entry in bundle.resources("volumes").values()]
    grants = {CATALOG: _grants(catalogs[0])}
    grants |= {f"{CATALOG}.{entry['name']}": _grants(entry) for entry in schemas}
    grants |= {f"{CATALOG}.{entry['schema_name']}.{entry['name']}": _grants(entry) for entry in volumes}
    return Declared(
        catalog=CATALOG,
        schemas=tuple(entry["name"] for entry in schemas if entry["catalog_name"] == CATALOG),
        volumes=tuple(f"{entry['schema_name']}.{entry['name']}" for entry in volumes),
        grants=grants,
    )


@dataclass(frozen=True)
class TableDefinition:
    path: Path
    schema: str
    table: str
    sql: str

    @property
    def full_name(self) -> str:
        return f"{CATALOG}.{self.schema}.{self.table}"


def table_definitions(folder: Path = TABLES, schemas: tuple[str, ...] | None = None) -> list[TableDefinition]:
    """Every table definition in folder, checked against its file's place, in schema then table order."""
    schemas = schemas or declared().schemas
    found = []
    for path in sorted(Path(folder).glob("*/*.sql")):
        schema, table = path.parent.name, path.stem
        if schema not in schemas:
            raise CatalogError(f"{path.name} sits in the folder {schema}, which is not one of the catalog's "
                               f"schemas: {', '.join(schemas)}. Move it into one of those folders.")
        sql = path.read_text()
        statement = COMMENT_LINE.sub("", sql).strip()
        start = re.compile(rf"CREATE TABLE IF NOT EXISTS {CATALOG}\.{schema}\.{table}\s*\(", re.I)
        if not start.match(statement):
            raise CatalogError(f"{schema}/{path.name} must hold one statement that starts with "
                               f"CREATE TABLE IF NOT EXISTS {CATALOG}.{schema}.{table} (. IF NOT EXISTS keeps a "
                               "deploy from replacing a table that holds rows (CLAUDE.md rule 5).")
        found.append(TableDefinition(path, schema, table, sql))
    return found


def check_public_from(engine: Engine) -> None:
    """Stop when any table in the catalog has no public_from DATE column (ADR 0002)."""
    missing = engine.run(MISSING_PUBLIC_FROM, {"catalog": CATALOG}).as_text()
    if missing:
        names = ", ".join(f"{CATALOG}.{schema}.{table}" for schema, table in missing)
        raise CatalogError(f"These tables have no public_from column of type DATE: {names}. Every table keeps "
                           "the date each row became public (ADR 0002), so add a public_from DATE column.")


def build(engine: Engine, folder: Path = TABLES, create_schemas: bool = True) -> list[str]:
    """Create the declared schemas (unless the bundle made them) and every table, then check public_from.

    It returns the full names of the tables it defined. Running it again changes nothing.
    """
    schemas = declared().schemas
    definitions = table_definitions(folder, schemas)
    if create_schemas:
        for schema in schemas:
            engine.run(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{schema}")  # names from the bundle, never values
    for definition in definitions:
        engine.run(definition.sql)
    check_public_from(engine)
    return [definition.full_name for definition in definitions]
