"""The routes of the package workspace's time estimate (ticket 26): lane 2 of section 1, "Compare with", the track
record, the plan-date choice and section 4's procurement approach options, all from one estimate_time call.

- GET /api/packages/{step_reference}/estimate and GET /api/planned-packages/{package_id}/estimate run estimate_time
  through the tool registry as the viewer, as of ?asof= (never later than today) and in ?view=, and answer with its
  result and the viewer's saved plan-date choice, plan_date_choice (middle, eight_in_ten, or null for the cautious
  default). A package from a STEP row takes section 1's criteria as find_comparables' own parameter names, as GET
  /api/packages/{step_reference}/comparables does; a package from a sentence uses the criteria its author saved,
  and describes itself with its saved fields, and only its author may open it (404 unknown_package for anyone else).
- PUT /api/packages/{step_reference}/plan-dates and PUT /api/planned-packages/{package_id}/plan-dates take
  {"choice": "middle"} or {"choice": "eight_in_ten"} and keep it for the viewer in the app state store
  (strata.app.plan_date_choices), written as the app's own service principal. The same choice sets the dates
  section 2 drafts (ticket 27). A preview changes nothing (403 preview).

A read the store cannot answer still answers the estimate, with no saved choice, and the failure goes to the log, so
Lakebase being down never hides the time estimate.
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

log = logging.getLogger("strata.server.estimates")
STAFF = "staff"
STEP_ROW, PLANNED = "step_reference", "planned"
CHOICES = ("middle", "eight_in_ten")
# A saved package's fields that describe it to estimate_time, by the tool's parameter names.
DESCRIBED = {"estimated_amount_usd": "described_amount_usd", "market_approach": "described_market_approach",
             "review_type": "described_review_type", "prequalification": "described_prequalification",
             "lots": "described_lots"}


class ChoiceRequest(BaseModel):
    choice: Literal["middle", "eight_in_ten"]
    view: Literal["staff", "piu", "public"] = "staff"


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, **details}, status_code=status, headers={"Cache-Control": "no-store"})


def described(values: dict) -> dict:
    """A saved package's fields as estimate_time's described_ parameters: a count as a whole number, an amount
    as a number, and the rest as text; a field with no value is left out."""
    found = {}
    for field, parameter in DESCRIBED.items():
        value = values.get(field)
        if value is None or value == "":
            continue
        found[parameter] = int(value) if field == "lots" else float(value) if field == "estimated_amount_usd" else str(value)
    return found


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: PackageStore | None, form: PackageForm,
               thresholds: Thresholds, today: Callable[[], dt.date], now: Callable[[], dt.datetime],
               reference: Callable[[], str]) -> None:

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def chosen(viewer: Viewer, kind: str, key: str) -> str | None:
        if store is None or not viewer.user_id:
            return None
        try:
            return store.plan_date_choice(viewer.user_id, kind, key)
        except Exception:  # Lakebase or the network: the estimate still shows, with the default choice
            log.exception("I could not read %s's plan-date choice for %s %s.", viewer.user_id, kind, key)
            return None

    def answer(viewer: Viewer, view: str, asof: dt.date | None, arguments: dict, kind: str, key: str):
        if engine_for is None:
            return refused(503, "no_data_service")
        as_of = min(asof, today()) if asof else today()
        try:
            with engine_for(viewer) as engine:
                result = registry.call("estimate_time", arguments, registry.Context(engine, viewer, view, as_of, thresholds))
        except registry.ToolError as error:
            return refused(422, "bad_request", detail=str(error))
        except registry.ToolContractError:
            ref = reference()
            log.exception("estimate_time broke its contract for %s %s, reference %s.", kind, key, ref)
            return refused(500, "tool_contract", trace_id=ref)
        except PermissionDenied:
            return refused(403, "permission")
        except EngineError:
            ref = reference()
            log.exception("The data service failed on the time estimate for %s %s, reference %s.", kind, key, ref)
            return refused(503, "data_service", trace_id=ref)
        return {**result, "plan_date_choice": chosen(viewer, kind, key)}

    def mine(viewer: Viewer, package_id: str):
        saved = store.get(package_id) if store is not None else None
        return saved if saved is not None and saved.author_id == viewer.user_id else None

    def save(viewer: Viewer, body: ChoiceRequest, kind: str, key: str):
        if not viewer.user_id:
            return refused(401, "no_identity")
        if body.view != STAFF:
            return refused(403, "preview", capability="choose", copy="preview")
        if store is None:
            return refused(503, "no_data_service")
        try:
            store.choose_plan_date(viewer.user_id, kind, key, body.choice, now())
            return {"plan_date_choice": store.plan_date_choice(viewer.user_id, kind, key)}
        except Exception:  # Lakebase or the network: the page keeps the choice on screen and offers Try again
            ref = reference()
            log.exception("I could not save %s's plan-date choice for %s %s, reference %s.", viewer.user_id, kind,
                          key, ref)
            return refused(503, "not_saved", trace_id=ref)

    def planned(viewer: Viewer, package_id: str):
        """The viewer's own saved package, or the answer that says why there is none."""
        if not viewer.user_id:
            return None, refused(401, "no_identity")
        try:
            saved = mine(viewer, package_id)
        except Exception:
            ref = reference()
            log.exception("I could not read package %s, reference %s.", package_id, ref)
            return None, refused(503, "data_service", trace_id=ref)
        if saved is None:
            return None, refused(404, "unknown_package")
        return saved, None

    @app.get("/api/packages/{step_reference}/estimate")
    def step_row_estimate(step_reference: str, request: Request, asof: dt.date | None = None, view: str = STAFF,
                          viewer: Viewer = Depends(current_viewer)):
        criteria = comparables_criteria(request)
        if isinstance(criteria, JSONResponse):
            return criteria
        return answer(viewer, view, asof, {**criteria, "step_reference": step_reference}, STEP_ROW, step_reference)

    @app.put("/api/packages/{step_reference}/plan-dates")
    def step_row_choice(step_reference: str, body: ChoiceRequest, viewer: Viewer = Depends(current_viewer)):
        return save(viewer, body, STEP_ROW, step_reference)

    @app.get("/api/planned-packages/{package_id}/estimate")
    def planned_estimate(package_id: str, asof: dt.date | None = None, view: str = STAFF,
                         viewer: Viewer = Depends(current_viewer)):
        saved, refusal = planned(viewer, package_id)
        if refusal is not None:
            return refusal
        shown = workflow.package_view(saved, form, thresholds)
        if not shown["comparables_query"]:
            return refused(422, "missing_criteria", missing=shown["missing"])
        values = {field["key"]: field["value"] for field in shown["fields"]}
        return answer(viewer, view, asof, {**shown["comparables_query"], **described(values)}, PLANNED, package_id)

    @app.put("/api/planned-packages/{package_id}/plan-dates")
    def planned_choice(package_id: str, body: ChoiceRequest, viewer: Viewer = Depends(current_viewer)):
        saved, refusal = planned(viewer, package_id)
        if refusal is not None:
            return refusal
        return save(viewer, body, PLANNED, package_id)
