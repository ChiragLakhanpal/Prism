"""Silver: each source's pages, typed and cleaned on purpose (docs/PLAN.md section 3).

Each source in the registry names its silver transform, a module in this package with:

- TABLES   each silver table it fills, with the columns it writes, in order
- PENDING  a query for the bronze pages its first table has no rows from yet
- parse()  one page's records turned into rows for each of its tables

The transforms are Python, not SQL, because the work is JSON and HTML: the transpile step cannot
carry Databricks' from_json to DuckDB, and Spark SQL mangles the backslashes that a regular
expression in a SQL literal needs (docs/PLAN.md section 12). Each one takes a page and returns
plain rows, so both engines run it the same way. The cleaning rules themselves live in
strata.lakehouse.clean.

A page is parsed once: run() reads only pages its tables have no rows from, and adds their rows.
Gold reads the newest row for each key, so a page fetched again after a change replaces the old
values there, and silver keeps every version.
"""

from __future__ import annotations

import datetime as dt
import importlib
import json

from strata.config import Source
from strata.lakehouse.engine import Engine


def transform(source: Source):
    return importlib.import_module(f"strata.lakehouse.silver.{source.silver_transform}")


def run(engine: Engine, source: Source) -> int:
    """Parse the source's bronze pages that silver has not read yet. Returns the rows it added."""
    module = transform(source)
    added = 0
    for page_hash, body, fetched_at in engine.run(module.PENDING, {"source": source.key}).rows:
        fetched_at = fetched_at if fetched_at.tzinfo else fetched_at.replace(tzinfo=dt.UTC)
        for table, rows in module.parse(json.loads(body), page_hash, fetched_at).items():
            added += engine.insert_rows(table, module.TABLES[table], rows)
    return added
