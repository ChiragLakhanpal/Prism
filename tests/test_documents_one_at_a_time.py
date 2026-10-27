"""The passage reader fetches, reads and writes one document at a time, inside the night's reading time (seam 1;
ticket 86).

On the paid workspace's first night, October 27, 2026 (run 564462742591748), parse_and_embed read P130164's plans
for 12 minutes, then spent the rest of the night's 60 minutes fetching 163 of P156634's Procurement Plans, and
strata.gold.passage held no row at the end. The fixture's documents are recorded, so a run over it never waits on
the host. These tests give the readers a fake document host that serves the recorded files by address, counts every
request and takes a share of the night's reading time for each one.
"""

import datetime as dt
import importlib.util
import json
import logging
import sys
import urllib.error
from pathlib import Path

import pytest

from strata.config import load_sources, load_thresholds
from strata.fixture import recorded as fmt
from strata.knowledge.embed import offline
from strata.knowledge.shields import PatternShield
from strata.lakehouse import catalog, nightly, passages, plans, readers
from strata.lakehouse.engine import DuckDBEngine
from strata.reader.documents import Fetched, LiveDocuments, NotFetched, RecordedDocuments
from strata.reader.layout import Layout, ParseFailed, RecordedLayout, https

ROOT = Path(__file__).resolve().parents[1]
NIGHT = dt.datetime(2026, 10, 27, 0, 27, tzinfo=dt.UTC)
ICR_REVIEWS = ("34056616", "31906731")  # P130164's first two documents, newest first (tests/ground_truth/values.toml)
ICR = "31525018"  # its third, the ICR, whose paragraph 54 holds the rebidding lesson


class Ticks:
    """One clock for the night: seconds for the document host's fetch, and the same moment in UTC for the job."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def utc(self) -> dt.datetime:
        return NIGHT + dt.timedelta(seconds=self.now)


class Host:
    """documents.worldbank.org and search.worldbank.org as a fake: each recorded list, text and PDF answered by its
    address, each request counted and taking `seconds` of the night. When a document's text is asked for, it notes
    which documents strata.gold.passage held at that moment."""

    def __init__(self, engine, ticks, seconds: float):
        self.engine, self.ticks, self.seconds = engine, ticks, seconds
        self.recorded = RecordedDocuments(fmt.load_manifest())
        self.asked: list[str] = []
        self.indexed_when_asked: dict[str, set[str]] = {}

    def __call__(self, url: str) -> bytes:
        self.asked.append(url)
        self.ticks.now += self.seconds
        try:
            found = self.recorded.text(url)
        except NotFetched:
            pass
        else:
            self.indexed_when_asked[url] = column(self.engine, "SELECT DISTINCT document_id FROM strata.gold.passage")
            return found.body.encode("utf-8")
        try:
            return fmt.PAGE_BREAK.join(self.recorded.pages(url).body).encode("utf-8")
        except NotFetched:
            pass
        try:
            return json.dumps(self.recorded.listing(url).body).encode("utf-8")
        except NotFetched:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None) from None


class FromTheHost(LiveDocuments):
    """The live documents source over the fake host. A PDF's pages come as the fixture records them, with a form feed
    between pages, so they are split there instead of read with pypdf."""

    def pages(self, url):
        return Fetched(url, self._get(url).decode("utf-8").split(fmt.PAGE_BREAK), self.clock())


def column(engine, sql, **params) -> set[str]:
    return {str(row[0]) for row in engine.run(sql, params).rows}


@pytest.fixture
def fresh():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


@pytest.fixture
def three_documents(monkeypatch):
    """At most three documents whose text Route A reads, to keep a run quick."""
    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 3
    monkeypatch.setattr(passages, "load_thresholds", lambda: limits)


def hold_in_bronze(engine, project_id: str, document_id: str) -> None:
    """A document an earlier night fetched: its text and pages are in bronze, so reading it asks the host nothing."""
    recorded = RecordedDocuments(fmt.load_manifest())
    plans.fetch_listing(engine, recorded, load_sources()["documents"].endpoint, project_id)
    [entry] = [found.entry() for found in passages.listed_documents(engine, project_id)
               if found.document_id == document_id]
    plans.fetch_documents(engine, recorded, project_id, [entry])


def night(engine, run_id, host, ticks, projects=("P130164", "P156634")):
    """The nightly job's parse_and_embed task, with the passage reader over the fake host and the night's reading
    time (config/thresholds.toml, ingestion.document_host_minutes)."""
    fetch = readers.document_host(host, None, sleep=ticks.sleep, clock=ticks)
    found = readers.Readers(FromTheHost(fetch, clock=ticks.utc), None, PatternShield(), offline(),
                            plan_projects=lambda _: [], report_projects=lambda _: list(projects), budget=fetch)
    nightly.main(["--task", "parse_and_embed", "--run-id", run_id, "--src", "src"], engine,
                 fetch=lambda source, _: (), clock=ticks.utc, readers_for=lambda _: found)
    return fetch


def test_each_document_is_written_before_the_next_is_fetched_and_the_time_is_checked_between_documents(
        fresh, three_documents, caplog):
    """Each request takes a fifth of the night's 60 minutes: P130164's list, then each ICR Review's text and PDF. So
    the time is spent once the second document is written. The ICR is already in bronze and needs no request, so only
    the check between documents keeps the reader from reading it."""
    hold_in_bronze(fresh, "P130164", ICR)
    minutes = load_thresholds().value("ingestion.document_host_minutes")
    ticks = Ticks()
    host = Host(fresh, ticks, seconds=minutes * 60 / 5)

    with caplog.at_level(logging.WARNING):
        night(fresh, "night-1", host, ticks)

    first, second = (passages_of(fresh, document_id) for document_id in ICR_REVIEWS)
    # The first document's passages were in strata.gold.passage before the host was asked for the second's text.
    assert host.indexed_when_asked[https(first.text_url)] == set()
    assert host.indexed_when_asked[https(second.text_url)] == {ICR_REVIEWS[0]}
    assert len(host.asked) == 5  # the list, and each ICR Review's text and PDF
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage") == set(ICR_REVIEWS)

    # The rest are listed as not read: P130164's other 15 reports (it has 17, tests/test_nightly_delta.py), the ICR
    # first, and P156634, whose list the night never reached.
    left = fresh.run("SELECT reader, project_id, document_id, outcome, reason FROM strata.ops.skipped_documents "
                     "WHERE run_id = 'night-1' ORDER BY skipped_at, project_id, document_id").rows
    assert {(reader, outcome) for reader, _, _, outcome, _ in left} == {("passages", "not_read")}
    documents = [document_id for _, project_id, document_id, _, _ in left if project_id == "P130164"]
    assert len(documents) == len(set(documents)) == 15 and ICR in documents
    assert not set(ICR_REVIEWS) & set(documents)
    assert [(project_id, document_id) for _, project_id, document_id, _, _ in left if project_id != "P130164"] == [
        ("P156634", None)]
    assert all("60 minutes" in reason for *_, reason in left)

    # The task's record names what it wrote and what it left: strata.silver.documents holds the two documents it
    # finished, the stop's note counts both, and the task's log names each one. strata.ops.documents_read counts a
    # whole run only, as the data readiness measures do, so the dashboard's documents and Coverage still agree.
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.silver.documents") == set(ICR_REVIEWS)
    assert fresh.run("SELECT run_id FROM strata.ops.documents_read WHERE run_id = 'night-1'").rows == ()
    [(status,)] = fresh.run("SELECT status FROM strata.ops.pipeline_runs WHERE run_id = 'night-1'").rows
    [(measure, detail)] = fresh.run("SELECT measure, detail FROM strata.ops.data_readiness WHERE run_id = 'night-1' "
                                    "AND source = 'documents' AND subject = 'all'").rows
    assert (status, measure) == ("succeeded", "document_host_budget_spent")
    assert ("I wrote the passages of two documents before the stop, and left 15 documents and one project's "
            "document list for the next night.") in detail
    assert any(f"I wrote the passages of two documents before the stop: {ICR_REVIEWS[0]} and {ICR_REVIEWS[1]}." in message
               for message in caplog.messages)
    assert any(message.startswith("I stopped before I reached 15 documents and one project's document list. ")
               and ICR in message and "the list of P156634" in message for message in caplog.messages)

    # The next night, with a fresh 60 minutes, asks the host for P130164's list only: the ICR Reviews and the ICR are
    # in bronze. It writes nothing twice: the ICR Reviews' rows stay as they were, no text is scanned or embedded a
    # second time, and the ICR, the third document, is written.
    kept = rows_of(fresh, ICR_REVIEWS)
    host.asked.clear()

    night(fresh, "night-2", host, ticks)

    assert [url for url in host.asked if "proid=" not in url] == []
    assert rows_of(fresh, ICR_REVIEWS) == kept
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage") == {*ICR_REVIEWS, ICR}
    for table, model in (("passage_shields", "shield"), ("passage_embeddings", "model")):
        assert fresh.run(f"SELECT text_hash FROM strata.silver.{table} GROUP BY text_hash, {model} "
                         "HAVING count(*) > 1").rows == ()
    assert fresh.run("SELECT document_id FROM strata.bronze.document_texts GROUP BY document_id "
                     "HAVING count(*) > 1").rows == ()


# The tables whose rows a rerun must leave as they were, and the passages' scans and vectors.
DOCUMENT_TABLES = ("strata.bronze.document_texts", "strata.bronze.document_pages", "strata.silver.documents",
                   "strata.silver.document_page_routes", "strata.silver.passages", "strata.gold.passage")


def rows_of(engine, document_ids) -> dict[str, list[str]]:
    """Every row the documents have in each table, and every scan and vector of their passages' texts."""
    ids = ",".join(document_ids)
    found = {table: sorted(map(repr, engine.run(
        f"SELECT * FROM {table} WHERE array_contains(split(:ids, ','), document_id)", {"ids": ids}).rows))
        for table in DOCUMENT_TABLES}
    for table in ("strata.silver.passage_shields", "strata.silver.passage_embeddings"):
        found[table] = sorted(map(repr, engine.run(
            f"SELECT * FROM {table} WHERE text_hash IN (SELECT text_hash FROM strata.silver.passages "
            "WHERE array_contains(split(:ids, ','), document_id))", {"ids": ids}).rows))
    return found


@pytest.fixture
def run_live(monkeypatch):
    """ops/documents/run_live.py as a module, as uv runs it; sys.path goes back after."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("strata_ops_documents_run_live_86",
                                                  ROOT / "ops" / "documents" / "run_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_stop_that_left_a_thousand_documents_or_more_writes_the_count_with_its_comma():
    """The readers' notes write one to nine in words and larger counts as numerals with commas, as every other count
    in Strata (ticket 86's review, F2): "1,234 documents", never "1234 documents"."""
    assert plans.left_words(1234, 12) == "1,234 documents and 12 projects' document lists"
    assert plans.left_words(1, 1) == "one document and one project's document list"


def test_the_live_documents_run_names_what_it_wrote_and_what_the_stop_left(fresh, three_documents, run_live, capsys):
    """ops/documents/run_live.py over the same fake host, with the readers its main() builds (document_readers, then
    live_readers): the night's time is checked between documents there too, so the ICR, which bronze holds and
    which needs no request, is not read once the time is spent. Its last lines count the documents left apart from
    any it left unfinished, and name each one."""
    hold_in_bronze(fresh, "P130164", ICR)
    minutes = load_thresholds().value("ingestion.document_host_minutes")
    ticks = Ticks()
    host = Host(fresh, ticks, seconds=minutes * 60 / 5)
    live, layout = run_live.document_readers(fresh, upload=lambda path, data: None, fetch=host, cache=None,
                                             sleep=ticks.sleep, clock=ticks)
    found = run_live.live_readers(FromTheHost(live.fetch, clock=ticks.utc), layout, PatternShield(), offline(),
                                  report_projects=lambda _: ["P130164", "P156634"], plan_projects=lambda _: [])

    assert run_live.read_documents(fresh, found, "live", clock=ticks.utc) == 0
    printed = capsys.readouterr().out

    assert ("Run live parsed 2 documents, skipped 0 and wrote the passages of 2 to strata.gold.passage. The stop left "
            "15 documents and one project's document list not read, for the next run.") in printed
    assert f"  document {ICR} of P130164, not read by the passage reader" in printed
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage") == set(ICR_REVIEWS)
    assert "  the document list of P156634, not read by the passage reader" in printed


def passages_of(engine, document_id: str) -> passages.Listed:
    [found] = [listed for listed in passages.listed_documents(engine, "P130164") if listed.document_id == document_id]
    return found


# ── The night's time shared between the readers ──────────────────────────

PAGE_MINUTES = 7  # each page the slow layout parser reads; P156634's 15 Route B pages of plans take 105 minutes


class SlowParser:
    """The layout parser config/models.toml names, as a fake whose pages take PAGE_MINUTES each, as ai_parse_document
    took 99 minutes for 97 pages of one plan on October 26, 2026. It reads the fixture's recorded layouts, and gives a
    page that has none its words as text."""

    name = "ai_parse_document"

    def __init__(self, ticks):
        self.ticks, self.read = ticks, []
        self.recorded = RecordedLayout(fmt.load_manifest())

    def __call__(self, engine, upload, fetch):  # as readers.live_parser builds the parser it names
        return self

    def parse(self, page):
        self.ticks.now += PAGE_MINUTES * 60
        self.read.append((page.document_id, page.pdf_page))
        try:
            return self.recorded.parse(page)
        except ParseFailed:
            return Layout(text=f"The words on page {page.pdf_page}.")


def test_the_plan_reader_leaves_the_passage_reader_its_minutes_of_the_night(fresh, three_documents, monkeypatch):
    """On October 27, 2026 the plan reader used the whole night's reading time and the passage reader never started.
    The plan reader reads first and stops once only the passage reader's minutes are left (config/thresholds.toml,
    ingestion.passage_reader_minutes); its unfinished plan waits for the next night. The passage reader then writes
    P130164's two ICR Reviews and stops inside the ICR when the night's 60 minutes are spent."""
    from strata import config
    from strata.reader import layout

    limits = config.load_thresholds()
    night_minutes = limits.value("ingestion.document_host_minutes")
    passage_minutes = limits.value("ingestion.passage_reader_minutes")
    ticks = Ticks()
    slow = SlowParser(ticks)
    monkeypatch.setitem(layout.PARSERS, config.load_layout_parser(), slow)

    def never(url):
        raise AssertionError(f"The night asked the host for {url}; the fixture's documents are recorded.")

    fetch = readers.document_host(never, None, sleep=ticks.sleep, clock=ticks)
    found = readers.Readers(RecordedDocuments(fmt.load_manifest()),
                            readers.live_parser(fresh, fetch, upload=lambda path, data: None), PatternShield(),
                            offline(), plan_projects=lambda _: ["P156634"], report_projects=lambda _: ["P130164"],
                            budget=fetch)

    nightly.main(["--task", "parse_and_embed", "--run-id", "night", "--src", "src"], fresh,
                 fetch=lambda source, _: (), clock=ticks.utc, readers_for=lambda _: found)

    # 30 minutes for the plans at 7 a page: the fifth page starts at minute 28, and the sixth waits for the next night.
    plan_pages = [page for page in slow.read if page[0] != ICR]
    assert (night_minutes, passage_minutes) == (60, 30)
    assert len(plan_pages) == 5
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage") == set(ICR_REVIEWS)
    [(_, icr, passages_reason), (plans_project, _, plans_reason)] = fresh.run(
        "SELECT project_id, document_id, reason FROM strata.ops.skipped_documents WHERE run_id = 'night' "
        "AND outcome = 'unfinished' ORDER BY reader").rows  # passages, then plans
    assert icr == ICR and "60 minutes" in passages_reason
    assert plans_project == "P156634"
    assert "30 of the night's 60 minutes" in plans_reason and "for the passage reader" in plans_reason
    # One note for the night, when its 60 minutes were spent: the plans' share is not a stop for the night.
    [(measure,)] = fresh.run("SELECT measure FROM strata.ops.data_readiness WHERE run_id = 'night' "
                             "AND source = 'documents' AND subject = 'all'").rows
    assert measure == "document_host_budget_spent"


def test_a_plan_reader_stopped_at_its_share_while_it_fetches_lists_the_plans_it_left(fresh, three_documents):
    """On October 27, 2026 the plan reader's time ran out while it fetched 163 of P156634's 240 Procurement Plans, and
    the run's record was empty. Here each request takes three minutes, so the plan reader's 30 minutes end while it
    fetches P156634's plans, most of which the fixture does not record (the host answers 404). The run's record
    names each plan: the ones the host could not give before the stop as skipped, and every plan bronze does not hold
    and the stop left as not read, as is the fixture's other plan project's document list. Then the passage reader
    writes P130164's documents in the minutes left."""
    ticks = Ticks()
    host = Host(fresh, ticks, seconds=3 * 60)
    fetch = readers.document_host(host, None, sleep=ticks.sleep, clock=ticks)
    plan_projects = list(readers.fixture_plan_projects())
    assert plan_projects == ["P156634", "P161305"]
    found = readers.Readers(FromTheHost(fetch, clock=ticks.utc), RecordedLayout(fmt.load_manifest()),
                            PatternShield(), offline(), plan_projects=lambda _: plan_projects,
                            report_projects=lambda _: ["P130164"], budget=fetch)

    nightly.main(["--task", "parse_and_embed", "--run-id", "night", "--src", "src"], fresh,
                 fetch=lambda source, _: (), clock=ticks.utc, readers_for=lambda _: found)

    record = fresh.run("SELECT project_id, document_id, outcome, reason FROM strata.ops.skipped_documents "
                       "WHERE run_id = 'night' AND reader = 'plans'").rows
    listed = {entry.document_id for entry in plans.listed_plans(fresh, "P156634").entries}
    held = column(fresh, "SELECT document_id FROM strata.bronze.document_texts WHERE project_id = 'P156634'")
    skipped = {document_id for project_id, document_id, outcome, _ in record
               if project_id == "P156634" and outcome == "skipped"}
    unread = [(document_id, reason) for project_id, document_id, outcome, reason in record
              if project_id == "P156634" and outcome == "not_read"]
    assert skipped and unread  # the host said 404 for some plans before the stop, and the stop left the rest
    # Each listed plan is in bronze, skipped or not read, and only one of them.
    assert len(unread) == len({document_id for document_id, _ in unread})
    assert sorted([*held, *skipped, *(document_id for document_id, _ in unread)]) == sorted(listed)
    assert all(reason.startswith("I stopped before I reached this plan. I spent 30 of the night's 60 minutes for "
                                 "the document host and kept the rest for the passage reader") for _, reason in unread)
    assert [(project_id, document_id, outcome) for project_id, document_id, outcome, _ in record
            if project_id != "P156634"] == [("P161305", None, "not_read")]

    # The passage reader still had its minutes: it wrote P130164's three documents (the fixture's cap here).
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.gold.passage") == {*ICR_REVIEWS, ICR}


DEMO_PLANS = ("40132287", "40122770", "40119876")  # P156634's three newest Procurement Plans: October 9, August 17
# and July 31, 2026 (config/slice.toml's demo plan is the first)


def test_the_plan_reader_fetches_a_project_s_newest_plan_first(fresh):
    """On October 27, 2026 the plan reader fetched P156634's plans oldest first and spent the night's second pass on an
    August 2023 plan, so the October 9, 2026 demo plan never reached bronze. It now asks for a project's plans newest
    first, by the date the documents API gives. Each request takes a seventh of the plan reader's 30 minutes: the
    project's document list, then the text and PDF of each of the three newest plans. The rest wait as not read."""
    limits = load_thresholds()
    share = (limits.value("ingestion.document_host_minutes") - limits.value("ingestion.passage_reader_minutes")) * 60
    ticks = Ticks()
    host = Host(fresh, ticks, seconds=share / 7)
    fetch = readers.document_host(host, None, sleep=ticks.sleep, clock=ticks)
    found = readers.Readers(FromTheHost(fetch, clock=ticks.utc), RecordedLayout(fmt.load_manifest()),
                            PatternShield(), offline(), plan_projects=lambda _: ["P156634"],
                            report_projects=lambda _: [], budget=fetch)

    nightly.main(["--task", "parse_and_embed", "--run-id", "night", "--src", "src"], fresh,
                 fetch=lambda source, _: (), clock=ticks.utc, readers_for=lambda _: found)

    listed = plans.listed_plans(fresh, "P156634").entries
    by_text = {https(entry.text_url): entry for entry in listed}
    asked = [by_text[url] for url in host.asked if url in by_text]
    assert [entry.document_id for entry in asked] == list(DEMO_PLANS)
    assert [entry.plan_date for entry in asked] == sorted((entry.plan_date for entry in asked), reverse=True)
    assert column(fresh, "SELECT document_id FROM strata.bronze.document_texts WHERE project_id = 'P156634'") == set(
        DEMO_PLANS)

    # Every older plan is listed as not read, for the next night.
    record = fresh.run("SELECT document_id, outcome FROM strata.ops.skipped_documents WHERE run_id = 'night' "
                       "AND reader = 'plans'").rows
    assert {outcome for _, outcome in record} == {"not_read"}
    assert sorted(document_id for document_id, _ in record) == sorted(
        entry.document_id for entry in listed if entry.document_id not in DEMO_PLANS)
