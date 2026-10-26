"""The reader's visits to Lessons, so the page opens on what came in since the last one (ticket 39; the 39 brief,
section 4.2).

A visit is a session on any Lessons page. It starts when the reader opens Lessons after lessons.visit_gap_minutes
away (config/thresholds.toml); a reload, or a trip to a draft and back, stays in the same visit, so the counts do not
reset while the reader works through them. The digest's window runs from the start of the previous visit to the
start of this one. The first time a reader opens Lessons there is no window.

LessonVisits keeps them in strata.ops.lesson_visits through the app's own service principal, with the viewer the
Databricks App forwarded (CLAUDE.md rule 7: nothing about a viewer is kept between requests). Each page load adds a
row and changes none (CLAUDE.md rule 5). A preview or an as-of view reads the window and records nothing.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from importlib import resources

from strata.drafts.store import moment
from strata.lakehouse.engine import Engine

COLUMNS = ("viewer_id", "visit_started_at", "seen_at", "public_from")


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.knowledge.lessons") / "sql" / f"{name}.sql").read_text()


@dataclass(frozen=True)
class Visit:
    """This visit's start, and the previous visit's start, which opens the digest's window; None on a first visit."""

    started_at: dt.datetime
    previous_started_at: dt.datetime | None

    @property
    def first(self) -> bool:
        return self.previous_started_at is None

    def as_dict(self) -> dict:
        def iso(value: dt.datetime | None) -> str | None:
            return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z") if value else None

        return {"first_visit": self.first, "started_at": iso(self.started_at),
                "last_visit_at": iso(self.previous_started_at),
                "last_visit_on": self.previous_started_at.date().isoformat() if self.previous_started_at else None}


def visit_at(rows: list[tuple[dt.datetime, dt.datetime]], now: dt.datetime, gap: dt.timedelta) -> Visit:
    """The visit a page load at now belongs to, from the reader's earlier loads as (visit started, seen) pairs."""
    latest = max(rows, key=lambda row: row[1], default=None)
    started = latest[0] if latest is not None and now - latest[1] <= gap else now
    earlier = [start for start, _ in rows if start < started]
    return Visit(started, max(earlier) if earlier else None)


class LessonVisits:
    """The visits in strata.ops.lesson_visits. engine() opens the app's own engine, which reads and writes them."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    @contextmanager
    def _open(self):
        engine = self.engine()
        try:
            yield engine
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                close()

    def visit(self, viewer_id: str, now: dt.datetime, gap: dt.timedelta, record: bool) -> Visit:
        """The visit this page load belongs to; recorded unless record is false (a preview or an as-of view)."""
        with self._open() as engine:
            result = engine.run(_sql("visits"), {"viewer_id": viewer_id})
            rows = [(moment(started), moment(seen)) for started, seen in result.rows]
            found = visit_at(rows, now, gap)
            if record:
                engine.insert_rows("strata.ops.lesson_visits", COLUMNS,
                                   [(viewer_id, found.started_at, now, now.astimezone(dt.UTC).date())])
        return found
