"""The recording command: re-record every scripted case from the live agent (spec, "Model outputs are
recorded, not called, in the offline gate").

record_all() asks each recording's question (tests/fixtures/agent/cases.toml names which cases share it)
through the same answer loop the app runs, with the agent and the tools it is given, and keeps every
response the agent gave, in order. It writes each one over its file in tests/fixtures/agent/recorded and
keeps the old text, so report_text() can show the change as a unified diff. Re-recording is a deliberate
act: review the diff, run the gate, and commit the recordings with the change that needed them. The
cases' plants stay in cases.toml, so they apply to the new recordings too.

A response keeps the fields that say what the agent did (its id, status, model, agent and output). Fields
that change on every call, such as its usage and creation time, stay out, so the diff shows only what
changed in the agent's answers.

ops/agent/record.py runs it with the Foundry agent and the SQL warehouse, as the env file's token.

record_judged() re-records the judge of the verifier's check 4 (ticket 24): it replays every scripted case
through the answer stream, and every writer case through its draft workflow's six checks, with the scripted
agent and its plants, and keeps the live judge's answer for each case that asks it, in
tests/fixtures/agent/judged/<case id>.json. Run it after record_all(), since the
sentences the judge is asked about come from the agent's recordings. Given the criteria reader's cases (ticket
31), it also replays each through section 5's comparison and its six checks, where the judge is asked about the
readings.
"""

from __future__ import annotations

import asyncio
import copy
import datetime as dt
import difflib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from strata.agent.loop import Agent, answer_runner, output_text
from strata.agent.scripted import Case
from strata.agent.verifier import Verdict, verify
from strata.dbx import Viewer
from strata.harness.turn import Scope, Turn
from strata.server.engines import EngineFor

KEPT = ("id", "object", "status", "model", "agent", "incomplete_details", "output")
ABOUT = ("The Foundry agent's answers through the Responses API, recorded by ops/agent/record.py from the live "
         "agent with the live tools. The scripted agent replays them in the offline gate.")
ABOUT_READER = ("The Foundry package reader's answer through the Responses API, recorded by ops/agent/record.py "
                "--packages from the live reader, given the sentence and the package form's fields as the "
                "plan-a-package workflow sends them. The scripted reader replays it in the offline gate.")
ABOUT_CRITERIA = ("The Foundry criteria reader's answer through the Responses API, recorded by ops/agent/record.py "
                  "--criteria from the live reader, given the pasted text and the item registry's items as the "
                  "check-your-criteria workflow sends them. The scripted reader replays it in the offline gate.")
ABOUT_WRITER = ("The Foundry writer's answer through the Responses API, recorded by ops/agent/record.py --writers "
                "from the live writer, given the facts its workflow read on the workspace. The scripted writer "
                "replays it in the offline gate.")


@dataclass(frozen=True)
class Recorded:
    recording: str
    path: Path
    cases: tuple[str, ...]
    before: str
    after: str
    counts: dict | None  # the verifier's counts on the answer, with no plants


class Keeper:
    """The live agent, with each response it gives kept, in the recording's shape."""

    def __init__(self, agent: Agent):
        self.agent, self.responses = agent, []
        self.name, self.version = agent.name, agent.version

    def respond(self, items, previous_response_id):
        response = self.agent.respond(items, previous_response_id)
        self.version = getattr(self.agent, "version", None) or self.version
        self.responses.append({key: response[key] for key in KEPT if key in response})
        return response


def _record_one(case: Case, agent: Agent, engine_for: EngineFor, viewer: Viewer, today: dt.date) -> tuple[dict, dict | None]:
    keeper = Keeper(agent)
    turn = Turn(question=case.question, viewer=viewer, run_id=f"record-{case.recording}",
                scope=Scope(chip=case.scope, as_of=case.as_of, language=case.language))
    run = answer_runner(lambda _: keeper, engine_for, today=lambda: today)

    async def drain():
        claims = None
        async for event in run(turn):
            if event.type == "claims":
                claims = event.data["claims"]
        return claims

    claims = asyncio.run(drain())
    recording = {"about": ABOUT, "recorded": True, "recorded_on": today.isoformat(), "question": case.question,
                 "scope": case.scope, "as_of": case.as_of.isoformat(),
                 **({"language": case.language} if case.language != "en" else {}),
                 "agent": {"name": keeper.name, "version": keeper.version}, "responses": keeper.responses}
    return recording, verify(claims, turn.facts, case.language).counts() if claims is not None else None


def _record_writer(case: Case, agent: Agent, engine_for: EngineFor, viewer: Viewer,
                   today: dt.date) -> tuple[dict, dict | None]:
    """A draft writer's case (tests/fixtures/agent/writers.toml): its kind's workflow reads its facts as the
    viewer, the live writer answers the one message, and the verifier's counts go with the recording."""
    from strata.config import load_draft_kinds
    from strata.drafts import runtime

    module = runtime.writer_module(load_draft_kinds().kinds[case.request["kind"]])
    with engine_for(viewer) as engine:
        facts = module.read(engine, viewer, case.request, today)
    keeper = Keeper(agent)
    response = keeper.respond([{"role": "user", "content": json.dumps(module.message(facts, case.language),
                                                                      ensure_ascii=False, default=str)}], None)
    from strata.agent.answer_check import SixChecks

    check, _, _ = runtime.note_check(module, facts, runtime.parse_notes(output_text(response), module.KEY),
                                     SixChecks(None, None), case.language)
    verdict = Verdict(tuple(sentence for _, sentence in sorted(check.sentences.items())))
    recording = {"about": ABOUT_WRITER, "recorded": True, "recorded_on": today.isoformat(), "question": case.question,
                 "scope": case.scope, "as_of": case.as_of.isoformat(),
                 **({"language": case.language} if case.language != "en" else {}),
                 "agent": {"name": keeper.name, "version": keeper.version}, "responses": keeper.responses}
    return recording, verdict.counts()


def _record_package(case: Case, agent: Agent, engine_for: EngineFor, viewer: Viewer,
                    today: dt.date) -> tuple[dict, dict | None]:
    """A package reader's case (tests/fixtures/agent/packages.toml): the live reader is sent the case's sentence
    with the package form's fields, as the plan-a-package workflow sends it (ticket 15). It writes no sentence
    a person reads, so no verifier counts go with it."""
    from strata.packages import reader
    from strata.config import load_package_form

    keeper = Keeper(agent)
    message = reader.message(case.question, load_package_form())
    keeper.respond([{"role": "user", "content": json.dumps(message, ensure_ascii=False)}], None)
    recording = {"about": ABOUT_READER, "recorded": True, "recorded_on": today.isoformat(), "question": case.question,
                 "scope": case.scope, "as_of": case.as_of.isoformat(),
                 "agent": {"name": keeper.name, "version": keeper.version}, "responses": keeper.responses}
    return recording, None


def _record_criteria(case: Case, agent: Agent, engine_for: EngineFor, viewer: Viewer,
                     today: dt.date) -> tuple[dict, dict | None]:
    """A criteria reader's case (tests/fixtures/agent/criteria.toml): the live reader is sent the case's pasted text
    with the item registry's items, as the check-your-criteria workflow sends it (ticket 31). The workflow checks
    and verifies its readings when it replays them, so no verifier counts go with the recording."""
    from strata.config import load_criteria_items
    from strata.criteria import workflow

    keeper = Keeper(agent)
    keeper.respond([{"role": "user", "content": json.dumps(workflow.message(case.question, load_criteria_items()),
                                                           ensure_ascii=False)}], None)
    recording = {"about": ABOUT_CRITERIA, "recorded": True, "recorded_on": today.isoformat(), "question": case.question,
                 "scope": case.scope, "as_of": case.as_of.isoformat(),
                 "agent": {"name": keeper.name, "version": keeper.version}, "responses": keeper.responses}
    return recording, None


def record_criteria(cases: dict[str, Case], agent_for: Callable[[], Agent], engine_for: EngineFor, viewer: Viewer,
                    today: dt.date | None = None) -> list[Recorded]:
    """Re-record every recording the criteria reader's cases name, once each, and write it over its file."""
    return record_all(cases, agent_for, engine_for, viewer, today, record_one=_record_criteria)


def record_packages(cases: dict[str, Case], agent_for: Callable[[], Agent], engine_for: EngineFor, viewer: Viewer,
                    today: dt.date | None = None) -> list[Recorded]:
    """Re-record every recording the package reader's cases name, once each, and write it over its file."""
    return record_all(cases, agent_for, engine_for, viewer, today, record_one=_record_package)


def record_writers(cases: dict[str, Case], agent_for: Callable[[], Agent], engine_for: EngineFor, viewer: Viewer,
                   today: dt.date | None = None) -> list[Recorded]:
    """Re-record every recording the draft writers' cases name, once each, and write it over its file."""
    return record_all(cases, agent_for, engine_for, viewer, today, record_one=_record_writer)


ABOUT_JUDGE = ("The judge's answer for this case's sentences through Azure OpenAI's chat completions, recorded by "
               "ops/agent/record.py --judge from config/models.toml's draft role. ScriptedJudge replays it in the "
               "offline gate.")


class JudgeKeeper:
    """The live judge, with the questions it was asked and the answer it gave kept. It keeps them by wrapping a copy
    of the judge's transport, so the judge the app runs keeps no viewer's sentences."""

    def __init__(self, judge):
        self.name = judge.name
        self.asked, self.response = None, None
        self.judge_ = copy.copy(judge)
        post = judge.post

        def keep(url, headers, body):
            self.response = post(url, headers, body)
            return self.response

        self.judge_.post = keep

    def judge(self, questions):
        judged = self.judge_.judge(questions)
        self.asked = list(questions)
        return judged


def _ask_through_the_stream(case: Case, engine_for: EngineFor, judge) -> None:
    from strata.agent.scripted import ScriptedAgent
    from strata.server.app import create_app

    import httpx

    app = create_app(runner=answer_runner(lambda turn: ScriptedAgent(case), engine_for, today=lambda: case.as_of),
                     engine_for=engine_for, judge=judge)

    async def ask():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            await client.post("/api/ask", headers={"X-Forwarded-User": "record@strata"}, json={
                "question": case.question, "scope": case.scope, "asof": case.as_of.isoformat(),
                **({"lang": case.language} if case.language != "en" else {})})

    asyncio.run(ask())


def _ask_through_the_draft(case: Case, engine_for: EngineFor, judge) -> None:
    """A writer case's notes through its draft workflow's six checks, as the draft runtime runs them, with the
    scripted writer and its plants: nothing is saved."""
    from strata.agent.answer_check import Asker, SixChecks
    from strata.agent.scripted import ScriptedAgent
    from strata.config import load_draft_kinds
    from strata.drafts import runtime

    viewer = Viewer(user_id="record@strata", name="record@strata")
    module = runtime.writer_module(load_draft_kinds().kinds[case.request["kind"]])
    with engine_for(viewer) as engine:
        try:
            facts = module.read(engine, viewer, case.request, case.as_of)
        except module.NotWritable:
            # Nothing to draft from where this runs, such as suggested PPSD rows (ticket 36) on tables whose lessons
            # no one has decided yet: the case asks the judge nothing, and keeps its file.
            return
    response = ScriptedAgent(case).respond([{"role": "user", "content": json.dumps(
        module.message(facts), ensure_ascii=False, default=str)}], None)
    six = SixChecks(engine_for, judge)
    check, seen, _ = runtime.note_check(module, facts, runtime.parse_notes(output_text(response), module.KEY), six)

    async def drain():
        async for _ in six.finish(check, seen, Asker(viewer, "staff", case.as_of, f"record-{case.id}")):
            pass

    asyncio.run(drain())


def _ask_through_the_criteria(case: Case, engine_for: EngineFor, judge) -> None:
    """A criteria reader's case through section 5's comparison and its six checks, with the scripted reader, on the
    case's package as of its date. Its app state is a throwaway file, so nothing is kept."""
    import tempfile

    import httpx

    from strata import appstate
    from strata.agent.scripted import ScriptedAgent
    from strata.criteria.store import CriteriaStore
    from strata.lakehouse.engine import DuckDBEngine
    from strata.server.app import create_app

    with tempfile.TemporaryDirectory() as folder:
        state = Path(folder) / "state.duckdb"
        with DuckDBEngine.open(state) as engine:
            appstate.build(engine)
        app = create_app(engine_for=engine_for, criteria=CriteriaStore(lambda: DuckDBEngine.open(state)),
                         criteria_reader=lambda: ScriptedAgent(case), today=lambda: case.as_of, judge=judge)

        async def ask():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                await client.post(f"/api/packages/{case.scope}/criteria/compare",
                                  headers={"X-Forwarded-User": "record@strata"}, json={"text": case.question})

        asyncio.run(ask())


def record_judged(cases: dict[str, Case], judge, engine_for: EngineFor, today: dt.date | None = None,
                  criteria: dict[str, Case] | None = None) -> list[Recorded]:
    """Re-record the judge's answer for every case whose answer or draft asks it, and write it over its file. A
    writer case (one with a request) runs through its draft workflow's six checks, an answer case through the
    answer stream, and a criteria reader's case (criteria) through section 5's comparison."""
    from strata.agent.scripted import NO_RESPONSE

    today = today or dt.datetime.now(dt.UTC).date()
    done = []
    asking = [(case, _ask_through_the_draft if case.request is not None else _ask_through_the_stream)
              for case in cases.values()]
    asking += [(case, _ask_through_the_criteria) for case in (criteria or {}).values()]
    for case, ask in asking:
        if case.judge == NO_RESPONSE:
            continue
        keeper = JudgeKeeper(judge)
        ask(case, engine_for, keeper)
        if keeper.asked is None:
            continue
        path = case.folder.parent / "judged" / f"{case.id}.json"
        path.parent.mkdir(exist_ok=True)
        before = path.read_text() if path.exists() else ""
        after = json.dumps({"about": ABOUT_JUDGE, "recorded": True, "recorded_on": today.isoformat(), "case": case.id,
                            "judge": {"deployment": judge.name},
                            "asked": [question.sentence for question in keeper.asked],
                            "response": keeper.response}, indent=1, ensure_ascii=False) + "\n"
        path.write_text(after)
        done.append(Recorded(case.id, path, (case.id,), before, after, None))
    return done


def record_all(cases: dict[str, Case], agent_for: Callable[[], Agent], engine_for: EngineFor, viewer: Viewer,
               today: dt.date | None = None, record_one=_record_one) -> list[Recorded]:
    """Re-record every recording the cases name, once each, and write it over its file."""
    today = today or dt.datetime.now(dt.UTC).date()
    done = []
    for name in dict.fromkeys(case.recording for case in cases.values()):
        sharing = [case for case in cases.values() if case.recording == name]
        first = sharing[0]
        recording, counts = record_one(first, agent_for(), engine_for, viewer, today)
        before = first.path.read_text() if first.path.exists() else ""
        after = json.dumps(recording, indent=1, ensure_ascii=False) + "\n"
        first.path.write_text(after)
        done.append(Recorded(name, first.path, tuple(case.id for case in sharing), before, after, counts))
    return done


def report_text(done: list[Recorded], root: Path) -> str:
    """What changed in each recording, as a unified diff, with the cases it serves and the verifier's counts."""
    lines = []
    for item in done:
        shown = item.path.relative_to(root) if item.path.is_relative_to(root) else item.path
        lines.append(f"{shown}: the recording of {', '.join(item.cases)}.")
        if item.counts:
            sentences, numbers, quotes = item.counts["sentences"], item.counts["numbers"], item.counts["quotes"]
            lines.append(f"The verifier kept {sentences['kept']} of {sentences['written']} sentences; "
                         f"{numbers['matched']} of {numbers['total']} numbers matched and {quotes['found']} of "
                         f"{quotes['total']} quotes were on their pages.")
        diff = list(difflib.unified_diff(item.before.splitlines(), item.after.splitlines(), fromfile=f"a/{shown}",
                                         tofile=f"b/{shown}", lineterm=""))
        lines += diff or ["No change."]
        lines.append("")
    lines.append("Review the change with git diff tests/fixtures/agent, run the gate, and commit the recordings.")
    return "\n".join(lines) + "\n"
