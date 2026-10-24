"""What the lesson reviewer groups may write on the warehouse (ticket 29).

A reviewer's act is written with the reviewer's own token (ADR 0003), so the warehouse holds the same line the
roles file draws: only the members of a group config/roles.toml names for lesson review may write the review
tables, and every viewer may read the lessons through the catalog's readers grant (bundle/catalog.yml). The
server checks the roles file first in any case (strata.knowledge.lessons.review). ops/lessons/grant_reviewers.py
runs these statements on the workspace.
"""

from __future__ import annotations

import re

from strata.config import Roles

# The tables a reviewer's act writes: the queue, the acts, the versions, the proposals each version rests on,
# and the writer's notes ("Try again" writes one as the reviewer).
WRITTEN = ("lesson_review_items", "lesson_review_acts", "lesson_versions", "lesson_sources", "lesson_review_notes")
GROUP = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]*")


def reviewer_grants(roles: Roles) -> list[str]:
    """GRANT statements for each workspace group whose members review lessons, in the roles file's order."""
    statements = []
    for group in roles.groups.values():
        if "lesson_review" not in group.pages:
            continue
        if not GROUP.fullmatch(group.workspace_group):
            raise ValueError(f"{group.workspace_group!r} is not a workspace group's name.")
        name = f"`{group.workspace_group}`"  # sql-lint: names only
        statements += [f"GRANT USE CATALOG ON CATALOG strata TO {name}",
                       f"GRANT USE SCHEMA ON SCHEMA strata.ops TO {name}",
                       *[f"GRANT SELECT, MODIFY ON TABLE strata.ops.{table} TO {name}" for table in WRITTEN]]
    return statements
