"""The deep research routes (ticket 148).

POST /api/projects/{project_id}/research runs the research and streams it as /api/ask's events (src/strata/research/
run.py): a step for the project's facts, one for each source, one for writing and one for checking, then the kept
sentences, the evidence they cite, the check counts, each removed sentence, and done. An error event names a code of
run.ERRORS. With {"reuse": true} it writes the brief from the latest run already kept, without reading the sources.
With research.live_sources false in config/thresholds.toml (the demo's setting, ticket 152), every POST is a reuse:
no source is read, whatever the body says; each source's step comes from the stored run with its read date, one by
one; the writer and the checks run live; a writer or judge that fails keeps the stored brief instead of an error; and
a project with no stored run ends with not_fetched.

GET /api/projects/{project_id}/research returns the latest brief kept for the project, which calls no model, or
{"status": "none"} when none was written, each with live_sources, so the tab names its button for the setting.

A brief on public items alone may be read and started by every view. A run in the staff view also reads the field
photos the viewer's team kept for the project (ticket 150; src/strata/server/field_photos.py), through the one access
rule, and the brief written from such a run is kept for that team: GET gives it only to that team, and everyone else
the latest brief on public items. The run, its items and the brief are written as the app's own service principal, as
drafts are.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import AsyncIterator, Callable

from fastapi import Depends, FastAPI, Path, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from strata.agent.answer_check import SixChecks
from strata.dbx import Viewer, viewer_from_headers
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.research import run as research_run
from strata.research.photos import PhotoStore
from strata.research.store import ResearchStore
from strata.server import field_photos as photo_routes
from strata.server.access import Access
from strata.server.criteria import KEEP_ALIVE, STREAM_HEADERS, VIEWS, frame, refused
from strata.server.engines import EngineFor
from strata.server.tags import MODEL
from strata.tools import registry

log = logging.getLogger("strata.server.research")
PROJECT = r"^P\d{6}$"


class ResearchRequest(BaseModel):
    view: VIEWS = "staff"
    asof: dt.date | None = None
    reuse: bool = False


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: ResearchStore | None,
               kit: Callable[[], research_run.Kit | None], writer: Callable[[], object | None], today: Callable[[], dt.date],
               now: Callable[[], dt.datetime], new_run_id: Callable[[], str], reference: Callable[[], str],
               heartbeat_seconds: float, six_checks: SixChecks, environ=None, access: Access | None = None,
               photos: PhotoStore | None = None) -> None:
    """kit gives ticket 147's readers, and writer the brief's writer, each when a run starts, so a test gives its own.
    access is the one access rule and photos the field photo store (ticket 150)."""

    def team_of(viewer: Viewer) -> str | None:
        return access.team(viewer).key if access is not None and viewer.user_id else None

    def live_sources() -> bool:
        return bool(six_checks.thresholds.value("research.live_sources"))

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def as_of_for(asof: dt.date | None) -> dt.date:
        return min(asof, today()) if asof else today()

    async def stream(run: research_run.Run, request: research_run.Request) -> AsyncIterator[str]:
        try:
            async for item in with_heartbeats(run.events(request), heartbeat_seconds):
                yield KEEP_ALIVE if item is HEARTBEAT else frame(item)
        except research_run.ResearchError as error:
            log.warning("Research run %s on %s stopped (%s).", request.run_id, request.project_id, error.code)
            yield frame(Event("error", {"code": error.code if error.code in research_run.ERRORS else "internal"}))
            yield frame(Event("done", {"run_id": request.run_id, "status": "stopped"}))
        except (PermissionDenied, EngineError, registry.ToolContractError):
            ref = reference()
            log.exception("Research run %s failed on the data service, reference %s.", request.run_id, ref)
            yield frame(Event("error", {"code": "data_service", "request_id": ref}))
            yield frame(Event("done", {"run_id": request.run_id, "status": "stopped"}))
        except Exception:
            ref = reference()
            log.exception("Research run %s failed, reference %s.", request.run_id, ref)
            yield frame(Event("error", {"code": "internal", "request_id": ref}))
            yield frame(Event("done", {"run_id": request.run_id, "status": "stopped"}))

    @app.post("/api/projects/{project_id}/research", tags=[MODEL])
    def start_research(body: ResearchRequest, project_id: str = Path(pattern=PROJECT),
                       viewer: Viewer = Depends(current_viewer)):
        if engine_for is None or store is None:
            return refused(503, "no_data_service")
        live = live_sources()
        run = research_run.Run(engine_for, kit() if live else None, store, writer(), six_checks, now, environ)
        # Only a run in the staff view reads the team's field photos: a preview of another view reads none.
        read_photos = (photo_routes.reader(photos, access, viewer)
                       if access is not None and photos is not None and body.view == "staff" else None)
        request = research_run.Request(viewer, body.view, project_id, as_of_for(body.asof), new_run_id(),
                                       body.reuse or not live, stored_only=not live, team_key=team_of(viewer),
                                       field_photos=read_photos)
        return StreamingResponse(stream(run, request), media_type="text/event-stream", headers=STREAM_HEADERS)

    @app.get("/api/projects/{project_id}/research")
    def read_research(project_id: str = Path(pattern=PROJECT), asof: dt.date | None = None, view: str = "staff",
                      viewer: Viewer = Depends(current_viewer)):
        if store is None:
            return refused(503, "no_data_service")
        try:
            # A preview of another view never reads a team's brief (a preview only takes things away).
            found = store.latest_brief(project_id, as_of_for(asof), team_of(viewer) if view == "staff" else None)
        except (PermissionDenied, EngineError):
            ref = reference()
            log.exception("The research brief of %s could not be read, reference %s.", project_id, ref)
            return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)
        live = live_sources()
        return ({"status": "none", "project_id": project_id, "live_sources": live} if found is None
                else {"status": "written", **found, "live_sources": live})
