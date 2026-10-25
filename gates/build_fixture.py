#!/usr/bin/env python3
"""Builds the fixture database, data/out/fixture.duckdb, that the offline tests read.

It builds four things, with no network:

- The strata catalog's schemas and tables, from the table definitions in
  src/strata/lakehouse/tables, the same ones the deploy builds on the workspace.
- The recorded sources listed in data/fixture/sources.toml, into the schema `recorded`:
  `recorded.files` (each file with its source and license line), `recorded.responses`
  (each API response as JSON), `recorded.documents` (each document's published text) and
  `recorded.pages` (the text of each PDF page, numbered from 1). The `recorded` schema is the
  fixture's copy of the sources, not a catalog layer.
- The Procurement Plans of the demo project and of the stress shelf's plan (config/slice.toml) as STEP
  rows. The plan reader (src/strata/lakehouse/plans.py) runs over the recorded plans with the offline
  document source and layout parser, and fills
  bronze, silver.plan_versions, plan_listings, plan_rows, plan_steps, plan_step_delays and
  plan_data_notes, and the ops tables, as ops/plans/run_live.py runs it on the workspace. Ticket 43
  adds it to the nightly job.
- The Data readiness page as data_readiness_for builds it, in strata.ops.readiness_snapshot, written
  once the plan reader, the nightly job and the passage reader have all measured, as the dashboard
  reads it (strata.dashboard.snapshot).
- Bronze, silver, gold and the data readiness measures, made by the nightly job's own tasks
  (strata.lakehouse.nightly.run_locally) with the recorded pages in place of the live APIs, so
  the fixture can never drift from the code that makes the real tables. They run after the plan
  reader, so gold can read the plan rows.
- The proposed lessons and the review queue, by the nightly job's propose_lessons task
  (strata.knowledge.lessons.propose) with the batch model's recorded answers, run again once the
  passage reader has read the documents it proposes from (ticket 29).

The build stops when any table outside the `recorded` schema lacks a public_from DATE column
(ADR 0002).

The tests attach the database as `strata`, so they query strata.recorded.pages and
strata.silver.plan_rows. It builds into a new file and swaps it in, so a failed build
never leaves a half-built database behind. Run it with this command:

    uv run --frozen python gates/build_fixture.py
"""

import datetime as dt
import itertools
import json
import os
import sys
from pathlib import Path

from strata.config import load_slice
from strata.dashboard import snapshot
from strata.fixture import recorded as fmt
from strata.knowledge import assertions, links
from strata.knowledge.lessons import propose
from strata.lakehouse import catalog, nightly, pages, passages, plans
from strata.lakehouse.catalog import CatalogError
from strata.lakehouse.engine import DuckDBEngine, EngineError
from strata.reader.documents import NotFetched

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "fixture"  # the run id the nightly job's pipeline runs and data readiness measures carry
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
DEMO = load_slice().demo_plan.project_id  # the project whose Procurement Plans the fixture holds
# The projects whose Procurement Plans the plan reader reads in the fixture: the demo plan's, then the
# stress shelf's plan's (ticket 18). The other projects' plans are not recorded.
PLAN_PROJECTS = tuple(dict.fromkeys([DEMO, *(item.project_id for item in load_slice().stress_shelf
                                            if item.kind == "large_plan" and item.project_id)]))
# The fixture's runs read pages recorded on October 23, 2026, and take their measures that morning,
# at 05:00 in Washington, when the nightly job starts. Every run of the build takes them at the same
# times, so a page or a test pinned to that day reads the same measures whatever day the gate runs.
RUNS_START = dt.datetime(2026, 10, 23, 9, 0, tzinfo=dt.UTC)


def fixture_clock(start=RUNS_START):
    """A clock that starts at start and moves on one millisecond each time it is read, so the rows the
    runs write keep the order they were written in."""
    ticks = itertools.count()
    return lambda: start + dt.timedelta(milliseconds=next(ticks))


RECORDED_TABLES = """
CREATE SCHEMA recorded;
CREATE TABLE recorded.files (file VARCHAR PRIMARY KEY, source VARCHAR NOT NULL, license VARCHAR NOT NULL,
                             recorded DATE NOT NULL, about VARCHAR, bytes BIGINT NOT NULL);
CREATE TABLE recorded.responses (file VARCHAR PRIMARY KEY, source VARCHAR NOT NULL, response JSON NOT NULL);
CREATE TABLE recorded.documents (document VARCHAR PRIMARY KEY, source VARCHAR NOT NULL, text VARCHAR NOT NULL);
CREATE TABLE recorded.pages (document VARCHAR NOT NULL, pdf_page INTEGER NOT NULL, text VARCHAR NOT NULL,
                             PRIMARY KEY (document, pdf_page));
"""



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
            elif name.endswith(".words.json"):
                continue  # the offline layout parser reads the words from the file itself
            elif name.endswith(".pages.txt"):
                con.executemany("INSERT INTO recorded.pages VALUES (?, ?, ?)",
                                [[source.file, number, text]
                                 for number, text in enumerate(file.body.split(fmt.PAGE_BREAK), 1)])
            else:
                con.execute("INSERT INTO recorded.documents VALUES (?, ?, ?)", [source.file, file.source, file.body])


def build(out=FIXTURE_DB, manifest=None, tables=catalog.TABLES, plans_for=PLAN_PROJECTS):
    """Build the database at out from the table definitions and a loaded manifest (by default,
    sources.toml), then read the Procurement Plans of the projects plans_for names (a project ID or
    several; none when it is None)."""
    manifest = manifest or fmt.load_manifest()
    out.parent.mkdir(parents=True, exist_ok=True)
    building = out.with_name(f"{out.stem}.building{out.suffix}")  # ignored by git like the database itself
    for leftover in (building, building.with_name(building.name + ".wal")):
        leftover.unlink(missing_ok=True)
    clock = fixture_clock()
    try:
        with DuckDBEngine.open(building) as engine:
            catalog.build(engine, tables)  # the catalog's schemas and tables, from the definitions the deploy uses
            load_recorded(engine.connection, manifest)
            for project_id in ((plans_for,) if isinstance(plans_for, str) else plans_for or ()):
                plans.run_on_fixture(engine, project_id, manifest=manifest, clock=clock)
            if tables == catalog.TABLES:  # the lakehouse run needs the real table definitions
                nightly.run_locally(engine, run_id=RUN_ID,
                                    fetch=lambda source, _engine: pages.recorded_pages(source, manifest), clock=clock)
                passages.run_on_fixture(engine, manifest=manifest, run_id=RUN_ID, clock=clock)
                # The nightly job's propose_lessons task again, now that the passages are read (ticket 29):
                # the batch model's recorded answers, the quote check and the review queue.
                propose.run_on_fixture(engine, RUN_ID, clock)
                # Assertions and disagreements, once the passages they rest on are read (ticket 20).
                assertions.run_on_fixture(engine, run_id=RUN_ID, clock=clock)
                # The nightly job's relink task again, now that the passages are read (ticket 22): the edge
                # table, with each contract scored against the paragraphs of its project's reports.
                links.relink(engine, RUN_ID, clock)
                # The dashboard's copy of the Data readiness page, once every reader has measured.
                snapshot.write(engine, RUN_ID, clock)
            catalog.check_public_from(engine, skip=("recorded",))  # every other table, whatever made it
    except (CatalogError, EngineError, NotFetched) as error:  # one sentence, never a traceback
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
