"""The server shell: health, identity, the answer stream and the plan check.

- GET /api/health says the server is up.
- GET /api/me names the viewer the Databricks App forwarded, and never returns the token.
- POST /api/ask takes a question, with the page's scope chip, as-of date, view and language, and
  streams a run's events as text/event-stream: steps, then the answer's sentences with their
  evidence ids, the evidence they cite, the check counts and the removed sentences, then a final
  done event with the run id and its trace ids. The verifier runs here, in the stream, on every
  answer the runner hands over, so no runner can send a sentence the checks did not see. A run that
  breaks ends with an error event whose details stay in the server log.
- GET /api/projects/{project_id}/procurement/{agency_id}[/{version}] checks one implementing
  agency's Procurement Plan, its latest version or the one dated version, through the tool
  registry's check_plan, as the viewer. It takes the page's ?asof= and ?view=. A viewer whose
  token cannot read strata gets 403 with the code permission and no rows.

Each request builds its own Viewer, Turn and engine; create_app keeps only settings, never a viewer.
"""

import asyncio
import datetime as dt
import json
import logging
import threading
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from strata.agent import traces
from strata.agent.runs import RunLog, run_row
from strata.agent.verifier import answer_events, verify
from strata.dbx import Viewer, viewer_from_headers
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import (Event, RunError, Runner, Scope, TraceIds, Turn, new_run_id as random_run_id,
                                 no_agent)
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.server import engines
from strata.tools import registry

log = logging.getLogger("strata.server")
KEEP_ALIVE = ": keep-alive\n\n"
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
# Only the verifier writes these, from the claims a runner hands over.
ANSWER_EVENTS = {"sentence", "evidence", "disagreement", "checks", "removed", "done"}


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    scope: str | None = Field(default=None, max_length=64)  # the page's scope chip: a P-code or STEP reference
    asof: dt.date | None = None
    view: Literal["staff", "piu", "public"] = "staff"
    lang: Literal["en", "fr", "es", "pt"] = "en"


def current_viewer(request: Request) -> Viewer:
    return viewer_from_headers(request.headers)


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def create_app(runner: Runner = no_agent, heartbeat_seconds: float = 15.0,
               new_run_id: Callable[[], str] = random_run_id, engine_for: engines.EngineFor | None = None,
               runs: RunLog | None = None, trace_ids: Callable[[], TraceIds] = traces.current) -> FastAPI:
    """engine_for makes the engine for each request's viewer; without it, the environment names one.
    runs writes each answer stream's run to strata.ops.agent_runs; without it, runs go to the log only.
    trace_ids reads the request's trace ids while its span is open."""
    engine_for = engine_for or engines.from_environment()
    app = FastAPI(title="Strata", docs_url=None, redoc_url=None, openapi_url=None)

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
            trace_id = uuid.uuid4().hex
            log.exception("The tool %s broke its contract, reference %s.", name, trace_id)
            return JSONResponse({"code": "tool_contract", "trace_id": trace_id}, status_code=500)
        except EngineError:
            trace_id = uuid.uuid4().hex
            log.exception("The data service failed on %s, reference %s.", name, trace_id)
            return JSONResponse({"code": "data_service", "trace_id": trace_id}, status_code=503)

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

    @app.post("/api/ask")
    async def ask(body: AskRequest, viewer: Viewer = Depends(current_viewer)) -> StreamingResponse:
        scope = Scope(chip=body.scope.strip().upper() if body.scope and body.scope.strip() else None,
                      as_of=body.asof, view=body.view, language=body.lang)
        turn = Turn(question=body.question, viewer=viewer, run_id=new_run_id(), scope=scope, trace=trace_ids())
        return StreamingResponse(stream(turn), media_type="text/event-stream", headers=STREAM_HEADERS)

    async def stream(turn: Turn) -> AsyncIterator[str]:
        """The run's events, then its row in the run log, even when the viewer leaves part way."""
        started, outcome = dt.datetime.now(dt.UTC), {"verdict": None, "error_code": "stopped"}
        try:
            async for chunk in run_events(turn, outcome):
                yield chunk
        finally:
            row = run_row(turn, outcome["verdict"], outcome["error_code"], started, dt.datetime.now(dt.UTC))
            log.info("Run %s ended: %s.", turn.run_id, row["error_code"] or row["status"])
            if runs is not None:  # its own thread, so a dropped connection cannot stop the write
                writer = threading.Thread(target=runs.record, args=(row,), name=f"strata-run-{turn.run_id}")
                writer.start()
                await asyncio.to_thread(writer.join, 60)

    async def run_events(turn: Turn, outcome: dict) -> AsyncIterator[str]:
        verdict, error_code = None, None
        try:
            async for item in with_heartbeats(runner(turn), heartbeat_seconds):
                if item is HEARTBEAT:
                    yield KEEP_ALIVE
                elif item.type == "claims":  # the verifier, with its own step, then the answer's events
                    yield frame(Event("step", {"id": "check", "kind": "check", "status": "running"}))
                    verdict = verify(item.data["claims"], turn.facts)
                    yield frame(Event("step", {"id": "check", "kind": "check", "status": "done",
                                               "removed": len(verdict.removed)}))
                    ran = [call["tool"] for call in turn.notes.tool_calls if call.get("ran")]
                    for event in answer_events(verdict, turn.facts, ran):
                        yield frame(event)
                elif item.type in ANSWER_EVENTS:
                    raise RuntimeError(f"A runner sent a {item.type} event, which only the verifier writes.")
                else:
                    error_code = item.data.get("code") if item.type == "error" else error_code
                    yield frame(item)
        except RunError as error:
            log.warning("Run %s could not answer (%s): %s", turn.run_id, error.code, error)
            error_code = error.code
            yield frame(Event("error", {"code": error.code}))
        except Exception:
            log.exception("Run %s failed.", turn.run_id)
            error_code = "internal"
            yield frame(Event("error", {"code": "internal"}))
        done = {"run_id": turn.run_id}
        if turn.trace is not None and (turn.trace.application_insights or turn.trace.mlflow):
            done["trace_ids"] = {"application_insights": turn.trace.application_insights, "mlflow": turn.trace.mlflow}
        outcome.update(verdict=verdict, error_code=error_code or (None if verdict else "no_answer"))
        yield frame(Event("done", done))

    return app
