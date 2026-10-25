"""Scoring one benchmark question's answer from the answer contract (ticket 33; spec, seam 3).

The full gate asks each question in evals/benchmark.yaml through /api/ask, the route and stream the app runs,
and scores what came back by the question's kind (docs/PLAN.md section 10):

- refusals: the stream refuses with the question's key, writes no sentence about the request, and holds no
  contact detail or individual's name (strata.agent.refusals.refusal_problems, as ticket 24's checks use it).
- every other kind: the answer kept at least one sentence after the verifier, and refused nothing. When the
  question names a tool, some call of that tool gave the expected answer: the reading of its result
  (strata.evals.answers) equals the reference, which is what the tool gives for the question's own arguments on
  the same data, or, for ask_genie, the rows of the question's ground-truth SQL on the same data. So the full
  gate needs no literal from the fixture, and the offline gate proves each reference equals the question's
  expected answer on the fixture (tests/test_tools.py).
- citations: every evidence id in the question's cites is cited by a kept sentence. A question with a tool and
  no cites needs at least one kept sentence that cites something the tool returned.

Each failure is one sentence that names the gap, which the full gate prints and stores.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from strata.agent.refusals import refusal_problems
from strata.evals import answers


@dataclass
class Asked:
    """One question as the full gate asked it: the question, the stream's events and text, every tool call with its
    whole result, and the reference answer its tool gives for the question's own arguments."""

    question: dict
    events: list[tuple[str, dict]]
    text: str
    calls: list[dict] = field(default_factory=list)  # {"tool", "arguments", "result"}
    reference: dict | None = None


@dataclass(frozen=True)
class Scored:
    id: str
    kind: str
    passed: bool
    problems: tuple[str, ...] = ()


def kept(events: list[tuple[str, dict]]) -> list[dict]:
    """The sentences the stream showed: the ones the verifier kept."""
    return [data for kind, data in events if kind == "sentence"]


def cited(events: list[tuple[str, dict]]) -> set[str]:
    return {evidence for sentence in kept(events) for evidence in sentence.get("evidence_ids") or ()}


def returned(result: dict) -> set[str]:
    """Every evidence id a tool's result holds: its rows, the records inside them, and its summary."""
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("evidence_id"), str):
                found.add(value["evidence_id"])
            for inner in value.values():
                walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)

    walk(result.get("rows"))
    walk(result.get("summary"))
    return found


def score(asked: Asked, restricted: Iterable[str] = ()) -> Scored:
    question = asked.question
    qid, kind = question["id"], question["kind"]
    if kind == "refusals":
        problems = refusal_problems(question["expected"]["refusal"], asked.events, asked.text, restricted)
        return Scored(qid, kind, not problems, tuple(problems))
    problems: list[str] = []
    errors = [data.get("code") for event, data in asked.events if event == "error"]
    if errors:
        return Scored(qid, kind, False, (f"It gave no answer: the stream ended with the error {errors[0]}.",))
    refused = [data.get("key") for event, data in asked.events if event == "refusal"]
    if refused:
        problems.append(f"It refused with {refused[0]}, though the question asks for nothing Strata turns down.")
    sentences = kept(asked.events)
    if not sentences:
        problems.append("It kept no sentence: the verifier removed every sentence it wrote, or it wrote none.")
    tool = question.get("tool")
    calls = [call for call in asked.calls if call["tool"] == tool] if tool else []
    if tool and not calls:
        problems.append(f"It never called {tool}, the tool the question is for.")
    elif tool:
        readings = [answers.answered(call["result"], question) for call in calls]
        if asked.reference not in readings:
            problems.append(f"No call of {tool} gave the expected answer. With the question's own arguments it gives "
                            f"{asked.reference}; the agent's calls gave {readings}.")
    shown = cited(asked.events)
    missing = [evidence for evidence in question.get("cites") or () if evidence not in shown]
    if missing:
        problems.append(f"Its kept sentences do not cite {', '.join(missing)}.")
    elif tool and calls and sentences and not question.get("cites"):
        if not shown & set().union(*(returned(call["result"]) for call in calls)):
            problems.append(f"No kept sentence cites anything {tool} returned.")
    return Scored(qid, kind, not problems, tuple(problems))
