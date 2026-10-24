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
  indicator by page number, and sends each page as [about the page, records]. For a code it does
  not know, it sends a message and no records, and the fetch stops with a sentence that names the
  code, rather than ending that indicator with no rows.
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


def split(body, records_key: str | None = None) -> tuple[dict, list[dict]]:
    """A page's two parts, for every API: what it says about itself, and its records. The Indicators
    API sends each page as [about the page, records]. The others send one object whose records_key
    holds the records, which the projects API keys by project ID; the rest of the object is what the
    page says about itself. This is the one place that knows the shapes."""
    if isinstance(body, list):
        about = body[0] if body and isinstance(body[0], dict) else {}
        held = (body[1] if len(body) > 1 else None) or []
    else:
        about = {key: value for key, value in body.items() if key != records_key}
        held = body.get(records_key) or [] if records_key else []
    return about, list(held.values()) if isinstance(held, dict) else list(held)


def records(source: Source, body) -> list[dict]:
    """The records a page holds."""
    return split(body, source.records)[1]


def reported_total(source: Source, body) -> int | None:
    """How many records the source says the whole request has."""
    about = split(body, source.records)[0]
    for key in ("count", "total"):
        if str(about.get(key, "")).isdigit():
            return int(about[key])
    return None


def _day(value) -> dt.date | None:
    """A watermark value as a date. A fiscal year alone, such as IEG's evaluation_fy 2020, is the
    last day of that year."""
    written = clean.text(value)
    if written and len(written) == 4 and written.isdigit():
        return clean.fiscal_year_end(int(written))
    return clean.parse_date(value)


def newest_record(source: Source, body) -> dt.date | None:
    """The newest date in the page's watermark field: the page's own, when it gives one, as the
    Indicators API's lastupdated, else its records' newest."""
    about, held = split(body, source.records)
    if source.watermark_field in about:
        return clean.parse_date(about[source.watermark_field])
    days = [_day(record.get(source.watermark_field)) for record in held]
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


def _message(message) -> str:
    """The Indicators API's error message, as one sentence: it sends a list of parts, each with a value."""
    parts = message if isinstance(message, list) else [message]
    said = [str(part.get("value") or part.get("key") or "") if isinstance(part, dict) else str(part) for part in parts]
    return "; ".join(part.strip().rstrip(".") for part in said if part.strip()) or "it gave no reason"


def reads_every_page(source: Source) -> bool:
    """Whether a live fetch asks for every page of the source each time. The search APIs sort
    newest first, so their fetch stops at the watermark and does not ask for older pages again."""
    return source.api != "search"


def _series(source, get, country, code, indicator, watermark, clock) -> Iterator[Page]:
    offset = 0
    while True:
        url = request_url(source, country, offset, indicator)
        body = json.loads(get(url))
        about, held = split(body, source.records)
        if source.api == "indicators" and "message" in about:
            raise OSError(f"The Indicators API did not give {indicator}: {_message(about['message'])}. "
                          f"If the code was retired, take it out of the {source.key} entry in config/sources.toml.")
        if not held:
            break
        yield Page(source.key, url, body, clock(), code)
        offset += len(held)
        total = reported_total(source, body)
        if len(held) < source.page_size or (total is not None and offset >= total):
            break
        if source.max_offset is not None and offset >= source.max_offset:
            break  # the API refuses a page past this offset, so the rest stays out of reach
        if not reads_every_page(source) and watermark is not None:
            oldest = min((day for day in (clean.parse_date(record.get(source.watermark_field))
                                          for record in held) if day), default=None)
            if oldest is not None and oldest < watermark:
                break
