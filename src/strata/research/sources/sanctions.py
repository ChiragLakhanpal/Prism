"""sanctions: whether a supplier on the project's contracts is on the World Bank's listing of ineligible firms and
individuals (ticket 154).

The list's API needs a subscription key, so the reader reads a copy downloaded by hand from the page's export (Export
to Excel on https://www.worldbank.org/en/projects-operations/procurement/debarred-firms), kept as
<settings.folder>/<yyyy-mm-dd>.xlsx or .csv, the date the copy was downloaded. It reads the newest copy dated on or
before the run's day, and checks each named supplier on the project's contracts (strata.gold.contract_supplier and
strata.gold.contract) against each firm on it, by its exact name and by its normalised name: lower case, punctuation
out, and the legal endings the registry lists (Ltd, Limited, S.R.L ...) taken off the end.

It gives one summary item ("<n> suppliers checked against the list of <date>; <m> on it.") and one item per supplier
found, with the firm, the grounds and the dates as the list prints them, and the counts suppliers_checked and
suppliers_sanctioned, which research_evidence's summary record states. With no copy it gives reached False, so the
brief's "could not see" says the check did not run.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path

from strata.config import ResearchSource
from strata.research.items import make_item
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of, long_date, rows

ROOT = Path(__file__).resolve().parents[4]
COPY = re.compile(r"(20\d\d-\d\d-\d\d)\.(xlsx|csv)$")
NO_LIST = "The sanctions check did not run: the list needs a download from the page."
AUTHOR = "World Bank"
# The list's columns, by the titles its export prints.
COLUMNS = {"firm": "Firm Name", "additional": "Additional Firm Info", "address": "Address", "country": "Country",
           "from_date": "From Date", "to_date": "To Date", "grounds": "Grounds"}
SHEET = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXCEL_EPOCH = dt.date(1899, 12, 30)


def newest_copy(folder: Path, day: dt.date) -> tuple[Path, dt.date] | None:
    """The newest downloaded copy dated on or before day, with its date."""
    found = []
    for path in folder.glob("*") if folder.is_dir() else []:
        match = COPY.fullmatch(path.name)
        if match and dt.date.fromisoformat(match.group(1)) <= day:
            found.append((dt.date.fromisoformat(match.group(1)), path.suffix == ".xlsx", path))
    if not found:
        return None
    date, _, path = max(found)
    return path, date


def _column(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    number = 0
    for letter in letters:
        number = number * 26 + ord(letter) - 64
    return number - 1


def _xlsx_rows(path: Path) -> list[list[str]]:
    """The first sheet's rows as text, with only the standard library: shared, inline and plain values."""
    with zipfile.ZipFile(path) as book:
        names = book.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.iter(f"{SHEET}t")) for item in root.iter(f"{SHEET}si")]
        sheet = sorted(name for name in names if name.startswith("xl/worksheets/sheet"))[0]
        root = ElementTree.fromstring(book.read(sheet))
    found = []
    for row in root.iter(f"{SHEET}row"):
        cells: dict[int, str] = {}
        for cell in row.iter(f"{SHEET}c"):
            kind, value = cell.get("t"), cell.findtext(f"{SHEET}v")
            if kind == "s" and value is not None:
                text = shared[int(value)]
            elif kind == "inlineStr":
                text = "".join(node.text or "" for node in cell.iter(f"{SHEET}t"))
            else:
                text = value or ""
            cells[_column(cell.get("r"))] = text
        found.append([cells.get(index, "") for index in range(max(cells, default=-1) + 1)])
    return found


def _csv_rows(path: Path) -> list[list[str]]:
    return list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))


def _date_as_printed(value: str) -> str:
    """A date cell as the list prints it; an Excel serial number becomes its date."""
    text = value.strip()
    if re.fullmatch(r"\d{4,5}(?:\.0+)?", text):
        return long_date(EXCEL_EPOCH + dt.timedelta(days=int(float(text))))
    return text


def listed_firms(path: Path) -> list[dict]:
    """The firms and individuals on a copy, each by the list's columns, read under the header row that holds Firm
    Name (the export prints the ineligibility period's From Date and To Date in the row under it)."""
    table = _xlsx_rows(path) if path.suffix == ".xlsx" else _csv_rows(path)
    header = next((index for index, row in enumerate(table) if COLUMNS["firm"] in [cell.strip() for cell in row]), None)
    if header is None:
        raise ValueError(f"{path.name} has no column {COLUMNS['firm']}.")
    titles: dict[str, int] = {}
    last = header
    for index in range(header, min(header + 3, len(table))):
        for column, cell in enumerate(table[index]):
            for key, title in COLUMNS.items():
                if cell.strip() == title and key not in titles:
                    titles[key] = column
                    last = max(last, index)
    firms = []
    for row in table[last + 1:]:
        value = {key: (row[column].strip() if column < len(row) else "") for key, column in titles.items()}
        if value.get("firm"):
            for key in ("from_date", "to_date"):
                value[key] = _date_as_printed(value.get(key, ""))
            firms.append(value)
    return firms


def normalised(name: str, endings: tuple[str, ...]) -> str:
    """A name without case, punctuation or the legal endings at its end: China Railway No.10 Engineering Group Co.,
    Ltd. is "china railway no 10 engineering group"."""
    text = " ".join(re.sub(r"[^\w\s]", " ", name.lower().replace("&", " and ")).split())
    ordered = sorted(endings, key=len, reverse=True)
    changed = True
    while changed and text:
        changed = False
        for ending in ordered:
            if text == ending:
                break
            if text.endswith(" " + ending):
                text, changed = text[: -len(ending) - 1].strip(), True
                break
    return text


def matches(suppliers: list[dict], firms: list[dict], endings: tuple[str, ...]) -> list[tuple[dict, dict, str]]:
    """Each supplier found on the list, with the firm it matched and how: "exact" or "normalised"."""
    exact = {firm["firm"].strip(): firm for firm in firms}
    loose: dict[str, dict] = {}
    for firm in firms:
        loose.setdefault(normalised(firm["firm"], endings), firm)
    found = []
    for supplier in suppliers:
        name = supplier["name"].strip()
        if name in exact:
            found.append((supplier, exact[name], "exact"))
        elif (key := normalised(name, endings)) and key in loose:
            found.append((supplier, loose[key], "normalised"))
    return found


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    day = as_of(now)
    copy = newest_copy(ROOT / source.settings.get("folder", "data/research/sanctions"), day)
    if copy is None:
        return SourceResult(source.key, [], False, "no list", NO_LIST)
    if engine is None:
        return SourceResult(source.key, [], False, "unreadable",
                            "The sanctions check did not run: Prism could not read the project's contracts.")
    path, listed_on = copy
    firms = listed_firms(path)
    every = rows(engine, "project_suppliers", project_id=project.project_id, as_of=day)
    suppliers = list({row["supplier_id"]: row for row in every if (row["name"] or "").strip()}.values())
    unnamed = len({row["supplier_id"] for row in every}) - len(suppliers)
    endings = tuple(source.settings.get("legal_endings", ()))
    found = matches(suppliers, firms, endings)
    date = long_date(listed_on)
    summary = f"{len(suppliers)} suppliers checked against the list of {date}; {len(found)} on it."
    if unnamed:
        summary += (f" {unnamed} suppliers have no name in the project's contract records, so they were not "
                    "checked.")
    items = [make_item(project=project, source=source, item_key=f"summary-{listed_on.isoformat()}",
                       public_from=listed_on, published=listed_on, title=f"Sanctions check against the list of {date}",
                       text=summary, url=source.endpoint, read_on=day, author=AUTHOR)]
    for supplier, firm, how in found:
        words = [f"Firm Name: {firm['firm']}.",
                 f"Additional Firm Info: {firm['additional']}." if firm.get("additional") else "",
                 f"Country: {firm['country']}." if firm.get("country") else "",
                 f"Ineligibility Period: From Date {firm.get('from_date') or 'not printed'}, To Date "
                 f"{firm.get('to_date') or 'not printed'}.",
                 f"Grounds: {firm['grounds']}." if firm.get("grounds") else "",
                 f"The project's supplier {supplier['name'].strip()} matches it by its {how} name."]
        items.append(make_item(
            project=project, source=source, item_key=f"hit-{supplier['supplier_id']}", public_from=listed_on,
            published=listed_on, title=f"{firm['firm']}, on the list of {date}",
            text=" ".join(word for word in words if word), url=source.endpoint, read_on=day, author=AUTHOR))
    note = f"{len(suppliers)} suppliers checked against the list of {date}; {len(found)} on it."
    return SourceResult(source.key, items, True, "read", note,
                        counts={"suppliers_checked": len(suppliers), "suppliers_sanctioned": len(found)})
