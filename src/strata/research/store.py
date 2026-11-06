"""Where deep research runs, their items and the briefs written from them are kept: strata.ops.research_runs and
research_items (ticket 147), and research_briefs (ticket 148), which keeps the team of a brief written from a team's
field photos (ticket 150).

Written as the uploads are (src/strata/uploads/store.py): on the workspace as the app's own service principal, on this
computer in the local DuckDB file the drafts use (STRATA_APP_STATE_FILE), through one engine factory. A save writes
the run's items first and the run's own row last, and every read starts from the run's row, so a save that fails
part way leaves nothing a reader can find; the store then removes the items it wrote with a DELETE that names the run
(CLAUDE.md rule 5). A run already kept is not written again, so a second seed changes nothing. An item read again in
a later run keeps the read_on of the first run that read it. A brief is a new row each time it is written, and
latest_brief() reads the newest, so a second view of the brief calls no model.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

from strata.lakehouse.engine import Engine, EngineError
from strata.research.fetching import opened
from strata.research.items import ITEM_KEYS, iso

RUN_COLUMNS = ("run_id", "project_id", "started", "finished", "as_of", "viewer", "sources_asked", "reached", "note",
               "source_notes", "public_from")
ITEM_COLUMNS = ("evidence_id", "run_id", "project_id", "source_key", "kind", "source", "title", "text", "url",
                "published", "date_known", "observed", "location", "image_urls", "author", "read_on", "public_from")
BRIEF_COLUMNS = ("run_id", "project_id", "written_at", "as_of", "brief", "public_from", "team_key")


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.research") / "sql" / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _utc(moment: dt.datetime) -> dt.datetime:
    """A moment as the TIMESTAMP columns keep it: UTC, without a zone."""
    return moment.astimezone(dt.UTC).replace(tzinfo=None) if moment.tzinfo else moment


def _moment(value) -> dt.datetime | None:
    if value is None or value == "":
        return None
    moment = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=dt.UTC)


def _date(value) -> dt.date | None:
    text = iso(value)
    return dt.date.fromisoformat(text) if text else None


@dataclass(frozen=True)
class Run:
    """One deep research run: who asked, as of when, which sources were asked and which answered, and each source's
    status and note (source_notes, by source key: {status, note, items})."""

    run_id: str
    project_id: str
    started: dt.datetime
    as_of: dt.date
    sources_asked: tuple[str, ...]
    reached: tuple[str, ...]
    finished: dt.datetime | None = None
    viewer: str | None = None
    note: str | None = None
    source_notes: dict = field(default_factory=dict, compare=False)


class ResearchStore:
    """The research runs and briefs in strata.ops. engine() opens the engine that reads and writes them: the app's
    own."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    def save(self, run: Run, items: list[dict]) -> bool:
        """Keep a run and its items: the items first, then the run's row, which makes them readable. False when the run
        is kept already, and then nothing is written."""
        with opened(self.engine) as engine:
            if _rows(engine, "research_run", run_id=run.run_id):
                return False
            first = {row["evidence_id"]: iso(row["read_on"])
                     for row in _rows(engine, "first_read_on", project_id=run.project_id)}
            rows = []
            for item in items:
                read_on = min(day for day in (first.get(item["evidence_id"]), item["read_on"]) if day)
                rows.append((item["evidence_id"], run.run_id, run.project_id, item["source"]["key"], item["kind"],
                             json.dumps(item["source"], ensure_ascii=False), item["title"], item["text"], item["url"],
                             _date(item["published"]), bool(item["date_known"]), _date(item["observed"]),
                             json.dumps(item["location"], ensure_ascii=False) if item["location"] else None,
                             json.dumps(item["image_urls"]), item["author"], _date(read_on),
                             _date(item["public_from"])))
            try:
                if rows:
                    engine.insert_rows("strata.ops.research_items", ITEM_COLUMNS, rows)
                engine.insert_rows("strata.ops.research_runs", RUN_COLUMNS, [(
                    run.run_id, run.project_id, _utc(run.started), _utc(run.finished) if run.finished else None,
                    run.as_of, run.viewer, json.dumps(list(run.sources_asked)), json.dumps(list(run.reached)),
                    run.note, json.dumps(run.source_notes, ensure_ascii=False), run.as_of)])
            except EngineError:
                with suppress(EngineError):  # the save already failed: say so, whether or not the removal ran
                    engine.run(_sql("remove_run_items"), {"run_id": run.run_id})
                raise
        return True

    @staticmethod
    def _run(row: dict) -> Run:
        return Run(run_id=row["run_id"], project_id=row["project_id"], started=_moment(row["started"]),
                   as_of=_date(row["as_of"]), sources_asked=tuple(json.loads(row["sources_asked"])),
                   reached=tuple(json.loads(row["reached"])), finished=_moment(row["finished"]),
                   viewer=row["viewer"], note=row["note"], source_notes=json.loads(row["source_notes"] or "{}"))

    def run(self, run_id: str) -> Run | None:
        with opened(self.engine) as engine:
            found = _rows(engine, "research_run", run_id=run_id)
        return self._run(found[0]) if found else None

    def runs(self, project_id: str) -> list[Run]:
        """A project's runs, newest first."""
        with opened(self.engine) as engine:
            return [self._run(row) for row in _rows(engine, "research_runs", project_id=project_id)]

    def items(self, run_id: str) -> list[dict]:
        """A kept run's items, in the one item shape, newest first; none for a run that is not kept."""
        with opened(self.engine) as engine:
            if not _rows(engine, "research_run", run_id=run_id):
                return []
            found = _rows(engine, "research_items", run_id=run_id)
        items = []
        for row in found:
            item = {"evidence_id": row["evidence_id"], "public_from": iso(row["public_from"]),
                    "source": json.loads(row["source"]), "kind": row["kind"], "title": row["title"],
                    "text": row["text"], "url": row["url"], "published": iso(row["published"]),
                    "date_known": bool(row["date_known"]), "observed": iso(row["observed"]),
                    "location": json.loads(row["location"]) if row["location"] else None,
                    "image_urls": json.loads(row["image_urls"]), "author": row["author"],
                    "read_on": iso(row["read_on"]), "team": None}
            items.append({key: item[key] for key in ITEM_KEYS})
        return items

    def save_brief(self, run_id: str, project_id: str, written_at: dt.datetime, as_of: dt.date, brief: dict,
                   team_key: str | None = None) -> None:
        """A brief written from a kept run (ticket 148), as a new row. team_key names the team whose field photos the
        run read (ticket 150), so only that team reads the brief; None for a brief on public items alone."""
        with opened(self.engine) as engine:
            engine.insert_rows("strata.ops.research_briefs", BRIEF_COLUMNS, [(
                run_id, project_id, _utc(written_at), as_of, json.dumps(brief, ensure_ascii=False),
                _utc(written_at).date(), team_key)])

    def latest_brief(self, project_id: str, as_of: dt.date, team_key: str | None = None) -> dict | None:
        """The latest brief for the project as of the day that the viewer's team may read, with its run and when it
        was written, or None. A brief on public items is read by everyone; one written from a team's field photos
        only by that team (ticket 150)."""
        with opened(self.engine) as engine:
            found = _rows(engine, "latest_brief", project_id=project_id, as_of=as_of, team_key=team_key or "")
        if not found:
            return None
        row = found[0]
        written = row["written_at"]
        return {**json.loads(row["brief"]), "run_id": row["run_id"],
                "written_at": written.isoformat() if isinstance(written, dt.datetime) else str(written)}
