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
from strata.harness.turn import TraceIds

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "agent"
CASES = FIXTURES / "cases.toml"
# The draft writers' cases, such as the review notes writer's (ticket 35), in the same shape.
WRITER_CASES = FIXTURES / "writers.toml"
# The package reader's cases (ticket 15): sentences it reads into the package form's fields.
PACKAGE_CASES = FIXTURES / "packages.toml"
# The criteria reader's cases (ticket 31): qualification criteria it reads into the item registry's items.
CRITERIA_CASES = FIXTURES / "criteria.toml"
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
    # A writer case (tests/fixtures/agent/writers.toml): the draft runtime's request, and planted notes,
    # each taking the place of the recorded note on the same activity.
    request: dict | None = None
    plant_notes: tuple[dict, ...] = ()
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
        if self.plant_claims or self.plant_notes:
            written = json.loads(output_text(answer))
            if self.plant_claims:
                written["claims"] += [copy.deepcopy(claim) for claim in self.plant_claims]
            for note in self.plant_notes:  # a planted note replaces the recorded note on its activity
                written["notes"] = [kept for kept in written["notes"]
                                    if kept.get("activity_reference_no") != note["activity_reference_no"]]
                written["notes"].append(copy.deepcopy(note))
            answer["output"] = [{"type": "message", "id": "msg_planted", "role": "assistant", "status": "completed",
                                 "content": [{"type": "output_text", "annotations": [],
                                              "text": json.dumps(written, ensure_ascii=False)}]}]
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
        plant_claims=tuple(case.get("plant_claims", [])), request=case.get("request"),
        plant_notes=tuple(case.get("plant_notes", [])), folder=folder) for case in cases}


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


# ── The recorded streams ─────────────────────────────────────────────────

# The run and trace ids the recorded streams in tests/fixtures/api carry, so they never change.
RECORDED_RUN_ID = "run-0001"
RECORDED_TRACES = TraceIds(application_insights="4bf92f3577b34da6a3ce929d0e0e4736",
                           mlflow="tr-0af7651916cd43dd8448eb211c80319c")
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"


def stream_text(case: Case, database: Path = FIXTURE_DB) -> str:
    """The answer stream the server sends for a case, run on the fixture database as a signed-in viewer."""
    import asyncio
    from contextlib import contextmanager

    import httpx

    from strata.agent.loop import answer_runner
    from strata.lakehouse.engine import DuckDBEngine
    from strata.server.app import create_app

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    app = create_app(runner=answer_runner(lambda turn: ScriptedAgent(case), engine_for, today=lambda: case.as_of),
                     new_run_id=lambda: RECORDED_RUN_ID, trace_ids=lambda: RECORDED_TRACES)

    async def ask():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            response = await client.post("/api/ask", headers={"X-Forwarded-User": "4021@1984"}, json={
                "question": case.question, "scope": case.scope, "asof": case.as_of.isoformat()})
            return response.text

    return asyncio.run(ask())


def failed_stream_text(code: str) -> str:
    """The answer stream the server sends when a run cannot answer, with the error code it gives: the agent
    did not respond (agent_unavailable), or a content filter stopped the question (content_filter)."""
    import asyncio

    import httpx

    from strata.harness.turn import RunError
    from strata.server.app import create_app

    async def runner(turn):
        raise RunError(code, f"A recorded stream for the screen tests: {code}.")
        yield

    app = create_app(runner=runner, new_run_id=lambda: RECORDED_RUN_ID, trace_ids=lambda: RECORDED_TRACES)

    async def ask():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            response = await client.post("/api/ask", headers={"X-Forwarded-User": "4021@1984"},
                                         json={"question": "Why were works contracts in P130164 advertised again?",
                                               "scope": "P130164"})
            return response.text

    return asyncio.run(ask())


def main(argv: list[str] | None = None) -> int:
    """Print a scripted case's answer stream, as tests/fixtures/api keeps it for the screen tests:

        uv run --frozen python -m strata.agent.scripted p130164-rebidding > tests/fixtures/api/ask-p130164-rebidding.sse

    or, with --error and a code, the stream of a run that could not answer:

        uv run --frozen python -m strata.agent.scripted --error agent_unavailable > tests/fixtures/api/ask-agent-unavailable.sse
    """
    import argparse
    import sys

    from strata.harness.turn import ERROR_CODES

    parser = argparse.ArgumentParser(prog="python -m strata.agent.scripted", description=main.__doc__.split("\n")[0])
    parser.add_argument("case", nargs="?", choices=sorted(load_cases()))
    parser.add_argument("--error", choices=ERROR_CODES, help="print the stream of a run that ends with this error")
    parser.add_argument("--database", type=Path, default=FIXTURE_DB, help="the fixture database (gates/build_fixture.py)")
    args = parser.parse_args(argv)
    if (args.case is None) == (args.error is None):
        parser.error("name a case or an --error code, not both")
    sys.stdout.write(failed_stream_text(args.error) if args.error else stream_text(load_cases()[args.case], args.database))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
