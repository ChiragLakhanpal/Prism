"""Every page answers in under two seconds on the workspace (ticket 125), proved on the fixture.

On October 29, 2026 the App's pages took one to five seconds and more: each statement cost the SQL warehouse's
statements API about two seconds, and a page ran its statements one after another. Three things fix it, and each is
tested here at the App's routes:

1. A page's reads go to the warehouse as one batch (src/strata/lakehouse/engine.py, read_together and run_many), so
   the Summary, the Timeline, a project's Packages and a package's header each cost one round trip.
2. A page's answer is kept in the App's memory for its as-of day and the viewer's role (the view the request is bound
   to), for app.page_cache_seconds and at most app.page_cache_entries pages (config/thresholds.toml), and the browser
   is told to keep it as long (Cache-Control), so the second view of a page reads nothing.
3. The demo's cases (config/demo.toml) are read into that memory when the App starts and every hour after, as the App
   itself, so a presenter never meets a cold page.

The live timings are the orchestrator's workspace step (the ticket's report).
"""

import asyncio
import datetime as dt
import json
import logging
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.config import Demo, load_demo, load_slice, load_thresholds
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine, EngineError, PermissionDenied, run_many
from strata.server.app import create_app
from strata.server.page_cache import PageCache
from strata.server.settings import app_from_env
from strata.server.warm import Warm
from test_app_from_env import fake_workspace

ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
       "X-Forwarded-Access-Token": "not-a-real-key"}
DAY = "asof=2026-10-23"


def get(app, path, headers=ANA):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=headers)
    return asyncio.run(go())


class Counted:
    """The fixture's engine, counting each round trip a request makes: each batch, with its statements, and each
    statement run alone."""

    def __init__(self, engine, trips: list):
        self.engine, self.trips = engine, trips

    def run(self, sql, params=None):
        self.trips.append(("alone", sql))
        return self.engine.run(sql, params)

    def run_many(self, statements, return_exceptions=False):
        self.trips.append(("batch", tuple(sql for sql, _ in statements)))
        return run_many(self.engine, statements, return_exceptions=return_exceptions)

    def __getattr__(self, name):
        return getattr(self.engine, name)


class FailsOn:
    """The fixture's engine, except that a statement naming `table` fails as the warehouse fails it: EngineError, or
    PermissionDenied when a grant is missing."""

    def __init__(self, engine, table: str, error: type[EngineError]):
        self.engine, self.table, self.error = engine, table, error

    def run(self, sql, params=None):
        if self.table in sql:
            raise self.error(f"The warehouse did not run the statement. Its state was FAILED: {self.table}")
        return self.engine.run(sql, params)


@pytest.fixture
def trips():
    return []


@pytest.fixture
def counted_reads(fixture_db, trips):
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield Counted(engine, trips)
    return engine_for


@pytest.mark.parametrize("path", [
    f"/api/projects/P130164/summary?{DAY}",
    f"/api/projects/P156634/summary?{DAY}",
    "/api/projects/P130164/timeline",
    f"/api/projects/P156634/timeline?{DAY}",
    f"/api/projects/P156634/timeline?{DAY}&view=public",
    f"/api/projects/P156634/packages?{DAY}",
    f"/api/packages/KE-NWWDA-541055-CW-RFB?{DAY}",
], ids=["summary-p130164", "summary-p156634", "timeline-p130164", "timeline-p156634", "timeline-public",
        "packages-p156634", "package-ke-nwwda-541055"])
def test_a_page_s_warehouse_reads_go_as_one_batch(counted_reads, trips, path):
    response = get(create_app(engine_for=counted_reads), path)

    assert response.status_code == 200
    assert [kind for kind, _ in trips] == ["batch"], trips
    assert_reads_no_masked_or_filtered_table(trips)


def assert_reads_no_masked_or_filtered_table(trips):
    """A kept page is served to everyone in the viewer's role, and the warm reads it as the App, which no mask or row
    filter limits (src/strata/lakehouse/masks.py), so a page in PAGES reads none of those tables."""
    from strata.lakehouse.masks import FILTERED, MASKED

    read = "\n".join(sql for _, sent in trips for sql in ((sent,) if isinstance(sent, str) else sent))
    assert read and not [table for table in {*FILTERED, *MASKED} if table in read]


@pytest.mark.parametrize("path, batches", [
    (f"/api/projects/P156634?{DAY}", 2), (f"/api/projects/P156634?{DAY}&view=public", 2),
    (f"/api/projects/P130164?{DAY}", 1),  # no Procurement Plan, so no agency to read more about
])
def test_a_project_s_header_reads_in_two_batches_since_the_second_needs_the_agencies_the_first_found(
        counted_reads, trips, path, batches):
    response = get(create_app(engine_for=counted_reads), path)

    assert response.status_code == 200
    assert [kind for kind, _ in trips] == ["batch"] * batches, trips
    assert_reads_no_masked_or_filtered_table(trips)


@pytest.fixture
def failing_reads(fixture_db, trips):
    def on(table: str, error: type[EngineError]):
        @contextmanager
        def engine_for(_viewer):
            with DuckDBEngine.open(fixture_db, read_only=True) as engine:
                yield Counted(FailsOn(engine, table, error), trips)
        return engine_for
    return on


# What build/strata's Timeline answered for the showcase when get_disagreements did not: the marks, with no bands and
# no dashed lines (tests/record_timeline_api.py, FAILED).
FAILED_TIMELINE = Path(__file__).parent / "fixtures" / "api" / "timeline-p130164-failed.json"


@pytest.mark.parametrize("table, error", [("strata.gold.disagreement", EngineError),
                                          ("strata.ops.assertion_rejections", PermissionDenied)],
                         ids=["engine-error", "permission"])
def test_a_failed_disagreement_read_in_the_batch_still_draws_the_timeline_as_it_did_before_the_batch(
        failing_reads, trips, table, error):
    app = create_app(engine_for=failing_reads(table, error), today=lambda: TODAY)

    response = get(app, "/api/projects/P130164/timeline")

    assert response.status_code == 200, response.text
    assert response.json()["disagreements"]["status"] == "failed"
    assert response.json() == json.loads(FAILED_TIMELINE.read_text())
    assert [kind for kind, _ in trips] == ["batch"], trips


class Clock:
    """A fake clock in seconds, which a test moves on by hand."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def kept_app(counted_reads, clock):
    return create_app(engine_for=counted_reads, page_cache=PageCache(seconds=600, entries=50, clock=clock))


PAGES = [f"/api/projects/P130164/summary?{DAY}", f"/api/projects/P156634/timeline?{DAY}",
         f"/api/projects/P156634/packages?{DAY}", f"/api/packages/KE-NWWDA-541055-CW-RFB?{DAY}",
         f"/api/projects/P156634?{DAY}"]


@pytest.mark.parametrize("path", PAGES, ids=["summary", "timeline", "packages", "package", "project"])
def test_a_page_read_again_within_the_window_reads_nothing_and_the_browser_keeps_it_as_long(kept_app, trips, clock,
                                                                                          path):
    first = get(kept_app, path)
    read = len(trips)
    clock.now += 599
    again = get(kept_app, path)

    assert first.status_code == again.status_code == 200
    assert read > 0 and len(trips) == read  # the second view issued no warehouse call
    assert again.json() == first.json()
    if "/summary" in path or "/timeline" in path or "/packages" in path:
        assert first.headers["cache-control"] == "private, max-age=600"
        assert again.headers["cache-control"] == "private, max-age=1"
    else:  # the browser asks again for a project's header, which a saved baseline changes
        assert first.headers["cache-control"] == again.headers["cache-control"] == "private, max-age=0"


def test_a_page_kept_answers_as_the_page_did_before_it_was_kept(counted_reads, kept_app):
    plain = create_app(engine_for=counted_reads)

    for path in PAGES:
        assert get(kept_app, path).json() == get(plain, path).json() == get(kept_app, path).json(), path


def test_a_page_read_past_a_failed_read_is_not_kept_so_the_next_view_reads_it_again(failing_reads, trips, clock):
    # The Timeline with its disagreements failed says it could not read them "just now", so the App does not keep it
    # for its window, and the browser is not told to keep it either.
    app = create_app(engine_for=failing_reads("strata.gold.disagreement", EngineError),
                     page_cache=PageCache(seconds=600, entries=50, clock=clock), today=lambda: TODAY)

    for _ in range(2):
        response = get(app, "/api/projects/P130164/timeline")
        assert response.json()["disagreements"]["status"] == "failed"
        assert "cache-control" not in response.headers
    assert [kind for kind, _ in trips] == ["batch", "batch"], trips


def test_another_as_of_date_another_role_or_a_page_past_its_window_is_read_again(kept_app, trips, clock):
    path = "/api/projects/P156634/summary"
    get(kept_app, f"{path}?{DAY}")

    def reads(address):
        before = len(trips)
        assert get(kept_app, address).status_code == 200
        return len(trips) - before

    assert reads(f"{path}?{DAY}") == 0
    assert reads(f"{path}?asof=2026-10-22") == 1  # another as-of date
    assert reads(f"{path}?{DAY}&view=public") == 1  # another role: the public view
    assert reads(f"{path}?{DAY}&view=public") == 0
    clock.now += 601
    assert reads(f"{path}?{DAY}") == 1  # past app.page_cache_seconds


def test_the_app_keeps_at_most_its_number_of_pages_and_lets_the_oldest_go_first(counted_reads, trips, clock):
    app = create_app(engine_for=counted_reads, page_cache=PageCache(seconds=600, entries=2, clock=clock))
    first, second, third = PAGES[:3]
    for path in (first, second, first, third):  # reading the first again makes the second the oldest
        get(app, path)
    trips.clear()

    get(app, first)
    get(app, third)
    assert trips == []
    get(app, second)
    assert trips != []


def test_a_search_of_a_project_s_packages_is_read_but_not_kept_so_searches_push_no_page_out(counted_reads, trips,
                                                                                           clock):
    app = create_app(engine_for=counted_reads, page_cache=PageCache(seconds=600, entries=1, clock=clock))
    packages = f"/api/projects/P156634/packages?{DAY}"
    get(app, packages)

    search = get(app, f"{packages}&q=water")
    assert search.status_code == 200 and "cache-control" not in search.headers
    trips.clear()
    get(app, packages)
    assert trips == []  # the one page the App keeps is still the plain Packages


def test_a_viewer_with_no_token_and_an_answer_that_is_no_page_are_never_kept(kept_app, trips):
    path = f"/api/projects/P156634/summary?{DAY}"
    get(kept_app, path)
    trips.clear()

    assert get(kept_app, path, headers={}).status_code == 200  # the fixture reads for anyone; the workspace refuses
    assert trips != []
    trips.clear()
    for _ in range(2):
        missing = get(kept_app, f"/api/projects/P999999/summary?{DAY}")
        assert missing.status_code == 404 and "cache-control" not in missing.headers
    assert len(trips) == 2


def test_saving_or_removing_a_baseline_lets_the_project_s_header_go_since_it_shows_the_baseline(kept_app, trips):
    path, summary = f"/api/projects/P156634?{DAY}", f"/api/projects/P156634/summary?{DAY}"
    get(kept_app, path)
    get(kept_app, summary)

    async def change(method):
        transport = httpx.ASGITransport(app=kept_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, "/api/projects/P156634/procurement/northern-water-works-development-"
                                        "agency/baseline", headers=ANA, json={"plan_date": "2026-10-09"})

    for method in ("PUT", "DELETE"):
        asyncio.run(change(method))  # the fixture is read-only, so the write fails; the kept header goes all the same
        trips.clear()
        get(kept_app, summary)
        assert trips == [], method  # the Summary shows no baseline, so it stays kept
        get(kept_app, path)
        assert trips != [], method


def test_a_header_read_while_a_baseline_was_saved_is_sent_but_not_kept(counted_reads, trips, clock):
    # The read began before the save and may hold the old baseline, so the next view reads the header again.
    cache = PageCache(seconds=600, entries=50, clock=clock)

    @contextmanager
    def engine_for(viewer):
        with counted_reads(viewer) as engine:
            if not trips:  # the first read: a baseline is saved while it runs
                cache.drop(lambda key: key.page == "project")
            yield engine

    app = create_app(engine_for=engine_for, page_cache=cache)
    path = f"/api/projects/P156634?{DAY}"
    assert get(app, path).status_code == 200
    read = len(trips)

    assert get(app, path).status_code == 200
    assert len(trips) > read


TODAY = dt.date(2026, 10, 23)
DEMO = Demo(projects=("P156634",), packages=("KE-NWWDA-541055-CW-RFB",))
# The demo's pages as a person opens them: no ?asof=, so as of today, in their own view.
DEMO_PAGES = ["/api/projects/P156634", "/api/projects/P156634/summary", "/api/projects/P156634/timeline",
              "/api/projects/P156634/packages", "/api/packages/KE-NWWDA-541055-CW-RFB"]


def the_app_itself():
    return Viewer(name="Prism", user_id="strata-app", token="not-a-real-key")


@pytest.fixture
def warmed(counted_reads, clock, request):
    """An app whose warm reads the demo's pages as the App itself, by the fake clock, and a nightly job whose end time
    the test sets. A test marked demo_pages="package" warms the demo package alone, to stay quick."""
    nightly = {"finished": "2026-10-23T09:57:00Z"}
    demo = Demo((), DEMO.packages) if getattr(request, "param", None) == "package" else DEMO
    warm = Warm(demo, the_app_itself, every_seconds=3600, clock=clock, finished=lambda engine: nightly["finished"])
    app = create_app(engine_for=counted_reads, page_cache=PageCache(seconds=7200, entries=50, clock=clock),
                     warm=warm, today=lambda: TODAY)
    return app, warm, nightly


def started(app, warm):
    """Start the app as the server does and stop it once its first warm has run."""
    async def run():
        async with app.router.lifespan_context(app):
            await asyncio.to_thread(warm.ran.wait, 10)
    asyncio.run(run())


def test_the_demo_s_pages_are_read_as_the_app_when_it_starts_so_the_first_view_reads_nothing(warmed, trips):
    app, warm, _ = warmed

    started(app, warm)
    read = len(trips)
    answers = [get(app, path) for path in DEMO_PAGES]

    assert read >= len(DEMO_PAGES)
    assert [answer.status_code for answer in answers] == [200] * len(DEMO_PAGES)
    assert len(trips) == read  # every demo page was kept already


@pytest.mark.parametrize("warmed", ["package"], indirect=True)
def test_the_demo_s_pages_are_read_again_each_hour_and_not_before(warmed, trips, clock):
    app, warm, _ = warmed
    assert warm.tick() is True
    first = len(trips)

    clock.now += 3599
    assert warm.tick() is False
    assert len(trips) == first
    clock.now += 1
    assert warm.tick() is True
    assert len(trips) == 2 * first  # each page read again
    clock.now += 7199  # two hours after the first warm, the page it kept would have gone; the second kept it
    trips.clear()
    get(app, DEMO_PAGES[-1])
    assert trips == []


@pytest.mark.parametrize("warmed", ["package"], indirect=True)
def test_every_kept_page_goes_once_the_nightly_job_has_finished_again(warmed, trips, clock):
    app, warm, nightly = warmed
    warm.tick()
    elsewhere = f"/api/projects/P130164/summary?{DAY}"  # a page no warm reads
    get(app, elsewhere)
    clock.now += 3600
    warm.tick()
    trips.clear()
    get(app, elsewhere)
    assert trips == []  # the nightly has not run again, so the page stays

    nightly["finished"] = "2026-10-24T09:57:00Z"
    clock.now += 3600
    warm.tick()
    trips.clear()
    get(app, elsewhere)
    assert trips != []


def test_the_warm_reads_when_the_nightly_job_last_finished_from_its_run_log(fixture_db):
    # The warm's own SQL, run on an engine, not a stand-in: a wrong name would show only on the workspace.
    from strata.lakehouse import catalog
    from strata.server.viewer_sql import nightly_finished

    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        finished = nightly_finished(engine)
    assert finished and dt.datetime.fromisoformat(finished).tzinfo is not None
    with DuckDBEngine.open() as empty:  # before any run, an empty strata.ops.pipeline_runs
        empty.run("CREATE SCHEMA IF NOT EXISTS strata.ops")
        (runs,) = [table for table in catalog.table_definitions() if table.full_name == "strata.ops.pipeline_runs"]
        empty.run(runs.sql)
        assert nightly_finished(empty) is None


def test_the_warm_counts_only_the_pages_it_kept(clock, caplog):
    # A Timeline read past a failed read answers 200 but is not kept, so the log the live record reads does not count
    # it as read ahead.
    cache = PageCache(seconds=7200, entries=50, clock=clock)

    def read_page(key, viewer):
        if key.page != "timeline":
            cache.keep(key, {"page": key.page})
        return {"page": key.page}

    warm = Warm(Demo(("P130164",), ()), the_app_itself, every_seconds=3600, clock=clock, finished=lambda engine: None)
    warm.bind(read_page, lambda viewer, read: None, cache, lambda: TODAY)
    with caplog.at_level(logging.INFO, logger="strata.server.warm"):
        assert warm.tick()

    assert "I read 3 of the demo's 4 pages ahead" in caplog.text
    assert "did not keep it" in caplog.text


def test_a_warm_every_zero_seconds_reads_nothing_ahead(counted_reads, trips, clock):
    warm = Warm(DEMO, the_app_itself, every_seconds=0, clock=clock, finished=lambda engine: None)
    create_app(engine_for=counted_reads, page_cache=PageCache(seconds=7200, entries=50, clock=clock), warm=warm,
               today=lambda: TODAY)

    assert warm.tick() is False
    assert trips == []


def test_the_server_reads_the_demo_s_pages_ahead_as_the_app_itself_and_a_command_driving_the_routes_does_not():
    environ = {"DATABRICKS_CLIENT_ID": "strata-app", "DATABRICKS_CLIENT_SECRET": "not-a-real-key",
               "DATABRICKS_WAREHOUSE_ID": "wh-1"}
    with fake_workspace() as (host, calls):
        environ["DATABRICKS_HOST"] = host
        assert app_from_env(environ).state.warm is None  # the seed command's app, and the tests'
        app = app_from_env(environ, read_ahead=True)
        assert app.state.page_cache is not None

        async def run():
            async with app.router.lifespan_context(app):
                await asyncio.to_thread(app.state.warm.ran.wait, 10)
        asyncio.run(run())

    read = [(auth, text) for kind, auth, text in calls if kind == "statement"]
    assert any("strata.gold.project" in text for _, text in read)
    assert any("strata.ops.pipeline_runs" in text for _, text in read)
    assert {auth for auth, _ in read} == {"Bearer app-not-real"}


def test_the_demo_file_names_the_slice_s_showcase_and_the_demo_plan_s_project_and_package():
    demo, cases = load_demo(), load_slice()

    assert {cases.showcase.project_id, cases.demo_plan.project_id} <= set(demo.projects)
    assert cases.demo_plan.package in demo.packages


def test_the_page_window_and_size_are_read_from_the_thresholds_file():
    thresholds = load_thresholds()

    kept = PageCache.from_thresholds(thresholds)

    assert (kept.seconds, kept.entries) == (thresholds.value("app.page_cache_seconds"),
                                            thresholds.value("app.page_cache_entries"))
