"""A project's Procurement Plans read into STEP rows, with delay measured from the first published
planned date (ticket 08). It runs the same on DuckDB in the gate and on the workspace's SQL warehouse.

For one project, a run:

1. Fetches the project's list from the documents API (the source registry's `documents` entry) into
   bronze.document_lists, and each Procurement Plan's published text and the text of each PDF page
   into bronze.document_texts and bronze.document_pages. A plan already in bronze is not fetched again.
2. Reads every version cheaply (Route A): its Executing Agency(ies) line, which puts it in one
   series per implementing agency, and every Activity Reference No. its text lists. These become
   silver.plan_versions and silver.plan_listings.
3. Chooses the versions whose tables the layout parser reads: each agency's latest version, the
   version before it (so a later ticket can show what changed), and the earliest version that lists
   each activity, which holds its first published planned dates. Only those go to Route B.
4. Sends the chosen versions' table pages to the layout parser, newest version first, each page
   once, until the day's pages reach the daily page cap (config/thresholds.toml,
   ingestion.daily_page_cap). Each page read goes to bronze.layout_pages, and the run, with the page
   it stopped at, to strata.ops.parse_runs.
5. Reads the parsed tables into silver.plan_rows and silver.plan_steps, for every version whose
   table pages have all been parsed, then runs the SQL that defines delay (silver.plan_step_delays)
   and the data notes (silver.plan_data_notes).
6. Writes its data readiness measures, each a count with its denominator, to strata.ops.data_readiness.

Bronze only grows. Silver is rebuilt from bronze for the project on every run.

Run it on the fixture and print what it wrote:

    uv run --frozen python -m strata.lakehouse.plans
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import resources

from strata.config import Thresholds, load_sources, load_thresholds
from strata.lakehouse.engine import Engine
from strata.reader import step
from strata.reader.documents import Documents, NotFetched, list_url
from strata.reader.layout import LayoutParser, Page, tables_from_json, tables_to_json

SOURCE = "documents"  # the source registry's key for the documents API
PLAN = "Procurement Plan"
TABLE_PAGE = step.squash("Activity Reference No.")  # a page that holds a STEP table goes to Route B


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


def insert(engine: Engine, table: str, columns: tuple[str, ...], rows: list[tuple], chunk: int = 100) -> int:
    """Insert rows with every value bound as a named parameter, a chunk of rows per statement."""
    for start in range(0, len(rows), chunk):
        params, values = {}, []
        for n, row in enumerate(rows[start:start + chunk]):
            names = []
            for column, value in zip(columns, row, strict=True):
                params[f"{column}_{n}"] = value
                names.append(f":{column}_{n}")
            values.append(f"({', '.join(names)})")
        engine.run(f"INSERT INTO {table} ({', '.join(columns)}) VALUES {', '.join(values)}", params)
    return len(rows)


def public_from(disclosed_on: dt.date | None, fetched_on: dt.date) -> dt.date:
    """ADR 0002: the day the source published it, or the day Strata first fetched it when that day is
    missing or later than the fetch."""
    return disclosed_on if disclosed_on is not None and disclosed_on <= fetched_on else fetched_on


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


def listed_plans(engine: Engine, project_id: str) -> tuple[list[Entry], int]:
    """The project's Procurement Plans in its latest document list, and how many plans it lists in all."""
    latest: dict[str, str] = {}
    for url, response in engine.run(
            "SELECT url, response FROM strata.bronze.document_lists WHERE project_id = :project_id "
            "ORDER BY fetched_at", {"project_id": project_id}).rows:
        latest[url] = response
    entries, listed = {}, set()
    for response in latest.values():
        for key, document in json.loads(response).get("documents", {}).items():
            if key == "facets" or not isinstance(document, dict) or document.get("docty") != PLAN:
                continue
            listed.add(document["id"])
            if document.get("txturl") and document.get("pdfurl") and document.get("docdt"):
                entries[document["id"]] = Entry(document["id"], _date(document["docdt"]),
                                                _date(document.get("disclosure_date")),
                                                document["txturl"], document["pdfurl"])
    return sorted(entries.values(), key=lambda e: (e.plan_date, e.document_id)), len(listed)


def fetch_plans(engine: Engine, documents: Documents, project_id: str, entries: list[Entry]) -> int:
    """Each plan's text and page texts, for the plans bronze does not hold yet. Returns how many it fetched."""
    held = {str(row[0]) for row in engine.run(
        "SELECT DISTINCT document_id FROM strata.bronze.document_texts WHERE project_id = :project_id",
        {"project_id": project_id}).rows}
    fetched = 0
    for entry in entries:
        if entry.document_id in held:
            continue
        try:
            text, pages = documents.text(entry.text_url), documents.pages(entry.pdf_url)
        except NotFetched:
            continue  # counted in the measures as a plan listed but not read
        public = public_from(entry.disclosed_on, text.fetched_at.date())
        insert(engine, "strata.bronze.document_texts",
               ("document_id", "project_id", "url", "content_hash", "text", "fetched_at", "public_from"),
               [(entry.document_id, project_id, entry.text_url, _sha(text.body), text.body, text.fetched_at, public)])
        insert(engine, "strata.bronze.document_pages",
               ("document_id", "project_id", "pdf_page", "url", "page_hash", "text", "fetched_at", "public_from"),
               [(entry.document_id, project_id, number, entry.pdf_url, _sha(page), page, pages.fetched_at, public)
                for number, page in enumerate(pages.body, 1)])
        fetched += 1
    return fetched


# ── 2 and 3. Read every version's text, and choose the ones whose tables get read ───

@dataclass
class Version:
    entry: Entry
    public_from: dt.date
    agency: str | None
    listings: list[str]
    pages: list[tuple[int, str, bool]]  # PDF page, its hash, whether it holds a STEP table
    series_order: int = 0
    previous: str | None = None
    is_latest: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def document_id(self) -> str:
        return self.entry.document_id

    @property
    def table_pages(self) -> list[tuple[int, str]]:
        return [(number, digest) for number, digest, table in self.pages if table]


def read_versions(engine: Engine, project_id: str, entries: list[Entry]) -> list[Version]:
    """Every plan bronze holds, read through its text (Route A), in series per implementing agency."""
    texts = {str(d): (t, _date(p)) for d, t, p in engine.run(
        "SELECT document_id, text, public_from FROM strata.bronze.document_texts WHERE project_id = :project_id",
        {"project_id": project_id}).rows}
    pages: dict[str, list] = defaultdict(list)
    for document_id, number, digest, text in engine.run(
            "SELECT document_id, pdf_page, page_hash, text FROM strata.bronze.document_pages "
            "WHERE project_id = :project_id ORDER BY document_id, pdf_page", {"project_id": project_id}).rows:
        pages[str(document_id)].append((int(number), str(digest), text))
    versions = []
    for entry in entries:
        if entry.document_id not in texts:
            continue
        text, public = texts[entry.document_id]
        page_texts = pages[entry.document_id]
        agency = step.executing_agency("\n".join(t for _, _, t in page_texts)) or step.executing_agency(text)
        versions.append(Version(entry, public, agency, step.references_in(text),
                                [(n, d, TABLE_PAGE in step.squash(t)) for n, d, t in page_texts]))

    series: dict[str | None, list[Version]] = defaultdict(list)
    for version in versions:
        series[version.agency].append(version)
    for members in series.values():
        members.sort(key=lambda v: (v.entry.plan_date, v.public_from, v.document_id))
        for order, version in enumerate(members, 1):
            version.series_order = order
            version.previous = members[order - 2].document_id if order > 1 else None
        members[-1].is_latest = True
        members[-1].reasons.append("the agency's latest version")
        if len(members) > 1:
            members[-2].reasons.append("the version before the latest")
    first: dict[str, Version] = {}
    for version in sorted(versions, key=lambda v: (v.entry.plan_date, v.public_from, v.document_id)):
        for reference in version.listings:
            first.setdefault(reference, version)
    for version in versions:
        firsts = [reference for reference in version.listings if first[reference] is version]
        if firsts:
            version.reasons.append(f"the first version to list {', '.join(firsts)}")
    return versions


def write_versions(engine: Engine, project_id: str, versions: list[Version]) -> None:
    for table in ("plan_versions", "plan_listings"):
        engine.run(f"DELETE FROM strata.silver.{table} WHERE project_id = :project_id", {"project_id": project_id})
    insert(engine, "strata.silver.plan_versions",
           ("document_id", "project_id", "implementing_agency", "plan_date", "disclosed_on", "series_order",
            "previous_document_id", "is_latest", "pdf_pages", "route_b_pages", "parse_reason", "text_url",
            "pdf_url", "public_from"),
           [(v.document_id, project_id, v.agency, v.entry.plan_date, v.entry.disclosed_on, v.series_order, v.previous,
             v.is_latest, len(v.pages), len(v.table_pages), "; ".join(v.reasons) or None, v.entry.text_url,
             v.entry.pdf_url, v.public_from) for v in versions])
    insert(engine, "strata.silver.plan_listings",
           ("document_id", "project_id", "activity_reference_no", "public_from"),
           [(v.document_id, project_id, reference, v.public_from) for v in versions for reference in v.listings])


# ── 4. Route B, under the daily page cap ─────────────────────────────────

@dataclass(frozen=True)
class Parsing:
    parser: str
    cap: int
    parsed_earlier_today: int
    waiting: int
    parsed: int
    stopped_at: tuple[str, int] | None  # the document and PDF page the run did not reach


def parsed_pages(engine: Engine, project_id: str) -> set[tuple[str, int, str]]:
    return {(str(d), int(n), str(h)) for d, n, h in engine.run(
        "SELECT document_id, pdf_page, page_hash FROM strata.bronze.layout_pages WHERE project_id = :project_id",
        {"project_id": project_id}).rows}


def parse_chosen(engine: Engine, layout: LayoutParser, project_id: str, versions: list[Version], cap: int,
                 clock: Callable[[], dt.datetime], run_id: str) -> Parsing:
    """Each chosen version's table pages that have not been parsed, newest version first, up to the cap."""
    done = parsed_pages(engine, project_id)
    chosen = sorted((v for v in versions if v.reasons), key=lambda v: (v.entry.plan_date, v.document_id), reverse=True)
    waiting = [(version, number, digest) for version in chosen for number, digest in version.table_pages
               if (version.document_id, number, digest) not in done]
    today = clock().date()
    earlier = int(engine.run("SELECT count(*) AS n FROM strata.bronze.layout_pages "
                             "WHERE CAST(parsed_at AS DATE) = :today", {"today": today}).rows[0][0])
    budget, parsed, stopped = max(cap - earlier, 0), 0, None
    for version, number, digest in waiting:
        if parsed >= budget:
            stopped = (version.document_id, number)
            break
        tables = layout.parse(Page(version.document_id, version.entry.pdf_url, number))
        insert(engine, "strata.bronze.layout_pages",
               ("document_id", "project_id", "pdf_page", "page_hash", "parser", "tables", "parsed_at", "run_id",
                "public_from"),
               [(version.document_id, project_id, number, digest, layout.name, tables_to_json(tables), clock(), run_id,
                 version.public_from)])
        parsed += 1
    return Parsing(layout.name, cap, earlier, len(waiting), parsed, stopped)


# ── 5. Silver rows, steps, delays and data notes ─────────────────────────

ROW_COLUMNS = ("loan_credit_no", "component", "review_type", "method", "market_approach", "procurement_process",
               "prequalification", "high_sea_sh_risk", "procurement_document_type", "contract_type",
               "estimated_amount_usd", "actual_amount_usd", "process_status")


def write_rows(engine: Engine, project_id: str, versions: list[Version]) -> set[str]:
    """STEP rows and step dates for every version whose table pages are all parsed. Returns those versions."""
    parsed: dict[tuple[str, int], tuple[str, str, str]] = {}
    for document_id, number, digest, parser, tables, _ in engine.run(
            "SELECT document_id, pdf_page, page_hash, parser, tables, parsed_at FROM strata.bronze.layout_pages "
            "WHERE project_id = :project_id ORDER BY parsed_at", {"project_id": project_id}).rows:
        parsed[(str(document_id), int(number))] = (str(digest), str(parser), tables)
    for table in ("plan_rows", "plan_steps", "plan_step_delays", "plan_data_notes"):
        engine.run(f"DELETE FROM strata.silver.{table} WHERE project_id = :project_id", {"project_id": project_id})
    rows, steps, read = [], [], set()
    for version in versions:
        pages = version.table_pages
        found = [parsed.get((version.document_id, number)) for number, _ in pages]
        if not pages or any(page is None or page[0] != digest for page, (_, digest) in zip(found, pages)):
            continue
        reading = step.plan_rows([(number, tables_from_json(page[2])) for (number, _), page in zip(pages, found)])
        parser = found[0][1]
        read.add(version.document_id)
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
    return read


# ── 6. Data readiness ────────────────────────────────────────────────────

def measure(engine: Engine, project_id: str, run_id: str, versions: list[Version], listed: int, read: set[str],
            parsed: set[tuple[str, int, str]], when: dt.datetime) -> list[tuple]:
    chosen = [v for v in versions if v.reasons]
    all_pages = sum(len(v.pages) for v in versions)
    route_b = [(v.document_id, n, d) for v in chosen for n, d in v.table_pages]
    route_a = all_pages - len(route_b)
    latest = [v for v in versions if v.is_latest]
    latest_listed = sum(len(v.listings) for v in latest)
    with_rows = {(str(d), str(a)) for d, a in engine.run(
        "SELECT document_id, activity_reference_no FROM strata.silver.plan_rows WHERE project_id = :project_id",
        {"project_id": project_id}).rows}
    first = {}
    for version in sorted(versions, key=lambda v: (v.entry.plan_date, v.public_from, v.document_id)):
        for reference in version.listings:
            first.setdefault(reference, version.document_id)
    measures = [
        ("plan_versions_read", "coverage", len(versions), listed),
        ("pages_read_route_a", "read_well", route_a, all_pages),
        ("pages_read_route_b", "read_well", sum(1 for page in route_b if page in parsed), len(route_b)),
        ("latest_activities_with_step_rows", "read_well",
         sum(1 for v in latest for a in v.listings if (v.document_id, a) in with_rows), latest_listed),
        ("latest_activities_with_first_listing_read", "coverage",
         sum(1 for v in latest for a in v.listings if first[a] in read), latest_listed),
    ]
    rows = [(run_id, SOURCE, project_id, name, kind, count, denominator, when, when.date())
            for name, kind, count, denominator in measures]
    insert(engine, "strata.ops.data_readiness",
           ("run_id", "source", "subject", "measure", "kind", "count", "denominator", "measured_at", "public_from"),
           rows)
    return rows


# ── The run ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Report:
    run_id: str
    versions: int
    parsing: Parsing
    versions_with_rows: int
    measures: list[tuple]


def run(engine: Engine, documents: Documents, layout: LayoutParser, project_id: str, *,
        thresholds: Thresholds | None = None, endpoint: str | None = None,
        clock: Callable[[], dt.datetime] = _now, run_id: str | None = None) -> Report:
    """Read one project's Procurement Plans into STEP rows. See the module's docstring for the steps."""
    cap = int((thresholds or load_thresholds()).value("ingestion.daily_page_cap"))
    endpoint = endpoint or load_sources()[SOURCE].endpoint
    started = clock()
    run_id = run_id or f"plans-{project_id}-{started:%Y%m%dT%H%M%S%f}"

    fetch_listing(engine, documents, endpoint, project_id)
    entries, listed = listed_plans(engine, project_id)
    fetch_plans(engine, documents, project_id, entries)
    versions = read_versions(engine, project_id, entries)
    write_versions(engine, project_id, versions)
    parsing = parse_chosen(engine, layout, project_id, versions, cap, clock, run_id)
    read = write_rows(engine, project_id, versions)
    finished = clock()
    insert(engine, "strata.ops.parse_runs",
           ("run_id", "project_id", "parser", "daily_page_cap", "parsed_earlier_today", "pages_waiting",
            "pages_parsed", "stopped_at_cap", "stopped_at_document_id", "stopped_at_pdf_page", "started_at",
            "finished_at", "public_from"),
           [(run_id, project_id, parsing.parser, parsing.cap, parsing.parsed_earlier_today, parsing.waiting,
             parsing.parsed, parsing.stopped_at is not None, *(parsing.stopped_at or (None, None)), started,
             finished, finished.date())])
    measures = measure(engine, project_id, run_id, versions, listed, read, parsed_pages(engine, project_id), finished)
    return Report(run_id, len(versions), parsing, len(read), measures)


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
    for _, _, subject, name, _, count, denominator, _, _ in report.measures:
        print(f"  {subject} {name}: {count} of {denominator}")
    return 0


if __name__ == "__main__":
    sys.exit(_print_fixture_run())
