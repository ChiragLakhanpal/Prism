"""A project's Procurement Plans read into STEP rows, with delay measured from the first published
planned date (ticket 08). It runs the same on DuckDB in the gate and on the workspace's SQL warehouse.

For one project, a run:

1. Fetches the project's list from the documents API (the source registry's `documents` entry) into
   bronze.document_lists, and each Procurement Plan's published text and the text of each PDF page
   into bronze.document_texts and bronze.document_pages. A plan already in bronze is not fetched again.
2. Reads every version cheaply (Route A): its Executing Agency(ies) line, which puts it in one
   series per implementing agency, and every Activity Reference No. its text lists. These become
   silver.plan_versions and silver.plan_listings.
3. Decides each activity's first listing, the earliest version read that lists it, which holds its
   first published planned dates. The first listing is confirmed only when every plan the list
   names that is dated on or before it, or that has no date, was read; otherwise an older version
   may list the activity first, and silver says so. Then it chooses the versions whose tables the layout parser reads:
   each agency's latest version, the version before it (so a later ticket can show what changed),
   and each first listing. Only those go to Route B.
4. Sends the chosen versions' table pages to the layout parser, newest version first, each page
   once, until the day's attempts reach the daily page cap (config/thresholds.toml,
   ingestion.daily_page_cap). Each page read goes to bronze.layout_pages. A page the parser cannot
   read goes to strata.ops.parse_failures, counts against the cap, and waits until the next day.
   The run, with the page it stopped at and the first page that failed, goes to strata.ops.parse_runs.
   When the host refuses a request or the night's reading time is spent (StopReading), the run stops
   before the next page, keeps the pages it read, and lists the document as unfinished in
   strata.ops.skipped_documents (ticket 72).
5. Reads the parsed tables into silver.plan_rows and silver.plan_steps, for every version whose
   table pages have all been parsed, then runs the SQL that defines delay (silver.plan_step_delays)
   and the data notes (silver.plan_data_notes).
6. Writes its data readiness measures, each a count with its denominator, to strata.ops.data_readiness:
   the listed versions it read, the pages each route read well, the table rows in which the STEP
   reader found an Activity Reference No., and how many of the latest versions' activities have
   STEP rows and a confirmed first listing that was read.

Bronze only grows. Silver is rebuilt from bronze for the project on every run.

Run it on the fixture and print what it wrote:

    uv run --frozen python -m strata.lakehouse.plans
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import astuple, dataclass, field, fields
from importlib import resources

from strata.config import Thresholds, load_sources, load_thresholds
from strata.lakehouse import contacts
from strata.lakehouse.clean import public_from  # ADR 0002's rule, defined once for every source
from strata.lakehouse.engine import Engine, RowTooLarge, WarehouseEngine
from strata.reader import step
from strata.reader.documents import Documents, NotFetched, StopReading, list_url
from strata.reader.layout import LayoutParser, Page, ParseFailed, Table, tables_from_json, tables_to_json

log = logging.getLogger(__name__)

SOURCE = "documents"  # the source registry's key for the documents API
PLAN = "Procurement Plan"
TABLE_PAGE = step.squash("Activity Reference No.")  # a page that holds a STEP table goes to Route B


def holds_table(text: str) -> bool:
    """Whether a plan page holds a STEP table: its header, or a row continued from the page before,
    which starts with an Activity Reference No. and no header above it."""
    return TABLE_PAGE in step.squash(text) or bool(step.references_in(text))


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def _sql(name: str) -> str:
    # importlib.resources rather than __file__, which serverless Python tasks do not set.
    return (resources.files("strata.lakehouse") / "sql" / "plans" / name).read_text()


WAREHOUSE_CHUNK = 20  # rows per INSERT on the SQL warehouse: a plan's pages are long text


def insert(engine: Engine, table: str, columns: tuple[str, ...], rows: list[tuple]) -> int:
    """Insert rows through the engine's own insert_rows, which binds every value. On the SQL warehouse
    each statement takes fewer rows than usual, so a statement of long page text stays small."""
    if isinstance(engine, WarehouseEngine):
        return engine.insert_rows(table, columns, list(rows), chunk=WAREHOUSE_CHUNK)
    return engine.insert_rows(table, columns, list(rows))


# ── What a run skipped or left unfinished (ticket 72) ────────────────────

SKIPPED, UNFINISHED = "skipped", "unfinished"


@dataclass(frozen=True)
class Skipped:
    """A document, or a project's document list, that a reader could not fetch or read, so it skipped it and went
    on (skipped), or a document it was reading when the run stopped (unfinished), and why. The plan reader and the
    passage reader both record them, in strata.ops.skipped_documents."""

    project_id: str
    document_id: str | None  # None when the run could not fetch the project's document list
    url: str
    reason: str
    outcome: str = SKIPPED


SKIP_COLUMNS = ("run_id", "reader", "project_id", "document_id", "url", "outcome", "reason", "skipped_at",
                "public_from")


def named(reader: str, document_id: str | None) -> str:
    """What a reader skipped, in words: a document, or, with no document, the project's plans (the plan reader
    stopped on the project) or its document list (the passage reader could not fetch it)."""
    if document_id:
        return f"document {document_id}"
    return "the plans" if reader == "plans" else "the document list"


def skip(engine: Engine, run_id: str, reader: str, skipped: Skipped, when: dt.datetime) -> None:
    """Record a document or a document list the run skipped or left unfinished, in the run's log and in
    strata.ops.skipped_documents. reader is the reader that met it: plans or passages."""
    what = named(reader, skipped.document_id)
    # A warning, so the nightly job's log shows it without a logging setup of its own, and the live script's too.
    if skipped.outcome == UNFINISHED:
        log.warning("I left %s of %s unfinished: %s", what, skipped.project_id, skipped.reason)
    else:
        log.warning("I skipped %s of %s and went on with the next: %s", what, skipped.project_id, skipped.reason)
    insert(engine, "strata.ops.skipped_documents", SKIP_COLUMNS, [
        (run_id, reader, skipped.project_id, skipped.document_id, skipped.url, skipped.outcome, skipped.reason, when,
         when.date())])


# ── 1. Fetch into bronze ─────────────────────────────────────────────────

@dataclass(frozen=True)
class Entry:
    """A Procurement Plan as the documents API lists it."""

    document_id: str
    plan_date: dt.date
    disclosed_on: dt.date | None
    text_url: str
    pdf_url: str


def fetch_listing(engine: Engine, documents: Documents, endpoint: str, project_id: str) -> None:
    """Every page of the project's document list, kept in bronze when it changed."""
    offset = 0
    while True:
        url = list_url(endpoint, project_id, offset)
        fetched = documents.listing(url)
        text = json.dumps(fetched.body, sort_keys=True, ensure_ascii=False)
        digest = _sha(text)
        seen = engine.run("SELECT count(*) AS n FROM strata.bronze.document_lists "
                          "WHERE url = :url AND content_hash = :hash", {"url": url, "hash": digest}).rows[0][0]
        if int(seen) == 0:
            insert(engine, "strata.bronze.document_lists",
                   ("source", "project_id", "url", "content_hash", "response", "fetched_at", "public_from"),
                   [(SOURCE, project_id, url, digest, text, fetched.fetched_at, fetched.fetched_at.date())])
        rows, total = int(fetched.body.get("rows", 0) or 0), int(fetched.body.get("total", 0) or 0)
        offset += rows
        if not rows or offset >= total:
            return


@dataclass(frozen=True)
class Listing:
    """The project's Procurement Plans in its latest document list."""

    entries: list[Entry]  # the plans the run can fetch, with a text, a PDF and a date, oldest first
    dates: dict[str, dt.date | None]  # every plan the list names, by document id, with its date (docdt) or None


def listed_plans(engine: Engine, project_id: str) -> Listing:
    """The project's Procurement Plans in its latest document list."""
    latest: dict[str, str] = {}
    for url, response in engine.run(
            "SELECT url, response FROM strata.bronze.document_lists WHERE project_id = :project_id "
            "ORDER BY fetched_at", {"project_id": project_id}).rows:
        latest[url] = response
    entries, dates = {}, {}
    for response in latest.values():
        for key, document in json.loads(response).get("documents", {}).items():
            if key == "facets" or not isinstance(document, dict) or document.get("docty") != PLAN:
                continue
            dates[document["id"]] = _date(document.get("docdt"))
            if document.get("txturl") and document.get("pdfurl") and document.get("docdt"):
                entries[document["id"]] = Entry(document["id"], _date(document["docdt"]),
                                                _date(document.get("disclosure_date")),
                                                document["txturl"], document["pdfurl"])
    return Listing(sorted(entries.values(), key=lambda e: (e.plan_date, e.document_id)), dates)


def fetch_plans(engine: Engine, documents: Documents, project_id: str, entries: list[Entry]) -> int:
    """Each plan's text and page texts, for the plans bronze does not hold yet. Returns how many it fetched."""
    return fetch_documents(engine, documents, project_id, entries).fetched


@dataclass(frozen=True)
class Fetching:
    fetched: int  # documents fetched into bronze
    with_contacts: int  # of those, the documents whose published text had contact details taken out
    # Documents fetched but not kept, with the characters in each one's text: the SQL warehouse takes a
    # statement's parameters up to about 1 MB, so a text past that cannot be written through it. Such a
    # document counts as listed but not read, which leaves later first listings unconfirmed.
    not_kept: tuple[tuple[str, int], ...] = ()
    # Documents the source could not give, each with the address that failed (its text's or its PDF's) and why
    # (NotFetched's message), which both readers record when they skip them (ticket 72).
    not_fetched: tuple[tuple[str, str, str], ...] = ()


def fetch_documents(engine: Engine, documents: Documents, project_id: str, entries: list[Entry]) -> Fetching:
    """Each document's text and page texts, for the documents bronze does not hold yet, with its email
    addresses and labelled phone numbers taken out before bronze keeps them (contacts.strip_text). The
    passage reader (src/strata/lakehouse/passages.py) fetches its documents here too."""
    held = {str(row[0]) for row in engine.run(
        "SELECT DISTINCT document_id FROM strata.bronze.document_texts WHERE project_id = :project_id",
        {"project_id": project_id}).rows}
    fetched = with_contacts = 0
    not_kept: list[tuple[str, int]] = []
    not_fetched: list[tuple[str, str, str]] = []
    for entry in entries:
        if entry.document_id in held:
            continue
        try:
            text, pages = documents.text(entry.text_url), documents.pages(entry.pdf_url)
        except NotFetched as error:
            not_fetched.append((entry.document_id, error.url or entry.text_url, str(error)))
            continue  # a document listed but not read, which leaves later first listings unconfirmed
        body, count = contacts.strip_text(text.body)
        page_texts = [contacts.strip_text(page)[0] for page in pages.body]  # the same details again, counted once
        public = public_from(entry.disclosed_on, text.fetched_at.date())
        try:
            insert(engine, "strata.bronze.document_texts",
                   ("document_id", "project_id", "url", "content_hash", "text", "fetched_at", "public_from"),
                   [(entry.document_id, project_id, entry.text_url, _sha(body), body, text.fetched_at, public)])
        except RowTooLarge:
            not_kept.append((entry.document_id, len(body)))
            continue
        insert(engine, "strata.bronze.document_pages",
               ("document_id", "project_id", "pdf_page", "url", "page_hash", "text", "fetched_at", "public_from"),
               [(entry.document_id, project_id, number, entry.pdf_url, _sha(page), page, pages.fetched_at, public)
                for number, page in enumerate(page_texts, 1)])
        fetched += 1
        with_contacts += count > 0
    return Fetching(fetched, with_contacts, tuple(not_kept), tuple(not_fetched))


# ── 2 and 3. Read every version's text, and choose the ones whose tables get read ───

@dataclass(frozen=True)
class PdfPage:
    number: int  # from 1
    digest: str  # the hash of its text
    holds_table: bool  # whether it holds a STEP table, which only the layout parser reads well
    has_text: bool  # whether its text is not empty, so Route A can read it


@dataclass
class Version:
    entry: Entry
    public_from: dt.date
    agency: str | None
    listings: list[str]
    pages: list[PdfPage]
    series_order: int = 0
    previous: str | None = None
    is_latest: bool = False
    reasons: list[str] = field(default_factory=list)
    first_listings: list[str] = field(default_factory=list)  # the activities no earlier version read lists
    nothing_older_unread: bool = False  # every plan the list names that is dated on or before this one was read

    @property
    def document_id(self) -> str:
        return self.entry.document_id

    @property
    def table_pages(self) -> list[tuple[int, str]]:
        return [(page.number, page.digest) for page in self.pages if page.holds_table]

    @property
    def route_a_pages(self) -> list[PdfPage]:
        """The pages left to Route A: every page, except a table page when the version is chosen for Route B."""
        return [page for page in self.pages if not (page.holds_table and self.reasons)]


def _published_order(version: Version) -> tuple:
    """Plan versions in the order they were published: by plan date, then public date, then document id."""
    return (version.entry.plan_date, version.public_from, version.document_id)


def read_versions(engine: Engine, project_id: str, listing: Listing) -> list[Version]:
    """Every listed plan bronze holds, read through its text (Route A), in series per implementing
    agency, with each activity's first listing. This is the one place that decides first listings."""
    texts = {str(d): (t, _date(p)) for d, t, p in engine.run(
        "SELECT document_id, text, public_from FROM strata.bronze.document_texts WHERE project_id = :project_id",
        {"project_id": project_id}).rows}
    pages: dict[str, list] = defaultdict(list)
    for document_id, number, digest, text in engine.run(
            "SELECT document_id, pdf_page, page_hash, text FROM strata.bronze.document_pages "
            "WHERE project_id = :project_id ORDER BY document_id, pdf_page", {"project_id": project_id}).rows:
        pages[str(document_id)].append((int(number), str(digest), text))
    versions = []
    for entry in listing.entries:
        if entry.document_id not in texts:
            continue
        text, public = texts[entry.document_id]
        page_texts = pages[entry.document_id]
        agency = step.executing_agency("\n".join(t for _, _, t in page_texts)) or step.executing_agency(text)
        versions.append(Version(entry, public, agency, step.references_in(text),
                                [PdfPage(n, d, holds_table(t), bool(t.strip()))
                                 for n, d, t in page_texts]))

    series: dict[str | None, list[Version]] = defaultdict(list)
    for version in versions:
        series[version.agency].append(version)
    for members in series.values():
        members.sort(key=_published_order)
        for order, version in enumerate(members, 1):
            version.series_order = order
            version.previous = members[order - 2].document_id if order > 1 else None
        members[-1].is_latest = True
        members[-1].reasons.append("the agency's latest version")
        if len(members) > 1:
            members[-2].reasons.append("the version before the latest")
    # An activity's first listing is the earliest version read that lists it, across every agency's
    # series, because an activity can move from one agency's plan to another's. A listed plan that
    # was not read (the fixture does not record it, it failed to fetch, or the list gives it no text,
    # PDF or date) may list the activity earlier, so a first listing is confirmed only when every
    # plan the list names that is dated on or before it, or that has no date, was read.
    read = {version.document_id for version in versions}
    unread = [date for document_id, date in listing.dates.items() if document_id not in read]
    seen: set[str] = set()
    for version in sorted(versions, key=_published_order):
        version.nothing_older_unread = all(date is not None and date > version.entry.plan_date for date in unread)
        version.first_listings = [reference for reference in version.listings if reference not in seen]
        seen.update(version.first_listings)
        if version.first_listings:
            version.reasons.append(f"the first version to list {', '.join(version.first_listings)}")
    return versions


def first_listings(versions: list[Version]) -> dict[str, Version]:
    """Each activity's first listing, as read_versions decided it."""
    return {reference: version for version in versions for reference in version.first_listings}


def write_versions(engine: Engine, project_id: str, versions: list[Version]) -> None:
    for table in ("plan_versions", "plan_listings"):
        engine.run(f"DELETE FROM strata.silver.{table} WHERE project_id = :project_id",  # sql-lint: names only
                   {"project_id": project_id})
    insert(engine, "strata.silver.plan_versions",
           ("document_id", "project_id", "implementing_agency", "plan_date", "disclosed_on", "series_order",
            "previous_document_id", "is_latest", "pdf_pages", "route_b_pages", "parse_reason", "text_url",
            "pdf_url", "public_from"),
           [(v.document_id, project_id, v.agency, v.entry.plan_date, v.entry.disclosed_on, v.series_order, v.previous,
             v.is_latest, len(v.pages), len(v.table_pages), "; ".join(v.reasons) or None, v.entry.text_url,
             v.entry.pdf_url, v.public_from) for v in versions])
    first = first_listings(versions)
    insert(engine, "strata.silver.plan_listings",
           ("document_id", "project_id", "activity_reference_no", "is_first_listing", "first_listing_confirmed",
            "public_from"),
           [(v.document_id, project_id, reference, first[reference] is v, first[reference].nothing_older_unread,
             v.public_from) for v in versions for reference in v.listings])


# ── 4. Route B, under the daily page cap ─────────────────────────────────

@dataclass(frozen=True)
class Parsing:
    parser: str
    cap: int
    parsed_earlier_today: int  # pages the parser tried earlier that day, read or failed
    waiting: int
    parsed: int
    stopped_at: tuple[str, int] | None  # the document and PDF page the run did not reach, at the cap or at a stop
    failed: tuple[tuple[str, int], ...] = ()  # the document and PDF page of each page the parser could not read
    # What stopped the run at stopped_at, when it was not the cap: the host refused a request, or the night's reading
    # time was spent (ticket 72).
    stop: StopReading | None = None

    @property
    def at_cap(self) -> bool:
        return self.stopped_at is not None and self.stop is None

    def then(self, later: Parsing) -> Parsing:
        """This parse and a later one for the same project in the same run, as one: the passage reader parses a
        project's pages document by document (ticket 72), and strata.ops.parse_runs keeps one row per project."""
        return Parsing(self.parser, self.cap, self.parsed_earlier_today, self.waiting + later.waiting,
                       self.parsed + later.parsed, self.stopped_at or later.stopped_at, self.failed + later.failed,
                       self.stop or later.stop)


def parsed_pages(engine: Engine, project_id: str) -> set[tuple[str, int, str]]:
    return {(str(d), int(n), str(h)) for d, n, h in engine.run(
        "SELECT document_id, pdf_page, page_hash FROM strata.bronze.layout_pages WHERE project_id = :project_id",
        {"project_id": project_id}).rows}


TRIED_TODAY = """
SELECT (SELECT count(*) FROM strata.bronze.layout_pages WHERE CAST(parsed_at AS DATE) = :today)
     + (SELECT count(*) FROM strata.ops.parse_failures WHERE CAST(failed_at AS DATE) = :today) AS n
"""


@dataclass(frozen=True)
class WaitingPage:
    """A page the page router sent to Route B: its document, project, PDF, number in the PDF, the hash
    of its text (the parse-once key with the document and the number) and its public date."""

    document_id: str
    project_id: str
    pdf_url: str
    pdf_page: int
    page_hash: str
    public_from: dt.date


def parse_chosen(engine: Engine, layout: LayoutParser, project_id: str, versions: list[Version], cap: int,
                 clock: Callable[[], dt.datetime], run_id: str) -> Parsing:
    """Each chosen version's table pages that have not been parsed, newest version first, up to the cap."""
    chosen = sorted((v for v in versions if v.reasons), key=lambda v: (v.entry.plan_date, v.document_id), reverse=True)
    return parse_pages(engine, layout, project_id, [
        WaitingPage(version.document_id, project_id, version.entry.pdf_url, number, digest, version.public_from)
        for version in chosen for number, digest in version.table_pages], cap, clock, run_id)


def parse_pages(engine: Engine, layout: LayoutParser, project_id: str, pages: list[WaitingPage], cap: int,
                clock: Callable[[], dt.datetime], run_id: str) -> Parsing:
    """One project's Route B pages that have not been parsed, in the order given, up to the cap. The
    plan reader and the document reader (src/strata/lakehouse/passages.py) both parse through here.

    Each page is parsed once: a page whose document, PDF page and text hash bronze.layout_pages holds
    is not parsed again. The cap counts every page the parser tried that day, in UTC, across every
    project and both readers, whether it read the page or not, because each attempt costs a parse. A
    page that failed that day waits until the next.

    When the host refuses a request or the night's reading time is spent before a page (StopReading, which the
    live parser checks before each page: strata.lakehouse.readers.OnBudget), the parse ends there and the Parsing
    it returns holds the stop and the page it did not read; the pages read before it are already in bronze. The
    caller records it (record_stop) and raises the stop again."""
    today = clock().date()
    done = parsed_pages(engine, project_id)
    failed_today = {(str(d), int(n), str(h)) for d, n, h in engine.run(
        "SELECT document_id, pdf_page, page_hash FROM strata.ops.parse_failures "
        "WHERE project_id = :project_id AND CAST(failed_at AS DATE) = :today",
        {"project_id": project_id, "today": today}).rows}
    waiting = [page for page in pages if (page.document_id, page.pdf_page, page.page_hash) not in done | failed_today]
    earlier = int(engine.run(TRIED_TODAY, {"today": today}).rows[0][0])
    budget, tried, parsed, stopped, failed = max(cap - earlier, 0), 0, 0, None, []
    for page in waiting:
        if tried >= budget:
            stopped = (page.document_id, page.pdf_page)
            break
        tried += 1
        try:
            found = layout.parse(Page(page.document_id, page.pdf_url, page.pdf_page))
        except StopReading as stop:  # the pages parsed before this one stay in bronze (ticket 72)
            return Parsing(layout.name, cap, earlier, len(waiting), parsed, (page.document_id, page.pdf_page),
                           tuple(failed), stop)
        except ParseFailed as error:
            when = clock()
            insert(engine, "strata.ops.parse_failures",
                   ("run_id", "project_id", "document_id", "pdf_page", "page_hash", "parser", "error", "failed_at",
                    "public_from"),
                   [(run_id, project_id, page.document_id, page.pdf_page, page.page_hash, layout.name, str(error),
                     when, when.date())])
            failed.append((page.document_id, page.pdf_page))
            continue
        # The parser reads the PDF itself, so its words lose their emails and labelled phone numbers here,
        # before bronze keeps them, as the published text does when it is fetched.
        tables = [Table(table.title, table.header_rows,
                        tuple(tuple(contacts.strip_text(cell)[0] for cell in row) for row in table.rows))
                  for table in found.tables]
        insert(engine, "strata.bronze.layout_pages",
               ("document_id", "project_id", "pdf_page", "page_hash", "parser", "tables", "text", "figures",
                "parsed_at", "run_id", "public_from"),
               [(page.document_id, project_id, page.pdf_page, page.page_hash, layout.name, tables_to_json(tables),
                 contacts.strip_text(found.text)[0], found.figures, clock(), run_id, page.public_from)])
        parsed += 1
    return Parsing(layout.name, cap, earlier, len(waiting), parsed, stopped, tuple(failed))


def record_parse_run(engine: Engine, run_id: str, project_id: str, parsing: Parsing, started: dt.datetime,
                     finished: dt.datetime) -> None:
    """One row of strata.ops.parse_runs: what one run's Route B did for one project."""
    insert(engine, "strata.ops.parse_runs",
           ("run_id", "project_id", "parser", "daily_page_cap", "parsed_earlier_today", "pages_waiting",
            "pages_parsed", "pages_failed", "first_failed_document_id", "first_failed_pdf_page", "stopped_at_cap",
            "stopped_at_document_id", "stopped_at_pdf_page", "started_at", "finished_at", "public_from"),
           [(run_id, project_id, parsing.parser, parsing.cap, parsing.parsed_earlier_today, parsing.waiting,
             parsing.parsed, len(parsing.failed), *(parsing.failed[0] if parsing.failed else (None, None)),
             parsing.at_cap, *(parsing.stopped_at or (None, None)), started, finished, finished.date())])


def record_stop(engine: Engine, run_id: str, reader: str, project_id: str, parsing: Parsing, started: dt.datetime,
                finished: dt.datetime) -> Skipped:
    """A parse that a stop ended (parsing.stop): its row of strata.ops.parse_runs, with the page it did not read, and
    the document it was reading listed as unfinished in strata.ops.skipped_documents. The caller raises the stop
    again, so the reading ends there; the pages read before it stay in bronze.layout_pages, and the next run reads
    the rest. Returns what it listed."""
    record_parse_run(engine, run_id, project_id, parsing, started, finished)
    document_id, page = parsing.stopped_at
    unfinished = Skipped(project_id, document_id, parsing.stop.url,
                         f"{parsing.stop} The pages read before page {page} are kept, and the next run reads the rest.",
                         UNFINISHED)
    skip(engine, run_id, reader, unfinished, finished)
    return unfinished


# ── 5. Silver rows, steps, delays and data notes ─────────────────────────

# silver.plan_rows's STEP columns after the reference and description, in STEP's order (step.COLUMNS).
# The STEP columns, then the plan's own words for its method (ticket 42).
ROW_COLUMNS = (*(key for key in step.COLUMNS.values() if key != "activity"), "method_original", "method_original_lang",
               "method_mapped")


@dataclass(frozen=True)
class RowsRead:
    """What write_rows read: the versions it wrote STEP rows for, the table rows in which the STEP
    reader found an Activity Reference No. and those in which it found none, and the column
    names it did not know."""

    versions: frozenset[str]
    with_reference: int
    without_reference: int
    unknown_columns: tuple[str, ...]


def write_rows(engine: Engine, project_id: str, versions: list[Version]) -> RowsRead:
    """STEP rows and step dates for every version whose table pages are all parsed."""
    parsed: dict[tuple[str, int], tuple[str, str, str]] = {}
    for document_id, number, digest, parser, tables, _ in engine.run(
            "SELECT document_id, pdf_page, page_hash, parser, tables, parsed_at FROM strata.bronze.layout_pages "
            "WHERE project_id = :project_id ORDER BY parsed_at", {"project_id": project_id}).rows:
        parsed[(str(document_id), int(number))] = (str(digest), str(parser), tables)
    for table in ("plan_rows", "plan_steps", "plan_step_delays", "plan_data_notes"):
        engine.run(f"DELETE FROM strata.silver.{table} WHERE project_id = :project_id",  # sql-lint: names only
                   {"project_id": project_id})
    rows, steps, read, without_reference, unknown = [], [], set(), 0, set()
    for version in versions:
        pages = version.table_pages
        found = [parsed.get((version.document_id, number)) for number, _ in pages]
        if not pages or any(page is None or page[0] != digest for page, (_, digest) in zip(found, pages)):
            continue
        reading = step.plan_rows([(number, tables_from_json(page[2])) for (number, _), page in zip(pages, found)])
        parser = found[0][1]
        read.add(version.document_id)
        without_reference += reading.rows_without_reference
        unknown |= reading.unknown_columns
        for row in reading.rows:
            rows.append((version.document_id, project_id, row.section, row.activity_reference_no,
                         row.description or None, *(row.fields.get(column) for column in ROW_COLUMNS),
                         row.pdf_page, parser, version.public_from))
            steps += [(version.document_id, project_id, row.activity_reference_no, s.step, s.step_order,
                       s.planned_on, s.actual_on, version.public_from) for s in row.steps]
    insert(engine, "strata.silver.plan_rows",
           ("document_id", "project_id", "section", "activity_reference_no", "description", *ROW_COLUMNS,
            "pdf_page", "parser", "public_from"), rows)
    insert(engine, "strata.silver.plan_steps",
           ("document_id", "project_id", "activity_reference_no", "step", "step_order", "planned_on", "actual_on",
            "public_from"), steps)
    for transform in ("plan_step_delays.sql", "plan_data_notes.sql"):
        engine.run(_sql(transform), {"project_id": project_id})
    return RowsRead(frozenset(read), len(rows), without_reference, tuple(sorted(unknown)))


# ── 6. Data readiness ────────────────────────────────────────────────────

@dataclass(frozen=True)
class Measure:
    """One data readiness measure, a count with its denominator: a row of strata.ops.data_readiness."""

    run_id: str
    source: str
    subject: str
    measure: str
    kind: str
    count: int
    denominator: int
    measured_at: dt.datetime
    public_from: dt.date


def measure(engine: Engine, project_id: str, run_id: str, versions: list[Version], listed: int, read: RowsRead,
            parsed: set[tuple[str, int, str]], when: dt.datetime) -> list[Measure]:
    route_a = [page for v in versions for page in v.route_a_pages]
    route_b = [(v.document_id, n, d) for v in versions if v.reasons for n, d in v.table_pages]
    latest = [v for v in versions if v.is_latest]
    latest_listed = sum(len(v.listings) for v in latest)
    with_rows = {(str(d), str(a)) for d, a in engine.run(
        "SELECT document_id, activity_reference_no FROM strata.silver.plan_rows WHERE project_id = :project_id",
        {"project_id": project_id}).rows}
    first = first_listings(versions)
    measures = [
        ("plan_versions_read", "coverage", len(versions), listed),
        ("pages_read_route_a", "read_well", sum(1 for page in route_a if page.has_text), len(route_a)),
        ("pages_read_route_b", "read_well", sum(1 for page in route_b if page in parsed), len(route_b)),
        ("step_rows_with_reference", "linked", read.with_reference, read.with_reference + read.without_reference),
        ("latest_activities_with_step_rows", "read_well",
         sum(1 for v in latest for a in v.listings if (v.document_id, a) in with_rows), latest_listed),
        ("latest_activities_with_confirmed_first_listing_read", "coverage",
         sum(1 for v in latest for a in v.listings
             if first[a].nothing_older_unread and first[a].document_id in read.versions), latest_listed),
    ]
    rows = [Measure(run_id, SOURCE, project_id, name, kind, count, denominator, when, when.date())
            for name, kind, count, denominator in measures]
    insert(engine, "strata.ops.data_readiness", tuple(f.name for f in fields(Measure)), [astuple(m) for m in rows])
    return rows


# ── The run ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Report:
    run_id: str
    versions: int
    parsing: Parsing
    versions_with_rows: int
    measures: list[Measure]
    unknown_columns: tuple[str, ...]  # STEP table columns the reader did not know, which it left out
    not_kept: tuple[tuple[str, int], ...] = ()  # plans fetched but too large for the warehouse (Fetching.not_kept)


def run(engine: Engine, documents: Documents, layout: LayoutParser, project_id: str, *,
        thresholds: Thresholds | None = None, endpoint: str | None = None,
        clock: Callable[[], dt.datetime] = _now, run_id: str | None = None) -> Report:
    """Read one project's Procurement Plans into STEP rows. See the module's docstring for the steps."""
    cap = int((thresholds or load_thresholds()).value("ingestion.daily_page_cap"))
    endpoint = endpoint or load_sources()[SOURCE].endpoint
    started = clock()
    run_id = run_id or f"plans-{project_id}-{started:%Y%m%dT%H%M%S%f}"

    fetch_listing(engine, documents, endpoint, project_id)
    listing = listed_plans(engine, project_id)
    fetching = fetch_documents(engine, documents, project_id, listing.entries)
    # Each plan listed but not fetched, which the run goes on without (ticket 72), at the time the run started: the
    # fetches follow it at once, and the fixture's clock, which moves on each time it is read, keeps its times.
    for document_id, url, reason in fetching.not_fetched:
        skip(engine, run_id, "plans", Skipped(project_id, document_id, url, reason), started)
    versions = read_versions(engine, project_id, listing)
    write_versions(engine, project_id, versions)
    parsing = parse_chosen(engine, layout, project_id, versions, cap, clock, run_id)
    if parsing.stop is not None:  # the host refused, or the night's reading time is spent: the reading ends here
        record_stop(engine, run_id, "plans", project_id, parsing, started, clock())
        raise parsing.stop
    read = write_rows(engine, project_id, versions)
    finished = clock()
    record_parse_run(engine, run_id, project_id, parsing, started, finished)
    measures = measure(engine, project_id, run_id, versions, len(listing.dates), read, parsed_pages(engine, project_id),
                       finished)
    return Report(run_id, len(versions), parsing, len(read.versions), measures, read.unknown_columns,
                  fetching.not_kept)


def run_on_fixture(engine: Engine, project_id: str | None = None, manifest=None, **options) -> Report:
    """The run over the recorded fixture, with the offline document source and layout parser."""
    from strata.config import load_slice
    from strata.fixture import recorded as fmt
    from strata.reader.documents import RecordedDocuments
    from strata.reader.layout import RecordedLayout

    manifest = manifest or fmt.load_manifest()
    return run(engine, RecordedDocuments(manifest), RecordedLayout(manifest),
               project_id or load_slice().demo_plan.project_id, **options)


def _print_fixture_run() -> int:
    from strata.lakehouse import catalog
    from strata.lakehouse.engine import DuckDBEngine

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        report = run_on_fixture(engine)
    print(f"Run {report.run_id} read {report.versions} plan versions and parsed {report.parsing.parsed} pages "
          f"with {report.parsing.parser}. {report.versions_with_rows} versions have STEP rows.")
    print_measures(report)
    return 0


def print_measures(report: Report) -> None:
    """The run's measures, one a line, and any STEP column the reader did not know."""
    for m in report.measures:
        print(f"  {m.subject} {m.measure}: {m.count} of {m.denominator}")
    if report.unknown_columns:
        print(f"The STEP reader did not know these columns and left them out: {', '.join(report.unknown_columns)}.")
    if report.not_kept:
        listed = ", ".join(f"{document_id} ({characters:,} characters)" for document_id, characters in report.not_kept)
        plans = "1 plan was" if len(report.not_kept) == 1 else f"{len(report.not_kept)} plans were"
        print(f"{plans} fetched but not kept, because the SQL warehouse takes a statement's parameters only up "
              f"to about 1 MB: {listed}. Each counts as listed but not read.")


if __name__ == "__main__":
    sys.exit(_print_fixture_run())
