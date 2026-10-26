"""The documents run keeps what it parsed (seam 1; ticket 72).

On October 26, 2026 a live documents run parsed 358 scanned pages over four hours, then stopped with exit 2 when
search.worldbank.org answered 503 for one project's document list, and strata.gold.passage still held no row: the
run wrote every passage at the end. The passage reader now writes each document's passages as soon as it has read
that document, skips a document whose fetch or parse fails with its reason in strata.ops.skipped_documents, and
goes on. These tests run it over the recorded fixture with a fetcher that fails on the third document.
"""

import pytest
from passage_rows import digest

from strata.config import load_thresholds
from strata.fixture import recorded as fmt
from strata.knowledge.embed import offline
from strata.knowledge.shields import PatternShield
from strata.lakehouse import catalog, passages
from strata.lakehouse.engine import DuckDBEngine
from strata.reader.documents import NotFetched, RecordedDocuments
from strata.reader.layout import RecordedLayout

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
