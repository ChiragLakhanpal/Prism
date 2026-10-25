"""Writes the risks section's recorded answers in tests/fixtures/api from the server itself (ticket 30).

The screen tests and the design gallery serve these files, and tests/test_package_risks.py checks that the
server still answers with them, so section 3 of the package workspace and the server cannot drift apart. Build
the fixture database first, then run:

    uv run --frozen python tests/record_risks_api.py

One story makes them all, on a copy of the fixture database as of October 28, 2026, after two reviewers from
tests/fixtures/roles.toml added the fixture's three proposed lessons to the library on October 27
(tests/lesson_scenario.py). The fixture's only completion reports are P130164's, and Kenya's comparable works
packages belong to projects still active, so:

- risks-ke-nwwda-541055.json: the demo plan's works package with section 1's default criteria, whose comparable
  packages reach no completion report (the fixture's true state for Kenya).
- risks-ke-nwwda-541055-india.json: the same package with section 1's country set to India and notices from
  2013, whose comparables reach P130164's IN-RRSMP-7431-CW-RFB and so its ICR: the table with the cost estimates
  row (ICR paragraph 54, restated in the ICR Review's section 10.b) and the permits row (ICR paragraph 55).
  risks-ke-nwwda-541055-india-selected.json is the same after Ana selected the cost estimates row, and
  risks-selection-saved.json is that PUT's answer.
- risks-planned-rural-roads.json: the rural roads package from a sentence (pkg-000000000001, as
  tests/record_packages_api.py records it), whose Kenya comparables reach no completion report either.
- evidence-icr-review-p130164-10b.json: the ICR Review's section 10.b, the cost estimates row's second source,
  for the evidence drawer's switcher.
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

import lesson_scenario as scenario  # noqa: E402
from strata import appstate  # noqa: E402
from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.packages.store import PackageStore  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
DECIDED, TODAY = dt.date(2026, 10, 27), dt.date(2026, 10, 28)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
DEMO = "/api/packages/KE-NWWDA-541055-CW-RFB"
INDIA = {"country": "IN", "notice_from": "2013-01-01"}


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    library = scenario.copy_of(FIXTURE_DB, folder)
    for passage in (scenario.REBIDDING, scenario.PERMITS, scenario.IEG_LESSON):
        scenario.decide(library, passage, DECIDED)
    state_db = folder / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        appstate.build(engine)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(library, read_only=True) as engine:
            yield engine

    cases = load_cases(PACKAGE_CASES)
    packages = iter(f"pkg-{number:012d}" for number in range(1, 100))
    app = create_app(engine_for=reading, packages=PackageStore(lambda: DuckDBEngine.open(state_db)),
                     package_reader=lambda: ScriptedAgent(cases["package-rural-roads-kenya"]), today=lambda: TODAY,
                     now=lambda: dt.datetime(2026, 10, 28, 9, tzinfo=dt.UTC), new_package_id=lambda: next(packages))

    def pretty(response) -> str:
        return json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"

    async def story() -> dict[str, str]:
        found = {}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            async def get(path: str, **params) -> str:
                return pretty(await client.get(path, headers=ANA, params=params))

            found["risks-ke-nwwda-541055.json"] = await get(f"{DEMO}/risks")
            found["risks-ke-nwwda-541055-india.json"] = await get(f"{DEMO}/risks", **INDIA)
            found["risks-selection-saved.json"] = pretty(await client.put(
                f"{DEMO}/risk-selection", headers=ANA, json={"changes": {"cost_estimates": True}}))
            found["risks-ke-nwwda-541055-india-selected.json"] = await get(f"{DEMO}/risks", **INDIA)
            await client.post("/api/planned-packages", headers=ANA,
                              json={"sentence": "rural roads, Kenya, about US$15 million"})
            found["risks-planned-rural-roads.json"] = await get("/api/planned-packages/pkg-000000000001/risks")
            found["evidence-icr-review-p130164-10b.json"] = await get(
                "/api/evidence", id="strata.gold.passage:34056616/v2/10.b", asof=TODAY.isoformat())
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
