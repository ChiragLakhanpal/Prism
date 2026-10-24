"""Route A: a document's published text read into numbered passages (docs/PLAN.md section 5).

A passage is a numbered paragraph with its PDF page and printed page, the unit every citation points
to (GLOSSARY.md). read() takes the text the World Bank publishes for a document, the number of pages
its PDF has, and the document type's template (src/strata/reader/templates.py), and does this:

1. It divides the text into pages on its form feeds. The published text ends each page with one, so
   page n is the nth part. A text that does not divide into as many pages as the PDF has, such as a
   scan's, gives no passages, and every page waits for Route B.
2. It reads each page's printed page number ("Page 19 of 62", or a bare 19 or ii at its foot), and
   drops the lines that repeat at the top or foot of most pages, such as the report's running title.
3. It routes each page. The pages before the body (the cover, the abbreviations and the contents)
   are read and give no passages. A data sheet's pages hold tables, so they go to Route B, as do a
   PAD's risk table, from the page that names its risk framework to the next annex, and a page with
   no text left, such as a figure. Every other page is Route A's. A scan's published text does not
   divide into its pages, so every page of a scan goes to Route B: its risk table as a table, the
   rest as scanned pages (route_scan).
4. It finds the headings from the template, which give each passage its section path (III.B), and
   separates the numbered paragraphs (54. Another lesson ...). The text between a numbered
   paragraph and the next belongs to it, across a page break too, until a heading or a short line
   standing alone, such as "Quality at Entry", ends it. Text that no number covers forms a paragraph
   that Strata numbers itself, and says so.
5. It divides any paragraph over max_tokens tokens at sentence ends. The parts share the
   paragraph's number, and each part starts on its own PDF page.

Each passage's text is the paragraph's words as published, with each run of spaces and line breaks
written as one space, so a quote found in it is found on its page.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

from strata.reader.templates import Template

PAGE_BREAK = "\f"
# "Page 19 of 62", or in a report in French "Page 6 sur 80", kept as the page prints it.
PRINTED = re.compile(r"\bPage\s+(\d+\s+(?:of|sur)\s+\d+)\b")
FOOT_NUMBER = re.compile(r"^\s*(\d{1,3}|[ivxlc]{1,7})\s*$")
TABLE_GAP = re.compile(r"\S\s{3,}\S")  # columns of a table, which no line of a paragraph has
BULLET = re.compile(r"^\s*(?:[•●▪o\-–]|\(\w{1,4}\)|\w\)|\d{1,2}\))\s")
TOKEN = re.compile(r"\w+|[^\w\s]")
# A sentence ends at a full stop, question mark or exclamation mark, with any closing quote or bracket,
# before the space (group 1) that comes before the next sentence's capital letter or number.
SENTENCE_END = re.compile(r"[.!?][\"'”’)]*(\s+)(?=[\"'“‘(]?[A-Z0-9])")

# Routes and the reasons a page takes one, as silver.document_page_routes records them.
ROUTE_A, ROUTE_B = "A", "B"
BODY, FRONT_MATTER = "body", "front_matter"
DATA_SHEET, NO_TEXT, NOT_PAGED = "data_sheet", "no_text", "text_not_paged"
SCANNED, RISK_TABLE = "scanned", "risk_table"  # a scan's page, and a page of a PAD's risk table
TABLE_REASONS = (DATA_SHEET, RISK_TABLE)  # the pages whose tables Route B reads into rows
# The kinds of passage, as silver.passages records them: a numbered paragraph (or a section, or a part
# of one), one row of a table, the one summary of a table that Strata writes and that never backs a
# number (spec, "Reading documents"; the verifier reads it), and a section of a notice's text.
PARAGRAPH, TABLE_ROW, TABLE_SUMMARY, NOTICE_TEXT = "paragraph", "table_row", "table_summary", "notice_text"


def tokens(text: str) -> int:
    """How many tokens a text has, counted as its words and its punctuation marks.

    The embedding model counts with its own tokenizer, which the offline gate cannot load, and on
    English prose it gives about as many tokens as this count. It is the one count Strata uses."""
    return len(TOKEN.findall(text))


def words(text: str) -> str:
    """The text with each run of spaces and line breaks written as one space."""
    return " ".join(text.split())


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PageRoute:
    pdf_page: int
    route: str
    reason: str
    printed_page: str | None
    numbering_found: bool  # a paragraph the report numbers has text on this page
    passages: int  # passages that start on this page


@dataclass(frozen=True)
class Passage:
    key: str  # unique in the document: the paragraph's number, annex2.3 in an annex, s4 when Strata numbers it
    section_path: str
    paragraph: str
    paragraph_numbered: bool
    part: int
    parts: int
    pdf_page: int
    last_pdf_page: int
    printed_page: str | None
    text: str
    tokens: int


@dataclass(frozen=True)
class Reading:
    pages: tuple[PageRoute, ...]
    passages: tuple[Passage, ...]

    @property
    def paged(self) -> bool:
        """Whether the published text divided into the PDF's pages, so Route A could read it."""
        return not any(page.reason == NOT_PAGED for page in self.pages)


# ── Pages ────────────────────────────────────────────────────────────────

def split_pages(text: str, pdf_pages: int) -> list[str] | None:
    """The text of each page, or None when the text does not divide into the PDF's pages."""
    parts = text.split(PAGE_BREAK)
    if len(parts) == pdf_pages + 1 and not parts[-1].strip():
        parts = parts[:-1]
    return parts if len(parts) == pdf_pages and pdf_pages > 0 else None


def _printed(lines: list[str]) -> str | None:
    for line in lines:
        found = PRINTED.search(line)
        if found:
            return words(found.group(1))
    filled = [line for line in lines if line.strip()]
    if filled and FOOT_NUMBER.match(filled[-1]):
        return filled[-1].strip()
    return None


def _running(pages: list[list[str]]) -> set[str]:
    """Lines that repeat at the top or the foot of most pages: a running title, not the text."""
    seen: Counter = Counter()
    for lines in pages:
        filled = [words(line) for line in lines if line.strip()]
        seen.update(set(filled[:5] + filled[-5:]))
    least = max(3, int(len(pages) * 0.3))
    return {line for line, count in seen.items() if count >= least} if len(pages) >= 3 else set()


def _page_lines(lines: list[str], running: set[str], printed: str | None) -> list[str]:
    """A page's lines without its running title, its printed page number and its foot number."""
    kept = [line for line in lines if words(line) not in running and not PRINTED.search(line)]
    filled = [i for i, line in enumerate(kept) if line.strip()]
    if printed and filled and words(kept[filled[-1]]) == printed:
        kept = kept[:filled[-1]]
    return kept


# ── Paragraphs ───────────────────────────────────────────────────────────

@dataclass
class _Paragraph:
    section_path: str
    number: str | None  # the report's own number, or None when Strata numbers it
    key: str
    lines: list[tuple[int, str]] = field(default_factory=list)  # (PDF page, line)


@dataclass
class _State:
    template: Template
    levels: list[str | None]
    annex: str | None = None
    section: str | None = None  # an unnumbered report's heading, or an ICR Review's section number
    last: int = 0  # the last paragraph number in this numbering
    item: str | None = None  # the last item letter in an ICR Review's section
    current: _Paragraph | None = None
    unnumbered: int = 0
    done: list[_Paragraph] = field(default_factory=list)

    def path(self) -> str:
        if self.template.headings or self.template.items:
            return self.section or ""
        ids = [i for i in self.levels if i]
        if self.annex:
            return ".".join([f"Annex {self.annex}", *ids])
        return ".".join(ids)

    def close(self):
        if self.current and self.current.lines:
            self.done.append(self.current)
        self.current = None

    def start(self, number: str | None, page: int, line: str):
        self.close()
        if number is None:
            self.unnumbered += 1
            key = f"s{self.unnumbered}"
        else:
            key = f"annex{self.annex}.{number}" if self.annex else number
        self.current = _Paragraph(self.path(), number, key, [(page, line)])

    def add(self, page: int, line: str):
        if self.current is None:
            self.start(None, page, line)
        else:
            self.current.lines.append((page, line))


def _follows(state: _State, number: int) -> bool:
    """A paragraph number continues the report's numbering: the next one, allowing for a start
    the text lost, or 1 when an annex starts its own numbering."""
    if state.annex and state.last == 0:
        return number == 1
    return state.last < number <= state.last + 3


def _numbered_start(state: _State, line: str) -> str | None:
    template = state.template
    if template.items:
        found = template.paragraph.match(line)
        if found and _follows(state, int(found.group(1))):
            state.last, state.section, state.item = int(found.group(1)), found.group(1), None
            return found.group(1)
        found = template.items.match(line)
        expected = chr(ord(state.item) + 1) if state.item else "a"
        if found and state.section and found.group(1) == expected:
            state.item = found.group(1)
            return f"{state.section}.{found.group(1)}"
        return None
    found = template.paragraph.match(line)
    if not found or TABLE_GAP.search(found.group(2)):
        return None
    number = int(found.group(1))
    if not _follows(state, number):
        return None
    state.last = number
    return found.group(1)


def _heading(state: _State, line: str) -> bool:
    """Apply a heading of the template, if the line is one. Returns whether it was."""
    template = state.template
    text = words(line)
    if template.headings:
        numbered = next((pattern.match(line) for pattern in template.levels if pattern.match(line)), None)
        if text in template.headings or numbered:
            state.close()
            state.section = numbered.group(1) if numbered else text
            return True
        return False
    if template.annex and template.annex.match(line):
        state.close()
        state.annex = template.annex.match(line).group(1)
        state.levels = [None] * len(template.levels)
        state.last = 0
        return True
    for depth, pattern in enumerate(template.levels):
        found = pattern.match(line)
        if found:
            state.close()
            state.levels[depth] = found.group(1)
            for deeper in range(depth + 1, len(state.levels)):
                state.levels[deeper] = None
            return True
    return False


def _minor_heading(block: list[str]) -> bool:
    """A short line standing alone, such as "Quality at Entry": it ends the paragraph before it."""
    if len(block) != 1:
        return False
    line = words(block[0])
    return (0 < len(line.split()) <= 12 and line[-1] not in ".:;," and not BULLET.match(block[0])
            and not line[0].isdigit())


LEAD = re.compile(r"^\s*(?:\d{1,3}\.|[•●▪o\-–]|\(\w{1,4}\))\s+")  # a paragraph's number or a bullet, then its gap


def _table(block: list[str]) -> bool:
    """Lines set out in columns, most of them with wide gaps: a table, which no paragraph runs into."""
    gaps = sum(bool(TABLE_GAP.search(LEAD.sub("", line).strip())) for line in block)
    return len(block) > 1 and gaps * 2 >= len(block)


def _blocks(lines: list[str]) -> list[list[str]]:
    blocks, block = [], []
    for line in lines:
        if line.strip():
            block.append(line)
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)
    return blocks


# ── Parts at sentence ends ───────────────────────────────────────────────

def sentences(text: str, abbreviations: tuple[str, ...] = ()) -> list[str]:
    """A paragraph's sentences. A full stop after an abbreviation or an initial ends none."""
    pieces, start = [], 0
    for found in SENTENCE_END.finditer(text):
        before = text[start:found.start(1)].rsplit(" ", 1)[-1]
        if before in abbreviations or re.fullmatch(r"(?:[A-Z]\.)+|\(?[a-z]\.|\d+\.", before):
            continue
        pieces.append(text[start:found.start(1)].strip())
        start = found.end(1)
    pieces.append(text[start:].strip())
    return [piece for piece in pieces if piece]


def _pieces(sentence: str, max_tokens: int) -> list[str]:
    """A sentence, or, when one sentence alone is over max_tokens (a table's cells run together, with
    no sentence end), its words in runs that fit."""
    if tokens(sentence) <= max_tokens:
        return [sentence]
    pieces, current = [], []
    for word in sentence.split(" "):
        if current and tokens(" ".join(current + [word])) > max_tokens:
            pieces.append(" ".join(current))
            current = []
        current.append(word)
    return pieces + [" ".join(current)] if current else pieces


def _parts(text: str, max_tokens: int, abbreviations: tuple[str, ...]) -> list[str]:
    """The paragraph, or its parts when it is over max_tokens: whole sentences, as many as fit."""
    if tokens(text) <= max_tokens:
        return [text]
    parts, current = [], []
    for sentence in sentences(text, abbreviations):
        for piece in _pieces(sentence, max_tokens):
            if current and tokens(" ".join(current + [piece])) > max_tokens:
                parts.append(" ".join(current))
                current = []
            current.append(piece)
    if current:
        parts.append(" ".join(current))
    return parts


def _passages(paragraph: _Paragraph, max_tokens: int, template: Template, printed: dict[int, str | None]):
    joined, starts = "", []
    for page, line in paragraph.lines:
        line = words(line)
        if not line:
            continue
        starts.append((len(joined) + (1 if joined else 0), page))
        joined = f"{joined} {line}" if joined else line

    def page_at(offset: int) -> int:
        return [page for start, page in starts if start <= offset][-1]

    parts = _parts(joined, max_tokens, template.abbreviations)
    found, offset = [], 0
    for number, part in enumerate(parts, 1):
        offset = joined.index(part, offset)
        first, last = page_at(offset), page_at(offset + len(part) - 1)
        key = paragraph.key if len(parts) == 1 else f"{paragraph.key}/{number}"
        shown = paragraph.number if paragraph.number is not None else paragraph.key  # s4 when Strata numbered it
        found.append(Passage(key, paragraph.section_path, shown, paragraph.number is not None, number,
                             len(parts), first, last, printed.get(first), part, tokens(part)))
        offset += len(part)
    return found


# ── The document ─────────────────────────────────────────────────────────

def risk_pages(page_texts: list[str], template: Template) -> set[int]:
    """The PDF pages of a document's risk table, from the page that names its risk framework to the
    page before the next annex, read from each page's text."""
    found, inside = set(), False
    if template.risk_table is None:
        return found
    ends = [pattern for pattern in (template.annex, ANY_ANNEX, template.body_start, *template.levels[:1]) if pattern]
    for number, text in enumerate(page_texts, 1):
        lines = [line for line in text.splitlines() if line.strip()]
        if any(template.risk_table.match(line) for line in lines):
            inside = True
        elif inside and any(pattern.match(line) for pattern in ends for line in lines[:12]):
            inside = False
        if inside:
            found.add(number)
    return found


ANY_ANNEX = re.compile(r"^\s*Annex\s+\d+\s*[:.\-]", re.I)  # an annex's heading, however it is punctuated


def route_scan(pdf_pages: int, template: Template, page_texts: list[str] | None = None) -> tuple[PageRoute, ...]:
    """Every page of a scan, whose published text does not divide into its pages, on Route B: the pages
    of its risk table as a table, read from the text layer of each PDF page when it is given, and the
    rest as scanned pages."""
    risks = risk_pages(page_texts, template) if page_texts and len(page_texts) == pdf_pages else set()
    return tuple(PageRoute(n, ROUTE_B, RISK_TABLE if n in risks else SCANNED if page_texts else NOT_PAGED, None,
                           False, 0) for n in range(1, pdf_pages + 1))


def read(text: str, pdf_pages: int, template: Template, max_tokens: int,
         page_texts: list[str] | None = None) -> Reading:
    """A document's published text read into pages, each with its route, and passages. A scan's text
    does not divide into its pages, so it gives no passages, and every page goes to Route B, routed
    by the text of each PDF page when page_texts gives it."""
    pages = split_pages(text, pdf_pages)
    if pages is None:
        return Reading(route_scan(pdf_pages, template, page_texts), ())

    raw = [page.splitlines() for page in pages]
    running = _running(raw)
    printed = {n: _printed(lines) for n, lines in enumerate(raw, 1)}
    state = _State(template, [None] * len(template.levels))
    reasons: dict[int, str] = {}
    in_body, in_data_sheet = False, False
    risks = risk_pages(pages, template)
    for number, lines in enumerate(raw, 1):
        kept = _page_lines(lines, running, printed[number])
        if in_body and number in risks:
            state.close()
            reasons[number] = RISK_TABLE  # its rows come from Route B's table, not from the text
            continue
        if not in_body:
            start = next((i for i, line in enumerate(kept) if template.body_start.match(line)), None)
            if start is None:
                if template.data_sheet and any(template.data_sheet.match(line) for line in kept):
                    in_data_sheet = True
                reasons[number] = DATA_SHEET if in_data_sheet else FRONT_MATTER
                continue
            in_body, kept = True, kept[start:]
        if not any(line.strip() for line in kept):
            reasons[number] = NO_TEXT
            continue
        reasons[number] = BODY
        for block in _blocks(kept):
            if template.minor_headings and _minor_heading(block) and not _heading(state, block[0]):
                state.start(None, number, block[0])
                continue
            table = template.minor_headings and _table(block)
            for at, line in enumerate(block):
                if _heading(state, line):
                    continue
                paragraph = _numbered_start(state, line) if template.numbered and not table else None
                if paragraph is not None:
                    state.start(paragraph, number, line)
                elif table and at == 0 and (state.current is None or state.current.number is not None):
                    state.start(None, number, line)  # a table after a numbered paragraph is not part of it
                else:
                    state.add(number, line)
    state.close()

    passages = []
    for paragraph in state.done:
        if paragraph.number is None and len(paragraph.lines) == 1 and template.minor_headings \
                and _minor_heading([paragraph.lines[0][1]]):
            continue  # a heading with no text of its own under it
        passages += _passages(paragraph, max_tokens, template, printed)

    numbered_on = {page for paragraph in state.done if paragraph.number is not None for page, _ in paragraph.lines}
    starting = Counter(passage.pdf_page for passage in passages)
    routes = []
    for number in range(1, len(raw) + 1):
        reason = reasons[number]
        route = ROUTE_B if reason in (DATA_SHEET, NO_TEXT, RISK_TABLE) else ROUTE_A
        routes.append(PageRoute(number, route, reason, printed[number], number in numbered_on,
                                starting.get(number, 0)))
    return Reading(tuple(routes), tuple(passages))
