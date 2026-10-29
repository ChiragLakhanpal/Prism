"""The demo's pages, read ahead (ticket 125), so a presenter never meets a cold page.

The SQL warehouse stops after ten idle minutes and takes seconds to start again, and each page read from it costs
seconds even with its reads in one batch. So the App reads the demo's cases (config/demo.toml) into the pages it keeps
(src/strata/server/page_cache.py) when it starts, and again every app.warm_every_seconds (config/thresholds.toml; 0
turns it off): for each project its header, Summary, Timeline and Packages as a person first opens them (as of today,
in the World Bank staff view, the first page of Packages with no search), and for each package its header. A warm
reads each page again, so a page it kept never reaches the end of its window before the next warm.

Each warm first reads when the nightly job last finished a task (strata.ops.pipeline_runs). When that time is not the
one the warm saw before, the night's data changed, so every kept page goes before the warm reads the demo's again.

The warm reads as the App itself: the App's own service principal, with the token its client id and secret get, the
one identity the App holds outside a request (src/strata/server/settings.py). It reads through the same routes' reads
as a viewer would, so the page it keeps is the page a viewer in that role would get. A read the warehouse refuses is
logged and left for a viewer's first view; nothing a warm does changes what a viewer sees otherwise.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from collections.abc import Callable

from strata.config import Demo
from strata.dbx import Viewer
from strata.lakehouse.engine import Engine
from strata.server.page_cache import PageCache, PageKey
from strata.server.viewer_sql import nightly_finished

log = logging.getLogger("strata.server.warm")
STAFF = "staff"  # the view a person first opens a page in


def demo_pages(demo: Demo, as_of: dt.date) -> list[PageKey]:
    """The demo's pages as a person first opens them, as of the date: each project's header, Summary, Timeline (with
    no date asked) and the first page of its Packages, then each package's header."""
    return [*[PageKey(page, STAFF, as_of, args) for project_id in demo.projects
              for page, args in (("project", (project_id,)), ("summary", (project_id,)),
                                 ("timeline", (project_id, None)), ("packages", (project_id, "", 1)))],
            *[PageKey("package", STAFF, as_of, (step_reference,)) for step_reference in demo.packages]]


class Warm:
    """Reads the demo's pages into the kept pages as the App, once when the App starts and then every every_seconds
    by the clock. tick() runs one warm when one is due; start() runs tick() on a thread of its own, every
    poll_seconds, until stop(). ran is set each time a warm has run."""

    def __init__(self, demo: Demo, as_the_app: Callable[[], Viewer], every_seconds: float,
                 clock: Callable[[], float] = time.monotonic,
                 finished: Callable[[Engine], object] = nightly_finished, poll_seconds: float = 60):
        self.demo, self.as_the_app, self.every_seconds = demo, as_the_app, every_seconds
        self.clock, self.finished, self.poll_seconds = clock, finished, poll_seconds
        self.last: float | None = None
        self.seen: object = None
        self.ran = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._read_page = self._read_as = self._cache = self._today = None

    def bind(self, read_page: Callable[[PageKey, Viewer], object],
             read_as: Callable[[Viewer, Callable[[Engine], object]], object], cache: PageCache,
             today: Callable[[], dt.date]) -> None:
        """What create_app gives the warm: a page read again as a viewer and kept, one read as a viewer, the kept
        pages, and the day a page is read as of."""
        self._read_page, self._read_as, self._cache, self._today = read_page, read_as, cache, today

    def tick(self) -> bool:
        """Run one warm, when one is due. Returns whether it ran."""
        if self.every_seconds <= 0 or self._read_page is None:
            return False
        at = self.clock()
        if self.last is not None and at - self.last < self.every_seconds:
            return False
        self.last = at
        started = time.monotonic()
        try:
            viewer = self.as_the_app()
            self._clear_after_the_nightly(viewer)
            pages = demo_pages(self.demo, self._today())
            kept = sum(self._warm(key, viewer) for key in pages)
            log.info("I read %d of the demo's %d pages ahead, as the App, in %.1f seconds.", kept, len(pages),
                     time.monotonic() - started)
        except Exception:  # the App's own token or the warehouse: a viewer's first view reads the page instead
            log.exception("I could not read the demo's pages ahead.")
        finally:
            self.ran.set()
        return True

    def _clear_after_the_nightly(self, viewer: Viewer) -> None:
        try:
            finished = self._read_as(viewer, self.finished)
        except Exception:  # noqa: BLE001 - the warm still runs; the pages' window still bounds them
            log.warning("I could not read when the nightly job last finished, so I kept the pages I hold.",
                        exc_info=True)
            return
        if finished != self.seen:
            self._cache.clear()
            self.seen = finished

    def _warm(self, key: PageKey, viewer: Viewer) -> bool:
        try:
            answer = self._read_page(key, viewer)
        except Exception:  # one page's failure leaves the others to read
            log.exception("I could not read the demo's page %s ahead.", key)
            return False
        status = getattr(answer, "status_code", 200)
        if status != 200:
            log.warning("I could not read the demo's page %s ahead: it answered %s.", key, status)
        return status == 200

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="strata-warm", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            self.tick()
            if self._stop.wait(self.poll_seconds):
                return

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
