"""Where uploads are kept: strata.ops, written as the app's own service principal, beside the drafts (ticket 38).

An upload is kept only after its file was read and checked, and only its activities are kept, never the file. A
save writes the activities first (strata.ops.upload_rows) and the upload's own row last (strata.ops.uploads), and
every read starts from the upload's row, so a save that fails part way leaves nothing a reader can find; the store
then removes the rows it wrote with a DELETE that names the upload (CLAUDE.md rule 5). Nothing else changes or
removes an upload: removing one is a retention policy the owner has not set.

The store holds no access rule. The upload routes (src/strata/server/uploads.py) ask the one access rule
(src/strata/server/access.py) before they show anything, and so do the tools that read an upload, through the
reader the routes give them. Every engine gives typed values (ticket 128), and each is
read once here.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

from strata.drafts.store import moment
from strata.lakehouse.engine import Engine, EngineError

UPLOAD_COLUMNS = ("upload_id", "team_key", "uploader_id", "uploader_name", "idempotency_key", "project_id",
                  "implementing_agency", "file_name", "reading", "uploaded_at", "public_from")
ROW_COLUMNS = ("upload_id", "position", "activity_reference_no", "description", "content", "public_from")


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.uploads") / "sql" / f"{name}.sql").read_text()


def _day(value) -> str | None:
    return value.isoformat() if isinstance(value, dt.date) else value


@dataclass
class NewUpload:
    upload_id: str
    team_key: str
    uploader_id: str
    uploader_name: str | None
    idempotency_key: str | None
    project_id: str
    implementing_agency: str
    file_name: str
    reading: dict  # sheets, used and unused headers
    uploaded_at: dt.datetime
    rows: list[dict] = field(default_factory=list)  # each activity: position, reference, description and the rest


@dataclass(frozen=True)
class Saved:
    """An upload as it is kept: its row, and its activities in the file's order (empty for a listing)."""

    upload_id: str
    team_key: str
    uploader_id: str
    uploader_name: str | None
    project_id: str
    implementing_agency: str
    file_name: str
    reading: dict
    uploaded_at: dt.datetime
    rows: tuple[dict, ...] = ()

    @property
    def uploaded_on(self) -> dt.date:
        return self.uploaded_at.astimezone(dt.UTC).date()


def row_content(row: dict) -> str:
    """An activity's values as the content column keeps them: dates as ISO dates."""
    steps = {name: {head: _day(day) for head, day in dates.items()} for name, dates in row["steps"].items()}
    fields = {key: (str(value) if value is not None and not isinstance(value, str) else value)
              for key, value in row["fields"].items()}
    return json.dumps({"sheet": row.get("sheet"), "section": row.get("section"), "fields": fields, "steps": steps,
                       "notes": row.get("notes") or [], "raw": row.get("raw") or {}}, ensure_ascii=False)


class UploadStore:
    """The uploads in strata.ops. engine() opens the engine that reads and writes them: the app's own."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    @contextmanager
    def _open(self) -> Iterator[Engine]:
        engine = self.engine()
        try:
            yield engine
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                close()

    @staticmethod
    def _rows(engine: Engine, query: str, **params) -> list[dict]:
        result = engine.run(_sql(query), params)
        return [dict(zip(result.columns, row)) for row in result.rows]

    def create(self, upload: NewUpload) -> None:
        """Keep an upload: its activities first, then its own row, which makes it readable. A failure part way removes
        the activities written, so nothing of it stays where a reader could find it."""
        day = upload.uploaded_at.astimezone(dt.UTC).date()
        with self._open() as engine:
            try:
                engine.insert_rows("strata.ops.upload_rows", ROW_COLUMNS, [(
                    upload.upload_id, row["position"], row.get("reference"), row.get("description"), row_content(row),
                    day) for row in upload.rows])
                engine.insert_rows("strata.ops.uploads", UPLOAD_COLUMNS, [(
                    upload.upload_id, upload.team_key, upload.uploader_id, upload.uploader_name,
                    upload.idempotency_key, upload.project_id, upload.implementing_agency, upload.file_name,
                    json.dumps(upload.reading, ensure_ascii=False), upload.uploaded_at, day)])
            except EngineError:
                with suppress(EngineError):  # the save already failed: say so, whether or not the removal ran
                    engine.run(_sql("remove_rows"), {"upload_id": upload.upload_id})
                raise

    def _saved(self, row: dict, rows: list[dict]) -> Saved:
        return Saved(row["upload_id"], row["team_key"], row["uploader_id"], row["uploader_name"], row["project_id"],
                     row["implementing_agency"], row["file_name"], json.loads(row["reading"]),
                     moment(row["uploaded_at"]), tuple(rows))

    def get(self, upload_id: str) -> Saved | None:
        """One upload by its id, whatever its team, with its activities: the caller asks the access rule."""
        with self._open() as engine:
            found = self._rows(engine, "upload", upload_id=upload_id)
            if not found:
                return None
            rows = [{"position": row["position"], "reference": row["activity_reference_no"],
                     "description": row["description"], **json.loads(row["content"])}
                    for row in self._rows(engine, "rows", upload_id=upload_id)]
        return self._saved(found[0], rows)

    def for_team(self, team_key: str, uploader_id: str) -> list[Saved]:
        """The uploads kept under a team, and every upload of this uploader whatever team they were on, newest
        first, without their activities."""
        with self._open() as engine:
            found = self._rows(engine, "team_uploads", team_key=team_key, uploader_id=uploader_id)
        return [self._saved(row, []) for row in found]

    def by_key(self, uploader_id: str, idempotency_key: str) -> str | None:
        with self._open() as engine:
            found = self._rows(engine, "by_key", uploader_id=uploader_id, idempotency_key=idempotency_key)
        return found[0]["upload_id"] if found else None
