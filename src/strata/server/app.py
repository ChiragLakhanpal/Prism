"""The server shell: health, identity, the data-freshness stamp, the answer stream and the plan check.

- GET /api/health says the server is up.
- GET /api/me names the viewer the Databricks App forwarded, and never returns the token.
- GET /api/me/warehouse runs one query as the viewer and returns the user the warehouse says
  ran it, so a deploy can show that each person's queries run as that person.
- GET /api/freshness returns the data-freshness stamp's day ({"data_through": "2026-10-21"},
  or null before any daily source has loaded), read from strata.ops as the viewer. It answers
  401 with no forwarded identity, 403 with the code permission when the warehouse refuses the
  viewer, 504 when the warehouse takes longer than the thresholds file's
  app.stamp_timeout_seconds, and 502 when it fails, with the details only in the server log.
- POST /api/ask takes a question and streams a run's events as text/event-stream, then a
  final done event with the run id. A run that breaks ends with an error event whose
  details stay in the server log.
- GET /api/projects/{project_id}/procurement/{agency_id}[/{version}] checks one implementing
  agency's Procurement Plan, its latest version or the one dated version, through the tool
  registry's check_plan, as the viewer. It takes the page's ?asof= and ?view=. A viewer whose
  token cannot read strata gets 403 with the code permission and no rows.
- Every other address outside /api gets the built web app, when create_app is given one.

Each request a viewer makes, except /api/health and the web app's files, writes one usage event
(src/strata/server/usage.py) and sends one trace (src/strata/server/tracing.py), whose id the
event keeps.

Each request builds its own Viewer, Turn and engine; create_app keeps only settings, never a viewer.
"""

import asyncio
import datetime as dt
import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from opentelemetry import trace
from pydantic import BaseModel, Field

from strata.config import load_thresholds
from strata.dbx import Viewer, viewer_from_headers
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event, Runner, Turn, new_run_id as random_run_id, no_agent
from strata.lakehouse.engine import Engine, EngineError, PermissionDenied
from strata.server import engines, tracing
from strata.server.usage import UsageEvent, UsageLog
from strata.server.viewer_sql import data_through, warehouse_user
from strata.tools import registry

log = logging.getLogger("strata.server")
KEEP_ALIVE = ": keep-alive\n\n"
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
# The platform's check that the app is up. It is not a viewer's request, so it is not counted.
UNCOUNTED = {"/api/health"}
# The view the server applies. Until ticket 40 adds the implementing agency and public previews,
# every request sees the World Bank staff view, whatever ?view= asks for.
STAFF = "staff"
IMMUTABLE = "public, max-age=31536000, immutable"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


def current_viewer(request: Request) -> Viewer:
    return viewer_from_headers(request.headers)


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def refused(status: int, code: str) -> JSONResponse:
    return JSONResponse({"code": code}, status_code=status, headers={"Cache-Control": "no-store"})


def create_app(runner: Runner = no_agent, heartbeat_seconds: float = 15.0,
               new_run_id: Callable[[], str] = random_run_id, engine_for: engines.EngineFor | None = None,
               stamp_timeout_seconds: float | None = None, usage: UsageLog | None = None,
               tracer_provider: trace.TracerProvider | None = None, web_dist: Path | None = None) -> FastAPI:
    """The app.

    engine_for makes the engine for each request's viewer; without it, the environment names one.
    usage receives one event per request, and tracer_provider (the process's global one when None)
    one span. web_dist is the built web app: its files are served as they are, and every other
    address outside /api gets its index.html, whose router shows the page or the not-found page.
    """
    engine_for = engine_for or engines.from_environment()
    web = web_dist.resolve() if web_dist is not None else None

    def web_file(path: str) -> Path | None:
        """The built web app's file at this address, if there is one inside it."""
        if web is None:
            return None
        candidate = (web / path.lstrip("/")).resolve()
        return candidate if candidate.is_file() and web in candidate.parents else None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if usage is not None:
            usage.start()
        try:
            yield
        finally:
            if usage is not None:
                await asyncio.to_thread(usage.stop)

    app = FastAPI(title="Strata", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    timeout = stamp_timeout_seconds or load_thresholds().value("app.stamp_timeout_seconds")
    tracer = (tracer_provider or trace.get_tracer_provider()).get_tracer("strata.server")

    @app.middleware("http")
    async def observe(request: Request, call_next):
        """One span and one usage event for each request a viewer makes."""
        path = request.url.path
        if path in UNCOUNTED or web_file(path) is not None:
            return await call_next(request)
        viewer = viewer_from_headers(request.headers)
        requested_at = dt.datetime.now(dt.UTC)
        name = f"{request.method} {path if path.startswith('/api/') else 'page'}"
        with tracer.start_as_current_span(name, kind=trace.SpanKind.SERVER) as span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("url.path", path)
            span.set_attribute("strata.view", STAFF)
            response = await call_next(request)
            span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(trace.StatusCode.ERROR)
        if usage is not None:
            usage.record(UsageEvent(viewer.user_id, path, STAFF, requested_at, tracing.trace_id(span)))
        return response

    def read_as(viewer: Viewer, read: Callable[[Engine], object]):
        with engine_for(viewer) as engine:
            return read(engine)

    async def as_viewer(viewer: Viewer, read: Callable[[Engine], object], answer: Callable[[object], dict]):
        """One read as the viewer, within the stamp's timeout, or the reason it could not run."""
        if not viewer.token:
            return refused(401, "no_identity")
        if engine_for is None:
            return refused(503, "no_data_service")
        try:
            value = await asyncio.wait_for(asyncio.to_thread(read_as, viewer, read), timeout)
        except TimeoutError:
            return refused(504, "timeout")
        except PermissionDenied:
            log.warning("The warehouse refused %s.", viewer.email or viewer.user_id)
            return refused(403, "permission")
        except EngineError:
            log.exception("A query for %s failed.", viewer.email or viewer.user_id)
            return refused(502, "unreadable")
        return JSONResponse(answer(value), headers={"Cache-Control": "no-store"})

    def run_tool(name: str, arguments: dict, viewer: Viewer, view: str, as_of: dt.date | None):
        """One tool call as the viewer, or the error a page can show: a bad request, permission, a tool
        that broke its contract, or the data service. The last two keep their details in the server log
        and give the page a reference to it."""
        if engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            with engine_for(viewer) as engine:
                return registry.call(name, arguments, registry.Context(engine, viewer, view, as_of))
        except registry.ToolError as error:  # a view or an argument the tool does not take
            return JSONResponse({"code": "bad_request", "detail": str(error)}, status_code=422)
        except PermissionDenied:
            return JSONResponse({"code": "permission"}, status_code=403)
        except registry.ToolContractError:
            reference = uuid.uuid4().hex
            log.exception("The tool %s broke its contract, reference %s.", name, reference)
            return JSONResponse({"code": "tool_contract", "trace_id": reference}, status_code=500)
        except EngineError:
            reference = uuid.uuid4().hex
            log.exception("The data service failed on %s, reference %s.", name, reference)
            return JSONResponse({"code": "data_service", "trace_id": reference}, status_code=503)

    @app.get("/api/projects/{project_id}/procurement/{agency_id}")
    def check_latest_plan(project_id: str, agency_id: str, asof: dt.date | None = None, view: str = "staff",
                          viewer: Viewer = Depends(current_viewer)):
        return run_tool("check_plan", {"project_id": project_id, "implementing_agency": agency_id},
                        viewer, view, asof)

    @app.get("/api/projects/{project_id}/procurement/{agency_id}/{version}")
    def check_plan_version(project_id: str, agency_id: str, version: dt.date, asof: dt.date | None = None,
                           view: str = "staff", viewer: Viewer = Depends(current_viewer)):
        return run_tool("check_plan", {"project_id": project_id, "implementing_agency": agency_id,
                                       "plan_date": version}, viewer, view, asof)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/me")
    def me(viewer: Viewer = Depends(current_viewer)) -> dict:
        return {"email": viewer.email, "name": viewer.name, "signed_in": viewer.signed_in,
                "has_token": viewer.token is not None}

    @app.get("/api/me/warehouse")
    async def me_on_the_warehouse(viewer: Viewer = Depends(current_viewer)):
        return await as_viewer(viewer, warehouse_user, lambda user: {"warehouse_user": user})

    @app.get("/api/freshness")
    async def freshness(viewer: Viewer = Depends(current_viewer)):
        return await as_viewer(viewer, data_through,
                               lambda day: {"data_through": day.isoformat() if day else None})

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

    if web is not None:
        @app.get("/{address:path}", include_in_schema=False)
        def page(address: str):
            if address == "api" or address.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            file = web_file(address)
            if file is not None:
                lasting = file.parent.name == "assets"  # Vite names each asset by its content
                return FileResponse(file, headers={"Cache-Control": IMMUTABLE if lasting else "no-cache"})
            return FileResponse(web / "index.html", headers={"Cache-Control": "no-cache"})

    return app
