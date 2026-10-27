"""The routes of the package workspace's section 3, procurement risks and what helped (ticket 30).

- GET /api/packages/{step_reference}/risks and GET /api/planned-packages/{package_id}/risks run the risk-table
  builder (src/strata/packages/risks.py) as the viewer, as of ?asof= (never later than today) and in ?view=,
  and answer with the section's payload: its rows, counts, checks and empty reason, and the viewer's selection.
  A package from a STEP row takes section 1's criteria as find_comparables' own parameter names
  (?review_type=Prior, ?country=any), as GET /api/packages/{step_reference}/comparables does; a package from a
  sentence uses the criteria its author saved, and only its author may open it (404 unknown_package for anyone
  else, as for a package that does not exist).
- PUT /api/packages/{step_reference}/risk-selection and PUT /api/planned-packages/{package_id}/risk-selection
  take {"changes": {"cost_estimates": true}}, risk keys from the closed list (config/lessons.toml) with whether
  each is selected now, and keep them for the viewer in the app state store (strata.app.risk_selections), written
  as the app's own service principal. Unselecting sets a value and deletes nothing. A preview changes nothing
  (403 preview), and an unknown risk key gets 422 unknown_risk. The answer lists every risk the viewer has
  selected for the package now.

A read the store cannot answer still draws the table, with no selection, and the failure goes to the log, so
Lakebase being down never hides the risks.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from strata.agent.answer_check import SixChecks
from strata.config import PackageForm, Thresholds, load_lesson_lists
from strata.dbx import Viewer, viewer_from_headers
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.packages import risks, workflow
from strata.packages.store import PackageStore
from strata.server.engines import EngineFor
from strata.server.packages import comparables_criteria
from strata.tools import registry

log = logging.getLogger("strata.server.risks")
STAFF = "staff"
STEP_ROW, PLANNED = "step_reference", "planned"


class SelectionRequest(BaseModel):
    changes: dict[str, bool] = Field(min_length=1, max_length=64)
    view: Literal["staff", "piu", "public"] = "staff"


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, **details}, status_code=status, headers={"Cache-Control": "no-store"})


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: PackageStore | None, form: PackageForm,
               thresholds: Thresholds, today: Callable[[], dt.date], now: Callable[[], dt.datetime],
               reference: Callable[[], str], six_checks: SixChecks | None = None) -> None:
    """six_checks are the app's six checks, with its judge, which every risk table runs (ticket 61)."""
    lists = load_lesson_lists()

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def selection(viewer: Viewer, kind: str, key: str) -> list[str]:
        if store is None or not viewer.user_id:
            return []
        try:
            return store.selected_risks(viewer.user_id, kind, key)
        except Exception:  # Lakebase or the network: the risks still show, with no selection
            log.exception("I could not read %s's risk selection for %s %s.", viewer.user_id, kind, key)
            return []

    def table(viewer: Viewer, view: str, asof: dt.date | None, criteria: dict | None, words: str | None,
              missing: list[str], kind: str, key: str):
        if engine_for is None:
            return refused(503, "no_data_service")
        as_of = min(asof, today()) if asof else today()
        chosen = selection(viewer, kind, key)
        try:
            with engine_for(viewer) as engine:
                built = risks.build(engine, viewer, as_of=as_of, criteria=criteria, words=words, view=view,
                                    selected=chosen, missing=missing, thresholds=thresholds, six_checks=six_checks)
        except registry.ToolError as error:
            return refused(422, "bad_request", detail=str(error))
        except PermissionDenied:
            return refused(403, "permission")
        except EngineError:
            ref = reference()
            log.exception("The data service failed on the risks for %s %s, reference %s.", kind, key, ref)
            return refused(503, "data_service", trace_id=ref)
        return built.payload

    def mine(viewer: Viewer, package_id: str):
        saved = store.get(package_id) if store is not None else None
        return saved if saved is not None and saved.author_id == viewer.user_id else None

    def save(viewer: Viewer, body: SelectionRequest, kind: str, key: str):
        if not viewer.user_id:
            return refused(401, "no_identity")
        unknown = sorted(risk for risk in body.changes if lists.risk_factor(risk) is None)
        if unknown:
            return refused(422, "unknown_risk", risk_keys=unknown)
        if store is None:
            return refused(503, "no_data_service")
        try:
            store.select_risks(viewer.user_id, kind, key, body.changes, now())
            return {"selected": store.selected_risks(viewer.user_id, kind, key)}
        except Exception:  # Lakebase or the network: the page keeps the change and offers Try again
            ref = reference()
            log.exception("I could not save %s's risk selection for %s %s, reference %s.", viewer.user_id, kind,
                          key, ref)
            return refused(503, "not_saved", trace_id=ref)

    @app.get("/api/packages/{step_reference}/risks")
    def step_row_risks(step_reference: str, request: Request, asof: dt.date | None = None, view: str = STAFF,
                       viewer: Viewer = Depends(current_viewer)):
        criteria = comparables_criteria(request)
        if isinstance(criteria, JSONResponse):
            return criteria
        return table(viewer, view, asof, {**criteria, "step_reference": step_reference}, None, [], STEP_ROW,
                     step_reference)

    @app.put("/api/packages/{step_reference}/risk-selection")
    def step_row_selection(step_reference: str, body: SelectionRequest, viewer: Viewer = Depends(current_viewer)):
        return save(viewer, body, STEP_ROW, step_reference)

    @app.get("/api/planned-packages/{package_id}/risks")
    def planned_risks(package_id: str, asof: dt.date | None = None, view: str = STAFF,
                      viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        try:
            saved = mine(viewer, package_id)
        except Exception:
            ref = reference()
            log.exception("I could not read package %s, reference %s.", package_id, ref)
            return refused(503, "data_service", trace_id=ref)
        if saved is None:
            return refused(404, "unknown_package")
        shown = workflow.package_view(saved, form, thresholds)
        values = {field["key"]: field["value"] for field in shown["fields"]}
        return table(viewer, view, asof, shown["comparables_query"], values.get("description") or saved.sentence,
                     shown["missing"], PLANNED, package_id)

    @app.put("/api/planned-packages/{package_id}/risk-selection")
    def planned_selection(package_id: str, body: SelectionRequest, viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        try:
            saved = mine(viewer, package_id)
        except Exception:
            ref = reference()
            log.exception("I could not read package %s, reference %s.", package_id, ref)
            return refused(503, "data_service", trace_id=ref)
        if saved is None:
            return refused(404, "unknown_package")
        return save(viewer, body, PLANNED, package_id)
