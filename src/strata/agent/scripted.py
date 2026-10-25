"""The scripted agent: seam 3's offline adapter, which replays the Foundry agent's recorded answers.

A scripted case (tests/fixtures/agent/cases.toml) is a question with its scope and as-of date, the
recording that answers it (tests/fixtures/agent/recorded/<recording>.json, the agent's responses through
the Responses API, in order), and what it plants: extra rounds of tool calls and extra claims, which are
added when the case is replayed and never written into the recording, so they survive a re-recording.

ScriptedAgent answers each request with the next response, as the live agent would. It also checks that
the loop talks to it the way the Responses API needs: each request continues the previous response and
answers every tool call that response asked for. A recording made for another question is refused, so a
changed case is re-recorded rather than replayed against the wrong answers.

ScriptedJudge stands in for the judge of the verifier's check 4 (src/strata/agent/judge.py) in the same way:
it answers from the case's recorded judge answer (tests/fixtures/agent/judged/<case id>.json), made for the
sentences the case's answer sends it, plants included. It counts its calls, so a test can say the judge was
asked once, or not at all. A case with judge = "no_response" stands for a judge that did not respond, and
one with disagreements = "unavailable" for a data service that fails when the verifier's check 6 asks
get_disagreements, after the agent's own tools ran (app_engine_for).
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from strata.agent.judge import JudgeError, Judgement, Question, judgements
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
# The judge's recorded answers for the scripted cases, one file per case that asks the judge (ticket 24).
JUDGED = FIXTURES / "judged"
NO_RESPONSE = "no_response"
UNAVAILABLE = "unavailable"


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
    # What the judge of check 4 does: answers from its recording (None), or does not respond (no_response).
    judge: str | None = None
    # Whether check 6 can ask get_disagreements (None), or the data service fails then (unavailable).
    disagreements: str | None = None
    # The language the answer is asked for, as ?lang= gives it (ticket 42).
    language: str = "en"

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
            for note in self.plant_notes:  # a planted note replaces the recorded note on its activity, part or cell
                key = next(name for name in ("activity_reference_no", "cell_key", "part") if name in note)
                written["notes"] = [kept for kept in written["notes"] if kept.get(key) != note[key]]
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
        plant_notes=tuple(case.get("plant_notes", [])), folder=folder, judge=case.get("judge"),
        disagreements=case.get("disagreements"), language=case.get("language", "en")) for case in cases}


class ScriptedAgent:
    """Answers from a case's recording, in order."""

    def __init__(self, case: Case):
        recording = case.recorded()
        asked = (recording["question"], recording["scope"], recording["as_of"], recording.get("language", "en"))
        if asked != (case.question, case.scope, case.as_of.isoformat(), case.language):
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


class ScriptedJudge:
    """Answers check 4's questions from the case's recorded judge answer, and counts its calls."""

    name = "scripted judge"

    def __init__(self, case: Case, folder: Path = JUDGED):
        self.case, self.path = case, folder / f"{case.id}.json"
        self.calls: list[list[Question]] = []

    def recorded(self) -> dict | None:
        return json.loads(self.path.read_text()) if self.path.exists() else None

    def judge(self, questions: list[Question]) -> list[Judgement]:
        self.calls.append(list(questions))
        if self.case.judge == NO_RESPONSE:
            raise JudgeError(f"Case {self.case.id} stands for a judge that did not respond.")
        recording = self.recorded()
        asked = [question.sentence for question in questions]
        if recording is None or recording["asked"] != asked:
            raise ScriptError(f"Case {self.case.id} asked the judge about {asked}, and its recorded judge answer "
                              f"{self.path.name} answers {None if recording is None else recording['asked']}. "
                              f"Re-record it: uv run --script ops/agent/record.py --judge --env-file .env")
        return judgements(recording["response"], questions)


def app_engine_for(case: Case, engine_for):
    """The engine the app's verifier asks get_disagreements with: the runner's, or for a case with disagreements =
    "unavailable", one whose data service fails."""
    if case.disagreements != UNAVAILABLE:
        return engine_for

    from contextlib import contextmanager

    from strata.lakehouse.engine import EngineError

    @contextmanager
    def down(viewer):
        raise EngineError(f"Case {case.id} stands for a data service that fails when check 6 asks.")
        yield

    return down


# ── The recorded streams ─────────────────────────────────────────────────

# The run and trace ids the recorded streams in tests/fixtures/api carry, so they never change.
RECORDED_RUN_ID = "run-0001"
RECORDED_TRACES = TraceIds(application_insights="4bf92f3577b34da6a3ce929d0e0e4736",
                           mlflow="tr-0af7651916cd43dd8448eb211c80319c")
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
API = ROOT / "tests" / "fixtures" / "api"


def _refusal_streams() -> dict[str, str]:
    from strata.agent.refusals import REFUSALS

    return {f"refuses-{key.replace('_', '-')}": f"ask-refuses-{key.replace('_', '-')}.sse" for key in REFUSALS}


# Each scripted case whose answer stream the screen tests serve, with its file in tests/fixtures/api.
# tests/test_answer_stream.py checks each file against the server byte for byte.
RECORDED_STREAMS = {
    "p130164-rebidding": "ask-p130164-rebidding.sse",
    "p130164-number-with-no-record": "ask-p130164-removed-number.sse",
    "p130164-nothing-found": "ask-p130164-nothing-found.sse",
    "p130164-before-the-icr": "ask-p130164-before-the-icr.sse",
    "p130164-isr-section": "ask-p130164-isr-section.sse",
    "p130164-number-from-a-table-summary": "ask-p130164-table-summary.sse",
    "p130164-rating-from-a-table-row": "ask-p130164-table-row.sse",
    # Ticket 24: the six checks and the refusals.
    "ke-nwwda-541055-past-range": "ask-ke-nwwda-541055-past-range.sse",
    "ke-nwwda-541055-advice": "ask-ke-nwwda-541055-advice.sse",
    "p130164-summaries": "ask-p130164-summaries.sse",
    "p130164-unsupported-summary": "ask-p130164-unsupported.sse",
    "p130164-advice-without-lesson": "ask-p130164-advice-without-lesson.sse",
    "p130164-several-removed": "ask-p130164-several-removed.sse",
    "p130164-disagreements-unavailable": "ask-p130164-disagreements-unavailable.sse",
    "p130164-isr-7-rating": "ask-p130164-isr-7-rating.sse",
    "p130164-both-sides": "ask-p130164-both-sides.sse",
    "p130164-judge-no-response": "ask-p130164-judge-no-response.sse",
    "p130164-summaries-judge-no-response": "ask-p130164-judge-no-response-none-kept.sse",
    "refuses-part-supplier-scores": "ask-refuses-part-supplier-scores.sse",
    # Ticket 42: an answer asked for in French.
    "p127203-fr-procurement-delays": "ask-p127203-fr.sse",
    **_refusal_streams(),
}


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
                     engine_for=app_engine_for(case, engine_for), judge=ScriptedJudge(case),
                     new_run_id=lambda: RECORDED_RUN_ID,
                     trace_ids=lambda: RECORDED_TRACES)

    async def ask():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            response = await client.post("/api/ask", headers={"X-Forwarded-User": "4021@1984"}, json={
                "question": case.question, "scope": case.scope, "asof": case.as_of.isoformat(),
                **({"lang": case.language} if case.language != "en" else {})})
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

    or, with --all, write every stream in RECORDED_STREAMS over its file.
    """
    import argparse
    import sys

    from strata.harness.turn import ERROR_CODES

    parser = argparse.ArgumentParser(prog="python -m strata.agent.scripted", description=main.__doc__.split("\n")[0])
    parser.add_argument("case", nargs="?", choices=sorted(load_cases()))
    parser.add_argument("--error", choices=ERROR_CODES, help="print the stream of a run that ends with this error")
    parser.add_argument("--database", type=Path, default=FIXTURE_DB, help="the fixture database (gates/build_fixture.py)")
    parser.add_argument("--all", action="store_true", help="write every recorded stream the screen tests serve")
    args = parser.parse_args(argv)
    if args.all:
        cases = load_cases()
        for case_id, name in RECORDED_STREAMS.items():
            (API / name).write_text(stream_text(cases[case_id], args.database))
        return 0
    if (args.case is None) == (args.error is None):
        parser.error("name a case or an --error code, not both")
    sys.stdout.write(failed_stream_text(args.error) if args.error else stream_text(load_cases()[args.case], args.database))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
