"""The upload routes (ticket 38): an implementing agency officer's private upload of their Procurement Plan.

- GET /api/uploads/form gives what Check my plan shows before a file is chosen: whether the viewer is an implementing
  agency officer, their agency, the projects whose records name it, its latest published plans, how many earlier
  uploads the team kept, the columns the reader needs and also reads (the STEP column registry), and the file
  limits. A viewer on no implementing agency's team gets officer false and no agency.
- POST /api/uploads?project_id=&idempotency_key= takes the file itself as the request's body and its name,
  percent-encoded, in the X-Strata-File-Name header, so the name never sits in an address a proxy's log may keep.
  It reads the file, checks it with check_plan, and only then keeps its activities in strata.ops with the
  uploader's team. It answers with the upload's id and its check, or 422 with the reading's error code and kept
  false, when nothing was kept. The file is held in memory for the request and never written anywhere, and the
  server stops reading a body that passes uploads.max_size_bytes. A second request with the same idempotency key
  answers with the upload it kept and keeps nothing new.
- GET /api/uploads lists the uploads the viewer's team kept, newest first, for the Packages tab.
- GET /api/uploads/{upload_id} gives the upload's check, run again on today's records, with how the file was read.
  An upload of another team, or one that does not exist, gets the same 404, so a link reveals nothing.
- GET /api/uploads/{upload_id}/rows/{position} gives one activity as the evidence drawer's record view shows it.

Every route goes through the one access rule (src/strata/server/access.py): only the uploader and their team read an
upload. Only an officer of an implementing agency's team (config/roles.toml) uploads, and only for a project whose
record names their agency; a preview of another view uploads nothing (the view switch's guard answers 403 preview, upload.holdPreview). The tools
read an upload only through reader(), which asks the same rule, so no answer, search or other team ever reaches
one. Uploads are written as the app's own service principal, like the drafts.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse

from strata.dbx import Viewer, viewer_from_headers
from strata.drafts.store import iso
from strata.lakehouse.engine import Engine, EngineError, PermissionDenied
from strata.reader.step_columns import registry as step_columns
from strata.reader.upload import UploadError, read_upload
from strata.server import projects
from strata.server.access import Access, is_author
from strata.server.engines import EngineFor
from strata.tools import registry
from strata.tools.check_plan import agency_id, implementing_agencies
from strata.uploads.store import NewUpload, Saved, UploadStore
from strata.uploads.store import _sql as upload_sql

log = logging.getLogger("strata.server.uploads")
STAFF = "staff"
PREFIX = "upl-"  # an upload's id: upl- and twelve hex digits
ROW_ID = "upload-row:"  # an upload row's evidence id: upload-row:{upload_id}:{position}


def new_upload_id() -> str:
    return f"{PREFIX}{uuid.uuid4().hex[:12]}"


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, "error": code, **details}, status_code=status,
                        headers={"Cache-Control": "no-store"})


def as_mapping(saved: Saved) -> dict:
    """An upload as check_plan and estimate_time read it."""
    return {"upload_id": saved.upload_id, "project_id": saved.project_id,
            "implementing_agency": saved.implementing_agency, "file_name": saved.file_name,
            "uploaded_on": saved.uploaded_on.isoformat(), "rows": list(saved.rows)}


def reader(store: UploadStore | None, access: Access, viewer: Viewer) -> Callable[[str], Mapping[str, Any] | None]:
    """The tools' way to an upload for this viewer: the upload, if they may read it by the one access rule, else
    None, the same for one that does not exist."""
    def read(upload_id: str) -> Mapping[str, Any] | None:
        if store is None or not viewer.user_id or not upload_id.startswith(PREFIX) or "," in upload_id:
            return None
        saved = store.get(upload_id)
        if saved is None or not access.may_read(viewer, saved.team_key, saved.uploader_id):
            return None
        return as_mapping(saved)
    return read


def readable(store: UploadStore, access: Access, viewer: Viewer, upload_id: str) -> Saved | None:
    if not upload_id.startswith(PREFIX) or "," in upload_id:
        return None
    saved = store.get(upload_id)
    return saved if saved is not None and access.may_read(viewer, saved.team_key, saved.uploader_id) else None


def agency_projects(engine: Engine, agency: str, as_of: dt.date) -> list[dict]:
    """The projects whose records name this implementing agency, newest first, each with the agency's latest
    published Procurement Plan for it."""
    found = engine.run(upload_sql("agency_projects"), {"agency": agency, "as_of": as_of})
    rows = [dict(zip(found.columns, row)) for row in found.rows]
    wanted = agency.strip().lower()
    listed = []
    for row in rows:
        if wanted not in [name.lower() for name in implementing_agencies(row["implementing_agency"])]:
            continue
        plans = engine.run(upload_sql("agency_latest_plan"),
                           {"project_id": row["project_id"], "agency": agency, "as_of": as_of})
        latest = [dict(zip(plans.columns, plan)) for plan in plans.rows]
        listed.append({"project_id": row["project_id"], "project_name": row["project_name"],
                       "display_name": projects.display_name(row["project_name"]),
                       "latest_plan": ({"plan_date": _day(latest[0]["plan_date"]),
                                        "disclosed_on": _day(latest[0]["disclosed_on"]),
                                        "agency_id": agency_id(latest[0]["implementing_agency"])}
                                       if latest else None)})
    return listed


def _day(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, dt.date) else str(value)[:10]


def listing(saved: Saved, viewer: Viewer) -> dict:
    return {"upload_id": saved.upload_id, "uploaded_at": iso(saved.uploaded_at), "uploaded_on": saved.uploaded_on.isoformat(),
            "uploader": {"name": saved.uploader_name, "you": is_author(viewer, saved.uploader_id)},
            "project_id": saved.project_id, "implementing_agency": saved.implementing_agency,
            "agency_id": agency_id(saved.implementing_agency), "file_name": saved.file_name,
            "activities": saved.reading.get("activities")}


def reading_of(reading, file_name: str) -> dict:
    """How the file was read, as the upload keeps it and "Show how I read your file" lists it."""
    return {"sheets": reading.sheets, "used": reading.used, "unused": reading.unused,
            "activities": len(reading.rows),
            "unread_values": sum(1 for row in reading.rows for note in row.notes
                                 if note["code"] in ("unread_date", "unread_amount")),
            "file_name": file_name}


def row_dict(row) -> dict:
    return {"position": row.position, "reference": row.reference, "description": row.description,
            "sheet": row.sheet, "section": row.section, "fields": row.fields, "steps": row.steps, "notes": row.notes,
            "raw": row.raw}


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: UploadStore | None, access: Access,
               today: Callable[[], dt.date], now: Callable[[], dt.datetime],
               new_upload_id: Callable[[], str], reference: Callable[[], str]) -> None:
    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def failed(what: str, error: Exception) -> JSONResponse:
        if isinstance(error, PermissionDenied):
            return refused(403, "permission")
        ref = reference()
        log.exception("The data service failed on %s, reference %s.", what, ref)
        return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)

    def check(viewer: Viewer, upload: Mapping[str, Any], read: Callable[[str], Mapping[str, Any] | None]) -> dict:
        """check_plan on an upload as the viewer, through the registry, on today's records: an upload is checked
        against the records as they are now, whatever the page's as-of date."""
        with engine_for(viewer) as engine:
            return registry.call("check_plan", {"project_id": upload["project_id"],
                                                "implementing_agency": upload["implementing_agency"],
                                                "upload_id": upload["upload_id"]},
                                 registry.Context(engine, viewer, STAFF, today(), uploads=read))

    def shown(saved: Saved, viewer: Viewer, result: dict) -> dict:
        if isinstance(result.get("project"), dict):
            result["project"]["display_name"] = projects.display_name(result["project"]["project_name"])
        return {**result, "upload": {**listing(saved, viewer), "reading": saved.reading}}

    @app.get("/api/uploads/form")
    def upload_form(view: str = "staff", viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        columns = step_columns()
        limits = columns.uploads
        answer = {"officer": False, "agency": None, "projects": [], "earlier": 0, "preview": view != STAFF,
                  "columns": {"needed": columns.needed(), "optional": columns.optional()},
                  "limits": {"accept": list(limits.accept), "max_size_bytes": limits.max_size_bytes,
                             "max_rows": limits.max_rows},
                  "format": limits.format}
        agency = access.agency(viewer)
        if agency is None or view != STAFF:
            return answer
        if engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            with engine_for(viewer) as engine:
                found = agency_projects(engine, agency, today())
            earlier = len(store.for_team(access.team(viewer).key, viewer.user_id)) if store else 0
        except EngineError as error:
            return failed(f"the projects of {agency}", error)
        return {**answer, "officer": True, "agency": {"name": agency, "agency_id": agency_id(agency)},
                "projects": found, "earlier": earlier}

    @app.post("/api/uploads")
    async def upload(request: Request, project_id: str = Query(pattern=r"^P\d{6}$"),
                     sent_name: str = Header(alias="X-Strata-File-Name", min_length=1, max_length=2048),
                     idempotency_key: str | None = Query(None, max_length=128), view: str = "staff",
                     viewer: Viewer = Depends(current_viewer)):
        # The file's name comes percent-encoded in a header, never in the address, where a proxy's log may keep it.
        file_name = unquote(sent_name).strip()
        if not file_name or len(file_name) > 255:
            return refused(422, "bad_request", kept=False)
        if not viewer.user_id:
            return refused(401, "no_identity")
        agency = access.agency(viewer)
        if agency is None:
            return refused(403, "not_agency_team")
        if store is None or engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        if idempotency_key:
            try:
                made = store.by_key(viewer.user_id, idempotency_key)
            except EngineError as error:
                return failed("an earlier upload", error)
            if made is not None:
                return {"upload_id": made, "kept": True}
        columns = step_columns()
        data = await _body(request, columns.uploads.max_size_bytes)
        if data is None:
            return refused(422, "size", kept=False, file_name=file_name, max_size=columns.uploads.max_size_bytes)
        try:
            with engine_for(viewer) as engine:
                named = [entry["project_id"] for entry in agency_projects(engine, agency, today())]
        except EngineError as error:
            return failed(f"the projects of {agency}", error)
        if project_id not in named:
            return refused(422, "unknown_project", kept=False)
        try:
            reading = read_upload(file_name, data, columns)
        except UploadError as error:
            return refused(422, error.code, kept=False, file_name=file_name, **error.details)
        upload_id, at = new_upload_id(), now()
        rows = [row_dict(row) for row in reading.rows]
        pending = {"upload_id": upload_id, "project_id": project_id, "implementing_agency": agency,
                   "file_name": file_name, "uploaded_on": at.astimezone(dt.UTC).date().isoformat(),
                   "rows": [_stored(row) for row in rows]}
        try:
            result = check(viewer, pending, lambda asked: pending if asked == upload_id else None)
        except EngineError as error:
            response = failed(f"checking {file_name}", error)
            return refused(response.status_code, "permission" if response.status_code == 403 else "service",
                           kept=False, file_name=file_name)
        kept = NewUpload(upload_id, access.team(viewer).key, viewer.user_id, viewer.name, idempotency_key, project_id,
                         agency, file_name, reading_of(reading, file_name), at, rows)
        try:
            # A second request with the same key may have kept its upload while this one was read and checked.
            made = store.by_key(viewer.user_id, idempotency_key) if idempotency_key else None
            if made is not None:
                return {"upload_id": made, "kept": True}
            store.create(kept)
        except PermissionDenied:
            return refused(503, "upload_store", kept=False, file_name=file_name, trace_id=reference())
        except EngineError as error:
            failed(f"keeping {file_name}", error)
            return refused(503, "service", kept=False, file_name=file_name)
        try:
            saved = store.get(upload_id)
        except EngineError as error:
            # The upload is kept, so the answer names it, as a repeated request with the same key does; its page
            # reads it again.
            log.warning("Reading back upload %s failed after it was kept: %s", upload_id, error)
            return {"upload_id": upload_id, "kept": True}
        return {**shown(saved, viewer, result), "upload_id": upload_id, "kept": True}

    @app.get("/api/uploads")
    def list_uploads(view: str = "staff", viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        # A preview never shows any team's upload, the previewing person's own included (the 38 brief, 6.9).
        if view != STAFF or store is None:
            return {"uploads": [], "preview": view != STAFF}
        try:
            found = store.for_team(access.team(viewer).key, viewer.user_id)
        except EngineError as error:
            return failed("the team's uploads", error)
        return {"uploads": [listing(saved, viewer) for saved in found], "preview": False}

    @app.get("/api/uploads/{upload_id}")
    def open_upload(upload_id: str, view: str = "staff", viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        if view != STAFF or store is None or engine_for is None:
            return refused(404, "unknown_upload")
        try:
            saved = readable(store, access, viewer, upload_id)
            if saved is None:
                return refused(404, "unknown_upload")
            result = check(viewer, as_mapping(saved), reader(store, access, viewer))
        except EngineError as error:
            return failed(f"upload {upload_id}", error)
        return shown(saved, viewer, result)

    @app.get("/api/uploads/{upload_id}/rows/{position}")
    def upload_row(upload_id: str, position: int, view: str = "staff", viewer: Viewer = Depends(current_viewer)):
        """One activity of an upload, as the evidence drawer's record view shows it, for the uploader's team only."""
        if not viewer.user_id:
            return refused(401, "no_identity")
        if view != STAFF or store is None:
            return refused(404, "unknown_evidence")
        try:
            saved = readable(store, access, viewer, upload_id)
        except EngineError as error:
            return failed(f"upload {upload_id}", error)
        row = next((row for row in saved.rows if row["position"] == position), None) if saved else None
        if row is None:
            return refused(404, "unknown_evidence")
        return {"id": f"{ROW_ID}{upload_id}:{position}", "kind": "upload_row",
                "upload": listing(saved, viewer), "row": row}


async def _body(request: Request, limit: int) -> bytes | None:
    """The request's body, or None as soon as it passes the limit: a length the request states over the limit is
    refused unread, and a body with no stated length is read only until it passes the limit."""
    stated = request.headers.get("content-length", "")
    if stated.isdigit() and int(stated) > limit:
        return None
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > limit:
            return None
    return bytes(data)


def _stored(row: dict) -> dict:
    """An activity as the store gives it back: its dates as ISO dates, its amounts as text."""
    steps = {name: {head: (day.isoformat() if isinstance(day, dt.date) else day) for head, day in dates.items()}
             for name, dates in row["steps"].items()}
    fields = {key: (str(value) if value is not None and not isinstance(value, str) else value)
              for key, value in row["fields"].items()}
    return {**row, "steps": steps, "fields": fields}
