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
the column or gives it another type. It reads the tables through listed_tables(), which the nightly's
table sizes measure reads too (strata.lakehouse.storage). Views hold no rows of their own, so the
listing leaves out plain views and the metric views that Genie reads. It also leaves out the search
index's own objects, which the AI Search service makes in the index's schema and Strata never defines:
the index that config/models.toml names, and every table of these two shapes, the event log and the view
an index serves from, which carry an index's id in their names, whichever index made them (ticket 87).
Nothing else is left out. The fixture build skips its
`recorded` schema, its copy of the sources, which is not a catalog layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from strata.config import load_search
from strata.lakehouse import bundle as bundle_files
from strata.lakehouse.engine import COLUMN_NAME, Engine

CATALOG = "strata"
TABLES = Path(__file__).resolve().parent / "tables"
VIEWS = "views"  # the folder beside the tables folder that holds the view definitions
COMMENT_LINE = re.compile(r"^\s*--.*$", re.M)

LISTED_TABLES = """
SELECT table_schema, table_name
FROM system.information_schema.tables
WHERE table_catalog = :catalog
  AND table_schema <> 'information_schema'
  AND table_type NOT IN ('VIEW', 'METRIC_VIEW')
ORDER BY table_schema, table_name
"""
DATED_TABLES = """
SELECT table_schema, table_name
FROM system.information_schema.columns
WHERE table_catalog = :catalog
  AND column_name = 'public_from'
  AND data_type = 'DATE'
"""
# The names the AI Search service gives the two tables it makes beside a Delta Sync index, in the index's schema:
# the event log of the pipeline that syncs it and the view the index serves from. Each carries the index's id, a
# UUID written with underscores, as strata.gold.event_log_cd8058ce_42aa_4722_ac9a_3ee310032e31 and
# strata.gold.__cd8058ce_42aa_4722_ac9a_3ee310032e31___online_index_view did on the paid workspace (ticket 87).
INDEX_ID_PATTERN = r"[0-9a-f]{8}(?:_[0-9a-f]{4}){3}_[0-9a-f]{12}"
INDEX_SERVICE_TABLES = (re.compile(rf"event_log_{INDEX_ID_PATTERN}"),
                        re.compile(rf"__{INDEX_ID_PATTERN}___online_index_view"))


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
    sources: tuple[str, ...] = ()  # a metric view's gold tables: its source and its joins'

    @property
    def full_name(self) -> str:
        return f"{CATALOG}.{self.schema}.{self.table}"


def _in_schema_order(folder: Path, schemas: tuple[str, ...]) -> list[Path]:
    """The definition files in folder, in the order bundle/catalog.yml declares their schemas (bronze, silver, gold,
    ops), then by name, so a gold view may read a silver view. A file in a folder that is no schema comes last, for
    the caller to refuse."""
    def place(path: Path) -> tuple[int, str]:
        schema = path.parent.name
        return (schemas.index(schema) if schema in schemas else len(schemas), path.as_posix())

    return sorted(Path(folder).glob("*/*.sql"), key=place)


def table_definitions(folder: Path = TABLES, schemas: tuple[str, ...] | None = None) -> list[TableDefinition]:
    """Every table definition in folder, checked against its file's place, in schema then table order."""
    schemas = schemas or declared().schemas
    found = []
    for path in _in_schema_order(folder, schemas):
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
    for path in _in_schema_order(folder, schemas):
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


def defined_names() -> frozenset[str]:
    """The three-part name of every table, view and metric view this catalog defines, read from the definition
    files' places alone. It does not read the bundle, so the App, which holds src/strata but no databricks.yml,
    can call it (the tool registry's lineage, ticket 45)."""
    tables = TABLES.glob("*/*.sql")
    views = TABLES.with_name(VIEWS).glob("*/*.sql")
    metric_views = METRIC_VIEWS.glob("*/*.yaml")
    return frozenset(f"{CATALOG}.{path.parent.name}.{path.stem}" for path in (*tables, *views, *metric_views))


def is_index_object(schema: str, table: str, index: str) -> bool:
    """Whether strata.<schema>.<table> is one of the search index's own objects: the index config/models.toml
    names, or a table the AI Search service made beside it in its schema with the index's id in its name. The
    service makes them and Strata never defines them, so none holds a public_from column (ticket 87)."""
    index_catalog, index_schema, index_name = index.split(".")
    if (index_catalog, index_schema) != (CATALOG, schema):
        return False
    return table == index_name or any(pattern.fullmatch(table) for pattern in INDEX_SERVICE_TABLES)


def listed_tables(engine: Engine) -> list[tuple[str, str]]:
    """Every table in the catalog, as (schema, table) in schema then table order, whatever made it. Views and
    metric views hold no rows of their own, and the search index's own objects are the AI Search service's
    (is_index_object), so the listing leaves them out. The public_from check and the nightly's table sizes measure
    both read it, so neither reads the index's view, which has no columns."""
    index = load_search().index
    return [(schema, table) for schema, table in engine.run(LISTED_TABLES, {"catalog": CATALOG}).as_text()
            if not is_index_object(schema, table, index)]


def check_public_from(engine: Engine, skip: tuple[str, ...] = ()) -> None:
    """Stop when any table in the catalog, outside the schemas in skip, has no public_from DATE column (ADR 0002)."""
    dated = set(engine.run(DATED_TABLES, {"catalog": CATALOG}).as_text())
    missing = [(schema, table) for schema, table in listed_tables(engine)
               if schema not in skip and (schema, table) not in dated]
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
    sources = (spec["source"], *[join["source"] for join in spec.get("joins") or []])
    for source in sources:
        if source not in tables:
            raise CatalogError(f"{where} reads {source}, which is not a gold table defined in tables/gold. A metric "
                               "view reads gold tables only.")
    sql = (f"CREATE OR REPLACE VIEW {CATALOG}.{schema}.{view}\nWITH METRICS\nLANGUAGE YAML\n"  # sql-lint: names only
           f"AS $$\n{body}\n$$")
    return TableDefinition(path, schema, view, sql, sources)


def metric_view_definitions(folder: Path = METRIC_VIEWS) -> list[TableDefinition]:
    """Every metric view in folder, one YAML body per file at metric_views/gold/<view>.yaml, checked against the
    rules fairshare's docs/limits.md gives (ticket 33's notes): no semicolon in the body, no join named like a
    dimension, and a source that is a gold table. Databricks only: DuckDB has no metric views, so build() never runs
    them and the gate checks these rules instead.

    The gold tables are read from tables/gold's file names, not through table_definitions(), which reads the bundle:
    ask_genie reads these definitions on every question, and the App holds src/strata but no databricks.yml or
    bundle/ (ops/app/deploy_app.py, package())."""
    gold = {f"{CATALOG}.gold.{path.stem}" for path in sorted((TABLES / "gold").glob("*.sql"))}
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
    """The gold tables each metric view reads, its source and its joins', by the view's full name, from the same
    checked definitions the deploy creates, so every name in it is a gold table defined in tables/gold."""
    return {view.full_name: view.sources for view in metric_view_definitions(folder)}
