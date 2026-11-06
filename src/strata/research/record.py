"""Records the research brief's writer and judge live, for the offline tests (ticket 148): ops/agent/record.py
--research.

It writes the brief for the seeded P156634 run on a copy of the fixture database with the run written into it
(ticket 147's seed, ops/research/seed.py), with the live writer and the live judge on Azure OpenAI,
through the same run the route streams (reuse, so no source is read). It keeps the writer's answer in
tests/fixtures/agent/research/P156634.json and the judge's in P156634.judged.json, and returns the verifier's counts.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from strata.agent import judge as answer_judge
from strata.agent.answer_check import SixChecks
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.research import run as research_run
from strata.research import writer as research_writer
from strata.research.store import ResearchStore

REPO = Path(__file__).resolve().parents[3]
FOLDER = REPO / "tests" / "fixtures" / "agent" / "research"
PROJECT, AS_OF = "P156634", dt.date(2026, 11, 5)


class KeptJudge:
    """The live judge, keeping what it was asked and what it answered."""

    def __init__(self, live: answer_judge.AzureOpenAIJudge):
        self.live, self.name = live, live.name
        self.asked: list[str] = []
        self.indexes: list[int] = []
        self.response: dict | None = None
        post = live.post

        def keep(url, headers, body):
            self.response = post(url, headers, body)
            return self.response

        live.post = keep

    def judge(self, questions):
        self.asked = [question.sentence for question in questions]
        self.indexes = [question.index for question in questions]
        return self.live.judge(questions)


def record_research(env, fixture: Path = REPO / "data" / "out" / "fixture.duckdb") -> dict:
    writer, live_judge = research_writer.from_environment(env), answer_judge.from_environment(env)
    if writer is None or live_judge is None:
        raise answer_judge.JudgeError("The env file has no AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY.")
    if not fixture.is_file():
        raise answer_judge.JudgeError(f"There is no fixture database at {fixture}. Build it: uv run python "
                                      "gates/build_fixture.py")
    sys.path.insert(0, str(REPO / "ops" / "research"))
    import seed as research_seed

    kept = KeptJudge(live_judge)
    with tempfile.TemporaryDirectory() as folder:
        database = Path(folder) / "fixture.duckdb"
        shutil.copy(fixture, database)
        engine = DuckDBEngine.open(database)
        research_seed.seed(ResearchStore(engine.cursor), PROJECT, fixture_db=fixture, say=lambda _: None)

        @contextmanager
        def engine_for(viewer):
            yield engine.cursor()

        run = research_run.Run(engine_for, None, ResearchStore(engine.cursor), writer, SixChecks(engine_for, kept),
                               lambda: dt.datetime.now(dt.UTC))
        request = research_run.Request(Viewer(name="the recording command", token=""), "staff", PROJECT, AS_OF,
                                       "research-recording", reuse=True)

        async def brief():
            last = None
            async for event in run.events(request):
                last = event
            return last

        done = asyncio.run(brief())
        engine.close()
    FOLDER.mkdir(parents=True, exist_ok=True)
    (FOLDER / f"{PROJECT}.json").write_text(json.dumps({
        "made_by": "Recorded live with uv run --script ops/agent/record.py --research --env-file .env, on the "
                   "run ops/research/seed.py keeps.", "recorded": "live", "project_id": PROJECT,
        "as_of": AS_OF.isoformat(), "response": writer.last_response}, indent=1, ensure_ascii=False) + "\n")
    (FOLDER / f"{PROJECT}.judged.json").write_text(json.dumps({
        "made_by": "Recorded live with uv run --script ops/agent/record.py --research --env-file .env.",
        "recorded": "live", "asked": kept.asked, "indexes": kept.indexes,
        "response": kept.response}, indent=1, ensure_ascii=False) + "\n")
    return done.data["brief"]["checks"] if done.type == "done" and "brief" in done.data else {"stopped": done.data}
