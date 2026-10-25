"""Asking a scripted case's question over HTTP, as the screen would (seam 3), for the tests of the six checks and
the refusals. The scripted agent replays the case's recording (tests/fixtures/agent), every tool it asks for
runs through the tool registry on the fixture database as the viewer, and the stream runs the verifier with the
case's recorded judge.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from contextlib import contextmanager
from dataclasses import dataclass

import httpx

from strata.agent.loop import answer_runner
from strata.agent.scripted import Case, ScriptedAgent, ScriptedJudge, app_engine_for, load_cases
from strata.harness.sse import events
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

TODAY = dt.date(2026, 10, 23)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}


@dataclass
class Asked:
    case: Case
    text: str  # the stream as the server sent it
    parsed: list[tuple[str, dict]]  # its events, in order
    agent: ScriptedAgent
    judge: ScriptedJudge

    def of(self, kind: str) -> list[dict]:
        return [data for found, data in self.parsed if found == kind]


def ask(fixture_db, case_id: str, today: dt.date = TODAY, **app_options) -> Asked:
    case = load_cases()[case_id]
    agents: list[ScriptedAgent] = []
    judge = app_options.pop("judge", None) or ScriptedJudge(case)

    def agent_for(turn):
        agents.append(ScriptedAgent(case))
        return agents[-1]

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = create_app(runner=answer_runner(agent_for, engine_for, today=lambda: today),
                     engine_for=app_engine_for(case, engine_for), judge=judge, new_run_id=lambda: "run-0001",
                     **app_options)

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.post("/api/ask", headers=ANA, json={
                "question": case.question, "scope": case.scope, "asof": case.as_of.isoformat()})

    response = asyncio.run(go())
    assert response.status_code == 200
    return Asked(case, response.text, events(response.text), agents[0], judge)
