"""Silver: each source's pages, typed and cleaned on purpose (docs/PLAN.md section 3).

Each source in the registry names its silver transform, a module in this package with:

- TABLES      each silver table it fills, with the columns it writes, in order
- RECORD_KEY  the columns of its first table that tell one of the source's records from another,
              which the data readiness measures count (strata.lakehouse.readiness)
- FISCAL_YEAR optional: the column of its first table that holds each record's fiscal year, by
              which the dashboard's Data readiness page splits the records the measures count
- VERSION     optional: a whole number, 1 unless the module sets one. Bump it when parse() changes
              the rows it gives, and the next run reads every page of the source again
- read_again() optional: a condition on its first table's rows, with the values it binds. The next
              run reads again each page whose rows the condition finds, whatever its record says
              (ticket 121), so a fix reaches only the pages that need it
- parse()     one page's records turned into rows for each of its tables

Two sources may share a transform, as the IDA credits and the IBRD loans share loans, when their
records are the same kind of thing.

The transforms are Python, not SQL, because the work is JSON and HTML: the transpile step cannot
carry Databricks' from_json to DuckDB, and Spark SQL mangles the backslashes that a regular
expression in a SQL literal needs (docs/PLAN.md section 12). Each one takes a page and returns
plain rows, so both engines run it the same way. The cleaning rules themselves live in
strata.lakehouse.clean.

What silver wrote from each page is recorded in strata.ops.silver_pages (ticket 75): the source, the
page, the transform's tables and its version. read() reads a page when it has no record, or when its
newest record names other tables or another version than the transform has now. So a page is read once,
and a transform that gains a table, or bumps its VERSION, reads every page of its source once more and
fills the new table from the pages bronze already holds. The record is the mark, not the rows: a page
whose rows were taken out of one table by hand is not read again until the transform changes, or
until its rows meet the transform's read_again() condition, as the notices whose text still holds a
contact detail do (ticket 121). Gold
reads the newest row for each key, so a page fetched again after a change replaces the old values
there, and silver keeps every version.

The pages are read in groups (config/thresholds.toml, ingestion.silver_group_pages), oldest first, and a
group costs a few statements whatever its size (ticket 85): one read of its pages, one read of which of
them the tables hold already, then for each table a DELETE with a WHERE for the pages it holds, only
when it holds some, and one insert of the group's rows, with the first table last, and then one insert
of the group's records. Page by page, a page cost about four statements for each table: 6.3 seconds a
page on the paid workspace's warehouse on October 26, 2026. A run that stops between two statements
leaves its group without records, so the rerun reads the group again, takes out what the stopped run
wrote of it, and writes it once more: no table holds a page twice or misses part of it. A pass given a
time (until) stops at the end of the group during which that time came, records the group, and counts
the pages it left for the next run (Pass.waiting), so gold still runs inside the job's window.
"""

from __future__ import annotations

import datetime as dt
import importlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from strata.config import Source, load_thresholds
from strata.lakehouse.engine import Engine


def transform(source: Source):
    return importlib.import_module(f"strata.lakehouse.silver.{source.silver_transform}")


SILVER_PAGES = "strata.ops.silver_pages"
SILVER_PAGES_COLUMNS = ("source", "page_hash", "tables", "version", "written_at", "public_from")

# The source's pages that silver has not read with the transform as it is now: one join on each page's newest record.
# A page that changed and then changed back is in bronze twice with one hash (strata.lakehouse.bronze), and silver
# reads it once, from its first fetch.
PENDING = """
WITH newest AS (
  SELECT page_hash, tables, version
  FROM strata.ops.silver_pages
  WHERE source = :source
  QUALIFY row_number() OVER (PARTITION BY page_hash ORDER BY written_at DESC) = 1
)
SELECT p.page_hash, min(p.fetched_at) AS first_fetched
FROM strata.bronze.api_pages AS p
LEFT JOIN newest AS r ON r.page_hash = p.page_hash
WHERE p.source = :source
  AND (r.page_hash IS NULL OR r.tables <> :tables OR r.version <> :version{again})
GROUP BY p.page_hash
ORDER BY first_fetched, p.page_hash
"""
# The pages whose rows the transform's read_again() condition finds, read again whatever their record says.
AGAIN = "\n       OR p.page_hash IN (SELECT page_hash FROM {table} WHERE {condition})"


def _pending_query(module) -> tuple[str, dict]:
    """PENDING for the transform, with its read_again() condition and the values that binds, when it has one."""
    again = getattr(module, "read_again", None)
    if again is None:
        return PENDING.format(again=""), {}
    condition, params = again()
    first = next(iter(module.TABLES))
    return PENDING.format(again=AGAIN.format(table=first, condition=condition)), params  # sql-lint: names only


def tables(module) -> str:
    """The transform's tables as its record names them: sorted and joined with commas."""
    return ",".join(sorted(module.TABLES))


def version(module) -> int:
    """The transform's VERSION, 1 unless it sets one."""
    return int(getattr(module, "VERSION", 1))


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def pending(engine: Engine, source: Source) -> list[str]:
    """The source's bronze pages that read() would read, oldest first."""
    module = transform(source)
    query, again = _pending_query(module)
    found = engine.run(query, {**again, "source": source.key, "tables": tables(module), "version": version(module)})
    return [page_hash for page_hash, _ in found.rows]


@dataclass(frozen=True)
class Waiting:
    """A source's pages that a pass given a time left for the next run."""

    source: str
    pages: int  # the pages left
    pending: int  # the pages that were waiting when the pass began


@dataclass(frozen=True)
class Pass:
    """What one pass wrote: the rows it added and, when its time came before it read every page, the time it
    stopped and the pages it left for the next run, by source."""

    added: int
    stopped_at: dt.datetime | None = None
    waiting: tuple[Waiting, ...] = ()


def _marks(page_hashes: list[str]) -> tuple[str, dict[str, str]]:
    """The group's page hashes as bound parameters: the text :page_0, :page_1, ... and the values for it."""
    names = [f"page_{number}" for number in range(len(page_hashes))]
    return ", ".join(f":{name}" for name in names), dict(zip(names, page_hashes, strict=True))


def _bodies(engine: Engine, source: Source, page_hashes: list[str]) -> dict[str, tuple[str, dt.datetime]]:
    """Each of the group's pages, by its hash: its body and when it was first fetched, in one statement."""
    marks, params = _marks(page_hashes)
    found = engine.run("SELECT page_hash, body, fetched_at FROM strata.bronze.api_pages "  # sql-lint: names only
                       f"WHERE source = :source AND page_hash IN ({marks}) ORDER BY fetched_at DESC",
                       {"source": source.key, **params})
    return {page_hash: (body, fetched_at) for page_hash, body, fetched_at in found.rows}  # the first fetch wins


def _held(engine: Engine, names: list[str], page_hashes: list[str]) -> dict[str, list[str]]:
    """The group's pages each table holds rows from already, in one statement for every table: the pages a run
    read before under another transform, and those a run that stopped partway wrote to some tables and not
    others. A Delta DELETE is a commit, so only a table that holds some of the group's pages gets one."""
    marks, params = _marks(page_hashes)
    query = " UNION ALL ".join(  # sql-lint: names only, the transform's TABLES and the group's marks
        f"SELECT DISTINCT {number} AS held_in, page_hash FROM {table} WHERE page_hash IN ({marks})"
        for number, table in enumerate(names))
    held: dict[str, list[str]] = {}
    for number, page_hash in engine.run(query, params).rows:
        held.setdefault(names[int(number)], []).append(page_hash)
    return held


def _write(engine: Engine, source: Source, module, page_hashes: list[str],
           clock: Callable[[], dt.datetime]) -> tuple[int, dt.datetime]:
    """One group of pages: parsed, each table's rows written once, and then the group's records. Returns the rows it
    added and when the group's last page was recorded."""
    first = next(iter(module.TABLES))
    order = [name for name in module.TABLES if name != first] + [first]
    bodies = _bodies(engine, source, page_hashes)
    rows: dict[str, list[tuple]] = {table: [] for table in order}
    for page_hash in page_hashes:
        body, fetched_at = bodies[page_hash]
        fetched_at = fetched_at if fetched_at.tzinfo else fetched_at.replace(tzinfo=dt.UTC)
        parsed = module.parse(json.loads(body), page_hash, fetched_at)
        for table in order:
            rows[table].extend(parsed.get(table, []))
    # A run that stops between two statements leaves the group without its records, so the rerun takes out what the
    # stopped run wrote of it before writing it again, and no table holds a page twice or misses part of it (ticket
    # 43; CLAUDE.md rule 5, a DELETE with a WHERE). The first table is still written last, as the readiness measures
    # count it, and the records after every table (ticket 75).
    held = _held(engine, order, page_hashes)
    added = 0
    for table in order:
        if held.get(table):
            marks, params = _marks(held[table])
            engine.run(f"DELETE FROM {table} WHERE page_hash IN ({marks})", params)  # sql-lint: names only, TABLES
        if rows[table]:
            added += engine.insert_rows(table, module.TABLES[table], rows[table])
    named, numbered = tables(module), version(module)
    records = []
    for page_hash in page_hashes:
        written = clock().astimezone(dt.UTC)
        records.append((source.key, page_hash, named, numbered, written, written.date()))
    engine.insert_rows(SILVER_PAGES, SILVER_PAGES_COLUMNS, records)
    return added, written


def read(engine: Engine, sources: Iterable[Source], clock: Callable[[], dt.datetime] = _now,
         until: dt.datetime | None = None, group: int | None = None) -> Pass:
    """Parse each source's bronze pages that silver has not read with its transform as it is now, in groups of
    `group` pages (config/thresholds.toml, ingestion.silver_group_pages, unless given), oldest first, and record
    each group once its rows are written. With until, the pass stops at the end of the group whose last record is
    written at or after it, and counts the pages left of that source and of the sources after it."""
    size = group or int(load_thresholds().value("ingestion.silver_group_pages"))
    added, stopped_at, waiting = 0, None, []
    for source in sources:
        page_hashes = pending(engine, source)
        done = 0
        if stopped_at is None:
            module = transform(source)
            for start in range(0, len(page_hashes), size):
                part = page_hashes[start:start + size]
                rows, written = _write(engine, source, module, part, clock)
                added, done = added + rows, done + len(part)
                if until is not None and written >= until:
                    stopped_at = written
                    break
        if done < len(page_hashes):
            waiting.append(Waiting(source.key, len(page_hashes) - done, len(page_hashes)))
    return Pass(added, stopped_at, tuple(waiting))


WAITING_MEASURE = "silver_pages_waiting"
NOTE_COLUMNS = ("run_id", "source", "subject", "measure", "kind", "count", "denominator", "as_of", "detail",
                "measured_at", "public_from")


def note_waiting(engine: Engine, run_id: str, passed: Pass, minutes: float) -> int:
    """A data readiness note for each source whose pages a pass stopped at its time left for the next run: the pages
    left, out of those waiting when the pass began. Returns the notes it wrote."""
    when = passed.stopped_at
    day = f"{when:%B} {when.day}, {when.year}"
    notes = [(run_id, found.source, "all", WAITING_MEASURE, "fresh", found.pages, found.pending, when.date(),
              f"I stopped reading bronze pages into silver on {day}, after the night's {minutes:g} minutes for "
              f"silver, so gold and the job's later tasks had time to run. {found.pages:,} of the {found.pending:,} "
              "pages of this source that were waiting are left, and the next night goes on from there.",
              when, when.date()) for found in passed.waiting]
    return engine.insert_rows("strata.ops.data_readiness", NOTE_COLUMNS, notes)


def run(engine: Engine, source: Source, clock: Callable[[], dt.datetime] = _now, group: int | None = None) -> int:
    """One source's pass with no time limit (read). Returns the rows it added."""
    return read(engine, [source], clock, group=group).added
