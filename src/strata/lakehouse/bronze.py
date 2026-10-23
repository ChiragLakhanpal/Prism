"""Bronze: every page a source returned, kept once, with its fetch time and source.

store() is the fetch task's last step. It first takes the contact details out of the page and
counts them (strata.lakehouse.contacts), so bronze keeps each page as received except for those.
It hashes each page with the source's ignore_keys left out (Finances One stamps every row with
today's as_of_date) and its records in a fixed order (Finances One cannot sort, so the same
records may come back in another order), and adds only pages whose hash bronze does not hold
yet, so a second fetch with no source changes adds no rows.
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
COLUMNS = ("source", "country_code", "request", "page_hash", "body", "records", "reported_total",
           "newest_record_on", "contact_details_removed", "fetched_at", "public_from")
HELD = "SELECT page_hash FROM strata.bronze.api_pages WHERE source = :source"
# The pages of a source that a fetch task that finished holds: how many, and the newest record date
# among them, for one series (a country's, or with '', the one with no country filter) or, with
# every_series, for all of them. The watermark and the frozen check both read it. A fetch that
# failed partway kept the pages it reached, and the records it never reached are older than those,
# or, for a frozen source, never fetched at all, so its pages do not count.
FINISHED = """
SELECT count(*) AS pages, max(p.newest_record_on) AS newest
FROM strata.bronze.api_pages AS p
WHERE p.source = :source
  AND (:every_series OR coalesce(p.country_code, '') = :country)
  AND p.fetched_at <= (
    SELECT max(r.finished_at)
    FROM strata.ops.pipeline_runs AS r
    WHERE r.task_key = 'fetch_by_watermark' AND r.status = 'succeeded'
  )
"""


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_hash(source: Source, body) -> str:
    """The page's hash, leaving out the keys that change on every fetch without the record changing.
    The page's records are hashed in a fixed order, each by its own content, so their order on the
    page does not change the hash."""
    def without(value):
        if isinstance(value, dict):
            return {key: without(item) for key, item in value.items() if key not in source.ignore_keys}
        if isinstance(value, list):
            return [without(item) for item in value]
        return value

    about, held = source_pages.split(without(body), source.records)
    kept = {"about": about, "records": sorted(held, key=_canonical)}
    return hashlib.sha256(_canonical(kept).encode("utf-8")).hexdigest()


def newest_held(engine: Engine, source: Source, country_code: str | None) -> dt.date | None:
    """The newest record date bronze holds for one series of a source, the live fetch's watermark:
    one country's, or with None, the series fetched for every country. Only pages of a fetch task
    that finished count, so a fetch cut short is made good by the next one."""
    rows = engine.run(FINISHED, {"source": source.key, "every_series": False, "country": country_code or ""}).rows
    return rows[0][1] if rows and rows[0][1] else None


def holds_a_finished_fetch(engine: Engine, source: Source) -> bool:
    """Whether bronze holds pages of the source from a fetch task that finished. Pages kept by a
    fetch that failed partway do not count, so the next run asks for the source again."""
    rows = engine.run(FINISHED, {"source": source.key, "every_series": True, "country": ""}).rows
    return int(rows[0][0]) > 0


def store(engine: Engine, source: Source, pages: Iterable[source_pages.Page]) -> int:
    """Add the pages bronze does not hold yet, each as it comes, so a fetch that fails partway keeps
    the pages it fetched and never holds a whole source in memory. Returns how many it added."""
    held = {row[0] for row in engine.run(HELD, {"source": source.key}).rows}
    added = 0
    for page in pages:
        body, removed = contacts.strip(page.body)  # before anything is kept (CLAUDE.md rule 8)
        page_hash = content_hash(source, body)
        if page_hash in held:
            continue
        held.add(page_hash)
        added += engine.insert_rows(TABLE, COLUMNS, [(
            source.key, page.country_code, page.request, page_hash, json.dumps(body, ensure_ascii=False),
            len(source_pages.records(source, body)), source_pages.reported_total(source, body),
            source_pages.newest_record(source, body), removed, page.fetched_at,
            page.fetched_at.astimezone(dt.UTC).date())])
    return added
