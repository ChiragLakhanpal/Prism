"""The mission brief at seam 3: written, checked and exported through the draft routes (ticket 37, criterion 6).

"Add to mission brief" on a Following row posts {"kind": "mission_brief", "project_id": ...} to /api/drafts. The
write-the-mission-brief workflow reads project_records and check_plan as the viewer, its writer (the scripted
writer, replaying tests/fixtures/agent/writers.toml) drafts the five parts, the verifier checks every sentence, and
the draft is saved in strata.ops. It then moves from Draft to Checked by you to Exported on its author's actions, and
the export makes a Word file with a heading for each part. Today is October 23, 2026, as in tests/test_drafts.py.

Expected values come from independent sources: the two contracts since ISR 19 and their amounts, and the credits,
from tests/ground_truth/values.toml.
"""

import asyncio
import datetime as dt
import io
import json
import tomllib
import zipfile
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.agent.scripted import WRITER_CASES, ScriptedAgent, load_cases
from strata.config import load_roles
from strata.drafts.store import DraftStore
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.server.evidence import OpenedLog
from strata.server.following import FollowStore

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
TODAY = dt.date(2026, 10, 23)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
GROUPS = {"4021@1984": ["users", "strata-team-kenya-water"]}
BRIEF = {"kind": "mission_brief", "project_id": "P156634"}
PARTS = ["plans", "awards", "ratings", "disbursement", "closing"]


def call(app, method, path, headers=None, **options):
    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


def events(text: str) -> list[tuple[str, dict]]:
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if lines:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found


@pytest.fixture
def briefing(fixture_db, tmp_path):
    state_db = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        catalog.build(engine)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    def make(case="mission-brief-p156634"):
        written = load_cases(WRITER_CASES)[case]
        numbers = iter(range(1, 100))
        clock = iter(dt.datetime(2026, 10, 23, 14, minute, tzinfo=dt.UTC) for minute in range(60))
        state = lambda: DuckDBEngine.open(state_db)  # noqa: E731
        return create_app(engine_for=reading, drafts=DraftStore(state), opened=OpenedLog(state),
                          follows=FollowStore(state), writers=lambda kind: ScriptedAgent(written),
                          access=Access(load_roles(), StaticGroups(GROUPS)), today=lambda: TODAY,
                          now=lambda: next(clock), new_draft_id=lambda: f"draft-{next(numbers):04d}",
                          new_run_id=lambda: "run-0001")
    return make


def write(app, key="key-1") -> tuple[list, str | None]:
    sent = events(call(app, "POST", "/api/drafts", ANA, json={**BRIEF, "idempotency_key": key}).text)
    made = [data["draft_id"] for kind, data in sent if kind == "draft"]
    return sent, made[0] if made else None


def test_add_to_mission_brief_writes_five_parts_with_numbers_from_tools_and_citations(briefing):
    app = briefing()

    sent, draft_id = write(app)
    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()

    assert [kind for kind, _ in sent if kind == "step"][:1] == ["step"] and draft_id
    assert draft["kind"] == "mission_brief" and draft["state"] == "draft"
    assert [note["key"] for note in draft["notes"]] == PARTS
    assert all(note["state"] == "written" and note["sentences"] for note in draft["notes"])
    assert draft["removed"] == []
    awards = next(note for note in draft["notes"] if note["key"] == "awards")
    signed = [next(field["value"] for field in row["fields"] if field["key"] == "signed_on") for row in awards["table"]]
    assert signed == [TRUTH["award-567630-signed"]["value"].isoformat(), TRUTH["award-565568-signed"]["value"].isoformat()]
    cited = {evidence for note in draft["notes"] for sentence in note["sentences"] for evidence in sentence["evidence_ids"]}
    assert cited <= set(draft["evidence"]) and "strata.gold.contract:1901323" in cited
    assert draft["checks"]["tools"] == ["project_records"]


def test_a_part_whose_sentences_all_fail_keeps_its_table_and_no_sentence(briefing):
    app = briefing("mission-brief-a-part-removed")

    _, draft_id = write(app)
    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    disbursement = next(note for note in draft["notes"] if note["key"] == "disbursement")

    assert disbursement["state"] == "abstained" and disbursement["sentences"] == []
    assert sorted(row["reference"] for row in disbursement["table"]) == ["IDA60290", "IDA60300"]
    assert {item["reason"] for item in draft["removed"]} == {"number_not_in_records", "id_not_returned"}


def test_the_brief_moves_through_the_draft_states_and_exports_a_word_file_with_its_five_parts(briefing):
    app = briefing()
    _, draft_id = write(app)

    held = call(app, "POST", f"/api/drafts/{draft_id}/export", ANA, json={"expected_state": "draft"})
    checked = call(app, "POST", f"/api/drafts/{draft_id}/check", ANA, json={"expected_state": "draft"}).json()
    exported = call(app, "POST", f"/api/drafts/{draft_id}/export", ANA, json={"expected_state": "checked"}).json()
    [word] = [file["name"] for file in exported["export"]["files"] if file["name"].endswith(".docx")]
    content = call(app, "GET", f"/api/drafts/{draft_id}/files/{word}", ANA).content
    document = zipfile.ZipFile(io.BytesIO(content)).read("word/document.xml").decode()

    assert held.status_code == 409 and checked["state"] == "checked" and exported["state"] == "exported"
    assert word == "mission-brief-P156634-2026-10-23.docx"
    assert "Mission brief for Water and Sanitation Development Project (P156634)" in document
    for heading in ("Latest Procurement Plans", "Awards since the last ISR", "Rating history", "Disbursement",
                    "Closing check"):
        assert heading in document
    assert "This brief is not a World Bank review, clearance or no-objection." in document
    assert exported["export"]["footnotes"] == exported["citations"]


def test_the_following_row_names_the_open_brief_its_author_started(briefing):
    app = briefing()
    call(app, "PUT", "/api/projects/P156634/follow", ANA)
    _, draft_id = write(app)

    [row] = call(app, "GET", "/api/following", ANA).json()["projects"]

    assert row["mission_brief"]["draft_id"] == draft_id
