"""The server shell: health, identity, the answer stream and the plan check.

- GET /api/health says the server is up.
- GET /api/me names the viewer the Databricks App forwarded, and never returns the token.
- POST /api/ask takes a question and streams a run's events as text/event-stream, then a
  final done event with the run id. A run that breaks ends with an error event whose
  details stay in the server log.
- GET /api/projects/{project_id}/procurement/{agency_id}[/{version}] checks one implementing
  agency's Procurement Plan, its latest version or the one dated version, through the tool
  registry's check_plan, as the viewer. It takes the page's ?asof= and ?view=. A viewer whose
  token cannot read strata gets 403 with the code permission and no rows.

Each request builds its own Viewer, Turn and engine; create_app keeps only settings, never a viewer.
"""

import datetime as dt
import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from strata.dbx import Viewer, viewer_from_headers
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event, Runner, Turn, new_run_id as random_run_id, no_agent
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.server import engines
from strata.tools import registry

log = logging.getLogger("strata.server")
View = Literal["staff", "piu", "public"]  # registry.VIEWS
KEEP_ALIVE = ": keep-alive\n\n"
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


def current_viewer(request: Request) -> Viewer:
    return viewer_from_headers(request.headers)


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def create_app(runner: Runner = no_agent, heartbeat_seconds: float = 15.0,
               new_run_id: Callable[[], str] = random_run_id, engine_for: engines.EngineFor | None = None) -> FastAPI:
    """engine_for makes the engine for each request's viewer; without it, the environment names one."""
    engine_for = engine_for or engines.from_environment()
    app = FastAPI(title="Strata", docs_url=None, redoc_url=None, openapi_url=None)

    def run_tool(name: str, arguments: dict, viewer: Viewer, view: str, as_of: dt.date | None):
        """One tool call as the viewer, or the error a page can show: permission, or the data service."""
        if engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            with engine_for(viewer) as engine:
                return registry.call(name, arguments, registry.Context(engine, viewer, view, as_of))
        except PermissionDenied:
            return JSONResponse({"code": "permission"}, status_code=403)
        except EngineError:
            trace_id = uuid.uuid4().hex
            log.exception("The data service failed on %s, reference %s.", name, trace_id)
            return JSONResponse({"code": "data_service", "trace_id": trace_id}, status_code=503)

    @app.get("/api/projects/{project_id}/procurement/{agency_id}")
    def check_latest_plan(project_id: str, agency_id: str, asof: dt.date | None = None, view: View = "staff",
                          viewer: Viewer = Depends(current_viewer)):
        return run_tool("check_plan", {"project_id": project_id, "implementing_agency": agency_id},
                        viewer, view, asof)

    @app.get("/api/projects/{project_id}/procurement/{agency_id}/{version}")
    def check_plan_version(project_id: str, agency_id: str, version: dt.date, asof: dt.date | None = None,
                           view: View = "staff", viewer: Viewer = Depends(current_viewer)):
        return run_tool("check_plan", {"project_id": project_id, "implementing_agency": agency_id,
                                       "plan_date": version}, viewer, view, asof)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/me")
    def me(viewer: Viewer = Depends(current_viewer)) -> dict:
        return {"email": viewer.email, "name": viewer.name, "signed_in": viewer.signed_in,
                "has_token": viewer.token is not None}

    @app.post("/api/ask")
    async def ask(body: AskRequest, viewer: Viewer = Depends(current_viewer)) -> StreamingResponse:
        turn = Turn(question=body.question, viewer=viewer, run_id=new_run_id())
        return StreamingResponse(stream(turn), media_type="text/event-stream", headers=STREAM_HEADERS)

    async def stream(turn: Turn) -> AsyncIterator[str]:
        try:
            async for item in with_heartbeats(runner(turn), heartbeat_seconds):
                yield KEEP_ALIVE if item is HEARTBEAT else frame(item)
        except Exception:
            log.exception("Run %s failed.", turn.run_id)
            yield frame(Event("error", {"code": "internal"}))
        yield frame(Event("done", {"run_id": turn.run_id}))

    return app
