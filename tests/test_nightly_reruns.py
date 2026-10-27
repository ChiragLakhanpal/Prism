"""Rerunning the nightly job (seam 1; ticket 43's criteria 3 and 4).

"Running the same night twice changes nothing" means: after a second run over the same pages and documents,
every table in bronze, silver, gold and strata.ops holds the rows it held, except the run logs, which gain the
second run's own rows (nightly.RUN_LOGS), and the one batch request the fixture's recordings never answer, which
each night sends again because it failed before. "A run forced to fail midway, then rerun, finishes with no
duplicate rows": a run that stops between two silver inserts is repaired under the same run id, as a Databricks
repair run does, and finishes with every page read once.

Each test runs on a writable copy of the fixture database the gate built.
"""

import copy
import datetime as dt
import shutil
from collections import Counter

import pytest
from nightly_helpers import clock

from strata.lakehouse import nightly, pages
from strata.lakehouse.silver import projects as silver_projects
from strata.lakehouse.engine import DuckDBEngine, EngineError

PLAN_ORDER = [task.key for task in nightly.job_tasks()]
UNANSWERED = "33407968/v1"  # P127203's ICR: the recorded batch has no answer for it, so its request fails


@pytest.fixture
def fixture_copy(fixture_db, tmp_path):
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        yield engine


def snapshot(engine) -> dict[str, Counter]:
    """Every table's rows, each as the hash of its text, counted."""
    tables = engine.run("SELECT table_schema, table_name FROM system.information_schema.tables "
                        "WHERE table_catalog = 'strata' AND table_schema IN ('bronze', 'silver', 'gold', 'ops') "
                        "AND table_type = 'BASE TABLE'").rows
    return {f"strata.{schema}.{table}": Counter(row[0] for row in engine.connection.execute(
        f"SELECT md5(CAST(t AS VARCHAR)) FROM strata.{schema}.{table} AS t").fetchall()) for schema, table in tables}


def added(before: dict[str, Counter], after: dict[str, Counter], table: str) -> int:
    return sum((after[table] - before[table]).values())


def latest_measures(engine, run_id):
    return {row[:3]: row[3:] for row in engine.run(
        "SELECT source, subject, measure, count, denominator, as_of FROM strata.ops.data_readiness "
        "WHERE run_id = :run_id", {"run_id": run_id}).rows}


def test_running_the_same_night_twice_changes_nothing(fixture_copy, every_plan_version):
    # The plan reader reads every plan version, as the fixture build did (ticket 108), so this is the same night.
    before = snapshot(fixture_copy)
    first = {row[:3]: row[3:] for row in fixture_copy.run(
        "SELECT source, subject, measure, count, denominator, as_of FROM strata.ops.data_readiness "
        "QUALIFY row_number() OVER (PARTITION BY source, subject, measure ORDER BY measured_at DESC) = 1").rows}

    # The same night: the fixture's run took its measures at 09:00 UTC on October 23, 2026.
    nightly.run_locally(fixture_copy, run_id="again", clock=clock(dt.datetime(2026, 10, 23, 11, tzinfo=dt.UTC)))

    after = snapshot(fixture_copy)
    changed = {table for table in after if after[table] != before[table]}
    assert changed - set(nightly.RUN_LOGS) == {"strata.bronze.lesson_batches"}
    for table in changed:  # nothing a run wrote before is taken away, and the new rows are the second run's own
        assert before[table] - after[table] == Counter()
    retried = fixture_copy.run("SELECT count(*) FROM strata.bronze.lesson_batches WHERE custom_id = :request "
                               "AND recorded_at >= TIMESTAMP '2026-10-23 11:00:00'", {"request": UNANSWERED}).rows[0][0]
    assert added(before, after, "strata.bronze.lesson_batches") == retried > 0
    for table in nightly.RUN_LOGS:
        again = fixture_copy.run(f"SELECT count(*) FROM {table} WHERE run_id = 'again'").rows[0][0]
        assert added(before, after, table) == again
    tasks = dict(fixture_copy.run("SELECT task_key, rows_changed FROM strata.ops.pipeline_runs WHERE run_id = 'again'"
                                  ).rows)
    # Only the tasks that write run logs count rows: propose_lessons its measure and the request it sends again.
    assert {task for task, rows in tasks.items() if rows} == {"propose_lessons", "score", "measure_data_readiness"}
    second = latest_measures(fixture_copy, "again")
    assert second and second == {key: first[key] for key in second}  # the Data readiness page reads the same


def with_a_project_renamed(source, engine):
    """The recorded pages, with one project's page changed since the fixture's run, so silver reads it again."""
    for page in pages.recorded_pages(source):
        if source.key == "projects" and "id=P130164" in page.request:
            body = copy.deepcopy(page.body)
            body["projects"]["P130164"]["project_name"] = "Rajasthan Road Sector Modernization Project, restructured"
            page = pages.Page(page.source, page.request, body, page.fetched_at + dt.timedelta(days=1))
        yield page


class StopsOnce:
    """The fixture's engine, which stops answering the first time a run inserts into one table, as the warehouse
    did mid-run on October 24, 2026."""

    def __init__(self, engine, table):
        self.engine, self.table, self.stopped = engine, table, False

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def insert_rows(self, table, columns, rows, *more, **options):
        if table == self.table and not self.stopped:
            self.stopped = True
            raise EngineError("The SQL warehouse stopped answering.")
        return self.engine.insert_rows(table, columns, rows, *more, **options)


SILVER_PROJECT_TABLES = list(silver_projects.TABLES)  # projects first, then its loans, ISR ratings and sectors


def page_rows(engine, request):
    """How many rows each silver table of the projects source holds from the newest page of a request."""
    page_hash = engine.run("SELECT page_hash FROM strata.bronze.api_pages WHERE request = :request "
                           "ORDER BY fetched_at DESC LIMIT 1", {"request": request}).rows[0][0]
    return {table: engine.run(f"SELECT count(*) FROM {table} WHERE page_hash = :page_hash",
                              {"page_hash": page_hash}).rows[0][0] for table in SILVER_PROJECT_TABLES}


def test_a_run_that_stops_between_two_silver_inserts_is_repaired_with_every_page_read_once(fixture_copy):
    request = "https://search.worldbank.org/api/v3/projects?format=json&id=P130164&fl=*"
    as_recorded = page_rows(fixture_copy, request)
    assert all(as_recorded.values())  # the page gives rows to each of the four tables
    stopping = StopsOnce(fixture_copy, "strata.silver.project_isr_ratings")
    night = clock(dt.datetime(2026, 10, 24, 7, tzinfo=dt.UTC))  # 03:00 in Washington

    with pytest.raises(EngineError, match="stopped answering"):
        nightly.run_locally(stopping, run_id="night-2", fetch=with_a_project_renamed, clock=night)
    repaired = nightly.repair_locally(stopping, "night-2", fetch=with_a_project_renamed, clock=night)

    assert repaired == PLAN_ORDER[1:]
    tries = fixture_copy.run("SELECT task_key, status FROM strata.ops.pipeline_runs WHERE run_id = 'night-2' "
                             "ORDER BY started_at").rows
    assert [row for row in tries if row[0] == "bronze_to_gold"] == [("bronze_to_gold", "failed"),
                                                                    ("bronze_to_gold", "succeeded")]
    assert [task for task, status in tries if status == "succeeded"] == PLAN_ORDER
    assert page_rows(fixture_copy, request) == as_recorded  # the renamed page, read once into every table
    failed = fixture_copy.run("SELECT task_key, check_kind, table_name, found FROM strata.ops.quality_checks "
                              "WHERE run_id = 'night-2' AND NOT passed").rows
    assert list(failed) == []
    for table in SILVER_PROJECT_TABLES:
        assert fixture_copy.run(f"SELECT count(*) FROM (SELECT DISTINCT * FROM {table})").rows[0][0] == \
            fixture_copy.run(f"SELECT count(*) FROM {table}").rows[0][0], f"{table} holds a row twice"
    assert fixture_copy.run("SELECT project_name FROM strata.gold.project WHERE project_id = 'P130164'").rows[0][0] == \
        "Rajasthan Road Sector Modernization Project, restructured"
