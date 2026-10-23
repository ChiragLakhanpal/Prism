"""Route B: the layout parser, which reads the tables on one PDF page.

The page router sends a page here when it holds a table that the published text scrambles, such as
the STEP table of a Procurement Plan (docs/PLAN.md section 5). A parser returns each table on the
page as a grid: its header rows first, then one row per table row, each row with one cell per
column. Each parser has a name, which the run records with every page it reads. A parser raises
ParseFailed for a page it cannot read; the run records the page and goes on to the next one.

- RecordedLayout, offline. The fixture records every word on each plan's PDF pages with its box
  (data/fixture/recorded/documents/<project>/<name>.words.json). This parser finds each table from
  its line of "Planned" and "Actual" column heads, takes the other columns from the gaps between
  words, and joins the words of each cell. It reads the layout of STEP's plan export, and it
  stands in for ai_parse_document so that the gate needs no workspace.
- AiParseDocument, live. It puts the one page, as a PDF of its own, in a volume and runs
  ai_parse_document on the SQL warehouse, then reads each table element's HTML into a grid.

A PDF cell wraps its text at the cell's edge, sometimes inside a word, and the PDF keeps no space at
the wrap. Joining a cell's lines therefore keeps a space at each wrap, as the published text does,
except where a number or a date wraps ("1,245,092.7" then "6") or a word ends in a hyphen. The STEP
reader (step.py) compares fixed values, such as a method or a status, without their spaces.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

PLANNED_ACTUAL = ("Planned", "Actual")


@dataclass(frozen=True)
class Table:
    """One table on a page: the line above it, its header rows, then its rows, one cell per column."""

    title: str
    header_rows: int
    rows: tuple[tuple[str, ...], ...]

    def as_dict(self) -> dict:
        return {"title": self.title, "header_rows": self.header_rows, "rows": [list(row) for row in self.rows]}

    @classmethod
    def from_dict(cls, data: dict) -> Table:
        return cls(data["title"], data["header_rows"], tuple(tuple(row) for row in data["rows"]))


def tables_to_json(tables: list[Table]) -> str:
    return json.dumps({"tables": [table.as_dict() for table in tables]}, ensure_ascii=False)


def tables_from_json(text: str) -> list[Table]:
    return [Table.from_dict(table) for table in json.loads(text)["tables"]]


@dataclass(frozen=True)
class Page:
    """One PDF page to read: the document it belongs to, where its PDF is, and its number from 1."""

    document_id: str
    pdf_url: str
    pdf_page: int


class ParseFailed(RuntimeError):
    """A page the layout parser could not read."""


class LayoutParser(Protocol):
    name: str

    def parse(self, page: Page) -> list[Table]:
        """The tables on one page. Raises ParseFailed when it cannot read the page."""


def https(url: str) -> str:
    """The same address over https, which is how the World Bank's hosts answer today."""
    return re.sub(r"^http://", "https://", url.strip())


# ── Offline: the tables from the recorded words ──────────────────────────

Word = tuple[float, float, float, float, str]  # x0, y0, x1, y1, text, in points from the top left


class RecordedLayout:
    """The layout parser's offline stand-in, which reads tables from each plan's recorded words."""

    name = "recorded words (pdftotext -bbox)"

    def __init__(self, manifest):
        self.files = {https(source.pdf_url): manifest.recorded / f"{source.file}.words.json"
                      for source in manifest.sources if source.words}

    def parse(self, page: Page) -> list[Table]:
        path = self.files.get(https(page.pdf_url))
        if path is None:
            raise LookupError(f"The fixture has no recorded words for {page.pdf_url}. Mark its source "
                              "words = true in data/fixture/sources.toml and record it again.")
        pages = _recorded_tables(path)
        if not 1 <= page.pdf_page <= len(pages):
            raise LookupError(f"{page.pdf_url} has {len(pages)} pages, so it has no page {page.pdf_page}.")
        return list(pages[page.pdf_page - 1])


@lru_cache(maxsize=64)
def _recorded_tables(path: Path) -> tuple[tuple[Table, ...], ...]:
    return tuple(tuple(tables) for tables in read_pages(_recorded_pages(path)))


@lru_cache(maxsize=64)
def _recorded_pages(path: Path) -> tuple[tuple[Word, ...], ...]:
    response = json.loads(Path(path).read_text())["response"]
    pages = []
    for page in response["pages"]:
        words = []
        for line in page["words"]:
            x0, y0, x1, y1, text = line.split(" ", 4)
            words.append((float(x0), float(y0), float(x1), float(y1), text))
        pages.append(tuple(words))
    return tuple(pages)


def _lines(words, tolerance: float = 1.0) -> list[tuple[float, list[Word]]]:
    """Words on the same baseline, top to bottom, each line left to right."""
    lines: list[list] = []
    for word in sorted(words, key=lambda w: (w[1], w[0])):
        if lines and abs(lines[-1][0] - word[1]) <= tolerance:
            lines[-1][1].append(word)
        else:
            lines.append([word[1], [word]])
    return [(top, sorted(line)) for top, line in lines]


def _space(words) -> float:
    """The page's commonest gap between two words on one line: the width of a space."""
    gaps = Counter(round(b[0] - a[2], 1) for _, line in _lines(words) for a, b in zip(line, line[1:])
                   if 0 < b[0] - a[2] < 5)
    return gaps.most_common(1)[0][0] if gaps else 1.0


def _spans(ranges, gap: float) -> list[list[float]]:
    """Horizontal ranges merged where they overlap or sit closer than gap."""
    spans: list[list[float]] = []
    for left, right in sorted(ranges):
        if spans and left <= spans[-1][1] + gap:
            spans[-1][1] = max(spans[-1][1], right)
        else:
            spans.append([left, right])
    return spans


def join_lines(parts: list[str]) -> str:
    """A cell's lines as one text: a space at each wrap, none inside a wrapped number or after a hyphen."""
    text = ""
    for part in parts:
        if not text:
            text = part
        elif (re.search(r"\d$", text) and re.match(r"[\d,.]", part)) or re.search(r"\w-$", text):
            text += part
        else:
            text += " " + part
    return text


def _text(words) -> str:
    return join_lines([" ".join(word[4] for word in line) for _, line in _lines(words)])


def _centre(word) -> float:
    return (word[0] + word[2]) / 2


@dataclass(frozen=True)
class _Header:
    """A table's title, the words of its header and its Planned and Actual heads, with their places."""

    title: str
    words: tuple[Word, ...]
    heads: tuple[Word, ...]


def read_pages(pages) -> list[list[Table]]:
    """The tables on each page of a document's recorded words, in page order.

    A table that runs onto the next page goes on there without its header, so the rows at the top
    of a page, above its first header, are read with the columns of the last table on the page before.
    """
    found, carried = [], None
    for words in pages:
        tables, carried = _tables_on(list(words), carried)
        found.append(tables)
    return found


def _tables_on(words, carried: _Header | None) -> tuple[list[Table], _Header | None]:
    if not words:
        return [], carried
    height = statistics.median(w[3] - w[1] for w in words)
    lines = _lines(words)
    heads = [(top, line) for top, line in lines if sum(w[4] in PLANNED_ACTUAL for w in line) >= 2]
    activity = [i for i, (_, line) in enumerate(lines) if any(w[4] == "Activity" and w[0] < LEFT for w in line)]
    found = []  # (where the title starts, header, where the table's rows start, where they stop)
    for top_of_heads, line in heads:
        above = [i for i in activity if lines[i][0] < top_of_heads]
        if not above:
            continue
        start, title, title_top = _header_start(lines, max(above), height)
        later = [i for i in activity if lines[i][0] > top_of_heads]
        end = _header_start(lines, min(later), height)[2] - 0.5 if later else float("inf")
        header = _Header(title, tuple(w for w in words if start - 0.5 <= w[1] < top_of_heads - 0.5),
                         tuple(sorted(w for w in line if w[4] in PLANNED_ACTUAL)))
        found.append((title_top, header, top_of_heads + 0.5, end))
    tables = []
    first = found[0][0] - 0.5 if found else float("inf")
    rest = [w for w in words if w[1] < first]
    if carried and rest:
        tables.append(_grid(carried, rest, height))
    for _, header, top, end in found:
        tables.append(_grid(header, [w for w in words if top < w[1] < end], height))
    return tables, (found[-1][1] if found else carried)


LEFT = 60  # points: a table's title and its first column start left of this


def _header_start(lines, activity: int, height: float) -> tuple[float, str, float]:
    """Where a table's header starts, the table's title, and where the title starts.

    A header begins on the line of "Activity Reference No.", or higher where a step's name starts
    above it. The title is the line above the header that starts at the left edge, such as WORKS.
    """
    start = lines[activity][0]
    for top, line in reversed(lines[:activity]):
        if start - top > 4 * height:
            break
        if any(w[0] < LEFT for w in line):
            return start, " ".join(w[4] for w in line), top
        start = top
    return start, "", start


def _grid(table: _Header, body: list[Word], height: float) -> Table:
    title, header, heads = table.title, list(table.words), table.heads
    first = heads[0][0]
    space = _space(body or header)

    # The columns left of the dates: wherever no word crosses the gap between two columns, a gap a
    # little wider than a space.
    columns = []
    for left, right in _spans([(w[0], w[2]) for w in header + body if w[2] < first - 1], 1.3 * space):
        label = _text([w for w in header if left <= _centre(w) <= right])
        columns.append({"left": left, "right": right, "label": label, "head": ""})
    # The date columns: one per Planned or Actual head, divided halfway between heads.
    for i, head in enumerate(heads):
        left = (heads[i - 1][2] + head[0]) / 2 if i else first - 1
        right = (head[2] + heads[i + 1][0]) / 2 if i + 1 < len(heads) else float("inf")
        columns.append({"left": left, "right": right, "label": "", "head": head[4]})
    # A step's name sits over its Planned column and the Actual column after it.
    dated = [c for c in columns if c["head"]]
    for i, column in enumerate(dated):
        if column["head"] != "Planned":
            continue
        pair = [column] + ([dated[i + 1]] if i + 1 < len(dated) and dated[i + 1]["head"] == "Actual" else [])
        left, right = pair[0]["left"], pair[-1]["right"]
        label = _text([w for w in header if left <= _centre(w) < right])
        for member in pair:
            member["label"] = label

    # Each column's words make cells where a gap between lines is wider than a line; cells whose
    # middles sit at the same height make a row.
    cells = []
    for index, column in enumerate(columns):
        mine = sorted((w for w in body if column["left"] <= _centre(w) < column["right"]), key=lambda w: (w[1], w[0]))
        group: list[Word] = []
        for word in mine:
            if group and word[1] - max(w[1] for w in group) > 1.6 * height:
                cells.append((index, group))
                group = []
            group.append(word)
        if group:
            cells.append((index, group))
    placed = sorted(((min(w[1] for w in g) + max(w[3] for w in g)) / 2, index, g) for index, g in cells)
    rows: list[list] = []
    for middle, index, group in placed:
        if rows and middle - rows[-1][0] <= 2 * height:
            rows[-1][1].append((index, group))
        else:
            rows.append([middle, [(index, group)]])
    grid = [tuple(c["label"] for c in columns), tuple(c["head"] for c in columns)]
    for _, row in rows:
        texts = [""] * len(columns)
        for index, group in row:
            texts[index] = f"{texts[index]} {_text(group)}".strip()
        grid.append(tuple(texts))
    return Table(title=title, header_rows=2, rows=tuple(grid))


# ── Live: ai_parse_document on the SQL warehouse ─────────────────────────

PARSE_SQL = """
SELECT to_json(ai_parse_document(content, map('version', '2.0'))) AS parsed
FROM READ_FILES(:path, format => 'binaryFile')
"""
VOLUME = "/Volumes/strata/bronze/files/layout"  # the bundle's bronze files volume


class AiParseDocument:
    """The layout parser on the workspace. Each page goes to the volume as a PDF of its own, so the
    daily page cap counts what ai_parse_document actually reads, and the warehouse parses it.

    engine runs SQL on the warehouse, upload(path, data) writes a file to a volume, and fetch(url)
    returns a PDF's bytes. If day-one test 3 chooses Content Understanding, a parser with the same
    name and parse method takes this one's place.
    """

    name = "ai_parse_document"

    def __init__(self, engine, upload, fetch, volume: str = VOLUME):
        self.engine, self.upload, self.fetch, self.volume = engine, upload, fetch, volume.rstrip("/")
        self._pdfs: dict[str, bytes] = {}

    def parse(self, page: Page) -> list[Table]:
        """One page's tables. A page that cannot be cut out of its PDF, or that ai_parse_document
        refuses or answers with nothing it can read, raises ParseFailed. A PDF that cannot be fetched,
        or a volume that refuses the upload, stops the run, because every page would fail the same way."""
        from strata.lakehouse.engine import EngineError

        url = https(page.pdf_url)
        if url not in self._pdfs:
            self._pdfs = {url: self.fetch(url)}  # keep one PDF at a time: pages come document by document
        path = f"{self.volume}/{page.document_id}/page-{page.pdf_page}.pdf"
        try:
            one_page = single_page(self._pdfs[url], page.pdf_page)
        except Exception as error:  # noqa: BLE001 - pypdf raises its own errors for a page it cannot cut out
            raise ParseFailed(f"I could not cut page {page.pdf_page} out of {url}: {error}") from error
        self.upload(path, one_page)
        try:
            result = self.engine.run(PARSE_SQL, {"path": path})
        except EngineError as error:
            raise ParseFailed(f"ai_parse_document could not read {path}: {error}") from error
        if not result.rows or not result.rows[0][0]:
            raise ParseFailed(f"ai_parse_document returned nothing for {path}.")
        try:
            return tables_from_parsed(json.loads(result.rows[0][0]))
        except (ValueError, TypeError, AttributeError) as error:
            raise ParseFailed(f"I could not read ai_parse_document's answer for {path}: {error}") from error


def single_page(pdf: bytes, number: int) -> bytes:
    """One page of a PDF, as a PDF of its own."""
    import io

    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(pdf)).pages[number - 1])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def tables_from_parsed(parsed: dict) -> list[Table]:
    """The tables in ai_parse_document's output (version 2.0), each titled by the element before it.

    A table's header rows end with the row of Planned and Actual heads; they become two rows, each
    column's name and its head, as the offline parser gives them. A table with no such row, such as
    one continued from the page before, keeps every row as a body row.
    """
    tables, title = [], ""
    for element in (parsed.get("document") or {}).get("elements") or []:
        content = (element.get("content") or "").strip()
        if element.get("type") != "table":
            if content:
                title = " ".join(content.split())
            continue
        grid = html_grid(content)
        heads_at = next((i for i, row in enumerate(grid) if sum(cell in PLANNED_ACTUAL for cell in row) >= 2), None)
        if heads_at is None:
            tables.append(Table(title, 0, tuple(grid)))
            continue
        labels = []
        for column in range(len(grid[heads_at])):
            parts: list[str] = []
            for row in grid[:heads_at + 1]:
                cell = row[column] if column < len(row) else ""
                if cell and cell not in PLANNED_ACTUAL and cell not in parts:
                    parts.append(cell)
            labels.append(" ".join(parts))
        heads = tuple(cell if cell in PLANNED_ACTUAL else "" for cell in grid[heads_at])
        tables.append(Table(title, 2, (tuple(labels), heads, *grid[heads_at + 1:])))
    return tables


def html_grid(markup: str) -> list[tuple[str, ...]]:
    """An HTML table as rows of cells, with each spanned cell's text repeated in every place it spans."""
    from html.parser import HTMLParser

    class Cells(HTMLParser):
        def __init__(self):
            super().__init__()
            self.rows: list[list[tuple[str, int, int]]] = []
            self.cell: list[str] | None = None
            self.spans = (1, 1)

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag == "tr":
                self.rows.append([])
            elif tag in ("td", "th"):
                if not self.rows:
                    self.rows.append([])
                self.cell = []
                self.spans = (int(attributes.get("rowspan") or 1), int(attributes.get("colspan") or 1))
            elif tag == "br" and self.cell is not None:
                self.cell.append(" ")

        def handle_endtag(self, tag):
            if tag in ("td", "th") and self.cell is not None:
                self.rows[-1].append((" ".join("".join(self.cell).split()), *self.spans))
                self.cell = None

        def handle_data(self, data):
            if self.cell is not None:
                self.cell.append(data)

    parser = Cells()
    parser.feed(markup)
    grid: list[list[str | None]] = []
    for r, row in enumerate(parser.rows):
        while len(grid) <= r:
            grid.append([])
        column = 0
        for text, rowspan, colspan in row:
            while column < len(grid[r]) and grid[r][column] is not None:
                column += 1
            for down in range(rowspan):
                while len(grid) <= r + down:
                    grid.append([])
                target = grid[r + down]
                while len(target) < column + colspan:
                    target.append(None)
                for across in range(colspan):
                    target[column + across] = text
            column += colspan
    width = max((len(row) for row in grid), default=0)
    return [tuple((cell or "") for cell in row) + ("",) * (width - len(row)) for row in grid]
