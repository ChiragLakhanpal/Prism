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


def test_the_screens_recorded_step_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """tests/record_steps_api.py writes the answers section 2's screen tests serve, from the fixture and the
    hand-made set; the routes must still answer with them word for word."""
    from record_steps_api import answers

    for name, text in answers(tmp_path).items():
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
