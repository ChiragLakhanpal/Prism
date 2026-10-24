"""IEG's project performance ratings (Finances One DS00053) into strata.silver.ieg_ratings.

Each row is one evaluation of one project: an ICR Review (ICRR) or a PPAR, with the outcome and
Bank performance ratings word for word. The dataset gives the fiscal year of the evaluation, not
its date, so a rating counts as public from the last day of that fiscal year, June 30, or from the
fetch day when that is later (ADR 0002). That is never before IEG published it.
"""

from __future__ import annotations

import datetime as dt

from strata.lakehouse import clean

TABLES = {
    "strata.silver.ieg_ratings": (
        "project_id", "project_name", "country", "region", "global_practice", "agreement_type",
        "lending_instrument_type", "approval_fiscal_year", "final_closing_fiscal_year", "evaluation_type",
        "evaluation_fiscal_year", "outcome", "bank_performance", "quality_at_entry", "quality_of_supervision",
        "me_quality", "page_hash", "fetched_at", "public_from"),
}

# The columns that tell one of the source's records from another (strata.lakehouse.readiness).
RECORD_KEY = ("project_id", "evaluation_type", "evaluation_fiscal_year")
# Each record's fiscal year, by which the dashboard splits coverage_rows (strata.lakehouse.readiness).
FISCAL_YEAR = "evaluation_fiscal_year"


def _year(value) -> int | None:
    written = clean.text(value)
    return int(written) if written and written.isdigit() else None


def parse(body: dict, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    fetched = fetched_at.astimezone(dt.UTC).date()
    rows = []
    for record in body.get("data") or []:
        project_id = clean.text(record.get("project_id"))
        if not project_id:
            continue
        evaluated = _year(record.get("evaluation_fy"))
        rows.append((
            project_id,
            clean.text(record.get("project_name")),
            clean.text(record.get("country")),
            clean.text(record.get("wb_region")),
            clean.text(record.get("global_practice")),
            clean.text(record.get("agreement_type")),
            clean.text(record.get("lending_instrument_type")),
            _year(record.get("approval_fy")),
            _year(record.get("final_closing_fy")),
            clean.text(record.get("evaluation_type")),
            evaluated,
            clean.text(record.get("outcome")),
            clean.text(record.get("bank_performance")),
            clean.text(record.get("quality_at_entry")),
            clean.text(record.get("quality_of_supervision")),
            clean.text(record.get("me_quality")),
            page_hash,
            fetched_at,
            clean.public_from(clean.fiscal_year_end(evaluated) if evaluated else None, fetched),
        ))
    return {"strata.silver.ieg_ratings": rows}
