"""The pages the App keeps in its memory (ticket 125), so the second view of a page is instant.

On the workspace each statement costs the SQL warehouse's statements API about two seconds, so a page read from it
takes seconds even with its reads in one batch. A page's answer is the same for everyone who asks for it with the same
as-of date in the same view, so the App keeps it, by the page, its own arguments (such as the project ID), its as-of
day and the viewer's role, for app.page_cache_seconds, and at most app.page_cache_entries pages, the oldest read let go
first (config/thresholds.toml). The browser is told to keep the answer as long, and no longer (Cache-Control).

The role is the view the request is bound to: World Bank staff, or a preview of the implementing agency or public view
(src/strata/server/views.py). The pages kept read nothing else about the viewer, and only public tables, so two people
in one view get the same answer from the warehouse. A viewer with no forwarded token is never served a kept page, so
the App never answers for someone the warehouse would refuse; a kept page is still served to a signed-in viewer whose
own grants the warehouse would refuse, a decision parked for the owner. Only a page's answer is kept, never an error.

The kept pages are cleared when the nightly job finishes (the warm in src/strata/server/warm.py sees its new end
time) and when their window passes, and a project's header goes when a baseline is saved or removed (it shows the
baseline). A page read while pages were let go may hold what changed, so it is sent but not kept (generation). A page
read past a failed read, such as the Timeline with its disagreements failed, is not kept either (src/strata/server/
app.py, read_for).

Nothing about a viewer is kept: the key holds the role, never the person (CLAUDE.md rule 7).
"""

from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
import datetime as dt

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from strata.config import Thresholds


@dataclass(frozen=True)
class PageKey:
    """A page as the App keeps it: its name, the viewer's role, its as-of day and its own arguments."""

    page: str
    role: str
    as_of: dt.date
    args: tuple


@dataclass(frozen=True)
class Kept:
    body: bytes
    until: float  # by the cache's clock


class PageCache:
    """Pages kept for `seconds`, at most `entries` of them, by a clock in seconds (time.monotonic, or a test's)."""

    def __init__(self, seconds: float, entries: int, clock: Callable[[], float] = time.monotonic):
        self.seconds, self.entries, self.clock = seconds, entries, clock
        self.kept: OrderedDict[PageKey, Kept] = OrderedDict()
        self.lock = threading.Lock()
        self.generation = 0  # one more each time pages are let go; a read that began before then is not kept

    @classmethod
    def from_thresholds(cls, thresholds: Thresholds, clock: Callable[[], float] = time.monotonic) -> PageCache:
        return cls(thresholds.value("app.page_cache_seconds"), int(thresholds.value("app.page_cache_entries")), clock)

    def get(self, key: PageKey) -> Kept | None:
        """The page kept under this key, if its window has not passed."""
        with self.lock:
            found = self.kept.get(key)
            if found is None:
                return None
            if found.until <= self.clock():
                del self.kept[key]
                return None
            self.kept.move_to_end(key)
            return found

    def keep(self, key: PageKey, answer, generation: int | None = None) -> Kept | None:
        """Keep a page's answer as the App sends it, letting the oldest read go when there are too many. A read that
        began at an earlier generation than now (pages were let go while it ran) is not kept, and gives None."""
        body = JSONResponse(jsonable_encoder(answer)).body
        with self.lock:
            if generation is not None and generation != self.generation:
                return None
            kept = self.kept[key] = Kept(body, self.clock() + self.seconds)
            self.kept.move_to_end(key)
            while len(self.kept) > self.entries:
                self.kept.popitem(last=False)
        return kept

    def drop(self, where: Callable[[PageKey], bool]) -> None:
        """Let go of each kept page whose key `where` picks, and of every read still running."""
        with self.lock:
            self.generation += 1
            for key in [key for key in self.kept if where(key)]:
                del self.kept[key]

    def clear(self) -> None:
        self.drop(lambda key: True)

    def __len__(self) -> int:
        return len(self.kept)

    def response(self, kept: Kept, longest: float | None = None) -> Response:
        """The page as the browser gets it, told to keep it for the rest of its window, or for `longest` seconds when
        that is shorter (the rest of the day, for a page read as of today)."""
        left = kept.until - self.clock()
        if longest is not None:
            left = min(left, longest)
        return Response(kept.body, media_type="application/json",
                        headers={"Cache-Control": f"private, max-age={max(0, math.ceil(left))}"})
