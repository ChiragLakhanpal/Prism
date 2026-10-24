"""The shield set: real passages with rule-like sentences must reach the agent as tool results without a
Prompt Shields refusal (evals/shield_passages.toml; spec, "Security and privacy").

fairshare hit false refusals when rules rode in the data. Strata keeps rules in the agent's instructions and
data in messages, and this check guards that: tool_result() asks search_passages for each passage by its
own sentence, as the agent would, and check() asks the agent a question, answers its tool call with that
result, and records whether the agent took it. A content filter or Prompt Shields refusal fails the check.
"""

from __future__ import annotations

import datetime as dt
import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from strata.agent.loop import Agent, AgentError, call_output, for_agent, function_calls
from strata.dbx import Viewer
from strata.lakehouse.engine import Engine
from strata.tools import registry

SET = Path(__file__).resolve().parents[3] / "evals" / "shield_passages.toml"
QUESTION = "What does the report say in the passage that holds this sentence: {sentence}"


@dataclass(frozen=True)
class ShieldPassage:
    evidence_id: str
    project_id: str
    source: str
    sentence: str


@dataclass(frozen=True)
class Outcome:
    evidence_id: str
    status: str  # passed, refused, no_tool_call or failed
    detail: str = ""


def load_passages(path: Path = SET) -> list[ShieldPassage]:
    with open(path, "rb") as handle:
        return [ShieldPassage(**entry) for entry in tomllib.load(handle)["passages"]]


def tool_result(passage: ShieldPassage, engine: Engine, viewer: Viewer, as_of: dt.date) -> dict:
    """search_passages' result for the passage's own sentence, keeping only that passage."""
    result = registry.call("search_passages", {"query": passage.sentence, "project_id": passage.project_id},
                           registry.Context(engine, viewer, "staff", as_of))
    rows = [row for row in result["rows"] if row["evidence_id"] == passage.evidence_id][:1]
    if not rows:
        raise LookupError(f"search_passages did not return {passage.evidence_id} for its own sentence.")
    return {**result, "rows": rows, "coverage": {"matched": 1, "used": 1, "not_used": []}}


def check(passages: list[ShieldPassage], results: dict[str, dict], agent_for: Callable[[], Agent],
          as_of: dt.date) -> list[Outcome]:
    """Send each passage's tool result to a fresh conversation with the agent."""
    outcomes = []
    for passage in passages:
        agent = agent_for()
        message = {"question": QUESTION.format(sentence=passage.sentence), "scope": passage.project_id,
                   "as_of": as_of.isoformat(), "view": "staff", "language": "en"}
        try:
            first = agent.respond([{"role": "user", "content": json.dumps(message, ensure_ascii=False)}], None)
            calls = function_calls(first)
            if not calls:
                outcomes.append(Outcome(passage.evidence_id, "no_tool_call", "The agent called no tool."))
                continue
            result = for_agent(results[passage.evidence_id], as_of)
            agent.respond([call_output(call, result) for call in calls], first.get("id"))
        except AgentError as error:
            status = "refused" if error.code == "content_filter" else "failed"
            outcomes.append(Outcome(passage.evidence_id, status, str(error)))
            continue
        outcomes.append(Outcome(passage.evidence_id, "passed"))
    return outcomes


def summary(outcomes: list[Outcome]) -> str:
    passed = [outcome for outcome in outcomes if outcome.status == "passed"]
    if len(passed) == len(outcomes):
        return f"All {len(outcomes)} passages reached the agent as tool results with no refusal.\n"
    lines = []
    for status, said in (("refused", "were refused by a content filter or Prompt Shields"),
                         ("no_tool_call", "never reached the agent, because it called no tool"),
                         ("failed", "met another error")):
        found = [outcome for outcome in outcomes if outcome.status == status]
        if found:
            lines.append(f"{len(found)} of {len(outcomes)} passages {said}:")
            lines += [f"- {outcome.evidence_id}: {outcome.detail}" for outcome in found]
    return "\n".join(lines) + "\n"
