"""The field photo routes (ticket 150): a World Bank staff viewer adds a photo from a mission to a project's Deep
research tab, and only their team sees it.

- GET /api/projects/{project_id}/field-photos lists the photos the viewer's team kept for the project, newest first,
  each with its date and place, and says whether the viewer may add one and the limits (config/uploads.toml,
  [field_photos]).
- POST /api/projects/{project_id}/field-photos takes the photo itself as the request's body, its name percent-encoded
  in the X-Strata-File-Name header and its caption in X-Strata-Caption, so neither sits in an address a proxy's log
  may keep. Only a World Bank staff viewer adds one, in the staff view. It reads the photo's EXIF date and GPS
  position, names the project location nearest that position, and keeps the file and its fields through the photo
  store. A file that is too large, a project whose team already keeps the most photos, a file that is not a JPEG or a
  PNG, and a missing caption each get 422 with a code and kept false. Adding a photo submits nothing to anyone.
- GET /api/projects/{project_id}/field-photos/{photo_id} gives the photo itself to the uploader's team, and 403 to
  anyone else.

Every route goes through the one access rule (src/strata/server/access.py). The deep research run reads the photos
only through reader(), which asks the same rule, so a run by a viewer of another team never sees one.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from collections.abc import Callable
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, Path, Request
from fastapi.responses import JSONResponse, Response

from strata.config import FieldPhotos, load_field_photos
from strata.dbx import Viewer, viewer_from_headers
from strata.drafts.store import iso
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.research import photos as field_photos
from strata.research.photos import Photo, PhotoError, PhotoStore
from strata.server.access import Access, is_author
from strata.server.engines import EngineFor
from strata.server.uploads import _body

log = logging.getLogger("strata.server.field_photos")
STAFF = "staff"
PROJECT = r"^P\d{6}$"
PHOTO = r"^fph-[0-9a-f]{12}$"


def new_photo_id() -> str:
    return f"{field_photos.PREFIX}{uuid.uuid4().hex[:12]}"


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, "error": code, **details}, status_code=status,
                        headers={"Cache-Control": "no-store"})


def listing(photo: Photo, viewer: Viewer) -> dict:
    return {"photo_id": photo.photo_id, "project_id": photo.project_id, "file_name": photo.file_name,
            "caption": photo.caption, "taken_on": photo.taken_on.isoformat() if photo.taken_on else None,
            "place": photo.place, "latitude": photo.latitude, "longitude": photo.longitude,
            "uploaded_at": iso(photo.uploaded_at),
            "uploader": {"name": photo.uploader_name, "you": is_author(viewer, photo.uploader_id)},
            "url": field_photos.photo_url(photo.project_id, photo.photo_id)}


def reader(store: PhotoStore | None, access: Access, viewer: Viewer,
           config: FieldPhotos | None = None) -> Callable[[str, dt.date], list[dict]]:
    """The deep research run's way to the viewer's team's photos of a project, as research items, kept by the as-of
    day: through the one access rule, and none for a viewer no one is signed in for."""
    def read(project_id: str, as_of: dt.date) -> list[dict]:
        if store is None or not viewer.user_id:
            return []
        team = access.team(viewer).key
        settings = config or load_field_photos()
        return [field_photos.item_of(photo, settings) for photo in store.for_team(project_id, team, viewer.user_id)
                if access.may_read(viewer, photo.team_key, photo.uploader_id) and photo.uploaded_on <= as_of]
    return read


def is_photo_item(evidence_id: str) -> bool:
    """Whether an evidence id names a field photo: strata.research.item:<project>/field_photos/<photo id>."""
    return evidence_id.startswith(field_photos.ITEM_PREFIX) and f"/{field_photos.SOURCE_KEY}/" in evidence_id


def read_item(store: PhotoStore | None, access: Access, viewer: Viewer, evidence_id: str) -> dict | None:
    """A field photo as the evidence drawer opens it, for the uploader's team only; None for anyone else, as for a
    photo that does not exist."""
    project_id, _, photo_id = evidence_id.removeprefix(field_photos.ITEM_PREFIX).partition(f"/{field_photos.SOURCE_KEY}/")
    if store is None or not viewer.user_id or not photo_id.startswith(field_photos.PREFIX):
        return None
    photo = store.get(photo_id)
    if photo is None or photo.project_id != project_id or not access.may_read(viewer, photo.team_key, photo.uploader_id):
        return None
    return field_photos.item_of(photo, load_field_photos())


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: PhotoStore | None, access: Access,
               now: Callable[[], dt.datetime], new_photo_id: Callable[[], str] = new_photo_id,
               reference: Callable[[], str], places: Callable | None = None) -> None:
    """places(engine, project_id) gives the project's locations, for the place a photo's position is nearest; by
    default, the project's record as the deep research readers read it (src/strata/research/project.py)."""

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def failed(what: str, error: Exception) -> JSONResponse:
        if isinstance(error, PermissionDenied):
            return refused(503, "photo_store", kept=False)
        ref = reference()
        log.exception("The photo store failed on %s, reference %s.", what, ref)
        return JSONResponse({"code": "data_service", "trace_id": ref, "kept": False}, status_code=503)

    def locations(project_id: str, viewer: Viewer):
        """The project's locations from its record, read as the viewer, or none when the record cannot be read."""
        if places is not None:
            return places(project_id)
        from strata.research.project import project_facts

        try:
            if engine_for is None:
                return project_facts(project_id).locations
            with engine_for(viewer) as engine:
                return project_facts(project_id, engine=engine).locations
        except (LookupError, EngineError, ValueError):
            return ()

    @app.get("/api/projects/{project_id}/field-photos")
    def list_photos(project_id: str = Path(pattern=PROJECT), view: str = STAFF,
                    viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        config = load_field_photos()
        answer = {"project_id": project_id, "photos": [], "may_add": False, "preview": view != STAFF,
                  "limits": {"accept": list(config.accept), "max_size_bytes": config.max_size_bytes,
                             "max_per_project": config.max_per_project, "max_caption": config.max_caption}}
        # A preview of another view never shows a team's photos (the 38 brief, 6.9), the previewing person's own
        # included.
        if view != STAFF or store is None:
            return answer
        try:
            found = store.for_team(project_id, access.team(viewer).key, viewer.user_id)
        except EngineError as error:
            return failed(f"the field photos of {project_id}", error)
        return {**answer, "photos": [listing(photo, viewer) for photo in found], "may_add": access.is_staff(viewer)}

    @app.post("/api/projects/{project_id}/field-photos")
    async def add_photo(request: Request, project_id: str = Path(pattern=PROJECT),
                        sent_name: str = Header(alias="X-Strata-File-Name", min_length=1, max_length=2048),
                        sent_caption: str = Header("", alias="X-Strata-Caption", max_length=8192),
                        view: str = STAFF, viewer: Viewer = Depends(current_viewer)):
        file_name, caption = unquote(sent_name).strip(), " ".join(unquote(sent_caption).split())
        config = load_field_photos()
        if not viewer.user_id:
            return refused(401, "no_identity")
        if view != STAFF or not access.is_staff(viewer):
            return refused(403, "not_staff", kept=False)
        if not file_name or len(file_name) > 255:
            return refused(422, "bad_request", kept=False)
        if not caption or len(caption) > config.max_caption:
            return refused(422, "caption", kept=False, file_name=file_name, max_caption=config.max_caption)
        if store is None:
            return JSONResponse({"code": "no_data_service", "kept": False}, status_code=503)
        team = access.team(viewer).key
        try:
            kept = store.for_team(project_id, team, viewer.user_id)
        except EngineError as error:
            return failed(f"the field photos of {project_id}", error)
        if len(kept) >= config.max_per_project:
            return refused(422, "count", kept=False, file_name=file_name, max_per_project=config.max_per_project)
        data = await _body(request, config.max_size_bytes)
        if data is None:
            return refused(422, "size", kept=False, file_name=file_name, max_size=config.max_size_bytes)
        try:
            reading = field_photos.read_photo(data)
        except PhotoError as error:
            return refused(422, error.code, kept=False, file_name=file_name)
        near = field_photos.nearest_place(locations(project_id, viewer), reading.latitude, reading.longitude,
                                          config.nearest_place_km)
        photo_id = new_photo_id()
        photo = Photo(photo_id, project_id, team, viewer.user_id, viewer.name, file_name, caption, reading.taken_on,
                      reading.latitude, reading.longitude, near.name if near else None,
                      near.geo_loc_id if near else None, f"{photo_id}{reading.extension}", reading.media_type, now())
        try:
            store.create(photo, data)
        except (EngineError, OSError) as error:
            return failed(f"keeping {file_name}", error)
        return {"kept": True, "photo": listing(photo, viewer)}

    @app.get("/api/projects/{project_id}/field-photos/{photo_id}")
    def photo_file(project_id: str = Path(pattern=PROJECT), photo_id: str = Path(pattern=PHOTO), view: str = STAFF,
                   viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        if store is None:
            return refused(404, "unknown_photo")
        try:
            photo = store.get(photo_id)
            if photo is None or photo.project_id != project_id:
                return refused(404, "unknown_photo")
            if view != STAFF or not access.may_read(viewer, photo.team_key, photo.uploader_id):
                return refused(403, "not_your_team")
            data = store.file(photo)
        except (EngineError, OSError) as error:
            return failed(f"field photo {photo_id}", error)
        return Response(data, media_type=photo.media_type, headers={"Cache-Control": "private, no-store"})
