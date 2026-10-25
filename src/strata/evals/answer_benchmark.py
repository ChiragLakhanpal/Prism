"""The benchmark through the answer contract (ticket 33; spec, seam 3's live adapter).

run() asks each question of the benchmark file through /api/ask, the same route and stream the app serves, with
the agent agent_for gives each turn: the Foundry agent in the full gate (ops/evals/full_gate.py), a stand-in in
the offline tests. The tools run as the viewer on engine_for's engine, and the verifier checks every answer as it
does in the app. For each question it keeps the stream, every tool call with its whole result (the answer loop's
on_result), and the reference answer the question's tool gives on the same data (strata.evals.answers.reference),
then scores it (strata.evals.scoring). A question added to the file is asked in the next run with no other change.

The run's answers, with the passages and records they cite, are also what Foundry evaluates
(strata.evals.foundry_evaluation).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Iterable

from strata.agent.loop import Agent, answer_runner
from strata.dbx import Viewer
from strata.evals import answers, scoring
from strata.harness.sse import events as stream_events
from strata.harness.turn import Turn
from strata.server.engines import EngineFor

# Who the full gate asks as: the env file's token on the workspace, so its grants decide what the tools read.
GATE = Viewer(email="full-gate@strata", name="Strata's full gate", user_id="full-gate@strata")


def scope_of(question: dict) -> tuple[str | None, str | None]:
    """The page's scope chip and as-of date a question is asked with: its own, or its tool's arguments'. A question
    whose as_of is null is asked as of the day the gate runs."""
    arguments = question.get("arguments") or {}
    chip = question.get("scope") or arguments.get("project_id") or arguments.get("step_reference")
    as_of = question["as_of"] if "as_of" in question else arguments.get("as_of")
    return chip, as_of


def run(questions: list[dict], agent_for: Callable[[Turn], Agent], engine_for: EngineFor, judge=None,
        restricted: Iterable[str] = (), viewer: Viewer = GATE) -> list[tuple[scoring.Asked, scoring.Scored]]:
    import httpx

    from strata.server.app import create_app

    calls: dict[str, list[dict]] = defaultdict(list)

    def keep(turn: Turn, name: str, arguments: dict, result: dict) -> None:
        calls[turn.run_id].append({"tool": name, "arguments": arguments, "result": result})

    app = create_app(runner=answer_runner(agent_for, engine_for, on_result=keep), engine_for=engine_for, judge=judge)
    restricted = set(restricted)

    async def ask(question: dict) -> str:
        chip, as_of = scope_of(question)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.gate",
                                     timeout=600) as client:
            response = await client.post("/api/ask", headers={"X-Forwarded-User": viewer.user_id or "full-gate",
                                                              "X-Forwarded-Email": viewer.email or ""},
                                         json={"question": question["question"], "scope": chip, "asof": as_of})
            return response.text

    results = []
    for question in questions:
        text = asyncio.run(ask(question))
        events = stream_events(text)
        run_id = next((data.get("run_id") for kind, data in events if kind == "done"), None)
        reference, problem = None, None
        try:
            with engine_for(viewer) as engine:
                reference = answers.reference(question, engine, viewer)
        except Exception as error:  # a question written wrong, or a tool or query that failed for it alone
            problem = f"{type(error).__name__}: {error}"
        asked = scoring.Asked(question, events, text, calls.pop(run_id, []), reference, problem)
        results.append((asked, scoring.score(asked, restricted)))
    return results
