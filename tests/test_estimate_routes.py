"""The time estimate's routes (ticket 26) at seam 3: GET .../estimate answers estimate_time's result with the
viewer's saved plan-date choice, and PUT .../plan-dates keeps that choice for the viewer in the app state store.

The app reads the fixture database as the viewer and keeps app state in a DuckDB file with only its own tables,
as Lakebase holds them on the App. The screens' recorded answers in tests/fixtures/api come from these routes
(tests/record_estimate_api.py), and the last test checks the routes still answer with them.
"""

import asyncio
import datetime as dt
import json
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata import appstate
from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.packages.store import PackageStore
from strata.server.app import create_app
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "tests" / "fixtures" / "api"
SCORED_ON = dt.date(2026, 10, 23)
SIGNED_2022 = "KE-NWWDA-229129-CW-RFB"
DEMO = "KE-NWWDA-541055-CW-RFB"


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"40{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN = viewer(21, "Ana"), viewer(22, "Ben")


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


@pytest.fixture
def app(fixture_db, tmp_path):
    state = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state) as engine:
        appstate.build(engine)

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    cases = load_cases(PACKAGE_CASES)
    numbers = iter(range(1, 100))
    return create_app(engine_for=reading, packages=PackageStore(lambda: DuckDBEngine.open(state)),
                      package_reader=lambda: ScriptedAgent(cases["package-rural-roads-kenya"]), today=lambda: SCORED_ON,
                      now=lambda: dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC),
                      new_package_id=lambda: f"pkg-{next(numbers):012d}", new_run_id=lambda: "run-0001")


def test_the_estimate_route_answers_estimate_time_as_the_viewer_with_no_saved_choice_yet(app, fixture_db):
    answered = call(app, "GET", f"/api/packages/{SIGNED_2022}/estimate", ANA)

    assert answered.status_code == 200
    body = answered.json()
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        direct = registry.call("estimate_time", {"step_reference": SIGNED_2022, "as_of": SCORED_ON},
                               registry.Context(engine, Viewer(name="Ana"), "staff", SCORED_ON))
    assert body["estimate"] == direct["estimate"]
    assert body["comparisons"] == direct["comparisons"] and body["options"] == direct["options"]
    assert body["plan_date_choice"] is None and body["plan_dates"]["default"] == "eight_in_ten"


def test_a_plan_date_choice_is_kept_for_its_viewer_and_package_only(app):
    saved = call(app, "PUT", f"/api/packages/{SIGNED_2022}/plan-dates", ANA, json={"choice": "middle"})

    assert saved.status_code == 200 and saved.json() == {"plan_date_choice": "middle"}
    assert call(app, "GET", f"/api/packages/{SIGNED_2022}/estimate", ANA).json()["plan_date_choice"] == "middle"
    assert call(app, "GET", f"/api/packages/{SIGNED_2022}/estimate", BEN).json()["plan_date_choice"] is None
    assert call(app, "GET", f"/api/packages/{DEMO}/estimate", ANA).json()["plan_date_choice"] is None
    again = call(app, "PUT", f"/api/packages/{SIGNED_2022}/plan-dates", ANA, json={"choice": "eight_in_ten"})
    assert again.json() == {"plan_date_choice": "eight_in_ten"}


def test_a_preview_cannot_change_the_plan_date_choice_and_a_choice_must_be_one_of_the_two(app):
    preview = call(app, "PUT", f"/api/packages/{SIGNED_2022}/plan-dates", ANA, json={"choice": "middle", "view": "piu"})
    wrong = call(app, "PUT", f"/api/packages/{SIGNED_2022}/plan-dates", ANA, json={"choice": "latest"})

    assert preview.status_code == 403 and preview.json()["code"] == "preview"
    assert wrong.status_code == 422
    assert call(app, "GET", f"/api/packages/{SIGNED_2022}/estimate", ANA).json()["plan_date_choice"] is None


def test_section_1_s_criteria_reach_the_tool_as_find_comparables_takes_them(app):
    narrower = call(app, "GET", f"/api/packages/{DEMO}/estimate?review_type=Prior", ANA).json()

    assert narrower["abstention"] == {"reason": "too_few_comparables", "count": 7, "min_comparables": 20}
    assert call(app, "GET", f"/api/packages/{DEMO}/estimate?size_from_usd=lots", ANA).status_code == 422


def test_a_package_planned_from_a_sentence_is_described_to_the_tool_by_its_saved_fields_for_its_author_only(app):
    sent = call(app, "POST", "/api/planned-packages", ANA, json={"sentence": "rural roads, Kenya, about US$15 million"})
    package_id = next(json.loads(line.removeprefix("data: "))["package"]["package_id"]
                      for block in sent.text.split("\n\n") if block.startswith("event: package")
                      for line in block.splitlines() if line.startswith("data: "))

    mine = call(app, "GET", f"/api/planned-packages/{package_id}/estimate", ANA)
    theirs = call(app, "GET", f"/api/planned-packages/{package_id}/estimate", BEN)

    assert mine.status_code == 200
    body = mine.json()
    # US$15 million is far larger than any package the fixture's champion learned from.
    assert body["abstention"]["reason"] == "outside_training"
    assert body["package"]["described"]["estimated_amount_usd"] == 15_000_000
    assert body["comparables"]["n"] == 49
    assert theirs.status_code == 404
    saved = call(app, "PUT", f"/api/planned-packages/{package_id}/plan-dates", ANA, json={"choice": "middle"})
    assert saved.json() == {"plan_date_choice": "middle"}
    assert call(app, "PUT", f"/api/planned-packages/{package_id}/plan-dates", BEN, json={"choice": "middle"}).status_code == 404


def test_the_screens_recorded_estimate_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """The screen tests and the gallery draw lane 2 from these files, so a change to the tool or the route that
    changes an answer fails here until the files are recorded again (tests/record_estimate_api.py)."""
    import record_estimate_api

    for name, text in record_estimate_api.answers(tmp_path).items():
        assert json.loads(text) == json.loads((RECORDED / name).read_text()), name
