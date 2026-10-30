"""STEP's Procurement Plan, word for word.

A published Procurement Plan is an export from STEP: a few pages of narrative, then one table per
section (WORKS, GOODS, NON CONSULTING SERVICES, CONSULTING FIRMS, INDIVIDUAL CONSULTANTS), with a
row per activity and a Planned and an Actual date for each step. This module holds STEP's names
for the sections, columns, steps and fixed values, and reads plans two ways:

- From the text (Route A): references_in(text) finds every Activity Reference No. a plan lists, and
  executing_agency(text) the Executing Agency(ies) line. The published text scrambles the tables,
  but each reference still sits at the start of its row, followed by " / " and the description.
- From the tables (Route B): plan_rows(pages) reads the layout parser's tables into one PlanRow per
  activity, with its Step dates. The method comes from the Method column, never from the reference. A
  method a plan writes by an old or a French name, such as STEP's French "Appel d'offres", is stored as
  the current name, with the plan's words beside it (strata.lakehouse.clean.read_method; ticket 42).
  Given the references Route A read, plan_rows writes each row's reference as the plan's text gives it
  where the layout parser misread a letter or two of it (ticket 78).

Fixed values (a review type, a method, a market approach, a procurement process, a contract type
or a process status) are matched to STEP's words without their spaces, because a PDF cell drops
the space where it wraps ("Request for Quota" then "tions").
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from strata.config import load_method_names
from strata.lakehouse import clean
from strata.reader.layout import Table

# An Activity Reference No., such as KE-NWWDA-541055-CW-RFB or NWWDA-WSDP-03-2019-2020.
REFERENCE = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}")

SECTIONS = ("WORKS", "GOODS", "NON CONSULTING SERVICES", "CONSULTING FIRMS", "INDIVIDUAL CONSULTANTS")

# Each STEP column, word for word, and the silver.plan_rows column that holds it.
COLUMNS = {
    "Activity Reference No. / Description": "activity",
    "Loan / Credit No.": "loan_credit_no",
    "Component": "component",
    "Review Type": "review_type",
    "Method": "method",
    "Market Approach": "market_approach",
    "Procurement Process": "procurement_process",
    "Prequalification (Y/N)": "prequalification",
    "High SEA/SH Risk": "high_sea_sh_risk",
    "Procurement Document Type": "procurement_document_type",
    "Contract Type": "contract_type",
    "Estimated Amount (US$)": "estimated_amount_usd",
    "Actual Amount (US$)": "actual_amount_usd",
    "Process Status": "process_status",
}

# STEP's steps, word for word: goods, works and non-consulting services; consulting firms;
# individual consultants. Signed Contract and Contract Completion end all three.
STEPS = (
    "Draft Pre-qualification Documents",
    "Prequalification Evaluation Report",
    "Draft Bidding Document / Justification",
    "Specific Procurement Notice / Invitation",
    "Bidding Documents as Issued",
    "Proposal Submission / Opening / Minutes",
    "Bid Evaluation Report and Recommendation for Award",
    "Terms of Reference",
    "Expression of Interest Notice",
    "Short List and Draft Request for Proposals",
    "Request for Proposals as Issued",
    "Opening of Technical Proposals / Minutes",
    "Evaluation of Technical Proposal",
    "Combined Evaluation Report and Draft Negotiated Contract",
    "Invitation to Identified/Selected Consultant",
    "Draft Negotiated Contract",
    "Signed Contract",
    "Contract Completion",
)
# Older exports print a step under another name.
STEP_ALIASES = {"Teams of Reference": "Terms of Reference"}

# STEP's fixed values, word for word, for the columns that take one.
VALUES = {
    "review_type": ("Prior", "Post"),
    "method": load_method_names().current,  # the method-name registry's current names (config/method_names.toml)
    "market_approach": (
        "Open - International", "Open - National", "Limited - International", "Limited - National",
        "Direct - International", "Direct - National", "Open", "Limited", "Direct",
    ),
    "procurement_process": (
        "Single Stage - One Envelope", "Single Stage - Two Envelope", "Two Stage - One Envelope",
        "Two Stage - Two Envelope",
    ),
    "prequalification": ("Y", "N"),
    "high_sea_sh_risk": ("Y", "N"),
    "contract_type": ("Lump-Sum", "Time-Based"),
    "process_status": (
        "Pending Implementation", "Under Implementation", "Under Review", "Signed", "Completed", "Canceled",
        "Terminated", "Draft",
    ),
}
AMOUNTS = ("estimated_amount_usd", "actual_amount_usd")


def squash(text: str) -> str:
    """Text without spaces, in lower case, for comparing STEP's words with a wrapped cell."""
    return re.sub(r"\s+", "", text).lower()


def tidy(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _known(text: str, known) -> str:
    match = {squash(value): value for value in known}.get(squash(text))
    return match if match is not None else tidy(text)


STEP_NAMES = {squash(name): name for name in STEPS} | {squash(old): new for old, new in STEP_ALIASES.items()}
COLUMN_NAMES = {squash(name): key for name, key in COLUMNS.items()}
SECTION_NAMES = {squash(name): name for name in SECTIONS}


# ── Route A: what a plan's text says ─────────────────────────────────────

_STARTS_A_ROW = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]*){2,}$")  # a reference, perhaps cut short by a wrap
_TAIL = re.compile(r"^([A-Z0-9]*)\s?/(?:\s|$)")
_WHOLE = re.compile(rf"^({REFERENCE.pattern})\s?/(?:\s|$)")


def _left_column(text: str):
    """The first column of each line: lines that start at the left margin, up to a wide gap."""
    for line in text.splitlines():
        if line.strip() and len(line) - len(line.lstrip(" ")) <= 2:
            yield re.split(r"\s{3,}", line.strip())[0]


def references_in(text: str) -> list[str]:
    """Every Activity Reference No. a plan's text lists, once each, in the order it lists them.

    A reference starts a row and is followed by " / " and the description. Where the cell wrapped
    it, its end sits at the start of the next line: "NWWDA-WSDP-03-2019-" then "2020 / Consultancy".
    """
    found: list[str] = []
    lines = list(_left_column(text))
    for i, line in enumerate(lines):
        whole = _WHOLE.match(line)
        if whole:
            reference = whole.group(1)
        elif _STARTS_A_ROW.match(line) and i + 1 < len(lines) and (tail := _TAIL.match(lines[i + 1])):
            reference = line + tail.group(1)
        else:
            continue
        if REFERENCE.fullmatch(reference) and reference not in found:
            found.append(reference)
    return found


def executing_agency(text: str) -> str | None:
    """The plan's Executing Agency(ies) line, which names the implementing agency."""
    match = re.search(r"Executing Agency\(ies\):[ \t]*([^\n]*)", text)
    return tidy(match.group(1)) or None if match else None


# ── Route B: the plan's tables, read into STEP rows ──────────────────────

@dataclass(frozen=True)
class StepDates:
    step: str  # STEP's name for the step, word for word
    step_order: int  # its place in the section's table, from 1
    planned_on: dt.date | None
    actual_on: dt.date | None


@dataclass
class PlanRow:
    section: str
    activity_reference_no: str
    description: str
    pdf_page: int
    fields: dict = field(default_factory=dict)  # silver column -> value, for the STEP columns the table has
    steps: list[StepDates] = field(default_factory=list)
    # The reference and description as the layout parser read them, and what the repair made of them before the row
    # is written (strata.reader.repair; ticket 131). activity_reference_no and description hold the repaired values.
    activity_reference_no_as_read: str | None = None
    reference_repair: str | None = None  # why the reference differs from the reading, or why it is flagged
    reference_carried_by: str | None = None  # the evidence id of the record that carries the reference kept
    description_as_read: str | None = None
    description_joins: tuple = ()  # each strata.reader.repair.Join the repair made

    def __post_init__(self):
        if self.activity_reference_no_as_read is None:
            self.activity_reference_no_as_read = self.activity_reference_no
        if self.description_as_read is None:
            self.description_as_read = self.description


def _date(text: str) -> dt.date | None:
    text = re.sub(r"\s+", "", text)
    try:
        return dt.date.fromisoformat(text) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None
    except ValueError:
        return None


def _amount(text: str) -> Decimal | None:
    text = re.sub(r"\s+", "", text)
    if not re.fullmatch(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", text):
        return None
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


def _value(key: str, text: str):
    if key in AMOUNTS:
        return _amount(text)
    if key == "method":
        return clean.read_method(text).name if text.strip() else None
    if key in VALUES:
        return _known(text, VALUES[key]) if text.strip() else None
    return tidy(text) or None


@dataclass
class Reading:
    """What the STEP tables of one plan gave: its rows, and the columns and rows it could not read."""

    rows: list[PlanRow] = field(default_factory=list)
    unknown_columns: set[str] = field(default_factory=set)
    rows_without_reference: int = 0
    # Each reference the layout parser misread, with the reference the plan's text gives, as (read, written).
    settled: list[tuple[str, str]] = field(default_factory=list)


def plan_rows(pages: list[tuple[int, list[Table]]], listed: Sequence[str] = (), misread_characters: int = 0) -> Reading:
    """Every activity in a plan's STEP tables, one PlanRow each, from (PDF page, tables) pairs.

    A table with no header rows continues the table before it onto a new page, so it is read with
    that table's title and header when it has as many columns.

    listed is every reference the plan's text lists (Route A, references_in). A row whose reference the
    text does not list takes the reference the text gives, when the two differ by at most
    misread_characters characters (see _settle).
    """
    reading, last = Reading(), None
    for pdf_page, tables in pages:
        for table in tables:
            if table.header_rows == 0:
                if last is None or len(last.rows[0]) != len(table.rows[0] if table.rows else ()):
                    reading.rows_without_reference += len(table.rows)
                    continue
                table = Table(last.title, 2, (*last.rows[:2], *table.rows))
            _read_table(table, pdf_page, reading)
            last = table
    reading.settled = _settle(reading.rows, listed, misread_characters)
    return reading


def _changes(read: str, written: str) -> int:
    """How many characters must be added, taken out or changed to turn one reference into the other."""
    previous = list(range(len(written) + 1))
    for i, letter in enumerate(read, 1):
        current = [i]
        for j, other in enumerate(written, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (letter != other)))
        previous = current
    return previous[-1]


def _settle(rows: list[PlanRow], listed: Sequence[str], most: int) -> list[tuple[str, str]]:
    """Each row's Activity Reference No. as the plan's own text writes it, where the layout parser misread it.

    The published text is the PDF's own words, so a reference it lists is the one STEP wrote. The layout
    parser reads the page as an image and can misread a letter: on the workspace on October 26, 2026,
    ai_parse_document read KE-NWWDA-229129-CW-RFB on page 3 of the October 9, 2026 plan as
    KE-NWWDA-229129-CW-RFQ (ticket 78). A row whose reference the text does not list takes the reference
    the text lists and no other row read, when that one is at most `most` characters away and no other such
    reference is as close. Otherwise the row keeps what the parser read: a plan with no text lists nothing,
    and two equally close references give no grounds to choose. Returns each (read, written) pair."""
    written_in_text, read = set(listed), {row.activity_reference_no for row in rows}
    unread = [reference for reference in dict.fromkeys(listed) if reference not in read]
    settled = []
    for row in rows:
        if most <= 0 or not unread or row.activity_reference_no in written_in_text:
            continue
        (fewest, closest), *others = sorted((_changes(row.activity_reference_no, reference), reference)
                                            for reference in unread)
        if fewest > most or (others and others[0][0] == fewest):
            continue
        settled.append((row.activity_reference_no, closest))
        row.activity_reference_no = closest
        unread.remove(closest)
    return settled


def _read_table(table: Table, pdf_page: int, reading: Reading) -> None:
    labels, heads = table.rows[0], table.rows[1]
    section = SECTION_NAMES.get(squash(table.title), tidy(table.title))
    keys: dict[int, str] = {}
    steps: list[tuple[str, int | None, int | None]] = []  # step, Planned column, Actual column
    for index, (label, head) in enumerate(zip(labels, heads)):
        if head in ("Planned", "Actual"):
            name = STEP_NAMES.get(squash(label), tidy(label))
            if not steps or steps[-1][0] != name or steps[-1][1 if head == "Planned" else 2] is not None:
                steps.append((name, None, None))
            step, planned, actual = steps[-1]
            steps[-1] = (step, index, actual) if head == "Planned" else (step, planned, index)
        elif squash(label) in COLUMN_NAMES:
            keys[index] = COLUMN_NAMES[squash(label)]
        elif label.strip():
            reading.unknown_columns.add(tidy(label))
    activity = next((i for i, key in keys.items() if key == "activity"), None)
    if activity is None:
        return
    for cells in table.rows[table.header_rows:]:
        reference, _, description = cells[activity].partition("/")
        reference = re.sub(r"\s+", "", reference)
        if not REFERENCE.fullmatch(reference):
            reading.rows_without_reference += 1 if cells[activity].strip() else 0
            continue
        row = PlanRow(section, reference, tidy(description), pdf_page)
        for index, key in keys.items():
            if key != "activity":
                row.fields[key] = _value(key, cells[index])
            if key == "method" and cells[index].strip():
                # The plan's own words beside the current name (ticket 42): an old or a French name maps to the
                # current Procurement Regulations' name, and one the registry does not list stays as written.
                read = clean.read_method(cells[index])
                row.fields |= {"method_original": read.original, "method_original_lang": read.language,
                               "method_mapped": read.mapped}
        for order, (step, planned, actual) in enumerate(steps, 1):
            row.steps.append(StepDates(step, order,
                                       _date(cells[planned]) if planned is not None else None,
                                       _date(cells[actual]) if actual is not None else None))
        reading.rows.append(row)
