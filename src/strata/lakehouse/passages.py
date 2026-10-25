"""The document slice read into numbered passages and made searchable (tickets 11 and 18). It runs the
same on DuckDB in the gate and on the workspace's SQL warehouse.

For the slice's projects (config/slice.toml: the projects its criteria select from strata.gold.project,
with the showcase, the demo plan and the stress shelf's projects named first), a run:

1. Counts the projects the slice criteria select, and fetches each project's list from the documents API
   into bronze.document_lists, and each document of a type the reader has a template for
   (src/strata/reader/templates.py) into bronze.document_texts and bronze.document_pages, with the
   plan reader's fetcher (src/strata/lakehouse/plans.py), which takes out emails and labelled phone
   numbers first. It takes each project's ICR Reviews, ICRs, PADs and ISRs in that order, newest first,
   up to ingestion.passage_documents documents whose published text divides into their PDF's pages
   (config/thresholds.toml). A document already in bronze is not fetched again. A scan, whose text
   does not divide, is kept and does not count.
2. Gives each document its version of its report: a report re-issued under the same number, in the same
   language, has a second version, which replaces the first for current answers from the day it
   became public. A report in two languages is two documents, each the first version of its own.
3. Reads each document through the page router (src/strata/reader/passages.py): Route A reads the
   published text into page routes and passages; every page it sends to Route B, the layout parser
   (src/strata/lakehouse/route_b.py), is parsed once under the daily page cap, which the plan reader
   shares, and read into passages: a scan's paragraphs, a table's rows and its one summary, and a
   figure's text. Each passage has the short header that is prepended before embedding. These become
   silver.documents, silver.document_page_routes and silver.passages.
4. Reads the scope and qualification text of the projects' notices into passages
   (src/strata/lakehouse/notice_passages.py), and the ISRs' ratings into silver.isr_ratings
   (src/strata/lakehouse/isr_ratings.py), the rating history the projects API does not keep.
5. Scans each passage text the shield has not scanned (Prompt Shields on the workspace, an offline
   stand-in here) and keeps every result in silver.passage_shields. A hit is kept and counted.
6. Embeds each passage text, header first, that the model has not embedded, into
   silver.passage_embeddings, and syncs strata.gold.passage, the AI Search index's source table. Only
   a passage whose header or text changed is embedded again.
7. Checks a sample of the passages' languages against a language detector that reads only their words
   (src/strata/knowledge/language.py; ticket 42), into strata.ops.passage_language_checks.
8. Writes its data readiness measures to strata.ops.data_readiness: for each project, documents and
   pages per route and the pages each route read well, the pages whose paragraph numbering was found,
   the passages linked to a project, embedded and screened, Prompt Shields' hits, the documents with
   contact details taken out, and freshness; for the slice, the projects its criteria selected, with
   the difference from docs/PLAN.md's planned count and its reason. Documents and pages per type and
   fiscal year go to strata.ops.documents_read, and each stress shelf entry's outcome to
   strata.ops.stress_shelf (src/strata/lakehouse/stress_shelf.py).

Bronze only grows. Silver is rebuilt from bronze for each project of the run on every run. On the
workspace, ops/documents/run_live.py runs it with the live adapters and then syncs the index.

Run it on the fixture and print what it wrote:

    uv run --frozen python -m strata.lakehouse.passages
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import astuple, dataclass, fields

from strata.config import Slice, Thresholds, load_languages, load_slice, load_sources, load_thresholds
from strata.knowledge import language
from strata.knowledge.embed import Embedder
from strata.knowledge.sectors import main_sector
from strata.knowledge.shields import Shield
from strata.lakehouse import gold, isr_ratings, notice_passages, plans, route_b, stress_shelf
from strata.lakehouse.clean import fiscal_year
from strata.lakehouse.clean import public_from  # ADR 0002's rule, defined once for every source
from strata.lakehouse.engine import Engine
from strata.reader import passages as route_a
from strata.reader.documents import Documents, list_url
from strata.reader.layout import LayoutParser
from strata.reader.templates import TEMPLATES, template

SOURCE = "documents"  # the source registry's key for the documents API
# The Documents API's lang field, "French", to its ISO 639-1 code, from the language registry (config/languages.toml).
LANGUAGES = {entry.api_name: entry.code for entry in load_languages().languages}
UNDETERMINED = "und"  # ISO 639's code for a language the registry does not list


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _date(value) -> dt.date | None:
    """A date from DuckDB (a date or a timestamp) or from the warehouse or an API (ISO text)."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _rows(engine: Engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


# ── 1. The documents, chosen and fetched ─────────────────────────────────

@dataclass(frozen=True)
class Listed:
    """A document of a type the reader knows, as the project's latest document list gives it."""

    project_id: str
    document_id: str
    document_type: str
    report_number: str | None
    document_date: dt.date
    disclosed_on: dt.date | None
    language: str
    title: str | None
    text_url: str
    pdf_url: str
    listed_on: dt.date  # the day the list was fetched, the public date's fallback (ADR 0002)

    @property
    def public_from(self) -> dt.date:
        return public_from(self.disclosed_on, self.listed_on)

    def entry(self) -> plans.Entry:
        return plans.Entry(self.document_id, self.document_date, self.disclosed_on, self.text_url, self.pdf_url)


def listed_documents(engine: Engine, project_id: str) -> list[Listed]:
    """The project's documents of the reader's types in its latest list: by type, then newest first."""
    latest: dict[str, tuple] = {}
    for url, response, fetched in engine.run(
            "SELECT url, response, fetched_at FROM strata.bronze.document_lists WHERE project_id = :project_id "
            "ORDER BY fetched_at", {"project_id": project_id}).rows:
        latest[url] = (response, _date(fetched))
    found: dict[str, Listed] = {}
    for response, fetched in latest.values():
        for key, document in json.loads(response).get("documents", {}).items():
            if key == "facets" or not isinstance(document, dict) or document.get("docty") not in TEMPLATES:
                continue
            if not (document.get("txturl") and document.get("pdfurl") and document.get("docdt")):
                continue
            found[str(document["id"])] = Listed(
                project_id, str(document["id"]), document["docty"], document.get("repnb") or None,
                _date(document["docdt"]), _date(document.get("disclosure_date")),
                LANGUAGES.get(document.get("lang") or "", UNDETERMINED), document.get("display_title"),
                document["txturl"], document["pdfurl"], fetched)
    order = list(TEMPLATES)
    return sorted(found.values(), key=lambda d: (order.index(d.document_type), -d.document_date.toordinal(),
                                                 d.document_id))


@dataclass(frozen=True)
class Held:
    """A chosen document as bronze holds it, with each PDF page's number, text hash and text."""

    listed: Listed
    text: str
    pdf_pages: int
    public_from: dt.date
    paged: bool
    version: int = 1
    replaced_on: dt.date | None = None
    pages: tuple[tuple[int, str, str], ...] = ()

    @property
    def hashes(self) -> dict[int, str]:
        return {number: digest for number, digest, _ in self.pages}


HELD_TEXT = """
SELECT text, public_from FROM strata.bronze.document_texts WHERE document_id = :document_id ORDER BY fetched_at DESC
"""
HELD_PUBLIC_FROM = """
SELECT public_from FROM strata.bronze.document_texts WHERE document_id = :document_id ORDER BY fetched_at DESC
"""


def _held(engine: Engine, listed: Listed) -> Held | None:
    texts = _rows(engine, HELD_TEXT, document_id=listed.document_id)
    if not texts:
        return None
    pages = tuple(route_b.page_texts(engine, listed.document_id))
    text = texts[0]["text"]
    return Held(listed, text, len(pages), _date(texts[0]["public_from"]),
                route_a.split_pages(text, len(pages)) is not None, pages=pages)


@dataclass(frozen=True)
class Chosen:
    documents: list[Held]
    # For each project, the documents this run fetched whose text had contact details taken out, and
    # the documents it fetched.
    with_contacts: dict[str, tuple[int, int]]


HELD_WITH_CONTACTS = """
SELECT DISTINCT document_id FROM strata.bronze.document_texts WHERE project_id = :project_id AND text LIKE :marker
"""


def with_contacts_held(engine: Engine, chosen: list[Held]) -> dict[str, tuple[int, int]]:
    """For each project, the chosen documents whose text bronze keeps with contact details taken out, and the
    chosen documents. Bronze fetches a document once, so counting what this run fetched would read 0 of 0 on
    every run after the first (ticket 11's review, P1); counting what bronze holds gives the same share each night."""
    from strata.lakehouse.contacts import REMOVED

    found: dict[str, tuple[int, int]] = {}
    for project_id in dict.fromkeys(held.listed.project_id for held in chosen):
        ids = {held.listed.document_id for held in chosen if held.listed.project_id == project_id}
        marked = {str(row[0]) for row in engine.run(HELD_WITH_CONTACTS, {"project_id": project_id,
                                                                        "marker": f"%{REMOVED}%"}).rows}
        found[project_id] = (len(ids & marked), len(ids))
    return found


def choose(engine: Engine, documents: Documents, endpoint: str, projects: list[str], cap: int) -> Chosen:
    """The documents to read, fetched into bronze: up to cap whose text Route A can read, and any
    scan met on the way, whose pages wait for Route B."""
    chosen, paged, removed, lists = [], 0, {}, {}
    for project_id in projects:
        if paged >= cap:
            break
        plans.fetch_listing(engine, documents, endpoint, project_id)
        listed = lists[project_id] = listed_documents(engine, project_id)
        for document in listed:
            if paged >= cap:
                break
            fetching = plans.fetch_documents(engine, documents, project_id, [document.entry()])
            count, fetched = removed.get(project_id, (0, 0))
            removed[project_id] = (count + fetching.with_contacts, fetched + fetching.fetched)
            held = _held(engine, document)
            if held is None:
                continue  # listed but not fetched: the source could not give it
            chosen.append(held)
            paged += held.paged
    return Chosen([_versioned(engine, held, lists[held.listed.project_id]) for held in chosen], removed)


def _versioned(engine: Engine, held: Held, listed: list[Listed]) -> Held:
    """The document's version of its report, and the day the next version replaced it: the next
    version's own public date as bronze holds it, so one version is current every day. The list's
    date is used only for a next version bronze does not hold."""
    document = held.listed
    if document.report_number is None:
        return held
    # A re-issue is in the same language: the same report in French and in English is two documents.
    issues = sorted((d for d in listed if (d.document_type, d.report_number, d.language) == (
        document.document_type, document.report_number, document.language)),
                    key=lambda d: (d.document_date, d.public_from, d.document_id))
    at = next(i for i, d in enumerate(issues) if d.document_id == document.document_id)
    replaced = None
    if at + 1 < len(issues):
        following = issues[at + 1]
        kept = _rows(engine, HELD_PUBLIC_FROM, document_id=following.document_id)
        replaced = _date(kept[0]["public_from"]) if kept else following.public_from
    return Held(held.listed, held.text, held.pdf_pages, held.public_from, held.paged, at + 1, replaced, held.pages)


# ── 3. The page router, Route A and Route B ──────────────────────────────

@dataclass(frozen=True)
class Project:
    """What a passage's header says about its project, and the sector search filters on."""

    project_id: str
    country: str | None
    sector: str | None  # the header's word, such as roads
    slice_sector: str | None = None  # its one sector in strata.gold.project, such as water


PROJECT = """
SELECT p.project_id, c.country_name, p.sector_codes, p.sector
FROM strata.gold.project AS p
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
WHERE p.project_id = :project_id
"""


def project(engine: Engine, project_id: str) -> Project:
    found = _rows(engine, PROJECT, project_id=project_id)
    if not found:
        return Project(project_id, None, None)
    sector = found[0]["sector"]  # its one sector in Strata's taxonomy (config/sectors.toml)
    code = main_sector(found[0]["sector_codes"], sector)
    return Project(project_id, found[0]["country_name"], code.word if code else None, sector)


def header(short_name: str, project: Project, passage: route_a.Passage) -> str:
    """The short header prepended before embedding: ICR, P130164, India, roads, III.B, ¶54, p.23."""
    parts = [short_name, project.project_id, project.country, project.sector, passage.section_path,
             f"¶{passage.paragraph}" if passage.paragraph_numbered else None, f"p.{passage.pdf_page}"]
    return ", ".join(part for part in parts if part)


def table_header(short_name: str, project: Project, item: route_b.TablePassage) -> str:
    """A table row's header names its table and row ("PAD, P130164, India, roads, Annex 4 - Operational
    Risk Assessment Framework (ORAF), row 2, p.65"), and a summary says it is one."""
    place = f"row {item.row.number}" if item.row else "summary"
    parts = [short_name, project.project_id, project.country, project.sector, item.table.title or None, place,
             f"p.{item.pdf_page}"]
    return ", ".join(part for part in parts if part)


def embedded_text(header_line: str, text: str) -> str:
    """What gets embedded and scanned: the header, a line break, then the passage."""
    return f"{header_line}\n{text}"


def doc_key(listed: Listed, others: list[Listed]) -> str:
    """The document's key in its project, as an address names it: its type's short name and its date,
    icr-2019-10-10, with -2 for the second document of that type on that date (by document id)."""
    slug = "-".join(TEMPLATES[listed.document_type].short_name.lower().split())
    same = sorted(d.document_id for d in others
                  if (d.document_type, d.document_date) == (listed.document_type, listed.document_date))
    at = same.index(listed.document_id) + 1 if listed.document_id in same else 1
    return f"{slug}-{listed.document_date.isoformat()}" + (f"-{at}" if at > 1 else "")


DOCUMENT_COLUMNS = ("document_id", "project_id", "document_type", "report_number", "version", "document_date",
                    "disclosed_on", "language", "title", "pdf_pages", "text_paged", "text_url", "pdf_url",
                    "replaced_on", "doc_key", "parse_parts", "public_from")
ROUTE_COLUMNS = ("document_id", "project_id", "pdf_page", "route", "reason", "printed_page", "numbering_found",
                 "passages", "part", "public_from")


@dataclass(frozen=True)
class PassageRow:
    """One row of silver.passages."""

    passage_id: str
    document_id: str
    project_id: str
    document_type: str
    version: int
    section_path: str
    paragraph: str
    paragraph_numbered: bool
    part: int
    parts: int
    pdf_page: int | None
    last_pdf_page: int | None
    printed_page: str | None
    language: str
    parse_route: str
    kind: str
    scanned: bool
    table_title: str | None
    table_row: int | None
    cells: str | None
    sector: str | None
    header: str
    text: str
    tokens: int
    text_hash: str
    public_from: dt.date


PASSAGE_COLUMNS = tuple(f.name for f in fields(PassageRow))


@dataclass(frozen=True)
class Read:
    """One document as the run read it: its page routes and its passages, from both routes."""

    held: Held
    routes: tuple[route_a.PageRoute, ...]
    passages: tuple[PassageRow, ...]
    parsed: frozenset[int]  # the PDF pages the layout parser read, with something recovered


def _route_a(held: Held, max_tokens: int) -> route_a.Reading:
    return route_a.read(held.text, held.pdf_pages, template(held.listed.document_type, held.listed.language), max_tokens,
                        page_texts=[text for _, _, text in held.pages])


def parse_route_b(engine: Engine, layout: LayoutParser, readings: list[tuple[Held, route_a.Reading]], cap: int,
                  part_pages: int, clock: Callable[[], dt.datetime], run_id: str) -> None:
    """Each project's Route B pages, parsed once under the daily page cap, document by document in the
    run's order, each long document part by part, with one row of strata.ops.parse_runs per project."""
    by_project: dict[str, list] = {}
    for held, reading in readings:
        listed = held.listed
        by_project.setdefault(listed.project_id, []).extend(
            route_b.waiting(listed.document_id, listed.project_id, listed.pdf_url, held.public_from, reading.pages,
                            held.hashes))
    for project_id, pages in by_project.items():
        if not pages:
            continue
        started = clock()
        parsing = plans.parse_pages(engine, layout, project_id, pages, cap, clock, run_id)
        plans.record_parse_run(engine, run_id, project_id, parsing, started, clock())


def read_documents(engine: Engine, chosen: list[Held], max_tokens: int, run_projects: list[str],
                   readings: list[tuple[Held, route_a.Reading]] | None = None, part_pages: int | None = None) -> list[Read]:
    """Each chosen document read through Route A and Route B, then written to silver, which is rebuilt
    for every project of the run: a project the cap left out this time keeps no passages from an
    earlier run."""
    readings = readings if readings is not None else [(held, _route_a(held, max_tokens)) for held in chosen]
    projects = {held.listed.project_id: project(engine, held.listed.project_id) for held in chosen}
    lists: dict[str, list[Listed]] = {}
    for held in chosen:
        lists.setdefault(held.listed.project_id, []).append(held.listed)
    for project_id in dict.fromkeys([*run_projects, *projects]):
        for table in ("documents", "document_page_routes", "passages"):
            engine.run(f"DELETE FROM strata.silver.{table} WHERE project_id = :project_id",  # sql-lint: names only
                       {"project_id": project_id})
    documents, routes, found = [], [], []
    for held, reading in readings:
        listed = held.listed
        reads = template(listed.document_type, listed.language)
        hashes = held.hashes
        parsed = route_b.layouts(engine, listed.document_id, hashes)
        second = route_b.read(reading.pages, parsed, reads, max_tokens, listed.document_type)
        long = part_pages is not None and held.pdf_pages > part_pages
        documents.append((listed.document_id, listed.project_id, listed.document_type, listed.report_number,
                          held.version, listed.document_date, listed.disclosed_on, listed.language, listed.title,
                          held.pdf_pages, held.paged, listed.text_url, listed.pdf_url, held.replaced_on,
                          doc_key(listed, lists[listed.project_id]),
                          route_b.parts(held.pdf_pages, part_pages) if long else 1, held.public_from))
        routes += [(listed.document_id, listed.project_id, page.pdf_page, page.route, page.reason, page.printed_page,
                    page.numbering_found, page.passages,
                    route_b.part_of(page.pdf_page, part_pages) if long else 1, held.public_from)
                   for page in second.routes]
        about = projects[listed.project_id]
        rows = []

        def add(key, section, paragraph, numbered, part, parts_, first, last, printed, route, kind, scanned, line,
                text, title=None, row=None, cells=None):
            rows.append(PassageRow(f"{listed.document_id}/v{held.version}/{key}", listed.document_id,
                                   listed.project_id, listed.document_type, held.version, section, paragraph,
                                   numbered, part, parts_, first, last, printed, listed.language, route, kind,
                                   scanned, title, row, cells, about.slice_sector, line, text, route_a.tokens(text),
                                   route_a.text_hash(embedded_text(line, text)), held.public_from))

        for passage in reading.passages:
            add(passage.key, passage.section_path, passage.paragraph, passage.paragraph_numbered, passage.part,
                passage.parts, passage.pdf_page, passage.last_pdf_page, passage.printed_page, route_a.ROUTE_A,
                route_a.PARAGRAPH, False, header(reads.short_name, about, passage), passage.text)
        for passage in second.paragraphs:
            add(passage.key, passage.section_path, passage.paragraph, passage.paragraph_numbered, passage.part,
                passage.parts, passage.pdf_page, passage.last_pdf_page, passage.printed_page, route_a.ROUTE_B,
                route_a.PARAGRAPH, True, header(reads.short_name, about, passage), passage.text)
        for item in second.tables:
            add(item.key, item.table.title, item.key, False, 1, 1, item.pdf_page, item.last_pdf_page, None,
                route_a.ROUTE_B, item.kind, not held.paged, table_header(reads.short_name, about, item), item.text,
                item.table.title or None, item.row.number if item.row else None, route_b.cells_json(item.row))
        found.append(Read(held, second.routes, tuple(rows),
                          frozenset(n for n, layout in parsed.items() if route_b.read_well(layout))))
    engine.insert_rows("strata.silver.documents", DOCUMENT_COLUMNS, documents)
    engine.insert_rows("strata.silver.document_page_routes", ROUTE_COLUMNS, routes)
    engine.insert_rows("strata.silver.passages", PASSAGE_COLUMNS, [astuple(row) for item in found for row in item.passages])
    return found


def read_notices(engine: Engine, projects: list[str], notice_types: tuple[str, ...], max_tokens: int) -> int:
    """The scope and qualification text of the projects' notices, as passages of the kind notice_text.
    Returns how many passages it wrote."""
    rows = []
    about = {project_id: project(engine, project_id) for project_id in projects}
    for notice in notice_passages.notices(engine, projects, notice_types):
        place = about[notice.project_id]
        language = LANGUAGES.get(notice.language or "", UNDETERMINED)
        for section in notice_passages.sections(notice.text, max_tokens):
            line = ", ".join(part for part in (f"Notice {notice.notice_id}", notice.project_id, place.country,
                                               place.sector, notice.notice_type, section.name) if part)
            rows.append(PassageRow(f"{notice.notice_id}/v1/{section.key}", notice.notice_id, notice.project_id,
                                   notice.notice_type, 1, section.name, section.key.split("/")[0], False, section.part,
                                   section.parts, None, None, None, language, route_a.ROUTE_A, route_a.NOTICE_TEXT,
                                   False, None, None, None, place.slice_sector, line, section.text,
                                   route_a.tokens(section.text), route_a.text_hash(embedded_text(line, section.text)),
                                   _date(notice.public_from)))
    engine.insert_rows("strata.silver.passages", PASSAGE_COLUMNS, [astuple(row) for row in rows])
    return len(rows)


# ── 4. Prompt Shields ────────────────────────────────────────────────────

WAITING_FOR_SHIELD = """
SELECT p.text_hash, min(p.header) AS header, min(p.text) AS text, min(p.public_from) AS public_from
FROM strata.silver.passages AS p
WHERE NOT EXISTS (SELECT 1 FROM strata.silver.passage_shields AS s
                  WHERE s.text_hash = p.text_hash AND s.shield = :shield)
GROUP BY p.text_hash
"""
SCANNED = """
SELECT p.project_id, p.passage_id, s.attack_detected
FROM strata.silver.passages AS p
LEFT JOIN strata.silver.passage_shields AS s ON s.text_hash = p.text_hash AND s.shield = :shield
"""


def screen(engine: Engine, shield: Shield, clock: Callable[[], dt.datetime]) -> int:
    """Scan each passage text the shield has not scanned, and keep each result. Returns how many it scanned."""
    waiting = _rows(engine, WAITING_FOR_SHIELD, shield=shield.name)
    scans = shield.scan([embedded_text(row["header"], row["text"]) for row in waiting]) if waiting else []
    when = clock()
    engine.insert_rows("strata.silver.passage_shields",
                       ("text_hash", "shield", "attack_detected", "detail", "scanned_at", "public_from"),
                       [(row["text_hash"], shield.name, scan.attack_detected, scan.detail, when, row["public_from"])
                        for row, scan in zip(waiting, scans, strict=True)])
    return len(waiting)


# ── 5. Embeddings, and the passages in gold ──────────────────────────────

WAITING_FOR_VECTOR = """
SELECT p.text_hash, min(p.header) AS header, min(p.text) AS text, min(p.public_from) AS public_from
FROM strata.silver.passages AS p
WHERE NOT EXISTS (SELECT 1 FROM strata.silver.passage_embeddings AS e
                  WHERE e.text_hash = p.text_hash AND e.model = :model)
GROUP BY p.text_hash
"""
VECTOR_COLUMNS = ("text_hash", "model", "dimensions", "embedding", "embedded_at", "public_from")
VECTORS_PER_CALL = 64  # passages the embedder is asked for at once, so a failure loses little


def store_vectors(engine: Engine, rows: list[tuple]) -> int:
    """Append vectors to silver.passage_embeddings. DuckDB and Spark take a list of numbers as it is. The
    SQL warehouse binds only single values, so each vector goes to it as JSON text, which from_json reads."""
    from strata.lakehouse.engine import WarehouseEngine

    if not isinstance(engine, WarehouseEngine):
        return engine.insert_rows("strata.silver.passage_embeddings", VECTOR_COLUMNS, rows)
    for start in range(0, len(rows), plans.WAREHOUSE_CHUNK):
        params, values = {}, []
        for n, (text_hash, model, dimensions, embedding, embedded_at, public) in enumerate(
                rows[start:start + plans.WAREHOUSE_CHUNK]):
            params |= {f"h{n}": text_hash, f"m{n}": model, f"d{n}": dimensions, f"e{n}": json.dumps(embedding),
                       f"t{n}": embedded_at, f"p{n}": public}
            values.append(f"(:h{n}, :m{n}, :d{n}, from_json(:e{n}, 'ARRAY<FLOAT>'), :t{n}, :p{n})")
        engine.run(f"INSERT INTO strata.silver.passage_embeddings ({', '.join(VECTOR_COLUMNS)}) "  # sql-lint: names only
                   f"VALUES {', '.join(values)}", params)  # sql-lint: names only
    return len(rows)


def embed(engine: Engine, embedder: Embedder, clock: Callable[[], dt.datetime]) -> int:
    """Embed each passage text, with its header in front, that the model has not embedded. Returns how many."""
    waiting = _rows(engine, WAITING_FOR_VECTOR, model=embedder.name)
    for start in range(0, len(waiting), VECTORS_PER_CALL):
        batch = waiting[start:start + VECTORS_PER_CALL]
        vectors = embedder.embed([embedded_text(row["header"], row["text"]) for row in batch])
        when = clock()
        store_vectors(engine, [(row["text_hash"], embedder.name, embedder.dimensions, vector, when, row["public_from"])
                               for row, vector in zip(batch, vectors, strict=True)])
    return len(waiting)


# ── The slice ────────────────────────────────────────────────────────────

SLICE = """
SELECT project_id, country_code
FROM strata.gold.project
WHERE array_contains(split(:countries, ','), country_code)
  AND array_contains(split(:sectors, ','), sector)
  AND approval_fiscal_year BETWEEN :first AND :last
ORDER BY project_id
"""


@dataclass(frozen=True)
class Selection:
    """The slice's projects: those its criteria select from strata.gold.project, by country, and those
    the slice file names (the showcase, the demo plan and the stress shelf's), which the run reads
    whatever the criteria select."""

    selected: tuple[str, ...]
    by_country: dict[str, int]  # each slice country's name and how many projects it has in the slice
    named: tuple[str, ...]
    planned: int | None  # docs/PLAN.md section 3's planned count, never shown as a finding

    @property
    def projects(self) -> tuple[str, ...]:
        """The run's projects: the named ones first, then the selected ones, once each."""
        return tuple(dict.fromkeys([*self.named, *self.selected]))

    def detail(self, chosen: Slice) -> str:
        """The slice count as a sentence for strata.ops.data_readiness, with the difference from the
        planned count and its reason."""
        names = [country.name for country in chosen.countries]
        counts = ", ".join(f"{name} {self.by_country.get(name, 0)}" for name in names)
        said = (f"The slice criteria (the {' and '.join(chosen.sectors)} projects of {_listed(names)} with a Board "
                f"date in fiscal {chosen.first_fiscal_year} to {chosen.last_fiscal_year}) selected {len(self.selected)} "
                f"projects from strata.gold.project: {counts}.")
        if self.planned is None or self.planned == len(self.selected):
            return said
        gap = len(self.selected) - self.planned
        empty = [name for name in names if not self.by_country.get(name)]
        reason = (f" strata.gold.project holds no such project for {_listed(empty)}." if empty else "")
        return (f"{said} docs/PLAN.md section 3 planned {self.planned}, {abs(gap)} {'more' if gap > 0 else 'fewer'}."
                f"{reason} Each project counts once, in the one sector that config/sectors.toml maps its largest "
                "share to, so a project whose largest share is in another sector is left out.")


def _listed(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}" if items else "none"


def select(engine: Engine, chosen: Slice) -> Selection:
    """The projects the slice criteria select from strata.gold.project at run time."""
    rows = engine.run(SLICE, {"countries": ",".join(c.iso2 for c in chosen.countries),
                              "sectors": ",".join(chosen.sectors), "first": chosen.first_fiscal_year,
                              "last": chosen.last_fiscal_year}).rows
    names = {country.iso2: country.name for country in chosen.countries}
    by_country = Counter(names[str(code)] for _, code in rows)
    return Selection(tuple(str(project_id) for project_id, _ in rows), dict(by_country), chosen.named_projects,
                     chosen.planned_projects)


# ── Data readiness ───────────────────────────────────────────────────────

MEASURE_COLUMNS = ("run_id", "source", "subject", "measure", "kind", "count", "denominator", "as_of", "detail",
                   "measured_at", "public_from")
DOCUMENTS_READ_COLUMNS = ("run_id", "document_type", "fiscal_year", "documents", "pdf_pages", "pages_route_a",
                          "pages_route_b", "pages_read_well_route_a", "pages_read_well_route_b", "measured_at",
                          "public_from")
PASSAGE_COUNTS = """
SELECT project_id, kind = :notice AS notice, count(*) AS n FROM strata.silver.passages GROUP BY project_id, kind = :notice
"""


def _read_well_a(item: Read) -> int:
    """The pages of published text with text on them."""
    texts = {number: text for number, _, text in item.held.pages}
    return sum(1 for page in item.routes if page.route == route_a.ROUTE_A and texts.get(page.pdf_page, "").strip())


def _read_well_b(item: Read) -> int:
    """The pages the layout parser read and recovered something from."""
    return sum(1 for page in item.routes if page.route == route_a.ROUTE_B and page.pdf_page in item.parsed)


def documents_read(engine: Engine, run_id: str, found: list[Read], when: dt.datetime) -> int:
    """Documents and pages per document type and fiscal year of disclosure (July to June), with the
    pages each route read and read well, in strata.ops.documents_read."""
    groups: dict[tuple, list[Read]] = {}
    for item in found:
        listed = item.held.listed
        groups.setdefault((listed.document_type, fiscal_year(listed.disclosed_on or item.held.public_from)),
                          []).append(item)
    rows = []
    for (document_type, year), items in sorted(groups.items(), key=lambda pair: (pair[0][0], pair[0][1] or 0)):
        rows.append((run_id, document_type, year, len(items), sum(item.held.pdf_pages for item in items),
                     sum(1 for item in items for page in item.routes if page.route == route_a.ROUTE_A),
                     sum(1 for item in items for page in item.routes if page.route == route_a.ROUTE_B),
                     sum(_read_well_a(item) for item in items), sum(_read_well_b(item) for item in items),
                     when, when.date()))
    return engine.insert_rows("strata.ops.documents_read", DOCUMENTS_READ_COLUMNS, rows)


def measure(engine: Engine, run_id: str, found: list[Read], with_contacts: dict[str, tuple[int, int]],
            shield: str, when: dt.datetime, selection: Selection | None = None, chosen: Slice | None = None) -> int:
    """The run's data readiness measures, each a count with its denominator, written to
    strata.ops.data_readiness. For each project: documents and pages per route, the pages each route
    read well, the pages whose paragraph numbering was found, the passages linked to a project,
    freshness, the contact details taken out, and what Prompt Shields found. For the slice: the
    projects its criteria selected, with each country's count in its detail sentence, and how many of them
    the run read documents for."""
    linked = {str(row[0]) for row in engine.run("SELECT project_id FROM strata.gold.project").rows}
    indexed = {str(project): int(count) for project, count in engine.run(
        "SELECT project_id, count(*) AS n FROM strata.gold.passage GROUP BY project_id").rows}
    made: dict[str, int] = {}  # every passage of a project, notices' text included
    reports: dict[str, int] = {}  # its reports' passages
    notices: dict[str, int] = {}  # its notices' text
    for project, notice, count in engine.run(PASSAGE_COUNTS, {"notice": route_a.NOTICE_TEXT}).rows:
        made[str(project)] = made.get(str(project), 0) + int(count)
        (notices if notice else reports)[str(project)] = int(count)
    scanned: dict[str, list] = {}
    for row in _rows(engine, SCANNED, shield=shield):
        scanned.setdefault(row["project_id"], []).append(row["attack_detected"])
    cadence = load_sources()[SOURCE].cadence
    rows = []

    def add(subject, name, kind, count, denominator, detail, as_of=None):
        rows.append((run_id, SOURCE, subject, name, kind, count, denominator, as_of, detail, when, when.date()))

    for project_id in dict.fromkeys(item.held.listed.project_id for item in found):
        items = [item for item in found if item.held.listed.project_id == project_id]
        reported = reports.get(project_id, 0)
        pages = [page for item in items for page in item.routes]
        on_a = [page for page in pages if page.route == route_a.ROUTE_A]
        # The body pages of the reports that number their paragraphs: an ISR numbers none of its own.
        body = [page for item in items if TEMPLATES[item.held.listed.document_type].numbered
                for page in item.routes if page.route == route_a.ROUTE_A and page.reason == route_a.BODY]
        passages = made.get(project_id, 0)
        stripped, fetched = with_contacts.get(project_id, (0, 0))

        def per(name, kind, count, denominator, detail, as_of=None):
            add(project_id, name, kind, count, denominator, detail, as_of)

        per("documents_read", "coverage", len(items), len(items),
            "This counts the documents the run read, through either route.")
        per("documents_read_projects", "coverage", 1, 1,
            "This counts the project once, because the run read at least one of its documents.")
        per("document_pages_read_well", "read_well", sum(_read_well_a(item) + _read_well_b(item) for item in items),
            len(pages), "This counts the pages read well across both routes, out of every page of the documents "
            "read: a page of published text that has text, and a page the layout parser recovered a table or "
            "text from.")
        per("documents_read_route_a_text", "coverage", sum(item.held.paged for item in items), len(items),
            "This counts the documents whose published text divides into their PDF's pages, so Route A read "
            "them, out of the documents chosen. The others are scans, whose pages go to Route B.")
        per("document_pages_route_a", "read_well", len(on_a), len(pages),
            "This counts the pages Route A read from the published text, out of every page of the documents "
            "chosen.")
        per("document_pages_route_b", "read_well", len(pages) - len(on_a), len(pages),
            "This counts the pages the page router sent to Route B, the layout parser, out of every page of the "
            "documents chosen. They are scans, data sheets, risk tables and pages with no text.")
        per("document_pages_read_route_a", "read_well", sum(_read_well_a(item) for item in items), len(on_a),
            "This counts the pages of published text that have text, out of the pages Route A read.")
        per("document_pages_read_route_b", "read_well", sum(_read_well_b(item) for item in items),
            len(pages) - len(on_a), "This counts the pages the layout parser read and recovered a table or text "
            "from, out of the pages the page router sent to it.")
        per("document_pages_paragraph_numbering_found", "read_well", sum(page.numbering_found for page in body),
            len(body), "This counts the body pages on which Route A found a paragraph the report numbers, out of "
            "the body pages Route A read of the PADs, ICRs and ICR Reviews. An ISR numbers none of its "
            "paragraphs, so its pages are not counted.")
        per("passages_linked_to_project", "linked", reported if project_id in linked else 0, reported,
            "This counts the reports' passages whose project record is held, out of every passage read from them.")
        per("passages_embedded", "coverage", indexed.get(project_id, 0), passages,
            "This counts the passages that have a vector and can be searched, out of every passage read.")
        per("documents_fresh", "fresh", None, None, cadence, as_of=max(item.held.public_from for item in items))
        per("contact_details_removed", "stripped", stripped, fetched,
            "This counts the documents read that had emails or phone numbers removed before they were kept, out "
            "of the documents read.")
        results = scanned.get(project_id, [])
        per("passages_screened", "screened", sum(result is not None for result in results), len(results),
            f"This counts the passages that have a stored result from {shield}, out of every passage read.")
        per("passages_prompt_shields_hit", "screened", sum(result is True for result in results), len(results),
            f"This counts the passages in which {shield} found a prompt attack, out of every passage read. "
            "They are kept, and search leaves them out.")
    for project_id, count in notices.items():
        rows.append((run_id, SOURCE, project_id, "notice_text_passages", "coverage", count, count, None,
                     "This counts the sections of the project's notices' scope and qualification text read into "
                     "passages.", when, when.date()))
        rows.append((run_id, SOURCE, project_id, "notice_text_linked", "linked", count if project_id in linked else 0,
                     count, None, "This counts the sections of notices' text whose project record is held, out of "
                     "every section read.", when, when.date()))
    if selection is not None and chosen is not None:
        add("all", "slice_projects", "coverage", len(selection.selected), None, selection.detail(chosen))
        read = {item.held.listed.project_id for item in found}
        add("all", "slice_projects_read", "coverage", sum(project in read for project in selection.selected),
            len(selection.selected), "This counts the projects the slice criteria selected of which the run read at "
            "least one document, out of the projects they selected. A project whose documents wait for a later run "
            "under the daily page cap, or that lists no document of a type the reader knows, is not counted.")
    engine.insert_rows("strata.ops.data_readiness", MEASURE_COLUMNS, rows)
    return len(rows)


# ── The run ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Report:
    run_id: str
    documents: int  # documents read whose text Route A could read
    scans: int  # documents whose pages all go to Route B
    passages: int
    scanned: int  # passage texts the shield scanned this run
    embedded: int  # passage texts the embedder embedded this run
    slice_projects: int = 0  # the projects the slice criteria selected
    notice_passages: int = 0
    shelf: tuple = ()  # each stress shelf entry's outcome (stress_shelf.Outcome)
    synced: int = 0  # rows of strata.gold.passage the run added, changed or removed


def run(engine: Engine, documents: Documents, projects: list[str] | None = None, *, shield: Shield,
        embedder: Embedder, layout: LayoutParser | None = None, thresholds: Thresholds | None = None,
        endpoint: str | None = None, clock: Callable[[], dt.datetime] = _now, run_id: str | None = None,
        chosen: Slice | None = None, detector: language.Detector | None = None) -> Report:
    """Read the slice's documents into passages. See the module's docstring for the steps. Without a
    layout parser, the pages the router sends to Route B wait for a run that has one."""
    limits = thresholds or load_thresholds()
    endpoint = endpoint or load_sources()[SOURCE].endpoint
    chosen = chosen or load_slice()
    selection = select(engine, chosen)
    projects = list(selection.projects) if projects is None else projects
    started = clock()
    run_id = run_id or f"passages-{started:%Y%m%dT%H%M%S%f}"
    max_tokens = int(limits.value("passages.max_tokens"))
    part_pages = int(limits.value("ingestion.parser_part_pages"))
    picked = choose(engine, documents, endpoint, projects, int(limits.value("ingestion.passage_documents")))
    readings = [(held, _route_a(held, max_tokens)) for held in picked.documents]
    if layout is not None:
        parse_route_b(engine, layout, readings, int(limits.value("ingestion.daily_page_cap")), part_pages, clock,
                      run_id)
    found = read_documents(engine, picked.documents, max_tokens, projects, readings, part_pages)
    notices = read_notices(engine, projects, chosen.notice_types, max_tokens)
    isr_ratings.write(engine, projects)
    scanned = screen(engine, shield, clock)
    embedded = embed(engine, embedder, clock)
    synced = gold.sync(engine, "passage")
    when = clock()
    measure(engine, run_id, found, with_contacts_held(engine, picked.documents), shield.name, when, selection, chosen)
    language.check(engine, run_id, when, limits, detector)
    documents_read(engine, run_id, found, when)
    shelf = stress_shelf.record(engine, run_id, chosen, limits, layout.name if layout else None, when,
                                selection.selected)
    return Report(run_id, sum(item.held.paged for item in found), sum(not item.held.paged for item in found),
                  sum(len(item.passages) for item in found), scanned, embedded, len(selection.selected), notices,
                  tuple(shelf), synced)


def default_projects(engine: Engine | None = None) -> list[str]:
    """The slice's projects: those the slice file names, then, given an engine, those its criteria select
    from strata.gold.project (config/slice.toml)."""
    chosen = load_slice()
    if engine is None:
        return list(chosen.named_projects)
    return list(select(engine, chosen).projects)


def run_on_fixture(engine: Engine, manifest=None, **options) -> Report:
    """The run over the recorded fixture, with the offline document source and layout parser, for each
    slice project whose document list the fixture records."""
    from strata.fixture import recorded as fmt
    from strata.knowledge.embed import offline
    from strata.knowledge.shields import PatternShield
    from strata.reader.documents import RecordedDocuments
    from strata.reader.layout import RecordedLayout

    manifest = manifest or fmt.load_manifest()
    options.setdefault("shield", PatternShield())
    options.setdefault("embedder", offline())
    options.setdefault("layout", RecordedLayout(manifest))
    documents = RecordedDocuments(manifest)
    endpoint = options.get("endpoint") or load_sources()[SOURCE].endpoint
    return run(engine, documents, listed_projects(documents, options.pop("projects", None) or default_projects(engine),
                                                  endpoint), **options)


def listed_projects(documents: Documents, projects: list[str], endpoint: str | None = None) -> list[str]:
    """The projects whose document list the source gives: offline, those the fixture records."""
    from strata.reader.documents import NotFetched

    endpoint = endpoint or load_sources()[SOURCE].endpoint
    found = []
    for project_id in projects:
        try:
            documents.listing(list_url(endpoint, project_id))
            found.append(project_id)
        except NotFetched:
            continue
    return found


def print_measures(engine: Engine, run_id: str) -> None:
    """The run's data readiness measures, one a line."""
    for row in _rows(engine, "SELECT subject, measure, count, denominator, as_of FROM strata.ops.data_readiness "
                             "WHERE run_id = :run_id AND source = :source ORDER BY subject, measured_at, measure",
                     run_id=run_id, source=SOURCE):
        shown = f"as of {row['as_of']}" if row["as_of"] else f"{row['count']} of {row['denominator']}"
        print(f"  {row['subject']} {row['measure']}: {shown}")


def _print_fixture_run() -> int:
    from strata.lakehouse import catalog, nightly
    from strata.lakehouse.engine import DuckDBEngine

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        nightly.run_locally(engine)
        report = run_on_fixture(engine)
        print(f"Run {report.run_id} read {report.documents} documents into {report.passages} passages. "
              f"{report.scans} more had no text Route A could read, so their pages wait for Route B.")
        print_measures(engine, report.run_id)
    return 0


if __name__ == "__main__":
    sys.exit(_print_fixture_run())
