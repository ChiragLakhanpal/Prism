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
from dataclasses import dataclass
from typing import Protocol

from strata.reader.layout import https

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

class LiveDocuments:
    """The World Bank's hosts. Reading a PDF's pages needs pypdf, which the recording command uses too."""

    def __init__(self, fetch=None, clock=None):
        from strata.fixture.record import fetch_url

        self.fetch = fetch or fetch_url
        self.clock = clock or (lambda: dt.datetime.now(dt.UTC))

    def _get(self, url: str) -> bytes:
        try:
            return self.fetch(https(url))
        except Exception as error:  # noqa: BLE001 - any failure means the source did not give it
            raise NotFetched(f"I could not fetch {url}: {error}") from error

    def listing(self, url: str) -> Fetched:
        return Fetched(url, json.loads(self._get(url)), self.clock())

    def text(self, url: str) -> Fetched:
        return Fetched(url, self._get(url).decode("utf-8", errors="replace").removeprefix("﻿"), self.clock())

    def pages(self, url: str) -> Fetched:
        from pypdf import PdfReader

        pdf = self._get(url)
        return Fetched(url, [page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages], self.clock())
