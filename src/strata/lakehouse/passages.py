"""The first documents read into numbered passages and made searchable (ticket 11). It runs the same
on DuckDB in the gate and on the workspace's SQL warehouse.

For the showcase project and then the demo plan's project (config/slice.toml), a run:

1. Fetches the project's list from the documents API into bronze.document_lists, and each document of
   a type the reader has a template for (src/strata/reader/templates.py) into bronze.document_texts and
   bronze.document_pages, with the plan reader's fetcher (src/strata/lakehouse/plans.py). It takes each
   project's ICR Reviews, ICRs, PADs and ISRs in that order, newest first, and stops when it holds
   ingestion.passage_documents documents whose published text divides into their PDF's pages
   (config/thresholds.toml). A document already in bronze is not fetched again. A document whose text
   does not divide, such as a scan, is kept with every page routed to Route B, and does not count.
2. Gives each document its version of its report: a report re-issued under the same number has a
   second version, which replaces the first for current answers from the day it became public.
3. Reads each document through Route A (src/strata/reader/passages.py) into page routes and passages,
   each passage with the short header that is prepended before embedding. These become
   silver.documents, silver.document_page_routes and silver.passages.

Bronze only grows. Silver is rebuilt from bronze for each project on every run.

Run it on the fixture and print what it wrote:

    uv run --frozen python -m strata.lakehouse.passages
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass

from strata.config import Thresholds, load_slice, load_sources, load_thresholds
from strata.knowledge.sectors import main_sector
from strata.lakehouse import plans
from strata.lakehouse.clean import public_from  # ADR 0002's rule, defined once for every source
from strata.lakehouse.engine import Engine
from strata.reader import passages as route_a
from strata.reader.documents import Documents, list_url
from strata.reader.templates import TEMPLATES

SOURCE = "documents"  # the source registry's key for the documents API
LANGUAGES = {"English": "en", "French": "fr", "Spanish": "es", "Portuguese": "pt", "Arabic": "ar", "Russian": "ru",
             "Chinese": "zh", "Hindi": "hi", "Bengali": "bn", "Vietnamese": "vi", "Urdu": "ur", "Swahili": "sw"}
UNDETERMINED = "und"  # ISO 639's code for a language the list does not name


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _date(value) -> dt.date | None:
    return plans._date(value)


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
    """A chosen document as bronze holds it."""

    listed: Listed
    text: str
    pdf_pages: int
    public_from: dt.date
    paged: bool
    version: int = 1
    replaced_on: dt.date | None = None


def _held(engine: Engine, listed: Listed) -> Held | None:
    texts = _rows(engine, "SELECT text, public_from FROM strata.bronze.document_texts WHERE document_id = :document_id "
                          "ORDER BY fetched_at DESC", document_id=listed.document_id)
    if not texts:
        return None
    pages = int(engine.run("SELECT count(DISTINCT pdf_page) AS n FROM strata.bronze.document_pages "
                           "WHERE document_id = :document_id", {"document_id": listed.document_id}).rows[0][0])
    text = texts[0]["text"]
    return Held(listed, text, pages, _date(texts[0]["public_from"]), route_a.split_pages(text, pages) is not None)


@dataclass(frozen=True)
class Chosen:
    documents: list[Held]
    # For each project, the emails and phone numbers taken out of the texts this run fetched, and how
    # many texts it fetched.
    contacts_removed: dict[str, tuple[int, int]]


def choose(engine: Engine, documents: Documents, endpoint: str, projects: list[str], cap: int) -> Chosen:
    """The documents to read, fetched into bronze: up to cap whose text Route A can read, and any
    scan met on the way, whose pages wait for Route B."""
    chosen, paged, removed = [], 0, {}
    for project_id in projects:
        if paged >= cap:
            break
        plans.fetch_listing(engine, documents, endpoint, project_id)
        listed = listed_documents(engine, project_id)
        for document in listed:
            if paged >= cap:
                break
            fetching = plans.fetch_documents(engine, documents, project_id, [document.entry()])
            count, fetched = removed.get(project_id, (0, 0))
            removed[project_id] = (count + fetching.contacts_removed, fetched + fetching.fetched)
            held = _held(engine, document)
            if held is None:
                continue  # listed but not fetched: the source could not give it
            chosen.append(_versioned(held, listed))
            paged += held.paged
    return Chosen(chosen, removed)


def _versioned(held: Held, listed: list[Listed]) -> Held:
    """The document's version of its report, and the day the next version replaced it."""
    document = held.listed
    if document.report_number is None:
        return held
    issues = sorted((d for d in listed if (d.document_type, d.report_number) == (document.document_type,
                                                                                 document.report_number)),
                    key=lambda d: (d.document_date, d.public_from, d.document_id))
    at = next(i for i, d in enumerate(issues) if d.document_id == document.document_id)
    replaced = issues[at + 1].public_from if at + 1 < len(issues) else None
    return Held(held.listed, held.text, held.pdf_pages, held.public_from, held.paged, at + 1, replaced)


# ── 3. Route A ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Project:
    """What a passage's header says about its project."""

    project_id: str
    country: str | None
    sector: str | None


PROJECT = """
SELECT p.project_id, c.country_name, p.sector_codes
FROM strata.gold.project AS p
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
WHERE p.project_id = :project_id
"""


def project(engine: Engine, project_id: str) -> Project:
    found = _rows(engine, PROJECT, project_id=project_id)
    if not found:
        return Project(project_id, None, None)
    sector = main_sector(found[0]["sector_codes"])
    return Project(project_id, found[0]["country_name"], sector.word if sector else None)


def header(short_name: str, project: Project, passage: route_a.Passage) -> str:
    """The short header prepended before embedding: ICR, P130164, India, roads, III.B, ¶54, p.23."""
    parts = [short_name, project.project_id, project.country, project.sector, passage.section_path,
             f"¶{passage.paragraph}" if passage.paragraph_numbered else None, f"p.{passage.pdf_page}"]
    return ", ".join(part for part in parts if part)


def embedded_text(header_line: str, text: str) -> str:
    """What gets embedded and scanned: the header, a line break, then the passage."""
    return f"{header_line}\n{text}"


DOCUMENT_COLUMNS = ("document_id", "project_id", "document_type", "report_number", "version", "document_date",
                    "disclosed_on", "language", "title", "pdf_pages", "text_paged", "text_url", "pdf_url",
                    "replaced_on", "public_from")
ROUTE_COLUMNS = ("document_id", "project_id", "pdf_page", "route", "reason", "printed_page", "numbering_found",
                 "passages", "public_from")
PASSAGE_COLUMNS = ("passage_id", "document_id", "project_id", "document_type", "version", "section_path",
                   "paragraph", "paragraph_numbered", "part", "parts", "pdf_page", "last_pdf_page", "printed_page",
                   "language", "parse_route", "header", "text", "tokens", "text_hash", "public_from")


@dataclass(frozen=True)
class Read:
    held: Held
    reading: route_a.Reading


def read_documents(engine: Engine, chosen: list[Held], max_tokens: int) -> list[Read]:
    """Each chosen document read through Route A, then written to silver for its project."""
    found = [Read(held, route_a.read(held.text, held.pdf_pages, TEMPLATES[held.listed.document_type], max_tokens))
             for held in chosen]
    projects = {held.listed.project_id: project(engine, held.listed.project_id) for held in chosen}
    for project_id in projects:
        for table in ("documents", "document_page_routes", "passages"):
            engine.run(f"DELETE FROM strata.silver.{table} WHERE project_id = :project_id",  # sql-lint: names only
                       {"project_id": project_id})
    documents, routes, passages = [], [], []
    for item in found:
        held, listed = item.held, item.held.listed
        documents.append((listed.document_id, listed.project_id, listed.document_type, listed.report_number,
                          held.version, listed.document_date, listed.disclosed_on, listed.language, listed.title,
                          held.pdf_pages, held.paged, listed.text_url, listed.pdf_url, held.replaced_on,
                          held.public_from))
        routes += [(listed.document_id, listed.project_id, page.pdf_page, page.route, page.reason, page.printed_page,
                    page.numbering_found, page.passages, held.public_from) for page in item.reading.pages]
        short = TEMPLATES[listed.document_type].short_name
        for passage in item.reading.passages:
            line = header(short, projects[listed.project_id], passage)
            passages.append((f"{listed.document_id}/v{held.version}/{passage.key}", listed.document_id,
                             listed.project_id, listed.document_type, held.version, passage.section_path,
                             passage.paragraph, passage.paragraph_numbered, passage.part, passage.parts,
                             passage.pdf_page, passage.last_pdf_page, passage.printed_page, listed.language,
                             route_a.ROUTE_A, line, passage.text, passage.tokens,
                             route_a.text_hash(embedded_text(line, passage.text)), held.public_from))
    engine.insert_rows("strata.silver.documents", DOCUMENT_COLUMNS, documents)
    engine.insert_rows("strata.silver.document_page_routes", ROUTE_COLUMNS, routes)
    engine.insert_rows("strata.silver.passages", PASSAGE_COLUMNS, passages)
    return found


# ── Data readiness ───────────────────────────────────────────────────────

MEASURE_COLUMNS = ("run_id", "source", "subject", "measure", "kind", "count", "denominator", "as_of", "detail",
                   "measured_at", "public_from")
CADENCE = "The documents API is read daily."


def measure(engine: Engine, run_id: str, found: list[Read], removed: dict[str, tuple[int, int]],
            when: dt.datetime) -> int:
    """The run's data readiness measures for each project, each a count with its denominator, written
    to strata.ops.data_readiness: documents and pages per route, the pages whose paragraph numbering
    was found, the passages linked to a project, freshness, and the contact details taken out."""
    linked = {str(row[0]) for row in engine.run("SELECT project_id FROM strata.gold.project").rows}
    rows = []
    for project_id in dict.fromkeys(item.held.listed.project_id for item in found):
        items = [item for item in found if item.held.listed.project_id == project_id]
        pages = [page for item in items for page in item.reading.pages]
        on_a = [page for page in pages if page.route == route_a.ROUTE_A]
        body = [page for page in on_a if page.reason == route_a.BODY]
        passages = sum(len(item.reading.passages) for item in items)
        stripped, fetched = removed.get(project_id, (0, 0))

        def add(name, kind, count, denominator, detail, as_of=None):
            rows.append((run_id, SOURCE, project_id, name, kind, count, denominator, as_of, detail, when, when.date()))

        add("documents_read_route_a", "coverage", sum(item.held.paged for item in items), len(items),
            "Documents whose published text divides into their PDF's pages, so Route A read them, of the documents "
            "chosen. The others are scans, whose pages wait for Route B.")
        add("pages_route_a", "read_well", len(on_a), len(pages),
            "Pages Route A read from the published text, of every page of the documents chosen.")
        add("pages_route_b", "read_well", len(pages) - len(on_a), len(pages),
            "Pages waiting for Route B, the layout parser: scans, data sheets and pages with no text.")
        add("pages_paragraph_numbering_found", "read_well", sum(page.numbering_found for page in body), len(body),
            "Pages of the body Route A read on which a paragraph the report numbers was found. An ISR numbers "
            "none of its paragraphs.")
        add("passages_linked_to_project", "linked", passages if project_id in linked else 0, passages,
            "Passages whose project is in strata.gold.project.")
        add("documents_fresh", "fresh", None, None, CADENCE,
            as_of=max(item.held.public_from for item in items))
        add("document_contacts_stripped", "stripped", stripped, fetched,
            "Emails and phone numbers taken out of the published texts this run fetched, of the documents it fetched.")
    engine.insert_rows("strata.ops.data_readiness", MEASURE_COLUMNS, rows)
    return len(rows)


# ── The run ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Report:
    run_id: str
    documents: int  # documents read whose text Route A could read
    scans: int  # documents whose pages all wait for Route B
    passages: int


def run(engine: Engine, documents: Documents, projects: list[str] | None = None, *,
        thresholds: Thresholds | None = None, endpoint: str | None = None,
        clock: Callable[[], dt.datetime] = _now, run_id: str | None = None) -> Report:
    """Read the first documents into passages. See the module's docstring for the steps."""
    limits = thresholds or load_thresholds()
    endpoint = endpoint or load_sources()[SOURCE].endpoint
    projects = default_projects() if projects is None else projects
    started = clock()
    run_id = run_id or f"passages-{started:%Y%m%dT%H%M%S%f}"
    chosen = choose(engine, documents, endpoint, projects, int(limits.value("ingestion.passage_documents")))
    found = read_documents(engine, chosen.documents, int(limits.value("passages.max_tokens")))
    measure(engine, run_id, found, chosen.contacts_removed, clock())
    return Report(run_id, sum(item.held.paged for item in found), sum(not item.held.paged for item in found),
                  sum(len(item.reading.passages) for item in found))


def default_projects() -> list[str]:
    """The showcase project, then the demo plan's project (config/slice.toml)."""
    chosen_slice = load_slice()
    return [chosen_slice.showcase.project_id, chosen_slice.demo_plan.project_id]


def run_on_fixture(engine: Engine, manifest=None, **options) -> Report:
    """The run over the recorded fixture, with the offline document source, for each project whose
    document list the fixture records."""
    from strata.fixture import recorded as fmt
    from strata.reader.documents import NotFetched, RecordedDocuments

    documents = RecordedDocuments(manifest or fmt.load_manifest())
    endpoint = options.get("endpoint") or load_sources()[SOURCE].endpoint
    recorded = []
    for project_id in options.pop("projects", None) or default_projects():
        try:
            documents.listing(list_url(endpoint, project_id))
            recorded.append(project_id)
        except NotFetched:
            continue
    return run(engine, documents, recorded, **options)


def _print_fixture_run() -> int:
    from strata.lakehouse import catalog, nightly
    from strata.lakehouse.engine import DuckDBEngine

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        nightly.run_locally(engine)
        report = run_on_fixture(engine)
    print(f"Run {report.run_id} read {report.documents} documents into {report.passages} passages. "
          f"{report.scans} more had no text Route A could read, so their pages wait for Route B.")
    return 0


if __name__ == "__main__":
    sys.exit(_print_fixture_run())
