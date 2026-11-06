"""The cleaning rules silver applies on purpose (docs/PLAN.md section 3, "Quirks to handle on purpose").

Each rule is defined once here, and every silver transform uses it:

- Text has its spacing made single, and a list is joined with commas. An amount keeps two decimal
  places.
- Text written with markup is kept as plain words: a notice's HTML, and the words of a Procurement
  Plan's table that the layout parser wrote with their tags. On the workspace, ai_parse_document
  wrote a section's name as <u>WORKS</u>, which is WORKS (ticket 122).
- Dates come in mixed formats (09-Sep-2019, 2021-09-17T00:00:00Z, 2022/04/19). parse_date reads
  each one and returns None for anything else, never a guess.
- World Bank fiscal years run July to June, so a date from July 1 on falls in the next year's FY.
- A row's public_from is the date its source published it or, when that date is missing or later
  than the fetch, the day Prism first fetched it (ADR 0002).
- A STEP reference (KE-NWWDA-541055-CW-RFB) is parsed into its parts. Sources write it with stray
  spaces (KE- WASREB-...) or slashes (KE/TAVEVO/82746/GO/RFB), and both normalize to hyphens. The
  method is never read from the reference: its last part is kept only for the data note. Its kinds
  and method codes are config/references.toml's, which the plan reader's repair also reads
  (follows_step_grammar; ticket 131).
- Loan numbers come in five forms (IDA60300, IDA-60300, IDA / 60300, a bare 60300, and the older
  four-digit number with a country code, 6030-KE) and normalize to one: the lender's letters and
  the five-digit number, IDA60300. The older form gains its 0 (6030-KE is credit 60300). A number
  written with no lender keeps only its digits, so gold resolves it against the loans of the
  notice's own project, and a lender with four digits and no country code is never a normalized
  value.
- A project record's financing numbers are kept whole, each with its financier (financing_number):
  a loan or credit as above, and an IDA grant, a trust fund, co-financing or a loan with a suffix
  letter as its financier, one hyphen and the rest of the number (IDA-H8060, TF-C3892, COFN-00280,
  IBRD-2075S).
- Method names from before the 2016 Procurement Regulations map to the current names, with the
  market approach the old name implies. The old wording is kept in its own column.
- One project's plans and record can write one implementing agency two ways ("Public Works Department" in
  P130164's plan, "Rajasthan State Public Works Department" in its record). Two of a project's names are one
  agency when they are the same after the words "the", "Government of" and "State" are dropped, or when one
  ends with the whole of the other, at least two words of it (ticket 133). So a leading place name on one of
  the two drops away, and two names that differ only by their places ("Kwale Water and Sewerage Company Ltd",
  "Wajir Water and Sewerage Company Ltd") stay two agencies. Agencies groups a project's names by this rule, and
  Agencies.of_project takes them in one order, so every caller gives an agency the same id. Every module of the
  server and the tools that names an agency in a link, or pairs two of its names, goes through it
  (tests/test_agency_names.py lists them). The plan reader's series in strata.lakehouse.plans still pairs a
  project's plan versions by the exact name each plan writes, so what changed between two plans that write one
  agency's name two ways is a follow-up.
"""

from __future__ import annotations

import datetime as dt
import decimal
import html
import re
from dataclasses import dataclass

from strata.config import MethodName, load_method_names, load_references

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


# A tag that ends a line (a line break, or the end of a paragraph, a block, a heading, a list item or a table row),
# and any tag.
BREAKS = re.compile(r"<\s*(br|/p|/div|/h\d|/li|/tr)\s*/?\s*>", re.I)
TAGS = re.compile(r"<[^>]+>")


def plain_text(markup) -> str:
    """Words written with markup as plain text, one line per paragraph or line break, each line's spacing made single,
    and an entity such as &amp; read as the character it stands for. It reads a notice's HTML, and each word of a
    Procurement Plan's table before the plan reader writes it, so <u>WORKS</u> is WORKS."""
    if not markup:
        return ""
    written = html.unescape(TAGS.sub(" ", BREAKS.sub("\n", str(markup))))
    lines = (" ".join(line.split()) for line in written.splitlines())
    return "\n".join(line for line in lines if line)


def as_written(value) -> str | None:
    """A field's text exactly as the source wrote it, spaces inside it included, with only the spaces at its ends
    taken off, or None when it is empty or says it is (NOT_GIVEN). For the columns that keep a source's own words
    beside Prism's name for them, such as procurement_method_as_written."""
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

# The parts a STEP reference is made of: its kinds, with STEP's category for each, and its method codes
# (config/references.toml, the one registry the plan reader's repair reads too; ticket 131).
REFERENCES = load_references()
CATEGORIES = REFERENCES.kinds
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
    rf"(?P<category>{'|'.join(map(re.escape, CATEGORIES))})-(?P<method>[A-Z]+)(?P<suffix>-.+)?")

# A plan row's reference in STEP's form, part by part: two characters, the agency's parts, the number, a kind of two
# characters, the method and perhaps one more part. Its characters may be misread; in_step_form checks only the
# shape, and follows_step_grammar checks every part: the country's two letters, the agency's letters, the number's
# digits, a kind in config/references.toml and a method code there (ticket 131).
_STEP_FORM = re.compile(r"[A-Z0-9]{2}-[A-Z0-9]+(?:-[A-Z0-9]+)*?-[A-Z0-9]+-[A-Z0-9]{2}-[A-Z0-9]+(?:-[A-Z0-9]+)?")
_STEP_GRAMMAR = re.compile(
    r"[A-Z]{2}-[A-Z]+(?:-[A-Z]+)*-\d+-"
    rf"(?:{'|'.join(map(re.escape, CATEGORIES))})-(?:{'|'.join(map(re.escape, REFERENCES.methods))})(?:-[A-Z0-9]+)?")


def in_step_form(reference: str) -> bool:
    """Whether a plan row's reference has the shape of STEP's references, whatever its characters, so
    KE-NWWDA-193461-90-RF8 does and NWWDA-WSDP-03-2019-2020, an older form, does not."""
    return bool(_STEP_FORM.fullmatch(reference))


def follows_step_grammar(reference: str) -> bool:
    """Whether every part of a plan row's reference is one STEP writes: KE-NWWDA-541055-CW-RFB does, and
    KE-NWWDA-193461-90-RF8, whose kind and method are not in config/references.toml, does not."""
    return bool(_STEP_GRAMMAR.fullmatch(reference))


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


# ── Financing numbers ────────────────────────────────────────────────────

# A project record's financing number as the projects API writes it: the financier's letters, a hyphen, and the
# rest of the number.
FINANCING_NUMBER = re.compile(r"(?P<financier>[A-Z]+)(?:\s*[-/–]\s*|\s+)?(?P<rest>[A-Z0-9].*)")


@dataclass(frozen=True)
class FinancingNumber:
    number: str  # IDA60300 for a loan or credit, IDA-H8060 for a grant, TF-C3892 for a trust fund
    financier: str | None  # IBRD, IDA, TF, COFN or another the records name; None when none is written


def financing_number(text) -> FinancingNumber | None:
    """A financing number a project record names in its loan transactions, with its financier (ticket 120).

    A loan or credit that loan_number reads whole is kept as its lender and digits, IDA60300. A lender with four
    digits, such as IBRD-8956, is kept the same way, IBRD8956: the projects API is the source of a project's loans,
    and an IBRD loan has four digits, where a notice's four digits may be a credit's older form. Every other number
    is kept as its financier, one hyphen and the rest of the number as written, in upper case: an IDA grant
    (IDA-H8060, IDA-D9910), a trust fund (TF-C3892), co-financing (COFN-00280) or a loan with a suffix letter
    (IBRD-2075S). A number with no financier written is kept as written, with none."""
    written = " ".join(str(text or "").split()).upper()
    if not written:
        return None
    loan = loan_number(written)
    if loan and loan.lender and loan.as_written == written:
        return FinancingNumber(loan.normalized or f"{loan.lender}{loan.digits}", loan.lender)
    parts = FINANCING_NUMBER.fullmatch(written)
    if not parts:
        return FinancingNumber(written, None)
    return FinancingNumber(f"{parts['financier']}-{parts['rest']}", parts["financier"])


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


# ── Implementing agencies ────────────────────────────────────────────────

# The words two names of one implementing agency may differ by, wherever they stand (ticket 133). A leading place
# name needs no list of places: the name that has it ends with the whole of the name that does not.
AGENCY_DROPPED_WORDS = (("government", "of"), ("state",), ("the",))
# The fewest words the shorter name must have for a name that ends with it to be the same agency, so a name that is
# one type word ("Agency", "Treasury") never takes in every name that ends with that word.
AGENCY_SHORTEST_END = 2


def agency_id(name: str) -> str:
    """An implementing agency's name as an id in links: in lower case, with hyphens between its words."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _agency_words(name: str) -> tuple[str, ...]:
    """A name's words in lower case, without the words AGENCY_DROPPED_WORDS lists. An id's words are its name's."""
    words, kept, i = re.findall(r"[a-z0-9]+", name.lower()), [], 0
    while i < len(words):
        dropped = next((drop for drop in AGENCY_DROPPED_WORDS if tuple(words[i:i + len(drop)]) == drop), None)
        if dropped:
            i += len(dropped)
        else:
            kept.append(words[i])
            i += 1
    return tuple(kept)


def same_agency(one: str, other: str) -> bool:
    """Whether two of one project's names are one implementing agency: the same words once AGENCY_DROPPED_WORDS are
    dropped, or one ends with the whole of the other, which has at least AGENCY_SHORTEST_END words."""
    first, second = _agency_words(one), _agency_words(other)
    if not first or not second:
        return False
    shorter, longer = sorted((first, second), key=len)
    return shorter == longer or (len(shorter) >= AGENCY_SHORTEST_END and longer[-len(shorter):] == shorter)


@dataclass(frozen=True)
class Agency:
    """One implementing agency of a project, with every way the project writes its name."""

    agency_id: str  # its id in links: its first name's, the newest plan's spelling when the caller lists plans first
    name: str  # the longest of its names, which its heading shows
    names: tuple[str, ...]  # each way the project writes it, once, in the order the caller gave them

    @property
    def also_written_as(self) -> tuple[str, ...]:
        """Its other names, which the heading's window lists ("Also written as Public Works Department")."""
        return tuple(name for name in self.names if name.lower() != self.name.lower())

    def holds(self, name: str | None) -> bool:
        """Whether the name is one of the ways it is written, in any case: a plan version's own name, say."""
        return (name or "").strip().lower() in {written.lower() for written in self.names}


class Agencies:
    """One project's implementing agencies, grouped by same_agency from the names its plans and its record give.

    Callers build it with of_project, which orders the names one way for all of them: the plan versions public by
    the as-of date, newest first, then those public only later, then the names the project record gives. So every
    caller gives an agency the same id, its newest public plan's spelling, the one each of its plan rows links with
    (agency_id of the row's own name), and an agency with no plan takes its record's. A name that pairs with two
    agencies joins neither and stands alone, so a bare type name ("Water Works Development Agency") never makes
    Coast and Northern one agency, and find, which calls such a name ambiguous, agrees."""

    def __init__(self, names):
        groups: list[list[str]] = []
        for raw in names:
            name = (raw or "").strip()
            if not name:
                continue
            joined = [group for group in groups if any(same_agency(name, other) for other in group)]
            if len(joined) == 1:
                if name.lower() not in {other.lower() for other in joined[0]}:
                    joined[0].append(name)
            elif not any(name.lower() in {other.lower() for other in group} for group in joined):
                groups.append([name])
        self._agencies = tuple(Agency(agency_id(group[0]), max(group, key=len), tuple(group)) for group in groups)

    @classmethod
    def of_project(cls, versions, record_names=(), as_of: dt.date | None = None) -> Agencies:
        """A project's agencies from its plan versions (each a mapping with implementing_agency, plan_date,
        public_from and document_id) and the names its record gives, in the one order every caller uses: the
        versions public by as_of newest first, by plan date, then the day each became public, then document id;
        then those public only later, newest first; then the record's names. Every version when as_of is None."""
        def newest(version) -> tuple:
            return (version["plan_date"] or dt.date.min, version["public_from"] or dt.date.min,
                    str(version["document_id"]))

        named = [version for version in versions if (version["implementing_agency"] or "").strip()]
        public = [version for version in named if as_of is None or version["public_from"] <= as_of]
        later = [version for version in named if as_of is not None and version["public_from"] > as_of]
        ordered = [*sorted(public, key=newest, reverse=True), *sorted(later, key=newest, reverse=True)]
        return cls([version["implementing_agency"] for version in ordered] + list(record_names))

    def __iter__(self):
        return iter(self._agencies)

    def __len__(self) -> int:
        return len(self._agencies)

    def find(self, asked: str) -> Agency | None:
        """The agency a name or an id stands for, in any case: one of its own names or their ids first, then the one
        agency whose names the rule pairs it with, so a link written with another of the agency's names still opens
        it. None when no agency, or more than one, pairs with it."""
        wanted = asked.strip().lower()
        for agency in self._agencies:
            if any(wanted in (name.lower(), agency_id(name)) for name in agency.names):
                return agency
        paired = [agency for agency in self._agencies if any(same_agency(asked, name) for name in agency.names)]
        return paired[0] if len(paired) == 1 else None
