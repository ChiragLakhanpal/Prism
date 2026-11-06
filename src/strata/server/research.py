"""The deep research routes (ticket 148).

POST /api/projects/{project_id}/research runs the research and streams it as /api/ask's events (src/strata/research/
run.py): a step for the project's facts, one for each source, one for writing and one for checking, then the kept
sentences, the evidence they cite, the check counts, each removed sentence, and done. An error event names a code of
run.ERRORS. With {"reuse": true} it writes the brief from the latest run already kept, without reading the sources.

GET /api/projects/{project_id}/research returns the latest brief kept for the project, which calls no model, or
{"status": "none"} when none was written.

The brief rests on public items, so every view may read and start one. The run, its items and the brief are written as
the app's own service principal, as drafts are.
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
from strata.research.store import ResearchStore
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
               heartbeat_seconds: float, six_checks: SixChecks, environ=None) -> None:
    """kit gives ticket 147's readers, and writer the brief's writer, each when a run starts, so a test gives its own."""

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
        run = research_run.Run(engine_for, kit(), store, writer(), six_checks, now, environ)
        request = research_run.Request(viewer, body.view, project_id, as_of_for(body.asof), new_run_id(), body.reuse)
        return StreamingResponse(stream(run, request), media_type="text/event-stream", headers=STREAM_HEADERS)

    @app.get("/api/projects/{project_id}/research")
    def read_research(project_id: str = Path(pattern=PROJECT), asof: dt.date | None = None,
                      viewer: Viewer = Depends(current_viewer)):
        if store is None:
            return refused(503, "no_data_service")
        try:
            found = store.latest_brief(project_id, as_of_for(asof))
        except (PermissionDenied, EngineError):
            ref = reference()
            log.exception("The research brief of %s could not be read, reference %s.", project_id, ref)
            return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)
        return {"status": "none", "project_id": project_id} if found is None else {"status": "written", **found}
