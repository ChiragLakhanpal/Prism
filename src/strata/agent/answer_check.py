"""The six checks on everything Strata writes for a person to read (CLAUDE.md rule 1; ticket 24): one
implementation, shared by the answer stream (POST /api/ask, src/strata/server/app.py) and the draft runtime
(src/strata/drafts/runtime.py), so no path can show a sentence that skipped a check.

The verifier (src/strata/agent/verifier.py) runs checks 1 to 3 and 5 at once, as AnswerCheck builds. SixChecks
runs the two that need a service, in the order the verifier needs them:

- check 6 asks get_disagreements, as the viewer and as of the page's date, about each project the standing
  sentences cite, through the tool registry, on one engine for every project. The rows and sides it returns
  join the evidence, each side as its whole passage, so a side's marker opens like any source. When it cannot
  ask, every sentence citing that project is removed (disagreements_unavailable).
- check 4 asks the judge (src/strata/agent/judge.py) once, about every standing sentence that checks 1 to 3 did
  not prove. When the judge does not respond, or none is connected, those sentences are removed
  (judge_unavailable).

finish() yields the steps the verifier takes inside its own (getting the other side of a disagreement, asking
the judge), each running then done, and last the Verdict. The answer stream sends the steps; the draft runtime
keeps its four steps and takes only the verdict.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from collections.abc import AsyncIterator, Iterable, Mapping
from dataclasses import dataclass

from strata.agent.claims import Claim
from strata.agent.judge import Judge, JudgeError
from strata.agent.loop import keep_result
from strata.agent.verifier import DISAGREEMENTS_TOOL, AnswerCheck, Checked, Verdict
from strata.config import Thresholds, Tool, load_thresholds, load_tools
from strata.dbx import Viewer
from strata.harness.facts import Facts
from strata.harness.turn import Event
from strata.lakehouse.engine import EngineError
from strata.server.engines import EngineFor
from strata.tools import registry
from strata.tools.search_passages import TABLE as PASSAGES, read_passage

log = logging.getLogger("strata.agent.answer_check")


@dataclass(frozen=True)
class Asker:
    """Who the checks ask as, in which view, as of which day, and the run they belong to (for the log)."""

    viewer: Viewer
    view: str
    as_of: dt.date
    run_id: str


class SixChecks:
    """Checks 4 to 6 for one app: the engine each viewer's questions run on, the judge, the tool registry and the
    thresholds file. Without engine_for, check 6 cannot ask; without a judge, check 4 removes what needed one."""

    def __init__(self, engine_for: EngineFor | None, judge: Judge | None, tools: Mapping[str, Tool] | None = None,
                 thresholds: Thresholds | None = None):
        self.engine_for, self.judge = engine_for, judge
        self.tools = dict(tools) if tools is not None else load_tools()
        self.thresholds = thresholds or load_thresholds()
        # The tools whose rows back advice (config/tools.toml, backs_advice): check 5's lessons and comparables.
        self.backs_advice = [name for name, tool in self.tools.items() if tool.result.backs_advice]
        # The tools whose "Not checked" clause applies only once a sentence on screen cites them.
        self.cited_only = [name for name, tool in self.tools.items() if tool.result.not_checked_when == "cited"]
        self.source_chars = int(self.thresholds.value("verifier.judge_source_chars"))

    def check(self, claims: Iterable[Claim], facts: Facts) -> AnswerCheck:
        """Checks 1 to 3 and 5 on an answer's claims, against one turn's evidence."""
        return AnswerCheck(claims, facts, self.backs_advice, source_chars=self.source_chars)

    def checked(self, sentences: Iterable[Checked], facts: Facts) -> AnswerCheck:
        """Check 5 on sentences checks 1 to 3 already saw, each against its own evidence, as a draft's notes are."""
        return AnswerCheck.from_checked(sentences, facts, self.backs_advice, source_chars=self.source_chars)

    async def finish(self, check: AnswerCheck, facts: Facts, asker: Asker) -> AsyncIterator[Event | Verdict]:
        """Checks 6 and 4 on what checks 1 to 3 and 5 left standing, then the verdict."""
        projects = check.projects()
        if projects:
            for project, rows in (await asyncio.to_thread(self.disagreements_about, facts, asker, projects)).items():
                check.disagreements_for(project, rows)
        resting = check.resting()
        if resting:
            await asyncio.to_thread(self.whole_passages, facts, asker, resting)
        found = [row for row in resting if row["evidence_id"] in check.fetched]
        if found:  # the draft left these out, and check 6 got them
            step = {"id": "check-disagreement", "kind": "disagreement"}
            yield Event("step", {**step, "status": "running"})
            yield Event("step", {**step, "status": "done", "count": len(found)})
        questions = check.questions()
        if questions:
            step = {"id": "check-judge", "kind": "judge", "count": len(questions)}
            yield Event("step", {**step, "status": "running"})
            try:
                if self.judge is None:
                    raise JudgeError("No judge is connected.")
                judgements = await asyncio.to_thread(self.judge.judge, questions)
            except JudgeError as error:
                log.warning("Run %s: the judge did not answer (%s), so its sentences are removed.", asker.run_id, error)
                judgements = None
            check.judged(questions, judgements)
            yield Event("step", {**step, "status": "done"})
        yield check.verdict()

    def disagreements_about(self, facts: Facts, asker: Asker, projects: list[str]) -> dict[str, list | None]:
        """Check 6's question about each project, as the viewer, on one engine, with every row and side it returns
        kept in the evidence; None for a project it could not ask about."""
        answers: dict[str, list | None] = dict.fromkeys(projects)
        if self.engine_for is None:
            return answers
        try:
            with self.engine_for(asker.viewer) as engine:
                context = registry.Context(engine, asker.viewer, asker.view, asker.as_of, self.thresholds)
                for project in projects:
                    try:
                        result = registry.call(DISAGREEMENTS_TOOL, {"subject_id": project}, context, self.tools)
                    except (EngineError, registry.ToolError, registry.ToolContractError):
                        log.exception("Run %s could not ask %s about %s.", asker.run_id, DISAGREEMENTS_TOOL, project)
                        continue
                    keep_result(facts, DISAGREEMENTS_TOOL, result, self.tools)
                    answers[project] = result["rows"]
        except EngineError:
            log.exception("Run %s could not open the data service to ask %s.", asker.run_id, DISAGREEMENTS_TOOL)
        return answers

    def whole_passages(self, facts: Facts, asker: Asker, rows: list) -> None:
        """Each side of a disagreement the answer shows, as its whole passage, so its marker opens the same
        evidence card and drawer as a passage a search returned."""
        wanted = [side["evidence_id"] for row in rows for side in row.get("sides") or ()
                  if side["evidence_id"].startswith(f"{PASSAGES}:")
                  and "source" not in (facts.get(side["evidence_id"]) or {})]
        if not wanted or self.engine_for is None:
            return
        try:
            with self.engine_for(asker.viewer) as engine:
                for evidence in wanted:
                    whole = read_passage(engine, evidence.partition(":")[2], asker.as_of)
                    if whole is not None:
                        held = facts.get(evidence)
                        facts.record(evidence, {**whole, "also": [held]} if held else whole,
                                     tool=facts.tool(evidence) or DISAGREEMENTS_TOOL)
        except EngineError:
            log.exception("Run %s could not read the sides of a disagreement.", asker.run_id)
