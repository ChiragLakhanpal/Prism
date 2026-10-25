"""The strata catalog: what the bundle declares, and the table definitions both engines build.

The bundle (databricks.yml and bundle/catalog.yml) declares the catalog, its four schemas and the
bronze files volume. A bundle does not declare tables, so each table is defined once, as one
`CREATE TABLE IF NOT EXISTS strata.<schema>.<table>` statement in tables/<schema>/<table>.sql.
build() runs those definitions through any engine: DuckDB for the fixture database in the gate,
the SQL warehouse for the deploy. IF NOT EXISTS means a deploy never replaces a table that holds
rows (CLAUDE.md rule 5); a change to a table's columns needs its own ALTER TABLE.

A view holds no rows, so it is defined as one `CREATE OR REPLACE VIEW strata.<schema>.<view> AS`
statement in views/<schema>/<view>.sql, in the folder beside tables/. build() creates the views
after the tables, in schema then view order, so each deploy carries a changed view's query.

Every table keeps the date it became public in a public_from DATE column (ADR 0002).
check_public_from() looks at every table in the catalog, whatever made it, and stops when one lacks
the column or gives it another type. Views hold no rows of their own, so it skips plain views and
the metric views that Genie reads. The fixture build skips its `recorded` schema, its copy of the
sources, which is not a catalog layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from strata.lakehouse import bundle as bundle_files
from strata.lakehouse.engine import COLUMN_NAME, Engine

CATALOG = "strata"
TABLES = Path(__file__).resolve().parent / "tables"
VIEWS = "views"  # the folder beside the tables folder that holds the view definitions
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
        start = re.compile(  # sql-lint: names only, a pattern for the definition's first line
            rf"CREATE TABLE IF NOT EXISTS {CATALOG}\.{schema}\.{table}\s*\(", re.I)
        if not start.match(statement):
            raise CatalogError(f"{schema}/{path.name} must hold one statement that starts with "
                               f"CREATE TABLE IF NOT EXISTS {CATALOG}.{schema}.{table} (. IF NOT EXISTS keeps a "
                               "deploy from replacing a table that holds rows (CLAUDE.md rule 5).")
        found.append(TableDefinition(path, schema, table, sql))
    return found


def view_definitions(folder: Path = TABLES.with_name(VIEWS),
                     schemas: tuple[str, ...] | None = None) -> list[TableDefinition]:
    """Every view definition in folder, checked against its file's place, in schema then view order."""
    schemas = schemas or declared().schemas
    found = []
    for path in sorted(Path(folder).glob("*/*.sql")):
        schema, view = path.parent.name, path.stem
        if schema not in schemas:
            raise CatalogError(f"{path.name} sits in the folder {schema}, which is not one of the catalog's "
                               f"schemas: {', '.join(schemas)}. Move it into one of those folders.")
        sql = path.read_text()
        start = re.compile(  # sql-lint: names only, a pattern for the definition's first line
            rf"CREATE OR REPLACE VIEW {CATALOG}\.{schema}\.{view}\s+AS\s", re.I)
        if not start.match(COMMENT_LINE.sub("", sql).strip()):
            raise CatalogError(f"{VIEWS}/{schema}/{path.name} must hold one statement that starts with "
                               f"CREATE OR REPLACE VIEW {CATALOG}.{schema}.{view} AS. A view holds no rows, so "
                               "each build replaces it with its current query.")
        found.append(TableDefinition(path, schema, view, sql))
    return found


def check_public_from(engine: Engine, skip: tuple[str, ...] = ()) -> None:
    """Stop when any table in the catalog, outside the schemas in skip, has no public_from DATE column (ADR 0002)."""
    missing = [(schema, table) for schema, table in engine.run(MISSING_PUBLIC_FROM, {"catalog": CATALOG}).as_text()
               if schema not in skip]
    if missing:
        names = ", ".join(f"{CATALOG}.{schema}.{table}" for schema, table in missing)
        raise CatalogError(f"These tables have no public_from column of type DATE: {names}. Every table keeps "
                           "the date each row became public (ADR 0002), so add a public_from DATE column.")


def build(engine: Engine, folder: Path = TABLES, create_schemas: bool = True) -> list[str]:
    """Create the declared schemas (unless the bundle made them) and every table, check public_from,
    then create the views defined in the views folder beside folder.

    It returns the full names of the tables and views it defined. Running it again changes no rows.
    """
    schemas = declared().schemas
    definitions = table_definitions(folder, schemas)
    views = view_definitions(Path(folder).with_name(VIEWS), schemas)
    if create_schemas:
        for schema in schemas:
            engine.run(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{schema}")  # sql-lint: names only, from the bundle
    for definition in definitions:
        engine.run(definition.sql)
    check_public_from(engine)
    for view in views:
        engine.run(view.sql)
    return [definition.full_name for definition in definitions + views]


# ── Metric views, for Genie (ticket 33) ─────────────────────────────────

METRIC_VIEWS = TABLES.with_name("metric_views")  # the folder beside tables/ that holds the metric views
METRIC_VIEW_KEYS = ("version", "source", "dimensions", "measures")


def _metric_view(path: Path, schema: str, view: str, tables: set[str]) -> TableDefinition:
    import yaml

    where = f"metric_views/{schema}/{path.name}"
    text = path.read_text()
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#")).strip()
    if ";" in body:
        raise CatalogError(f"{where} holds a semicolon. The SQL task cuts a file at every semicolon outside quotes, "
                           "so a metric view's body holds none.")
    try:
        spec = yaml.safe_load(body)
    except yaml.YAMLError as error:
        raise CatalogError(f"{where} is not valid YAML: {error}") from error
    missing = [key for key in METRIC_VIEW_KEYS if not (spec or {}).get(key)]
    if missing:
        raise CatalogError(f"{where} needs {', '.join(missing)}.")
    dimensions = [entry["name"] for entry in spec["dimensions"]]
    measures = [entry["name"] for entry in spec["measures"]]
    for name in dimensions + measures + [join.get("name", "") for join in spec.get("joins") or []]:
        if not COLUMN_NAME.fullmatch(name):
            raise CatalogError(f"{where} names {name!r}. Write every name in snake_case.")
    if len(set(dimensions + measures)) != len(dimensions + measures):
        raise CatalogError(f"{where} gives two dimensions or measures one name.")
    for join in spec.get("joins") or []:
        if join["name"] in dimensions:
            raise CatalogError(f"{where} has a join named {join['name']}, like one of its dimensions. Genie reads "
                               "such a name as the dimension, so give the join another name.")
    for source in [spec["source"], *[join["source"] for join in spec.get("joins") or []]]:
        if source not in tables:
            raise CatalogError(f"{where} reads {source}, which is not a gold table defined in tables/gold. A metric "
                               "view reads gold tables only.")
    sql = (f"CREATE OR REPLACE VIEW {CATALOG}.{schema}.{view}\nWITH METRICS\nLANGUAGE YAML\n"  # sql-lint: names only
           f"AS $$\n{body}\n$$")
    return TableDefinition(path, schema, view, sql)


def metric_view_definitions(folder: Path = METRIC_VIEWS) -> list[TableDefinition]:
    """Every metric view in folder, one YAML body per file at metric_views/gold/<view>.yaml, checked against the
    rules fairshare's docs/limits.md gives (ticket 33's notes): no semicolon in the body, no join named like a
    dimension, and a source that is a gold table. Databricks only: DuckDB has no metric views, so build() never runs
    them and the gate checks these rules instead."""
    gold = {definition.full_name for definition in table_definitions() if definition.schema == "gold"}
    found = []
    for path in sorted(Path(folder).glob("*/*.yaml")):
        schema = path.parent.name
        if schema != "gold":
            raise CatalogError(f"{path.name} sits in metric_views/{schema}. Genie's metric views go in "
                               "metric_views/gold.")
        found.append(_metric_view(path, schema, path.stem, gold))
    return found


def build_metric_views(engine: Engine, folder: Path = METRIC_VIEWS) -> list[str]:
    """Create or replace each metric view on the SQL warehouse, after build() has made the gold tables it reads."""
    views = metric_view_definitions(folder)
    for view in views:
        engine.run(view.sql)
    return [view.full_name for view in views]


def metric_view_sources(folder: Path = METRIC_VIEWS) -> dict[str, tuple[str, ...]]:
    """The gold tables each metric view reads, its source and its joins', by the view's full name. It reads the
    files without checking them, which metric_view_definitions() does in the gate and the deploy."""
    import yaml

    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    found = {}
    for path in sorted(Path(folder).glob("*/*.yaml")):
        spec = yaml.load(path.read_text(), Loader=loader)
        found[f"{CATALOG}.{path.parent.name}.{path.stem}"] = (
            spec["source"], *[join["source"] for join in spec.get("joins") or []])
    return found
