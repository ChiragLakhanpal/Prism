"""A "next day" delta through the nightly job (seam 1; ticket 43's criteria 1 and 6).

The fixture records every document of P130164 and P156634, so the night before is the fixture with two documents
held back: P130164's ICR (D31525018, disclosed November 2, 2019), whose paragraph 54 holds the rebidding lesson,
and the Coast Water Services Board's Procurement Plan of August 17, 2026 (40122770), the first to list
KE-CWSB-567630-CW-DIR. Between the two nights, people act as they would by day: a lead adds IEG's lesson from the
ICR Review to the library, an author saves a draft that cites it at version 1, and a re-check changes its wording
to version 2. On the next night both documents appear in the documents API's lists, and the job takes in only
them. The recorded pages here are the projects source's alone, which the readers need for each passage's header
and each lesson's region; the other structured sources would only slow the test.
"""

import copy
import datetime as dt
from contextlib import contextmanager
from pathlib import Path

import pytest
from lesson_scenario import ASHA, IEG_LESSON, OMAR, WANJIRU, decide, review_on
from nightly_helpers import Unclosed, clock

from strata.config import load_thresholds
from strata.drafts.store import DraftStore, NewDraft
from strata.fixture import recorded as fmt
from strata.lakehouse import catalog, nightly, pages, plans, readers
from strata.lakehouse.engine import DuckDBEngine
from strata.reader.documents import Fetched, RecordedDocuments

ICR, PLAN = "31525018", "40122770"
PLAN_ORDER = [task.key for task in nightly.job_tasks()]
NIGHT_ONE = dt.datetime(2026, 10, 23, 7, tzinfo=dt.UTC)  # 03:00 in Washington
DAY = dt.date(2026, 10, 23)
NIGHT_TWO = dt.datetime(2026, 10, 24, 7, tzinfo=dt.UTC)


class TheNightBefore:
    """The recorded documents as the documents API listed them a day earlier, before the two were published."""

    def __init__(self, documents, held: set[str]):
        self.documents, self.held = documents, held

    def listing(self, url):
        fetched = self.documents.listing(url)
        body = copy.deepcopy(fetched.body)
        body["documents"] = {key: document for key, document in body.get("documents", {}).items()
                             if not (isinstance(document, dict) and str(document.get("id")) in self.held)}
        return Fetched(url, body, fetched.fetched_at - dt.timedelta(days=1))

    def text(self, url):
        return self.documents.text(url)

    def pages(self, url):
        return self.documents.pages(url)


def projects_only(source, engine):
    return pages.recorded_pages(source) if source.key == "projects" else ()


def one(engine, sql, **params):
    return engine.run(sql, params).rows[0][0]


def column(engine, sql, **params):
    return {str(row[0]) for row in engine.run(sql, params).rows}


@pytest.fixture(scope="module")
def nights(tmp_path_factory):
    with two_nights(tmp_path_factory.mktemp("delta") / "nightly.duckdb") as found:
        yield found


@contextmanager
def two_nights(path: Path):
    """Night one, the day's decisions and the draft, then night two, on one database at path. It gives the
    database and what each step left, read between the steps. tests/passage_rows.py hashes the rows it leaves.

    The plan reader reads every plan version here (ingestion.plan_versions = "all"), as before ticket 108: the plan
    the second night finds, of August 17, 2026, is older than the October 9, 2026 demo plan, so the nightly job's
    default, the newest plan only, would list it as superseded."""
    every = plans.with_plan_versions(load_thresholds(), plans.EVERY_VERSION)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(plans, "load_thresholds", lambda: every)
        with _two_nights(path) as found:
            yield found


@contextmanager
def _two_nights(path: Path):
    manifest = fmt.load_manifest()
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
        nightly.run_locally(engine, run_id="night-1", fetch=projects_only, clock=clock(NIGHT_ONE),
                            readers_for=lambda _: readers.recorded(
                                manifest, documents=TheNightBefore(RecordedDocuments(manifest), {ICR, PLAN})))
        before = {
            "texts": column(engine, "SELECT document_id FROM strata.bronze.document_texts"),
            "failed": column(engine, "SELECT document_id FROM strata.ops.parse_failures"),
            "items": column(engine, "SELECT proposal_id FROM strata.ops.lesson_review_items WHERE kind = 'new'"),
        }

    # By day: IEG's lesson added at version 1, a draft citing it, and a re-check that changes its wording.
    decide(path, IEG_LESSON, DAY)
    with DuckDBEngine.open(path) as engine:
        lesson_id = one(engine, "SELECT lesson_id FROM strata.ops.lesson_versions")
        content = {"subject": {}, "evidence": {}, "checks": None, "removed": [], "disagreements": [], "notes": [
            {"key": "KE-NWWDA-541055-CW-RFB", "state": "written", "sentences": [
                {"text": "Base the estimate on current market rates.",
                 "evidence_ids": [f"strata.ops.lesson_versions:{lesson_id}/v1"]}]}]}
        DraftStore(lambda: Unclosed(engine)).create(NewDraft(
            "draft-cites-v1", "review_notes", "team:nwwda", "id-author", "An author", None, "P156634", "40132287",
            content, dt.datetime.combine(DAY, dt.time(16), dt.UTC)))
        review = review_on(DAY, 17)
        item = review.recheck(engine, WANJIRU, lesson_id, "The 2025 Regulations changed how estimates are made.",
                              writer=engine)["item_id"]
        change = {"statement": "Base works estimates on current market rates, checked against recent awards."}
        review.act(engine, ASHA, item, "recommend", {"expected_stage": "recommendation", "outcome": "change",
                                                     "reason": "Say where the rates come from.", "change": change},
                   writer=engine)
        review_on(DAY, 18).act(engine, OMAR, item, "decide", {"expected_stage": "decision", "outcome": "change",
                                                              "reason": "Clearer.", "change": change}, writer=engine)
        drafts = (engine.run("SELECT * FROM strata.ops.drafts").rows,
                  engine.run("SELECT * FROM strata.ops.draft_states").rows)

        nightly.run_locally(engine, run_id="night-2", fetch=projects_only, clock=clock(NIGHT_TWO),
                            readers_for=lambda _: readers.recorded(manifest))
        yield engine, before, lesson_id, drafts


def test_the_next_night_runs_every_task_in_order(nights):
    engine, *_ = nights

    rows = engine.run("SELECT task_key, status FROM strata.ops.pipeline_runs WHERE run_id = 'night-2' "
                      "ORDER BY started_at").rows
    assert list(rows) == [(task, "succeeded") for task in PLAN_ORDER]


def test_only_the_new_documents_are_fetched_parsed_and_embedded(nights):
    engine, before, *_ = nights
    night_two = NIGHT_TWO.replace(tzinfo=None)

    assert column(engine, "SELECT document_id FROM strata.bronze.document_texts") - before["texts"] == {ICR, PLAN}
    # The layout parser read the new plan version's table page and no page of a document it had read before.
    assert column(engine, "SELECT document_id FROM strata.bronze.layout_pages WHERE run_id = 'night-2'") == {PLAN}
    # It also tried the ICR's pages that the fixture has no recorded layout for; a page that failed on the night
    # before is tried again the next day, as the daily page cap allows (strata.lakehouse.plans, parse_pages).
    tried = column(engine, "SELECT document_id FROM strata.ops.parse_failures WHERE run_id = 'night-2'")
    assert ICR in tried and tried - {ICR} <= before["failed"]
    embedded = column(engine, "SELECT DISTINCT p.document_id FROM strata.silver.passage_embeddings AS e "
                              "JOIN strata.silver.passages AS p ON p.text_hash = e.text_hash "
                              "WHERE e.embedded_at >= :night", night=night_two)
    screened = column(engine, "SELECT DISTINCT p.document_id FROM strata.silver.passage_shields AS s "
                              "JOIN strata.silver.passages AS p ON p.text_hash = s.text_hash "
                              "WHERE s.scanned_at >= :night", night=night_two)
    assert embedded == screened == {ICR}
    assert one(engine, "SELECT count(*) FROM strata.gold.passage WHERE passage_id = :id", id=f"{ICR}/v1/54") == 1


def test_the_new_icr_s_lessons_are_proposed_and_wait_for_review(nights):
    engine, before, *_ = nights

    queued = column(engine, "SELECT proposal_id FROM strata.ops.lesson_review_items WHERE kind = 'new'")
    assert before["items"] == {f"{IEG_LESSON}#1"}
    assert queued - before["items"] == {f"{ICR}/v1/54#1", f"{ICR}/v1/55#1"}


def test_the_data_readiness_measures_count_the_new_documents(nights):
    engine, *_ = nights

    def measure(run_id, subject, name):
        return engine.run("SELECT count, denominator FROM strata.ops.data_readiness WHERE run_id = :run_id "
                          "AND subject = :subject AND measure = :measure",
                          {"run_id": run_id, "subject": subject, "measure": name}).rows[0]

    # data/fixture/README.md: 11 Procurement Plan versions of P156634; 17 reports of P130164 (tests/test_passages.py).
    assert measure("night-1", "P156634", "plan_versions_read")[0] == 10
    assert measure("night-2", "P156634", "plan_versions_read")[0] == 11
    assert measure("night-1", "P130164", "documents_read")[0] == 16
    assert measure("night-2", "P130164", "documents_read")[0] == 17


def test_the_draft_citing_the_changed_lesson_is_marked_and_its_content_is_unchanged(nights):
    engine, _, lesson_id, drafts = nights

    notices = engine.run("SELECT draft_id, row_key, lesson_id, cited_version, current_version, tier, holds_export, "
                         "run_id FROM strata.ops.lesson_version_notices").rows
    assert list(notices) == [("draft-cites-v1", "KE-NWWDA-541055-CW-RFB", lesson_id, 1, 2, "narrowed", False,
                              "night-2")]
    assert (engine.run("SELECT * FROM strata.ops.drafts").rows,
            engine.run("SELECT * FROM strata.ops.draft_states").rows) == drafts


def test_the_nightly_task_writes_the_same_document_rows_as_before_the_reader_wrote_each_document_on_its_own(nights):
    """Ticket 72: the passage reader writes each document's passages as soon as it has read that document, and the
    nightly task's parse_and_embed and ops/documents/run_live.py share that writer. Over these two nights it gives
    the same rows, table by table, as the reader that wrote every passage at the end (tests/passage_rows.py)."""
    from passage_rows import digest, golden

    engine, *_ = nights

    assert digest(engine) == golden()["nightly"]
