"""How much room the strata catalog takes, measured by every run of the nightly job.

Structured data for every country must stay under the limit in config/thresholds.toml
(ingestion.structured_data_limit_bytes, from docs/PLAN.md section 3). measure() records each
table's rows and bytes in strata.ops.table_sizes, marking the tables that hold documents' text,
layout, passages and vectors as not structured. The Governance page adds up the structured ones.
Each engine says how many bytes a table takes (Engine.table_bytes): Databricks from its Delta files,
DuckDB from the blocks of its database file.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from strata.lakehouse import catalog
from strata.lakehouse.engine import Engine

COLUMNS = ("run_id", "table_name", "structured", "row_count", "bytes", "measured_at", "public_from")
# The tables that hold documents' text, layout, passages and the passages' vectors rather than
# records. A new table of document text or vectors goes here, so it never counts as structured data.
DOCUMENT_TABLES = ("strata.bronze.document_pages", "strata.bronze.document_texts", "strata.bronze.layout_pages",
                   "strata.silver.documents", "strata.silver.document_page_routes", "strata.silver.passages",
                   "strata.silver.passage_embeddings", "strata.silver.passage_shields", "strata.gold.passage")


def measure(engine: Engine, run_id: str, clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)) -> int:
    """Record each catalog table's rows and bytes under the run's id, from the catalog's listing, which leaves out
    views and the search index's own objects (catalog.listed_tables; ticket 87). Returns how many rows it wrote."""
    measured_at = clock()
    schemas = catalog.declared().schemas
    rows = []
    for schema, name in catalog.listed_tables(engine):
        if schema not in schemas:
            continue  # the fixture database's own copy of the sources, for one
        table = f"{catalog.CATALOG}.{schema}.{name}"
        count = engine.run(f"SELECT count(*) AS n FROM {table}").rows[0][0]  # sql-lint: names only, from the catalog
        rows.append((run_id, table, table not in DOCUMENT_TABLES, int(count), engine.table_bytes(table),
                     measured_at, measured_at.astimezone(dt.UTC).date()))
    return engine.insert_rows("strata.ops.table_sizes", COLUMNS, rows)
