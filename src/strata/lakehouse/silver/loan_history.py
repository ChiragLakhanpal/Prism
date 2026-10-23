"""The monthly history of loans and credits (Finances One DS00976 for IDA credits, DS00975 for IBRD
loans) into strata.silver.loan_history, for the slice's countries.

Each row is one loan or credit at the end of one month (end_of_period), in the same columns as the
latest snapshot (strata.lakehouse.silver.loans). Its closing date month by month is what
gold.project_closing_date reads, so a closing-date extension shows in the month it was first
reported.
"""

from __future__ import annotations

import datetime as dt

from strata.lakehouse.silver import loans

TABLES = {"strata.silver.loan_history": loans.COLUMNS}

# The columns that tell one of the source's records from another (strata.lakehouse.readiness).
RECORD_KEY = ("loan_number", "end_of_period")


def parse(body: dict, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    rows = [loans.row(record, page_hash, fetched_at) for record in body.get("data") or []]
    return {"strata.silver.loan_history": [kept for kept in rows if kept]}
