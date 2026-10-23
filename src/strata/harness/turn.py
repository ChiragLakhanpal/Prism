"""One turn of a run: the question, who asked it, and the evidence it has seen so far.

A runner takes a Turn and yields Events, which the stream route sends to the browser in
order. The event types follow the answer contract in the spec (seam 3): step, sentence,
evidence, disagreement, checks, removed, error and done.
"""

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


@dataclass
class Turn:
    question: str
    viewer: Viewer
    run_id: str
    facts: Facts = field(default_factory=Facts)


Runner = Callable[[Turn], AsyncIterator[Event]]


def new_run_id() -> str:
    return f"run-{uuid.uuid4().hex}"


async def no_agent(turn: Turn) -> AsyncIterator[Event]:
    """The runner until the agent exists: it says there is no agent, so the screen can say so."""
    yield Event("error", {"code": "no_agent"})
