"""The server shell at seam 3: its health, identity and stream routes, driven over HTTP.

The recorded responses in tests/fixtures/api are written by hand once. The server must
match them, and the web app's tests serve the same files from their mocked API.
"""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from strata.harness.turn import Event
from strata.server.app import create_app

RECORDED = Path(__file__).parent / "fixtures" / "api"

ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}
BEN = {
    "X-Forwarded-Email": "ben.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ben Example",
    "X-Forwarded-User": "4022@1984",
    "X-Forwarded-Access-Token": "token-for-ben-only",
}


def events(body):
    """Parse a text/event-stream body into (type, data) pairs, keeping comment lines as ("comment", text)."""
    parsed = []
    for block in body.strip().split("\n\n"):
        kind, data = "message", None
        for line in block.splitlines():
            if line.startswith(":"):
                parsed.append(("comment", line[1:].strip()))
            elif line.startswith("event: "):
                kind = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if data is not None:
            parsed.append((kind, data))
    return parsed


def call(app, method, path, **kwargs):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(go())


def ask(app, question, headers=None):
    return call(app, "POST", "/api/ask", json={"question": question}, headers=headers or {})


def test_the_server_answers_its_health_route():
    response = call(create_app(), "GET", "/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_the_identity_route_names_the_viewer_the_app_forwarded():
    response = call(create_app(), "GET", "/api/me", headers=ANA)

    assert response.status_code == 200
    assert response.json() == json.loads((RECORDED / "me.json").read_text())
    assert "token-for-ana-only" not in response.text


def test_the_identity_route_says_when_no_one_signed_in():
    response = call(create_app(), "GET", "/api/me")

    assert response.json() == {"email": None, "name": None, "signed_in": False, "has_token": False, "staff": False,
                               "agency": None, "own_view": "staff"}


def test_with_no_agent_the_stream_says_so_and_ends():
    app = create_app(new_run_id=lambda: "run-0001")

    response = ask(app, "Why were works contracts in P130164 advertised again?", ANA)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == (RECORDED / "ask-no-agent.sse").read_text()


def test_overlapping_questions_from_two_viewers_each_run_as_their_own_viewer():
    async def runner(turn):
        for step in range(3):
            await asyncio.sleep(0.01)
            yield Event("step", {"text": f"Step {step} for {turn.viewer.email} with {turn.viewer.token}"})

    app = create_app(runner=runner)

    async def both():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await asyncio.gather(
                client.post("/api/ask", json={"question": "First"}, headers=ANA),
                client.post("/api/ask", json={"question": "Second"}, headers=BEN),
            )

    for_ana, for_ben = asyncio.run(both())

    assert "ana.example@worldbank.org" in for_ana.text and "token-for-ana-only" in for_ana.text
    assert "ben.example" not in for_ana.text and "token-for-ben-only" not in for_ana.text
    assert "ben.example@worldbank.org" in for_ben.text and "token-for-ben-only" in for_ben.text
    assert "ana.example" not in for_ben.text and "token-for-ana-only" not in for_ben.text


def test_evidence_that_came_back_in_one_turn_is_not_there_in_the_next():
    async def runner(turn):
        if turn.question == "First":
            turn.facts.record("strata.silver.plan_rows:KE-NWWDA-541055-CW-RFB", {"process_status": "Pending Implementation"})
        yield Event("step", {"came_back": turn.facts.came_back("strata.silver.plan_rows:KE-NWWDA-541055-CW-RFB")})

    app = create_app(runner=runner)

    first, second = ask(app, "First"), ask(app, "Second")

    assert events(first.text)[0] == ("step", {"came_back": True})
    assert events(second.text)[0] == ("step", {"came_back": False})


def test_a_run_that_breaks_ends_with_an_error_event_and_keeps_its_details_private():
    async def runner(turn):
        yield Event("step", {"text": "Looking up the plan"})
        raise RuntimeError("the warehouse password is not-for-viewers")

    response = ask(create_app(runner=runner, new_run_id=lambda: "run-0002"), "Check the plan")

    assert events(response.text) == [
        ("step", {"text": "Looking up the plan"}),
        ("error", {"code": "internal"}),
        ("done", {"run_id": "run-0002"}),
    ]
    assert "not-for-viewers" not in response.text


def test_a_slow_run_keeps_the_connection_alive():
    async def runner(turn):
        await asyncio.sleep(0.2)
        yield Event("step", {"text": "Done thinking"})

    response = ask(create_app(runner=runner, heartbeat_seconds=0.02), "Take your time")

    parsed = events(response.text)
    assert ("comment", "keep-alive") in parsed
    assert parsed[-2:][0] == ("step", {"text": "Done thinking"})


@pytest.mark.parametrize("body", [{}, {"question": ""}])
def test_a_request_without_a_question_is_refused_before_any_stream(body):
    response = call(create_app(), "POST", "/api/ask", json=body)

    assert response.status_code == 422
    assert not response.headers["content-type"].startswith("text/event-stream")
