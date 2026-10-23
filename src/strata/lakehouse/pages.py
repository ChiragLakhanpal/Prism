"""Where a source's pages come from: the recorded fixture in the gate, the live API on the workspace.

Both adapters yield the same Page, so everything after the fetch runs the same way on both.

- recorded_pages() reads the files that data/fixture/sources.toml lists under the source's
  fixture_dataset. Each recorded file is one page, fetched on the day it was recorded.
- live_pages() asks the source's endpoint for each country in the registry, one page at a time,
  until the source has no more. The search APIs return the newest records first by the source's
  watermark field, so it stops at the first page whose oldest record is older than the newest
  record bronze already holds for that country. Each country has its own watermark, so a country
  added to the registry is fetched in full the first time. Finances One cannot sort, so every page of an awards fetch is asked
  for, and the content hash keeps the ones already held out of bronze.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from urllib.parse import quote

from strata.config import Source
from strata.lakehouse import clean

Get = Callable[[str], bytes]


@dataclass(frozen=True)
class Page:
    """One page as a source returned it."""

    source: str
    request: str
    body: dict
    fetched_at: dt.datetime
    country_code: str | None = None  # the country the request asked for; a recorded page names none


def records(source: Source, body: dict) -> list[dict]:
    """The records a page holds. The projects API keys its records by project ID."""
    held = body.get(source.records) or []
    return list(held.values()) if isinstance(held, dict) else list(held)


def reported_total(source: Source, body: dict) -> int | None:
    """How many records the source says the whole request has."""
    for key in ("count", "total"):
        if str(body.get(key, "")).isdigit():
            return int(body[key])
    return None


def newest_record(source: Source, body: dict) -> dt.date | None:
    """The newest date in the page's watermark field."""
    days = [clean.parse_date(record.get(source.watermark_field)) for record in records(source, body)]
    return max((day for day in days if day), default=None)


# ── The recorded fixture ─────────────────────────────────────────────────

def recorded_pages(source: Source, manifest=None) -> Iterator[Page]:
    """Every recorded file of the source's fixture dataset, as the page it recorded."""
    from strata.fixture import recorded as fmt

    manifest = manifest or fmt.load_manifest()
    for entry in manifest.sources:
        if entry.dataset != source.fixture_dataset or entry.kind != "json":
            continue
        file = fmt.read(manifest.recorded / entry.file)
        fetched = dt.datetime.combine(dt.date.fromisoformat(file.recorded), dt.time(), dt.UTC)
        yield Page(source.key, file.source, file.body, fetched)


# ── The live API ─────────────────────────────────────────────────────────

def request_url(source: Source, country, offset: int) -> str:
    """The URL for one page of one country's records."""
    scope = source.country_filter.format(iso2=quote(country.iso2), name=quote(country.name))
    if source.api == "finances_one":
        paging = f"top={source.page_size}&skip={offset}"
    else:
        paging = f"rows={source.page_size}&os={offset}&srt={source.watermark_field}&order=desc"
    return f"{source.endpoint}&{scope}&{paging}"


def live_pages(source: Source, get: Get, newest_held: Callable[[str], dt.date | None] = lambda country: None,
               clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)) -> Iterator[Page]:
    """Each page of each country's records, newest first where the API can sort. newest_held gives
    the newest record date bronze holds for a country's two-letter code: its watermark."""
    for country in source.countries:
        watermark = newest_held(country.iso2)
        offset = 0
        while True:
            url = request_url(source, country, offset)
            body = json.loads(get(url))
            held = records(source, body)
            if not held:
                break
            yield Page(source.key, url, body, clock(), country.iso2)
            offset += len(held)
            total = reported_total(source, body)
            if len(held) < source.page_size or (total is not None and offset >= total):
                break
            if source.api == "search" and watermark is not None:
                oldest = min((day for day in (clean.parse_date(record.get(source.watermark_field))
                                              for record in held) if day), default=None)
                if oldest is not None and oldest < watermark:
                    break
