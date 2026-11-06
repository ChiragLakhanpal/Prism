"""Reading an implementing agency's upload of its Procurement Plan into STEP rows (ticket 38).

An upload is an Excel file (.xlsx) or a CSV file. Every sheet is read, and on each the reader finds every table
by its header row: a row that names STEP's columns (src/strata/reader/step_columns.py), with each step's Planned
and Actual dates either in a second header row under the step's name, as STEP's published plans print them, or in
one header row as "{step} (Planned)". A row above a table that holds only a section's name, such as WORKS, names
the section its activities belong to, as in the published plans; so does a sheet named for a section. Activities
are joined in sheet order, then row order, and keep that order as their position.

Values are read by the parsers the plan reader uses for published plans: dates by strata.lakehouse.clean.parse_date
(ISO dates, 09-Oct-2026 and Excel's own dates), amounts by strata.reader.step's, and STEP's fixed values matched to
STEP's words. A value that will not read becomes a data note on its row, never a guess. A row with no Method gets
one too, since its steps cannot be chosen, and so does each row whose reference another row repeats.

Nothing here keeps anything. read_upload returns the rows or raises UploadError with the code the reading page
says, so the route can keep nothing when a reading fails. An Excel file is read with the standard library and
defusedxml, so a file cannot make the parser fetch anything or expand without limit.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath

from defusedxml import ElementTree

from strata.config import Uploads
from strata.lakehouse.clean import parse_date
from strata.reader.step import AMOUNTS, REFERENCE, SECTION_NAMES, VALUES, _amount, _known, squash, tidy
from strata.reader.step_columns import ACTUAL, DESCRIPTION, NAMES, PLANNED, Registry
from strata.reader.step_columns import REFERENCE as REFERENCE_HALF

ACTIVITY = "activity"
EXCEL_EPOCH = dt.date(1899, 12, 30)  # day 0 of Excel's dates on Windows and Mac since 2011
EXCEL_DAYS = range(20_000, 80_000)  # 1954 to 2119: a number in a date column outside these is not a date
LONGEST_NUMBER = 30  # an Excel number with more digits than this before or after the point is read as its text
ONE_ROW_STEP = re.compile(r"^(?P<step>.+?)\s*[(\[:-]?\s*(?P<head>planned|actual)\s*[)\]]?$", re.I)
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DOC_RELS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


class UploadError(Exception):
    """Why a file could not be read and checked, with the values its sentence names."""

    def __init__(self, code: str, **details):
        super().__init__(code)
        self.code, self.details = code, details


@dataclass
class UploadRow:
    """One activity as the officer's file gives it: its STEP values typed, and each step's two dates by STEP's name."""

    position: int  # from 1, in the file's order
    sheet: str | None
    section: str | None
    reference: str | None
    description: str | None
    fields: dict = field(default_factory=dict)  # descriptive column key -> value
    steps: dict = field(default_factory=dict)  # step name -> {"planned": date or None, "actual": date or None}
    notes: list = field(default_factory=list)  # data notes: {"code", and "column" and "value", or "ref"}
    # Each descriptive column's cell as the file writes it, which the STEP rows CSV copies unchanged.
    raw: dict = field(default_factory=dict)


@dataclass
class Reading:
    rows: list[UploadRow]
    sheets: list[str]  # the sheets activities were read from, in order
    used: list[dict]  # each header the reading used: {"header": the file's words, "as": STEP's name or None}
    unused: list[str]  # each header it did not use


# ── The file's sheets, as rows of cells ──────────────────────────────────

def _csv_sheets(data: bytes) -> list[tuple[str | None, list[list]]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="strict")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [(None, [list(row) for row in csv.reader(io.StringIO(text), dialect)])]


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def _xlsx_sheets(data: bytes, limits: Uploads) -> list[tuple[str | None, list[list]]]:
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        if sum(info.file_size for info in book.infolist()) > limits.max_unzipped_bytes:
            raise UploadError("unreadable")
        names = set(book.namelist())

        def xml(path: str):
            return ElementTree.fromstring(book.read(path))

        shared = []
        if "xl/sharedStrings.xml" in names:
            for item in xml("xl/sharedStrings.xml").iter(f"{MAIN}si"):
                shared.append("".join(text.text or "" for text in item.iter(f"{MAIN}t")))
        targets = {rel.get("Id"): rel.get("Target") for rel in xml("xl/_rels/workbook.xml.rels").iter(f"{RELS}Relationship")}
        sheets = []
        for sheet in xml("xl/workbook.xml").iter(f"{MAIN}sheet"):
            target = targets.get(sheet.get(f"{DOC_RELS}id"), "")
            path = target.lstrip("/") if target.startswith("/") else str(PurePosixPath("xl") / target)
            if path not in names:
                continue
            rows: list[list] = []
            for row in xml(path).iter(f"{MAIN}row"):
                cells: dict[int, object] = {}
                for position, cell in enumerate(row.iter(f"{MAIN}c")):
                    index = _column_index(cell.get("r")) if cell.get("r") else position
                    if index >= limits.max_columns:  # past the last column Prism reads
                        continue
                    kind, value = cell.get("t"), cell.find(f"{MAIN}v")
                    if kind == "inlineStr":
                        cells[index] = "".join(text.text or "" for text in cell.iter(f"{MAIN}t"))
                    elif value is None or value.text is None:
                        continue
                    elif kind == "s":
                        cells[index] = shared[int(value.text)]
                    elif kind in ("str", "e", "b"):
                        cells[index] = value.text
                    else:
                        try:
                            number = Decimal(value.text)
                        except InvalidOperation:
                            cells[index] = value.text
                        else:  # infinity, not-a-number and a number too long to write stay as the cell's text
                            readable = number.is_finite() and abs(number.adjusted()) <= LONGEST_NUMBER
                            cells[index] = number if readable else value.text
                rows.append([cells.get(index) for index in range(max(cells) + 1)] if cells else [])
            sheets.append((sheet.get("name"), rows))
        return sheets


def sheets_of(file_name: str, data: bytes, limits: Uploads) -> list[tuple[str | None, list[list]]]:
    """Each sheet of the file, with its rows of cells: text, a Decimal for an Excel number, or None."""
    try:
        if file_name.lower().endswith(".xlsx"):
            return _xlsx_sheets(data, limits)
        return _csv_sheets(data)
    except UploadError:
        raise
    except (zipfile.BadZipFile, KeyError, ValueError, OSError, ElementTree.ParseError, UnicodeDecodeError) as error:
        raise UploadError("unreadable") from error
    except Exception as error:  # defusedxml refuses a file that defines entities, and anything else malformed
        raise UploadError("unreadable") from error


# ── The tables in a sheet ────────────────────────────────────────────────

def _text(cell) -> str:
    if cell is None:
        return ""
    if isinstance(cell, Decimal):
        return format(cell.normalize(), "f") if cell == cell.to_integral_value() else str(cell)
    return tidy(str(cell))


def _section(cells: list) -> str | None:
    """The section a row names when it holds nothing but a section's name, as above each published table."""
    filled = [_text(cell) for cell in cells if _text(cell)]
    return SECTION_NAMES.get(squash(filled[0])) if len(filled) == 1 else None


@dataclass
class Header:
    columns: dict[int, str]  # cell index -> descriptive key, activity_reference_no or description
    steps: dict[int, tuple[str, str]]  # cell index -> (step name, Planned or Actual)
    used: list[dict]
    unused: list[str]
    rows: int  # how many header rows: 1, or 2 when Planned and Actual sit under the step names


def _header(cells: list, below: list | None, registry: Registry) -> Header | None:
    """The header a row starts, or None. A header row names the activity column, or its Description half."""
    names, step_names = registry.header_names(), registry.step_names()
    texts = [_text(cell) for cell in cells]
    found = {index: names[squash(text)] for index, text in enumerate(texts) if text and squash(text) in names}
    if not {ACTIVITY, DESCRIPTION} & set(found.values()):
        return None
    heads = [_text(cell).lower() for cell in (below or [])]
    two_rows = any(head in ("planned", "actual") for head in heads)
    steps: dict[int, tuple[str, str]] = {}
    if two_rows:
        current = None
        for index in range(max(len(texts), len(heads))):
            text = texts[index] if index < len(texts) else ""
            if text and squash(text) in step_names:
                current = step_names[squash(text)]
            elif text:
                current = None
            head = heads[index] if index < len(heads) else ""
            if current and head in ("planned", "actual"):
                steps[index] = (current, PLANNED if head == "planned" else ACTUAL)
    else:
        for index, text in enumerate(texts):
            match = ONE_ROW_STEP.match(text) if index not in found else None
            if match and squash(match["step"]) in step_names:
                steps[index] = (step_names[squash(match["step"])], PLANNED if match["head"].lower() == "planned" else ACTUAL)
    used, unused = [], []
    for index, text in enumerate(texts):
        if not text:
            continue
        if index in found:
            key = found[index]
            name = NAMES.get(key) or dict(zip((REFERENCE_HALF, DESCRIPTION), registry.halves))[key]
            used.append({"header": text, "as": None if squash(text) == squash(name) else name})
        elif two_rows and squash(text) in step_names:  # a step's name above its Planned and Actual
            name = step_names[squash(text)]
            used.append({"header": text, "as": None if squash(text) == squash(name) else name})
        elif index in steps:
            step, head = steps[index]
            name = registry.step_header(step, head)
            used.append({"header": text, "as": None if squash(text) == squash(name) else name})
        else:
            unused.append(text)
    return Header(found, steps, used, unused, 2 if two_rows else 1)


def _missing(header: Header) -> list[str]:
    keys = set(header.columns.values())
    missing = []
    if not {ACTIVITY, DESCRIPTION} & keys:
        missing.append(NAMES[ACTIVITY])
    if "method" not in keys:
        missing.append(NAMES["method"])
    return missing


# ── Values ───────────────────────────────────────────────────────────────

def _date(cell) -> tuple[dt.date | None, bool]:
    """A step's date and whether the cell read: an Excel day number, or any date the sources write."""
    if cell is None or _text(cell) == "":
        return None, True
    if isinstance(cell, Decimal):
        try:
            day = int(cell) if cell == cell.to_integral_value() else None
        except (InvalidOperation, ValueError, OverflowError):
            return None, False
        if day is not None and day in EXCEL_DAYS:
            return EXCEL_EPOCH + dt.timedelta(days=day), True
        return None, False
    found = parse_date(_text(cell))
    return found, found is not None


def _value(key: str, cell) -> tuple[object, bool]:
    """A descriptive column's value and whether it read."""
    text = _text(cell)
    if not text:
        return None, True
    if key in AMOUNTS:
        found = cell if isinstance(cell, Decimal) else _amount(text)
        if found is None:
            return None, False
        try:  # an amount longer than a Decimal's 28 places, such as a pasted ID number, will not read
            return found.quantize(Decimal("0.01")), True
        except (InvalidOperation, ValueError, OverflowError):
            return None, False
    if key in VALUES:
        return _known(text, VALUES[key]), True
    return text, True


def _activity(text: str) -> tuple[str | None, str | None]:
    """STEP's one activity column: the reference before " / ", then the Description. A cell with no reference is
    all Description."""
    reference, slash, description = text.partition("/")
    squashed = re.sub(r"\s+", "", reference)
    if slash and REFERENCE.fullmatch(squashed):
        return squashed, tidy(description) or None
    if slash and not squashed:
        return None, tidy(description) or None
    return None, tidy(text) or None


def _row(cells: list, header: Header, position: int, sheet: str | None, section: str | None,
         headers: list[str]) -> UploadRow | None:
    def cell(index: int):
        return cells[index] if index < len(cells) else None

    reference = description = None
    fields: dict = {}
    notes: list = []
    raw = {key: _text(cell(index)) for index, key in header.columns.items() if key not in (ACTIVITY, REFERENCE_HALF,
                                                                                          DESCRIPTION)}
    for index, key in header.columns.items():
        if key == ACTIVITY:
            reference, description = _activity(_text(cell(index)))
        elif key == REFERENCE_HALF:
            reference = re.sub(r"\s+", "", _text(cell(index))) or None
        elif key == DESCRIPTION:
            description = _text(cell(index)) or None
        else:
            value, read = _value(key, cell(index))
            fields[key] = value
            if not read:
                notes.append({"code": "unread_amount", "column": headers[index], "value": _text(cell(index))})
    if reference is None and description is None:
        return None
    steps: dict = {}
    for index, (step, head) in header.steps.items():
        day, read = _date(cell(index))
        steps.setdefault(step, {"planned": None, "actual": None})[head.lower()] = day
        if not read:
            notes.append({"code": "unread_date", "column": headers[index], "value": _text(cell(index))})
    if not fields.get("method"):
        notes.append({"code": "no_method"})
    return UploadRow(position, sheet, section, reference, description, fields, steps, notes, raw)


def read_upload(file_name: str, data: bytes, registry: Registry) -> Reading:
    """Every activity the file lists, in its order, or UploadError with the reason none could be kept."""
    limits = registry.uploads
    ending = PurePosixPath(file_name.lower()).suffix
    if ending not in limits.accept:
        raise UploadError("type", extension=ending or None)
    if not data:
        raise UploadError("empty")
    if len(data) > limits.max_size_bytes:
        raise UploadError("size", size=len(data), max_size=limits.max_size_bytes)
    rows: list[UploadRow] = []
    sheets: list[str] = []
    used: list[dict] = []
    unused: list[str] = []
    found_header = False
    for sheet, cells in sheets_of(file_name, data, limits):
        section = SECTION_NAMES.get(squash(sheet)) if sheet else None
        index = 0
        while index < len(cells):
            named = _section(cells[index])
            if named:
                section, index = named, index + 1
                continue
            header = _header(cells[index], cells[index + 1] if index + 1 < len(cells) else None, registry)
            if header is None:
                index += 1
                continue
            found_header = True
            missing = _missing(header)
            if missing:
                raise UploadError("missing_columns", missing=missing)
            headers = [_text(cell) for cell in cells[index]]
            if header.rows == 2:  # name a step column by its step and its head, as the one-row layout does
                for column, (step, head) in header.steps.items():
                    while len(headers) <= column:
                        headers.append("")
                    headers[column] = registry.step_header(step, head)
            used += [entry for entry in header.used if entry not in used]
            unused += [text for text in header.unused if text not in unused]
            index += header.rows
            while index < len(cells):
                if not any(_text(cell) for cell in cells[index]):
                    index += 1
                    break
                if _section(cells[index]) or _header(cells[index], None, registry):
                    break
                row = _row(cells[index], header, len(rows) + 1, sheet, section, headers)
                if row is not None:
                    rows.append(row)
                    if sheet is not None and sheet not in sheets:
                        sheets.append(sheet)
                index += 1
    if not found_header:
        raise UploadError("no_table")
    if not rows:
        raise UploadError("no_rows")
    if len(rows) > limits.max_rows:
        raise UploadError("too_many_rows", n=len(rows), max_rows=limits.max_rows)
    seen: dict[str, int] = {}
    for row in rows:
        if row.reference:
            seen[row.reference] = seen.get(row.reference, 0) + 1
    for row in rows:
        if row.reference and seen[row.reference] > 1:
            row.notes.append({"code": "duplicate_ref", "ref": row.reference})
    return Reading(rows, sheets, used, unused)
