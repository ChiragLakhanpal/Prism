"""The routes of the package workspace's section 2, "Planned date for each step" (ticket 27; the 27 brief).

- GET /api/packages/{step_reference}/steps and GET /api/planned-packages/{package_id}/steps run estimate_time
  through the tool registry as the viewer, as of ?asof= (never later than today) and in ?view=, with the date the
  viewer gave the package's first step, and answer with its result, both choices of dates in one response, and
  the viewer's saved choice, plan_date_choice (middle, eight_in_ten, or null for the cautious default). A package
  from a STEP row takes section 1's criteria as find_comparables' own parameter names, as GET
  /api/packages/{step_reference}/comparables does; a package from a sentence uses the criteria its author saved,
  and only its author may open it (404 unknown_package for anyone else).
- PUT /api/packages/{step_reference}/plan-dates and PUT /api/planned-packages/{package_id}/plan-dates take
  {"choice": "middle"} or {"choice": "eight_in_ten"}: the one stored choice ticket 26's plan-date choice shares
  (strata.app.plan_date_choices). Section 2 calls eight_in_ten its cautious dates.
- PUT /api/packages/{step_reference}/step-start and PUT /api/planned-packages/{package_id}/step-start take
  {"start_date": "2026-11-02"}, keep it for the viewer (strata.app.step_start_dates) and answer with the steps
  dated from it. A date outside the thresholds file's range gets 422 bad_request.

Both are written as the app's own service principal; a preview changes nothing (403 preview). A read the store
cannot answer still answers the dates, with no saved choice or start date, and the failure goes to the log, so
Lakebase being down never hides the section.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from strata.config import PackageForm, Thresholds
from strata.dbx import Viewer, viewer_from_headers
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.packages import workflow
from strata.packages.store import PackageStore
from strata.server.engines import EngineFor
from strata.server.packages import comparables_criteria
from strata.tools import registry

log = logging.getLogger("strata.server.steps")
STAFF = "staff"
STEP_ROW, PLANNED = "step_reference", "planned"


class ChoiceRequest(BaseModel):
    choice: Literal["middle", "eight_in_ten"]
    view: Literal["staff", "piu", "public"] = "staff"


class StartRequest(BaseModel):
    start_date: dt.date
    view: Literal["staff", "piu", "public"] = "staff"


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, **details}, status_code=status, headers={"Cache-Control": "no-store"})

def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: PackageStore | None, form: PackageForm,
               thresholds: Thresholds, today: Callable[[], dt.date], now: Callable[[], dt.datetime],
               reference: Callable[[], str]) -> None:

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def saved(viewer: Viewer, kind: str, key: str) -> tuple[str | None, dt.date | None]:
        """The viewer's choice of dates and the date they gave the first step, or None for each the store lacks."""
        if store is None or not viewer.user_id:
            return None, None
        try:
            return store.plan_date_choice(viewer.user_id, kind, key), store.step_start(viewer.user_id, kind, key)
        except Exception:  # Lakebase or the network: the dates still show, with the defaults
            log.exception("I could not read %s's saved step dates for %s %s.", viewer.user_id, kind, key)
            return None, None

    def dates(viewer: Viewer, view: str, asof: dt.date | None, criteria: dict, kind: str, key: str,
              start: dt.date | None = None):
        if engine_for is None:
            return refused(503, "no_data_service")
        choice, stored_start = saved(viewer, kind, key)
        start = start or stored_start
        as_of = min(asof, today()) if asof else today()
        try:
            with engine_for(viewer) as engine:
                context = registry.Context(engine=engine, viewer=viewer, view=view, as_of=as_of, thresholds=thresholds)
                arguments = {**criteria, **({"start_date": start} if start else {})}
                result = registry.call("estimate_time", arguments, context)
        except registry.ToolError as error:
            return refused(422, "bad_request", detail=str(error))
        except PermissionDenied:
            return refused(403, "permission")
        except EngineError:
            ref = reference()
            log.exception("The data service failed on the step dates for %s %s, reference %s.", kind, key, ref)
            return refused(503, "data_service", trace_id=ref)
        if result["abstention"] and result["abstention"]["reason"] == "unknown_package":
            return refused(404, "unknown_package")
        return {**result, "plan_date_choice": choice}

    def mine(viewer: Viewer, package_id: str):
        found = store.get(package_id) if store is not None else None
        return found if found is not None and found.author_id == viewer.user_id else None

    def planned_criteria(viewer: Viewer, package_id: str) -> dict | JSONResponse:
        if not viewer.user_id:
            return refused(401, "no_identity")
        try:
            package = mine(viewer, package_id)
        except Exception:
            ref = reference()
            log.exception("I could not read package %s, reference %s.", package_id, ref)
            return refused(503, "data_service", trace_id=ref)
        if package is None:
            return refused(404, "unknown_package")
        return workflow.package_view(package, form, thresholds)["comparables_query"] or {}

    def keep(viewer: Viewer, body_view: str, kind: str, key: str, write: Callable[[], None]):
        if not viewer.user_id:
            return refused(401, "no_identity")
        if body_view != STAFF:
            return refused(403, "preview", capability="save", copy="preview")
        if store is None:
            return refused(503, "no_data_service")
        try:
            write()
        except Exception:  # Lakebase or the network: the page keeps the change and offers Try again
            ref = reference()
            log.exception("I could not save %s's step dates for %s %s, reference %s.", viewer.user_id, kind, key, ref)
            return refused(503, "not_saved", trace_id=ref)
        return None

    def choose(viewer: Viewer, body: ChoiceRequest, kind: str, key: str):
        failed = keep(viewer, body.view, kind, key,
                      lambda: store.choose_plan_date(viewer.user_id, kind, key, body.choice, now()))
        return failed or {"plan_date_choice": body.choice}

    def start_from(viewer: Viewer, body: StartRequest, criteria: dict, kind: str, key: str):
        """Date the steps from the viewer's date, which estimate_time checks against the thresholds file's range,
        and keep the date only when it was in range."""
        if body.view != STAFF:
            return refused(403, "preview", capability="save", copy="preview")
        checked = dates(viewer, STAFF, None, criteria, kind, key, start=body.start_date)
        if isinstance(checked, JSONResponse):
            return checked
        failed = keep(viewer, body.view, kind, key,
                      lambda: store.choose_step_start(viewer.user_id, kind, key, body.start_date, now()))
        return failed or checked

    @app.get("/api/packages/{step_reference}/steps")
    def step_row_steps(step_reference: str, request: Request, asof: dt.date | None = None, view: str = STAFF,
                       viewer: Viewer = Depends(current_viewer)):
        criteria = comparables_criteria(request)
        if isinstance(criteria, JSONResponse):
            return criteria
        return dates(viewer, view, asof, {**criteria, "step_reference": step_reference}, STEP_ROW, step_reference)

    @app.put("/api/packages/{step_reference}/plan-dates")
    def step_row_choice(step_reference: str, body: ChoiceRequest, viewer: Viewer = Depends(current_viewer)):
        return choose(viewer, body, STEP_ROW, step_reference)

    @app.put("/api/packages/{step_reference}/step-start")
    def step_row_start(step_reference: str, body: StartRequest, viewer: Viewer = Depends(current_viewer)):
        return start_from(viewer, body, {"step_reference": step_reference}, STEP_ROW, step_reference)

    @app.get("/api/planned-packages/{package_id}/steps")
    def planned_steps(package_id: str, asof: dt.date | None = None, view: str = STAFF,
                      viewer: Viewer = Depends(current_viewer)):
        criteria = planned_criteria(viewer, package_id)
        if isinstance(criteria, JSONResponse):
            return criteria
        return dates(viewer, view, asof, criteria, PLANNED, package_id)

    @app.put("/api/planned-packages/{package_id}/plan-dates")
    def planned_choice(package_id: str, body: ChoiceRequest, viewer: Viewer = Depends(current_viewer)):
        criteria = planned_criteria(viewer, package_id)
        if isinstance(criteria, JSONResponse):
            return criteria
        return choose(viewer, body, PLANNED, package_id)

    @app.put("/api/planned-packages/{package_id}/step-start")
    def planned_start(package_id: str, body: StartRequest, viewer: Viewer = Depends(current_viewer)):
        criteria = planned_criteria(viewer, package_id)
        if isinstance(criteria, JSONResponse):
            return criteria
        return start_from(viewer, body, criteria, PLANNED, package_id)
