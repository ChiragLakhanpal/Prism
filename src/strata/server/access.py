"""The one access rule for what Strata keeps for a team (ticket 35; the 38 design brief, section 11).

A draft belongs to its author's team. Everyone on that team can open it and its files; only its author
can mark it as checked, export it, discard it or restore it (the 35 brief, section 2). Ticket 38 sends
its uploads, and the packages made from them, through the same helper, so one rule decides who reads
what a team keeps, on every route.

- Access.team(viewer) is the viewer's team: the first team in the roles file (config/roles.toml) one of
  whose workspace groups the viewer is in, or else a team of their own, keyed by their user id, so their
  drafts are theirs alone.
- Access.may_read(viewer, team_key) says whether the viewer is on that team.
- is_author(viewer, author_id) says whether the viewer is the author.

A viewer's workspace groups come from an adapter: WorkspaceGroups asks the workspace's SCIM API for the
viewer's own groups with their forwarded token, which only the workspace can answer, and StaticGroups is
the offline stand-in the tests use. A lookup that fails counts as no groups, so the viewer falls back to
a team of their own and sees less, never more.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from strata.config import Roles
from strata.dbx import Viewer
from strata.lakehouse.engine import Transport, http_transport

log = logging.getLogger("strata.server.access")
ME = "/api/2.0/preview/scim/v2/Me"


class GroupsReader(Protocol):
    def groups(self, viewer: Viewer) -> list[str]:
        """The workspace groups the viewer is in, by display name."""


class StaticGroups:
    """The offline adapter: each viewer's groups, by user id."""

    def __init__(self, groups_by_user: Mapping[str, list[str]]):
        self.by_user = groups_by_user

    def groups(self, viewer: Viewer) -> list[str]:
        return list(self.by_user.get(viewer.user_id or "", []))


class NoGroups:
    """No groups for anyone: every viewer is on a team of their own."""

    def groups(self, viewer: Viewer) -> list[str]:
        return []


class WorkspaceGroups:
    """The live adapter: the viewer's groups from the workspace's SCIM API, read with their own token."""

    def __init__(self, host: str, transport: Callable[[str, str], Transport] = http_transport):
        self.host, self.transport = host, transport

    def groups(self, viewer: Viewer) -> list[str]:
        if not viewer.token:
            return []
        try:
            reply = self.transport(self.host, viewer.token)("GET", ME, None)
        except Exception:  # the workspace, the network or the token: the viewer then sees only their own
            log.exception("I could not read the workspace groups of %s.", viewer.user_id)
            return []
        return [group["display"] for group in reply.get("groups") or [] if group.get("display")]


@dataclass(frozen=True)
class Membership:
    """The team a viewer is on: its key, its name, and whether the roles file names it."""

    key: str
    name: str | None
    named: bool


def is_author(viewer: Viewer, author_id: str) -> bool:
    return bool(viewer.user_id) and viewer.user_id == author_id


class Access:
    def __init__(self, roles: Roles, groups: GroupsReader):
        self.roles, self.reader = roles, groups

    def team(self, viewer: Viewer) -> Membership:
        held = set(self.reader.groups(viewer))
        for team in self.roles.teams:
            if held & set(team.groups):
                return Membership(f"team:{team.key}", team.name, True)
        return Membership(f"viewer:{viewer.user_id}", None, False)

    def may_read(self, viewer: Viewer, team_key: str) -> bool:
        return bool(viewer.user_id) and self.team(viewer).key == team_key
