"""Projects (search.worldbank.org's v3 projects API) into strata.silver.projects,
strata.silver.project_loans and strata.silver.project_isr_ratings.

The projects API keys each page's records by project ID. Each project's loans and credits come
from its loan transactions, written IDA-60300, and are normalized once (strata.lakehouse.clean),
so a loan number in any of its forms joins to its project. The team leader's name is not kept.

Each project gets one sector in Strata's taxonomy (config/sectors.toml): the sector of the major
sector with the largest share, whichever of the API's two taxonomies its codes come from. The API
keeps only each project's latest ISR ratings and lists some of them twice; each is kept once.
"""

from __future__ import annotations

import datetime as dt

from strata.config import load_sectors
from strata.lakehouse import clean

TABLES = {
    "strata.silver.projects": (
        "project_id", "project_name", "country_code", "country_name", "region", "status", "approval_date",
        "approval_fiscal_year", "closing_date", "implementing_agency", "borrower", "sector_codes", "major_sector",
        "major_sector_code", "sector", "sector_name", "total_commitment_usd", "public_disclosure_date",
        "last_updated_on", "page_hash", "fetched_at", "public_from"),
    "strata.silver.project_loans": (
        "project_id", "loan_number", "loan_number_as_written", "page_hash", "fetched_at", "public_from"),
    "strata.silver.project_isr_ratings": (
        "project_id", "rating_code", "rating_name", "isr_date", "value", "page_hash", "fetched_at", "public_from"),
}

# The columns that tell one of the source's records from another (strata.lakehouse.readiness).
RECORD_KEY = ("project_id",)

PENDING = """
SELECT p.page_hash, p.body, p.fetched_at
FROM strata.bronze.api_pages AS p
WHERE p.source = :source
  AND NOT EXISTS (SELECT 1 FROM strata.silver.projects AS s WHERE s.page_hash = p.page_hash)
ORDER BY p.fetched_at, p.page_hash
"""


def parse(body: dict, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    fetched = fetched_at.astimezone(dt.UTC).date()
    held = body.get("projects") or {}
    sectors = load_sectors()
    projects, loans, ratings = [], [], []
    for record in (held.values() if isinstance(held, dict) else held):
        project_id = clean.text(record.get("id") or record.get("proj_id"))
        if not project_id:
            continue
        approved = clean.parse_date(record.get("boardapprovaldate"))
        disclosed = clean.parse_date(record.get("public_disclosure_date"))
        public = clean.public_from(disclosed or approved, fetched)
        sector, code = sectors.of(record.get("major_sectors"))
        projects.append((
            project_id,
            clean.text(record.get("project_name")),
            clean.text(record.get("countrycode")),
            clean.text(record.get("countryshortname")),
            clean.text(record.get("regionname")),
            clean.text(record.get("status")),
            approved,
            clean.fiscal_year(approved),
            clean.parse_date(record.get("closingdate")),
            clean.text(record.get("impagency")),
            clean.text(record.get("borrower")),
            clean.text(record.get("sectorcode")),
            clean.text(record.get("major_sector_name")),
            code,
            sector,
            sectors.names.get(sector),
            clean.amount(record.get("curr_total_commitment") or record.get("totalamt")),
            disclosed,
            clean.parse_date(record.get("proj_last_upd_date")),
            page_hash,
            fetched_at,
            public,
        ))
        written = sorted({transaction.get("financier_loan") for transaction in record.get("loan_transactions") or []
                          if transaction.get("financier_loan")})
        for as_written in written:
            loan = clean.loan_number(as_written)
            if loan and loan.normalized:
                loans.append((project_id, loan.normalized, as_written, page_hash, fetched_at, public))
        ratings += _isr_ratings(project_id, record.get("isr_ratings"), page_hash, fetched_at, fetched)
    return {"strata.silver.projects": projects, "strata.silver.project_loans": loans,
            "strata.silver.project_isr_ratings": ratings}


def _isr_ratings(project_id: str, listed, page_hash: str, fetched_at: dt.datetime, fetched: dt.date) -> list[tuple]:
    """A project's latest ISR ratings, each once: the API lists some of them twice."""
    kept, rows = set(), []
    for rating in listed or []:
        code, value = clean.text(rating.get("code")), clean.text(rating.get("value"))
        day = clean.parse_date(rating.get("isr_date"))
        if not code or (code, day, value) in kept:
            continue
        kept.add((code, day, value))
        rows.append((project_id, code, clean.text(rating.get("name")), day, value, page_hash, fetched_at,
                     clean.public_from(day, fetched)))
    return rows
