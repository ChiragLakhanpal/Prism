"""The silver pass in groups of pages, and the time it may take each night (ticket 85; seam 1).

On the paid workspace's first nightly run (October 26, 2026, run 686994790675456), silver read one bronze page at a
time and, for each of its transform's tables, ran a read, a DELETE with a WHERE and an insert: about 6.3 seconds a
page on the 2X-Small warehouse. bronze_to_gold spent the job's whole 150-minute window on 1,231 of 1,460 pages, so
gold never ran. The pass now reads its pages in groups (config/thresholds.toml, ingestion.silver_group_pages) and
writes each table once a group, and it stops at the end of the group during which its time ran out
(ingestion.silver_minutes), so gold runs on what silver holds and the next night reads the rest.

Most tests here build only the tables silver needs, in a new in-memory database, as tests/test_silver_pages.py does,
and store versions of P130164's recorded projects page in bronze, each with a project name of its own.
"""

import copy
import datetime as dt
import logging
import shutil
from contextlib import contextmanager

import pytest

from strata.config import load_sources, load_thresholds
from strata.lakehouse import bronze, catalog, nightly, pages, silver
from strata.lakehouse.engine import DuckDBEngine, EngineError
from strata.lakehouse.silver import projects

PROJECTS = load_sources()["projects"]
NEEDED = {"strata.bronze.api_pages", "strata.ops.contact_removals", "strata.ops.silver_pages", *projects.TABLES}
P130164 = "https://search.worldbank.org/api/v3/projects?format=json&id=P130164&fl=*"


@contextmanager
def a_database():
    """A new database with the recorded projects pages in bronze and nothing in silver."""
    with DuckDBEngine.open() as engine:
        for schema in ("bronze", "silver", "ops"):
            engine.run(f"CREATE SCHEMA IF NOT EXISTS strata.{schema}")
        for definition in catalog.table_definitions():
            if definition.full_name in NEEDED:
                engine.run(definition.sql)
        bronze.store(engine, PROJECTS, pages.recorded_pages(PROJECTS))
        yield engine


@pytest.fixture
def engine():
    with a_database() as engine:
        yield engine


def versions_of_p130164(count: int):
    """count versions of P130164's recorded page, each renamed, fetched a minute apart: count new pages for bronze."""
    (page,) = [page for page in pages.recorded_pages(PROJECTS) if page.request == P130164]
    for number in range(count):
        body = copy.deepcopy(page.body)
        body["projects"]["P130164"]["project_name"] = f"Rajasthan Road Sector Modernization Project, version {number}"
        yield pages.Page(page.source, page.request, body, page.fetched_at + dt.timedelta(minutes=number + 1))


class Counted:
    """The test's engine, which keeps each statement silver sends it: every run() and every insert_rows() is one,
    as each is one statement on the SQL warehouse and one Delta commit or query in a Databricks job."""

    def __init__(self, engine):
        self.engine, self.statements = engine, []

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def run(self, sql, params=None):
        self.statements.append(sql.split()[0].upper())
        return self.engine.run(sql, params)

    def insert_rows(self, table, columns, rows, *more, **options):
        self.statements.append("INSERT")
        return self.engine.insert_rows(table, columns, rows, *more, **options)


def test_new_pages_cost_fewer_statements_than_one_per_page_per_table_and_no_delete(engine):
    bronze.store(engine, PROJECTS, versions_of_p130164(120))
    new = len(silver.pending(engine, PROJECTS))
    counted = Counted(engine)

    assert silver.run(counted, PROJECTS) > 0
    assert new > 120
    assert len(counted.statements) < new * len(projects.TABLES)
    assert "DELETE" not in counted.statements
    assert silver.pending(engine, PROJECTS) == []


def a_clock(start=dt.datetime(2026, 10, 27, 7, tzinfo=dt.UTC), step=dt.timedelta(milliseconds=1)):
    """A clock that moves on by step each time it is read, as the fixture build's does."""
    ticks = iter(range(10**7))
    return lambda: start + step * next(ticks)


def everything(engine):
    """Every row of each silver table and every record, sorted, so a row held twice, lost or changed shows."""
    return {table: sorted(engine.run(f"SELECT * FROM {table}").rows, key=repr)
            for table in [*projects.TABLES, "strata.ops.silver_pages"]}


def test_a_pass_in_groups_writes_the_same_rows_and_records_as_a_pass_page_by_page(engine):
    """Groups of one page are the pass as it was before ticket 85. The clock moves on each time it is read, so the
    records' times show that each page is still recorded at the time it was before."""
    bronze.store(engine, PROJECTS, versions_of_p130164(20))
    by_page = silver.run(engine, PROJECTS, a_clock(), group=1)
    with a_database() as grouped:
        bronze.store(grouped, PROJECTS, versions_of_p130164(20))
        assert silver.run(grouped, PROJECTS, a_clock(), group=7) == by_page > 0
        assert everything(grouped) == everything(engine)


def test_a_rerun_writes_nothing(engine):
    bronze.store(engine, PROJECTS, versions_of_p130164(60))
    silver.run(engine, PROJECTS)
    before = everything(engine)
    counted = Counted(engine)

    assert silver.run(counted, PROJECTS) == 0
    assert everything(engine) == before
    assert not {"INSERT", "DELETE"} & set(counted.statements)


class StopsOnce:
    """The test's engine, which stops answering at one statement, as the warehouse did mid-run on October 24, 2026:
    the number-th statement that `at` picks, given its SQL text or, for an insert, its table."""

    def __init__(self, engine, at, number):
        self.engine, self.at, self.left = engine, at, number

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def _maybe_stop(self, text):
        if self.left and self.at(text):
            self.left -= 1
            if self.left == 0:
                raise EngineError("The SQL warehouse stopped answering.")

    def run(self, sql, params=None):
        self._maybe_stop(sql)
        return self.engine.run(sql, params)

    def insert_rows(self, table, columns, rows, *more, **options):
        self._maybe_stop(table)
        return self.engine.insert_rows(table, columns, rows, *more, **options)


GROUP = 5
STOPS = {
    # The second group's first statement, the read of its pages: the first group is recorded, the second is not.
    "between-two-groups": lambda text: "strata.bronze.api_pages" in text and "body" in text,
    # The second group's insert into its first table, which is written last, after its four other tables.
    "between-two-statements-of-a-group": lambda text: text == "strata.silver.projects",
    # The second group's records, after every table took its rows.
    "before-a-group-s-records": lambda text: text == "strata.ops.silver_pages",
}


@pytest.mark.parametrize("stop", STOPS)
def test_a_stop_leaves_its_group_pending_and_the_rerun_writes_it_once(engine, stop):
    bronze.store(engine, PROJECTS, versions_of_p130164(3 * GROUP))
    waiting = silver.pending(engine, PROJECTS)

    with pytest.raises(EngineError, match="stopped answering"):
        silver.run(StopsOnce(engine, STOPS[stop], 2), PROJECTS, group=GROUP)

    assert silver.pending(engine, PROJECTS) == waiting[GROUP:]  # the first group is recorded, the second is not
    silver.run(engine, PROJECTS, group=GROUP)
    assert silver.pending(engine, PROJECTS) == []
    with a_database() as fresh:
        bronze.store(fresh, PROJECTS, versions_of_p130164(3 * GROUP))
        silver.run(fresh, PROJECTS, group=GROUP)
        mine, theirs = everything(engine), everything(fresh)
    for table in projects.TABLES:
        assert mine[table] == theirs[table], f"{table} holds a page twice or misses one"
    assert len(mine["strata.ops.silver_pages"]) == len(waiting)  # one record for each page


def project_name(engine, project_id="P130164"):
    return engine.run("SELECT project_name FROM strata.gold.project WHERE project_id = :pid", {"pid": project_id}
                      ).rows[0][0]


def test_silver_s_minutes_stop_the_pass_after_the_current_group_and_gold_runs_on_what_silver_holds(
        fixture_db, tmp_path, caplog):
    """A night with more new pages than silver's minutes allow, as on October 26, 2026, on a copy of the fixture.
    The task reads the clock when it starts, and silver reads it once for each page it records. The fake clock moves
    on so that the first group is recorded inside silver's minutes and the second after them, so the pass stops at
    the end of the second group, gold runs on what silver holds, and the pages left wait for the next night."""
    limits = load_thresholds()
    size, minutes = int(limits.value("ingestion.silver_group_pages")), float(limits.value("ingestion.silver_minutes"))
    count, left = 2 * size + 3, 3
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        bronze.store(engine, PROJECTS, versions_of_p130164(count))
        night = a_clock(step=dt.timedelta(minutes=minutes) / (1.5 * size))
        with caplog.at_level(logging.WARNING, logger="strata.lakehouse.nightly"):
            nightly.run_task(engine, "bronze_to_gold", "night-85", fetch=lambda source, engine: (), clock=night)

        assert engine.run("SELECT status FROM strata.ops.pipeline_runs WHERE run_id = 'night-85'").rows == (
            ("succeeded",),)
        assert len(silver.pending(engine, PROJECTS)) == left
        assert project_name(engine) == f"Rajasthan Road Sector Modernization Project, version {2 * size - 1}"
        assert engine.run("SELECT source, subject, measure, kind, count, denominator FROM strata.ops.data_readiness "
                          "WHERE run_id = 'night-85'").rows == (
            ("projects", "all", "silver_pages_waiting", "fresh", left, count),)
        assert [record.getMessage() for record in caplog.records] == [
            f"Silver stopped after its {minutes:.0f} minutes with {left} pages left for the next night: "
            f"projects {left} of {count}."]

        nightly.run_task(engine, "bronze_to_gold", "night-86", fetch=lambda source, engine: (), clock=a_clock())

        assert silver.pending(engine, PROJECTS) == []
        assert project_name(engine) == f"Rajasthan Road Sector Modernization Project, version {count - 1}"
        assert engine.run("SELECT count(*) FROM strata.ops.data_readiness WHERE run_id = 'night-86' "
                          "AND measure = 'silver_pages_waiting'").rows == ((0,),)
        for table in projects.TABLES:  # each version of the page once in each table, none twice and none missed
            per_page = dict(engine.run(
                f"SELECT page_hash, count(*) AS n FROM {table} WHERE page_hash IN ("
                "SELECT page_hash FROM strata.bronze.api_pages WHERE request = :request) GROUP BY page_hash",
                {"request": P130164}).rows)
            assert len(set(per_page.values())) <= 1 and len(per_page) in (0, count + 1), table
