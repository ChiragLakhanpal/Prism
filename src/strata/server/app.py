"""The server shell: health, identity and the answer stream.

- GET /api/health says the server is up.
- GET /api/me names the viewer the Databricks App forwarded, and never returns the token.
- POST /api/ask takes a question and streams a run's events as text/event-stream, then a
  final done event with the run id. A run that breaks ends with an error event whose
  details stay in the server log.

Each request builds its own Viewer and Turn; create_app keeps only settings, never a viewer.
"""

import json
import logging
from collections.abc import AsyncIterator, Callable

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from strata.dbx import Viewer, viewer_from_headers
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event, Runner, Turn, new_run_id as random_run_id, no_agent

log = logging.getLogger("strata.server")
KEEP_ALIVE = ": keep-alive\n\n"
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


def current_viewer(request: Request) -> Viewer:
    return viewer_from_headers(request.headers)


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def create_app(runner: Runner = no_agent, heartbeat_seconds: float = 15.0,
               new_run_id: Callable[[], str] = random_run_id) -> FastAPI:
    app = FastAPI(title="Strata", docs_url=None, redoc_url=None, openapi_url=None)

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
