#!/usr/bin/env python3
"""Builds the fixture database, data/out/fixture.duckdb, that the offline tests read.

For now it loads the placeholder tables. Each CSV file in data/fixture/placeholder becomes a
table in the schema `placeholder` of the fixture database. The tests attach the database as
`strata`, so they query plan_rows.csv as strata.placeholder.plan_rows. Ticket 05 replaces
this with the lakehouse run over recorded sources. It builds into a new file and swaps it
in, so a failed build never leaves a half-built database behind.

Run it with this command:

    uv run --frozen python gates/build_fixture.py
"""

import os
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = ROOT / "data" / "fixture" / "placeholder"
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
TABLE_NAME = re.compile(r"[a-z][a-z0-9_]*")


def build(out=FIXTURE_DB, source=PLACEHOLDER):
    out.parent.mkdir(parents=True, exist_ok=True)
    building = out.with_name(f"{out.stem}.building{out.suffix}")  # ignored by git like the database itself
    for leftover in (building, building.with_name(building.name + ".wal")):
        leftover.unlink(missing_ok=True)
    with duckdb.connect(str(building)) as con:
        con.execute("CREATE SCHEMA placeholder")
        for table in sorted(source.glob("*.csv")):
            if not TABLE_NAME.fullmatch(table.stem):
                raise SystemExit(f"The fixture file {table.name} needs a lower-case table name. Use only "
                                 "letters, digits and underscores, and start with a letter.")
            con.execute(f"CREATE TABLE placeholder.{table.stem} AS SELECT * FROM read_csv(?, header = true)",
                        [str(table)])
    os.replace(building, out)
    return out


def main():
    out = build()
    print(f"The fixture database is {out.stat().st_size / 1_000_000:.1f} MB, at {out.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
