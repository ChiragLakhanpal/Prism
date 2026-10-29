"""The stress shelf's outcomes (ticket 18; docs/PLAN.md section 3): what the document run recovered from
each of the hardest documents, written to strata.ops.stress_shelf for the Data readiness page.

config/slice.toml lists the shelf's entries in order. Each names a fixed document or a rule that picks
one from the documents the run read, and its kind says what its outcome counts:

- scan_annex: the rated risks recovered from the hard part's pages (each a row of a risk table that
  names its risk and gives its rating), against the entry's hand count in config/slice.toml
  (expected_rows, which a person counts from the PDF's page images, and counted_on) when it has one.
  Without one, as in the fixture today, the outcome has nothing to check against. When the layout
  parser could read none of the part's pages, the part is recorded as unreadable.
- longest_pad (rule longest): the longest document of its type among the documents the run read for
  the projects the slice criteria select (not the projects the slice file names), and its pages read
  well, against the pages in the PDF: a page of published text that has text, and a page the layout
  parser read and recovered something from.
- large_plan: the activities that became STEP rows, against the activity references its published
  text lists.
- other_language: the passages that carry the entry's language, against the passages made from it.
- over_parser_limit (rule over_parser_limit): the longest document over the layout parser's page limit
  (ingestion.parser_part_pages), read in parts: the pages whose number matches the PDF, against the
  pages in the PDF. A page matches when the words read for it, by the layout parser (its text and its
  tables' cells) or from the published text, and the words of the PDF page with that number share at
  least ingestion.page_match_shared_words of them. A page the parser read whose PDF page has no text
  layer can't be compared, so it matches when the parser read it. When no document is over the limit,
  the entry records that, with the longest page count.

A document the run has not fetched is not read yet; one whose layout parser pages wait for the next run
because a parse run of its project stopped at the daily page cap that day (the plan reader's or the
passage reader's) is recorded as stopped there, with the pages read so far. A kind whose hard part has
no page to point to, such as a document none of whose pages went to the parser, has no hard page.
The page computes nothing: the Data readiness tool (src/strata/tools/data_readiness_for.py) reads these
rows and sets each badge from the thresholds file.
"""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from dataclasses import astuple, dataclass, fields

from strata.config import ShelfItem, Slice, Thresholds
from strata.lakehouse import plans, route_b
from strata.lakehouse.engine import Engine
from strata.reader import passages as route_a
from strata.reader import step
from strata.reader.layout import tables_from_json


@dataclass(frozen=True)
class Outcome:
    """One row of strata.ops.stress_shelf."""

    run_id: str
    shelf_key: str
    kind: str
    position: int  # the entry's place on the shelf, from 1, in the slice file's order
    state: str  # read, stopped_at_cap, not_read or no_document
    document_id: str | None
    project_id: str | None
    document_type: str | None
    document_date: dt.date | None
    pdf_pages: int | None
    pdf_url: str | None
    language: str | None
    part: str | None  # the hard part's key in the copy file, such as risk_annex
    hard_page: int | None  # the PDF page where the hard part starts
    parser_pages: int | None  # the pages the page router sent to the layout parser
    count: int | None
    denominator: int | None
    denominator_from: str | None  # hand_count, pdf_pages, text_references or passages_made
    counted_on: dt.date | None
    unreadable: bool
    parts: int | None
    parser: str | None
    parser_limit_pages: int
    longest_pages: int | None
    read_pages: int | None
    daily_page_cap: int
    measured_at: dt.datetime
    public_from: dt.date


COLUMNS = tuple(f.name for f in fields(Outcome))
REPORTS = """
SELECT document_id, project_id, document_type, document_date, pdf_pages, pdf_url, language
FROM strata.silver.documents
"""
PLANS = """
SELECT document_id, project_id, plan_date, pdf_pages, pdf_url, route_b_pages, parse_reason
FROM strata.silver.plan_versions
"""
ROUTES = """
SELECT pdf_page, route, reason, part FROM strata.silver.document_page_routes WHERE document_id = :document_id
ORDER BY pdf_page
"""
DOCUMENT_PASSAGES = """
SELECT kind, language, paragraph_numbered, pdf_page, cells FROM strata.silver.passages WHERE document_id = :document_id
"""
LAYOUT_PAGES = """
SELECT pdf_page, page_hash, tables, text FROM strata.bronze.layout_pages WHERE document_id = :document_id
"""
FAILED = """
SELECT DISTINCT pdf_page FROM strata.ops.parse_failures WHERE document_id = :document_id
"""
STOPPED = """
SELECT count(*) AS n FROM strata.ops.parse_runs
WHERE project_id = :project_id AND stopped_at_cap AND CAST(started_at AS DATE) = :day
"""
PLAN_TEXT = """
SELECT text FROM strata.bronze.document_texts WHERE document_id = :document_id ORDER BY fetched_at DESC
"""
PLAN_ROWS = """
SELECT DISTINCT activity_reference_no FROM strata.silver.plan_rows WHERE document_id = :document_id
"""


def _rows(engine: Engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


@dataclass(frozen=True)
class Document:
    document_id: str
    project_id: str
    document_type: str
    document_date: dt.date | None
    pdf_pages: int
    pdf_url: str
    language: str | None
    plan: bool = False


def documents(engine: Engine) -> dict[str, Document]:
    """Every document the run read: the passage reader's, then the plan reader's versions."""
    found = {str(row["document_id"]): Document(str(row["document_id"]), row["project_id"], row["document_type"],
                                               _date(row["document_date"]), row["pdf_pages"], row["pdf_url"],
                                               row["language"]) for row in _rows(engine, REPORTS)}
    for row in _rows(engine, PLANS):
        found.setdefault(str(row["document_id"]), Document(
            str(row["document_id"]), row["project_id"], plans.PLAN, _date(row["plan_date"]), row["pdf_pages"],
            row["pdf_url"], "en", plan=True))
    return found


def _words(text: str) -> Counter:
    return Counter(word.lower() for word in route_a.words(text).split() if any(ch.isalnum() for ch in word))


def _matches(read: str, pdf: str, shared: float) -> bool:
    """Whether the words read for a page are the PDF page's with its number: they share at least this share
    of their words."""
    mine, theirs = _words(read), _words(pdf)
    if not mine and not theirs:
        return True
    return sum((mine & theirs).values()) >= shared * max(sum(mine.values()), sum(theirs.values()))


def _layout_words(row: dict) -> str:
    """The words the layout parser read on a page: its text, and each table's title and cells."""
    cells = [text for table in tables_from_json(row["tables"]) for text in (table.title, *(c for r in table.rows for c in r))]
    return " ".join([row["text"] or "", *cells])


class Reader:
    """What the run read of one document, for its outcome."""

    def __init__(self, engine: Engine, document: Document):
        self.engine, self.document = engine, document
        self.routes = _rows(engine, ROUTES, document_id=document.document_id)
        self.pages = route_b.page_texts(engine, document.document_id)
        hashes = {number: digest for number, digest, _ in self.pages}
        self.layouts = {row["pdf_page"]: row for row in _rows(engine, LAYOUT_PAGES, document_id=document.document_id)
                        if hashes.get(row["pdf_page"]) == str(row["page_hash"])}
        self.failed = {row[0] for row in engine.run(FAILED, {"document_id": document.document_id}).rows}

    @property
    def parser_pages(self) -> list[int]:
        if self.document.plan:
            return [number for number, _, text in self.pages if plans.holds_table(text)]
        return [row["pdf_page"] for row in self.routes if row["route"] == route_a.ROUTE_B]

    def read_well(self, number: int) -> bool:
        row = self.layouts.get(number)
        return row is not None and (bool(tables_from_json(row["tables"])) or bool((row["text"] or "").strip()))

    def waiting(self) -> list[int]:
        """The parser's pages it has neither read nor failed on: the cap stopped the run before them."""
        return [n for n in self.parser_pages if n not in self.layouts and n not in self.failed]

    def read_pages(self) -> int:
        """The pages read so far: published text with text, and the parser's pages read."""
        sent = set(self.parser_pages)
        texts = {number: text for number, _, text in self.pages}
        return sum(1 for n in texts if n not in sent and texts[n].strip()) + sum(1 for n in sent if n in self.layouts)


def _base(run_id: str, item: ShelfItem, position: int, limits: Thresholds, parser: str | None,
          when: dt.datetime) -> dict:
    return {"run_id": run_id, "shelf_key": item.key, "kind": item.kind, "position": position, "state": "no_document",
            "document_id": None, "project_id": item.project_id, "document_type": item.document_type,
            "document_date": None, "pdf_pages": None, "pdf_url": None, "language": item.language, "part": item.part,
            "hard_page": None, "parser_pages": None, "count": None, "denominator": None, "denominator_from": None,
            "counted_on": None, "unreadable": False, "parts": None, "parser": parser,
            "parser_limit_pages": int(limits.value("ingestion.parser_part_pages")), "longest_pages": None,
            "read_pages": None, "daily_page_cap": int(limits.value("ingestion.daily_page_cap")),
            "measured_at": when, "public_from": when.date()}


def outcome(engine: Engine, run_id: str, item: ShelfItem, position: int, held: dict[str, Document],
            limits: Thresholds, parser: str | None, when: dt.datetime, selected: tuple[str, ...] = ()) -> Outcome:
    found = _base(run_id, item, position, limits, parser, when)
    limit = found["parser_limit_pages"]
    longest = max((document.pdf_pages for document in held.values()), default=None)
    found["longest_pages"] = longest
    if item.rule == "longest":
        # The longest of the slice's own projects (docs/PLAN.md section 3), not of the projects the slice
        # file names, such as the showcase in India.
        candidates = [d for d in held.values() if d.document_type == item.document_type and d.project_id in selected]
        document = max(candidates, key=lambda d: (d.pdf_pages, d.document_id), default=None)
    elif item.rule == "over_parser_limit":
        document = max((d for d in held.values() if d.pdf_pages > limit), key=lambda d: (d.pdf_pages, d.document_id),
                       default=None)
    else:
        document = held.get(item.document_id)
        if document is None:
            found |= {"state": "not_read", "document_id": item.document_id}
            return Outcome(**found)
    if document is None:
        return Outcome(**found)
    reader = Reader(engine, document)
    sent = reader.parser_pages
    found |= {"state": "read", "document_id": document.document_id, "project_id": document.project_id,
              "document_type": document.document_type, "document_date": document.document_date,
              "pdf_pages": document.pdf_pages, "pdf_url": document.pdf_url, "language": document.language,
              "parser_pages": len(sent), "read_pages": reader.read_pages()}
    stopped = int(engine.run(STOPPED, {"project_id": document.project_id, "day": when.date()}).rows[0][0]) > 0
    if reader.waiting() and stopped:
        found["state"] = "stopped_at_cap"
    passages = _rows(engine, DOCUMENT_PASSAGES, document_id=document.document_id)
    if item.kind == "scan_annex":
        span = range(item.first_page, item.last_page + 1)
        rows = [row for row in passages if row["kind"] == route_a.TABLE_ROW and row["pdf_page"] in span
                and _rated(row["cells"])]
        found |= {"hard_page": item.first_page, "count": len(rows),
                  "denominator": item.expected_rows, "denominator_from": "hand_count" if item.expected_rows else None,
                  "counted_on": item.counted_on,
                  "unreadable": not rows and all(n in reader.failed and n not in reader.layouts for n in span)}
    elif item.kind == "longest_pad":
        texts = {number: text for number, _, text in reader.pages}
        good = sum(1 for n in texts if (reader.read_well(n) if n in sent else bool(texts[n].strip())))
        found |= {"hard_page": min(sent) if sent else None, "count": good, "denominator": document.pdf_pages,
                  "denominator_from": "pdf_pages"}
    elif item.kind == "large_plan":
        texts = [row[0] for row in engine.run(PLAN_TEXT, {"document_id": document.document_id}).rows]
        listed = set(step.references_in(texts[0])) if texts else set()
        rows = {str(row[0]) for row in engine.run(PLAN_ROWS, {"document_id": document.document_id}).rows}
        found |= {"hard_page": min(sent) if sent else None, "count": len(listed & rows), "denominator": len(listed),
                  "denominator_from": "text_references"}
    elif item.kind == "other_language":
        numbered = [row["pdf_page"] for row in passages if row["paragraph_numbered"] and row["pdf_page"]]
        found |= {"hard_page": min(numbered) if numbered else None,
                  "count": sum(1 for row in passages if row["language"] == item.language),
                  "denominator": len(passages), "denominator_from": "passages_made"}
    elif item.kind == "over_parser_limit":
        texts = {number: text for number, _, text in reader.pages}
        published = route_a.split_pages(_published(engine, document), document.pdf_pages) or []
        shared = float(limits.value("ingestion.page_match_shared_words"))
        matched = 0
        for number in range(1, document.pdf_pages + 1):
            pdf = texts.get(number)
            if number in sent:
                layout = reader.layouts.get(number)
                matched += layout is not None and (not (pdf or "").strip() or _matches(_layout_words(layout), pdf, shared))
            elif number <= len(published) and pdf is not None:
                matched += _matches(published[number - 1], pdf, shared)
        found |= {"hard_page": limit + 1, "count": matched, "denominator": document.pdf_pages,
                  "denominator_from": "pdf_pages", "parts": route_b.parts(document.pdf_pages, limit)}
    return Outcome(**found)


def _rated(cells: str | None) -> bool:
    """Whether a table row is a rated risk: a row of a risk table that names its risk and gives its rating."""
    found = dict(json.loads(cells or "[]"))
    return bool(found.get("Risk")) and bool(found.get("Rating"))


def _published(engine: Engine, document: Document) -> str:
    texts = [row[0] for row in engine.run(PLAN_TEXT, {"document_id": document.document_id}).rows]
    return texts[0] if texts else ""


def record(engine: Engine, run_id: str, chosen: Slice, limits: Thresholds, parser: str | None,
           when: dt.datetime, selected: tuple[str, ...] = ()) -> list[Outcome]:
    """Each shelf entry's outcome, in the slice file's order, written to strata.ops.stress_shelf. selected
    holds the projects the slice criteria selected, from which the longest rule chooses."""
    held = documents(engine)
    found = [outcome(engine, run_id, item, position, held, limits, parser, when, selected)
             for position, item in enumerate(chosen.stress_shelf, 1)]
    engine.insert_rows("strata.ops.stress_shelf", COLUMNS, [astuple(row) for row in found])
    return found
