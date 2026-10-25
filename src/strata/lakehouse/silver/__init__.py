"""Silver: each source's pages, typed and cleaned on purpose (docs/PLAN.md section 3).

Each source in the registry names its silver transform, a module in this package with:

- TABLES      each silver table it fills, with the columns it writes, in order
- RECORD_KEY  the columns of its first table that tell one of the source's records from another,
              which the data readiness measures count (strata.lakehouse.readiness)
- FISCAL_YEAR optional: the column of its first table that holds each record's fiscal year, by
              which the dashboard's Data readiness page splits the records the measures count
- parse()     one page's records turned into rows for each of its tables

Two sources may share a transform, as the IDA credits and the IBRD loans share loans, when their
records are the same kind of thing.

The transforms are Python, not SQL, because the work is JSON and HTML: the transpile step cannot
carry Databricks' from_json to DuckDB, and Spark SQL mangles the backslashes that a regular
expression in a SQL literal needs (docs/PLAN.md section 12). Each one takes a page and returns
plain rows, so both engines run it the same way. The cleaning rules themselves live in
strata.lakehouse.clean.

A page is parsed once: run() reads only pages its first table has no rows from, one page at a
time, and adds their rows, writing the first table last. A run that stops partway leaves the page
waiting, and the next run takes out what it wrote of the page before writing it again, so a rerun
never holds a page twice. Gold reads the newest row for each key, so a page fetched again after a
change replaces the old values there, and silver keeps every version.
"""

from __future__ import annotations

import datetime as dt
import importlib
import json

from strata.config import Source
from strata.lakehouse.engine import Engine


def transform(source: Source):
    return importlib.import_module(f"strata.lakehouse.silver.{source.silver_transform}")


PAGE = "SELECT body, fetched_at FROM strata.bronze.api_pages WHERE source = :source AND page_hash = :page_hash"


def _holds(engine: Engine, table: str, page_hash: str) -> bool:
    query = f"SELECT count(*) AS n FROM {table} WHERE page_hash = :page_hash"  # sql-lint: names only, TABLES
    return int(engine.run(query, {"page_hash": page_hash}).rows[0][0]) > 0


def run(engine: Engine, source: Source) -> int:
    """Parse the source's bronze pages that silver has not read yet, one at a time, so a fetch for
    every country never needs all its pages in memory. Returns the rows it added."""
    module = transform(source)
    first = next(iter(module.TABLES))
    pending = (f"SELECT p.page_hash FROM strata.bronze.api_pages AS p WHERE p.source = :source "  # sql-lint: names only
               f"AND NOT EXISTS (SELECT 1 FROM {first} AS s WHERE s.page_hash = p.page_hash) "
               f"ORDER BY p.fetched_at, p.page_hash")
    added = 0
    for (page_hash,) in engine.run(pending, {"source": source.key}).rows:
        body, fetched_at = engine.run(PAGE, {"source": source.key, "page_hash": page_hash}).rows[0]
        fetched_at = fetched_at if fetched_at.tzinfo else fetched_at.replace(tzinfo=dt.UTC)
        parsed = module.parse(json.loads(body), page_hash, fetched_at)
        # The first table marks the page as read, so it is written last: a run that stops between two inserts
        # leaves the page waiting, and the rerun first takes out what the stopped run wrote of it, so no table
        # holds a page twice or misses part of it (ticket 43; CLAUDE.md rule 5, a DELETE with a WHERE).
        for table in [name for name in module.TABLES if name != first] + [first]:
            if table != first and _holds(engine, table, page_hash):  # a read first: a Delta DELETE is a commit
                engine.run(f"DELETE FROM {table} WHERE page_hash = :page_hash",  # sql-lint: names only, TABLES
                           {"page_hash": page_hash})
            added += engine.insert_rows(table, module.TABLES[table], parsed.get(table, []))
    return added
