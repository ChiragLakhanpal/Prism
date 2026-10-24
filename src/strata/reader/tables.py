"""Route B's tables read into typed rows and one summary passage each (docs/PLAN.md section 5).

The layout parser returns each table on a page as a grid (src/strata/reader/layout.py). A table can
run over several pages: a PAD's risk table, for one, runs over its whole annex, and a risk that
starts at the foot of a page carries on at the top of the next with no name or rating of its own.
read() joins the pages of one document's tables into whole tables, each with its rows, and each row
with its cells labelled by the table's column heads, so a citation can point at one row.

Each table also gets one summary passage, which says what the table is and names its rows. Strata
writes the summary, not the document, so it never backs a number (spec, "Reading documents"): the
verifier (src/strata/agent/verifier.py) never lets a number rest on it alone.
"""

from __future__ import annotations

from dataclasses import dataclass

from strata.reader.layout import RISK_HEAD, Table


@dataclass(frozen=True)
class Row:
    number: int  # from 1, in the table's order
    cells: tuple[tuple[str, str], ...]  # (column head, value), in the table's column order, blanks left out
    pdf_page: int  # the PDF page the row starts on
    last_pdf_page: int  # the PDF page it ends on

    @property
    def text(self) -> str:
        """The row as one passage's text: each column head with its value, in order."""
        return "; ".join(f"{label}: {value}" for label, value in self.cells)

    def value(self, label: str) -> str:
        return next((value for head, value in self.cells if head == label), "")


@dataclass(frozen=True)
class WholeTable:
    title: str
    columns: tuple[str, ...]
    rows: tuple[Row, ...]
    pdf_page: int  # the PDF page the table starts on
    last_pdf_page: int
    risk: bool  # a risk table, whose rows each name a risk and its rating

    @property
    def key(self) -> str:
        """The table's key in its document: table and the PDF page it starts on, such as table65."""
        return f"table{self.pdf_page}"


def _heads(table: Table) -> tuple[str, ...]:
    """Each column's head: its header rows' words joined, top to bottom."""
    if table.header_rows == 0:
        return tuple(f"Column {n}" for n in range(1, len(table.rows[0]) + 1)) if table.rows else ()
    heads = []
    for column in range(len(table.rows[0])):
        parts = [row[column] for row in table.rows[:table.header_rows] if column < len(row) and row[column]]
        heads.append(" ".join(dict.fromkeys(parts)))
    return tuple(heads)


def read(pages: list[tuple[int, list[Table]]]) -> list[WholeTable]:
    """One document's tables from (PDF page, tables) pairs in page order, each table whole. A table
    on the next page with the same title and column heads carries on the one before it, and a row
    with an empty first cell at its top carries on that table's last row."""
    found: list[dict] = []
    for pdf_page, tables in pages:
        for table in tables:
            if not table.rows:
                continue
            heads = _heads(table)
            body = table.rows[table.header_rows:]
            last = found[-1] if found else None
            same = (last is not None and last["title"] == table.title and last["columns"] == heads
                    and last["last_pdf_page"] in (pdf_page - 1, pdf_page))
            if not same:
                last = {"title": table.title, "columns": heads, "rows": [], "pdf_page": pdf_page,
                        "last_pdf_page": pdf_page, "risk": tuple(heads) == RISK_HEAD}
                found.append(last)
            last["last_pdf_page"] = pdf_page
            for cells in body:
                cells = tuple(cell.strip() for cell in cells)
                if not any(cells):
                    continue
                if not cells[0] and last["rows"]:  # the end of a row the page before began
                    previous = last["rows"][-1]
                    previous["cells"] = [" ".join(part for part in (old, new) if part)
                                         for old, new in zip(previous["cells"], cells)]
                    previous["last_pdf_page"] = pdf_page
                    continue
                last["rows"].append({"cells": list(cells), "pdf_page": pdf_page, "last_pdf_page": pdf_page})
    tables = []
    for table in found:
        rows = tuple(Row(number, tuple((label, value) for label, value in zip(table["columns"], row["cells"])
                                       if value), row["pdf_page"], row["last_pdf_page"])
                     for number, row in enumerate(table["rows"], 1))
        if rows:
            tables.append(WholeTable(table["title"], table["columns"], rows, table["pdf_page"],
                                     table["last_pdf_page"], table["risk"]))
    return tables


def _listed(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def summary(table: WholeTable, document_type: str) -> str:
    """The table's one summary passage, in Strata's words: what the table is, where, its columns and
    the first cell of each row (with a risk's rating). It is never the document's own words; its kind,
    table_summary, says so, and the evidence drawer's caption says who wrote it, so the text starts with
    the table (design review r2 P2)."""
    pages = (f"PDF page {table.pdf_page}" if table.pdf_page == table.last_pdf_page
             else f"PDF pages {table.pdf_page} to {table.last_pdf_page}")
    titled = f" is titled {table.title}. It has" if table.title else " has"
    named = [f"{row.cells[0][1]} ({row.value('Rating')})" if table.risk and row.value("Rating")
             else row.cells[0][1] for row in table.rows if row.cells]
    rows = "one row" if len(table.rows) == 1 else f"{len(table.rows)} rows"
    return (f"The table on {pages} of the {document_type}{titled} {rows} and the columns "
            f"{_listed(list(table.columns))}. Its rows: {'; '.join(named)}.")
