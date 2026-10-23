"""The answer contract at seam 3: a question goes in over HTTP and a checked, cited answer streams back.

The scripted agent replays the Foundry agent's recorded answers (tests/fixtures/agent), and every tool
it asks for runs through the tool registry on the fixture database, as the viewer. The verifier runs in
the stream on every answer. Expected passages, numbers and quotes come from the ICR of October 10, 2019
(tests/ground_truth/values.toml, icr-para-54), never from the code under test.
"""

import asyncio
import datetime as dt
import json
import re
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.agent.loop import answer_runner
from strata.agent.scripted import ScriptedAgent, load_cases
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

RECORDED = Path(__file__).parent / "fixtures" / "api"
ICR_54 = "strata.gold.passage:31525018/v1/54"
TODAY = dt.date(2026, 10, 23)
ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}


def events(body):
    """The stream's (type, data) pairs, in order, without its keep-alive comments."""
    parsed = []
    for block in body.strip().split("\n\n"):
        kind, data = "message", None
        for line in block.splitlines():
            if line.startswith("event: "):
                kind = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if data is not None:
            parsed.append((kind, data))
    return parsed


def of(parsed, kind):
    return [data for found, data in parsed if found == kind]


@pytest.fixture
def ask_case(fixture_db):
    """Ask a scripted case's question over HTTP. Returns the stream's events and the scripted agent."""
    def ask(case_id, asof=None, today=TODAY, **app_options):
        case = load_cases()[case_id]
        agents = []

        def agent_for(turn):
            agents.append(ScriptedAgent(case))
            return agents[-1]

        @contextmanager
        def engine_for(viewer):
            with DuckDBEngine.open(fixture_db, read_only=True) as engine:
                yield engine

        app = create_app(runner=answer_runner(agent_for, engine_for, today=lambda: today),
                         new_run_id=lambda: "run-0001", **app_options)

        async def go():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                return await client.post("/api/ask", headers=ANA, json={
                    "question": case.question, "scope": case.scope, "asof": (asof or case.as_of).isoformat()})

        response = asyncio.run(go())
        assert response.status_code == 200
        return events(response.text), agents[0]
    return ask


def test_the_p130164_question_streams_steps_then_an_answer_citing_icr_paragraph_54(ask_case):
    parsed, _ = ask_case("p130164-rebidding")

    kinds = [kind for kind, _ in parsed]
    assert kinds[0] == "step" and kinds.index("sentence") > kinds.index("step")
    searched = [step for step in of(parsed, "step") if step.get("tool") == "search_passages"]
    assert [step["status"] for step in searched] == ["running", "done"]
    sentences = of(parsed, "sentence")
    citing_54 = [sentence for sentence in sentences if ICR_54 in sentence["evidence_ids"]]
    assert any("108 of 328" in sentence["text"] for sentence in citing_54)
    paragraph_54 = next(evidence for evidence in of(parsed, "evidence") if evidence["id"] == ICR_54)
    assert (paragraph_54["kind"], paragraph_54["row"]["pdf_page"], paragraph_54["row"]["paragraph"]) == (
        "passage", 23, "54")
    highlight = paragraph_54["highlights"][0]
    assert paragraph_54["row"]["text"][highlight["start"]:highlight["end"]] == (
        "108 of 328 cases had to go through rebidding")
    checks = of(parsed, "checks")[0]
    assert checks["numbers"]["total"] > 0 and checks["numbers"]["matched"] == checks["numbers"]["total"]
    assert checks["quotes"]["total"] > 0 and checks["quotes"]["found"] == checks["quotes"]["total"]
    assert of(parsed, "removed") == []
    assert kinds[-1] == "done"


def test_a_number_no_record_holds_is_removed_with_the_copy_files_reason(ask_case):
    parsed, _ = ask_case("p130164-number-with-no-record")

    removed = of(parsed, "removed")
    assert [(item["sentence"], item["reason"]) for item in removed] == [
        ("Bids were usually opened within 45 days.", "number_not_in_records")]
    assert copy_reasons()[removed[0]["reason"]] == "No record supports this number."
    assert "45 days" not in " ".join(sentence["text"] for sentence in of(parsed, "sentence"))
    checks = of(parsed, "checks")[0]
    # The base answer states 108 and 328, both on ICR paragraph 54; the planted sentence adds 45.
    assert checks["numbers"] == {"total": 3, "matched": 2}
    assert checks["sentences"] == {"written": 4, "kept": 3, "removed": 1}


def test_a_sentence_citing_a_source_no_tool_returned_this_turn_is_removed(ask_case):
    parsed, _ = ask_case("p130164-source-not-returned")

    removed = of(parsed, "removed")
    assert [(item["sentence"], item["reason"]) for item in removed] == [
        ("Some works started before their forest clearance came through.", "id_not_returned")]
    assert removed[0]["reasons"][0]["text"] == "strata.gold.passage:31525018/v1/71"
    assert copy_reasons()["id_not_returned"] == "It cited a source I did not retrieve for this question."
    assert "strata.gold.passage:31525018/v1/71" not in [evidence["id"] for evidence in of(parsed, "evidence")]
    checks = of(parsed, "checks")[0]
    assert checks["sources"] == {"total": 3, "returned": 2}
    assert checks["sentences"] == {"written": 4, "kept": 3, "removed": 1}


def test_a_quote_that_is_not_word_for_word_on_its_page_is_removed(ask_case):
    parsed, _ = ask_case("p130164-misquote")

    removed = of(parsed, "removed")
    assert [(item["sentence"], item["reason"]) for item in removed] == [
        ('The report puts it plainly: "108 of 328 works contracts had to be bid again".', "quote_not_on_page")]
    assert [reason["code"] for reason in removed[0]["reasons"]] == ["quote_not_on_page"]
    assert copy_reasons()["quote_not_on_page"] == "The quote is not on the page it cites."
    checks = of(parsed, "checks")[0]
    assert checks["quotes"] == {"total": 3, "found": 2}
    # The misquote's two numbers are not backed by a quote that is on its page.
    assert checks["numbers"] == {"total": 4, "matched": 2}


def test_a_fourth_round_of_tool_calls_gets_no_results_and_the_answer_rests_on_the_first_three(ask_case):
    parsed, agent = ask_case("p130164-fourth-round")

    ran = [step for step in of(parsed, "step") if step["kind"] == "tool" and step["status"] == "done"]
    assert len(ran) == 3
    fourth = [json.loads(item["output"]) for item in agent.received[4]["input"]]
    assert fourth == [{"not_run": "round_limit", "tool_rounds": 3}]
    removed = of(parsed, "removed")
    assert [(item["reason"], item["reasons"][0]["text"]) for item in removed] == [
        ("id_not_returned", "strata.gold.passage:31525018/v1/88")]
    assert len(of(parsed, "sentence")) == 3


def test_the_agent_gets_no_date_after_its_as_of_date_from_a_tool_that_abstained(ask_case):
    parsed, agent = ask_case("p156634-plan-not-yet-public")

    asked = json.loads(agent.received[0]["input"][0]["content"])
    assert (asked["question"], asked["scope"], asked["as_of"]) == (
        "Check the Northern Water Works Development Agency's Procurement Plan of October 9, 2026 for P156634.",
        "P156634", "2026-10-01")
    result = agent.received[1]["input"][0]["output"]
    assert json.loads(result)["abstention"]["reason"] == "version_not_public"
    # The plan is dated, and became public, on October 9, 2026 (values.toml, plan_date of the demo plan).
    assert "2026-10-09" not in result
    assert [sentence["index"] for sentence in of(parsed, "sentence")] == [0]


def test_an_as_of_date_after_today_asks_as_of_today(ask_case):
    _, agent = ask_case("p130164-rebidding", asof=dt.date(2027, 3, 1), today=dt.date(2026, 10, 23))

    assert json.loads(agent.received[0]["input"][0]["content"])["as_of"] == "2026-10-23"
    assert json.loads(agent.received[1]["input"][0]["output"])["as_of"] == "2026-10-23"


def test_every_reason_the_verifier_gives_has_its_sentence_in_the_copy_file():
    from strata.agent.verifier import REASONS

    sentences = copy_reasons()
    assert [code for code in REASONS if not sentences.get(code)] == []


def copy_reasons():
    """The removed box's reason sentences, read from the copy file (web/src/copy.ts, removed.reasons)."""
    text = (Path(__file__).resolve().parents[1] / "web" / "src" / "copy.ts").read_text()
    removed = re.search(r"\n  removed: \{(.*?)\n  \},", text, re.S).group(1)
    reasons = re.search(r"reasons: \{(.*?)\n    \}", removed, re.S).group(1)
    return dict(re.findall(r'(\w+): "([^"]*)"', reasons))
