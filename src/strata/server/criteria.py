"""The routes of "Check your criteria", section 5 of the package workspace (ticket 31; src/strata/criteria).

For a package from a plan row, under /api/packages/{step_reference}/criteria, and for a package planned from a
sentence, under /api/planned-packages/{package_id}/criteria:

- GET .../criteria?asof=&view= gives the section's collapsed state with the page (strata.criteria.workflow.summary):
  how many comparable packages published their qualification criteria, the viewer's own saved comparison with
  its text and the saved package-level run, each only while the comparable packages are the same.
- POST .../criteria/run takes {"view": "staff", "asof": null} and streams the package-level run as
  text/event-stream: step events, then a package_run event, or an error event, and last a done event.
- POST .../criteria/compare takes {"text": "...", "view": "staff", "asof": null} and streams the comparison: a
  saved event once the text is kept, step events, then a comparison event (with the refusal key when the text
  asks for something Strata does not do), or an error event with a code from COMPARE_ERRORS, and a done event.

The pasted text arrives only in a request body, never in an address, and is kept with its owner (CLAUDE.md rule 8):
only the person who pasted it reads it back. A preview can read the section but compares nothing: 403 preview. A
planned package is read only by the person who made it, as its other routes do; anyone else gets 404.

Both runs pass ticket 24's six checks (strata.agent.answer_check.SixChecks, the app's one instance), asked as the
viewer, in the request's view and as of its date.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from strata.agent.answer_check import SixChecks
from strata.config import Thresholds
from strata.criteria import workflow
from strata.criteria.store import CriteriaStore
from strata.dbx import Viewer, viewer_from_headers
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.server.engines import EngineFor
from strata.server.tags import MODEL
from strata.tools import registry, search_passages

log = logging.getLogger("strata.server.criteria")
STAFF = "staff"
VIEWS = Literal["staff", "piu", "public"]
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
KEEP_ALIVE = ": keep-alive\n\n"


class RunRequest(BaseModel):
    view: VIEWS = "staff"
    asof: dt.date | None = None


class CompareRequest(BaseModel):
    text: str = Field(max_length=200_000)
    view: VIEWS = "staff"
    asof: dt.date | None = None


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False, default=str)}\n\n"


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, **details}, status_code=status, headers={"Cache-Control": "no-store"})


def new_check_id() -> str:
    return f"chk-{uuid.uuid4().hex[:12]}"


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: CriteriaStore | None,
               reader_for: Callable[[], object | None], planned: Callable[[Viewer, str], workflow.Package | None],
               thresholds: Thresholds, today: Callable[[], dt.date], now: Callable[[], dt.datetime],
               new_check_id: Callable[[], str], reference: Callable[[], str], heartbeat_seconds: float,
               six_checks: SixChecks) -> None:
    max_chars = int(thresholds.value("criteria.max_chars"))

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def as_of_for(asof: dt.date | None) -> dt.date:
        return min(asof, today()) if asof else today()

    def tools_for(engine, viewer: Viewer, view: str, as_of: dt.date):
        context = registry.Context(engine, viewer, view, as_of)
        return (lambda name, arguments: registry.call(name, arguments, context),
                lambda passage_id: search_passages.read_passage(engine, passage_id, as_of))

    def checking(viewer: Viewer, body: RunRequest | CompareRequest) -> workflow.Checking:
        return workflow.Checking(six_checks, viewer, body.view, as_of_for(body.asof))

    def step_package(step_reference: str) -> workflow.Package:
        return workflow.Package(f"step:{step_reference}", step_reference, {"step_reference": step_reference})

    def resolve(viewer: Viewer, kind: str, key: str) -> workflow.Package | JSONResponse:
        if kind == "step":
            return step_package(key)
        found = planned(viewer, key)
        return found if found is not None else refused(404, "unknown_package")

    def read_summary(viewer: Viewer, package: workflow.Package, view: str, asof: dt.date | None):
        if engine_for is None:
            return refused(503, "no_data_service")
        try:
            with engine_for(viewer) as engine:
                call_tool, _ = tools_for(engine, viewer, view, as_of_for(asof))
                return workflow.summary(call_tool, package, store, viewer.user_id, thresholds)
        except PermissionDenied:
            return refused(403, "permission")
        except (EngineError, registry.ToolContractError):
            ref = reference()
            log.exception("I couldn't read section 5 of %s, reference %s.", package.key, ref)
            return refused(503, "data_service", request_id=ref)

    async def stream(viewer: Viewer, package: workflow.Package, view: str, asof: dt.date | None,
                     events: Callable, errors: tuple[str, ...]) -> AsyncIterator[str]:
        try:
            with engine_for(viewer) as engine:
                call_tool, read_passage = tools_for(engine, viewer, view, as_of_for(asof))
                async for item in with_heartbeats(events(call_tool, read_passage), heartbeat_seconds):
                    yield KEEP_ALIVE if item is HEARTBEAT else frame(item)
        except workflow.CompareError as error:
            ref = reference()
            log.warning("Section 5 of %s could not compare the criteria (%s), reference %s.", package.key, error.code, ref)
            yield frame(Event("error", {"code": error.code if error.code in errors else "internal", "request_id": ref}))
        except (PermissionDenied, EngineError, registry.ToolContractError):
            ref = reference()
            log.exception("Section 5 of %s failed on the data service, reference %s.", package.key, ref)
            yield frame(Event("error", {"code": "data_service", "request_id": ref}))
        except Exception:
            ref = reference()
            log.exception("Section 5 of %s failed, reference %s.", package.key, ref)
            yield frame(Event("error", {"code": "internal", "request_id": ref}))
        yield frame(Event("done", {}))

    def start_run(viewer: Viewer, package: workflow.Package, body: RunRequest):
        if engine_for is None:
            return refused(503, "no_data_service")
        events = lambda call_tool, read_passage: workflow.package_run(  # noqa: E731
            call_tool, read_passage, package, store, viewer.user_id, thresholds, now, new_check_id,
            checking(viewer, body))
        return StreamingResponse(stream(viewer, package, body.view, body.asof, events, ("data_service", "internal")),
                                 media_type="text/event-stream", headers=STREAM_HEADERS)

    def start_compare(viewer: Viewer, package: workflow.Package, body: CompareRequest):
        if not viewer.user_id:
            return refused(401, "no_identity")
        text = body.text.strip()
        if not text:
            return refused(422, "empty")
        if len(text) > max_chars:
            return refused(422, "too_long", max_chars=max_chars)
        if engine_for is None or store is None:
            return refused(503, "no_data_service")
        events = lambda call_tool, _read: workflow.compare(  # noqa: E731
            call_tool, reader_for, package, text, store, viewer.user_id, thresholds, now, new_check_id,
            checking(viewer, body))
        return StreamingResponse(stream(viewer, package, body.view, body.asof, events, workflow.COMPARE_ERRORS),
                                 media_type="text/event-stream", headers=STREAM_HEADERS)

    for prefix, kind in (("/api/packages/{key}", "step"), ("/api/planned-packages/{key}", "planned")):
        def routes(kind: str = kind, prefix: str = prefix):
            @app.get(f"{prefix}/criteria", name=f"criteria_summary_{kind}")
            def criteria_summary(key: str, asof: dt.date | None = None, view: VIEWS = "staff",
                                 viewer: Viewer = Depends(current_viewer)):
                package = resolve(viewer, kind, key)
                if isinstance(package, JSONResponse):
                    return package
                return read_summary(viewer, package, view, asof)

            @app.post(f"{prefix}/criteria/run", name=f"criteria_run_{kind}", tags=[MODEL])
            def criteria_run(key: str, body: RunRequest, viewer: Viewer = Depends(current_viewer)):
                package = resolve(viewer, kind, key)
                if isinstance(package, JSONResponse):
                    return package
                return start_run(viewer, package, body)

            @app.post(f"{prefix}/criteria/compare", name=f"criteria_compare_{kind}", tags=[MODEL])
            def criteria_compare(key: str, body: CompareRequest, viewer: Viewer = Depends(current_viewer)):
                package = resolve(viewer, kind, key)
                if isinstance(package, JSONResponse):
                    return package
                return start_compare(viewer, package, body)
        routes()
