"""The passages a decision ranks lower for a kind of question (ticket 32; docs/PLAN.md section 11: "feedback can
demote a passage but never hide it").

A passage is ranked lower for one kind of question while the latest act on its group (strata.ops.label_decisions)
is a passage reviewer's "Rank it lower", an agreement at scale, or an audit that left it lower; "Keep its
ranking", "Restore its ranking" and reopening give it its earlier ranking. Only acts made by the as-of date count,
so a replay sees the ranking of its day (ADR 0002). Reports alone change nothing.

rank() moves the ranked-lower passages below every other passage the search found, in their own order, and keeps
them: a ranked-lower passage still appears, and comes first when it is the only one.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Sequence
from typing import TypeVar

from strata.knowledge.retrieval.labels import rows
from strata.lakehouse.engine import Engine

T = TypeVar("T")
# The acts that rank a passage lower for its kind of question, and those that give it its earlier ranking.
LOWERING = frozenset({"accepted", "accepted_by_agreement", "audit", "left_lower"})
RESTORING = frozenset({"declined", "restored", "reopened"})


def lowered(engine: Engine, query_kind: str, as_of: dt.date) -> set[str]:
    """The passages ranked lower for this kind of question, as of a date."""
    latest: dict[str, tuple[str, str]] = {}
    for row in rows(engine, "lowered", query_kind=query_kind, as_of=as_of):
        latest[row["group_id"]] = (row["passage_id"], row["act"])
    return {passage for passage, act in latest.values() if act in LOWERING}


def rank(items: Sequence[T], passage_of: Callable[[T], str], ranked_lower: set[str]) -> list[T]:
    """The items with every ranked-lower passage moved after the others, each part in its own order."""
    return ([item for item in items if passage_of(item) not in ranked_lower]
            + [item for item in items if passage_of(item) in ranked_lower])
