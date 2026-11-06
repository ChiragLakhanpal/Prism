"""Field photos (ticket 150): the photos World Bank staff take on a mission and add to a project's Deep research tab,
which only the uploader's team sees, and which a run by a viewer of that team cites in the brief.

- read_photo() reads a JPEG or a PNG with Pillow, and from its EXIF data the day the camera recorded and its GPS
  position. A photo without them is kept, with no date or no position.
- PhotoStore keeps each photo's fields in strata.ops.field_photos and its file through a PhotoFiles adapter: the
  volume on the workspace (VolumeFiles, written as the app's own service principal through the Files API), or a
  folder beside the app state's DuckDB file on this computer (LocalFiles), never in the repo. It writes the file
  first and the row last, so a row a reader finds always has its file. The store holds no access rule: the routes
  (src/strata/server/field_photos.py) ask the one access rule before they show anything.
- item_of() makes a photo an item of ticket 147's shape, kind field_photo, public_from None and team set. Its text is
  the uploader's caption, so the brief's writer can describe the photo only in the uploader's words: the writer is
  never sent the photo itself.
"""

from __future__ import annotations

import datetime as dt
import math
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from importlib import resources
from io import BytesIO
from pathlib import Path
from typing import Protocol

from strata.config import FieldPhotos
from strata.lakehouse.engine import Engine, EngineError, PermissionDenied, base_url
from strata.research.items import PREFIX as ITEM_PREFIX
from strata.research.items import evidence_id

SOURCE_KEY = "field_photos"
KIND = "field_photo"
PREFIX = "fph-"  # a photo's id: fph- and twelve hex digits
MEDIA_TYPES = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png")}
EXIF_IFD, GPS_IFD = 0x8769, 0x8825
DATE_TIME_ORIGINAL, DATE_TIME = 36867, 306
GPS_LATITUDE_REF, GPS_LATITUDE, GPS_LONGITUDE_REF, GPS_LONGITUDE = 1, 2, 3, 4
PHOTO_COLUMNS = ("photo_id", "project_id", "team_key", "uploader_id", "uploader_name", "file_name", "caption",
                 "taken_on", "latitude", "longitude", "place", "geo_loc_id", "stored_as", "media_type", "uploaded_at",
                 "public_from")


class PhotoError(ValueError):
    """A file Prism does not keep as a field photo: code names why, for the screen's sentence."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Reading:
    media_type: str
    extension: str
    taken_on: dt.date | None
    latitude: float | None
    longitude: float | None


def _degrees(value, ref) -> float | None:
    try:
        degrees, minutes, seconds = (float(part) for part in value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    found = degrees + minutes / 60 + seconds / 3600
    if not math.isfinite(found):
        return None
    return round(-found if str(ref).strip().upper() in ("S", "W") else found, 6)


def _day(text) -> dt.date | None:
    try:
        return dt.datetime.strptime(str(text).strip()[:19], "%Y:%m:%d %H:%M:%S").date()
    except ValueError:
        return None


def read_photo(data: bytes) -> Reading:
    """The photo's format, and the day and position its EXIF data recorded. PhotoError("format") for a file that is
    not a JPEG or a PNG Pillow can read."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in MEDIA_TYPES:
                raise PhotoError("format")
            image.load()
            exif = image.getexif()
    except PhotoError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
        raise PhotoError("format") from error
    media_type, extension = MEDIA_TYPES[image.format]
    taken = _day(exif.get_ifd(EXIF_IFD).get(DATE_TIME_ORIGINAL) or exif.get(DATE_TIME) or "")
    gps = exif.get_ifd(GPS_IFD)
    latitude = _degrees(gps.get(GPS_LATITUDE), gps.get(GPS_LATITUDE_REF)) if GPS_LATITUDE in gps else None
    longitude = _degrees(gps.get(GPS_LONGITUDE), gps.get(GPS_LONGITUDE_REF)) if GPS_LONGITUDE in gps else None
    if latitude is None or longitude is None or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        latitude = longitude = None
    return Reading(media_type, extension, taken, latitude, longitude)


def kilometres(a: tuple[float, float], b: tuple[float, float]) -> float:
    """The great-circle distance between two positions, in kilometres."""
    (lat1, lon1), (lat2, lon2) = (tuple(math.radians(value) for value in point) for point in (a, b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def nearest_place(locations, latitude: float | None, longitude: float | None, within_km: float):
    """The project location nearest the position, when it is within within_km, or None."""
    if latitude is None or longitude is None:
        return None
    found = [(kilometres((latitude, longitude), (location.latitude, location.longitude)), location)
             for location in locations]
    near = min(found, key=lambda pair: pair[0], default=None)
    return near[1] if near and near[0] <= within_km else None


# ── Where the files are kept ─────────────────────────────────────────────

class PhotoFiles(Protocol):
    def put(self, name: str, data: bytes) -> None: ...

    def get(self, name: str) -> bytes: ...


class LocalFiles:
    """On this computer: a folder beside the app state's DuckDB file."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def put(self, name: str, data: bytes) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / name).write_bytes(data)

    def get(self, name: str) -> bytes:
        return (self.folder / name).read_bytes()


class VolumeFiles:
    """On the workspace: a Unity Catalog volume, through the Files API, as the app's own service principal."""

    def __init__(self, host: str, token: Callable[[], str], volume: str, timeout: int = 60):
        self.base, self.token, self.volume, self.timeout = base_url(host), token, volume.rstrip("/"), timeout

    def _call(self, method: str, name: str, data: bytes | None = None) -> bytes:
        path = urllib.parse.quote(f"{self.volume}/{name}")
        request = urllib.request.Request(
            f"{self.base}/api/2.0/fs/files{path}" + ("?overwrite=false" if method == "PUT" else ""), method=method,
            data=data, headers={"Authorization": f"Bearer {self.token()}", "Content-Type": "application/octet-stream"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            refused = PermissionDenied if error.code in (401, 403) else EngineError
            raise refused(f"The workspace answered {error.code} to {method} on the field photos volume.") from error
        except OSError as error:
            raise EngineError(f"I could not reach the field photos volume: {error}") from error

    def put(self, name: str, data: bytes) -> None:
        self._call("PUT", name, data)

    def get(self, name: str) -> bytes:
        return self._call("GET", name)


# ── The store ────────────────────────────────────────────────────────────

@cache
def _sql(name: str) -> str:
    return (resources.files("strata.research") / "sql" / f"{name}.sql").read_text()


@dataclass(frozen=True)
class Photo:
    photo_id: str
    project_id: str
    team_key: str
    uploader_id: str
    uploader_name: str | None
    file_name: str
    caption: str
    taken_on: dt.date | None
    latitude: float | None
    longitude: float | None
    place: str | None
    geo_loc_id: str | None
    stored_as: str
    media_type: str
    uploaded_at: dt.datetime

    @property
    def uploaded_on(self) -> dt.date:
        moment = self.uploaded_at
        return (moment.astimezone(dt.UTC) if moment.tzinfo else moment).date()


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _moment(value) -> dt.datetime:
    moment = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=dt.UTC)


def _float(value) -> float | None:
    return None if value is None or value == "" else float(value)


class PhotoStore:
    """The field photos in strata.ops and their files. engine() opens the engine that reads and writes them: the
    app's own."""

    def __init__(self, engine: Callable[[], Engine], files: PhotoFiles):
        self.engine, self.files = engine, files
        self.forgets: list[Callable[[str], None]] = []

    def on_forget(self, forget: Callable[[str], None]) -> None:
        """forget(photo_id) is called each time the store keeps, replaces or removes a photo, so a copy kept elsewhere
        (the photo route's memory, ticket 160) goes. A path that removes a photo must call forget() too."""
        self.forgets.append(forget)

    def forget(self, photo_id: str) -> None:
        for forget in self.forgets:
            forget(photo_id)

    @contextmanager
    def _open(self):
        engine = self.engine()
        try:
            yield engine
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                close()

    @staticmethod
    def _photo(row: dict) -> Photo:
        return Photo(row["photo_id"], row["project_id"], row["team_key"], row["uploader_id"], row["uploader_name"],
                     row["file_name"], row["caption"], _date(row["taken_on"]), _float(row["latitude"]),
                     _float(row["longitude"]), row["place"], row["geo_loc_id"], row["stored_as"], row["media_type"],
                     _moment(row["uploaded_at"]))

    def _rows(self, name: str, **params) -> list[dict]:
        with self._open() as engine:
            result = engine.run(_sql(name), params)
        return [dict(zip(result.columns, row)) for row in result.rows]

    def create(self, photo: Photo, data: bytes) -> None:
        """Keep a photo: its file first, then its row, which makes it readable. Any copy of a photo with its id goes."""
        try:
            self.files.put(photo.stored_as, data)
            with self._open() as engine:
                engine.insert_rows("strata.ops.field_photos", PHOTO_COLUMNS, [(
                    photo.photo_id, photo.project_id, photo.team_key, photo.uploader_id, photo.uploader_name,
                    photo.file_name, photo.caption, photo.taken_on, photo.latitude, photo.longitude, photo.place,
                    photo.geo_loc_id, photo.stored_as, photo.media_type,
                    photo.uploaded_at.astimezone(dt.UTC).replace(tzinfo=None), photo.uploaded_on)])
        finally:
            self.forget(photo.photo_id)

    def every(self) -> list[Photo]:
        """Every team's photos, newest first: for the load into the photo route's memory, which asks the access rule
        on every request before it serves one."""
        return [self._photo(row) for row in self._rows("every_field_photo")]

    def get(self, photo_id: str) -> Photo | None:
        """One photo by its id, whatever its team: the caller asks the access rule."""
        found = self._rows("field_photo", photo_id=photo_id)
        return self._photo(found[0]) if found else None

    def for_team(self, project_id: str, team_key: str, uploader_id: str) -> list[Photo]:
        """A project's photos kept under the team, and the uploader's own whatever team they were on, newest first."""
        return [self._photo(row) for row in self._rows("team_field_photos", project_id=project_id, team_key=team_key,
                                                       uploader_id=uploader_id)]

    def file(self, photo: Photo) -> bytes:
        return self.files.get(photo.stored_as)


# ── A photo as a research item ───────────────────────────────────────────

def photo_url(project_id: str, photo_id: str) -> str:
    """The photo route, which answers only the uploader's team."""
    return f"/api/projects/{project_id}/field-photos/{photo_id}"


def _when(day: dt.date) -> str:
    return f"{day.strftime('%B')} {day.day}, {day.year}"


def title_of(photo: Photo) -> str:
    """The item's one line, with the place and the day the photo's own data recorded, so a sentence that states them
    is checked against the item."""
    where = f"at {photo.place}" if photo.place else "at a position its data did not record" if photo.latitude is None \
        else f"at {photo.latitude:.4f}, {photo.longitude:.4f}"
    when = f"on {_when(photo.taken_on)}" if photo.taken_on else "on a day its data did not record"
    return f"Field photo taken {where} {when}, added by a World Bank staff member"


def item_of(photo: Photo, config: FieldPhotos) -> dict:
    """The photo in ticket 147's one item shape: kind field_photo, public_from None, team set, its text the
    uploader's caption, and no image address, so the writer never reads the pixels."""
    location = None
    if photo.latitude is not None and photo.longitude is not None:
        location = {"geo_loc_id": photo.geo_loc_id, "name": photo.place, "latitude": photo.latitude,
                    "longitude": photo.longitude}
    return {"evidence_id": evidence_id(photo.project_id, SOURCE_KEY, photo.photo_id), "public_from": None,
            "source": {"key": SOURCE_KEY, "label": config.label, "kind": KIND, "license": config.license,
                       "url_of_source": photo_url(photo.project_id, photo.photo_id)},
            "kind": KIND, "title": title_of(photo), "text": photo.caption,
            "url": photo_url(photo.project_id, photo.photo_id), "published": None, "date_known": False,
            "observed": photo.taken_on.isoformat() if photo.taken_on else None, "location": location,
            "image_urls": [], "author": "World Bank staff member", "read_on": photo.uploaded_on.isoformat(),
            "team": photo.team_key}
