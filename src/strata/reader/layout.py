"""Route B: the layout parser, which reads one PDF page: its tables, its text and its figures.

The page router sends a page here when the published text cannot be trusted with it: a scanned page,
a table that the published text scrambles, such as the STEP table of a Procurement Plan or a PAD's
risk table, or a figure (docs/PLAN.md section 5). A parser returns the page's Layout: each table as a
grid (its header rows first, then one row per table row, each row with one cell per column), the
page's other words as text in reading order, one line per line with a blank line between blocks,
and how many figures it found. Each parser has a name, which the run records with every page it
reads. A parser raises ParseFailed for a page it cannot read; the run records the page and goes on to
the next one.

- RecordedLayout, offline. The fixture records every word on the PDF pages of each Procurement Plan
  and of the scanned P130164 PAD with its box (data/fixture/recorded/documents/<project>/<name>.words.json,
  read from the PDF's text layer). This parser finds each STEP table from its line of "Planned" and
  "Actual" column heads, takes the other columns from the gaps between words, and joins the words
  of each cell. It reads a PAD's risk table, set in two columns, from the line of each risk's
  Rating (risk_table below). It stands in for ai_parse_document so that the gate needs no
  workspace. It cannot read a page whose words the fixture did not record, or a page with no words
  (a scan's text layer can be empty), so it raises ParseFailed for each.
- AiParseDocument, live. It puts the one page, as a PDF of its own, in a volume and runs
  ai_parse_document on the SQL warehouse, then reads each table element's HTML into a grid and the
  other elements into text. Each page goes on its own, so a document of any length is read in parts
  of one page, and every page keeps its number in the whole PDF.

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
class Layout:
    """What the layout parser read on one page: its tables, its other words as text in reading order
    (one line per line, a blank line between blocks), and how many figures it found."""

    tables: tuple[Table, ...] = ()
    text: str = ""
    figures: int = 0


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

    def parse(self, page: Page) -> Layout:
        """One page's tables, text and figures. Raises ParseFailed when it cannot read the page."""


def https(url: str) -> str:
    """The same address over https, which is how the World Bank's hosts answer today."""
    return re.sub(r"^http://", "https://", url.strip())


# ── Offline: the tables from the recorded words ──────────────────────────

Word = tuple[float, float, float, float, str]  # x0, y0, x1, y1, text, in points from the top left


class RecordedLayout:
    """The layout parser's offline stand-in, which reads each page from its document's recorded words."""

    # The registry name every shelf window looks up in web/src/copy.ts's dataReadiness.shelf.parserNames, which gives
    # it plain words ("My offline substitute"); rename both together, or the window falls back to this name in mono.
    name = "recorded words"

    def __init__(self, manifest, rejoin_split_words: bool | None = None):
        from strata.config import load_rejoin_split_words

        self.files = {https(source.pdf_url): manifest.recorded / f"{source.file}.words.json"
                      for source in manifest.sources if source.words}
        # config/models.toml's [layout] rejoin_split_words, a parked decision: false until the user decides.
        self.rejoin = load_rejoin_split_words() if rejoin_split_words is None else rejoin_split_words

    def parse(self, page: Page) -> Layout:
        path = self.files.get(https(page.pdf_url))
        if path is None:
            raise ParseFailed(f"The fixture has no recorded words for {page.pdf_url}, so the offline layout "
                              "parser cannot read it. Mark its source words = true in data/fixture/sources.toml "
                              "and record it again.")
        pages = _recorded_layouts(path, self.rejoin)
        if not 1 <= page.pdf_page <= len(pages):
            raise ParseFailed(f"{page.pdf_url} has {len(pages)} pages, so it has no page {page.pdf_page}.")
        found = pages[page.pdf_page - 1]
        if found is None:
            raise ParseFailed(f"Page {page.pdf_page} of {page.pdf_url} has no words in its text layer, so the "
                              "offline layout parser cannot read it. ai_parse_document reads the scanned image.")
        return found


@lru_cache(maxsize=64)
def _recorded_layouts(path: Path, rejoin: bool = False) -> tuple[Layout | None, ...]:
    return tuple(read_layouts(_recorded_pages(path), rejoin))


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


def _text(words, right: float | None = None, rejoin: bool = False) -> str:
    """A cell's words as one text. With rejoin, a word the cell wrapped at its right edge joins its end
    on the next line with no space ("Explor" then "atory" reads "Exploratory")."""
    lines = _lines(words)
    if not (rejoin and right is not None and right != float("inf")):
        return join_lines([" ".join(word[4] for word in line) for _, line in lines])
    text = ""
    for at, (_, line) in enumerate(lines):
        part = " ".join(word[4] for word in line)
        previous = lines[at - 1][1] if at else None
        if previous and previous[-1][2] >= right - 2 and part[:1].islower() and previous[-1][4][-1:].isalpha():
            text += part
        else:
            text = join_lines([text, part]) if text else part
    return text


def _centre(word) -> float:
    return (word[0] + word[2]) / 2


@dataclass(frozen=True)
class _Header:
    """A table's title, the words of its header and its Planned and Actual heads, with their places."""

    title: str
    words: tuple[Word, ...]
    heads: tuple[Word, ...]


def read_pages(pages) -> list[list[Table]]:
    """The tables on each page of a document's recorded words, in page order."""
    return [list(layout.tables) if layout else [] for layout in read_layouts(pages)]


def read_layouts(pages, rejoin: bool = False) -> list[Layout | None]:
    """Each page of a document's recorded words as the layout parser reads it, in page order, or None
    for a page with no words.

    A table that runs onto the next page goes on there without its header, so the rows at the top
    of a page, above its first header, are read with the columns of the last table on the page before.
    A risk table runs from the page that names the risk assessment framework to the next annex.
    """
    found, carried, risks = [], None, None
    for words in pages:
        words = list(words)
        if not words:
            found.append(None)
            continue
        risks = risk_table_title(words, risks)
        if risks is not None:
            table, used = _risk_table(words, risks)
            tables = [table] if table else []
        else:
            tables, carried, used = _tables_on(words, carried, rejoin)
        text = _text_blocks([w for i, w in enumerate(words) if i not in used])
        found.append(Layout(tuple(tables), text, 0))
    return found


def _text_blocks(words) -> str:
    """Words in reading order: one line per line, and a blank line where the gap between two lines is
    wider than a line, so a paragraph reads as one block."""
    if not words:
        return ""
    height = statistics.median(w[3] - w[1] for w in words)
    out, last = [], None
    for top, line in _lines(words):
        if last is not None and top - last > 2 * height:
            out.append("")
        out.append(" ".join(w[4] for w in line))
        last = top
    return "\n".join(out)


def _tables_on(words, carried: _Header | None, rejoin: bool = False) -> tuple[list[Table], _Header | None, set[int]]:
    """The STEP tables on a page, the header the next page carries on with, and the indexes of the
    words the tables hold."""
    if not words:
        return [], carried, set()
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
    tables, used = [], set()
    first = found[0][0] - 0.5 if found else float("inf")
    rest = [i for i, w in enumerate(words) if w[1] < first]
    if carried and rest:
        tables.append(_grid(carried, [words[i] for i in rest], height, rejoin))
        used |= set(rest)
    for title_top, header, top, end in found:
        body = [i for i, w in enumerate(words) if top < w[1] < end]
        tables.append(_grid(header, [words[i] for i in body], height, rejoin))
        used |= set(body) | {i for i, w in enumerate(words) if title_top - 0.5 <= w[1] <= top}
    return tables, (found[-1][1] if found else carried), used


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


def _grid(table: _Header, body: list[Word], height: float, rejoin: bool = False) -> Table:
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

    # A row starts at each Activity Reference No. at the left of the first column. Every word from its
    # line down to the next reference's line belongs to it, so rows set close together, with no gap
    # wider than a line between them, stay apart.
    anchored = _anchored_rows(columns, body, height, space, rejoin)
    if anchored is not None:
        return Table(title=title, header_rows=2, rows=(tuple(c["label"] for c in columns),
                                                       tuple(c["head"] for c in columns), *anchored))

    # Otherwise each column's words make cells where a gap between lines is wider than a line; cells
    # whose middles sit at the same height make a row.
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


# ── A PAD's risk table, set in two columns ───────────────────────────────

# The heading that starts a PAD's risk table, a line of its own: the Operational Risk Assessment
# Framework (ORAF) in a PAD from before 2014, the Systematic Operations Risk-Rating Tool (SORT) after
# it, perhaps as an annex ("Annex 4 - Operational Risk Assessment Framework (ORAF)"). A mention in a
# sentence, in the list of abbreviations or in the contents (with its dotted leader) is not one. The
# table runs to the next annex. The PAD's template (src/strata/reader/templates.py) routes by it too.
RISK_TITLE = re.compile(r"^\s*(?:Annex\s+\d+\s*[:.\-\u2013]\s*)?(?:Operational Risk Assessment Framework|"
                        r"Systematic Operations Risk[-\s]*Rating Tool)\s*(?:\([A-Z]+\))?\s*$", re.I)
ANNEX_HEAD = re.compile(r"^Annex\s+\d+", re.I)
RISK_HEAD = ("Risk", "Rating", "Risk Description", "Risk Management")
RISK_LABELS = ("Description:", "Management:")


def risk_table_title(words, current: str | None) -> str | None:
    """The title of the risk table this page holds or carries on, or None. A page that names a risk
    assessment framework starts one; a page that starts another annex ends it."""
    lines = _lines(words)
    for _, line in lines:
        text = " ".join(w[4] for w in line)
        if RISK_TITLE.match(text):
            return text
    if current is not None and any(ANNEX_HEAD.match(" ".join(w[4] for w in line)) for _, line in lines[:3]):
        return None
    return current


def _risk_table(words, title: str) -> tuple[Table | None, set[int]]:
    """A page of a risk table: one row from each risk's line of "{Risk} Rating {rating}" to the next,
    its left column the risk's description and its right column how it is managed. Words above the
    first such line carry on the last risk of the page before, and make a row with no risk or rating.
    The title, the project's line under it and the printed page number at the foot are not in the
    table. Returns the table, or None when the page holds no risk, and the indexes of its words."""
    index = {id(w): i for i, w in enumerate(words)}
    lines = _lines(words)
    ratings = [(top, line, next(w for w in line if w[4].rstrip(":") == "Rating"))
               for top, line in lines if _rating_line(line)]
    labels = [w for _, line in lines for a, w in zip(line, line[1:]) if a[4] == "Risk" and w[4] in RISK_LABELS]
    marks = [rating for *_, rating in ratings] + [w for w in labels if w[4] == "Management:"]
    if not marks:
        return None, set()
    split = min(w[0] for w in marks) - 2
    if any(w[4] == "Management:" for w in marks):
        split = min(split, min(w[0] for w in labels if w[4] == "Management:") - 35)  # "Risk" starts left of it
    outside = set()
    for top, line in lines:
        text = " ".join(w[4] for w in line)
        if RISK_TITLE.match(text) or re.search(r"\(P\d{6}\)", text) and not _rating_line(line):
            outside |= {index[id(w)] for w in line}
    if lines and re.fullmatch(r"\d{1,3}|[ivxlc]{1,7}", " ".join(w[4] for w in lines[-1][1])):
        outside |= {index[id(w)] for w in lines[-1][1]}
    dropped = {id(w) for _, line in lines for a, w in zip(line, line[1:]) if a[4] == "Risk" and w[4] in RISK_LABELS}
    dropped |= {id(a) for _, line in lines for a, w in zip(line, line[1:]) if a[4] == "Risk" and w[4] in RISK_LABELS}
    starts = [top for top, *_ in ratings]
    rows = []
    for number in range(-1, len(ratings)):
        top = starts[number] if number >= 0 else float("-inf")
        bottom = starts[number + 1] if number + 1 < len(starts) else float("inf")
        if number >= 0:
            line, rating = ratings[number][1], ratings[number][2]
            risk = " ".join(w[4] for w in line if w[0] < rating[0]).rstrip(":")
            value = " ".join(w[4] for w in line if w[0] > rating[0])
            below = [w for t, l in lines if top < t < bottom for w in l]
        else:
            risk = value = ""
            below = [w for t, l in lines if t < bottom for w in l]
        below = [w for w in below if index[id(w)] not in outside and id(w) not in dropped]
        description = _text([w for w in below if w[0] < split])
        management = _text([w for w in below if w[0] >= split])
        if number >= 0 or description or management:
            rows.append((risk, value, description, management))
    used = set(range(len(words))) - outside
    return Table(title=title, header_rows=1, rows=(RISK_HEAD, *rows)), used


def _rating_line(line) -> bool:
    """A risk's first line: its name, the word Rating, then its rating, as in "Capacity Rating Low"."""
    at = next((i for i, w in enumerate(line) if w[4].rstrip(":") == "Rating"), None)
    return at is not None and 0 < at < len(line) - 1


# A reference at the start of a row, perhaps cut short where its cell wraps: KE-NWWDA-541055-CW-RFB,
# or NWWDA-WSDP-03-2019- with 2020 on the next line.
ROW_START = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]*){2,}$")


def _anchored_rows(columns, body: list[Word], height: float, space: float,
                   rejoin: bool = False) -> list[tuple[str, ...]] | None:
    """The table's rows, each from a reference at the left edge of the first column to the next, or
    None when the first column starts no row with a reference. Words above the first reference, the
    end of a row the page before began, make a row of their own.

    STEP's export lets a long description run past the foot of its cell, so its last line can be
    printed over the next row's reference ("CELARS Co" then "nstruction Works" over
    KE-KENHA-201831-CS-QCBS). A word on a reference's line that overlaps the reference belongs to the
    row above."""
    if not columns or not body:
        return None
    first = columns[0]
    anchors = sorted((w for w in body if first["left"] <= _centre(w) < first["right"]
                      and w[0] - first["left"] < 2 * space and ROW_START.match(w[4])), key=lambda w: w[1])
    if not anchors:
        return None
    groups: dict[int, list[Word]] = {}
    for word in body:
        row = sum(1 for anchor in anchors if anchor[1] <= word[1] + height / 2) - 1  # -1: above the first reference
        if row >= 0 and word is not anchors[row]:
            anchor = anchors[row]
            if abs(word[1] - anchor[1]) < height / 2 and word[0] < anchor[2] and word[2] > anchor[0]:
                row -= 1
        groups.setdefault(row, []).append(word)
    rows = []
    for row in sorted(groups):
        texts = []
        for column in columns:
            texts.append(_text([w for w in groups[row] if column["left"] <= _centre(w) < column["right"]],
                               column["right"], rejoin))
        rows.append(tuple(texts))
    return rows


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
    parse method joins PARSERS below, and config/models.toml names it.
    """

    name = "ai_parse_document"

    def __init__(self, engine, upload, fetch, volume: str = VOLUME):
        self.engine, self.upload, self.fetch, self.volume = engine, upload, fetch, volume.rstrip("/")
        self._pdfs: dict[str, bytes] = {}

    def parse(self, page: Page) -> Layout:
        """One page's layout. A page that cannot be cut out of its PDF, or that ai_parse_document
        refuses or answers with nothing it can read, raises ParseFailed. A PDF that cannot be fetched
        raises NotFetched, naming the PDF, and a volume that refuses the upload raises the SDK's error:
        both stop the run, because every page would fail the same way."""
        from strata.lakehouse.engine import EngineError
        from strata.reader.documents import NotFetched

        url = https(page.pdf_url)
        if url not in self._pdfs:
            try:
                fetched = self.fetch(url)  # HostRefused, from the job's PoliteFetch, stops the run as it is
            except OSError as error:  # urllib's errors are OSErrors; the host's answer is in the message
                raise NotFetched(f"I could not fetch {url}: {error}", url) from error
            self._pdfs = {url: fetched}  # keep one PDF at a time: pages come document by document
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
            return layout_from_parsed(json.loads(result.rows[0][0]))
        except (ValueError, TypeError, AttributeError) as error:
            raise ParseFailed(f"I could not read ai_parse_document's answer for {path}: {error}") from error


# The live layout parsers, by the name config/models.toml gives in [layout] parser.
PARSERS = {AiParseDocument.name: AiParseDocument}


def single_page(pdf: bytes, number: int) -> bytes:
    """One page of a PDF, as a PDF of its own."""
    import io

    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(pdf)).pages[number - 1])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ai_parse_document's element types that are not text of the page: a figure is counted, and a page's
# running header, its footer and its page number are left out.
FIGURES = ("figure", "image", "picture")
NOT_TEXT = ("page_header", "page_footer", "page_number")


def layout_from_parsed(parsed: dict) -> Layout:
    """One page's layout from ai_parse_document's output (version 2.0): its tables, the content of its
    other elements as text blocks in their order, and how many figures it has."""
    elements = (parsed.get("document") or {}).get("elements") or []
    blocks = [(element.get("content") or "").strip() for element in elements
              if element.get("type") not in ("table", *FIGURES, *NOT_TEXT)]
    figures = sum(1 for element in elements if element.get("type") in FIGURES)
    return Layout(tuple(tables_from_parsed(parsed)), "\n\n".join(block for block in blocks if block), figures)


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
