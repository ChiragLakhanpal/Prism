"""Where a source's pages come from: the recorded fixture in the gate, the live API on the workspace.

Both adapters yield the same Page, so everything after the fetch runs the same way on both.

- recorded_pages() reads the files that data/fixture/sources.toml lists under the source's
  fixture_dataset. Each recorded file is one page, fetched on the day it was recorded.
- live_pages() asks the source's endpoint one page at a time until the source has no more. A
  source fetched for every country is one series of pages with no country filter; a source
  fetched for the slice countries is one series for each country. The search APIs return the
  newest records first by the source's watermark field, so it stops at the first page whose
  oldest record is older than the newest record bronze already holds for that series. Each
  country has its own watermark, so a country added to the slice is fetched in full the first
  time. Finances One cannot sort, so every page of a Finances One fetch is asked for, and the
  content hash keeps the ones already held out of bronze. The Indicators API pages each
  indicator by page number, and sends each page as [about the page, records].
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


def _about(body) -> dict:
    """What the page says about itself: the page's own keys, or the first part of an Indicators API page."""
    if isinstance(body, list):
        return body[0] if body and isinstance(body[0], dict) else {}
    return body


def records(source: Source, body) -> list[dict]:
    """The records a page holds. The projects API keys its records by project ID, and the
    Indicators API sends them as the second part of the page."""
    if isinstance(body, list):
        held = body[1] if len(body) > 1 else []
    else:
        held = body.get(source.records)
    held = held or []
    return list(held.values()) if isinstance(held, dict) else list(held)


def reported_total(source: Source, body) -> int | None:
    """How many records the source says the whole request has."""
    about = _about(body)
    for key in ("count", "total"):
        if str(about.get(key, "")).isdigit():
            return int(about[key])
    return None


def newest_record(source: Source, body) -> dt.date | None:
    """The newest date in the page's watermark field. For the Indicators API, the watermark is the
    page's own lastupdated date."""
    if isinstance(body, list):
        return clean.parse_date(_about(body).get(source.watermark_field))
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

def request_url(source: Source, country, offset: int, indicator: str | None = None) -> str:
    """The URL for one page: of one country's records when a country is given, else of every
    country's. For the Indicators API, offset counts records, as for the other APIs, and the
    request asks for the page that starts there."""
    endpoint = source.endpoint.replace("{indicator}", quote(indicator)) if indicator else source.endpoint
    parts = [endpoint]
    if country is not None:
        parts.append(source.country_filter.format(iso2=quote(country.iso2), iso3=quote(country.iso3),
                                                  name=quote(country.name)))
    if source.api == "finances_one":
        parts.append(f"top={source.page_size}&skip={offset}")
    elif source.api == "indicators":
        parts.append(f"page={offset // source.page_size + 1}&per_page={source.page_size}")
    else:
        parts.append(f"rows={source.page_size}&os={offset}&srt={source.watermark_field}&order=desc")
    return "&".join(parts)


def live_pages(source: Source, get: Get, newest_held: Callable[[str | None], dt.date | None] = lambda country: None,
               clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)) -> Iterator[Page]:
    """Each page of each series of the source's records, newest first where the API can sort.
    newest_held gives the newest record date bronze holds for a country's two-letter code, or for
    None, the series with no country filter: its watermark."""
    countries = source.countries or (None,)
    indicators = source.indicators if source.api == "indicators" else (None,)
    for country in countries:
        code = country.iso2 if country is not None else None
        watermark = newest_held(code)
        for indicator in indicators:
            yield from _series(source, get, country, code, indicator, watermark, clock)


def _series(source, get, country, code, indicator, watermark, clock) -> Iterator[Page]:
    offset = 0
    while True:
        url = request_url(source, country, offset, indicator)
        body = json.loads(get(url))
        held = records(source, body)
        if not held:
            break
        yield Page(source.key, url, body, clock(), code)
        offset += len(held)
        total = reported_total(source, body)
        if len(held) < source.page_size or (total is not None and offset >= total):
            break
        if source.api == "search" and watermark is not None:
            oldest = min((day for day in (clean.parse_date(record.get(source.watermark_field))
                                          for record in held) if day), default=None)
            if oldest is not None and oldest < watermark:
                break
