"""The view switch, applied by the server (ticket 40; the 40 brief, sections 5 and 10).

The roles file's [views] section (config/roles.toml, read by strata.config.load_views) is the one place a view's rules
live. This module applies them:

- applied(views, own, requested) is the view a request gets: the person's own view, or a preview of another view
  their own view may preview. A preview can only take things away: it keeps a capability only where the previewed
  view and the person's own view both have it, never one private to a team, and never an act.
- offered(views, own) is the views the popover offers a person: their own, then each view they may preview.
- ViewParams is the middleware that binds a request's view and as-of date before any route reads them. It keeps the
  address's ?view= only for a preview the person may have, so every route reads "piu" or "public" only in a preview
  and nothing in its own view; and it drops an ?asof= that is not a past date, so every route reads today. What the
  address asked for is kept in the request's scope for GET /api/me, which says what was applied and why.
- guard is the dependency every route runs: in a preview, a route that needs a capability the preview does not keep
  answers 403 {"error": "preview", "capability", "copy_key"} for an act, {"recorded": false} for a quiet record, and
  404 {"error": "not_in_view", "view"} for a read, before the route reads or writes anything.

A person's own view is the implementing agency view when they are on an agency's team in the roles file (an
implementing agency officer, ticket 38), and the World Bank staff view otherwise. In their own view, each route checks
the role it needs itself (the World Bank staff role, a reviewer group, the agency's team), as the roles file sets.
Nothing about a viewer lives in a module global (CLAUDE.md rule 7): each request computes its own.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode

from fastapi import Request

from strata.config import VIEW_KEYS, Views
from strata.dbx import Viewer, viewer_from_headers

STAFF, PIU, PUBLIC = VIEW_KEYS
PREVIEWS = (PIU, PUBLIC)
REQUESTED = "strata.requested"  # where ViewParams keeps what the address asked for, in the request's scope


@dataclass(frozen=True)
class Applied:
    """The view a request gets. own is the person's own view, view the one whose rules apply, preview whether it is a
    preview, capabilities what it keeps, and problem "unknown" when the address asked for a view I can't give them."""

    own: str
    view: str
    preview: bool
    capabilities: frozenset[str] = field(default_factory=frozenset)
    problem: str | None = None

    def allows(self, capability: str) -> bool:
        return capability in self.capabilities


def own_capabilities(views: Views, own: str) -> frozenset[str]:
    return frozenset(key for key, capability in views.capabilities.items() if capability.values[own])


def may_preview(views: Views, own: str, other: str) -> bool:
    """Whether a person whose own view is own may preview other: every capability a preview of other could keep (those
    it has that are neither private to a team nor an act), their own view has too, so the preview only takes away."""
    if other == own or other not in views.views:
        return False
    return all(capability.values[own] for capability in views.capabilities.values()
               if capability.values[other] and not capability.private and not capability.act)


def offered(views: Views, own: str) -> tuple[str, ...]:
    """The views the popover offers: the person's own, then each one they may preview, in the file's order."""
    return (own, *(key for key in VIEW_KEYS if may_preview(views, own, key)))


def applied(views: Views, own: str, requested: str | None) -> Applied:
    """The view a request gets, from the person's own view and the view the address asks for."""
    if requested is None or requested == own:
        return Applied(own, own, False, own_capabilities(views, own))
    if not may_preview(views, own, requested):
        return Applied(own, own, False, own_capabilities(views, own), "unknown")
    kept = frozenset(key for key, capability in views.capabilities.items()
                     if capability.values[requested] and capability.values[own] and not capability.private
                     and not capability.act)
    return Applied(own, requested, True, kept)


# ── The as-of date ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class AsOf:
    """The page's as-of date: the date applied, or None for today, and the problem with what the address asked for:
    unreadable, not_past (today or later), or None."""

    applied: dt.date | None
    problem: str | None = None


def as_of(asked: str | None, today: dt.date) -> AsOf:
    if asked is None or asked == "":
        return AsOf(None)
    try:
        day = dt.date.fromisoformat(asked)
    except ValueError:
        return AsOf(None, "unreadable")
    if len(asked) != 10:  # only a plain ISO day, such as 2016-08-26
        return AsOf(None, "unreadable")
    return AsOf(day) if day < today else AsOf(None, "not_past")


# ── Binding a request's view and date ────────────────────────────────────

class ViewParams:
    """Middleware that binds each /api request's view and as-of date before a route reads them (the 40 brief, 10).

    officer(viewer) says whether the viewer is an implementing agency officer, whose own view is piu, so ?view=piu is
    their own view and not a preview. It is asked only when the address names piu, because that is the only case it
    changes: anyone may preview the public, and staff or an unknown value is the person's own view."""

    def __init__(self, app, officer: Callable[[Viewer], bool], views: Callable[[], Views],
                 today: Callable[[], dt.date]):
        self.app, self.officer, self.views, self.today = app, officer, views, today

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        pairs = parse_qsl(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)
        asked = dict(pairs)
        kept = []
        for key, value in pairs:
            if key == "view":
                if value == PUBLIC or (value == PIU and not self.officer(viewer_of(scope))):
                    kept.append((key, value))
            elif key == "asof":
                # A date I can't read is left out, so the route reads today. A date of today or later stays: every
                # route reads the earlier of it and today (ADR 0002), and the Timeline names it as today.
                if as_of(value, self.today()).problem != "unreadable":
                    kept.append((key, value))
            else:
                kept.append((key, value))
        # In place, so the middleware around this one sees the route the router chose for the same request.
        scope["query_string"] = urlencode(kept).encode("latin-1")
        scope[REQUESTED] = {"view": asked.get("view"), "asof": asked.get("asof")}
        return await self.app(scope, receive, send)


def viewer_of(scope) -> Viewer:
    headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in scope.get("headers", [])}
    return viewer_from_headers(headers)


def requested(request: Request) -> dict:
    """What the address asked for, as ViewParams kept it: {"view": ..., "asof": ...}, each None when it named none."""
    return request.scope.get(REQUESTED) or {"view": request.query_params.get("view"),
                                            "asof": request.query_params.get("asof")}


class ViewRefused(Exception):
    """A route a preview does not keep: the answer the guard gives instead of running it."""

    def __init__(self, status: int, body: dict):
        super().__init__(body.get("error") or "recorded")
        self.status, self.body = status, body


async def requested_preview(request: Request) -> str | None:
    """The preview a request is in: the address's ?view=, as ViewParams bound it, or the view a JSON body names, which
    the screens send with each act. A preview named either way is a preview, since a preview only takes things away."""
    view = request.query_params.get("view")
    if view in PREVIEWS:
        return view
    if "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return None
        named = body.get("view") if isinstance(body, dict) else None
        if named in PREVIEWS:
            return named
    return None


def make_guard(views: Callable[[], Views], officer: Callable[[Viewer], bool]):
    """The dependency every route runs: in a preview, a route that needs a capability the preview does not keep is
    refused before it reads or writes anything (the 40 brief, 5.1 and 10)."""

    async def guard(request: Request) -> None:
        route = request.scope.get("route")
        held = views()
        rule = held.route(request.method, getattr(route, "path", "")) if route is not None else None
        if rule is None:
            return
        capability = rule.needs(request.path_params)
        if capability is None:
            return
        preview = await requested_preview(request)
        if preview is None:
            return
        # An officer whose body names piu is in their own view (the query was already bound by ViewParams). The public
        # preview keeps the same capabilities from either own view (tests/test_views.py), so only piu asks who it is.
        own = PIU if preview == PIU and officer(viewer_from_headers(request.headers)) else STAFF
        found = applied(held, own, preview)
        if not found.preview or found.allows(capability):
            return
        needed = held.capabilities[capability]
        if needed.quiet:
            raise ViewRefused(200, {"recorded": False})
        if needed.act:
            raise ViewRefused(403, {"code": "preview", "error": "preview", "capability": capability,
                                    "copy_key": needed.reason, "view": found.view})
        raise ViewRefused(404, {"code": "not_in_view", "error": "not_in_view", "capability": capability,
                                "view": found.view})

    return guard
