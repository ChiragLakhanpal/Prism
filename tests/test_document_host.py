"""The nightly job and the World Bank's document host (seam 1; ticket 43).

On October 25, 2026 documents.worldbank.org answered 403 to every request from one computer after some hundreds of
PDFs asked for back to back. The job's live reader waits between requests (config/sources.toml, pause_seconds),
keeps each answer so a document is fetched once, and stops at the first refusal; parse_and_embed then writes a
data readiness note and finishes, and the next night goes on from where it stopped.
"""

import datetime as dt
import urllib.error

import pytest

from strata import config
from strata.lakehouse import catalog, nightly, readers
from strata.lakehouse.engine import DuckDBEngine
from strata.reader.documents import BudgetSpent, HostRefused, PoliteFetch, RecordedDocuments, list_url

NIGHT = dt.datetime(2026, 10, 24, 7, tzinfo=dt.UTC)


class Host:
    """A document host that answers each address with its own bytes, until it starts refusing."""

    def __init__(self, refuse_from: int | None = None):
        self.asked: list[str] = []
        self.refuse_from = refuse_from

    def __call__(self, url):
        self.asked.append(url)
        if self.refuse_from is not None and len(self.asked) >= self.refuse_from:
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        return f"the document at {url}".encode()


class Clock:
    def __init__(self):
        self.now, self.slept = 100.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(round(seconds, 3))
        self.now += seconds


def test_the_documents_source_names_the_pause_between_requests():
    assert config.load_sources()["documents"].pause_seconds == 3.0


def test_the_live_fetch_waits_between_requests_and_asks_for_each_document_once(tmp_path):
    host, clock = Host(), Clock()
    fetch = PoliteFetch(host, pause=3.0, cache=tmp_path / "fetched", sleep=clock.sleep, clock=clock)

    first = fetch("https://documents.worldbank.org/a.pdf")
    clock.now += 1.0  # the reader spends a second on the first document
    fetch("https://documents.worldbank.org/b.pdf")
    again = fetch("https://documents.worldbank.org/a.pdf")  # a later night, or the layout parser, asks again

    assert first == again == b"the document at https://documents.worldbank.org/a.pdf"
    assert host.asked == ["https://documents.worldbank.org/a.pdf", "https://documents.worldbank.org/b.pdf"]
    assert clock.slept == [2.0]
    assert PoliteFetch(host, 3.0, cache=tmp_path / "fetched")("https://documents.worldbank.org/b.pdf").startswith(b"the")
    assert len(host.asked) == 2


def test_the_job_asks_for_each_project_s_document_list_every_night_and_keeps_only_the_documents(tmp_path):
    """The job's fetch keeps each document it fetched, but never a project's list: the list's address is the same
    every night, and a kept list would hide every document disclosed after the first night (review B1)."""
    host, clock = Host(), Clock()
    fetch = readers.document_host(host, tmp_path / "fetched", sleep=clock.sleep, clock=clock)
    listing = list_url(config.load_sources()["documents"].endpoint, "P156634")
    pdf = "https://documents.worldbank.org/curated/en/099/a.pdf"

    fetch(listing)
    fetch(pdf)
    fetch(listing)  # the next night
    fetch(pdf)

    assert host.asked == [listing, pdf, listing]


def test_the_fetch_stops_asking_once_the_night_s_reading_time_is_spent(tmp_path):
    """At 3 seconds a request, the backlog of plans and reports would outlast the job's 150 minutes and cancel
    every task after parse_and_embed (review B3). The job's fetch stops at the night's budget instead."""
    host, clock = Host(), Clock()
    fetch = PoliteFetch(host, pause=3.0, cache=tmp_path, sleep=clock.sleep, clock=clock, budget=60.0)

    fetch("https://documents.worldbank.org/a.pdf")
    clock.now += 58.0
    fetch("https://documents.worldbank.org/b.pdf")  # second 58 of the budget's 60
    clock.now += 1.0
    with pytest.raises(BudgetSpent, match="1 minute"):
        fetch("https://documents.worldbank.org/c.pdf")  # the pause runs to second 61, past the budget
    with pytest.raises(BudgetSpent):
        fetch("https://documents.worldbank.org/a.pdf")  # even a kept document: the night's reading is over

    assert host.asked == ["https://documents.worldbank.org/a.pdf", "https://documents.worldbank.org/b.pdf"]


def test_the_job_s_reading_budget_comes_from_the_thresholds_file(tmp_path):
    minutes = config.load_thresholds().value("ingestion.document_host_minutes")

    assert minutes == 120  # the user's call of October 27, 2026 (decision 95, ticket 108); 60 before
    assert readers.document_host(Host(), tmp_path).budget == minutes * 60


def test_a_refusal_from_the_host_stops_the_fetch(tmp_path):
    fetch = PoliteFetch(Host(refuse_from=1), pause=0.0, cache=tmp_path)

    with pytest.raises(HostRefused, match="answered HTTP 403"):
        fetch("https://documents.worldbank.org/a.pdf")
    assert list(tmp_path.iterdir()) == []


class RefusesAfter:
    """The recorded documents, with a host that refuses every text after the first few, as the real one did, or
    a fetch that has spent the night's reading time by then."""

    def __init__(self, documents, texts: int | None, stop=lambda url: HostRefused(url, 403)):
        self.documents, self.texts, self.given, self.stop = documents, texts, 0, stop

    def listing(self, url):
        return self.documents.listing(url)

    def text(self, url):
        if self.texts is not None and self.given >= self.texts:
            raise self.stop(url)
        found = self.documents.text(url)  # a plan the fixture does not record raises NotFetched, and is skipped
        self.given += 1
        return found

    def pages(self, url):
        return self.documents.pages(url)


def plans_only(documents):
    found = readers.recorded(documents=documents)
    return readers.Readers(found.documents, found.layout, None, None, plan_projects=lambda engine: ["P156634"],
                           report_projects=lambda engine: [])


STOPS = {
    "document_host_refused": (lambda url: HostRefused(url, 403),
                              "The document host answered HTTP 403 on October 24, 2026, so I stopped reading documents "
                              "for the night."),
    "document_host_budget_spent": (lambda url: BudgetSpent(url, 3600),
                                   "I stopped reading documents on October 24, 2026, after the night's 60 minutes"),
}


@pytest.mark.parametrize("measure", list(STOPS))
def test_a_night_the_reading_stops_finishes_with_a_note_and_the_next_night_goes_on_from_there(measure, monkeypatch,
                                                                                             every_plan_version):
    """The plan rows read before the stop reach strata.gold.package the same night (review r2 follow-up 2). The
    plan reader reads every version of P156634's plans here, so the stop falls between two of them."""
    from strata.fixture import recorded as fmt
    from strata.lakehouse import gold

    synced, sync = [], gold.sync
    monkeypatch.setattr(gold, "sync", lambda engine, table: synced.append(table) or sync(engine, table))
    stop, sentence = STOPS[measure]
    documents = RecordedDocuments(fmt.load_manifest())
    with DuckDBEngine.open() as engine:
        catalog.build(engine)

        def night(run_id, stopping):
            nightly.main(["--task", "parse_and_embed", "--run-id", run_id, "--src", "src"], engine,
                         fetch=lambda source, _: (), clock=lambda: NIGHT,
                         readers_for=lambda _: plans_only(RefusesAfter(documents, stopping, stop)))
            return engine.run("SELECT count(*) FROM strata.bronze.document_texts").rows[0][0]

        held = night("night-1", stopping=2)

        status = engine.run("SELECT status FROM strata.ops.pipeline_runs WHERE run_id = 'night-1'").rows
        note = engine.run("SELECT measure, kind, as_of, detail FROM strata.ops.data_readiness "
                          "WHERE run_id = 'night-1' AND source = 'documents' AND subject = 'all'").rows
        assert (held, list(status), synced) == (2, [("succeeded",)], ["package"])
        assert note[0][:3] == (measure, "fresh", NIGHT.date())
        assert note[0][3].startswith(sentence)

        assert night("night-2", stopping=None) == 11  # data/fixture/README.md: P156634's 11 plan versions
