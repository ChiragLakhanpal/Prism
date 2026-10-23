"""Loans and credits, latest snapshot (Finances One DS00001 for IDA credits, DS00047 for IBRD loans)
into strata.silver.loans.

Each row is one loan or credit at the end of the month the snapshot describes (end_of_period), with
its disbursed, undisbursed and canceled amounts in US dollars and its most recent closing date.
The two datasets name the same things differently: IDA's credit_number and disbursed_amount_us_
are IBRD's loan_number and disbursed_amount, and so on, so row() reads either. Both write the loan
number in its normalized form, such as IDA60290 or IBRD89940, which gold joins to projects on.

A row's public_from is end_of_period, the date the snapshot describes, or the fetch day when that is
later (ADR 0002). The monthly history (strata.lakehouse.silver.loan_history) uses the same row.
"""

from __future__ import annotations

import datetime as dt
import re

from strata.lakehouse import clean

COLUMNS = (
    "loan_number", "lender", "project_id", "project_name", "country_code", "country", "borrower", "status",
    "original_principal_usd", "disbursed_usd", "undisbursed_usd", "cancelled_usd", "approval_date", "effective_date",
    "closing_date", "last_disbursement_date", "end_of_period", "page_hash", "fetched_at", "public_from")
TABLES = {"strata.silver.loans": COLUMNS}

# The columns that tell one of the source's records from another (strata.lakehouse.readiness).
RECORD_KEY = ("loan_number",)


LENDER = re.compile(r"^(IBRD|IDA|TF)")


def _either(record: dict, *names):
    """The first of the fields that the record fills: IDA's name, then IBRD's."""
    for name in names:
        if record.get(name) not in (None, ""):
            return record[name]
    return None


def row(record: dict, page_hash: str, fetched_at: dt.datetime) -> tuple | None:
    """One loan or credit as a row of COLUMNS, or None when it has no loan number."""
    number = clean.text(_either(record, "credit_number", "loan_number"))
    if not number:
        return None
    lender = LENDER.match(number.upper())
    end_of_period = clean.parse_date(record.get("end_of_period"))
    return (
        number.upper(),
        lender[1] if lender else None,
        clean.text(record.get("project_id")),
        clean.text(_either(record, "project_name", "project_name_")),
        clean.text(record.get("country_code")),
        clean.text(record.get("country")),
        clean.text(record.get("borrower")),
        clean.text(_either(record, "credit_status", "loan_status")),
        clean.amount(_either(record, "original_principal_amount_us_", "original_principal_amount")),
        clean.amount(_either(record, "disbursed_amount_us_", "disbursed_amount")),
        clean.amount(_either(record, "undisbursed_amount_us_", "undisbursed_amount")),
        clean.amount(_either(record, "cancelled_amount_us_", "cancelled_amount")),
        clean.parse_date(record.get("board_approval_date")),
        clean.parse_date(record.get("effective_date_most_recent")),
        clean.parse_date(record.get("closed_date_most_recent")),
        clean.parse_date(record.get("last_disbursement_date")),
        end_of_period,
        page_hash,
        fetched_at,
        clean.public_from(end_of_period, fetched_at.astimezone(dt.UTC).date()),
    )


def parse(body: dict, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    rows = [row(record, page_hash, fetched_at) for record in body.get("data") or []]
    return {"strata.silver.loans": [kept for kept in rows if kept]}
