"""Following (ticket 37): the projects a World Bank staff member follows, with each one's signals.

- PUT and DELETE /api/projects/{project_id}/follow follow and unfollow a project, and GET says whether the
  viewer follows it ({"following": true}). Follows are saved per viewer in strata.ops.follows, written as the
  app's own service principal (FollowStore); unfollowing writes a new row and never removes one. The change is
  made only for a signed-in viewer (401 no_identity) with the World Bank staff role (403 not_staff), in the
  World Bank staff view (403 preview: a preview can only take things away), on a project Prism holds a record
  for (404 unknown_project).
- GET /api/following?asof= runs the tool registry's project_signals on each project the viewer follows, as the
  viewer and as of the page's date (today's follows, with signals as the checks would have run on that date), and
  answers with the rows in the page's order: Needs a look, then Watch, then Not checked, then the projects that
  fold away (no signals, closed, in the pipeline), each by its soonest closing date and then its name, never by
  how many signals it has. With them come the counts the page states, the thresholds the checks used, the
  sources each citation marker opens (so the evidence drawer opens at once), the viewer's own open mission
  brief on each project, and the track record the replay harness stored (strata.estimates.signals_track), or
  none when it has never run. It answers only World Bank staff (403 not_staff), and never in a preview.

The role comes from the roles file's [staff] groups, through the one access helper (src/strata/server/access.py),
so who counts as staff is one line there and no code names a group.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from functools import cache
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from strata.dbx import Viewer, viewer_from_headers
from strata.lakehouse.engine import Engine, EngineError, PermissionDenied
from strata.server import evidence as evidence_routes
from strata.server.access import Access, is_author
from strata.server.engines import EngineFor
from strata.server.viewer_sql import data_through
from strata.config import load_thresholds, load_tools
from strata.tools import registry
from strata.tools.project_signals import CHECKS, thresholds_used

log = logging.getLogger("strata.server.following")
SQL = Path(__file__).resolve().parent / "sql" / "following"
STAFF = "staff"
TABLE = "strata.ops.follows"
# The page's order: the statuses shown as rows, then those that fold away.
ORDER = ("needs_a_look", "watch", "not_checked", "no_signals", "closed", "pipeline", "dropped")
FOLDED = ("no_signals", "closed", "pipeline", "dropped")
MISSION_BRIEF = "mission_brief"
OPEN_STATES = ("draft", "checked")


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _close(engine) -> None:
    close = getattr(engine, "close", None)
    if callable(close):
        close()


def _moment(value) -> dt.datetime | None:
    if value is None or value == "":
        return None
    if not isinstance(value, dt.datetime):
        value = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00").replace(" ", "T"))
    return value if value.tzinfo else value.replace(tzinfo=dt.UTC)


class FollowStore:
    """The projects each viewer follows. engine() opens the engine that reads and writes them, as the app."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    def _run(self, name: str, params: dict):
        engine = self.engine()
        try:
            return engine.run(_query(name), params)
        finally:
            _close(engine)

    def followed(self, viewer_id: str) -> dict[str, dt.datetime]:
        """The projects the viewer follows now, with when they last followed each."""
        result = self._run("followed", {"viewer_id": viewer_id})
        return {row[0]: _moment(row[1]) for row in result.rows}

    def follows(self, viewer_id: str, project_id: str) -> bool:
        return project_id in self.followed(viewer_id)

    def change(self, viewer_id: str, project_id: str, following: bool, at: dt.datetime) -> None:
        self._run("change", {"viewer_id": viewer_id, "project_id": project_id, "following": following,
                             "changed_at": at.astimezone(dt.UTC).replace(tzinfo=None)})


def _iso_day(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, dt.date) else str(value)[:10]


# A plan row's fields in the evidence drawer, under STEP's names, as ticket 28 lays out a plan row: each with the
# kind it is written as. Then the fields a check adds, and the fields it fired on, which the drawer highlights
# (the 37 brief, section 4.3): the date or amounts its line states.
PLAN_FIELDS = (("description", "text"), ("method", "text"), ("market_approach", "text"), ("review_type", "text"),
               ("estimated_amount_usd", "usd"), ("process_status", "text"))
CHECK_FIELDS = {"completion_passed": (("planned_completion_on", "date"), ("planned_completion_plan_date", "date")),
                "above_estimate": (("signed_on", "date"), ("actual_amount_usd", "usd")),
                "late_direct": (("first_plan_date", "date"),)}
FIRED_ON = {"completion_passed": ("planned_completion_on",), "above_estimate": ("actual_amount_usd", "estimated_amount_usd"),
            "late_direct": ("estimated_amount_usd", "first_plan_date")}


def _plan_record(item: dict, checks: list[str]) -> dict:
    """A plan row a signal rests on, as the drawer's record view shows it, with the fields its checks fired on
    highlighted."""
    wanted = [*PLAN_FIELDS, *(field for check in checks for field in CHECK_FIELDS.get(check, ()))]
    marked = {key for check in checks for key in FIRED_ON.get(check, ())}
    fields, seen = [], set()
    for key, kind in wanted:
        if key in seen or item.get(key) in (None, ""):
            continue
        seen.add(key)
        fields.append({"key": key, "value": item[key], "kind": kind, **({"highlight": True} if key in marked else {})})
    return {"reference": item["activity_reference_no"], "activity_reference_no": item["activity_reference_no"],
            "fields": fields, "public_from": item["public_from"], "source": item["source"]}


def _evidence(engine: Engine, result: dict, as_of: dt.date) -> list[dict]:
    """The source each signal's citation marker opens, as the evidence drawer shows it: a plan row with the fields
    its checks fired on highlighted, and any other record as the drawer reads it by its evidence id."""
    plans: dict[str, tuple[dict, list[str]]] = {}
    others: list[str] = []
    for row in result.get("rows") or []:
        for item in row["items"]:
            evidence_id = item["evidence_id"]
            if isinstance(item.get("source"), dict) and item["source"].get("document_type") == "Procurement Plan":
                plans.setdefault(evidence_id, (item, []))[1].append(row["check"])
            elif evidence_id not in others:
                others.append(evidence_id)
    events = [{"id": evidence_id, "kind": "record", "tool": None, "stratum": "What", "short_name": None,
               "row": _plan_record(item, checks), "highlights": []} for evidence_id, (item, checks) in plans.items()]
    for evidence_id in others:
        found = evidence_routes.read(engine, evidence_id, as_of)
        if found is not None:
            events.append(found)
    return events


def _order(entry: dict) -> tuple:
    project = entry["project"] or {}
    closing = project.get("closing_date")
    return (ORDER.index(entry["status"]) if entry["status"] in ORDER else len(ORDER), closing is None, closing or "",
            project.get("project_name") or "")


def _counts(entries: list[dict]) -> dict:
    statuses = [entry["status"] for entry in entries]
    partly = [entry for entry in entries if entry["status"] not in ("not_checked", "closed", "pipeline", "dropped")
              and entry["counts"]["ran"] < entry["counts"]["checks"]]
    checked = sum(1 for entry in entries if entry["status"] not in ("not_checked", "closed", "pipeline", "dropped"))
    return {"total": len(entries), "checked": checked, "needs_a_look": statuses.count("needs_a_look"),
            "watch": statuses.count("watch"),
            "not_checked": statuses.count("not_checked"), "no_signals": statuses.count("no_signals"),
            "closed": sum(1 for status in statuses if status in ("closed", "dropped")),
            "pipeline": statuses.count("pipeline"),
            "ended": sum(1 for status in statuses if status in ("closed", "dropped", "pipeline")),
            "folded": sum(1 for status in statuses if status in FOLDED),
            "shown": sum(1 for status in statuses if status not in FOLDED),
            "partly": len(partly), "fully": checked - len(partly),
            "partly_folded": sum(1 for entry in partly if entry["status"] in FOLDED)}


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: FollowStore | None, access: Access,
               drafts, today: Callable[[], dt.date], now: Callable[[], dt.datetime], reference: Callable[[], str],
               track_record: Callable[[Engine], dict | None],
               examples: Callable[[Viewer], set[str]] | None = None) -> None:
    """drafts is the draft store, for the viewer's open mission briefs; track_record reads the replay harness's
    stored results (strata.estimates.signals_track.stored); examples gives the projects the seed command followed for
    the viewer (ticket 41), which the follow control and Following label as examples while the viewer follows them."""

    def seeded(viewer: Viewer) -> set[str]:
        return examples(viewer) if examples is not None else set()

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def refused(status: int, code: str, **details) -> JSONResponse:
        return JSONResponse({"code": code, **details}, status_code=status, headers={"Cache-Control": "no-store"})

    # A preview never reaches these routes: the view switch's guard answers first (ticket 40; src/strata/server/views.py).
    def allowed(viewer: Viewer) -> JSONResponse | None:
        if not viewer.user_id:
            return refused(401, "no_identity")
        if not access.is_staff(viewer):
            return refused(403, "not_staff")
        if store is None or engine_for is None:
            return refused(503, "no_data_service")
        return None

    def guarded(what: str, act: Callable[[], object]):
        try:
            return act()
        except PermissionDenied:
            return refused(403, "permission")
        except EngineError:
            ref = reference()
            log.exception("The data service failed on %s, reference %s.", what, ref)
            return refused(503, "data_service", trace_id=ref)

    def known(viewer: Viewer, project_id: str) -> bool:
        """Whether Prism holds a record of the project, read as the viewer, without running the checks."""
        with engine_for(viewer) as engine:
            return bool(engine.run(_query("known"), {"project_id": project_id, "as_of": today()}).rows)

    @app.get("/api/projects/{project_id}/follow")
    def follow_state(project_id: str, viewer: Viewer = Depends(current_viewer)):
        refusal = allowed(viewer)
        if refusal is not None:
            return refusal
        def read():
            following = store.follows(viewer.user_id, project_id.upper())
            # A follow the seed command made for the viewer (ticket 41), which the control says it made.
            return {"following": following,
                    **({"example": True} if following and project_id.upper() in seeded(viewer) else {})}
        return guarded(f"the follow of {project_id}", read)

    def change(project_id: str, viewer: Viewer, following: bool):
        refusal = allowed(viewer)
        if refusal is not None:
            return refusal
        pid = project_id.upper()

        def act():
            if following and not known(viewer, pid):
                return refused(404, "unknown_project")
            store.change(viewer.user_id, pid, following, now())
            return {"following": following}
        return guarded(f"{'following' if following else 'unfollowing'} {pid}", act)

    @app.put("/api/projects/{project_id}/follow")
    def follow(project_id: str, viewer: Viewer = Depends(current_viewer)):
        return change(project_id, viewer, True)

    @app.delete("/api/projects/{project_id}/follow")
    def unfollow(project_id: str, viewer: Viewer = Depends(current_viewer)):
        return change(project_id, viewer, False)

    def open_briefs(viewer: Viewer) -> dict[str, dict]:
        """The viewer's own newest open mission brief on each project: only its author can act on a draft."""
        if drafts is None:
            return {}
        newest: dict[str, object] = {}
        for draft in drafts.for_team(access.team(viewer).key, viewer.user_id):
            pid = draft.content["subject"].get("project_id")
            if (draft.kind == MISSION_BRIEF and draft.state.state in OPEN_STATES and is_author(viewer, draft.author_id)
                    and (pid not in newest or draft.created_at > newest[pid].created_at)):
                newest[pid] = draft
        return {pid: {"draft_id": draft.draft_id, "created_at": draft.created_at.astimezone(dt.UTC).isoformat()}
                for pid, draft in newest.items()}

    @app.get("/api/following")
    def following(asof: dt.date | None = None, viewer: Viewer = Depends(current_viewer)):
        refusal = allowed(viewer)
        if refusal is not None:
            return refusal
        checked_on = today()
        as_of = min(asof, checked_on) if asof else checked_on

        def read():
            followed = store.followed(viewer.user_id)
            briefs = open_briefs(viewer) if as_of == checked_on else {}
            made = seeded(viewer)
            entries, events, thresholds = [], {}, None
            with engine_for(viewer) as engine:
                for project_id, since in followed.items():
                    result = registry.call("project_signals", {"project_id": project_id},
                                           registry.Context(engine, viewer, STAFF, as_of))
                    thresholds = result["thresholds"]
                    if result["project"] is None:
                        continue
                    for event in _evidence(engine, result, as_of):
                        events.setdefault(event["id"], event)
                    counts = {**result["counts"], "not_ran": result["counts"]["checks"] - result["counts"]["ran"]}
                    entries.append({"project": result["project"], "status": result["status"], "rows": result["rows"],
                                    "checks": result["checks"], "counts": counts,
                                    "coverage": result["coverage"], "following_since": since.isoformat() if since else None,
                                    "mission_brief": briefs.get(project_id),
                                    # A follow the seed command made (ticket 41), labeled "Example".
                                    **({"example": True} if project_id in made else {})})
                if thresholds is None:
                    thresholds = thresholds_used(load_thresholds())
                through = data_through(engine)
                track = track_record(engine)
            entries.sort(key=_order)
            sources = sorted({key for entry in entries for check in entry["checks"] if check["missing"]
                              for key in [check["missing"]]})
            return JSONResponse({"as_of": as_of.isoformat(), "checked_on": checked_on.isoformat(),
                                 "past": as_of < checked_on,
                                 # Never after the date the checks ran as of (ADR 0002).
                                 "data_through": _iso_day(min(through, as_of) if through else None),
                                 "projects": entries, "counts": _counts(entries), "thresholds": thresholds,
                                 # How many checks run, and the sources they read, for the page's words and its
                                 # Data readiness link: one definition each (CLAUDE.md rule 4).
                                 "checks": len(CHECKS), "sources": list(load_tools()["project_signals"].sources),
                                 "missing": sources, "evidence": list(events.values()), "track_record": track},
                                headers={"Cache-Control": "no-store"})
        return guarded("the projects the viewer follows", read)
