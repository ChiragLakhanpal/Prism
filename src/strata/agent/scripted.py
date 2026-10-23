"""The scripted agent: seam 3's offline adapter, which replays the Foundry agent's recorded answers.

A scripted case (tests/fixtures/agent/cases.toml) is a question with its scope and as-of date, the
recording that answers it (tests/fixtures/agent/recorded/<recording>.json, the agent's responses through
the Responses API, in order), and what it plants: extra rounds of tool calls and extra claims, which are
added when the case is replayed and never written into the recording, so they survive a re-recording.

ScriptedAgent answers each request with the next response, as the live agent would. It also checks that
the loop talks to it the way the Responses API needs: each request continues the previous response and
answers every tool call that response asked for. A recording made for another question is refused, so a
changed case is re-recorded rather than replayed against the wrong answers.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from strata.agent.loop import function_calls, output_text

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "agent"
CASES = FIXTURES / "cases.toml"
RECORDINGS = FIXTURES / "recorded"


class ScriptError(AssertionError):
    """The loop asked the scripted agent something its recording does not answer."""


@dataclass(frozen=True)
class Case:
    id: str
    says: str
    question: str
    scope: str | None
    as_of: dt.date
    recording: str
    plant_rounds: tuple[tuple[dict, ...], ...] = ()
    plant_claims: tuple[dict, ...] = ()
    folder: Path = field(default=RECORDINGS, compare=False)

    @property
    def path(self) -> Path:
        return self.folder / f"{self.recording}.json"

    def recorded(self) -> dict:
        return json.loads(self.path.read_text())

    def responses(self) -> list[dict]:
        """The recording's responses with the case's plants: planted rounds of tool calls before the
        answer, and planted claims at the end of it."""
        responses = copy.deepcopy(self.recorded()["responses"])
        *rounds, answer = responses
        planted = [{"id": f"resp_planted_{number}", "object": "response", "status": "completed",
                    "output": [{"type": "function_call", "id": f"fc_planted_{number}_{place}",
                                "call_id": f"call_planted_{number}_{place}", "name": call["name"],
                                "arguments": json.dumps(call.get("arguments", {})), "status": "completed"}
                               for place, call in enumerate(calls, 1)]}
                   for number, calls in enumerate(self.plant_rounds, 1)]
        if self.plant_claims:
            claims = json.loads(output_text(answer))
            claims["claims"] += [copy.deepcopy(claim) for claim in self.plant_claims]
            answer["output"] = [{"type": "message", "id": "msg_planted", "role": "assistant", "status": "completed",
                                 "content": [{"type": "output_text", "annotations": [],
                                              "text": json.dumps(claims, ensure_ascii=False)}]}]
        return [*rounds, *planted, answer]


def load_cases(path: Path = CASES, recordings: Path | None = None) -> dict[str, Case]:
    """Every scripted case, by id."""
    with open(path, "rb") as handle:
        cases = tomllib.load(handle)["cases"]
    folder = recordings or path.parent / "recorded"
    return {case["id"]: Case(
        id=case["id"], says=case["says"], question=case["question"], scope=case.get("scope"), as_of=case["as_of"],
        recording=case["recording"],
        plant_rounds=tuple(tuple(planted["calls"]) for planted in case.get("plant_rounds", [])),
        plant_claims=tuple(case.get("plant_claims", [])), folder=folder) for case in cases}


class ScriptedAgent:
    """Answers from a case's recording, in order."""

    def __init__(self, case: Case):
        recording = case.recorded()
        asked = (recording["question"], recording["scope"], recording["as_of"])
        if asked != (case.question, case.scope, case.as_of.isoformat()):
            raise ScriptError(f"The recording {case.recording} answers {asked}, not case {case.id}'s question. "
                              f"Re-record it: uv run --script ops/agent/record.py --env-file .env")
        self.name = recording["agent"]["name"]
        self.version = recording["agent"].get("version")
        self.case = case
        self.responses = case.responses()
        self.received: list[dict] = []

    def respond(self, items: list[dict], previous_response_id: str | None) -> dict:
        turn = len(self.received)
        self.received.append({"input": copy.deepcopy(items), "previous_response_id": previous_response_id})
        if turn >= len(self.responses):
            raise ScriptError(f"Case {self.case.id} was asked for answer {turn + 1}, and it has "
                              f"{len(self.responses)}.")
        if turn:
            before = self.responses[turn - 1]
            if previous_response_id != before["id"]:
                raise ScriptError(f"Request {turn + 1} continued {previous_response_id}, not {before['id']}.")
            asked = [call["call_id"] for call in function_calls(before)]
            answered = [item.get("call_id") for item in items if item.get("type") == "function_call_output"]
            if answered != asked:
                raise ScriptError(f"Request {turn + 1} answered the tool calls {answered}, not {asked}.")
        return copy.deepcopy(self.responses[turn])
