"""Route B for the documents the passage reader reads (ticket 18): the pages the page router sent to
the layout parser, parsed once under the daily page cap, and read into passages.

The page router (src/strata/reader/passages.py) sends a page to Route B when the published text
cannot be trusted with it: every page of a scan, a report's data sheet, a PAD's risk table, and a page
with no text, such as a figure. For each project of the run, waiting() lists those pages and
plans.parse_pages parses them, the same step the plan reader uses, so both readers share one daily
page cap and one parse-once key (document, PDF page, text hash). A document longer than the layout
parser takes at once (ingestion.parser_part_pages) is read in parts: the live parser gets one page at
a time, so each part's pages go one by one, every page keeps its number in the whole PDF, and the page
routes record each page's part.

Then read() turns what the parser read into passages:

- A scan's pages are read like published text, page by page from the parser's text, so a scanned
  PAD keeps its numbered paragraphs, with the PDF page of each. These passages are paragraphs read
  by the layout parser from a scanned page.
- The pages of a table (a data sheet, a risk table) give one passage per row, each row's cells
  labelled by the table's column heads, and one summary passage per table, which Strata writes and
  which never backs a number (src/strata/reader/tables.py).
- A page with no published text, such as a figure, gives the parser's text blocks, each a passage
  Strata numbers.

A page the parser has not read yet (the cap stopped the run, or it failed today) gives nothing, and
the next run reads it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from strata.lakehouse.engine import Engine
from strata.lakehouse.plans import WaitingPage
from strata.reader import passages as route_a
from strata.reader import tables as table_reader
from strata.reader.layout import Layout, Table, tables_from_json
from strata.reader.templates import Template

PAGE_HASHES = """
SELECT pdf_page, page_hash, text FROM strata.bronze.document_pages WHERE document_id = :document_id ORDER BY pdf_page
"""
LAYOUTS = """
SELECT pdf_page, page_hash, tables, text, figures FROM strata.bronze.layout_pages WHERE document_id = :document_id
ORDER BY parsed_at
"""


def page_texts(engine: Engine, document_id: str) -> list[tuple[int, str, str]]:
    """Each PDF page of a document as bronze holds it: its number, the hash of its text and its text."""
    return [(int(n), str(h), t or "") for n, h, t in engine.run(PAGE_HASHES, {"document_id": document_id}).rows]


def part_of(pdf_page: int, part_pages: int) -> int:
    """The part of a long document a page is read in, from 1: pages 1 to part_pages are part 1."""
    return (pdf_page - 1) // part_pages + 1


def parts(pdf_pages: int, part_pages: int) -> int:
    """How many parts a document of pdf_pages is read in."""
    return max(1, part_of(pdf_pages, part_pages)) if pdf_pages else 1


def waiting(document_id: str, project_id: str, pdf_url: str, public_from, routes, hashes: dict[int, str]) -> list[WaitingPage]:
    """The pages of one document the router sent to Route B, in page order, so a long document's
    parts go one after the other."""
    return [WaitingPage(document_id, project_id, pdf_url, route.pdf_page, hashes[route.pdf_page], public_from)
            for route in routes if route.route == route_a.ROUTE_B and route.pdf_page in hashes]


def layouts(engine: Engine, document_id: str, hashes: dict[int, str]) -> dict[int, Layout]:
    """What the layout parser read on each page of a document, for the pages whose text has not changed
    since it read them."""
    found = {}
    for number, digest, tables, text, figures in engine.run(LAYOUTS, {"document_id": document_id}).rows:
        if hashes.get(int(number)) == str(digest):
            found[int(number)] = Layout(tuple(tables_from_json(tables)), text or "", int(figures or 0))
    return found


def read_well(layout: Layout | None) -> bool:
    """Whether the parser recovered something from a page: a table, or text."""
    return layout is not None and (bool(layout.tables) or bool(layout.text.strip()))


@dataclass(frozen=True)
class TablePassage:
    """A table's row, or its summary, as a passage."""

    key: str
    kind: str
    table: table_reader.WholeTable
    row: table_reader.Row | None
    text: str
    pdf_page: int
    last_pdf_page: int


@dataclass(frozen=True)
class Reading:
    """What Route B gave one document: its page routes, with the paragraph numbering and passages the
    parser's text gave, its paragraphs, and its tables' rows and summaries."""

    routes: tuple[route_a.PageRoute, ...]
    paragraphs: tuple[route_a.Passage, ...]
    tables: tuple[TablePassage, ...]


def read(routes: tuple[route_a.PageRoute, ...], found: dict[int, Layout], template: Template, max_tokens: int,
         document_type: str) -> Reading:
    """One document's Route B pages read into passages. routes are the router's, found what the parser
    read on each page."""
    paragraphs: list[route_a.Passage] = []
    by_page = {route.pdf_page: route for route in routes}
    scan = any(route.reason in (route_a.SCANNED, route_a.NOT_PAGED) for route in routes)
    if scan:
        # A scan read page by page from the parser's text, as published text is read, so its numbered
        # paragraphs keep their numbers and pages. Its table pages are read as tables, below.
        texts = [found[n].text if n in found and by_page[n].reason not in route_a.TABLE_REASONS else ""
                 for n in range(1, len(routes) + 1)]
        scanned = route_a.read(route_a.PAGE_BREAK.join(texts), len(routes), template, max_tokens)
        paragraphs += scanned.passages
        numbered = {page.pdf_page: page for page in scanned.pages}
        routes = tuple(replace(route, printed_page=numbered[route.pdf_page].printed_page,
                               numbering_found=numbered[route.pdf_page].numbering_found,
                               passages=numbered[route.pdf_page].passages) for route in routes)
    else:
        # A page with no published text, such as a figure: each of the parser's text blocks, numbered by Strata.
        for route in routes:
            if route.reason == route_a.NO_TEXT and route.pdf_page in found:
                blocks = [route_a.words(block) for block in found[route.pdf_page].text.split("\n\n")]
                for number, block in enumerate((block for block in blocks if block), 1):
                    paragraphs.append(route_a.Passage(f"p{route.pdf_page}.{number}", "", f"p{route.pdf_page}.{number}",
                                                      False, 1, 1, route.pdf_page, route.pdf_page, None, block,
                                                      route_a.tokens(block)))
    pages: list[tuple[int, list[Table]]] = [(n, list(found[n].tables)) for n in sorted(found)
                                            if by_page.get(n) and by_page[n].reason in route_a.TABLE_REASONS]
    tables: list[TablePassage] = []
    keys: set[str] = set()
    for table in table_reader.read(pages):
        key = table.key
        while key in keys:
            key += "b"
        keys.add(key)
        tables.append(TablePassage(key, route_a.TABLE_SUMMARY, table, None, table_reader.summary(table, document_type),
                                   table.pdf_page, table.last_pdf_page))
        tables += [TablePassage(f"{key}.{row.number}", route_a.TABLE_ROW, table, row, row.text, row.pdf_page,
                                row.last_pdf_page) for row in table.rows]
    rows_on = {}
    for passage in tables:
        rows_on[passage.pdf_page] = rows_on.get(passage.pdf_page, 0) + 1
    routes = tuple(replace(route, passages=route.passages + rows_on.get(route.pdf_page, 0))
                   if route.route == route_a.ROUTE_B else route for route in routes)
    return Reading(routes, tuple(paragraphs), tuple(tables))


def cells_json(row: table_reader.Row | None) -> str | None:
    """A table row's cells as silver.passages keeps them: [[column head, value], ...]."""
    return None if row is None else json.dumps([list(cell) for cell in row.cells], ensure_ascii=False)
