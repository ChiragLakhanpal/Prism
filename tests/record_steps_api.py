"""Writes section 2's recorded answers in tests/fixtures/api from the server itself (ticket 27).

The screen tests, the design gallery and the capture command serve these files, and tests/test_step_routes.py checks
that the server still answers with them, so section 2 of the package workspace and the server cannot drift apart.
Build the fixture database first, then run:

    uv run --frozen python tests/record_steps_api.py

Two stories make them. On the fixture, as of October 28, 2026, every step abstains, because no step has 20
comparable packages whose plans recorded it:

- steps-ke-nwwda-541055.json: the demo plan's works package, dated on the delay basis.
- steps-planned-rural-roads.json: Ana's rural roads package from a sentence (pkg-000000000001), which asks for the
  date of its first step.

On the hand-made set tests/step_set.py builds, as of January 15, 2021, every step but the completion can be dated
(tests/ground_truth/values.toml, [step_dates]):

- package-ke-hand-900000.json, comparables-ke-hand-900000.json and risks-ke-hand-900000.json: the target package's
  page, section 1 and section 3, so its workspace opens whole.
- steps-ke-hand-900000.json: its steps on the delay basis, both choices, with ran longest; and
  steps-ke-hand-900000-few.json the same with notices only to December 1, 2019, under 20 comparables in all.
- steps-plan-dates-saved.json: the answer to Ana choosing the middle dates.
- planned-package-hand-made.json, comparables-planned-hand-made.json and risks-planned-hand-made.json: Ana's rural
  roads package from a sentence on the hand-made set; steps-planned-hand-made.json, its steps before a start date,
  and steps-planned-hand-made-dated.json, the answer to giving March 1, 2021.
- steps-planned-hand-made-needs-earlier.json: the same package and date where a later plan records no comparable's
  bidding document, so the steps after it need an earlier step's date.
"""

import asyncio
import datetime as dt
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import step_set  # noqa: E402
from strata import appstate  # noqa: E402
from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.packages.store import PackageStore  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
SENTENCE = {"sentence": "rural roads, Kenya, about US$15 million"}
DEMO = "/api/packages/KE-NWWDA-541055-CW-RFB"
TARGET = f"/api/packages/{step_set.TARGET}"
PLANNED = "/api/planned-packages/pkg-000000000001"


def app_on(database: Path, folder: Path, today: dt.date):
    state_db = folder / f"state-{database.stem}.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        appstate.build(engine)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    cases = load_cases(PACKAGE_CASES)
    packages = iter(f"pkg-{number:012d}" for number in range(1, 100))
    now = dt.datetime.combine(today, dt.time(9), tzinfo=dt.UTC)
    return create_app(engine_for=reading, packages=PackageStore(lambda: DuckDBEngine.open(state_db)),
                      package_reader=lambda: ScriptedAgent(cases["package-rural-roads-kenya"]), today=lambda: today,
                      now=lambda: now, new_package_id=lambda: next(packages))


def pretty(response) -> str:
    return json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"

async def fixture_story(app) -> dict[str, str]:
    found = {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
        found["steps-ke-nwwda-541055.json"] = pretty(await client.get(f"{DEMO}/steps", headers=ANA))
        await client.post("/api/planned-packages", headers=ANA, json=SENTENCE)
        found["steps-planned-rural-roads.json"] = pretty(await client.get(f"{PLANNED}/steps", headers=ANA))
    return found


async def hand_made_story(app) -> dict[str, str]:
    found = {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
        async def get(path: str, **params) -> str:
            return pretty(await client.get(path, headers=ANA, params=params))

        found["package-ke-hand-900000.json"] = await get(TARGET)
        found["comparables-ke-hand-900000.json"] = await get(f"{TARGET}/comparables")
        found["risks-ke-hand-900000.json"] = await get(f"{TARGET}/risks")
        found["steps-ke-hand-900000.json"] = await get(f"{TARGET}/steps")
        found["steps-ke-hand-900000-few.json"] = await get(f"{TARGET}/steps", notice_to="2019-12-01")
        found["steps-plan-dates-saved.json"] = pretty(await client.put(
            f"{TARGET}/plan-dates", headers=ANA, json={"choice": "middle"}))
        await client.post("/api/planned-packages", headers=ANA, json=SENTENCE)
        found["planned-package-hand-made.json"] = await get(PLANNED)
        found["comparables-planned-hand-made.json"] = await get(
            "/api/comparables", category="Works", country="KE", method="Request for Bids")
        found["risks-planned-hand-made.json"] = await get(f"{PLANNED}/risks")
        found["steps-planned-hand-made.json"] = await get(f"{PLANNED}/steps")
        found["steps-planned-hand-made-dated.json"] = pretty(await client.put(
            f"{PLANNED}/step-start", headers=ANA, json={"start_date": step_set.TARGET_PLANNED[0].isoformat()}))
    return found


async def unrecorded_story(app) -> dict[str, str]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
        await client.post("/api/planned-packages", headers=ANA, json=SENTENCE)
        answer = await client.put(f"{PLANNED}/step-start", headers=ANA,
                                  json={"start_date": step_set.TARGET_PLANNED[0].isoformat()})
    return {"steps-planned-hand-made-needs-earlier.json": pretty(answer)}


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    hand_made, unrecorded = folder / "hand-made.duckdb", folder / "unrecorded.duckdb"
    step_set.build(hand_made).close()
    step_set.build(unrecorded, bidding_document_unrecorded=True).close()
    found = asyncio.run(fixture_story(app_on(FIXTURE_DB, folder, dt.date(2026, 10, 28))))
    found |= asyncio.run(hand_made_story(app_on(hand_made, folder, dt.date(2021, 1, 15))))
    found |= asyncio.run(unrecorded_story(app_on(unrecorded, folder, dt.date(2021, 1, 15))))
    return found


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        for name, text in answers(Path(folder)).items():
            (OUT / name).write_text(text)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
