"""The mission brief and Following at seam 3, through the HTTP routes (ticket 37, criteria 1, 5 and 6).

One story runs once for this module (tests/record_following_api.py): Ana, World Bank staff on the Kenya water team,
follows P156634 and P130164 and opens Following; then "Add to mission brief" posts {"kind": "mission_brief",
"project_id": "P156634"} to /api/drafts. The write-the-mission-brief workflow reads project_records and check_plan
as Ana, its writer (the scripted writer, replaying tests/fixtures/agent/writers.toml) drafts the five parts, the
verifier checks every sentence, and the draft is saved in strata.ops; Ana marks it as checked and exports it. The
screens' tests serve the story's answers, so they must stay word for word what the routes answer.

Expected values come from independent sources: the four signals from the ticket, the two contracts since ISR 19 and
their amounts from tests/ground_truth/values.toml.
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

from record_following_api import answers
from strata.agent.scripted import WRITER_CASES, ScriptedAgent, load_cases
from strata.config import load_roles
from strata.drafts.store import DraftStore
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "tests" / "fixtures" / "api"
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
PARTS = ["plans", "awards", "ratings", "disbursement", "closing"]


@pytest.fixture(scope="module")
def story(fixture_db, tmp_path_factory):
    files: dict[str, bytes] = {}
    found = answers(tmp_path_factory.mktemp("following-story"), fixture_db, files)
    return found, files


def read(story, name: str) -> dict:
    return json.loads(story[0][name])


def test_the_screens_recorded_answers_are_what_the_routes_answer(story):
    """The Following and mission brief screens' tests serve these files; the routes must still answer with them."""
    for name, text in story[0].items():
        assert text == (RECORDED / name).read_text(), f"{name} is out of date: uv run --frozen python tests/record_following_api.py"


def test_followings_p156634_row_needs_a_look_with_its_four_signals_and_the_closed_project_folds(story):
    following = read(story, "following-p156634.json")
    first, second = following["projects"]

    assert (first["project"]["project_id"], first["status"]) == ("P156634", "needs_a_look")
    assert [row["check"] for row in first["rows"]] == ["completion_passed", "above_estimate", "late_direct", "closing_moves"]
    assert (second["project"]["project_id"], second["status"]) == ("P130164", "closed")
    assert following["counts"]["shown"] == 1 and following["counts"]["folded"] == 1
    assert read(story, "following-asof-2024-06-30.json")["projects"][0]["status"] == "watch"
    # Follows are kept per viewer: Ben, also staff, follows nothing, and Ana's follow was saved before it was listed.
    assert read(story, "following-empty.json")["projects"] == []
    assert (read(story, "follow-off.json"), read(story, "follow-on.json")) == ({"following": False}, {"following": True})


def test_add_to_mission_brief_writes_five_parts_with_numbers_from_tools_and_citations(story):
    draft = read(story, "drafts-mission-brief-draft.json")

    assert draft["kind"] == "mission_brief" and draft["state"] == "draft"
    assert [note["key"] for note in draft["notes"]] == PARTS
    assert all(note["state"] == "written" and note["sentences"] for note in draft["notes"])
    assert draft["removed"] == []
    awards = next(note for note in draft["notes"] if note["key"] == "awards")
    signed = [next(field["value"] for field in row["fields"] if field["key"] == "signed_on") for row in awards["table"]]
    assert signed == [TRUTH["award-567630-signed"]["value"].isoformat(), TRUTH["award-565568-signed"]["value"].isoformat()]
    amounts = [next(field["value"] for field in row["fields"] if field["key"] == "signed_amount_usd") for row in awards["table"]]
    assert amounts[0] == f'{TRUTH["award-567630-amount"]["value"]:.2f}'
    cited = {evidence for note in draft["notes"] for sentence in note["sentences"] for evidence in sentence["evidence_ids"]}
    assert cited <= set(draft["evidence"]) and "strata.gold.contract:1901323" in cited
    assert draft["checks"]["tools"] == ["project_records"]


def test_the_brief_moves_through_the_draft_states_and_exports_a_word_file_with_its_five_parts(story):
    checked, exported = read(story, "drafts-mission-brief-checked.json"), read(story, "drafts-mission-brief-exported.json")
    [(name, word)] = story[1].items()
    document = zipfile.ZipFile(io.BytesIO(word)).read("word/document.xml").decode()

    assert checked["state"] == "checked" and exported["state"] == "exported"
    assert name == "mission-brief-P156634-2026-10-23.docx"
    assert "Mission brief for Water and Sanitation Development Project (P156634)" in document
    for heading in ("Latest Procurement Plans", "Awards since the last ISR", "Rating history", "Disbursement", "Closing check"):
        assert heading in document
    assert "This brief is not a World Bank review, clearance or no-objection." in document
    assert exported["export"]["footnotes"] == exported["citations"]


def test_the_following_row_names_the_open_brief_its_author_started(story):
    [row, _] = read(story, "following-with-brief.json")["projects"]

    assert row["mission_brief"]["draft_id"] == "draft-0001"


def test_a_part_whose_sentences_all_fail_keeps_its_table_and_no_sentence(fixture_db, tmp_path):
    state_db = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        catalog.build(engine)

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    ana = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
           "X-Forwarded-Access-Token": "token-for-ana-only"}
    written = load_cases(WRITER_CASES)["mission-brief-a-part-removed"]
    app = create_app(engine_for=reading, drafts=DraftStore(lambda: DuckDBEngine.open(state_db)),
                     writers=lambda kind: ScriptedAgent(written), access=Access(load_roles(), StaticGroups({})),
                     today=lambda: dt.date(2026, 10, 23), new_draft_id=lambda: "draft-0001")

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            await client.post("/api/drafts", headers=ana, json={"kind": "mission_brief", "project_id": "P156634"})
            return (await client.get("/api/drafts/draft-0001", headers=ana)).json()
    draft = asyncio.run(go())
    disbursement = next(note for note in draft["notes"] if note["key"] == "disbursement")

    assert disbursement["state"] == "abstained" and disbursement["sentences"] == []
    assert sorted(row["reference"] for row in disbursement["table"]) == ["IDA60290", "IDA60300"]
    assert {item["reason"] for item in draft["removed"]} == {"number_not_in_records", "id_not_returned"}
