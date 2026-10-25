"""Writes the time estimate's recorded answers in tests/fixtures/api from the server itself (ticket 26).

The screen tests serve these files from their mocked API, and tests/test_estimate_routes.py checks that the server
still answers with them, so the package workspace and the server cannot drift apart. Build the fixture database
first, then run:

    uv run --frozen python tests/record_estimate_api.py

Everything is read as of October 23, 2026, the day the fixture's nightly run scored every package with the
champion it trained. The demo package, KE-NWWDA-541055-CW-RFB, is larger than any package that model learned
from, so its time estimate abstains; with review type Prior it has seven comparable packages. KE-NWWDA-229129-CW-RFB,
estimated at US$300,000, is inside what the model learned from, so its page, comparables, risks and time estimate
are recorded for lane 2 drawn in full, and its time estimate as of October 22, the day before the model's training
data ended. Ana's rural roads package from a sentence and a saved plan-date choice are recorded too.
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

from strata import appstate  # noqa: E402
from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.packages.store import PackageStore  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
TODAY = dt.date(2026, 10, 23)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
DEMO, SIGNED_2022 = "KE-NWWDA-541055-CW-RFB", "KE-NWWDA-229129-CW-RFB"
# Each GET the screens make, by the file its answer is recorded in, with its query.
GETS = {
    "estimate-ke-nwwda-541055.json": (f"/api/packages/{DEMO}/estimate", {}),
    "estimate-ke-nwwda-541055-prior.json": (f"/api/packages/{DEMO}/estimate", {"review_type": "Prior"}),
    "package-ke-nwwda-229129.json": (f"/api/packages/{SIGNED_2022}", {"asof": "2026-10-23"}),
    "comparables-ke-nwwda-229129.json": (f"/api/packages/{SIGNED_2022}/comparables", {}),
    "risks-ke-nwwda-229129.json": (f"/api/packages/{SIGNED_2022}/risks", {}),
    "estimate-ke-nwwda-229129.json": (f"/api/packages/{SIGNED_2022}/estimate", {}),
    "estimate-ke-nwwda-229129-before-training.json": (f"/api/packages/{SIGNED_2022}/estimate", {"asof": "2026-10-22"}),
}


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    state_db = folder / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        appstate.build(engine)
    cases = load_cases(PACKAGE_CASES)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(FIXTURE_DB, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=reading, packages=PackageStore(lambda: DuckDBEngine.open(state_db)),
                     package_reader=lambda: ScriptedAgent(cases["package-rural-roads-kenya"]), today=lambda: TODAY,
                     now=lambda: dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC),
                     new_package_id=lambda: "pkg-000000000001", new_save_id=lambda: "save-0001",
                     new_run_id=lambda: "run-0001")

    def pretty(response) -> str:
        return json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"

    async def story() -> dict[str, str]:
        found = {}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            for name, (path, params) in GETS.items():
                found[name] = pretty(await client.get(path, headers=ANA, params=params))
            await client.post("/api/planned-packages", headers=ANA,
                              json={"sentence": "rural roads, Kenya, about US$15 million"})
            found["estimate-planned-rural-roads.json"] = pretty(
                await client.get("/api/planned-packages/pkg-000000000001/estimate", headers=ANA))
            found["plan-dates-saved.json"] = pretty(
                await client.put(f"/api/packages/{SIGNED_2022}/plan-dates", headers=ANA, json={"choice": "middle"}))
        return found

    return asyncio.run(story())


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        for name, text in answers(Path(folder)).items():
            (OUT / name).write_text(text)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
