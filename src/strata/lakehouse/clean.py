"""The cleaning rules silver applies on purpose (docs/PLAN.md section 3, "Quirks to handle on purpose").

Each rule is defined once here, and every silver transform uses it:

- Text has its spacing made single, and a list is joined with commas. An amount keeps two decimal
  places.
- Dates come in mixed formats (09-Sep-2019, 2021-09-17T00:00:00Z, 2022/04/19). parse_date reads
  each one and returns None for anything else, never a guess.
- World Bank fiscal years run July to June, so a date from July 1 on falls in the next year's FY.
- A row's public_from is the date its source published it or, when that date is missing or later
  than the fetch, the day Strata first fetched it (ADR 0002).
- A STEP reference (KE-NWWDA-541055-CW-RFB) is parsed into its parts. Sources write it with stray
  spaces (KE- WASREB-...) or slashes (KE/TAVEVO/82746/GO/RFB), and both normalize to hyphens. The
  method is never read from the reference: its last part is kept only for the data note.
- Loan numbers come in five forms (IDA60300, IDA-60300, IDA / 60300, a bare 60300, and the older
  four-digit number with a country code, 6030-KE) and normalize to one: the lender's letters and
  the five-digit number, IDA60300. The older form gains its 0 (6030-KE is credit 60300). A number
  written with no lender keeps only its digits, so gold resolves it against the loans of the
  notice's own project, and a lender with four digits and no country code is never a normalized
  value.
- Method names from before the 2016 Procurement Regulations map to the current names, with the
  market approach the old name implies. The old wording is kept in its own column.
"""

from __future__ import annotations

import datetime as dt
import decimal
import re
from dataclasses import dataclass

from strata.config import MethodName, load_method_names

# ── Text and amounts ─────────────────────────────────────────────────────

# How a source writes an empty field in words: the awards since FY2020 write the word null for a
# supplier and a country they do not give.
NOT_GIVEN = frozenset({"null"})


def text(value) -> str | None:
    """A field's text with its spacing made single, or None when it is empty or says it is (NOT_GIVEN). A
    list is joined with commas."""
    if isinstance(value, list):
        value = ",".join(str(item) for item in value)
    written = " ".join(str(value).split()) if value is not None else ""
    return None if written.lower() in NOT_GIVEN else written or None


def as_written(value) -> str | None:
    """A field's text exactly as the source wrote it, spaces inside it included, with only the spaces at its ends
    taken off, or None when it is empty or says it is (NOT_GIVEN). For the columns that keep a source's own words
    beside Strata's name for them, such as procurement_method_as_written."""
    written = str(value).strip() if value is not None else ""
    return None if written.lower() in NOT_GIVEN else written or None


def supplier_id(value) -> str | None:
    """A STEP supplier ID, or None when the field is empty or 0, which the awards write for a row that
    names no supplier (ticket 19), so no supplier is keyed 0."""
    written = text(value)
    return None if written in (None, "0") else written


def amount(value) -> decimal.Decimal | None:
    """An amount to the cent, or None when the field is empty."""
    if value is None or str(value).strip() == "":
        return None
    return decimal.Decimal(str(value)).quantize(decimal.Decimal("0.01"))


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
    written = str(value).strip()
    if not written:
        return None
    written = re.sub(r"T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$", "", written)
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(written, fmt).date()
        except ValueError:
            continue
    return None


def fiscal_year(day: dt.date | None) -> int | None:
    """The World Bank fiscal year a date falls in: FY2020 runs from July 1, 2019 to June 30, 2020."""
    if day is None:
        return None
    return day.year + 1 if day.month >= 7 else day.year


def fiscal_year_end(year: int) -> dt.date:
    """The last day of a World Bank fiscal year: FY2020 ends on June 30, 2020."""
    return dt.date(year, 6, 30)


def public_from(published: dt.date | None, fetched: dt.date) -> dt.date:
    """The day a row became public: the source's own date, unless it is missing or after the fetch."""
    if published is None or published > fetched:
        return fetched
    return published


# ── STEP references ──────────────────────────────────────────────────────

CATEGORIES = {"CW": "Works", "GO": "Goods", "CS": "Consultant Services", "NC": "Non-consulting Services"}
# A category as the FY2001 to FY2016 awards dataset writes it, where it differs from STEP's name.
OLD_CATEGORIES = {"CIVIL WORKS": "Works"}


def category(name) -> str | None:
    """A procurement category in STEP's words: Works, Goods, Consultant Services or Non-consulting Services."""
    written = text(name)
    return OLD_CATEGORIES.get(written.upper(), written) if written else None


# A personal title followed by a name, as a description names a consultant hired in person: "the
# Consultancy Services of Dr. ..." or "CONSULTANCY SERVICES OF DR ...". In capitals, MS and ENG
# count only with their period, so MS OFFICE and ENG WORKS are not people; MR, MRS, DR, CAPT and
# PROF are not words of their own, so they count without one. DR before Congo, in any case, is the
# Democratic Republic of the Congo.
PERSONAL_TITLE = re.compile(
    r"\b(?:(?:Mr|Mrs|Ms|Miss|Dr(?!\.?\s+(?i:congo)\b)|Capt|Eng|Prof)\.?|(?:MS|ENG)\.|"
    r"(?:MR|MRS|DR(?!\.?\s+(?i:congo)\b)|CAPT|PROF)\.?)\s+[A-Z]")

# A word that names a firm, not a person, in any case: a legal form such as LTD or GMBH, a word such
# as PARTNERS, ENTERPRISES or UNIVERSITY that is never part of a person's name, or an ampersand.
# CONSULTANT alone is not one, as a person is one.
FIRM = re.compile(r"\b(?:LTD|LIMITED|LLC|LLP|INC|PLC|PVT|PTY|SARL|GMBH|COMPANY|CORP(?:ORATION)?|"
                  r"PARTNERS?|ASSOCIATES|LABORATORIES|CONSULT(?:ING|ANTS|ANCY)|GROUP|ENGINEERS?|ENGINEERING|"
                  r"ENTERPRISES?|SOLUTIONS?|SERVICES|SUPPLIES|SUPPLIERS|INVESTMENTS?|INTERNATIONAL|HOLDINGS|"
                  r"TECHNOLOGIES|SYSTEMS|INDUSTRIES|INDUSTRIAL|TRADING|CONSTRUCTION|CONTRACTORS|VENTURES?|"
                  r"MOTORS|MERCHANTS|HARDWARE|LOGISTICS|AGENC(?:Y|IES)|UNIVERSITY|INSTITUTE|FOUNDATION|"
                  r"ASSOCIATION|AUTHORITY)\b|&", re.I)

# A two-letter legal form such as S.A., B.V., AG or CO, where a firm writes it: at the end of the name
# or before a comma or a bracket. A person's initials or surname can end a name the same way, as in
# DOE, S.A. or JOHN CO, so this form alone never makes a titled supplier a firm, and it does not
# keep the name of the person a description names.
LEGAL_FORM = re.compile(r"\b(?:S\.?A|B\.?V|AG|CO)\b\.?\s*(?:[,(]|$)", re.I)


def names_a_person(procurement_category, description) -> bool:
    """Whether a contract's description names a person: a Consultant Services contract whose
    description gives a personal title followed by a name (spec, user stories 59 and 115)."""
    return category(procurement_category) == "Consultant Services" and bool(PERSONAL_TITLE.search(text(description) or ""))


def titled(name) -> bool:
    """Whether a supplier is written as a person, in any category: a personal title before the name,
    and no word that names a firm, so DR. REDDY'S LABORATORIES LTD stays a firm."""
    written = text(name) or ""
    return bool(PERSONAL_TITLE.match(written)) and not FIRM.search(written)


def _words(written: str) -> set[str]:
    return set(re.findall(r"[A-Z]+", written.upper()))


def is_the_named_person(description, supplier) -> bool:
    """Whether every word of the supplier's name is in the description from its personal title on,
    so the supplier is the person the description names."""
    written = text(description) or ""
    title = PERSONAL_TITLE.search(written)
    return bool(title) and _words(text(supplier) or "") <= _words(written[title.start():])


def hires_a_named_person(procurement_category, description, supplier) -> bool:
    """Whether a contract is with a person whom the row may name: its supplier is written with a
    personal title, or its description names a person and its supplier has no word that names a firm
    and either no two-letter legal form or is that person. A firm hired for a person's services keeps
    its name."""
    written = text(supplier) or ""
    return titled(supplier) or (names_a_person(procurement_category, description) and not FIRM.search(written)
                                and (not LEGAL_FORM.search(written) or is_the_named_person(description, supplier)))


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
# The lender, a hyphen, en dash or slash, the number, and a country code after a space or a hyphen.
# The country code is two letters on their own: 6030 AND is the number 6030 with no country code.
LOAN_NUMBER = re.compile(
    r"(?<![A-Z0-9])(?:(?P<lender>IBRD|IDA|TF)\s*(?:[-/\u2013]\s*)?)?(?P<digits>\d{4,6})(?![0-9])"
    r"(?:\s*[-\u2013]?\s*(?P<country>[A-Z]{2})(?![A-Z0-9]))?")


@dataclass(frozen=True)
class LoanNumber:
    as_written: str
    lender: str | None
    digits: str

    @property
    def normalized(self) -> str | None:
        """IDA60300 for every written form; None when the lender is not written, or when the number
        has four digits and no country code to say it is the older form."""
        return f"{self.lender}{self.digits}" if self.lender and len(self.digits) > 4 else None


def loan_number(text) -> LoanNumber | None:
    """The first loan or credit number in text, in any of its five forms."""
    if not text:
        return None
    match = LOAN_NUMBER.search(str(text).upper())
    if not match:
        return None
    digits = match["digits"]
    if len(digits) == 4 and match["country"]:
        digits += "0"  # the older form: credit 6030-KE is IDA60300
    return LoanNumber(match.group(0).strip(), match["lender"], digits)


# ── Selection methods ────────────────────────────────────────────────────

@dataclass(frozen=True)
class Method:
    name: str  # the current Procurement Regulations' name
    market_approach: str | None  # what the old name says about the market approach, in STEP's words


# Every name a source writes for a method other than the current one, by code and by name, and what each is now:
# the names before the July 2016 Procurement Regulations, the French plan template's and STEP's French names
# (config/method_names.toml, ticket 42). Matching ignores case, runs of spaces and curly apostrophes.
METHOD_NAMES = load_method_names()


def method_key(text) -> str:
    """A method name as the registry matches it: upper case, apostrophes straight, each run of spaces one."""
    return re.sub(r"\s+", " ", str(text).replace("\u2019", "'").replace("\u2018", "'")).strip().upper()


def _other_names() -> dict[str, MethodName]:
    return {method_key(entry.written): entry for entry in METHOD_NAMES.names}


def old_methods() -> dict[str, Method]:
    """Every other name, by its key, with the current method it stands for: the package form's method chip takes
    them too (src/strata/packages/form.py)."""
    return {key: Method(entry.method, entry.market_approach) for key, entry in _other_names().items()}


OLD_METHODS = old_methods()


def method(code=None, name=None) -> Method | None:
    """The current method for a code or name as a source writes it. A current name, or one the registry does not
    list, passes through as written: the awards and notices keep their own words beside it."""
    names = _other_names()
    for key in (code, name):
        if key and method_key(key) in names:
            found = names[method_key(key)]
            return Method(found.method, found.market_approach)
    if name and str(name).strip():
        return Method(re.sub(r"\s+", " ", str(name)).strip(), None)
    return None


@dataclass(frozen=True)
class MethodReading:
    """A plan's Method cell, read: the current name, the plan's own words and their language, and whether the
    words were mapped (True), already the current name (False), or a name the registry does not list (None),
    which keeps the plan's words and gets a Data note."""

    name: str
    original: str
    language: str | None
    mapped: bool | None


def read_method(text: str) -> MethodReading:
    """A plan's Method cell as the current Procurement Regulations' name, beside the words the plan used."""
    written = re.sub(r"\s+", " ", str(text)).strip()
    current = {re.sub(r"\s+", "", name).lower(): name for name in METHOD_NAMES.current}
    if re.sub(r"\s+", "", written).lower() in current:  # a PDF cell drops the space where it wraps
        return MethodReading(current[re.sub(r"\s+", "", written).lower()], written, "en", False)
    found = _other_names().get(method_key(written))
    if found is not None:
        return MethodReading(found.method, written, found.language, True)
    return MethodReading(written, written, None, None)
