"""The answer contract at seam 3: a question goes in over HTTP and a checked, cited answer streams back.

The scripted agent replays the Foundry agent's recorded answers (tests/fixtures/agent), and every tool
it asks for runs through the tool registry on the fixture database, as the viewer. The verifier runs in
the stream on every answer. Expected passages, numbers and quotes come from the ICR of October 10, 2019
(tests/ground_truth/values.toml, icr-para-54), never from the code under test.
"""

import asyncio
import json
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
    def ask(case_id, **app_options):
        case = load_cases()[case_id]
        agents = []

        def agent_for(turn):
            agents.append(ScriptedAgent(case))
            return agents[-1]

        @contextmanager
        def engine_for(viewer):
            with DuckDBEngine.open(fixture_db, read_only=True) as engine:
                yield engine

        app = create_app(runner=answer_runner(agent_for, engine_for), new_run_id=lambda: "run-0001", **app_options)

        async def go():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                return await client.post("/api/ask", headers=ANA, json={
                    "question": case.question, "scope": case.scope, "asof": case.as_of.isoformat()})

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
