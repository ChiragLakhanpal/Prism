#!/usr/bin/env python3
"""Builds the fixture database, data/out/fixture.duckdb, that the offline tests read.

It builds three things, with no network:

- The strata catalog's schemas and tables, from the table definitions in
  src/strata/lakehouse/tables, the same ones the deploy builds on the workspace. The build stops
  when any table in those schemas lacks a public_from DATE column (ADR 0002).
- The recorded sources listed in data/fixture/sources.toml, into the schema `recorded`:
  `recorded.files` (each file with its source and license line), `recorded.responses`
  (each API response as JSON), `recorded.documents` (each document's published text) and
  `recorded.pages` (the text of each PDF page, numbered from 1). Ticket 07's lakehouse run
  turns these into bronze, silver and gold. The `recorded` schema is the fixture's copy of
  the sources, not a catalog layer. The public-date check covers bronze, silver, gold and ops,
  which ticket 07 builds from it.
- The placeholder tables. Each CSV file in data/fixture/placeholder becomes a table in the
  schema `placeholder`. Ticket 08 replaces them with plan rows read from the recorded plans.

The tests attach the database as `strata`, so they query strata.recorded.pages and
strata.placeholder.plan_rows. It builds into a new file and swaps it in, so a failed build
never leaves a half-built database behind. Run it with this command:

    uv run --frozen python gates/build_fixture.py
"""

import json
import os
import re
import sys
from pathlib import Path

from strata.fixture import recorded as fmt
from strata.lakehouse import catalog
from strata.lakehouse.catalog import CatalogError
from strata.lakehouse.engine import DuckDBEngine, EngineError

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = ROOT / "data" / "fixture" / "placeholder"
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
TABLE_NAME = re.compile(r"[a-z][a-z0-9_]*")
RECORDED_TABLES = """
CREATE SCHEMA recorded;
CREATE TABLE recorded.files (file VARCHAR PRIMARY KEY, source VARCHAR NOT NULL, license VARCHAR NOT NULL,
                             recorded DATE NOT NULL, about VARCHAR, bytes BIGINT NOT NULL);
CREATE TABLE recorded.responses (file VARCHAR PRIMARY KEY, source VARCHAR NOT NULL, response JSON NOT NULL);
CREATE TABLE recorded.documents (document VARCHAR PRIMARY KEY, source VARCHAR NOT NULL, text VARCHAR NOT NULL);
CREATE TABLE recorded.pages (document VARCHAR NOT NULL, pdf_page INTEGER NOT NULL, text VARCHAR NOT NULL,
                             PRIMARY KEY (document, pdf_page));
"""


def load_placeholder(con, source):
    con.execute("CREATE SCHEMA placeholder")
    for table in sorted(source.glob("*.csv")):
        if not TABLE_NAME.fullmatch(table.stem):
            raise SystemExit(f"The fixture file {table.name} needs a lower-case table name. Use only "
                             "letters, digits and underscores, and start with a letter.")
        con.execute(f"CREATE TABLE placeholder.{table.stem} AS SELECT * FROM read_csv(?, header = true)",
                    [str(table)])


def load_recorded(con, manifest):
    con.execute(RECORDED_TABLES)
    for source in manifest.sources:
        for name in source.files():
            path = manifest.recorded / name
            if not path.exists():
                raise SystemExit(f"The fixture has no file {name}, which {manifest.path.name} lists. Record it "
                                 f"with: uv run python -m strata.fixture.record --only {source.file} --write")
            file = fmt.read(path)
            con.execute("INSERT INTO recorded.files VALUES (?, ?, ?, ?, ?, ?)",
                        [name, file.source, file.license, file.recorded, file.about, path.stat().st_size])
            if source.kind == "json":
                con.execute("INSERT INTO recorded.responses VALUES (?, ?, ?)",
                            [name, file.source, json.dumps(file.body)])
            elif name.endswith(".pages.txt"):
                con.executemany("INSERT INTO recorded.pages VALUES (?, ?, ?)",
                                [[source.file, number, text]
                                 for number, text in enumerate(file.body.split(fmt.PAGE_BREAK), 1)])
            else:
                con.execute("INSERT INTO recorded.documents VALUES (?, ?, ?)", [source.file, file.source, file.body])


def build(out=FIXTURE_DB, source=PLACEHOLDER, manifest=None, tables=catalog.TABLES):
    """Build the database at out from the table definitions, the placeholder folder and a loaded
    manifest (by default, sources.toml)."""
    manifest = manifest or fmt.load_manifest()
    out.parent.mkdir(parents=True, exist_ok=True)
    building = out.with_name(f"{out.stem}.building{out.suffix}")  # ignored by git like the database itself
    for leftover in (building, building.with_name(building.name + ".wal")):
        leftover.unlink(missing_ok=True)
    try:
        with DuckDBEngine.open(building) as engine:
            catalog.build(engine, tables)  # the catalog's schemas and tables, from the definitions the deploy uses
            load_placeholder(engine.connection, source)
            load_recorded(engine.connection, manifest)
            catalog.check_public_from(engine)  # every table in the catalog's schemas, whatever made it
    except (CatalogError, EngineError) as error:  # one sentence, never a traceback
        building.unlink(missing_ok=True)
        raise SystemExit(str(error)) from error
    except BaseException:
        building.unlink(missing_ok=True)
        raise
    os.replace(building, out)
    return out


def main():
    manifest = fmt.load_manifest()
    out = build(manifest=manifest)
    files = manifest.files()
    recorded_mb = sum((manifest.recorded / name).stat().st_size for name in files) / 1_000_000
    print(f"The fixture holds {len(files)} recorded files ({recorded_mb:.1f} MB) from {len(manifest.sources)} "
          f"sources. The fixture database is {out.stat().st_size / 1_000_000:.1f} MB, at {out.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
