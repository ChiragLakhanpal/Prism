"""Governance indicators from the Indicators API (api.worldbank.org/v2): CPIA's IQ.CPA codes and WGI's
GOV_WGI estimates, into strata.silver.indicators.

The API sends each page as [about the page, records]. The first part gives lastupdated, the day the
API last published the indicator; each record is one country's value for one year. The API
overwrites a value it revises, so each fetch whose page changed is a new version: its rows carry
the page's lastupdated as their public_from (ADR 0002), and gold.governance_score keeps every
version. A year with no value is kept with an empty value, so silver holds every record the API
reported.
"""

from __future__ import annotations

import datetime as dt

from strata.lakehouse import clean, pages

TABLES = {
    "strata.silver.indicators": (
        "indicator_id", "indicator_name", "country_code", "country_iso3", "country_name", "year", "value",
        "last_updated", "page_hash", "fetched_at", "public_from"),
}

# The columns that tell one of the source's records from another (strata.lakehouse.readiness).
RECORD_KEY = ("indicator_id", "country_code", "country_iso3", "year")


def _value(value) -> float | None:
    return None if value in (None, "") else float(value)


def parse(body, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    about, records = pages.split(body)
    last_updated = clean.parse_date(about.get("lastupdated"))
    public = clean.public_from(last_updated, fetched_at.astimezone(dt.UTC).date())
    rows = []
    for record in records:
        indicator, country = record.get("indicator") or {}, record.get("country") or {}
        year = clean.text(record.get("date"))
        if not clean.text(indicator.get("id")):
            continue
        rows.append((
            clean.text(indicator.get("id")),
            clean.text(indicator.get("value")),
            clean.text(country.get("id")),
            clean.text(record.get("countryiso3code")),
            clean.text(country.get("value")),
            int(year) if year and year.isdigit() else None,
            _value(record.get("value")),
            last_updated,
            page_hash,
            fetched_at,
            public,
        ))
    return {"strata.silver.indicators": rows}
