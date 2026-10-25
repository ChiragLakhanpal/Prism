"""Where documents come from: a project's list in the documents API, each document's published text,
and the text of each page of its PDF.

- RecordedDocuments, offline: the fixture's recorded files (data/fixture/sources.toml), found by the
  address they were fetched from, with the day they were recorded as the time they were fetched.
- LiveDocuments, live: the World Bank's hosts, with each PDF page's text read from its text layer
  with pypdf (the recording command reads pages the same way).

A document the source cannot give, such as one the fixture never recorded, raises NotFetched.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import logging
from dataclasses import dataclass
from typing import Protocol

from strata.reader.layout import https

log = logging.getLogger("strata.reader")

LIST_FIELDS = "id,docty,docdt,disclosure_date,display_title,repnb,lang,txturl,pdfurl,guid"


class NotFetched(LookupError):
    """A document or list the source could not give."""


@dataclass(frozen=True)
class Fetched:
    url: str
    body: object  # the parsed JSON of a list, a document's text, or the text of each PDF page
    fetched_at: dt.datetime


class Documents(Protocol):
    def listing(self, url: str) -> Fetched:
        """A documents API response, as parsed JSON."""

    def text(self, url: str) -> Fetched:
        """A document's published text."""

    def pages(self, url: str) -> Fetched:
        """The text of each page of a document's PDF, page 1 first."""


def list_url(endpoint: str, project_id: str, offset: int = 0, rows: int = 500) -> str:
    """The documents API address that lists a project's documents, newest first."""
    return (f"{endpoint}?format=json&proid={project_id}&rows={rows}&os={offset}&fl={LIST_FIELDS}"
            "&srt=docdt&order=desc")


# ── Offline ──────────────────────────────────────────────────────────────

class RecordedDocuments:
    """The fixture's recorded lists, texts and pages, by the address each was fetched from."""

    def __init__(self, manifest):
        from strata.fixture import recorded as fmt

        self._fmt, self._recorded = fmt, manifest.recorded
        self._lists, self._texts, self._pages = {}, {}, {}
        for source in manifest.sources:
            if source.kind == "json":
                self._lists[https(source.url)] = source.file
            else:
                self._texts[https(source.text_url)] = f"{source.file}.txt"
                self._pages[https(source.pdf_url)] = f"{source.file}.pages.txt"

    def _read(self, files: dict, url: str):
        name = files.get(https(url))
        if name is None:
            raise NotFetched(f"The fixture has no recording of {url}.")
        return self._fmt.read(self._recorded / name)

    @staticmethod
    def _when(recorded: str) -> dt.datetime:
        return dt.datetime.combine(dt.date.fromisoformat(recorded), dt.time(), dt.UTC)

    def listing(self, url: str) -> Fetched:
        file = self._read(self._lists, url)
        return Fetched(url, file.body, self._when(file.recorded))

    def text(self, url: str) -> Fetched:
        file = self._read(self._texts, url)
        return Fetched(url, file.body, self._when(file.recorded))

    def pages(self, url: str) -> Fetched:
        file = self._read(self._pages, url)
        return Fetched(url, file.body.split(self._fmt.PAGE_BREAK), self._when(file.recorded))


# ── Live ─────────────────────────────────────────────────────────────────

class HostRefused(Exception):
    """A World Bank host refused a request outright (HTTP 403, or 429 after fetch_url's retries). On October 25,
    2026 documents.worldbank.org answered 403 to every request from one computer after some hundreds of PDFs, so
    a reader stops at the first refusal instead of asking for every other document, and the next run goes on
    from where it stopped. It is not a NotFetched: a reader skips a document it could not fetch, but never this."""

    def __init__(self, url: str, status: int):
        super().__init__(f"{url} answered HTTP {status}, so I stopped asking the host.")
        self.url, self.status = url, status


REFUSED = (403, 429)


class PoliteFetch:
    """fetch(url) for the World Bank's document host, as the nightly job asks it (ticket 43).

    It waits pause seconds after the previous request before the next (config/sources.toml, the documents
    source's pause_seconds), keeps each answer in the cache folder, by its address's hash, so a document
    is fetched once and never again (on the workspace, the bronze files volume, which serverless compute
    reads as a folder), and raises HostRefused when the host answers 403 or 429."""

    def __init__(self, fetch, pause: float, cache=None, sleep=None, clock=None):
        import time
        from pathlib import Path

        self.fetch, self.pause = fetch, pause
        self.cache = Path(cache) if cache else None
        self.sleep, self.clock = sleep or time.sleep, clock or time.monotonic
        self.last: float | None = None
        self.asked = 0  # requests that reached the host, for the tests and the run's report

    def _cached(self, url: str):
        import hashlib

        return self.cache / hashlib.sha256(url.encode("utf-8")).hexdigest() if self.cache else None

    def __call__(self, url: str) -> bytes:
        import urllib.error

        kept = self._cached(url)
        if kept is not None and kept.is_file():
            return kept.read_bytes()
        if self.last is not None:
            waited = self.clock() - self.last
            if waited < self.pause:
                self.sleep(self.pause - waited)
        self.asked += 1
        try:
            body = self.fetch(url)
        except urllib.error.HTTPError as error:
            if error.code in REFUSED:
                raise HostRefused(url, error.code) from error
            raise
        finally:
            self.last = self.clock()
        if kept is not None:
            kept.parent.mkdir(parents=True, exist_ok=True)
            kept.write_bytes(body)
        return body


class LiveDocuments:
    """The World Bank's hosts. Reading a PDF's pages needs pypdf, which the recording command uses too."""

    def __init__(self, fetch=None, clock=None):
        from strata.fixture.record import fetch_url

        self.fetch = fetch or fetch_url
        self.clock = clock or (lambda: dt.datetime.now(dt.UTC))

    def _get(self, url: str) -> bytes:
        try:
            return self.fetch(https(url))
        except HostRefused:
            raise  # the host refused: the run stops, rather than skipping this document and asking for the next
        except Exception as error:  # noqa: BLE001 - any failure means the source did not give it
            raise NotFetched(f"I could not fetch {url}: {error}") from error

    def listing(self, url: str) -> Fetched:
        return Fetched(url, json.loads(self._get(url)), self.clock())

    def text(self, url: str) -> Fetched:
        return Fetched(url, self._get(url).decode("utf-8", errors="replace").removeprefix("﻿"), self.clock())

    def pages(self, url: str) -> Fetched:
        """Each page's text from the PDF's text layer. A PDF pypdf cannot open raises NotFetched, like a PDF
        the host did not give. A page whose text pypdf cannot decode, as when a font's encoding is broken,
        reads as empty, like a scanned page, so the page router sends it to Route B instead of the run
        stopping on it."""
        from pypdf import PdfReader

        pdf = self._get(url)
        try:
            pages = list(PdfReader(io.BytesIO(pdf)).pages)
        except Exception as error:  # noqa: BLE001 - pypdf raises its own errors and Python's for a broken file
            raise NotFetched(f"I could not read the PDF at {url}: {error}") from error
        texts = []
        for number, page in enumerate(pages, 1):
            try:
                texts.append(page.extract_text() or "")
            except Exception as error:  # noqa: BLE001 - a broken font raises UnicodeDecodeError, among others
                log.info("Page %s of %s has text pypdf cannot decode (%s); it reads as empty.", number, url, error)
                texts.append("")
        return Fetched(url, texts, self.clock())
