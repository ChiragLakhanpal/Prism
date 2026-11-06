"""App state: what people make in Prism and expect to find again, kept in Lakebase (ADR 0005).

The Lakebase probe chose Lakebase over strata.ops for app state (docs/app-state.md): a write and a read took
145 ms there in the middle, against 2,293 ms on the SQL warehouse. Ticket 15 writes the first app state, the
packages a person plans and the plan checks they open, so it sets up how the app reaches Lakebase:

- Each table is defined once, in Databricks SQL like every other table, as one
  `CREATE TABLE IF NOT EXISTS strata.app.<table>` statement in tables/app/<table>.sql. build() runs those
  definitions on any engine: DuckDB on this computer and in the gate, and Lakebase on the App, through
  LakebaseEngine (lakebase.py), which rewrites each statement for Postgres. The schema is app, so the SQL
  lint's three-part names hold, and strata.app never names a table in Unity Catalog.
- On the App, the app reaches Lakebase as its own service principal, through the database resource the
  deploy gives it (ops/app/deploy_app.py), with its own OAuth token as the password. A viewer's forwarded
  token is never sent to Lakebase. Each read and write names the viewer it is for, bound per request
  (CLAUDE.md rule 7), and the routes show a person only their own rows, as the drafts' routes do
  (src/strata/server/packages.py). The team rule for uploads (CLAUDE.md rule 8) will filter by team the
  same way.
- The app makes its tables when it first needs them (PackageStore asks build() once), so a deploy needs to
  give the app only its database, and a table that holds rows is never replaced (CLAUDE.md rule 5).

Usage events, agent runs, opened sources and every measure stay in strata.ops, because the dashboard reads
them there.
"""

from __future__ import annotations

from pathlib import Path

from strata.lakehouse.catalog import table_definitions
from strata.lakehouse.engine import Engine

SCHEMA = "app"
TABLES = Path(__file__).resolve().parent / "tables"


def build(engine: Engine) -> list[str]:
    """Create the schema app and every app state table, unless they exist. Running it again changes no rows.
    It returns the tables' full names."""
    definitions = table_definitions(TABLES, (SCHEMA,))
    engine.run(f"CREATE SCHEMA IF NOT EXISTS strata.{SCHEMA}")  # sql-lint: names only, the one app state schema
    for definition in definitions:
        engine.run(definition.sql)
    return [definition.full_name for definition in definitions]
