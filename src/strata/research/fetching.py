"""How deep research reaches a source (ticket 147): one Fetch, with pacing and a cache around it.

A Fetch is one function, fetch(url, *, headers=None) -> (status, headers, body). Two make the answers:

- live() asks with urllib, always with Prism's named agent (config/research.toml, [client]) and its timeout, never a
  browser's. A refusal (403, 429) comes back as an answer, so the reader can say so; a host it cannot reach raises
  Unreachable. It never tries a call again.
- offline() replays the answers ops/research/record.py recorded under data/fixture/recorded/research/<source>/, one
  file per address, and refuses an address it has no file for (NotRecorded). Every test reads through it.

Around a source's fetch, paced() keeps one call per source per pace_seconds, waiting on an injected clock, and cached()
answers an address again within the source's cache_hours from a Cache: TableCache keeps the answers in
strata.ops.research_cache through an engine (the app's own on the workspace, or the local DuckDB file the drafts use),
MemoryCache in the process. Only an answer of 200 is kept, so a refusal is never reused as the source's answer.

refusal() tells a refusal by its status or by a bot check page (the registry's bot_check_markers).
"""

from __future__ import annotations

import base64
import datetime as dt
import gzip
import hashlib
import json
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from strata.config import load_research_client

Answer = tuple[int, dict, bytes]
Fetch = Callable[..., Answer]
# The answer's headers a recording and the cache keep.
KEPT_HEADERS = ("content-type", "retry-after", "location", "last-modified")
# A recorded body larger than this is kept gzipped, in base64, so the fixture stays small.
TEXT_LIMIT = 60_000


class Unreachable(Exception):
    """A host Prism could not reach: no answer at all, so no status."""

    def __init__(self, url: str, reason: str):
        super().__init__(f"I could not reach {url}: {reason}")
        self.url, self.reason = url, reason


class NotRecorded(Unreachable):
    """The offline fetch has no recording of the address."""

    def __init__(self, url: str):
        Exception.__init__(self, f"Prism has no recording of {url}.")
        self.url, self.reason = url, "no recording"


class Refused(Exception):
    """A source refused the call that decides its result: 403, 429, a bot check page, or another status."""

    def __init__(self, status: str, note: str):
        super().__init__(note)
        self.status, self.note = status, note


def _kept(headers) -> dict:
    found = {str(name).lower(): str(value) for name, value in (headers.items() if headers else [])}
    return {name: found[name] for name in KEPT_HEADERS if name in found}


def live(client=None, opener=urllib.request.urlopen) -> Fetch:
    """The live fetch: urllib with the named agent and the registry's timeout. opener stands in for urlopen in tests."""
    client = client or load_research_client()
    context = ssl.create_default_context()

    def fetch(url: str, *, headers: dict | None = None) -> Answer:
        request = urllib.request.Request(url, headers={**(headers or {}), "User-Agent": client.user_agent})
        try:
            if opener is urllib.request.urlopen:
                response = opener(request, timeout=client.timeout_seconds, context=context)
            else:
                response = opener(request, timeout=client.timeout_seconds)
            with response:
                return response.status, _kept(response.headers), response.read()
        except urllib.error.HTTPError as refused:
            return refused.code, _kept(refused.headers), refused.read() or b""
        except urllib.error.URLError as unreachable:
            raise Unreachable(url, str(unreachable.reason)) from unreachable
        except (TimeoutError, OSError) as unreachable:
            raise Unreachable(url, str(unreachable) or type(unreachable).__name__) from unreachable

    return fetch


# ── The recordings ──────────────────────────────────────────────────────

def recording_name(url: str) -> str:
    """The file an address is recorded in, inside its source's folder."""
    return hashlib.sha256(url.encode()).hexdigest()[:16] + ".json"


def recording(url: str, answer: Answer, *, source: str, license: str, recorded: dt.date, read_with: str,
              note: str | None = None, keep_body: bool = True) -> dict:
    """One recorded answer: the address, the status, the date and the agent it was read with, and the body as text,
    or gzipped in base64 when it is large or not text. keep_body false keeps no body, for an image."""
    status, headers, body = answer
    entry = {"url": url, "source": source, "license": license, "recorded": recorded.isoformat(),
             "read_with": read_with, "status": status, "headers": _kept(headers)}
    if note:
        entry["note"] = note
    if not keep_body:
        entry["body_omitted"] = f"{len(body)} bytes of {headers.get('content-type', 'binary data')}, not kept"
        return entry
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is not None and len(body) <= TEXT_LIMIT:
        entry["body"] = text
    else:
        entry["body_gzip_base64"] = base64.b64encode(gzip.compress(body, mtime=0)).decode()
    return entry


def recorded_answer(entry: dict) -> Answer:
    if "body" in entry:
        body = entry["body"].encode("utf-8")
    elif "body_gzip_base64" in entry:
        body = gzip.decompress(base64.b64decode(entry["body_gzip_base64"]))
    else:
        body = b""
    return int(entry["status"]), dict(entry.get("headers") or {}), body


def offline(root: Path, source: str | None = None) -> Fetch:
    """The offline fetch: the answers recorded under root (each source's folder, or only source's), by address."""
    folders = [root / source] if source else [path for path in sorted(Path(root).iterdir()) if path.is_dir()]
    files = {path.name: path for folder in folders if folder.is_dir() for path in folder.glob("*.json")}

    def fetch(url: str, *, headers: dict | None = None) -> Answer:
        path = files.get(recording_name(url))
        if path is None:
            raise NotRecorded(url)
        entry = json.loads(path.read_text())
        if entry["url"] != url:
            raise NotRecorded(url)
        if "unreachable" in entry:  # the host could not be reached when it was recorded
            raise Unreachable(url, entry["unreachable"])
        return recorded_answer(entry)

    return fetch


# ── Refusals ────────────────────────────────────────────────────────────

def refusal(answer: Answer, markers: tuple[str, ...] | None = None) -> str | None:
    """"429" or "403" when the source refused by its status, "bot check" when it answered a bot check page, else None."""
    status, _, body = answer
    head = body[:20_000].decode("utf-8", errors="replace")
    if any(marker in head for marker in (markers or load_research_client().bot_check_markers)):
        return "bot check"
    if status in (403, 429):
        return str(status)
    return None


def refusal_note(label: str, status: str) -> str:
    """One sentence on why a source gave no item."""
    if status == "429":
        return f"{label} limited calls from this network."
    if status == "403":
        return f"{label} answered 403 to Prism's named client, so Prism kept no item from it."
    if status == "bot check":
        return f"{label} answered with a bot check page, so Prism kept no item from it."
    return f"{label} answered {status}, so Prism kept no item from it."


def body_of(fetch: Fetch, url: str, label: str, headers: dict | None = None) -> bytes:
    """The body of a call that decides a source's result; a refusal or any status but 200 raises Refused."""
    answer = fetch(url, headers=headers)
    refused = refusal(answer)
    if refused is None and answer[0] != 200:
        refused = str(answer[0])
    if refused is not None:
        raise Refused(refused, refusal_note(label, refused))
    return answer[2]


# ── Pacing ──────────────────────────────────────────────────────────────

class Pacer:
    """One call per source per its pace: a call waits until pace_seconds have passed since the source's last call.
    Each source waits on its own, so a slow source never holds up another."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        self.clock, self.sleep = clock, sleep
        self.last: dict[str, float] = {}
        self.locks: dict[str, threading.Lock] = {}
        self.guard = threading.Lock()

    def wait(self, key: str, pace_seconds: float) -> None:
        with self.guard:
            lock = self.locks.setdefault(key, threading.Lock())
        with lock:
            last = self.last.get(key)
            if last is not None and pace_seconds > 0:
                waited = self.clock() - last
                if waited < pace_seconds:
                    self.sleep(pace_seconds - waited)
            self.last[key] = self.clock()


def paced(fetch: Fetch, key: str, pace_seconds: float, pacer: Pacer) -> Fetch:
    def call(url: str, *, headers: dict | None = None) -> Answer:
        pacer.wait(key, pace_seconds)
        return fetch(url, headers=headers)

    return call


# ── The cache ───────────────────────────────────────────────────────────

class MemoryCache:
    """Answers kept in this process, by address."""

    def __init__(self):
        self.held: dict[str, tuple[dt.datetime, Answer]] = {}

    def get(self, url: str, since: dt.datetime) -> Answer | None:
        found = self.held.get(url)
        return found[1] if found and found[0] >= since else None

    def put(self, source_key: str, url: str, answer: Answer, at: dt.datetime) -> None:
        self.held[url] = (at, answer)


class TableCache:
    """Answers kept in strata.ops.research_cache, through the engine engine() opens."""

    READ = ("SELECT status, headers, body FROM strata.ops.research_cache "
            "WHERE url = :url AND fetched_at >= :since ORDER BY fetched_at DESC LIMIT 1")
    COLUMNS = ("url", "source_key", "status", "headers", "body", "fetched_at", "public_from")

    def __init__(self, engine: Callable):
        self.engine = engine

    def get(self, url: str, since: dt.datetime) -> Answer | None:
        with opened(self.engine) as engine:
            result = engine.run(self.READ, {"url": url, "since": since.astimezone(dt.UTC).replace(tzinfo=None)})
        if not result.rows:
            return None
        status, headers, body = result.rows[0]
        return int(status), json.loads(headers), base64.b64decode(body)

    def put(self, source_key: str, url: str, answer: Answer, at: dt.datetime) -> None:
        status, headers, body = answer
        at = at.astimezone(dt.UTC)
        with opened(self.engine) as engine:
            engine.insert_rows("strata.ops.research_cache", self.COLUMNS, [(
                url, source_key, status, json.dumps(_kept(headers)), base64.b64encode(body).decode(),
                at.replace(tzinfo=None), at.date())])


@contextmanager
def opened(engine_factory: Callable) -> Iterator:
    """The engine engine_factory() opens, closed after use, as the uploads store opens its engine."""
    engine = engine_factory()
    try:
        yield engine
    finally:
        close = getattr(engine, "close", None)
        if callable(close):
            close()


def cached(fetch: Fetch, key: str, cache_hours: float, cache, now: Callable[[], dt.datetime]) -> Fetch:
    """The fetch, with each answer of 200 reused for cache_hours. A source with no cache_hours is asked every time."""
    if cache_hours <= 0 or cache is None:
        return fetch

    def call(url: str, *, headers: dict | None = None) -> Answer:
        at = now()
        held = cache.get(url, at - dt.timedelta(hours=cache_hours))
        if held is not None:
            return held
        answer = fetch(url, headers=headers)
        if answer[0] == 200 and refusal(answer) is None:
            cache.put(key, url, answer, at)
        return answer

    return call


def for_source(source, fetch: Fetch, *, pacer: Pacer, cache=None,
               now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)) -> Fetch:
    """A source's fetch: its answers reused for its cache_hours, and its calls paced by its pace_seconds."""
    return cached(paced(fetch, source.key, source.pace_seconds, pacer), source.key, source.cache_hours, cache, now)
