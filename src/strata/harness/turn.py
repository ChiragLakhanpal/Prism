"""One turn of a run: the question, who asked it, what it is about, and the evidence it has seen so far.

A runner takes a Turn and yields Events, which the stream route sends to the browser in
order. The event types follow the answer contract in the spec (seam 3): step, sentence,
evidence, disagreement, checks, removed, error and done. A runner yields only steps and, once,
the agent's claims; the stream runs the verifier on the claims and writes the answer's events
itself, so no answer reaches the page without the checks (CLAUDE.md rule 1).
"""

import datetime as dt
import uuid
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from strata.dbx import Viewer
from strata.harness.facts import Facts


@dataclass(frozen=True)
class Event:
    type: str
    data: Mapping[str, Any]


@dataclass(frozen=True)
class Scope:
    """What a question is about: the page's scope chip (a P-code or a STEP reference), its as-of date,
    the view it is asked in, and the language the answer is written in."""

    chip: str | None = None
    as_of: dt.date | None = None
    view: str = "staff"
    language: str = "en"


@dataclass(frozen=True)
class TraceIds:
    """Where a run's trace can be found: Application Insights' operation id and MLflow's trace id."""

    application_insights: str | None = None
    mlflow: str | None = None


@dataclass
class RunNotes:
    """What the runner did, for the run's row in strata.ops.agent_runs."""

    agent: str | None = None
    agent_version: str | None = None
    as_of: dt.date | None = None  # the as-of date the tools ran at
    tool_rounds: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    response_ids: list[str] = field(default_factory=list)


@dataclass
class Turn:
    question: str
    viewer: Viewer
    run_id: str
    scope: Scope = field(default_factory=Scope)
    facts: Facts = field(default_factory=Facts)
    notes: RunNotes = field(default_factory=RunNotes)
    trace: TraceIds | None = None


class RunError(Exception):
    """A run that cannot answer, with a code the page has a sentence for. Its details stay in the log."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code


Runner = Callable[[Turn], AsyncIterator[Event]]


def new_run_id() -> str:
    return f"run-{uuid.uuid4().hex}"


async def no_agent(turn: Turn) -> AsyncIterator[Event]:
    """The runner until the agent exists: it says there is no agent, so the screen can say so."""
    yield Event("error", {"code": "no_agent"})
