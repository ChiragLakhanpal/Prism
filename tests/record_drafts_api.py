"""Writes the draft routes' recorded answers in tests/fixtures/api from the server itself (ticket 35).

The screen tests serve these files from their mocked API, and tests/test_drafts.py checks that the server
still answers with them, so the draft screens and the server cannot drift apart. Build the fixture
database first, then run:

    uv run --frozen python tests/record_drafts_api.py

One story makes them all, on the fixture database as of October 23, 2026, with the scripted writer's cases
(tests/fixtures/agent/writers.toml), a fixed clock and fixed ids: Ana, on the Kenya water team, drafts
review notes on the NWWDA plan of October 9, 2026, Ben (her teammate) opens them and finds them from the
plan check, as Ana does, Ana checks and exports
them after opening one source, and drafts three more (one with an activity whose sentences all failed,
one with a refused activity, and one she discards). The writing streams of a draft no sentence of which
passed, and of a writer that did not answer, are recorded too.
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

from strata.agent.loop import AgentError  # noqa: E402
from strata.agent.scripted import WRITER_CASES, ScriptedAgent, load_cases  # noqa: E402
from strata.config import load_draft_kinds, load_roles  # noqa: E402
from strata.drafts import files  # noqa: E402
from strata.drafts.store import DraftStore  # noqa: E402
from strata.lakehouse import catalog  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.access import Access, StaticGroups  # noqa: E402
from strata.server.app import create_app  # noqa: E402
from strata.server.evidence import OpenedLog  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
BEN = {"X-Forwarded-Email": "ben.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ben Example",
       "X-Forwarded-User": "4022@1984", "X-Forwarded-Access-Token": "token-for-ben-only"}
CY = {"X-Forwarded-Email": "cy.example@worldbank.org", "X-Forwarded-Preferred-Username": "Cy Example",
      "X-Forwarded-User": "4023@1984", "X-Forwarded-Access-Token": "token-for-cy-only"}
GROUPS = {"4021@1984": ["strata-team-kenya-water"], "4022@1984": ["strata-team-kenya-water"]}
NWWDA = {"kind": "review_notes", "project_id": "P156634", "agency_id": "northern-water-works-development-agency",
         "plan_date": "2026-10-09"}
SECOND_ROW = "strata.silver.plan_rows:40132287/KE-NWWDA-229129-CW-RFB"


class Unavailable:
    name, version = "strata-review-notes-writer", None

    def respond(self, items, previous_response_id):
        raise AgentError("agent_unavailable", "A recorded stream for the screen tests.")


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    state_db = folder / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        catalog.build(engine)
    at = [dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC)]
    cases = load_cases(WRITER_CASES)
    writing = ["review-notes-nwwda-2026-10-09"]
    ids = iter(f"draft-{number:04d}" for number in range(1, 100))
    runs = iter(f"run-{number:04d}" for number in range(1, 100))

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(FIXTURE_DB, read_only=True) as engine:
            yield engine

    def state():
        return DuckDBEngine.open(state_db)

    def writer(kind):
        return Unavailable() if writing[0] == "unavailable" else ScriptedAgent(cases[writing[0]])

    app = create_app(engine_for=reading, drafts=DraftStore(state), opened=OpenedLog(state, now=lambda: at[0]),
                     writers=writer, access=Access(load_roles(), StaticGroups(GROUPS)),
                     today=lambda: dt.date(2026, 10, 23), now=lambda: at[0], new_draft_id=lambda: next(ids),
                     new_run_id=lambda: next(runs))

    def later(minutes: int):
        at[0] += dt.timedelta(minutes=minutes)

    async def story() -> dict[str, str]:
        found = {}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            async def write(case: str, key: str, **extra) -> str:
                writing[0] = case
                answer = await client.post("/api/drafts", headers=ANA, json={**NWWDA, "idempotency_key": key, **extra})
                return answer.text

            async def get(path: str, headers=ANA, **params) -> str:
                return json.dumps((await client.get(path, headers=headers, params=params)).json(), indent=2,
                                  ensure_ascii=False) + "\n"

            async def act(draft_id: str, action: str, expected: str) -> str:
                answer = await client.post(f"/api/drafts/{draft_id}/{action}", headers=ANA,
                                           json={"expected_state": expected})
                return json.dumps(answer.json(), indent=2, ensure_ascii=False) + "\n"

            found["drafts-write-review-notes.sse"] = await write("review-notes-nwwda-2026-10-09", "key-1")
            found["drafts-review-notes-draft.json"] = await get("/api/drafts/draft-0001")
            # The check line the evidence pack writes for this draft, which the page must write word for word
            # (src/strata/drafts/files.py and web/src/components/Checks.tsx state the same rule twice).
            kind = load_draft_kinds().kinds["review_notes"]
            checks = json.loads(found["drafts-review-notes-draft.json"])["checks"]
            found["drafts-check-line.txt"] = files.check_line(checks, kind) + "\n"
            found["drafts-review-notes-teammate.json"] = await get("/api/drafts/draft-0001", BEN)
            found["drafts-existing.json"] = await get("/api/drafts/existing", BEN, **{
                key: value for key, value in NWWDA.items()})
            found["drafts-existing-yours.json"] = await get("/api/drafts/existing", ANA, **{
                key: value for key, value in NWWDA.items()})
            # The plan check with no version in its address asks with no plan date, before it knows the version.
            found["drafts-existing-latest.json"] = await get("/api/drafts/existing", ANA, **{
                key: value for key, value in NWWDA.items() if key != "plan_date"})
            # Ben's own /api/me, for the screens that show Ana's draft to her teammate.
            found["drafts-me-teammate.json"] = await get("/api/me", BEN)
            later(2)
            found["drafts-review-notes-checked.json"] = await act("draft-0001", "check", "draft")
            later(2)
            await client.post("/api/evidence/opened", headers=ANA, json={"evidence_id": SECOND_ROW,
                                                                        "route": "/drafts/draft-0001"})
            later(2)
            found["drafts-review-notes-exported.json"] = await act("draft-0001", "export", "checked")
            later(10)
            await write("review-notes-one-activity-fails", "key-2")
            found["drafts-review-notes-partial.json"] = await get("/api/drafts/draft-0002")
            later(10)
            await write("review-notes-a-refused-activity", "key-3")
            found["drafts-review-notes-refused.json"] = await get("/api/drafts/draft-0003")
            later(2)
            await act("draft-0003", "check", "draft")
            later(10)
            await write("review-notes-nwwda-2026-10-09", "key-4")
            later(2)
            found["drafts-review-notes-discarded.json"] = await act("draft-0004", "discard", "draft")
            found["drafts-write-nothing-survived.sse"] = await write("review-notes-nothing-passes", "key-5")
            found["drafts-write-agent-unavailable.sse"] = await write("unavailable", "key-6")
            found["drafts-list.json"] = await get("/api/drafts")
            found["drafts-list-teammate.json"] = await get("/api/drafts", BEN)
            found["drafts-list-empty.json"] = await get("/api/drafts", CY)
            # Ticket 42: review notes asked for in French, and the identity route's answer for a link that asks for
            # French and for one that asks for a language I can't write in.
            later(10)
            written = await write("review-notes-nwwda-2026-10-09-fr", "key-7", lang="fr")
            french = next(json.loads(line[len("data: "):])["draft_id"] for line in written.splitlines()
                          if line.startswith("data: ") and '"draft_id"' in line)
            found["drafts-review-notes-fr.json"] = await get(f"/api/drafts/{french}")
            found["me-lang-fr.json"] = await get("/api/me", ANA, lang="fr")
            found["me-lang-unknown.json"] = await get("/api/me", ANA, lang="xx")
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
