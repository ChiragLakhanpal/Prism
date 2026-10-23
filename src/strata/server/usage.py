"""Usage events: one row in strata.ops.usage_events for each request a viewer makes.

The adoption measures (weekly users, the page each visit starts on and the API routes it calls,
which view people use) read these rows. The web app's router changes pages without asking the
server, so later pages in a visit are not recorded. An event keeps the viewer's user id, never
their email, because every account user can read strata.ops. The server keeps each event in memory and writes them in one insert at a time, from a
background thread every usage_flush_seconds (config/thresholds.toml) and once more when the
server stops, so no request waits for the warehouse. A write that fails is logged and its
events wait for the next one; a request never fails because its event could not be written.

On the Databricks App the rows are written as the app's own service principal, because a
viewer only reads (ADR 0003): the deploy grants the principal MODIFY on this one table.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
from collections.abc import Callable
from dataclasses import astuple, dataclass

from strata.lakehouse.engine import Engine

log = logging.getLogger("strata.server.usage")
TABLE = "strata.ops.usage_events"
COLUMNS = ("viewer_id", "route", "view", "requested_at", "trace_id", "public_from")
# Events kept while the warehouse cannot take them. Beyond this, the oldest are dropped.
MOST_KEPT = 5000


@dataclass(frozen=True)
class UsageEvent:
    viewer_id: str | None
    route: str
    view: str
    requested_at: dt.datetime
    trace_id: str | None

    def row(self) -> tuple:
        return (*astuple(self), self.requested_at.astimezone(dt.UTC).date())


class UsageLog:
    """Usage events on their way to strata.ops.usage_events.

    engine() opens the engine that writes them; flush_seconds=None writes only when flush() or
    stop() is called, as the tests do.
    """

    def __init__(self, engine: Callable[[], Engine], flush_seconds: float | None):
        self.engine, self.flush_seconds = engine, flush_seconds
        self.waiting: list[UsageEvent] = []
        self.lock = threading.Lock()
        self.stopping = threading.Event()
        self.thread: threading.Thread | None = None

    def record(self, event: UsageEvent) -> None:
        with self.lock:
            self.waiting.append(event)

    def flush(self) -> int:
        """Write every waiting event in one insert. Returns how many it wrote."""
        with self.lock:
            batch, self.waiting = self.waiting, []
        if not batch:
            return 0
        try:
            engine = self.engine()
            try:
                engine.insert_rows(TABLE, COLUMNS, [event.row() for event in batch])
            finally:
                close = getattr(engine, "close", None)
                if callable(close):
                    close()
        except Exception:  # the warehouse, the network or a token: none of them may stop a page
            log.exception("I could not write %d usage events; they wait for the next write.", len(batch))
            with self.lock:
                self.waiting = (batch + self.waiting)[-MOST_KEPT:]
            return 0
        return len(batch)

    def start(self) -> None:
        if self.flush_seconds is None or self.thread is not None:
            return
        self.stopping.clear()

        def every_few_seconds():
            while not self.stopping.wait(self.flush_seconds):
                self.flush()

        self.thread = threading.Thread(target=every_few_seconds, name="strata-usage", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stopping.set()
        if self.thread is not None:
            self.thread.join(timeout=5)
            self.thread = None
        self.flush()
