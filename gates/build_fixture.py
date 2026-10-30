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
  rows. The plan reader (src/strata/lakehouse/plans.py) runs over every recorded plan, where the nightly
  job reads only each project's newest (ingestion.plan_versions), with the offline
  document source and layout parser, and fills
  bronze, silver.plan_versions, plan_listings, plan_rows, plan_steps, plan_step_delays and
  plan_data_notes, and the ops tables, as the nightly job's parse_and_embed task runs it on the
  workspace (strata.lakehouse.readers).
- The Data readiness page as data_readiness_for builds it, in strata.ops.readiness_snapshot, written
  once the plan reader, the nightly job and the passage reader have all measured, as the dashboard
  reads it (strata.dashboard.snapshot).
- Bronze, silver, gold and the data readiness measures, made by the nightly job's own tasks
  (strata.lakehouse.nightly.run_locally) with the recorded pages in place of the live APIs, so
  the fixture can never drift from the code that makes the real tables. They run after the plan
  reader, so gold can read the plan rows. Then the plan rows are written again from bronze
  (strata.lakehouse.plans.rewrite), with silver's notices as the repair's dictionary, and gold syncs
  them (ticket 131).
- The proposed lessons and the review queue, by the nightly job's propose_lessons task
  (strata.knowledge.lessons.propose) with the batch model's recorded answers, run again once the
  passage reader has read the documents it proposes from (ticket 29).
- The labeled set retrieval is measured on, with each query set's size, by the weekly retrieval run
  (strata.knowledge.retrieval.weekly), once the passages are read (ticket 32).

The build stops when any table outside the `recorded` schema lacks a public_from DATE column
(ADR 0002).

The tests attach the database as `strata`, so they query strata.recorded.pages and
strata.silver.plan_rows. It builds into a new file and swaps it in, so a failed build
never leaves a half-built database behind. Run it with this command:

    uv run --frozen python gates/build_fixture.py

A run whose inputs have not changed since the last build keeps the database as it is, in about a
second instead of 15 to 30 (ticket 119). The build writes the hash of every file and folder it read
beside the database, in data/out/fixture.inputs.json, and gates/fixture_cache.py explains the key.
Delete that file to build the database again anyway.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"

if __name__ == "__main__":
    # Before the imports below, which read config files: the cache ends the run here when nothing the
    # last build read has changed, and otherwise records every file the build reads from here on.
    import fixture_cache

    CACHE = fixture_cache.start(FIXTURE_DB, ROOT)

import datetime as dt
import itertools
import json
import logging
import os

from strata.config import load_slice, load_thresholds
from strata.dashboard import snapshot
from strata.fixture import recorded as fmt
from strata.knowledge import assertions, links
from strata.knowledge.lessons import propose
from strata.knowledge.retrieval import weekly
from strata.lakehouse import catalog, gold, nightly, pages, passages, plans, readers
from strata.lakehouse.catalog import CatalogError
from strata.lakehouse.engine import DuckDBEngine, EngineError
from strata.reader.documents import NotFetched

RUN_ID = "fixture"  # the run id the nightly job's pipeline runs and data readiness measures carry
DEMO = load_slice().demo_plan.project_id  # the project whose Procurement Plans the fixture holds
# The projects whose Procurement Plans the plan reader reads in the fixture: the demo plan's, then the
# stress shelf's plan's (ticket 18). The other projects' plans are not recorded. The nightly job's
# parse_and_embed reads the same ones over the recorded fixture (strata.lakehouse.readers).
PLAN_PROJECTS = readers.fixture_plan_projects()
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
    projects = (plans_for,) if isinstance(plans_for, str) else tuple(plans_for or ())
    out.parent.mkdir(parents=True, exist_ok=True)
    building = out.with_name(f"{out.stem}.building{out.suffix}")  # ignored by git like the database itself
    for leftover in (building, building.with_name(building.name + ".wal")):
        leftover.unlink(missing_ok=True)
    clock = fixture_clock()
    try:
        with DuckDBEngine.open(building) as engine:
            catalog.build(engine, tables)  # the catalog's schemas and tables, from the definitions the deploy uses
            load_recorded(engine.connection, manifest)
            # Every recorded plan, though the nightly job reads only each project's newest (config/thresholds.toml,
            # ingestion.plan_versions; ticket 108): the tests compare P156634's versions, first listings and delays.
            every = plans.with_plan_versions(load_thresholds(), plans.EVERY_VERSION)
            for project_id in projects:
                plans.run_on_fixture(engine, project_id, manifest=manifest, clock=clock, thresholds=every)
            if tables == catalog.TABLES:  # the lakehouse run needs the real table definitions
                # The job's own parse_and_embed reads no documents here: the plan reader ran above, so gold's
                # packages hold the plan rows from the first sync, and the passage reader runs below, as before.
                nightly.run_locally(engine, run_id=RUN_ID,
                                    fetch=lambda source, _engine: pages.recorded_pages(source, manifest), clock=clock,
                                    readers_for=nightly.no_documents)
                # The plan rows written again now that silver.notices holds the projects' notices, as on the
                # workspace, where bronze_to_gold runs before the plan reader: the repair takes the notices as its
                # dictionary (strata.reader.repair; ticket 131). Gold syncs the rows that changed.
                for project_id in projects:
                    plans.rewrite(engine, project_id, thresholds=every)
                gold.build(engine)
                passages.run_on_fixture(engine, manifest=manifest, run_id=RUN_ID, clock=clock)
                # The nightly job's propose_lessons task again, now that the passages are read (ticket 29):
                # the batch model's recorded answers, the quote check and the review queue.
                propose.run_on_fixture(engine, RUN_ID, clock)
                # Assertions and disagreements, once the passages they rest on are read (ticket 20).
                assertions.run_on_fixture(engine, run_id=RUN_ID, clock=clock)
                # The nightly job's relink task again, now that the passages are read (ticket 22): the edge
                # table, with each contract scored against the paragraphs of its project's reports.
                links.relink(engine, RUN_ID, clock)
                # The weekly retrieval run, once the passages are read (ticket 32): the labeled set, with
                # each query set's size, and the loop's measures.
                weekly.run(engine, now=clock)
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


def main(cache):
    # The fixture's document lists name many documents it never recorded. The readers skip each one with its reason
    # in strata.ops.skipped_documents and a warning in the log (ticket 72); the build counts them in one line instead.
    logging.getLogger("strata.lakehouse.plans").setLevel(logging.ERROR)
    manifest = fmt.load_manifest()
    out = build(manifest=manifest)
    cache.write()  # once the new database is in place, so a failed build leaves no key that matches
    files = manifest.files()
    recorded_mb = sum((manifest.recorded / name).stat().st_size for name in files) / 1_000_000
    with DuckDBEngine.open(out, read_only=True) as engine:
        skipped = engine.run("SELECT count(DISTINCT document_id) AS n FROM strata.ops.skipped_documents").rows[0][0]
    print(f"The fixture holds {len(files)} recorded files ({recorded_mb:.1f} MB) from {len(manifest.sources)} "
          f"sources. The fixture database is {out.stat().st_size / 1_000_000:.1f} MB, at {out.relative_to(ROOT)}. "
          f"The readers skipped {skipped} listed documents that the fixture does not record "
          "(strata.ops.skipped_documents).")
    return 0


if __name__ == "__main__":
    sys.exit(main(CACHE))
