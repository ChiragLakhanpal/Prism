"""The data readiness measures the nightly job writes to strata.ops.data_readiness (spec, "Data
readiness and the dashboard"): coverage (rows and years), linked (to STEP references, notices,
projects and countries), fresh (as of, with the cadence) and the contact details removed, per
source and country. Each is a count with its denominator, or a date. There is no composite score.

Three measures are the same for every source the nightly job fetches page by page, so they are
defined once, here, for the source as a whole (subject all):

- coverage_rows        the source's records held, counted once in each request they came back
                       in, of the totals the source reported for those requests at its last fetch.
                       Bronze keeps every page it was sent. For a source the job fetches in full
                       each night, only the newest page of each request counts
                       (strata.bronze.current_pages), so a record the source dropped since is not
                       counted. For a search source, every page bronze holds counts, because a
                       later fetch asks again only for the newest pages, and the older records stay
                       on pages it does not ask for (strata.lakehouse.pages.reads_every_page). When
                       the two are equal, the fetch holds every record the API reported.
- fresh_fetched        the day of the last fetch, with the source's cadence
- fresh_newest_record  the newest date in the source's watermark field, with its cadence

The rest are defined once per silver transform, in <transform>.sql in this folder: a query that
returns source, subject (all, or a country's two-letter code), measure, kind, count, denominator,
as_of and detail, with the source's key bound as :source. Two sources that share a transform, such
as the IDA credits and the IBRD loans, share its file. measure() runs both for every source in the
registry that the job fetches, and adds the rows under the run's id. The plan reader writes the
documents source's measures itself (strata.lakehouse.plans).
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from importlib import resources

from strata.config import Source, load_sources
from strata.lakehouse import pages as source_pages
from strata.lakehouse import silver
from strata.lakehouse.engine import Engine

COLUMNS = "run_id, source, subject, measure, kind, count, denominator, as_of, detail, measured_at, public_from"

# A request without its paging, so the pages of one request count together.
QUERY = "regexp_replace(request, '[?&](per_page|page|top|skip|rows|os)=[0-9]+', '')"

COVERAGE_ROWS_DETAIL = ("This counts the records held, once in each request they came back in, out of the totals "
                        "the source reported for those requests.")


def _counted(source: Source) -> tuple[str, str, str]:
    """What coverage_rows counts for a paged source: its silver transform's first table, the columns
    that tell one record from another, and the bronze pages whose records count."""
    module = silver.transform(source)
    table = next(iter(module.TABLES))
    key = ", ".join(f"coalesce(CAST(s.{column} AS STRING), '')" for column in module.RECORD_KEY)
    counted = ("strata.bronze.current_pages" if source_pages.reads_every_page(source)  # sql-lint: names only
               else "strata.bronze.api_pages")
    return table, key, counted


def coverage_rows_by_year(source: Source) -> str | None:
    """coverage_rows for the source as a whole, split by fiscal year: the same records, each counted
    once in each request it came back in, so a source's years add up to its measure (the dashboard's
    Data readiness page, ticket 16). A record with no fiscal year has a row with none. Returns a query
    of fiscal_year and records, with the source's key bound as :source, or None when the source's
    silver transform names no FISCAL_YEAR."""
    year = getattr(silver.transform(source), "FISCAL_YEAR", None)
    if year is None:
        return None
    table, key, counted = _counted(source)
    return f"""
WITH counted_pages AS (
  SELECT page_hash, {QUERY} AS query
  FROM {counted}
  WHERE source = :source
)
SELECT s.{year} AS fiscal_year, count(DISTINCT concat_ws('|', p.query, {key})) AS records
FROM {table} AS s
JOIN counted_pages AS p ON p.page_hash = s.page_hash
GROUP BY s.{year}
"""  # sql-lint: names only, the table and columns come from the source's silver transform


def _source_query(source: Source) -> str:
    """The three measures every paged source has, for the source as a whole."""
    table, key, counted = _counted(source)
    return f"""
WITH pages AS (
  SELECT page_hash, {QUERY} AS query, reported_total, fetched_at, newest_record_on
  FROM strata.bronze.api_pages
  WHERE source = :source
),
counted_pages AS (
  SELECT page_hash, {QUERY} AS query
  FROM {counted}
  WHERE source = :source
),
reported AS (
  SELECT sum(total) AS total
  FROM (SELECT query, max_by(reported_total, fetched_at) AS total FROM pages GROUP BY query) AS per_query
),
held AS (
  SELECT sum(records) AS records
  FROM (
    SELECT p.query, count(DISTINCT concat_ws('|', {key})) AS records
    FROM {table} AS s
    JOIN counted_pages AS p ON p.page_hash = s.page_hash
    GROUP BY p.query
  ) AS per_query
),
fresh AS (
  SELECT CAST(max(fetched_at) AS DATE) AS fetched_on, max(newest_record_on) AS newest
  FROM pages
)
SELECT :source AS source, 'all' AS subject, 'coverage_rows' AS measure, 'coverage' AS kind,
  CAST(coalesce(h.records, 0) AS BIGINT) AS count, CAST(r.total AS BIGINT) AS denominator,
  CAST(NULL AS DATE) AS as_of, :coverage_rows_detail AS detail
FROM reported AS r
CROSS JOIN held AS h
WHERE r.total IS NOT NULL
UNION ALL
SELECT :source, 'all', 'fresh_fetched', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), fetched_on, :cadence
FROM fresh
WHERE fetched_on IS NOT NULL
UNION ALL
SELECT :source, 'all', 'fresh_newest_record', 'fresh', CAST(NULL AS BIGINT), CAST(NULL AS BIGINT), newest, :cadence
FROM fresh
WHERE newest IS NOT NULL
"""  # sql-lint: names only, the tables and key columns come from the source and its silver transform


def _transform_query(source: Source) -> str | None:
    # importlib.resources rather than __file__, which serverless Python tasks do not set.
    path = resources.files("strata.lakehouse.readiness") / f"{source.silver_transform}.sql"
    if not path.is_file():
        return None
    return "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("--"))


PARAMETER = re.compile(r"(?<![:\w]):([a-z_]+)\b")


def _bound(sql: str, params: dict) -> dict:
    """The parameters a statement names, as an engine binds exactly those."""
    return {name: params[name] for name in set(PARAMETER.findall(sql)) if name in params}


def _write(engine: Engine, query: str, params: dict) -> int:
    count = f"SELECT 1 AS one FROM ({query}) AS m"  # sql-lint: names only
    written = len(engine.run(count, _bound(count, params)).rows)
    insert = (f"INSERT INTO strata.ops.data_readiness ({COLUMNS}) "  # sql-lint: names only
              f"SELECT :run_id, m.source, m.subject, m.measure, m.kind, m.count, m.denominator, m.as_of, m.detail, "
              f":measured_at, :public_from FROM ({query}) AS m")
    engine.run(insert, _bound(insert, params))
    return written


def measure(engine: Engine, run_id: str, clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)) -> int:
    """Write this run's measures for every source the nightly job fetches. Returns how many rows it wrote."""
    measured_at = clock()
    written = 0
    for source in load_sources().values():
        if not source.paged:
            continue
        params = {"run_id": run_id, "source": source.key, "cadence": source.cadence, "measured_at": measured_at,
                  "public_from": measured_at.astimezone(dt.UTC).date()}
        written += _write(engine, _source_query(source), params | {"coverage_rows_detail": COVERAGE_ROWS_DETAIL})
        query = _transform_query(source)
        if query is not None:
            written += _write(engine, query, params)
    return written
