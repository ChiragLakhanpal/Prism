"""The routes of the package workspace's section 2, "Planned date for each step" (ticket 27; spec, seam 3).

GET .../steps runs estimate_time as the viewer and answers with its result, the viewer's saved choice of dates
(shared with ticket 26's plan-date choice) and the date they gave the first step. PUT .../plan-dates keeps the
choice and PUT .../step-start the date, in the app state store (a DuckDB file here, Lakebase on the App), for the
viewer and package, and a preview keeps neither.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest
import step_set

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
KNOWN = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["step_dates"]
TODAY = dt.date(2026, 10, 28)


def person(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": name,
            "X-Forwarded-User": f"60{number}@1984", "X-Forwarded-Access-Token": "not-a-real-token"}


ANA, BEN = person(1, "Ana"), person(2, "Ben")


def make_app(database, tmp_path):
    from contextlib import contextmanager

    from strata import appstate
    from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases
    from strata.packages.store import PackageStore
    from strata.server.app import create_app

    state = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state) as engine:
        appstate.build(engine)

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    cases = load_cases(PACKAGE_CASES)
    numbers = iter(range(1, 100))
    return create_app(engine_for=reading, packages=PackageStore(lambda: DuckDBEngine.open(state)),
                      package_reader=lambda: ScriptedAgent(cases["package-rural-roads-kenya"]), today=lambda: TODAY,
                      now=lambda: dt.datetime(2026, 10, 28, 9, tzinfo=dt.UTC),
                      new_package_id=lambda: f"pkg-{next(numbers):012d}")


def call(app, method, path, headers, **options):
    import asyncio

    import httpx

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers, **options)
    return asyncio.run(go())


@pytest.fixture
def hand_made_app(tmp_path):
    path = tmp_path / "set.duckdb"
    step_set.build(path).close()
    return make_app(path, tmp_path)


TARGET = f"/api/packages/{KNOWN['target']}"


@pytest.mark.parametrize("story", ["fixture", "hand-made", "unrecorded", "tracker"])
def test_the_screens_recorded_step_answers_are_what_the_routes_answer(story, fixture_db, tmp_path):
    """tests/record_steps_api.py writes the answers section 2's screen tests serve, from the fixture and the
    hand-made set; the routes must still answer with them word for word. Each story runs on its own, so the
    workers can share them out."""
    from record_steps_api import STORIES

    for name, text in STORIES[story](tmp_path).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), f"{name} is out of date"


def test_a_step_row_packages_section_answers_with_both_choices_and_cautious_by_default(hand_made_app):
    answer = call(hand_made_app, "GET", f"{TARGET}/steps?asof={KNOWN['as_of']}", ANA)

    assert answer.status_code == 200
    body = answer.json()
    assert body["plan_date_choice"] is None  # no choice saved: the screen shows the cautious dates
    signed = next(step for step in body["step_dates"]["steps"] if step["step_key"] == "contract_signed")
    assert (signed["cautious"]["planned_date"], signed["middle"]["planned_date"]) == (
        KNOWN["cautious_dates"][4].isoformat(), KNOWN["middle_dates"][4].isoformat())


def test_the_choice_of_dates_is_kept_for_the_viewer_and_a_preview_keeps_nothing(hand_made_app):
    saved = call(hand_made_app, "PUT", f"{TARGET}/plan-dates", ANA, json={"choice": "middle"})
    preview = call(hand_made_app, "PUT", f"{TARGET}/plan-dates", BEN, json={"choice": "middle", "view": "piu"})

    assert saved.status_code == 200 and saved.json() == {"plan_date_choice": "middle"}
    assert (preview.status_code, preview.json()["code"]) == (403, "preview")
    assert call(hand_made_app, "GET", f"{TARGET}/steps?asof={KNOWN['as_of']}", ANA).json()["plan_date_choice"] == "middle"
    assert call(hand_made_app, "GET", f"{TARGET}/steps?asof={KNOWN['as_of']}", BEN).json()["plan_date_choice"] is None


def test_a_package_from_a_sentence_dates_its_steps_from_the_start_date_its_author_gave(fixture_db, tmp_path):
    from test_planned_packages import plan

    app = make_app(fixture_db, tmp_path)
    _, package = plan(app, headers=ANA)
    path = f"/api/planned-packages/{package['package_id']}"

    before = call(app, "GET", f"{path}/steps", ANA).json()["step_dates"]
    given = call(app, "PUT", f"{path}/step-start", ANA, json={"start_date": "2026-11-02"})
    out_of_range = call(app, "PUT", f"{path}/step-start", ANA, json={"start_date": "2062-11-02"})

    assert (before["basis"], before["needs_start_date"]) == ("duration", True)
    assert given.status_code == 200 and given.json()["step_dates"]["start_date"] == "2026-11-02"
    assert (out_of_range.status_code, out_of_range.json()["code"]) == (422, "bad_request")
    assert call(app, "GET", f"{path}/steps", ANA).json()["step_dates"]["start_date"] == "2026-11-02"
    assert call(app, "GET", f"{path}/steps", BEN).status_code == 404
    assert call(app, "PUT", f"{path}/step-start", ANA, json={"start_date": "2026-11-03", "view": "piu"}).status_code == 403


def test_a_start_date_dates_the_steps_as_of_the_pages_date(hand_made_app):
    """A page as of January 15, 2021 dates the steps from its comparables then; today's start-date range would
    refuse March 1, 2021 as five years back."""
    from test_planned_packages import plan

    _, package = plan(hand_made_app, headers=ANA)
    path = f"/api/planned-packages/{package['package_id']}/step-start"
    start = {"start_date": KNOWN["duration_start"].isoformat()}

    as_of = call(hand_made_app, "PUT", f"{path}?asof={KNOWN['as_of']}", ANA, json=start)
    today = call(hand_made_app, "PUT", path, ANA, json=start)

    assert as_of.status_code == 200, as_of.text
    later = as_of.json()["step_dates"]["steps"][1:5]
    assert [step["cautious"]["planned_date"] for step in later] == [day.isoformat() for day in KNOWN["duration_cautious_dates"]]
    assert (today.status_code, today.json()["code"]) == (422, "bad_request")


def test_the_server_refuses_a_choice_for_an_unknown_package_and_a_start_date_its_plan_does_not_need(hand_made_app):
    unknown = call(hand_made_app, "PUT", "/api/packages/KE-HAND-999999-CW-RFB/plan-dates", ANA, json={"choice": "middle"})
    dated_by_plan = call(hand_made_app, "PUT", f"{TARGET}/step-start?asof={KNOWN['as_of']}", ANA,
                         json={"start_date": KNOWN["duration_start"].isoformat()})

    assert (unknown.status_code, unknown.json()["code"]) == (404, "unknown_package")
    assert (dated_by_plan.status_code, dated_by_plan.json()["code"]) == (409, "no_start_needed")
    # Nothing was kept: the package's steps still count from its plan, with no start date.
    steps = call(hand_made_app, "GET", f"{TARGET}/steps?asof={KNOWN['as_of']}", ANA).json()["step_dates"]
    assert (steps["basis"], steps["start_date"]) == ("delay", None)
