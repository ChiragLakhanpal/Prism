"""The planned package routes (ticket 15): planning a package from a sentence, its workspace, its changes, its
comparables and the Packages tab.

- POST /api/planned-packages takes {"sentence": "rural roads, Kenya, about US$15 million", "read": true,
  "view": "staff"} and streams the plan-a-package workflow as text/event-stream (src/strata/packages/
  workflow.py): a form event with the package form schema, step events (read, compute, save, compare), a
  package event with the saved package, a
  comparables event with find_comparables' result, or an error event with a code from PLAN_ERRORS, and last
  a done event with the run id. With "read": false the person sets the criteria themselves: no reading,
  and the package is saved with their sentence and no criteria.
- GET /api/planned-packages lists the Packages tab's rows: the viewer's packages and the plans they checked,
  newest first.
- GET /api/planned-packages/{package_id} gives one package with the package form schema it is shown in.
- POST /api/planned-packages/{package_id} takes one change, {"field": "method", "action": "set", "value":
  "ICB"}, saves it as a new save and answers with the package as it is now. The actions are set, remove,
  keep (a guess) and use_computed. A change to the plan also takes "plan_before_range".
- GET /api/comparables runs find_comparables through the tool registry as the viewer for a package with no
  STEP row, with the tool's criteria as query parameters (the package's comparables_query), ?asof= and
  ?view=.

A package is read and changed only by the person who made it: anyone else gets 404 unknown_package, as for a
package that does not exist. Packages are written by the app's own service principal, like drafts. A preview
can read the packages but change nothing: 403 preview. Changes to one package are made one at a time, so a
change that arrives while another is being made starts from that one's save.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import math
import threading
import time
import uuid
from collections.abc import AsyncIterator, Callable
from functools import cache
from importlib import resources
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from strata.agent.runs import RunLog, run_row
from strata.config import Thresholds
from strata.dbx import Viewer, viewer_from_headers
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event, Scope, TraceIds, Turn
from strata.lakehouse.engine import Engine, EngineError, PermissionDenied
from strata.packages import criteria as criteria_of, workflow
from strata.packages.form import Form, Invalid, payload
from strata.packages.store import PackageStore
from strata.server.engines import EngineFor
from strata.tools import registry

log = logging.getLogger("strata.server.packages")
STAFF = "staff"
VIEWS = Literal["staff", "piu", "public"]
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
KEEP_ALIVE = ": keep-alive\n\n"
NUMBERS = ("size_from_usd", "size_to_usd")
DATES = ("notice_from", "notice_to")


class PlanRequest(BaseModel):
    sentence: str = Field(min_length=1, max_length=500)
    read: bool = True
    view: VIEWS = "staff"


class ChangeRequest(BaseModel):
    field: str = Field(min_length=1, max_length=64)
    action: Literal["set", "remove", "keep", "use_computed"]
    value: str | int | float | None = None
    plan_before_range: bool | None = None
    view: VIEWS = "staff"


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.packages") / "sql" / f"{name}.sql").read_text()


def _countries_sql() -> str:
    return _sql("countries")


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, **details}, status_code=status, headers={"Cache-Control": "no-store"})


def comparables_criteria(request: Request) -> dict | JSONResponse:
    """find_comparables' criteria from a query, by the tool's own parameter names, for both comparables routes:
    sizes as finite numbers and the notice dates as dates, or 422 bad_request saying which one is not. The
    registry checks the rest."""
    criteria: dict = {name: value for name, value in request.query_params.items() if name not in ("asof", "view")}
    for name in NUMBERS:
        if name in criteria:
            try:
                number = float(criteria[name])
            except ValueError:
                number = math.nan
            if not math.isfinite(number):  # float() reads inf and nan, which no JSON answer can hold
                return refused(422, "bad_request", detail=f"{name} must be a number.")
            criteria[name] = number
    for name in DATES:
        if name in criteria:
            try:
                criteria[name] = dt.date.fromisoformat(criteria[name])
            except ValueError:
                return refused(422, "bad_request", detail=f"{name} must be a date.")
    return criteria


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: PackageStore | None,
               reader_for: Callable[[], object | None], form: Form, thresholds: Thresholds,
               today: Callable[[], dt.date], now: Callable[[], dt.datetime], new_package_id: Callable[[], str],
               new_save_id: Callable[[], str], new_run_id: Callable[[], str], runs: RunLog | None,
               trace_ids: Callable[[], TraceIds], reference: Callable[[], str], heartbeat_seconds: float) -> None:
    max_months = float(thresholds.value("past_range.max_plan_months"))
    # One lock per package, so two changes to it are made one after the other (review round 2, P1).
    locks: dict[str, threading.Lock] = {}
    locks_lock = threading.Lock()

    def lock_for(package_id: str) -> threading.Lock:
        with locks_lock:
            return locks.setdefault(package_id, threading.Lock())

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def countries(viewer: Viewer) -> list[dict]:
        """The World Bank's country list, read as the viewer."""
        with engine_for(viewer) as engine:
            result = engine.run(_countries_sql(), {})
        return [{"code": code, "name": name} for code, name in result.rows]

    def codes(viewer: Viewer) -> dict[str, str]:
        return {entry["code"]: entry["name"] for entry in countries(viewer)}

    def project_countries(viewer: Viewer, project_ids: set[str]) -> dict[str, str | None]:
        """Each checked plan's project's country code, read as the viewer, one project at a time: a person has
        checked the plans of a few projects."""
        found = {}
        with engine_for(viewer) as engine:
            for project_id in sorted(project_ids):
                rows = engine.run(_sql("project_country"), {"project_id": project_id}).rows
                found[project_id] = rows[0][0] if rows else None
        return found

    def find(viewer: Viewer, view: str, as_of: dt.date | None, query: dict) -> dict:
        with engine_for(viewer) as engine:
            return registry.call("find_comparables", query, registry.Context(engine, viewer, view, as_of or today()))

    def guarded(what: str, act: Callable[[], object]):
        """One use of the store and the viewer's reads, or the error a page can show."""
        if store is None or engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            return act()
        except PermissionDenied:
            ref = reference()
            log.exception("A read or write was refused on %s, reference %s.", what, ref)
            return JSONResponse({"code": "permission", "trace_id": ref}, status_code=403)
        except EngineError:
            ref = reference()
            log.exception("The data service failed on %s, reference %s.", what, ref)
            return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)

    def mine(viewer: Viewer, package_id: str):
        saved = store.get(package_id)
        return saved if saved is not None and saved.author_id == viewer.user_id else None

    def allowed(viewer: Viewer) -> JSONResponse | None:
        """A signed-in viewer. A preview never reaches here: the view switch's guard refuses it (ticket 40)."""
        if not viewer.user_id:
            return refused(401, "no_identity")
        return None

    # ── Planning ─────────────────────────────────────────────────────────

    @app.post("/api/planned-packages")
    async def start_package(body: PlanRequest, viewer: Viewer = Depends(current_viewer)):
        if (refusal := allowed(viewer)) is not None:
            return refusal
        if store is None or engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        planning = workflow.Planning(body.sentence.strip(), viewer, new_run_id(), read=body.read)
        return StreamingResponse(_stream(planning, trace_ids()), media_type="text/event-stream", headers=STREAM_HEADERS)

    async def _stream(planning: workflow.Planning, trace: TraceIds) -> AsyncIterator[str]:
        started, outcome = dt.datetime.now(dt.UTC), {"error_code": "stopped"}
        try:
            async for chunk in _events(planning, trace, outcome):
                yield chunk
        finally:
            if runs is not None and planning.read:  # its own thread, so a dropped connection cannot stop the write
                row = _run_row(planning, trace, outcome["error_code"], started)
                writer = threading.Thread(target=runs.record, args=(row,), name=f"strata-run-{planning.run_id}")
                writer.start()
                await asyncio.to_thread(writer.join, 60)

    async def _events(planning: workflow.Planning, trace: TraceIds, outcome: dict) -> AsyncIterator[str]:
        error_code = None
        try:
            # The schema first, so the reading page can draw the card's groups while the reader reads.
            shown = await asyncio.to_thread(countries, planning.viewer)
            yield frame(Event("form", {"form": payload(form, shown, max_months)}))
            names = {entry["code"]: entry["name"] for entry in shown}
            events = workflow.plan(planning, reader_for, form, thresholds, lambda: names, store,
                                   lambda query: find(planning.viewer, STAFF, None, query), now, new_package_id,
                                   new_save_id, max_months)
            async for item in with_heartbeats(events, heartbeat_seconds):
                yield KEEP_ALIVE if item is HEARTBEAT else frame(item)
        except workflow.PlanError as error:
            error_code = error.code if error.code in workflow.PLAN_ERRORS else "internal"
            log.warning("Run %s could not plan a package (%s).", planning.run_id, error.code)
            yield frame(Event("error", {"code": error_code}))
        except Exception:
            error_code = "internal"
            log.exception("Run %s failed while planning a package.", planning.run_id)
            yield frame(Event("error", {"code": "internal"}))
        outcome["error_code"] = error_code or (None if planning.package_id else "no_answer")
        done = {"run_id": planning.run_id}
        if trace.application_insights or trace.mlflow:
            done["trace_ids"] = {"application_insights": trace.application_insights, "mlflow": trace.mlflow}
        yield frame(Event("done", done))

    def _run_row(planning: workflow.Planning, trace: TraceIds, error_code: str | None, started: dt.datetime) -> dict:
        turn = Turn(question=planning.sentence, viewer=planning.viewer, run_id=planning.run_id,
                    scope=Scope(chip=None, as_of=today()), trace=trace)
        turn.notes.agent, turn.notes.agent_version, turn.notes.as_of = planning.agent, planning.agent_version, today()
        return run_row(turn, None, error_code, started, dt.datetime.now(dt.UTC))

    # ── The Packages tab ─────────────────────────────────────────────────

    @app.get("/api/planned-packages")
    def list_packages(view: VIEWS = "staff", viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")

        def read():
            checks = store.plan_checks(viewer.user_id)
            # Country names come from the warehouse, as the viewer; a person's own packages and plan checks
            # come from the app state store and are listed without the names if the warehouse refuses.
            try:
                names = codes(viewer)
                projects = project_countries(viewer, {check.project_id for check in checks})
            except (PermissionDenied, EngineError):
                log.warning("I listed %s's packages without country names: the warehouse did not answer.", viewer.user_id)
                names, projects = {}, {}
            return workflow.list_rows(store.mine(viewer.user_id), checks, form, thresholds, names, projects)
        return guarded("the viewer's packages", read)

    # ── One package ──────────────────────────────────────────────────────

    @app.get("/api/planned-packages/{package_id}")
    def open_package(package_id: str, viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")

        def read():
            saved = mine(viewer, package_id)
            if saved is None:
                return refused(404, "unknown_package")
            return {"package": workflow.package_view(saved, form, thresholds),
                    "form": payload(form, countries(viewer), max_months)}
        return guarded(f"package {package_id}", read)

    @app.post("/api/planned-packages/{package_id}")
    def change_package(package_id: str, body: ChangeRequest, viewer: Viewer = Depends(current_viewer)):
        if (refusal := allowed(viewer)) is not None:
            return refusal

        def act():
            with lock_for(package_id):
                return change(viewer, package_id, body)
        return guarded(f"a change to package {package_id}", act)

    def change(viewer: Viewer, package_id: str, body: ChangeRequest):
        """One change, from the latest save to a new one. Only a change to a country reads the World Bank's
        country list, so the other changes need no warehouse."""
        saved = mine(viewer, package_id)
        if saved is None:
            return refused(404, "unknown_package")
        before = criteria_of.Criteria.from_json(saved.criteria)
        country = body.action == "set" and form.has(body.field) and form.field(body.field).kind == "country"
        try:
            after = criteria_of.change(form, before, body.field, body.action, body.value, thresholds,
                                       codes(viewer) if country else {}, max_months)
        except Invalid:
            return refused(422, "invalid_value", field=body.field)
        plan_months = after.get("plan_months") if form.has("plan_months") else saved.plan_months
        before_range = saved.plan_before_range
        if before_range is None and plan_months is not None and body.plan_before_range is not None:
            before_range = body.plan_before_range
        store.save(package_id, new_save_id(), after.as_json(), plan_months, before_range, now())
        return {"package": workflow.package_view(store.get(package_id), form, thresholds)}

    # ── Comparables for a package with no STEP row ───────────────────────

    @app.get("/api/comparables")
    def comparables(request: Request, asof: dt.date | None = None, view: str = "staff",
                    viewer: Viewer = Depends(current_viewer)):
        criteria = comparables_criteria(request)
        if isinstance(criteria, JSONResponse):
            return criteria
        if "step_reference" in criteria:
            return refused(422, "bad_request", detail="This route is for a package with no STEP reference.")
        if engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        as_of = min(asof, today()) if asof else today()
        try:
            return find(viewer, view, as_of, criteria)
        except registry.ToolError as error:
            return refused(422, "bad_request", detail=str(error))
        except PermissionDenied:
            return JSONResponse({"code": "permission"}, status_code=403)
        except EngineError:
            ref = reference()
            log.exception("The data service failed on find_comparables, reference %s.", ref)
            return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)


def new_save_id() -> str:
    """A save's id, in the order saves are made, so of two saves at the same moment the later sorts last."""
    return f"{time.time_ns():020d}-{uuid.uuid4().hex[:8]}"


def new_package_id() -> str:
    return f"pkg-{uuid.uuid4().hex[:12]}"
