"""Writes the planned package routes' recorded answers in tests/fixtures/api from the server itself (ticket 15).

The screen tests serve these files from their mocked API, and tests/test_planned_packages.py checks that the
server still answers with them, so the package workspace and the server cannot drift apart. Build the fixture
database first, then run:

    uv run --frozen python tests/record_packages_api.py

One story makes them all, on the fixture database as of October 23, 2026, with the scripted package reader's
cases (tests/fixtures/agent/packages.toml), a fixed clock and fixed ids. Ana opens the NWWDA plan check, then
plans "rural roads, Kenya, about US$15 million" (pkg-000000000001). Each change the screens make to it is
recorded from that same first save, so every change answer belongs to the package the page opened. She then
plans a package and sets its criteria herself, plans one whose sentence asks for lots to stay under prior
review, and tries a sentence with no package in it and a reader that does not answer. The comparables for
Kenya's works under Request for Bids and under Request for Quotations, the evidence drawer's view of three
comparables and of one canceled package, and the Packages tab, Ana's and an empty one, are recorded too.
"""

import asyncio
import datetime as dt
import json
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strata.agent.loop import AgentError  # noqa: E402
from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases  # noqa: E402
from strata import appstate  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.packages.store import PackageStore  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
TODAY = dt.date(2026, 10, 23)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
CY = {"X-Forwarded-Email": "cy.example@worldbank.org", "X-Forwarded-Preferred-Username": "Cy Example",
      "X-Forwarded-User": "4023@1984", "X-Forwarded-Access-Token": "token-for-cy-only"}
SENTENCE = "rural roads, Kenya, about US$15 million"
DIVIDING = "rural roads, Kenya, about US$15 million, in lots small enough to stay under prior review"
NO_PACKAGE = "what is the weather like in Nairobi"
RFB = {"category": "Works", "country": "KE", "method": "Request for Bids"}
RFQ = {"category": "Works", "country": "KE", "method": "Request for Quotations"}
# Each change the screen tests make to the first package, by the file its answer is recorded in.
CHANGES = {
    "planned-package-change-method-rfq.json": {"field": "method", "action": "set", "value": "Request for Quotations"},
    "planned-package-change-method-icb.json": {"field": "method", "action": "set", "value": "ICB"},
    "planned-package-change-keep-lots.json": {"field": "lots", "action": "keep"},
    "planned-package-change-amount.json": {"field": "estimated_amount_usd", "action": "set", "value": 5_000_000},
    "planned-package-change-review-post.json": {"field": "review_type", "action": "set", "value": "Post"},
    "planned-package-change-description.json": {"field": "description", "action": "set", "value": "Rural feeder roads"},
    "planned-package-change-plan.json": {"field": "plan_months", "action": "set", "value": 6, "plan_before_range": True},
    # Goods in Kenya: the thresholds file gives no market approach threshold, so market approach empties.
    "planned-package-change-category-goods.json": {"field": "category", "action": "set", "value": "Goods"},
}
# Three comparables of Kenya's works under Request for Bids: signed with a contract award, still open, and
# signed only in its award notice; and one that was canceled (tests/ground_truth/values.toml).
EVIDENCE = {
    "evidence-package-ke-mowi-47509.json": "strata.gold.package:KE-MOWI-47509-CW-RFB",
    "evidence-package-ke-icta-571738.json": "strata.gold.package:KE-ICTA-571738-CW-RFB",
    "evidence-package-ke-gawasco-54771.json": "strata.gold.package:KE-GAWASCO-54771-CW-RFB",
    "evidence-package-ke-kimawasco-149448.json": "strata.gold.package:KE-KIMAWASCO-149448-CW-RFB",
}


class Unavailable:
    name, version = "strata-package-reader", None

    def respond(self, items, previous_response_id):
        raise AgentError("agent_unavailable", "A recorded stream for the screen tests.")


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    state_db = folder / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        appstate.build(engine)
    at = [dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC)]
    cases = load_cases(PACKAGE_CASES)
    reading_case = ["package-rural-roads-kenya"]
    packages = iter(f"pkg-{number:012d}" for number in range(1, 100))
    saves = iter(f"save-{number:04d}" for number in range(1, 1000))
    runs = iter(f"run-{number:04d}" for number in range(1, 100))

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(FIXTURE_DB, read_only=True) as engine:
            yield engine

    def state():
        return DuckDBEngine.open(state_db)

    def reader():
        return Unavailable() if reading_case[0] == "unavailable" else ScriptedAgent(cases[reading_case[0]])

    app = create_app(engine_for=reading, packages=PackageStore(state), package_reader=reader, today=lambda: TODAY,
                     now=lambda: at[0], new_package_id=lambda: next(packages), new_save_id=lambda: next(saves),
                     new_run_id=lambda: next(runs))

    def later(minutes: int):
        at[0] += dt.timedelta(minutes=minutes)

    def pretty(response) -> str:
        return json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"

    async def story() -> dict[str, str]:
        found = {}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            async def plan(case: str, sentence: str, **extra) -> str:
                reading_case[0] = case
                answer = await client.post("/api/planned-packages", headers=ANA, json={"sentence": sentence, **extra})
                return answer.text

            async def get(path: str, headers=ANA, **params) -> str:
                return pretty(await client.get(path, headers=headers, params=params))

            await client.get("/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09",
                             headers=ANA, params={"asof": "2026-10-23"})
            later(5)
            found["package-plan-rural-roads.sse"] = await plan("package-rural-roads-kenya", SENTENCE)
            found["planned-package-rural-roads.json"] = await get("/api/planned-packages/pkg-000000000001")
            found["comparables-planned-works-rfb-ke.json"] = await get("/api/comparables", **RFB)
            found["comparables-planned-works-rfq-ke.json"] = await get("/api/comparables", **RFQ)
            # Each change from the first save: the state is put back before the next one.
            first = folder / "first.duckdb"
            shutil.copyfile(state_db, first)
            later(1)
            for name, body in CHANGES.items():
                found[name] = pretty(await client.post("/api/planned-packages/pkg-000000000001", headers=ANA, json=body))
                shutil.copyfile(first, state_db)
            for name, evidence in EVIDENCE.items():
                found[name] = await get("/api/evidence", id=evidence, asof="2026-10-23")
            later(10)
            found["package-plan-yourself.sse"] = await plan("package-rural-roads-kenya", SENTENCE, read=False)
            found["planned-package-yourself.json"] = await get("/api/planned-packages/pkg-000000000002")
            # Sections 2 and 5 of the package set up yourself, which lacks the criteria that pick comparables (ticket
            # 60's design review, F6), so the capture's planned--missing shows each section as the app reads it.
            found["steps-planned-yourself.json"] = await get("/api/planned-packages/pkg-000000000002/steps")
            found["criteria-summary-planned-yourself.json"] = await get("/api/planned-packages/pkg-000000000002/criteria")
            later(10)
            found["package-plan-dividing.sse"] = await plan("package-dividing", DIVIDING)
            found["planned-package-dividing.json"] = await get("/api/planned-packages/pkg-000000000003")
            found["steps-planned-dividing.json"] = await get("/api/planned-packages/pkg-000000000003/steps")
            found["criteria-summary-planned-dividing.json"] = await get("/api/planned-packages/pkg-000000000003/criteria")
            found["package-plan-no-package.sse"] = await plan("package-no-package", NO_PACKAGE)
            found["package-plan-reader-unavailable.sse"] = await plan("unavailable", SENTENCE)
            found["planned-packages-list.json"] = await get("/api/planned-packages")
            found["planned-packages-empty.json"] = await get("/api/planned-packages", CY)
            found["planned-package-not-found.json"] = await get("/api/planned-packages/pkg-000000000001", CY)
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
