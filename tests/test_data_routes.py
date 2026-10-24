"""The Data tab's routes at seam 3, driven over HTTP (ticket 16).

- GET /api/data/readiness runs data_readiness_for through the tool registry as the viewer, with the
  page's ?sources=, ?from= and ?asof=. Its answers on the fixture are recorded once in
  tests/fixtures/api, and the screen tests serve the same files. tests/record_api.py writes them.
- GET /api/data/sources reads only the source and tool registries, so the Sources and licenses page
  and the Data readiness page's skeleton work while the warehouse is down.
"""

import asyncio
import json
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path

import httpx
import pytest

from strata import config
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine, EngineError, PermissionDenied, Result
from strata.server.app import create_app

RECORDED = Path(__file__).parent / "fixtures" / "api"
ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}
# The day the fixture's sources were recorded and measured (tests/test_data_readiness.py).
ON_THE_FIXTURE_DAY = "asof=2026-10-23"


def recorded(name):
    return json.loads((RECORDED / name).read_text())


def get(app, path, headers=None):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=headers or {})
    return asyncio.run(go())


@pytest.fixture
def viewers_seen():
    return []


@pytest.fixture
def fixture_app(fixture_db, viewers_seen):
    @contextmanager
    def engine_for(viewer):
        viewers_seen.append(viewer)
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for)


def each_viewer_gets(engine):
    return lambda viewer: nullcontext(engine)


@pytest.mark.parametrize("query, name", [
    (ON_THE_FIXTURE_DAY, "data-readiness.json"),
    (f"sources=awards,notices&from=find_comparables&{ON_THE_FIXTURE_DAY}", "data-readiness-filtered.json"),
    (f"sources=documents,projects&from=check_plan&{ON_THE_FIXTURE_DAY}", "data-readiness-plan-check.json"),
    (f"sources=awards,not-a-source&from=find_comparables&{ON_THE_FIXTURE_DAY}", "data-readiness-unknown-key.json"),
    (f"sources=not-a-source&{ON_THE_FIXTURE_DAY}", "data-readiness-no-known-key.json"),
    ("asof=2026-10-01", "data-readiness-before-first.json"),
])
def test_the_page_s_answers_on_the_fixture_are_the_recorded_ones(fixture_app, viewers_seen, query, name):
    response = get(fixture_app, f"/api/data/readiness?{query}", ANA)

    assert response.status_code == 200
    assert response.json() == recorded(name)
    assert [(viewer.email, viewer.token) for viewer in viewers_seen] == [("ana.example@worldbank.org", "token-for-ana-only")]
    assert "token-for-ana-only" not in response.text


@pytest.fixture
def engine_on(tmp_path):
    """An app that reads a catalog this test builds under tmp_path."""
    def app_for(rows=None):
        path = tmp_path / "strata.duckdb"
        with DuckDBEngine.open(path) as engine:
            catalog.build(engine)
            if rows is not None:
                engine.insert_rows("strata.ops.data_readiness", rows.columns, list(rows.rows))

        @contextmanager
        def engine_for(viewer):
            with DuckDBEngine.open(path, read_only=True) as engine:
                yield engine
        return create_app(engine_for=engine_for)
    return app_for


def test_the_recorded_answer_with_no_measures_yet_is_the_server_s_on_an_empty_catalog(engine_on):
    response = get(engine_on(), f"/api/data/readiness?{ON_THE_FIXTURE_DAY}", ANA)

    assert response.json() == recorded("data-readiness-empty.json")


def test_the_recorded_answer_with_one_source_unmeasured_is_the_server_s_without_wgi_s_measures(fixture_db, engine_on):
    """As tests/record_api.py makes it: the fixture's measures for every source but WGI."""
    with DuckDBEngine.open(fixture_db, read_only=True) as fixture:
        measured = fixture.run("SELECT * FROM strata.ops.data_readiness WHERE source <> :left_out", {"left_out": "wgi"})

    response = get(engine_on(measured), f"/api/data/readiness?{ON_THE_FIXTURE_DAY}", ANA)

    assert response.json() == recorded("data-readiness-unmeasured.json")


def test_with_no_forwarded_identity_the_page_runs_no_query():
    asked = []

    response = get(create_app(engine_for=lambda viewer: asked.append(viewer)), "/api/data/readiness")

    assert (response.status_code, response.json(), asked) == (401, {"code": "no_identity"}, [])


def test_a_viewer_the_warehouse_refuses_gets_a_permission_error_and_no_measures():
    class Refusing:
        def run(self, sql, params=None):
            raise PermissionDenied("[INSUFFICIENT_PERMISSIONS] User does not have USE CATALOG on Catalog 'strata'.")

    response = get(create_app(engine_for=each_viewer_gets(Refusing())), "/api/data/readiness", ANA)

    assert (response.status_code, response.json()) == (403, recorded("data-readiness-no-access.json"))


def test_a_slow_warehouse_gives_a_timeout_that_says_how_long_the_page_waited():
    class Slow:
        def run(self, sql, params=None):
            time.sleep(0.2)
            return Result((), ())

    app = create_app(engine_for=each_viewer_gets(Slow()), stamp_timeout_seconds=0.02)

    response = get(app, "/api/data/readiness", ANA)

    assert (response.status_code, response.json()) == (504, {"code": "timeout", "timeout_seconds": 0.02})


def test_a_failing_warehouse_gives_an_error_that_keeps_its_reason_private():
    class Failing:
        def run(self, sql, params=None):
            raise EngineError("The warehouse did not run the statement: the secret detail")

    response = get(create_app(engine_for=each_viewer_gets(Failing())), "/api/data/readiness", ANA)

    assert (response.status_code, response.json()) == (502, recorded("data-readiness-error.json"))
    assert "secret detail" not in response.text


def test_the_recorded_timeout_says_the_thresholds_file_s_wait():
    assert recorded("data-readiness-timeout.json") == {
        "code": "timeout", "timeout_seconds": config.load_thresholds().value("app.stamp_timeout_seconds")}


def test_sources_and_licenses_read_only_the_registries_and_work_with_no_data_service():
    response = get(create_app(engine_for=None), "/api/data/sources", ANA)

    assert response.status_code == 200
    assert response.json() == recorded("data-sources.json")


def test_sources_and_licenses_list_every_dataset_in_registry_order_with_its_checked_name():
    sources = config.load_sources()

    datasets = recorded("data-sources.json")["datasets"]

    assert [entry["key"] for entry in datasets] == [key for key, source in sources.items() if source.attribution]
    awards = datasets[0]
    assert (awards["dataset_name"], awards["data_source"]) == (
        "Contract Awards in Investment Project Financing (Since FY 2020)",
        "Systematic Tracking of Exchanges in Procurement (STEP)")
    assert recorded("data-sources.json")["readiness_rows"] == sum(len(s.readiness) for s in sources.values())
