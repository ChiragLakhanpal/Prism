"""The documents run keeps what it parsed (seam 1; ticket 72).

On October 26, 2026 a live documents run parsed 358 scanned pages over four hours, then stopped with exit 2 when
search.worldbank.org answered 503 for one project's document list, and strata.gold.passage still held no row: the
run wrote every passage at the end. The passage reader now writes each document's passages as soon as it has read
that document, skips a document whose fetch or parse fails with its reason in strata.ops.skipped_documents, and
goes on. These tests run it over the recorded fixture with a fetcher that fails on the third document.
"""

import datetime as dt
import importlib.util
import logging
import sys
from pathlib import Path

import pytest

from strata.config import load_thresholds
from strata.fixture import recorded as fmt
from strata.knowledge.embed import offline
from strata.knowledge.shields import PatternShield
from strata.lakehouse import catalog, passages, readers
from strata.lakehouse.engine import DuckDBEngine
from strata.reader.documents import NotFetched, RecordedDocuments
from strata.reader.layout import RecordedLayout

ROOT = Path(__file__).resolve().parents[1]

UNAVAILABLE = "HTTP Error 503: Service Unavailable"
# What a second run must leave as the first run left it: what was fetched, read, scanned, embedded and indexed.
KEPT = ("strata.bronze.document_texts", "strata.bronze.document_pages", "strata.bronze.layout_pages",
        "strata.silver.documents", "strata.silver.document_page_routes", "strata.silver.passages",
        "strata.silver.passage_shields", "strata.silver.passage_embeddings", "strata.gold.passage")


class FailsOnTheThird:
    """The recorded documents, except that the third document the run asks for cannot be fetched, on this run and
    every later one, as the host answered 503 on October 26, 2026. When the fetch fails, it notes which documents
    strata.gold.passage held at that moment."""

    def __init__(self, engine, documents):
        self.engine, self.documents = engine, documents
        self.asked: list[str] = []  # each document's text address, in the order the run first asked for it
        self.failing: str | None = None
        self.indexed_when_it_failed: set[str] | None = None

    def listing(self, url):
        return self.documents.listing(url)

    def text(self, url):
        if url not in self.asked:
            self.asked.append(url)
        if self.failing is None and len(self.asked) == 3:
            self.failing = url
        if url == self.failing:
            self.indexed_when_it_failed = column(self.engine, "SELECT DISTINCT document_id FROM strata.gold.passage")
            raise NotFetched(f"I could not fetch {url}: {UNAVAILABLE}")
        return self.documents.text(url)

    def pages(self, url):
        return self.documents.pages(url)


def column(engine, sql, **params) -> set[str]:
    return {str(row[0]) for row in engine.run(sql, params).rows}


def document_of(engine, url) -> str:
    [document_id] = column(engine, "SELECT document_id FROM strata.bronze.document_texts WHERE url = :url", url=url)
    return document_id


@pytest.fixture
def fresh():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


def read_p130164(engine, documents, run_id):
    """P130164's documents, up to three whose text Route A reads, with the offline readers."""
    manifest = fmt.load_manifest()
    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 3
    return passages.run(engine, documents, ["P130164"], shield=PatternShield(), embedder=offline(),
                        layout=RecordedLayout(manifest), thresholds=limits, run_id=run_id)


def test_a_document_whose_fetch_fails_is_skipped_after_the_documents_before_it_were_written(fresh):
    documents = FailsOnTheThird(fresh, RecordedDocuments(fmt.load_manifest()))

    report = read_p130164(fresh, documents, "first")

    first, second, third, *later = documents.asked
    written = {document_of(fresh, first), document_of(fresh, second)}
    # The first two documents' passages were in strata.gold.passage before the third one's fetch failed.
    assert documents.indexed_when_it_failed == written
    indexed = column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage")
    assert written <= indexed and later and document_of(fresh, later[0]) in indexed  # and the run went on
    skipped = fresh.run("SELECT run_id, reader, project_id, document_id, url, reason FROM strata.ops.skipped_documents "
                        "WHERE run_id = 'first'").rows
    [(run_id, reader, project_id, document_id, url, reason)] = skipped
    assert (run_id, reader, project_id, url) == ("first", "passages", "P130164", third)
    assert document_id not in indexed and UNAVAILABLE in reason
    assert [(skip.document_id, skip.reason) for skip in report.skipped] == [(document_id, reason)]


@pytest.fixture
def run_live(monkeypatch):
    """ops/documents/run_live.py as a module, as uv runs it; sys.path goes back after."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("strata_ops_documents_run_live_72",
                                                  ROOT / "ops" / "documents" / "run_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def held(engine) -> dict[str, list]:
    """What each table a second run must leave alone holds, row by row."""
    return {table: sorted(map(repr, engine.run(f"SELECT * FROM {table}").rows)) for table in KEPT}


def test_the_documents_run_writes_as_it_goes_skips_the_third_document_and_exits_0_with_its_counts(
        fresh, run_live, monkeypatch, capsys, caplog):
    """The live script's run (ops/documents/run_live.py) over the fixture, through the nightly job's own path, with
    a fetcher that fails on the third document, as search.worldbank.org answered 503 on October 26, 2026."""
    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 3  # three documents whose text Route A reads, to keep it quick
    monkeypatch.setattr(passages, "load_thresholds", lambda: limits)
    manifest = fmt.load_manifest()
    documents = FailsOnTheThird(fresh, RecordedDocuments(manifest))
    found = readers.Readers(documents, RecordedLayout(manifest), PatternShield(), offline(),
                            plan_projects=lambda engine: [], report_projects=lambda engine: ["P130164"])

    with caplog.at_level(logging.WARNING):
        code = run_live.read_documents(fresh, found, "first")
    printed = capsys.readouterr().out

    first, second, third, *later = documents.asked
    assert documents.indexed_when_it_failed == {document_of(fresh, first), document_of(fresh, second)}
    indexed = column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage")
    [(document_id, reason)] = fresh.run("SELECT document_id, reason FROM strata.ops.skipped_documents "
                                        "WHERE run_id = 'first' AND project_id = 'P130164' AND url = :url",
                                        {"url": third}).rows
    assert code == 0
    assert document_id not in indexed and UNAVAILABLE in reason
    assert f"I skipped document {document_id} of P130164 and went on with the next: {reason}" in caplog.messages
    read = len(documents.asked) - 1  # every document the run asked for, but the third
    assert (read, len(indexed)) == (len(later) + 2, len(later) + 2)
    assert (f"Run first parsed {read} documents, skipped 1 and wrote the passages of {read} to strata.gold.passage."
            in printed)
    assert f"  document {document_id} of P130164, skipped by the passage reader ({third}): {reason}" in printed

    before = held(fresh)
    assert run_live.read_documents(fresh, found, "second") == 0  # the third still fails, and is skipped again
    assert held(fresh) == before  # the second run wrote nothing new
    assert column(fresh, "SELECT run_id FROM strata.ops.skipped_documents") == {"first", "second"}


class Writes:
    """The engine, noting each statement that adds, changes or removes rows of a table in silver or gold. On the SQL
    warehouse each one costs a round trip of a second or more, so a rerun that rewrote every document it holds would
    spend its reading time before it reached a new one."""

    def __init__(self, engine):
        self.engine, self.writes = engine, []  # each write's table, statement and document, when it names one

    def run(self, sql, params=None):
        words = sql.split()
        if words and words[0].upper() in ("DELETE", "INSERT", "MERGE", "UPDATE"):
            document = (params or {}).get("document_id", (params or {}).get("value"))
            self.writes += [(word, sql, document) for word in words
                            if word.startswith(("strata.silver.", "strata.gold."))][:1]
        return self.engine.run(sql, params)

    def insert_rows(self, table, columns, rows, **options):
        if rows and table.startswith(("strata.silver.", "strata.gold.")):
            at = columns.index("document_id") if "document_id" in columns else None
            self.writes += [(table, "INSERT", row[at] if at is not None else None) for row in rows[:1]]
        return self.engine.insert_rows(table, columns, rows, **options)

    def __getattr__(self, name):
        return getattr(self.engine, name)


def test_a_rerun_writes_the_rows_of_only_the_documents_that_changed(fresh):
    """Each document is written as soon as it is read, so a second run reads every document the first one wrote. When
    silver and strata.gold.passage already hold exactly what it read, the run sends no statement that writes that
    document's rows; it still writes what every run writes, the notices' passages and the ISR ratings. A document
    whose rows differ, here one whose passage lost its page number and one that lost a passage from gold, is written
    again and comes back as it was."""
    documents = RecordedDocuments(fmt.load_manifest())
    read_p130164(fresh, documents, "first")
    kept = held(fresh)
    [(changed, passage_id), (lost, gone)] = fresh.run(
        "SELECT document_id, min(passage_id) AS passage_id FROM strata.gold.passage GROUP BY document_id "
        "ORDER BY document_id LIMIT 2").rows
    fresh.run("UPDATE strata.silver.passages SET pdf_page = -1 WHERE passage_id = :id", {"id": passage_id})
    fresh.run("DELETE FROM strata.gold.passage WHERE passage_id = :id", {"id": gone})
    writes = Writes(fresh)

    read_p130164(writes, documents, "second")

    documents_rows = ("strata.silver.documents", "strata.silver.document_page_routes", "strata.silver.passages",
                      "strata.silver.passage_shields", "strata.silver.passage_embeddings", "strata.gold.passage")
    # Every run takes the notices' passages out and reads them again (passages.prune and read_notices).
    rewritten = {document for table, sql, document in writes.writes if table in documents_rows and ":notice" not in sql}
    assert rewritten == {changed, lost}
    assert {table for table, _, _ in writes.writes} <= {*documents_rows, "strata.silver.isr_ratings"}
    assert held(fresh) == kept


def test_a_project_whose_document_list_cannot_be_fetched_is_skipped_and_the_plan_reader_goes_on(fresh, caplog):
    """On October 26, 2026 search.worldbank.org answered 503 for P089634's document list and the run stopped. The
    fixture records no list for P089634, so its list cannot be fetched either: the plan reader skips the project
    and reads the next one's plans."""
    from strata.config import load_sources
    from strata.reader.documents import list_url

    manifest = fmt.load_manifest()
    found = readers.Readers(RecordedDocuments(manifest), RecordedLayout(manifest), None, None,
                            plan_projects=lambda engine: ["P089634", "P156634"], report_projects=lambda engine: [])

    with caplog.at_level(logging.WARNING):
        done = readers.reading(fresh, found, "night", passages._now)

    listing = list_url(load_sources()["documents"].endpoint, "P089634")
    assert list(fresh.run("SELECT reader, project_id, document_id, url, outcome FROM strata.ops.skipped_documents "
                          "WHERE project_id = 'P089634'").rows) == [("plans", "P089634", None, listing, "skipped")]
    assert f"I skipped the plans of P089634 and went on with the next: The fixture has no recording of {listing}." \
        in caplog.messages
    assert done.stopped is None
    assert column(fresh, "SELECT project_id FROM strata.silver.plan_versions") == {"P156634"}


def test_a_documents_run_that_wrote_no_document_exits_2(fresh, run_live, capsys):
    """When every document's fetch fails, nothing reaches strata.gold.passage, and the run says so with exit 2."""

    class FailsEveryText(FailsOnTheThird):
        def text(self, url):
            raise NotFetched(f"I could not fetch {url}: {UNAVAILABLE}")

    manifest = fmt.load_manifest()
    found = readers.Readers(FailsEveryText(fresh, RecordedDocuments(manifest)), RecordedLayout(manifest),
                            PatternShield(), offline(), plan_projects=lambda engine: [],
                            report_projects=lambda engine: ["P130164"])

    assert run_live.read_documents(fresh, found, "nothing") == 2
    assert "skipped" in capsys.readouterr().out
    assert fresh.run("SELECT count(*) FROM strata.gold.passage").rows[0][0] == 0


# ── The reading budget between pages (the nightly run of October 26, 2026) ──

NIGHT = dt.datetime(2026, 10, 26, 6, 40, tzinfo=dt.UTC)
PAGE_MINUTES = 7  # each page the slow parser reads; the fixture's 15 Route B pages of P156634's plans take 105 minutes


class Ticks:
    """One clock for the whole night: seconds for the document host's fetch, as it reads time.monotonic, and the
    same moment in UTC for the job's tasks."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def utc(self) -> dt.datetime:
        return NIGHT + dt.timedelta(seconds=self.now)


class SlowParser:
    """The layout parser config/models.toml names, as a fake whose pages outlast the night's reading time: each page
    takes PAGE_MINUTES, as ai_parse_document took 99 minutes for 97 pages of one plan on October 26, 2026. It reads
    the fixture's recorded layouts."""

    def __init__(self, recorded, ticks, minutes=PAGE_MINUTES):
        self.recorded, self.ticks, self.minutes, self.read = recorded, ticks, minutes, []

    def __call__(self, engine, upload, fetch):  # as readers.live_parser builds the parser it names
        self.name = "ai_parse_document"
        return self

    def parse(self, page):
        self.ticks.now += self.minutes * 60
        self.read.append((page.document_id, page.pdf_page))
        return self.recorded.parse(page)


def test_the_nightly_reading_stops_between_pages_once_its_time_is_spent_and_the_tasks_after_it_run(
        fresh, monkeypatch):
    """parse_and_embed checks the reading time (config/thresholds.toml, ingestion.document_host_minutes) before each
    page the layout parser reads, not only before each request to the host. Once the time is spent, the reader stops
    after the page it is reading: the pages it read stay in strata.bronze.layout_pages, the document it was reading is
    listed as unfinished, and the task ends, so the tasks after it run inside the job's window."""
    from strata import config
    from strata.lakehouse import nightly
    from strata.reader import layout

    manifest = fmt.load_manifest()
    ticks = Ticks()
    slow = SlowParser(RecordedLayout(manifest), ticks)
    monkeypatch.setitem(layout.PARSERS, config.load_layout_parser(), slow)

    def never(url):
        raise AssertionError(f"The night asked the host for {url}; the fixture's documents are recorded.")

    host = readers.document_host(never, None, sleep=ticks.sleep, clock=ticks)
    found = readers.Readers(RecordedDocuments(manifest), readers.live_parser(fresh, host, upload=lambda path, data: None),
                            None, None, plan_projects=lambda engine: ["P156634"], report_projects=lambda engine: [])
    minutes = config.load_thresholds().value("ingestion.document_host_minutes")

    def task(key):
        nightly.main(["--task", key, "--run-id", "night", "--src", "src"], fresh, fetch=lambda source, engine: (),
                     clock=ticks.utc, readers_for=lambda engine: found)

    task("parse_and_embed")

    # 60 minutes at 7 a page: the ninth page starts at minute 56, inside the time, and the tenth is never read.
    assert len(slow.read) == minutes // PAGE_MINUTES + 1 == 9
    assert column(fresh, "SELECT document_id || '/' || pdf_page FROM strata.bronze.layout_pages") == {
        f"{document_id}/{page}" for document_id, page in slow.read}
    [(status, started, finished)] = fresh.run("SELECT status, started_at, finished_at FROM strata.ops.pipeline_runs "
                                              "WHERE run_id = 'night' AND task_key = 'parse_and_embed'").rows
    assert status == "succeeded"
    # It ended one page past the 60 minutes, at minute 63, not at minute 105 after all 15 pages: inside the job's
    # 150 minutes (bundle/nightly.yml, timeout_seconds), with 87 minutes left for the tasks after it.
    assert finished - started == dt.timedelta(minutes=9 * PAGE_MINUTES)
    [(parsed, at_cap, document_id, pdf_page)] = fresh.run(
        "SELECT pages_parsed, stopped_at_cap, stopped_at_document_id, stopped_at_pdf_page FROM strata.ops.parse_runs "
        "WHERE run_id = 'night'").rows
    assert (parsed, at_cap) == (9, False)
    assert (document_id, pdf_page) not in slow.read
    [(reader, outcome, url, reason)] = fresh.run(
        "SELECT reader, outcome, url, reason FROM strata.ops.skipped_documents WHERE run_id = 'night' "
        "AND document_id = :document_id", {"document_id": document_id}).rows
    assert (reader, outcome) == ("plans", "unfinished") and url.endswith(".pdf")
    assert f"page {pdf_page}" in reason and "60 minutes" in reason
    [(measure,)] = fresh.run("SELECT measure FROM strata.ops.data_readiness WHERE run_id = 'night' "
                             "AND source = 'documents' AND subject = 'all'").rows
    assert measure == "document_host_budget_spent"

    later = [step.key for step in nightly.job_tasks()]
    later = later[later.index("parse_and_embed") + 1:]
    for key in later:
        task(key)
    assert len(later) == 7
    assert list(fresh.run("SELECT task_key, status FROM strata.ops.pipeline_runs WHERE run_id = 'night' "
                          "AND task_key <> 'parse_and_embed' ORDER BY started_at, finished_at").rows) == [
        (key, "succeeded") for key in later]


class AnyPage:
    """What ai_parse_document gives for a page the fixture records no words for: its text."""

    def parse(self, page):
        from strata.reader.layout import Layout

        return Layout(text=f"The words on page {page.pdf_page}.")


def test_the_passage_reader_keeps_the_documents_it_wrote_when_the_time_runs_out_inside_a_document(fresh, monkeypatch):
    """The same check inside the passage reader: P130164's two ICR Reviews have no page for the layout parser, so
    their passages are written; its ICR sends 7 pages to the parser, and at 20 minutes a page the night's 60 minutes
    run out after the third. The ICR is listed as unfinished, its 3 pages stay in bronze, and the reading ends."""
    from strata import config
    from strata.reader import layout

    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 3
    monkeypatch.setattr(passages, "load_thresholds", lambda: limits)
    manifest = fmt.load_manifest()
    ticks = Ticks()
    slow = SlowParser(AnyPage(), ticks, minutes=20)
    monkeypatch.setitem(layout.PARSERS, config.load_layout_parser(), slow)
    host = readers.document_host(lambda url: b"", None, sleep=ticks.sleep, clock=ticks)
    found = readers.Readers(RecordedDocuments(manifest), readers.live_parser(fresh, host, upload=lambda path, data: None),
                            PatternShield(), offline(), plan_projects=lambda engine: [],
                            report_projects=lambda engine: ["P130164"])

    done = readers.reading(fresh, found, "night", ticks.utc)

    icr_reviews, icr = {"34056616", "31906731"}, "31525018"  # tests/ground_truth/values.toml's showcase documents
    assert {document_id for document_id, _ in slow.read} == {icr} and len(slow.read) == 3
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage") == icr_reviews
    assert column(fresh, "SELECT document_id || '/' || pdf_page FROM strata.bronze.layout_pages") == {
        f"{icr}/{page}" for _, page in slow.read}
    [(reader, outcome, reason)] = fresh.run("SELECT reader, outcome, reason FROM strata.ops.skipped_documents "
                                            "WHERE run_id = 'night' AND document_id = :icr", {"icr": icr}).rows
    assert (reader, outcome) == ("passages", "unfinished") and "60 minutes" in reason
    assert fresh.run("SELECT pages_parsed, stopped_at_cap, stopped_at_document_id FROM strata.ops.parse_runs "
                     "WHERE run_id = 'night'").rows[0] == (3, False, icr)
    assert (done.stopped.measure, done.tally.written) == ("document_host_budget_spent", 2)


def test_the_live_run_reads_passages_first_so_plan_pages_that_outlast_the_time_still_leave_passages(
        fresh, run_live, monkeypatch, capsys):
    """On October 26, 2026 the plan reader spent the whole reading time on one plan's scanned pages, and the passage
    reader never started: strata.gold.passage still held no row. The live run (ops/documents/run_live.py) reads the
    slice's reports into passages first, then the Procurement Plans with the time that is left. Here P130164's three
    documents are read first; then P156634's plan pages, at 7 minutes each, outlast the 60 minutes, and the plan the
    reader was in is listed as unfinished. The run wrote passages, so it exits 0 and the index is synced after it."""
    from strata import config
    from strata.reader import layout

    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 3
    monkeypatch.setattr(passages, "load_thresholds", lambda: limits)
    manifest = fmt.load_manifest()
    ticks = Ticks()
    slow = SlowParser(RecordedLayout(manifest), ticks)
    monkeypatch.setitem(layout.PARSERS, config.load_layout_parser(), slow)
    host = readers.document_host(lambda url: b"", None, sleep=ticks.sleep, clock=ticks)
    found = readers.Readers(RecordedDocuments(manifest), readers.live_parser(fresh, host, upload=lambda path, data: None),
                            PatternShield(), offline(), plan_projects=lambda engine: ["P156634"],
                            report_projects=lambda engine: ["P130164"])

    code = run_live.read_documents(fresh, found, "live", clock=ticks.utc)
    printed = capsys.readouterr().out

    assert code == 0
    # P130164's two ICR Reviews and its ICR, whose 7 scanned pages took 49 of the 60 minutes, are written first.
    icr_reviews, icr = {"34056616", "31906731"}, "31525018"  # tests/ground_truth/values.toml's showcase documents
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage") == {*icr_reviews, icr}
    # Then the plan reader reads P156634's plan pages with the 11 minutes left, and the plan it reaches after them
    # is listed as unfinished.
    plan_pages = [page for page in slow.read if page[0] != icr]
    assert len(plan_pages) == 2
    [(project_id, document_id, reason)] = fresh.run(
        "SELECT project_id, document_id, reason FROM strata.ops.skipped_documents WHERE run_id = 'live' "
        "AND reader = 'plans' AND outcome = 'unfinished'").rows
    assert project_id == "P156634" and "60 minutes" in reason
    assert document_id not in {read for read, _ in slow.read}
    assert "It stopped before it finished: I spent the night's 60 minutes" in printed
