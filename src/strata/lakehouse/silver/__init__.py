"""Silver: each source's pages, typed and cleaned on purpose (docs/PLAN.md section 3).

Each source in the registry names its silver transform, a module in this package with:

- TABLES      each silver table it fills, with the columns it writes, in order
- RECORD_KEY  the columns of its first table that tell one of the source's records from another,
              which the data readiness measures count (strata.lakehouse.readiness)
- FISCAL_YEAR optional: the column of its first table that holds each record's fiscal year, by
              which the dashboard's Data readiness page splits the records the measures count
- VERSION     optional: a whole number, 1 unless the module sets one. Bump it when parse() changes
              the rows it gives, and the next run reads every page of the source again
- parse()     one page's records turned into rows for each of its tables

Two sources may share a transform, as the IDA credits and the IBRD loans share loans, when their
records are the same kind of thing.

The transforms are Python, not SQL, because the work is JSON and HTML: the transpile step cannot
carry Databricks' from_json to DuckDB, and Spark SQL mangles the backslashes that a regular
expression in a SQL literal needs (docs/PLAN.md section 12). Each one takes a page and returns
plain rows, so both engines run it the same way. The cleaning rules themselves live in
strata.lakehouse.clean.

What silver wrote from each page is recorded in strata.ops.silver_pages (ticket 75): the source, the
page, the transform's tables and its version. run() reads a page when it has no record, or when its
newest record names other tables or another version than the transform has now, one page at a time.
For each page it takes out what each table holds of the page, writes the page's rows again with the
first table last, and then writes the record. So a page is read once; a run that stops partway
leaves the page waiting, and the rerun never holds a page twice or misses part of it; and a
transform that gains a table, or bumps its VERSION, reads every page of its source once more and
fills the new table from the pages bronze already holds. The record is the mark, not the rows: a page
whose rows were taken out of one table by hand is not read again until the transform changes. Gold
reads the newest row for each key, so a page fetched again after a change replaces the old values
there, and silver keeps every version.
"""

from __future__ import annotations

import datetime as dt
import importlib
import json
from collections.abc import Callable

from strata.config import Source
from strata.lakehouse.engine import Engine


def transform(source: Source):
    return importlib.import_module(f"strata.lakehouse.silver.{source.silver_transform}")


SILVER_PAGES = "strata.ops.silver_pages"
SILVER_PAGES_COLUMNS = ("source", "page_hash", "tables", "version", "written_at", "public_from")

PAGE = "SELECT body, fetched_at FROM strata.bronze.api_pages WHERE source = :source AND page_hash = :page_hash"

# The source's pages that silver has not read with the transform as it is now: one join on each page's newest record.
PENDING = """
WITH newest AS (
  SELECT page_hash, tables, version
  FROM strata.ops.silver_pages
  WHERE source = :source
  QUALIFY row_number() OVER (PARTITION BY page_hash ORDER BY written_at DESC) = 1
)
SELECT p.page_hash
FROM strata.bronze.api_pages AS p
LEFT JOIN newest AS r ON r.page_hash = p.page_hash
WHERE p.source = :source
  AND (r.page_hash IS NULL OR r.tables <> :tables OR r.version <> :version)
ORDER BY p.fetched_at, p.page_hash
"""


def tables(module) -> str:
    """The transform's tables as its record names them: sorted and joined with commas."""
    return ",".join(sorted(module.TABLES))


def version(module) -> int:
    """The transform's VERSION, 1 unless it sets one."""
    return int(getattr(module, "VERSION", 1))


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _holds(engine: Engine, table: str, page_hash: str) -> bool:
    query = f"SELECT count(*) AS n FROM {table} WHERE page_hash = :page_hash"  # sql-lint: names only, TABLES
    return int(engine.run(query, {"page_hash": page_hash}).rows[0][0]) > 0


def pending(engine: Engine, source: Source) -> list[str]:
    """The source's bronze pages that run() would read, oldest first."""
    module = transform(source)
    found = engine.run(PENDING, {"source": source.key, "tables": tables(module), "version": version(module)})
    return [page_hash for (page_hash,) in found.rows]


def run(engine: Engine, source: Source, clock: Callable[[], dt.datetime] = _now) -> int:
    """Parse the source's bronze pages that silver has not read with its transform as it is now, one at a
    time, so a fetch for every country never needs all its pages in memory, and record each page once its
    rows are written. Returns the rows it added."""
    module = transform(source)
    first = next(iter(module.TABLES))
    named, numbered = tables(module), version(module)
    added = 0
    for page_hash in pending(engine, source):
        body, fetched_at = engine.run(PAGE, {"source": source.key, "page_hash": page_hash}).rows[0]
        fetched_at = fetched_at if fetched_at.tzinfo else fetched_at.replace(tzinfo=dt.UTC)
        parsed = module.parse(json.loads(body), page_hash, fetched_at)
        # A run that stops between two inserts leaves the page without its record, so the rerun takes out what
        # the stopped run wrote of it before writing it again, and no table holds a page twice or misses part of
        # it (ticket 43; CLAUDE.md rule 5, a DELETE with a WHERE). The first table is still written last, as the
        # readiness measures count it, and the record after every table (ticket 75).
        for table in [name for name in module.TABLES if name != first] + [first]:
            if _holds(engine, table, page_hash):  # a read first: a Delta DELETE is a commit
                engine.run(f"DELETE FROM {table} WHERE page_hash = :page_hash",  # sql-lint: names only, TABLES
                           {"page_hash": page_hash})
            added += engine.insert_rows(table, module.TABLES[table], parsed.get(table, []))
        written = clock().astimezone(dt.UTC)
        engine.insert_rows(SILVER_PAGES, SILVER_PAGES_COLUMNS,
                           [(source.key, page_hash, named, numbered, written, written.date())])
    return added
