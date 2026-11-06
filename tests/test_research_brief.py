"""Ticket 148: the deep research run and its brief, through the routes.

POST /api/projects/{project_id}/research streams the run as /api/ask's events; GET returns the brief kept, or
{"status": "none"}. The sources give each source's result from ticket 147's demo seed (ops/research/seed.py, through
tests/research_world.py's seed_kit), and a reuse run writes from the seed's run kept in a copy of the fixture; the
writer replays the recorded answer for P156634 (tests/fixtures/agent/research/P156634.json) and the judge its recorded
answers (P156634.judged.json).
"""

import asyncio
import copy
import datetime as dt
import json
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from research_world import SEED_RUN_ID, seed_kit, seeded_copy

from strata.agent.verifier import find_quote
from strata.lakehouse.engine import DuckDBEngine
from strata.research import run as research_run
from strata.config import load_research
from strata.research.store import ResearchStore
from strata.research.writer import RecordedJudge, RecordedWriter
from strata.server.app import create_app

RECORDED = Path(__file__).parent / "fixtures" / "agent" / "research"
ANSWER, JUDGED = RECORDED / "P156634.json", RECORDED / "P156634.judged.json"
TODAY = dt.date(2026, 11, 5)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
ROUTE = "/api/projects/P156634/research"
SECTIONS = ["headline", "picture", "bottom_line", "developments", "by_site", "voices", "questions", "could_not_see"]


def call(app, method, path, headers=ANA, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers, **options)
    return asyncio.run(go())


def events(text: str) -> list[tuple[str, dict]]:
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if lines:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found


class World:
    """The app on one DuckDB file that holds the fixture and the app's own tables, with the recorded writer and judge."""

    def __init__(self, database: Path, kit, writer=None):
        self.database = DuckDBEngine.open(database)
        self.writer = writer or RecordedWriter(ANSWER)
        self.judge = RecordedJudge(JUDGED)
        numbers = iter(range(1, 100))

        @contextmanager
        def reading(viewer):
            yield self.database.cursor()

        self.app = create_app(engine_for=reading, research=ResearchStore(self.database.cursor),
                              research_kit=lambda: kit, research_writer=lambda: self.writer,
                              judge=self.judge, today=lambda: TODAY,
                              now=lambda: dt.datetime(2026, 11, 5, 10, 30, tzinfo=dt.UTC),
                              new_run_id=lambda: f"research-{next(numbers):04d}")

    def research(self, **body) -> list[tuple[str, dict]]:
        return events(call(self.app, "POST", ROUTE, json=body).text)


@pytest.fixture
def fresh(fixture_db, tmp_path):
    """A copy of the fixture with no research run in it."""
    import shutil

    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    return target


@pytest.fixture
def seeded(fixture_db, tmp_path):
    """A copy of the fixture with the run ticket 147's seed keeps for P156634 on November 5, 2026."""
    return seeded_copy(fixture_db, tmp_path)


@pytest.fixture
def kit(fixture_db):
    return seed_kit(fixture_db)


def steps(sent) -> list[tuple[str, str]]:
    return [(data["id"], data["status"]) for kind, data in sent if kind == "step"]


def test_the_run_streams_its_facts_one_step_per_source_writing_checking_and_done(fresh, kit):
    world = World(fresh, kit)

    sent = world.research()

    shown = steps(sent)
    sources = [f"source-{key}" for key, source in load_research().items() if source.enabled]
    assert shown[:2] == [("facts", "running"), ("facts", "done")]
    assert [step for step, status in shown if step.startswith("source-")] == [s for s in sources for _ in (1, 2)]
    assert ("source-gdelt_news", "not_reached") in shown and ("source-outlet_feeds", "done") in shown
    reached = [step for step in shown if step[0].startswith("source-")]
    after = shown[shown.index(reached[-1]) + 1:]
    assert [step for step in after if step[0] in ("writing", "checking")] == [
        ("writing", "running"), ("writing", "done"), ("checking", "running"), ("checking", "done")]
    kinds = [kind for kind, _ in sent]
    assert {"sentence", "evidence", "checks"} <= set(kinds)
    assert kinds[-1] == "done" and sent[-1][1]["status"] == "written"
    gdelt = next(data for kind, data in sent if kind == "step" and data["id"] == "source-gdelt_news"
                 and data["status"] == "not_reached")
    assert gdelt["note"] == "GDELT limited calls from this network."


def test_a_source_whose_reader_fails_is_a_step_not_reached_and_the_run_goes_on(fresh, fixture_db):
    world = World(fresh, seed_kit(fixture_db, fail="mastodon"))

    sent = world.research()

    assert ("source-mastodon", "not_reached") in steps(sent)
    assert sent[-1] == ("done", {**sent[-1][1], "status": "written"})


def test_the_brief_has_every_section_in_order_and_every_sentence_cites_an_item(fresh, kit):
    world = World(fresh, kit)

    brief = world.research()[-1][1]["brief"]

    assert [key for key in brief if key in SECTIONS] == SECTIONS
    assert brief["headline"]["text"].startswith("In the last months before its closing date")
    assert 4 <= len(brief["picture"]) <= 6 and 2 <= len(brief["bottom_line"]) <= 4
    assert 5 <= len(brief["questions"]) <= 7 and 1 <= len(brief["could_not_see"]) <= 3
    developments = brief["developments"]
    assert [entry["date"] for entry in developments[:3]] == ["2026-10-13", "2026-10-12", "2026-10-08"]
    dated = [entry["date"] for entry in developments if entry["date_known"]]
    assert dated == sorted(dated, reverse=True)
    assert developments[-1] == {**developments[-1], "date": None, "date_known": False, "label": "undated"}
    assert all(group["title"]["text"] and group["sentences"] for group in brief["by_site"])
    kanui = brief["voices"][0]
    assert kanui["quote"].startswith("We have had problems when water supply is disrupted")
    assert (kanui["who"], kanui["outlet"], kanui["date"]) == (
        "David Kanui, the water project coordinator at the Coast Water Works Development Agency", "The Star", "2026-01-14")
    assert brief["questions"][1]["lead"] == "The direct contracts."
    every = [brief["headline"], *brief["picture"], *brief["bottom_line"],
             *[s for group in developments for s in group["sentences"]],
             *[s for group in brief["by_site"] for s in (group["title"], *group["sentences"])],
             *[voice["sentence"] for voice in brief["voices"]],
             *[s for question in brief["questions"] for s in question["sentences"]], *brief["could_not_see"]]
    assert all(sentence["evidence_ids"] and sentence["kind"] in ("record", "quote", "summary", "advice")
               for sentence in every)


def test_on_the_seeded_run_the_verifier_keeps_every_sentence_with_its_numbers_dates_and_quotes_matched(fresh, kit):
    world = World(fresh, kit)

    sent = world.research()

    brief = sent[-1][1]["brief"]
    checks = brief["checks"]
    assert checks["sentences"] == {"written": 70, "kept": 70, "removed": 0}
    assert checks["numbers"]["total"] == checks["numbers"]["matched"] > 40
    assert checks["dates"]["total"] == checks["dates"]["matched"] > 40
    assert checks["quotes"]["total"] == checks["quotes"]["found"] > 5
    items = {data["id"]: data for kind, data in sent if kind == "evidence"}
    for voice in brief["voices"]:
        cited = items[voice["sentence"]["evidence_ids"][0]]["row"]
        assert find_quote(voice["quote"], cited["text"])
    assert len(world.judge.calls) == 1 and len(world.writer.calls) == 1


def planted(answer: dict) -> dict:
    """The recorded answer with a sentence whose number no item holds and a voice whose words its item does not print."""
    brief = json.loads(answer["response"]["choices"][0]["message"]["content"])
    brief["bottom_line"].append({
        "sentence": "Twelve contracts were awarded by direct selection in the 110 days before closing.",
        "kind": "record", "evidence_ids": ["strata.tools.research_evidence:P156634@2026-11-05"],
        "numbers": ["Twelve", "110"], "dates": [], "quote": None})
    voice = brief["voices"][0]["claim"]
    voice["sentence"] = voice["sentence"].replace("because of power being disconnected", "because the power was cut")
    voice["quote"]["text"] = voice["quote"]["text"].replace("because of power being disconnected", "because the power was cut")
    changed = copy.deepcopy(answer)
    changed["response"]["choices"][0]["message"]["content"] = json.dumps(brief)
    return changed


def test_the_verifier_removes_a_planted_number_and_a_misquote_with_their_reasons(fresh, kit, tmp_path):
    recording = tmp_path / "planted.json"
    recording.write_text(json.dumps(planted(json.loads(ANSWER.read_text()))))
    world = World(fresh, kit, writer=RecordedWriter(recording))

    sent = world.research()

    removed = {data["sentence"]: [reason["code"] for reason in data["reasons"]] for kind, data in sent if kind == "removed"}
    assert removed["Twelve contracts were awarded by direct selection in the 110 days before closing."] == ["number_not_in_records"]
    [misquote] = [codes for text, codes in removed.items() if "because the power was cut" in text]
    assert misquote == ["quote_not_on_page"]
    brief = sent[-1][1]["brief"]
    assert brief["checks"]["sentences"] == {"written": 71, "kept": 69, "removed": 2}
    assert [voice["quote"][:20] for voice in brief["voices"]][0] == "We have been dealing"
    assert all(removal["section"] in ("bottom_line", "voices") for removal in brief["removed"])


def test_get_returns_none_before_a_brief_and_the_kept_brief_after_without_a_model_call(fresh, kit):
    world = World(fresh, kit)

    assert call(world.app, "GET", ROUTE).json() == {"status": "none", "project_id": "P156634"}
    written = world.research()[-1][1]["brief"]
    first, second = call(world.app, "GET", ROUTE).json(), call(world.app, "GET", ROUTE).json()

    assert first == second
    assert first["status"] == "written" and first["headline"] == written["headline"]
    assert first["run_id"] == "research-0001" and first["checks"]["sentences"]["kept"] == 70
    assert len(world.writer.calls) == 1 and len(world.judge.calls) == 1


def test_reuse_writes_the_brief_from_the_seeded_run_without_reading_the_sources(seeded, fixture_db):
    world = World(seeded, seed_kit(fixture_db, fail="isr_narrative"))

    sent = world.research(reuse=True)

    assert ("source-isr_narrative", "done") in steps(sent) and ("source-gdelt_news", "not_reached") in steps(sent)
    assert sent[-1][1]["status"] == "written"
    assert call(world.app, "GET", ROUTE).json()["run_id"] == SEED_RUN_ID


def test_reuse_with_no_run_kept_says_not_fetched(fresh, kit):
    sent = World(fresh, kit).research(reuse=True)

    assert ("error", {"code": "not_fetched"}) in sent
    assert sent[-1][1]["status"] == "stopped"


def test_the_evidence_drawer_opens_a_research_item_with_its_source_link(seeded, kit):
    world = World(seeded, kit)
    item = "strata.research.item:P156634/outlet_feeds/24d1ca8a593f492b"

    opened = call(world.app, "GET", "/api/evidence", params={"id": item, "asof": "2026-11-05"}).json()

    assert opened["id"] == item and opened["kind"] == "record"
    assert opened["row"]["url"].startswith("https://www.the-star.co.ke/")
    assert opened["row"]["title"] == "Sh280m Kipevu wastewater treatment plant to be ready by October"


def test_the_tab_s_recorded_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """tests/record_research_api.py writes the answers the Deep research tab's screen tests serve (web/tests/
    research.spec.ts), from the brief written with reuse from the seeded run; the routes still answer with them."""
    from record_research_api import OUT, answers

    for name, text in answers(tmp_path, fixture_db).items():
        assert text == (OUT / name).read_text(), f"Record {name} again: uv run --frozen python tests/record_research_api.py"
