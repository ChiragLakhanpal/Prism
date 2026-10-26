"""Procurement notices (search.worldbank.org's procnotices API) into strata.silver.notices.

Contact details are gone before a page reaches bronze (strata.lakehouse.contacts), so this
transform never sees them; it notes which notices lost some. It types each field, parses the STEP
reference, maps an old method name such as ICB to the current one with the market approach it
implies (keeping the notice's own words in their own columns), and reads three things from the
notice's text: the loan or credit number, and for a Contract Award notice, the Contract Signature
Date and the signed contract price with its currency. The text itself is kept as plain text.
"""

from __future__ import annotations

import datetime as dt
import decimal
import html
import re
from dataclasses import dataclass

from strata.lakehouse import clean, contacts, quality
from strata.lakehouse.engine import Engine

TABLES = {
    "strata.silver.notices": (
        "notice_id", "notice_type", "notice_date", "fiscal_year", "notice_status", "notice_language",
        "project_id", "project_name", "project_country", "bid_reference_no", "step_reference",
        "reference_method_code", "bid_description", "procurement_group", "procurement_category",
        "procurement_method_code", "procurement_method_as_written", "procurement_method", "market_approach",
        "submission_deadline", "loan_number_as_written", "loan_number", "loan_digits",
        "contract_signature_date", "contract_fiscal_year", "signed_contract_price", "signed_contract_currency",
        "notice_text",
        "contact_details_removed", "page_hash", "fetched_at", "public_from"),
}

# The columns that tell one of the source's records from another (strata.lakehouse.readiness).
RECORD_KEY = ("notice_id",)
# Each record's fiscal year, by which the dashboard splits coverage_rows (strata.lakehouse.readiness).
FISCAL_YEAR = "fiscal_year"
# 2 since parse() runs the contact removal again (ticket 76). Ticket 75's record of what silver wrote for each page
# (strata.ops.silver_pages) holds the version each page was read under, so the next run reads every page recorded
# under 1 again, with the removal as it is now, and the nightly check then finds none of the numbers it left.
VERSION = 2


@dataclass(frozen=True)
class Flagged:
    """The notices in strata.silver.notices that the nightly check's contacts_left counts, and their pages."""

    notices: int
    pages: int


# It builds in only quality.CONTACTS_LEFT, the check's own condition, whose values are bound parameters.
FLAGGED = ("SELECT count(*) AS notices, count(DISTINCT page_hash) AS pages FROM strata.silver.notices WHERE "
           + quality.CONTACTS_LEFT)  # sql-lint: names only


def contacts_left(engine: Engine) -> Flagged:
    """How many notices the nightly check would flag now, and on how many pages."""
    notices, pages = engine.run(FLAGGED, quality.contacts_left_params()).rows[0]
    return Flagged(int(notices), int(pages))


BREAKS = re.compile(r"<\s*(br|/p|/div|/h\d|/li|/tr)\s*/?\s*>", re.I)
TAGS = re.compile(r"<[^>]+>")
SIGNATURE_DATE = re.compile(r"Contract Signature Date\s*(?:\(YYYY/MM/DD\))?\s*:?\s*([0-9]{1,4}[-/][0-9A-Za-z]{2,3}[-/][0-9]{2,4})", re.I)
SIGNED_PRICE = re.compile(r"(?:Signed Contract price|Contract Price)\s*:?\s*([A-Z]{3})\s*([0-9][0-9,]*(?:\.[0-9]+)?)", re.I)
LOAN_FIELD = re.compile(r"(?:Loan|Credit)[^:\n]{0,25}:\s*([^\n]{0,40})", re.I)


def plain_text(markup) -> str:
    """A notice's HTML as plain text, one line per paragraph or line break."""
    if not markup:
        return ""
    text = html.unescape(TAGS.sub(" ", BREAKS.sub("\n", str(markup))))
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _price(text: str) -> tuple[decimal.Decimal | None, str | None]:
    match = SIGNED_PRICE.search(text)
    if not match:
        return None, None
    return clean.amount(match[2].replace(",", "")), match[1].upper()


def _loan(text: str) -> clean.LoanNumber | None:
    for match in LOAN_FIELD.finditer(text):
        found = clean.loan_number(match[1])
        if found:
            return found
    return None


def parse(body: dict, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    fetched = fetched_at.astimezone(dt.UTC).date()
    rows = []
    for record in body.get("procnotices") or []:
        if not clean.text(record.get("id")):
            continue
        # Bronze kept the page after the removal as it was then, so silver runs it again: a fix to the patterns
        # reaches every page silver reads. Its last pass runs once more on the plain text, the text the nightly
        # check reads, where no HTML entity or tag sits between a label and its number (ticket 76).
        text = contacts.strip_left(plain_text(contacts.strip_again(record.get("notice_text"))))
        description = contacts.strip_again(clean.text(record.get("bid_description")))
        reference = clean.step_reference(record.get("bid_reference_no"))
        method = clean.method(record.get("procurement_method_code"), record.get("procurement_method_name"))
        notice_date = clean.parse_date(record.get("noticedate")) or clean.parse_date(record.get("submission_date"))
        award = (record.get("notice_type") or "").strip().lower() == "contract award"
        signature = SIGNATURE_DATE.search(text) if award else None
        signed = clean.parse_date(signature[1]) if signature else None
        price, currency = _price(text) if award else (None, None)
        loan = _loan(text)
        group = clean.text(record.get("procurement_group"))
        rows.append((
            clean.text(record.get("id")),
            clean.text(record.get("notice_type")),
            notice_date,
            clean.fiscal_year(notice_date),
            clean.text(record.get("notice_status")),
            clean.text(record.get("notice_lang_name")),
            clean.text(record.get("project_id")),
            clean.text(record.get("project_name")),
            clean.text(record.get("project_ctry_name")),
            clean.text(record.get("bid_reference_no")),
            reference.reference if reference else None,
            reference.method_code if reference else None,
            description,
            group,
            clean.CATEGORIES.get(group or ""),
            clean.text(record.get("procurement_method_code")),
            clean.text(record.get("procurement_method_name")),
            method.name if method else None,
            method.market_approach if method else None,
            clean.parse_date(record.get("submission_deadline_date")),
            loan.as_written if loan else None,
            loan.normalized if loan else None,
            loan.digits if loan else None,
            signed,
            clean.fiscal_year(signed or notice_date) if award else None,
            price,
            currency,
            text or None,
            contacts.removed_from({**record, "notice_text": text, "bid_description": description}),
            page_hash,
            fetched_at,
            clean.public_from(notice_date, fetched),
        ))
    return {"strata.silver.notices": rows}
