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
from research_world import SEED_RUN_ID, seed_kit, seeded_copy, with_live_sources

from strata.agent import judge as judges
from strata.agent.judge import Judgement, Question, Source
from strata.agent.verifier import find_quote
from strata.config import load_research, load_thresholds
from strata.lakehouse.engine import DuckDBEngine
from strata.research import run as research_run
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
    """The app on one DuckDB file that holds the fixture and the app's own tables, with the recorded writer and judge.
    It reads the sources live unless live_sources is False."""

    def __init__(self, database: Path, kit, writer=None, live_sources: bool = True, judge=None):
        self.database = DuckDBEngine.open(database)
        self.writer = writer or RecordedWriter(ANSWER)
        self.judge = judge or RecordedJudge(JUDGED)
        numbers = iter(range(1, 100))

        @contextmanager
        def reading(viewer):
            yield self.database.cursor()

        self.app = create_app(engine_for=reading, research=ResearchStore(self.database.cursor),
                              research_kit=lambda: kit, research_writer=lambda: self.writer,
                              judge=self.judge, today=lambda: TODAY, thresholds=with_live_sources(live_sources),
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

    assert call(world.app, "GET", ROUTE).json() == {"status": "none", "project_id": "P156634", "live_sources": True}
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


def no_reading_kit():
    """A kit whose facts and readers fail the test if a run calls them, counting the calls."""
    calls = []

    def refuse(*arguments):
        calls.append(arguments)
        raise AssertionError("With live_sources false, a run reads no source.")

    sources = [source for source in load_research().values() if source.enabled]
    kit = research_run.Kit(facts=refuse, sources=lambda: sources, read=refuse, fetch=None)
    return kit, calls


def test_with_live_sources_off_a_post_reads_no_source_and_writes_the_brief_from_the_stored_run(seeded):
    kit, calls = no_reading_kit()
    world = World(seeded, kit, live_sources=False)

    sent = world.research(reuse=False)

    assert calls == []
    # The same source steps as a live run, in its order, each done with its count and the day the stored run read it.
    enabled = [key for key, source in load_research().items() if source.enabled]
    done = [data for kind, data in sent if kind == "step" and data["kind"] == "source" and data["status"] != "running"]
    assert [step["source"] for step in done] == enabled
    isr = next(step for step in done if step["source"] == "isr_narrative")
    assert (isr["status"], isr["items"], isr["note"], isr["stored_on"]) == ("done", 7, "read on November 5, 2026",
                                                                           "2026-11-05")
    assert ("source-gdelt_news", "not_reached") in steps(sent)
    # The writer and the checks run live on the stored items, and their brief is the one GET returns.
    assert ("writing", "done") in steps(sent) and ("checking", "done") in steps(sent)
    assert sent[-1][1]["status"] == "written" and len(world.writer.calls) == 1
    kept = call(world.app, "GET", ROUTE).json()
    assert kept["run_id"] == SEED_RUN_ID and kept["live_sources"] is False


def test_with_live_sources_off_and_no_stored_run_the_run_ends_not_fetched_and_get_stays_none(fresh):
    kit, calls = no_reading_kit()
    world = World(fresh, kit, live_sources=False)

    sent = world.research(reuse=False)

    assert calls == []
    assert ("error", {"code": "not_fetched"}) in sent and sent[-1][1]["status"] == "stopped"
    assert call(world.app, "GET", ROUTE).json() == {"status": "none", "project_id": "P156634", "live_sources": False}


class FailingWriter:
    name = "a writer that fails"

    def write(self, *arguments):
        from strata.research.writer import WriterError

        raise WriterError("The model did not answer.")


class JudgeThatStops(RecordedJudge):
    """The recorded judge, until stopped is set: then it does not answer."""

    stopped = False

    def judge(self, questions):
        from strata.agent.judge import JudgeError

        if self.stopped:
            raise JudgeError("The judge did not answer.")
        return super().judge(questions)


def test_with_live_sources_off_a_writer_that_fails_keeps_the_stored_brief_and_ends_done_with_no_error(seeded):
    kit, _ = no_reading_kit()
    world = World(seeded, kit, live_sources=False)
    stored = world.research()[-1][1]["brief"]
    world.writer = FailingWriter()

    sent = world.research()

    assert not [data for kind, data in sent if kind == "error"]
    writing = [data for kind, data in sent if kind == "step" and data["id"] == "writing"][-1]
    assert (writing["status"], writing["kept_from"]) == ("done", "2026-11-05")
    assert writing["label"] == "Writing: kept the brief of November 5, 2026"
    assert sent[-1][0] == "done" and sent[-1][1]["status"] == "kept"
    assert sent[-1][1]["brief"]["headline"] == stored["headline"]


def test_with_live_sources_off_a_judge_that_fails_keeps_the_stored_brief(seeded):
    kit, _ = no_reading_kit()
    world = World(seeded, kit, live_sources=False, judge=JudgeThatStops(JUDGED))
    world.research()
    world.judge.stopped = True

    sent = world.research()

    assert not [data for kind, data in sent if kind == "error"]
    assert sent[-1][1]["status"] == "kept"
    assert call(world.app, "GET", ROUTE).json()["checks"]["sentences"]["removed"] == 0


def test_the_shipped_setting_is_the_demo_s_stored_runs_only():
    assert load_thresholds().value("research.live_sources") is False
    assert load_thresholds().value("research.stored_step_seconds") == 1.0


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


# ── Ticket 155: the first live brief's 18 removals ─────────────────────────

UKUNDA = "strata.research.item:P156634/procurement_notices/OP00471125"


class FactsJudge:
    """Check 4's judge as the planted sentences need it: a sentence holding words it was told are wrong does not follow,
    with the reason it was given; every other sentence follows. It keeps every question it was asked."""

    name = "facts judge"

    def __init__(self, wrong: dict[str, str] | None = None):
        self.wrong, self.calls = wrong or {}, []

    def judge(self, questions):
        self.calls.append(list(questions))
        found = []
        for question in questions:
            reason = next((why for words, why in self.wrong.items() if words in question.sentence), None)
            found.append(Judgement(question.index, reason is None, reason or "Its facts follow from its items."))
        return found


def recorded_brief() -> dict:
    return json.loads(json.loads(ANSWER.read_text())["response"]["choices"][0]["message"]["content"])


def recording_of(brief: dict, folder: Path) -> RecordedWriter:
    answer = json.loads(ANSWER.read_text())
    answer["response"]["choices"][0]["message"]["content"] = json.dumps(brief)
    path = folder / "planted.json"
    path.write_text(json.dumps(answer))
    return RecordedWriter(path)


def claim(sentence: str, kind: str, evidence_ids: list[str], numbers=(), dates=()) -> dict:
    return {"sentence": sentence, "kind": kind, "evidence_ids": evidence_ids, "numbers": list(numbers),
            "dates": list(dates), "quote": None}


def test_the_judge_is_told_a_question_s_facts_are_judged_and_the_question_itself_is_prism_s():
    source = (Source(UKUNDA, "Direct Selection"),)
    body = judges.request_body("draft", [Question(0, "Why was it awarded by direct selection?", source, facts_only=True),
                                         Question(1, "It was awarded by direct selection.", source)])

    system, sent = body["messages"][0]["content"], json.loads(body["messages"][1]["content"])
    assert "facts_only" in system and "Prism's own" in system and "not judged" in system
    assert sent["sentences"][0]["facts_only"] is True and "facts_only" not in sent["sentences"][1]


def test_a_question_is_kept_when_its_facts_hold_and_removed_with_the_judge_s_reason_when_one_is_wrong(fresh, kit,
                                                                                                      tmp_path):
    brief = recorded_brief()
    holds = "Ask why the Ukunda solar system contract, awarded by direct selection, runs for 425 Day(s)."
    wrong = "Ask why the Northern Water Works Development Agency awarded the Ukunda solar system by direct selection."
    brief["questions"][1]["sentences"] += [claim(holds, "advice", [UKUNDA], ["425"]), claim(wrong, "advice", [UKUNDA])]
    reason = "The Ukunda notice is the Coast Water Works' contract, not the Northern Water Works Development Agency's."
    judge = FactsJudge({"Northern Water Works Development Agency awarded the Ukunda": reason})
    world = World(fresh, kit, writer=recording_of(brief, tmp_path), judge=judge)

    sent = world.research()

    removed = {data["sentence"]: data for kind, data in sent if kind == "removed"}
    assert list(removed) == [wrong]
    assert removed[wrong]["reasons"] == [{"check": 4, "code": "not_supported", "text": reason}]
    question = sent[-1][1]["brief"]["questions"][1]
    assert holds in [sentence["text"] for sentence in question["sentences"]]
    asked = {question.sentence: question for question in judge.calls[0]}
    advice = [recorded_brief()["bottom_line"][0]["sentence"], holds, wrong]
    assert all(asked[sentence].facts_only for sentence in advice)
    assert not asked[recorded_brief()["headline"]["sentence"]].facts_only


SARMAN = "strata.research.item:P156634/procurement_notices/OP00474946"
BIG3 = "strata.research.item:P156634/outlet_feeds/595f89b9956ceda3"


def test_a_development_stating_a_notice_s_award_date_is_kept_because_the_date_is_a_field(fresh, kit, tmp_path):
    brief = recorded_brief()
    # Two of the first live brief's sentences removed by check 1, word for word: a date the notice prints only as
    # "2026/06/22", and the 3 of the outlet's name, Big3Africa.
    award = ("A World Bank procurement notice published on October 13, 2026 showed an RFB award for equipping "
             "exploratory boreholes at Sarman - Tarbaj Water Supply Project in Wajir County, with award notification "
             "issued on June 22, 2026, a 90 Day(s) contract duration, and a signed contract price of KES 166668894.48.")
    big3 = ("Big3Africa reported on January 20, 2026 that the Baricho Water Solarisation Plant financed under the project "
            "was a Sh670 million installation that started in October 2025 and was scheduled for completion by March "
            "31, 2026, with phase one reported at 60 percent complete.")
    quoted = 'The Sarman - Tarbaj award notice reads "Date Notification of Award Issued (YYYY/MM/DD) 2026/06/22".'
    brief["developments"][0]["sentences"] += [claim(award, "record", [SARMAN], ["90", "166668894.48"],
                                                    ["October 13, 2026", "June 22, 2026"]),
                                              claim(quoted, "record", [SARMAN])]
    brief["developments"].append({"date": "2026-01-20", "date_known": True,
                                  "sentences": [claim(big3, "record", [BIG3], ["670", "60"])]})
    world = World(fresh, kit, writer=recording_of(brief, tmp_path), judge=FactsJudge())

    sent = world.research()

    assert [data["sentence"] for kind, data in sent if kind == "removed"] == []
    kept = {data["text"]: data for kind, data in sent if kind == "sentence"}
    assert {"text": "June 22, 2026", "evidence_id": SARMAN} in kept[award]["dates"]
    assert kept[award]["kind"] == "record" and quoted in kept and big3 in kept
    items = {item["evidence_id"]: item for item in json.loads(world.writer.calls[0])["items"]}
    assert items[SARMAN]["notice"]["award_notification_date"] == "2026-06-22"


def test_the_writer_is_told_to_quote_a_date_or_number_found_only_in_an_item_s_words_or_leave_it_out():
    from strata.research.writer import instructions

    told = " ".join(instructions().split())
    assert "notice: the notice's own dates as fields" in told
    assert ("A date or number found only in an item's words, not in its fields or the summary, must be quoted word for "
            "word in the sentence") in told
    assert "or left out" in told


def test_a_could_not_see_sentence_citing_the_run_s_coverage_record_is_kept(fresh, kit, tmp_path):
    brief = recorded_brief()
    gdelt = "strata.research.coverage:research-0001/gdelt_news"
    said = "GDELT limited calls from this network, so the run read no GDELT news."
    brief["could_not_see"] = [claim(said, "record", [gdelt]), *brief["could_not_see"][1:]]
    judge = FactsJudge()
    world = World(fresh, kit, writer=recording_of(brief, tmp_path), judge=judge)

    sent = world.research()

    assert [data["sentence"] for kind, data in sent if kind == "removed"] == []
    assert said in [sentence["text"] for sentence in sent[-1][1]["brief"]["could_not_see"]]
    [asked] = [question for question in judge.calls[0] if question.sentence == said]
    record = json.loads(asked.sources[0].text)
    assert (asked.sources[0].evidence_id, record["reached"], record["note"]) == (
        gdelt, False, "GDELT limited calls from this network.")
    evidence = {data["id"]: data for kind, data in sent if kind == "evidence"}
    assert evidence[gdelt]["row"]["source_key"] == "gdelt_news"
    written = json.loads(world.writer.calls[0])
    assert gdelt in [record["evidence_id"] for record in written["coverage_records"]]
    from strata.research.writer import instructions

    assert "could_not_see sentence cites the coverage record" in " ".join(instructions().split())
