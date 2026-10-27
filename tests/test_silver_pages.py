"""What silver wrote from each bronze page (ticket 75; seam 1).

silver.run reads a source's bronze page when strata.ops.silver_pages holds no record of it, or when the page's
newest record names other tables or another version than the source's silver transform has, and writes the
record after the page's rows. So a page is read once, and a transform that gains a table or bumps its VERSION
reads every page of its source once more. Before this, the first table's rows marked a page as read, so the two
tables ticket 21 added to the projects transform held rows only from pages fetched after its deploy, and none for
P130164, whose page bronze already held.

Most tests here build only the tables silver needs, in a new in-memory database, and store the recorded projects
pages in bronze: a fraction of a second, where a whole catalog takes seconds.
"""

import copy
import dataclasses
import datetime as dt
import sys
import types
from collections import Counter
from contextlib import contextmanager

import pytest

from strata.config import load_sources
from strata.lakehouse import bronze, catalog, pages, silver
from strata.lakehouse.engine import DuckDBEngine
from strata.lakehouse.silver import projects

PROJECTS = load_sources()["projects"]
SILVER_PAGES = "strata.ops.silver_pages"
# What silver needs: bronze's pages and the contact counts bronze writes beside them, the projects transform's
# five tables, and the record of what silver wrote from each page; and the view of each request's newest page, which
# bronze.store reads.
NEEDED = {"strata.bronze.api_pages", "strata.bronze.current_pages", "strata.ops.contact_removals", SILVER_PAGES,
          *projects.TABLES}
# The projects transform's tables, sorted and joined with commas, as the record names them.
PROJECT_TABLES = ("strata.silver.project_environment,strata.silver.project_isr_ratings,strata.silver.project_loans,"
                  "strata.silver.project_sectors,strata.silver.projects")
SECTORS = "strata.silver.project_sectors"
ENVIRONMENT = "strata.silver.project_environment"
# P130164's sectors (data/fixture/recorded/api/projects/P130164.json; tests/test_project_hub.py).
P130164_SECTORS = [("TF", 3.0), ("TI", 97.0)]


@contextmanager
def a_database():
    """A new database with the recorded projects pages in bronze and nothing in silver."""
    with DuckDBEngine.open() as engine:
        for schema in ("bronze", "silver", "ops"):
            engine.run(f"CREATE SCHEMA IF NOT EXISTS strata.{schema}")
        for definition in catalog.table_definitions() + catalog.view_definitions():
            if definition.full_name in NEEDED:
                engine.run(definition.sql)
        bronze.store(engine, PROJECTS, pages.recorded_pages(PROJECTS))
        yield engine


@pytest.fixture
def engine():
    with a_database() as engine:
        yield engine


def column(engine, sql, **params):
    return [row[0] for row in engine.run(sql, params).rows]


def bronze_pages(engine):
    return set(column(engine, "SELECT page_hash FROM strata.bronze.api_pages WHERE source = 'projects'"))


def records(engine):
    """Each record silver wrote for the projects source, as (page_hash, tables, version), counted."""
    return Counter(engine.run(f"SELECT page_hash, tables, version FROM {SILVER_PAGES} WHERE source = 'projects'"
                              ).rows)


def rows(engine, tables=tuple(projects.TABLES)):
    """Every row of each table, counted, so a row held twice or lost shows."""
    return {table: Counter(engine.run(f"SELECT * FROM {table}").rows) for table in tables}


def sectors_of(engine, project_id):
    return sorted((code, float(share)) for code, share in engine.run(
        f"SELECT sector_code, share_percent FROM {SECTORS} WHERE project_id = :pid", {"pid": project_id}).rows)


def like_projects(monkeypatch, name, leave_out=(), version=None):
    """The projects source with a test transform, strata.lakehouse.silver.<name>, that reads pages as the projects
    transform does, without the tables in leave_out, and with VERSION set when version is given."""
    module = types.ModuleType(f"strata.lakehouse.silver.{name}")
    module.TABLES = {table: columns for table, columns in projects.TABLES.items() if table not in leave_out}
    module.RECORD_KEY = projects.RECORD_KEY
    module.parse = projects.parse
    if version is not None:
        module.VERSION = version
    monkeypatch.setitem(sys.modules, module.__name__, module)
    return dataclasses.replace(PROJECTS, silver_transform=name)


def test_a_run_records_every_page_it_read_and_reads_none_of_them_again(engine):
    first = silver.run(engine, PROJECTS)

    assert first > 0
    assert records(engine) == Counter({(page, PROJECT_TABLES, 1): 1 for page in bronze_pages(engine)})
    assert silver.pending(engine, PROJECTS) == []
    assert silver.run(engine, PROJECTS) == 0  # every table holds every page: no page is read again
    assert sum(records(engine).values()) == len(bronze_pages(engine))


def test_a_page_whose_rows_one_table_lost_is_still_not_read_again(engine):
    """The record is the mark, not the rows."""
    silver.run(engine, PROJECTS)
    page = column(engine, "SELECT page_hash FROM strata.silver.projects WHERE project_id = 'P130164'")[0]
    engine.run(f"DELETE FROM {SECTORS} WHERE page_hash = :page", {"page": page})

    assert silver.pending(engine, PROJECTS) == []
    assert silver.run(engine, PROJECTS) == 0
    assert sectors_of(engine, "P130164") == []


@pytest.mark.parametrize("before", [(SECTORS,), (SECTORS, ENVIRONMENT)], ids=["one-more-table", "ticket-21-s-two"])
def test_a_transform_that_gains_a_table_reads_every_page_of_its_source_again(engine, monkeypatch, before):
    """As on the workspace before this ticket: bronze held P130164's page when ticket 21 gave the projects
    transform its new tables. The next run fills them from that page, and every table holds what a run with
    today's transform from the start holds."""
    silver.run(engine, like_projects(monkeypatch, "projects_before_ticket_21", leave_out=before))
    kept = [table for table in projects.TABLES if table not in before]
    first = rows(engine, kept)
    assert sectors_of(engine, "P130164") == []

    assert set(silver.pending(engine, PROJECTS)) == bronze_pages(engine)
    silver.run(engine, PROJECTS)

    assert sectors_of(engine, "P130164") == P130164_SECTORS
    assert rows(engine, kept) == first
    with a_database() as fresh:
        silver.run(fresh, PROJECTS)
        assert rows(engine) == rows(fresh)
    assert silver.pending(engine, PROJECTS) == []


def test_a_bumped_version_reads_every_page_of_its_source_again_and_the_rows_match_the_first_run_s(engine,
                                                                                                    monkeypatch):
    first = silver.run(engine, PROJECTS)
    before = rows(engine)
    bumped = like_projects(monkeypatch, "projects_version_2", version=2)

    assert set(silver.pending(engine, bumped)) == bronze_pages(engine)
    assert silver.run(engine, bumped) == first
    assert rows(engine) == before
    assert records(engine) == Counter({(page, PROJECT_TABLES, number): 1
                                       for page in bronze_pages(engine) for number in (1, 2)})
    assert silver.run(engine, bumped) == 0


def test_a_later_run_reads_only_the_pages_bronze_gained(engine):
    silver.run(engine, PROJECTS)
    held = bronze_pages(engine)
    old = column(engine, "SELECT page_hash FROM strata.silver.projects WHERE project_id = 'P130164'")[0]

    def renamed():
        for page in pages.recorded_pages(PROJECTS):
            if "id=P130164" in page.request:
                body = copy.deepcopy(page.body)
                body["projects"]["P130164"]["project_name"] = "Rajasthan Road Sector Modernization Project, restructured"
                yield pages.Page(page.source, page.request, body, page.fetched_at + dt.timedelta(days=1))

    bronze.store(engine, PROJECTS, renamed())
    (new,) = bronze_pages(engine) - held

    assert silver.pending(engine, PROJECTS) == [new]
    old_rows = sum(column(engine, f"SELECT count(*) FROM {table} WHERE page_hash = :page", page=old)[0]
                   for table in projects.TABLES)
    assert silver.run(engine, PROJECTS) == old_rows
    assert sectors_of(engine, "P130164") == sorted(P130164_SECTORS * 2)  # the old page's and the new page's


def test_the_pending_query_joins_the_record_once_and_reads_no_silver_table():
    assert silver.PENDING.count(SILVER_PAGES) == 1
    assert "strata.silver." not in silver.PENDING
    assert "NOT EXISTS" not in silver.PENDING.upper()


def test_the_fixture_s_run_recorded_every_page_of_every_source_once(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        for source in (source for source in load_sources().values() if source.paged):
            held = column(engine, "SELECT page_hash FROM strata.bronze.api_pages WHERE source = :source",
                          source=source.key)
            found = engine.run(f"SELECT page_hash, tables, version FROM {SILVER_PAGES} WHERE source = :source",
                               {"source": source.key}).rows
            named = PROJECT_TABLES if source.key == "projects" else silver.tables(silver.transform(source))
            numbered = silver.version(silver.transform(source))  # 1, or the VERSION a transform sets (notices: 2)
            assert held, source.key
            assert Counter(found) == Counter({(page, named, numbered): 1 for page in held}), source.key
