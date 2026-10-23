"""The server shell: health, identity, the data-freshness stamp and the answer stream.

- GET /api/health says the server is up.
- GET /api/me names the viewer the Databricks App forwarded, and never returns the token.
- GET /api/me/warehouse runs one query as the viewer and returns the user the warehouse says
  ran it, so a deploy can show that each person's queries run as that person.
- GET /api/freshness returns the data-freshness stamp's day ({"data_through": "2026-10-21"},
  or null before any daily source has loaded), read from strata.ops as the viewer. It answers
  401 with no forwarded identity, 403 when the warehouse refuses the viewer, 504 when the
  warehouse takes longer than the thresholds file's app.stamp_timeout_seconds, and 502 when it
  fails, with the details only in the server log.
- POST /api/ask takes a question and streams a run's events as text/event-stream, then a
  final done event with the run id. A run that breaks ends with an error event whose
  details stay in the server log.

Each request builds its own Viewer, its own engine and its own Turn; create_app keeps only
settings, never a viewer.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from strata.config import load_thresholds
from strata.dbx import Viewer, viewer_from_headers
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event, Runner, Turn, new_run_id as random_run_id, no_agent
from strata.lakehouse.engine import AccessDenied, Engine, EngineError
from strata.server.viewer_sql import SqlAs, data_through, run_as, warehouse_user

log = logging.getLogger("strata.server")
KEEP_ALIVE = ": keep-alive\n\n"
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


def current_viewer(request: Request) -> Viewer:
    return viewer_from_headers(request.headers)


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def refused(status: int, code: str) -> JSONResponse:
    return JSONResponse({"code": code}, status_code=status, headers={"Cache-Control": "no-store"})


def create_app(runner: Runner = no_agent, heartbeat_seconds: float = 15.0,
               new_run_id: Callable[[], str] = random_run_id, sql_as: SqlAs | None = None,
               stamp_timeout_seconds: float | None = None) -> FastAPI:
    """The app. sql_as builds a viewer's own engine for each request that reads data."""
    app = FastAPI(title="Strata", docs_url=None, redoc_url=None, openapi_url=None)
    timeout = stamp_timeout_seconds or load_thresholds().value("app.stamp_timeout_seconds")

    async def as_viewer(viewer: Viewer, read: Callable[[Engine], object], answer: Callable[[object], dict]):
        """Run one read as the viewer, or say plainly why it could not run."""
        if not viewer.token:
            return refused(401, "no_identity")
        if sql_as is None:
            return refused(503, "no_warehouse")
        try:
            value = await asyncio.wait_for(asyncio.to_thread(run_as, sql_as, viewer, read), timeout)
        except TimeoutError:
            return refused(504, "timeout")
        except AccessDenied:
            log.warning("The warehouse refused %s.", viewer.email or viewer.user_id)
            return refused(403, "no_access")
        except EngineError:
            log.exception("A query for %s failed.", viewer.email or viewer.user_id)
            return refused(502, "unreadable")
        return JSONResponse(answer(value), headers={"Cache-Control": "no-store"})

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

    return app
