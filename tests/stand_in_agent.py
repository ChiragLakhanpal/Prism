"""A stand-in for the Foundry agent in the full gate's offline tests (tests/test_benchmark.py, tests/test_full_gate.py).

The full gate asks each benchmark question of the live agent through /api/ask. Offline, StandIn plays the agent's
part in the Responses API's shape: it calls one tool with the arguments it is given, then writes one sentence citing
what came back, or it refuses with a key. Agrees is a judge that finds every sentence follows from its sources, so
only the scoring decides. Neither is the agent: they let the tests drive the route, the stream, the verifier and the
scoring exactly as the full gate does, with the tools on the fixture.
"""

from __future__ import annotations

import json

from strata.agent.judge import Judgement
from strata.evals.answers import arguments_of


def reply(output: list[dict], number: int) -> dict:
    return {"id": f"response-{number}", "output": output}


def said(claims: list[dict], refusal: dict | None = None) -> list[dict]:
    body = {"claims": claims, **({"refusal": refusal} if refusal else {})}
    return [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(body)}]}]


class StandIn:
    """One answer: call a tool once with the given arguments, then cite rows of its result by their place, or the
    evidence ids in cite_ids when given (falling back to the result's summary when it has no rows), or refuse."""

    name, version = "stand-in", "1"

    def __init__(self, tool=None, arguments=None, cite=(0,), refuse=None, cite_ids=None):
        self.tool, self.arguments, self.cite, self.refuse, self.cite_ids = tool, arguments, cite, refuse, cite_ids

    def respond(self, items, previous_response_id):
        outputs = [item for item in items if item.get("type") == "function_call_output"]
        if self.refuse:
            return reply(said([], {"key": self.refuse, "partial": False}), 1)
        if not outputs:
            return reply([{"type": "function_call", "call_id": "call-1", "name": self.tool,
                           "arguments": json.dumps(self.arguments)}], 1)
        result = json.loads(outputs[0]["output"])
        rows = result.get("rows") or []
        if self.cite_ids:
            cited = list(self.cite_ids)
        elif rows:
            cited = [rows[place]["evidence_id"] for place in self.cite if place < len(rows)]
        else:
            cited = [result["summary"]["evidence_id"]] if result.get("summary") else []
        return reply(said([{"sentence": "These are the records the tool returned.", "kind": "summary",
                            "evidence_ids": cited, "numbers": [], "dates": [], "quote": None}]), 2)


class Agrees:
    """A judge that finds every sentence follows from its sources."""

    name = "agrees"

    def judge(self, questions):
        return [Judgement(item.index, True, "") for item in questions]


def for_question(question: dict, engine, viewer) -> StandIn:
    """The stand-in's answer to any benchmark question: refuse a must-refuse question with its key, or call the
    question's tool with the question's own arguments and cite what the question expects."""
    if question["kind"] == "refusals":
        return StandIn(refuse=question["expected"]["refusal"])
    return StandIn(question["tool"], arguments_of(question, engine, viewer), cite_ids=question.get("cites"))
