"""Writes the recorded answers of a project's Deep research tab in tests/fixtures/api from the server itself (tickets
148 and 149).

The tab's screen tests (web/tests/research.spec.ts) serve these files from their mocked API, and
tests/test_research_brief.py checks that the server still answers with them, so the tab and the routes cannot drift
apart. Build the fixture database first, then run:

    uv run --frozen python tests/record_research_api.py

One story makes them all, as the demo does on the workspace: ticket 147's seed keeps its run for P156634 of November
5, 2026 (ops/research/seed.py) in a copy of the fixture database; Ana reads the tab before any brief is written
(research-p156634-none.json); the brief is written from the seeded run with "reuse", the recorded writer's answer
and the recorded judge's (tests/fixtures/agent/research), and its stream kept (research-p156634.sse); she reads the
brief (research-p156634.json); and she opens The Star's article of January 14, 2026 from a link
(evidence-research-item-p156634-star.json). The clock and the run's id are fixed.
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

from research_world import seed_kit, seeded_copy  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.research.store import ResearchStore  # noqa: E402
from strata.research.writer import RecordedJudge, RecordedWriter  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
RECORDED = ROOT / "tests" / "fixtures" / "agent" / "research"
TODAY = dt.date(2026, 11, 5)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
ROUTE = "/api/projects/P156634/research"
STAR = "strata.research.item:P156634/outlet_feeds/1daaf047c22f24eb"


def answers(folder: Path, fixture_db: Path = FIXTURE_DB) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    database = DuckDBEngine.open(seeded_copy(fixture_db, folder))

    @contextmanager
    def reading(viewer):
        yield database.cursor()

    app = create_app(engine_for=reading, research=ResearchStore(database.cursor),
                     research_kit=lambda: seed_kit(fixture_db),
                     research_writer=lambda: RecordedWriter(RECORDED / "P156634.json"),
                     judge=RecordedJudge(RECORDED / "P156634.judged.json"), today=lambda: TODAY,
                     now=lambda: dt.datetime(2026, 11, 5, 10, 30, tzinfo=dt.UTC),
                     new_run_id=lambda: "research-0001", heartbeat_seconds=3600)

    def pretty(response) -> str:
        return json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"

    async def story() -> dict[str, str]:
        found = {}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            found["research-p156634-none.json"] = pretty(await client.get(ROUTE, headers=ANA))
            found["research-p156634.sse"] = (await client.post(ROUTE, headers=ANA, json={
                "view": "staff", "asof": TODAY.isoformat(), "reuse": True})).text
            found["research-p156634.json"] = pretty(await client.get(ROUTE, headers=ANA))
            found["evidence-research-item-p156634-star.json"] = pretty(await client.get(
                "/api/evidence", headers=ANA, params={"id": STAR, "asof": TODAY.isoformat()}))
        return found

    try:
        return asyncio.run(story())
    finally:
        database.close()


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        for name, text in answers(Path(folder)).items():
            (OUT / name).write_text(text)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
