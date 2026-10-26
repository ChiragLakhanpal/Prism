"""Writes the recorded answers of "Check your criteria" in tests/fixtures/api from the server itself (ticket 31).

The screen tests serve these files from their mocked API, and tests/test_check_criteria.py checks that the server
still answers with them, so section 5 of the package workspace and the server cannot drift apart. Build the
fixture database first, then run:

    uv run --frozen python tests/record_criteria_api.py

One story makes them all, as of October 28, 2026, on a copy of the fixture database in which two people added the
rebidding lesson (ICR P130164 paragraph 54) to the library on October 27 (tests/lesson_scenario.py), with the
scripted criteria reader's cases (tests/fixtures/agent/criteria.toml) and check 4's recorded judge answers for
them (tests/fixtures/agent/judged), a fixed clock and fixed ids. Ana opens
KE-NWWDA-541055-CW-RFB, whose works comparables published no qualification criteria, and its package-level run;
then the consultant services package KE-CWSB-224323-CS-QCBS, whose comparables did, its run, and five comparisons
of pasted text: the ticket's similar experience, a live tender's bids, a partial refusal, text with no criteria,
a question about a review decision, and the ticket's text read back with its numbers swapped, which check 4's judge
removes. Her saved comparison then shows in the collapsed summary, and nobody else's does. Last, she plans
"rural roads, Kenya, about US$15 million" and opens its section.
"""

import asyncio
import datetime as dt
import json
import sys
import tempfile
from unittest import mock
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import lesson_scenario as scenario  # noqa: E402
from strata import appstate  # noqa: E402
from strata.agent.scripted import CRITERIA_CASES, PACKAGE_CASES, ScriptedAgent, ScriptedJudge, load_cases  # noqa: E402
from strata.criteria.store import CriteriaStore  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.packages.store import PackageStore  # noqa: E402
from strata.server.app import create_app  # noqa: E402
from strata.tools import registry  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
TODAY = dt.date(2026, 10, 28)
# The day these answers were recorded. A route called with no asof date dates its answer by the registry's clock
# (strata.tools.registry.today), not by the app's today, so the recorder pins that clock: without it the
# recorded answers stop matching at the next midnight UTC.
RECORDED_ON = dt.date(2026, 10, 25)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
CY = {"X-Forwarded-Email": "cy.example@worldbank.org", "X-Forwarded-Preferred-Username": "Cy Example",
      "X-Forwarded-User": "4023@1984", "X-Forwarded-Access-Token": "token-for-cy-only"}
WORKS, CONSULTANT = "KE-NWWDA-541055-CW-RFB", "KE-CWSB-224323-CS-QCBS"
COMPARISONS = {"criteria-compare-similar-experience.sse": "criteria-similar-experience",
               "criteria-compare-live-tender.sse": "criteria-live-tender",
               "criteria-compare-partial-refusal.sse": "criteria-partial-refusal",
               "criteria-compare-none-found.sse": "criteria-none-found",
               "criteria-compare-review-decisions.sse": "criteria-review-decisions",
               "criteria-compare-swapped-reading.sse": "criteria-swapped-reading"}


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    library = scenario.copy_of(FIXTURE_DB, folder)
    scenario.decide(library, scenario.REBIDDING, dt.date(2026, 10, 27))
    state_db = folder / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        appstate.build(engine)
    at = [dt.datetime(2026, 10, 28, 14, 0, tzinfo=dt.UTC)]
    criteria_cases, package_cases = load_cases(CRITERIA_CASES), load_cases(PACKAGE_CASES)
    case = ["criteria-similar-experience"]
    checks = iter(f"chk-{number:012d}" for number in range(1, 100))

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(library, read_only=True) as engine:
            yield engine

    def state():
        return DuckDBEngine.open(state_db)

    class CaseJudge:
        """Check 4's judge for the reader's case in play: its recorded answers (tests/fixtures/agent/judged)."""

        name = "scripted judge"

        def judge(self, questions):
            return ScriptedJudge(criteria_cases[case[0]]).judge(questions)

    def now() -> dt.datetime:
        at[0] += dt.timedelta(seconds=1)
        return at[0]

    app = create_app(engine_for=reading, criteria=CriteriaStore(state), packages=PackageStore(state),
                     criteria_reader=lambda: ScriptedAgent(criteria_cases[case[0]]),
                     package_reader=lambda: ScriptedAgent(package_cases["package-rural-roads-kenya"]),
                     today=lambda: TODAY, now=now, new_check_id=lambda: next(checks),
                     new_package_id=lambda: "pkg-000000000001", new_save_id=lambda: "save-0001",
                     new_run_id=lambda: "run-0001", judge=CaseJudge())

    def pretty(response) -> str:
        return json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"

    async def story() -> dict[str, str]:
        found = {}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            async def get(path: str, headers=ANA) -> str:
                return pretty(await client.get(path, headers=headers))

            async def post(path: str, body: dict, headers=ANA) -> str:
                return (await client.post(path, headers=headers, json=body)).text

            found["criteria-summary-ke-nwwda-541055.json"] = await get(f"/api/packages/{WORKS}/criteria")
            found["criteria-run-ke-nwwda-541055.sse"] = await post(f"/api/packages/{WORKS}/criteria/run", {})
            # The award notice a rejected bid of KE-MOWI-47509-CW-RFB cites, with the reason it quoted.
            found["evidence-award-notice-op00125282.json"] = await get(
                "/api/evidence?id=strata.gold.notice:OP00125282/reason/1&asof=2026-10-28")
            found["package-ke-cwsb-224323.json"] = await get(f"/api/packages/{CONSULTANT}")
            found["comparables-ke-cwsb-224323.json"] = await get(f"/api/packages/{CONSULTANT}/comparables")
            found["criteria-summary-ke-cwsb-224323.json"] = await get(f"/api/packages/{CONSULTANT}/criteria")
            found["criteria-run-ke-cwsb-224323.sse"] = await post(f"/api/packages/{CONSULTANT}/criteria/run", {})
            # A notice whose short-listing criteria a comparison counted, as the drawer opens it from an item's list.
            found["evidence-passage-op00077276-s3.json"] = await get(
                "/api/evidence?id=strata.gold.passage:OP00077276/v1/s3&asof=2026-10-28")
            for name, reader_case in COMPARISONS.items():
                case[0] = reader_case
                found[name] = await post(f"/api/packages/{CONSULTANT}/criteria/compare",
                                         {"text": criteria_cases[reader_case].question})
            # The comparison she kept is the last one she made: compare the ticket's text again, so the summary
            # shows it.
            case[0] = "criteria-similar-experience"
            await post(f"/api/packages/{CONSULTANT}/criteria/compare",
                       {"text": criteria_cases["criteria-similar-experience"].question})
            found["criteria-summary-ke-cwsb-224323-compared.json"] = await get(f"/api/packages/{CONSULTANT}/criteria")
            found["criteria-summary-ke-cwsb-224323-someone-else.json"] = await get(f"/api/packages/{CONSULTANT}/criteria", CY)
            await post("/api/planned-packages", {"sentence": "rural roads, Kenya, about US$15 million"})
            found["criteria-summary-planned-rural-roads.json"] = await get("/api/planned-packages/pkg-000000000001/criteria")
            found["criteria-run-planned-rural-roads.sse"] = await post("/api/planned-packages/pkg-000000000001/criteria/run", {})
        return found

    with mock.patch.object(registry, "today", lambda: RECORDED_ON):
        return asyncio.run(story())


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        for name, text in answers(Path(folder)).items():
            (OUT / name).write_text(text)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
