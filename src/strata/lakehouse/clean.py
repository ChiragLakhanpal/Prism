"""The cleaning rules silver applies on purpose (docs/PLAN.md section 3, "Quirks to handle on purpose").

Each rule is defined once here, and every silver transform uses it:

- Dates come in mixed formats (09-Sep-2019, 2021-09-17T00:00:00Z, 2022/04/19). parse_date reads
  each one and returns None for anything else, never a guess.
- World Bank fiscal years run July to June, so a date from July 1 on falls in the next year's FY.
- A row's public_from is the date its source published it or, when that date is missing or later
  than the fetch, the day Strata first fetched it (ADR 0002).
- A STEP reference (KE-NWWDA-541055-CW-RFB) is parsed into its parts. Sources write it with stray
  spaces (KE- WASREB-...) or slashes (KE/TAVEVO/82746/GO/RFB), and both normalize to hyphens. The
  method is never read from the reference: its last part is kept only for the data note.
- Loan numbers come in four forms (IDA60300, IDA-60300, IDA / 60300 and a bare 60300) and
  normalize to one: the lender's letters and the number, IDA60300. A bare number has no lender, so
  gold resolves it against the loans of the notice's own project.
- Method names from before the 2016 Procurement Regulations map to the current names, with the
  market approach the old name implies. The old wording is kept in its own column.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

# ── Dates ────────────────────────────────────────────────────────────────

DATE_FORMATS = ("%d-%b-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%B-%Y")


def parse_date(value) -> dt.date | None:
    """A date written in any of the sources' formats, or None."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$", "", text)
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def fiscal_year(day: dt.date | None) -> int | None:
    """The World Bank fiscal year a date falls in: FY2020 runs from July 1, 2019 to June 30, 2020."""
    if day is None:
        return None
    return day.year + 1 if day.month >= 7 else day.year


def public_from(published: dt.date | None, fetched: dt.date) -> dt.date:
    """The day a row became public: the source's own date, unless it is missing or after the fetch."""
    if published is None or published > fetched:
        return fetched
    return published


# ── STEP references ──────────────────────────────────────────────────────

CATEGORIES = {"CW": "Works", "GO": "Goods", "CS": "Consultant Services", "NC": "Non-consulting Services"}
STEP_REFERENCE = re.compile(
    r"(?P<country>[A-Z]{2})-(?P<agency>[A-Z0-9][A-Z0-9 &.()]*?)-(?P<number>\d+)-"
    r"(?P<category>CW|GO|CS|NC)-(?P<method>[A-Z]+)(?P<suffix>-.+)?")


@dataclass(frozen=True)
class StepReference:
    reference: str
    country: str
    agency: str
    number: str
    category: str  # the reference's own category code: CW, GO, CS or NC
    method_code: str  # the reference's method part, kept for the data note and never used as the method


def step_reference(text) -> StepReference | None:
    """A STEP activity reference, normalized, or None when the text is not one."""
    if not text:
        return None
    candidate = re.sub(r"\s+", " ", str(text)).strip().upper()
    if "/" in candidate and "-" not in candidate:
        candidate = candidate.replace("/", "-")
    candidate = re.sub(r"\s*-\s*", "-", candidate)
    match = STEP_REFERENCE.fullmatch(candidate)
    if not match:
        return None
    return StepReference(candidate, match["country"], match["agency"], match["number"], match["category"],
                         match["method"])


# ── Loan numbers ─────────────────────────────────────────────────────────

LENDERS = ("IBRD", "IDA", "TF")
LOAN_NUMBER = re.compile(r"(?<![A-Z0-9])(?:(?P<lender>IBRD|IDA|TF)\s*(?:[-/]\s*)?)?(?P<digits>\d{4,6})(?:\s*[A-Z]{2})?(?![0-9])")


@dataclass(frozen=True)
class LoanNumber:
    as_written: str
    lender: str | None
    digits: str

    @property
    def normalized(self) -> str | None:
        """IDA60300 for every written form; None for a bare number, whose lender is not written."""
        return f"{self.lender}{self.digits}" if self.lender else None


def loan_number(text) -> LoanNumber | None:
    """The first loan or credit number in text, in any of its four forms."""
    if not text:
        return None
    match = LOAN_NUMBER.search(str(text).upper())
    if not match:
        return None
    return LoanNumber(match.group(0).strip(), match["lender"], match["digits"])


# ── Selection methods ────────────────────────────────────────────────────

@dataclass(frozen=True)
class Method:
    name: str  # the current Procurement Regulations' name
    market_approach: str | None  # what the old name says about the market approach, in STEP's words


# Old names (before the July 2016 Procurement Regulations), by code and by name, and what each is now.
OLD_METHODS = {
    "ICB": Method("Request for Bids", "Open - International"),
    "INTERNATIONAL COMPETITIVE BIDDING": Method("Request for Bids", "Open - International"),
    "NCB": Method("Request for Bids", "Open - National"),
    "NATIONAL COMPETITIVE BIDDING": Method("Request for Bids", "Open - National"),
    "LIB": Method("Request for Bids", "Limited - International"),
    "LIMITED INTERNATIONAL BIDDING": Method("Request for Bids", "Limited - International"),
    "SHOPPING": Method("Request for Quotations", None),
    "NATIONAL SHOPPING": Method("Request for Quotations", "Limited - National"),
    "INTERNATIONAL SHOPPING": Method("Request for Quotations", "Limited - International"),
    "DC": Method("Direct Selection", "Direct"),
    "DIRECT CONTRACTING": Method("Direct Selection", "Direct"),
}


def method(code=None, name=None) -> Method | None:
    """The current method for a code or name as a source writes it. A current name passes through."""
    for key in (code, name):
        if key and re.sub(r"\s+", " ", str(key)).strip().upper() in OLD_METHODS:
            return OLD_METHODS[re.sub(r"\s+", " ", str(key)).strip().upper()]
    if name and str(name).strip():
        return Method(re.sub(r"\s+", " ", str(name)).strip(), None)
    return None
