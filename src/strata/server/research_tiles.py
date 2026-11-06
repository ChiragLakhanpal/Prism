"""The Sentinel-2 tiles of a brief's grids, served by Prism (ticket 158).

GET /api/research/tiles/{year}/{zoom}/{row}/{col}.jpg answers one tile of EOX's cloud-free yearly mosaic. The browser
never asks EOX itself: a brief shows up to 72 tiles, and EOX throttles a page that asks for them all at once, so a
printed brief came out with blank grids. Prism answers from three places, in order:

1. the tiles this process already served (a dict in memory);
2. strata.ops.research_cache, where the seed (ops/research/seed_tiles.py) and every earlier miss kept them, under
   source_key "sentinel2_mosaic", the body in base64 (src/strata/research/fetching.py, TableCache);
3. EOX itself, with the named client every research reader uses, paced by the source's pace_seconds. An answer that is
   an image is kept in both caches; anything else answers 502 with the code tile_server, so the page says why.

The address is built from the one endpoint the registry gives (config/research.toml, [sources.sentinel2_mosaic]), and
only for a year the registry lists and its zoom, so the route asks EOX for nothing else. The tiles are public, so the
answer may be kept by the browser for a day; EOX's CC BY-NC-SA credit stays in the grid's caption.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import FastAPI, Path
from fastapi.responses import JSONResponse, Response

from strata.lakehouse.engine import EngineError
from strata.research import fetching

log = logging.getLogger("strata.server.research_tiles")
SOURCE_KEY = "sentinel2_mosaic"  # the registry key of the source, strata-gate: not-a-secret
# A tile never changes once EOX publishes a year's mosaic, so a kept tile is good however old it is.
EVER = dt.datetime(2000, 1, 1, tzinfo=dt.UTC)
JPEG, PNG = b"\xff\xd8", b"\x89PNG"
HEADERS = {"Cache-Control": "public, max-age=86400"}


def is_image(answer: fetching.Answer) -> bool:
    status, headers, body = answer
    kind = str((headers or {}).get("content-type", "")).lower()
    return status == 200 and (kind.startswith("image/") or body[:2] == JPEG or body[:4] == PNG) and len(body) > 0


@dataclass
class Tiles:
    """Where a tile comes from: memory, then the cache table, then EOX. fetch is the named client's (fetching.live())
    or a test's; cache is a fetching.TableCache, or None when the app keeps no table."""

    endpoint: str
    years: tuple[int, ...]
    zoom: int
    pace_seconds: float
    fetch: fetching.Fetch
    cache: object | None = None
    now: Callable[[], dt.datetime] = field(default=lambda: dt.datetime.now(dt.UTC))
    pacer: fetching.Pacer = field(default_factory=fetching.Pacer)
    held: dict[str, bytes] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def from_registry(cls, *, fetch: fetching.Fetch | None = None, cache=None,
                      now: Callable[[], dt.datetime] | None = None) -> Tiles:
        from strata.config import load_research

        source = load_research()[SOURCE_KEY]
        years = tuple(int(year) for year in source.settings.get("years", ()))
        return cls(source.endpoint, years, int(source.settings.get("zoom", 15)), source.pace_seconds,
                   fetch or fetching.live(), cache, **({"now": now} if now else {}))

    def address(self, year: int, zoom: int, row: int, col: int) -> str | None:
        """EOX's address of the tile, or None for a year or zoom the registry does not list, or a tile off the grid."""
        if year not in self.years or zoom != self.zoom or not (0 <= row < 2 ** zoom and 0 <= col < 2 ** zoom):
            return None
        return self.endpoint.format(year=year, zoom=zoom, row=row, col=col)

    def kept(self, url: str) -> bytes | None:
        """The tile from memory or the cache table, without asking EOX."""
        with self.lock:
            found = self.held.get(url)
        if found is not None:
            return found
        if self.cache is None:
            return None
        try:
            answer = self.cache.get(url, EVER)
        except EngineError:
            log.warning("The research cache did not answer for %s.", url, exc_info=True)
            return None
        if answer is None or not is_image(answer):
            return None
        with self.lock:
            self.held[url] = answer[2]
        return answer[2]

    def from_eox(self, url: str) -> fetching.Answer | None:
        """EOX's answer for the tile, asked with the named client and paced, or None when it is not an image."""
        self.pacer.wait(SOURCE_KEY, self.pace_seconds)
        try:
            answer = self.fetch(url)
        except fetching.Unreachable:
            log.warning("The tile server could not be reached for %s.", url)
            return None
        if not is_image(answer):
            log.warning("The tile server answered %s for %s.", answer[0], url)
            return None
        return answer

    def get(self, url: str) -> tuple[str, bytes | None]:
        """("kept", bytes) from memory or the table; ("fetched", bytes) from EOX, now kept in both; ("refused", None)
        when EOX answered something that is not an image or could not be reached."""
        found = self.kept(url)
        if found is not None:
            return "kept", found
        answer = self.from_eox(url)
        if answer is None:
            return "refused", None
        with self.lock:
            self.held[url] = answer[2]
        if self.cache is not None:
            try:
                self.cache.put(SOURCE_KEY, url, answer, self.now())
            except EngineError:
                log.warning("The research cache did not keep %s.", url, exc_info=True)
        return "fetched", answer[2]


def add_routes(app: FastAPI, *, tiles: Tiles | Callable[[], Tiles]) -> None:
    """tiles is the Tiles the route answers from, or a function that makes it on the first request."""
    made: dict[str, Tiles] = {}

    def current() -> Tiles:
        if isinstance(tiles, Tiles):
            return tiles
        if "tiles" not in made:
            made["tiles"] = tiles()
        return made["tiles"]

    @app.get("/api/research/tiles/{year}/{zoom}/{row}/{col}.jpg")
    def tile(year: int = Path(ge=1900, le=2999), zoom: int = Path(ge=0, le=24), row: int = Path(ge=0),
             col: int = Path(ge=0)):
        source = current()
        url = source.address(year, zoom, row, col)
        if url is None:
            return JSONResponse({"code": "unknown_tile"}, status_code=404, headers={"Cache-Control": "no-store"})
        status, body = source.get(url)
        if body is None:
            return JSONResponse({"code": "tile_server"}, status_code=502, headers={"Cache-Control": "no-store"})
        return Response(body, media_type="image/jpeg", headers=HEADERS)
