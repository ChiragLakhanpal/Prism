"""Bronze: every page a source returned, kept once, with its fetch time and source.

store() is the fetch task's last step. It first takes the contact details out of the page and
counts them (strata.lakehouse.contacts), so bronze keeps each page as received except for those. It hashes each page with the source's ignore_keys left out
(Finances One stamps every row with today's as_of_date), and adds only pages whose hash bronze does
not hold yet, so a second fetch with no source changes adds no rows.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Iterable

from strata.config import Source
from strata.lakehouse import contacts
from strata.lakehouse import pages as source_pages
from strata.lakehouse.engine import Engine

TABLE = "strata.bronze.api_pages"
COLUMNS = ("source", "request", "page_hash", "body", "records", "reported_total", "newest_record_on",
           "contact_details_removed", "fetched_at", "public_from")
HELD = "SELECT page_hash FROM strata.bronze.api_pages WHERE source = :source"
NEWEST = "SELECT max(newest_record_on) AS newest FROM strata.bronze.api_pages WHERE source = :source"


def content_hash(source: Source, body: dict) -> str:
    """The page's hash, leaving out the keys that change on every fetch without the record changing."""
    def without(value):
        if isinstance(value, dict):
            return {key: without(item) for key, item in value.items() if key not in source.ignore_keys}
        if isinstance(value, list):
            return [without(item) for item in value]
        return value

    canonical = json.dumps(without(body), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def newest_held(engine: Engine, source: Source) -> dt.date | None:
    """The newest record date bronze holds for a source: the live fetch's watermark."""
    rows = engine.run(NEWEST, {"source": source.key}).rows
    return rows[0][0] if rows and rows[0][0] else None


def store(engine: Engine, source: Source, pages: Iterable[source_pages.Page]) -> int:
    """Add the pages bronze does not hold yet. Returns how many it added."""
    held = {row[0] for row in engine.run(HELD, {"source": source.key}).rows}
    rows = []
    for page in pages:
        body, removed = contacts.strip(page.body)  # before anything is kept (CLAUDE.md rule 8)
        page_hash = content_hash(source, body)
        if page_hash in held:
            continue
        held.add(page_hash)
        rows.append((source.key, page.request, page_hash, json.dumps(body, ensure_ascii=False),
                     len(source_pages.records(source, body)), source_pages.reported_total(source, body),
                     source_pages.newest_record(source, body), removed, page.fetched_at,
                     page.fetched_at.astimezone(dt.UTC).date()))
    return engine.insert_rows(TABLE, COLUMNS, rows)
