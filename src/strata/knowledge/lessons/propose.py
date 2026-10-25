"""The nightly job's propose_lessons task: lessons proposed from evaluation reports, kept only when their
quotes are word for word on the pages they cite (ticket 29; docs/PLAN.md section 5, "Lessons").

A run:

1. Sends each current ICR, ICR Review and PPAR the passage reader holds (strata.silver.documents and
   strata.silver.passages) to the batch model once, with the extractor's instructions (extractor.md, with
   the lesson lists of config/lessons.toml filled in) and the document's passages as data. A document
   already sent is not sent again, unless its request failed. Each request and answer is kept in
   strata.bronze.lesson_batches, and a batch still running is asked again on the next run.
2. Rebuilds, for each project with an answer, the proposals (strata.silver.lesson_proposals), the
   restatements (strata.silver.lesson_restatements) and the evidence (strata.silver.lesson_evidence). A
   proposal passes only when the passage it cites exists, its quote is word for word on the cited PDF page
   as Strata read it (the published text's page, as Route A read it, or the layout parser's) and in that
   passage, and its tags are on the closed lists. The check uses the
   verifier's own quote matcher (strata.agent.verifier.find_quote), which ignores only whitespace,
   line-end hyphenation and whether a quote mark is curly or straight. It rejects and never repairs: a
   failing proposal is kept as the model wrote it, with its reason. An ICR Review's or a PPAR's
   restatement of an ICR paragraph attaches to the proposals from that paragraph, once for each report
   number. Each proposal carries the edition of the procurement rules its project's PAD names.
3. Queues each passing proposal once (strata.ops.lesson_review_items), for its project's region, with its
   business-day clock starting that day.
4. Writes the lessons verified measure to strata.ops.data_readiness for each project: the proposals that
   passed, out of every proposal.

The review-proposed-lessons workflow then writes each open item's summary (strata.knowledge.lessons.writer).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
from collections.abc import Callable
from functools import cache
from importlib import resources
from pathlib import Path

from strata.agent.verifier import find_quote
from strata.config import Editions, LessonLists, load_editions, load_lesson_lists, load_thresholds
from strata.knowledge.lessons.batch import Batch, RecordedBatch
from strata.lakehouse import rewrites
from strata.lakehouse.engine import Engine
from strata.reader.passages import split_pages
from strata.reader.templates import ICR, ICR_REVIEW, PPAR

log = logging.getLogger("strata.lessons")
SOURCE = "documents"  # the source registry's key the measures belong to
TYPES = (ICR.document_type, ICR_REVIEW.document_type, PPAR.document_type)
IEG_TYPES = (ICR_REVIEW.document_type, PPAR.document_type)  # IEG writes these
PASSED = "passed"
BATCH_COLUMNS = ("custom_id", "document_id", "version", "project_id", "batch_id", "model", "status", "request",
                 "output", "error", "recorded_at", "public_from")
PROPOSAL_COLUMNS = ("proposal_id", "document_id", "version", "project_id", "document_type", "report_number",
                    "passage_id", "paragraph", "cited_page", "statement", "quote", "risk_factors", "stage", "kind",
                    "edition_key", "quote_check", "model", "batch_id", "proposed_on", "public_from")
RESTATEMENT_COLUMNS = ("document_id", "version", "project_id", "document_type", "report_number", "restates",
                       "passage_id", "paragraph", "cited_page", "quote", "quote_check", "batch_id", "found_on",
                       "public_from")
EVIDENCE_COLUMNS = ("proposal_id", "role", "passage_id", "document_id", "version", "project_id", "document_type",
                    "report_number", "document_date", "paragraph", "cited_page", "quote", "restated_by_ieg",
                    "public_from")
ITEM_COLUMNS = ("item_id", "kind", "proposal_id", "project_id", "region", "origin", "entered_on", "created_at",
                "public_from")
MEASURE_COLUMNS = ("run_id", "source", "subject", "measure", "kind", "count", "denominator", "as_of", "detail",
                   "measured_at", "public_from")
LESSON_TABLES = ("lesson_proposals", "lesson_restatements", "lesson_evidence")


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.knowledge.lessons") / "sql" / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


# Values arrive typed from DuckDB and as text from the SQL warehouse, so each is read once here.

def _int(value) -> int | None:
    return None if value is None or value == "" else int(value)


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def custom_id(document_id: str, version) -> str:
    """A request's id in its batch: the document and its version, 31525018/v1."""
    return f"{document_id}/v{_int(version)}"


def item_id(kind: str, key: str) -> str:
    """A queue item's id, the same on every run for the same proposal or act: new-3f2a9c1d0b."""
    return f"{kind}-{hashlib.sha256(key.encode()).hexdigest()[:10]}"


# ── The request ──────────────────────────────────────────────────────────

def instructions(lists: LessonLists | None = None) -> str:
    """The extractor's instructions, with the closed lists and the statement's length filled in."""
    lists = lists or load_lesson_lists()
    listed = "\n".join(f"  - {title}: " + "; ".join(f"{item.key} ({item.label})" for item in getattr(lists, name))
                       for name, title in (("risk_factors", "Risk factors"), ("stages", "Stages"),
                                           ("kinds", "Kinds")))
    text = (resources.files("strata.knowledge.lessons") / "extractor.md").read_text()
    limit = str(load_thresholds().value("lesson_review.statement_max_chars"))
    return text.replace("{lists}", listed).replace("{lesson_review.statement_max_chars}", limit)


def request(document: dict, passages: list[dict], model: str, lists: LessonLists | None = None) -> dict:
    """One line of a batch's input file: the instructions, then the document and its passages as data."""
    data = {"document": {"document_id": str(document["document_id"]), "version": _int(document["version"]),
                         "document_type": document["document_type"], "project_id": document["project_id"]},
            "passages": [{"passage_id": passage["passage_id"], "pdf_page": _int(passage["pdf_page"]),
                          "last_pdf_page": _int(passage["last_pdf_page"]), "text": passage["text"]}
                         for passage in passages]}
    return {"custom_id": custom_id(document["document_id"], document["version"]), "method": "POST",
            "url": "/chat/completions",
            "body": {"model": model, "response_format": {"type": "json_object"},
                     "messages": [{"role": "system", "content": instructions(lists)},
                                  {"role": "user", "content": json.dumps(data, ensure_ascii=False)}]}}


# ── The quote check ──────────────────────────────────────────────────────

class Pages:
    """A document's PDF pages as Strata read them: the published text divided on its form feeds, as Route A
    read it, or, for a document whose published text does not divide into its pages, each page the layout
    parser read, else the PDF's text layer."""

    def __init__(self, engine: Engine, document_id: str):
        self.engine, self.document_id = engine, document_id
        found = _rows(engine, "published_text", document_id=document_id)
        paged = found and str(found[0]["text_paged"]).lower() == "true"
        self.published = split_pages(found[0]["text"], _int(found[0]["pdf_pages"]) or 0) if paged else None

    def text(self, pdf_page: int | None) -> str | None:
        if not pdf_page or pdf_page < 1:
            return None
        if self.published is not None:
            return self.published[pdf_page - 1] if pdf_page <= len(self.published) else None
        found = _rows(self.engine, "page_text", document_id=self.document_id, pdf_page=pdf_page)
        return found[0]["text"] if found else None


def check_quote(pages: Pages, passage: dict | None, page, quote) -> str:
    """passed, or why not: the passage the quote cites must exist, and the quote must be word for word on
    the cited PDF page and inside that passage. Nothing is changed to make it fit."""
    if passage is None:
        return "unknown_passage"
    text = pages.text(_int(page))
    if not isinstance(quote, str) or text is None or find_quote(quote, text) is None:
        return "quote_not_on_page"
    if find_quote(quote, passage["text"]) is None:
        return "quote_not_in_passage"
    return PASSED


def _on_lists(lesson: dict, lists: LessonLists) -> bool:
    factors = lesson.get("risk_factors")
    return (isinstance(factors, list) and bool(factors) and all(lists.risk_factor(key) for key in factors)
            and lists.stage(lesson.get("stage")) is not None and lists.kind(lesson.get("kind")) is not None)


def _answer(text: str | None) -> dict:
    """The model's JSON, or empty lists when it wrote something else."""
    try:
        answer = json.loads(text or "")
    except ValueError:
        return {"lessons": [], "restatements": []}
    return answer if isinstance(answer, dict) else {"lessons": [], "restatements": []}


# ── The run ──────────────────────────────────────────────────────────────

def _send(engine: Engine, batch: Batch, documents: list[dict], states: dict, now: dt.datetime,
          lists: LessonLists) -> int:
    """Each document not sent yet, or whose request failed, in one batch."""
    waiting = [document for document in documents
               if states.get(custom_id(document["document_id"], document["version"]), {}).get("status")
               in (None, "failed")]
    if not waiting:
        return 0
    requests = [request(document, _rows(engine, "passages_of", document_id=str(document["document_id"])),
                        batch.model, lists) for document in waiting]
    batch_id = batch.submit(requests)
    rows = [(line["custom_id"], str(document["document_id"]), _int(document["version"]), document["project_id"],
             batch_id, batch.model, "submitted", json.dumps(line, ensure_ascii=False), None, None, now, now.date())
            for document, line in zip(waiting, requests, strict=True)]
    return engine.insert_rows("strata.bronze.lesson_batches", BATCH_COLUMNS, rows)


def _collect(engine: Engine, batch: Batch, states: dict, now: dt.datetime) -> int:
    """The answers of each batch still running, kept as they came back."""
    running: dict[str, list[dict]] = {}
    for state in states.values():
        if state["status"] == "submitted":
            running.setdefault(state["batch_id"], []).append(state)
    rows = []
    for batch_id, waiting in running.items():
        answers = batch.results(batch_id, [state["custom_id"] for state in waiting])
        if answers is None:
            continue
        for state, answer in zip(waiting, answers, strict=True):
            rows.append((state["custom_id"], str(state["document_id"]), _int(state["version"]), state["project_id"],
                         batch_id, state["model"], "completed" if answer.error is None else "failed", None,
                         answer.text, answer.error, now, now.date()))
    return engine.insert_rows("strata.bronze.lesson_batches", BATCH_COLUMNS, rows) if rows else 0


def _document(engine: Engine, document_id: str) -> dict:
    result = engine.run("SELECT document_type, report_number, document_date, public_from FROM strata.silver.documents "
                        "WHERE document_id = :document_id", {"document_id": document_id})
    return dict(zip(result.columns, result.rows[0], strict=True))


def rebuild(engine: Engine, project_id: str, answered: list[dict], lists: LessonLists, editions: Editions) -> int:
    """A project's proposals, restatements and evidence, from its answered requests, written again only when they
    differ from the ones held (strata.lakehouse.rewrites), so a night with nothing new changes no row. Returns the
    proposals it added or removed."""
    edition = next((found.key for found in (editions.named_in(row["text"])
                                            for row in _rows(engine, "pad_passages", project_id=project_id))
                    if found), None)
    proposals, restatements = [], []
    for state in answered:
        document_id, version = str(state["document_id"]), _int(state["version"])
        document = _document(engine, document_id)
        passages = {row["passage_id"]: row for row in _rows(engine, "passages_of", document_id=document_id)}
        pages = Pages(engine, document_id)
        answer, day = _answer(state["output"]), _date(state["recorded_at"])
        seen: dict[str, int] = {}
        for lesson in answer.get("lessons") or []:
            if not isinstance(lesson, dict):
                continue
            passage_id = str(lesson.get("passage_id") or "")
            seen[passage_id] = seen.get(passage_id, 0) + 1
            passage = passages.get(passage_id)
            # A passage id is unique across documents; a missing or unknown one is not, so it keeps its document.
            key = passage_id if passage else f"{custom_id(document_id, version)}/unknown"
            check = check_quote(pages, passage, lesson.get("page"), lesson.get("quote"))
            if check == PASSED and not _on_lists(lesson, lists):
                check = "not_in_lists"
            factors = lesson.get("risk_factors") if isinstance(lesson.get("risk_factors"), list) else []
            proposals.append({
                "proposal_id": f"{key}#{seen[passage_id]}", "document_id": document_id, "version": version,
                "project_id": project_id, "document_type": document["document_type"],
                "report_number": document["report_number"], "passage_id": passage_id,
                "paragraph": passage["paragraph"] if passage else None, "cited_page": _int(lesson.get("page")),
                "statement": str(lesson.get("statement") or ""), "quote": str(lesson.get("quote") or ""),
                "risk_factors": json.dumps(factors), "stage": lesson.get("stage"), "kind": lesson.get("kind"),
                "edition_key": edition, "quote_check": check, "model": state["model"],
                "batch_id": state["batch_id"], "proposed_on": day, "public_from": day})
        if document["document_type"] not in IEG_TYPES:
            continue
        for found in answer.get("restatements") or []:
            if not isinstance(found, dict) or found.get("icr_paragraph") is None:
                continue
            passage = passages.get(str(found.get("passage_id") or ""))
            restatements.append({
                "document_id": document_id, "version": version, "project_id": project_id,
                "document_type": document["document_type"], "report_number": document["report_number"],
                "restates": str(found["icr_paragraph"]), "passage_id": str(found.get("passage_id") or ""),
                "paragraph": passage["paragraph"] if passage else None, "cited_page": _int(found.get("page")),
                "quote": str(found.get("quote") or ""),
                "quote_check": check_quote(pages, passage, found.get("page"), found.get("quote")),
                "batch_id": state["batch_id"], "found_on": day, "public_from": _date(document["public_from"]),
                "document_date": _date(document["document_date"])})
    new = {"lesson_proposals": (PROPOSAL_COLUMNS, [tuple(row[c] for c in PROPOSAL_COLUMNS) for row in proposals]),
           "lesson_restatements": (RESTATEMENT_COLUMNS,
                                   [tuple(row[c] for c in RESTATEMENT_COLUMNS) for row in restatements]),
           "lesson_evidence": (EVIDENCE_COLUMNS, [tuple(row[c] for c in EVIDENCE_COLUMNS)
                                                 for row in _evidence(engine, proposals, restatements)])}
    differs = {table: rewrites.differing(
        rewrites.comparable(rewrites.held(engine, f"strata.silver.{table}", columns, "project_id = :project_id",
                                          {"project_id": project_id})),
        rewrites.comparable(rows)) for table, (columns, rows) in new.items()}
    if not any(differs.values()):
        return 0
    for table in LESSON_TABLES:
        engine.run(f"DELETE FROM strata.silver.{table} WHERE project_id = :project_id",  # sql-lint: names only
                   {"project_id": project_id})
    for table, (columns, rows) in new.items():
        engine.insert_rows(f"strata.silver.{table}", columns, rows)
    return differs["lesson_proposals"]


def _evidence(engine: Engine, proposals: list[dict], restatements: list[dict]) -> list[dict]:
    """Each passing proposal's own quote, then each passing restatement of its ICR paragraph, one for each
    report number, from the newest version."""
    newest: dict[tuple[str, str], dict] = {}
    for found in restatements:
        if found["quote_check"] == PASSED:
            key = (found["restates"], found["report_number"] or found["document_id"])
            if key not in newest or found["version"] > newest[key]["version"]:
                newest[key] = found
    rows = []
    for proposal in proposals:
        if proposal["quote_check"] != PASSED:
            continue
        document = _document(engine, proposal["document_id"])
        rows.append({**{column: proposal[column] for column in ("proposal_id", "passage_id", "document_id", "version",
                                                                 "project_id", "document_type", "report_number",
                                                                 "paragraph", "cited_page", "quote")},
                     "role": "source", "document_date": _date(document["document_date"]),
                     "restated_by_ieg": proposal["document_type"] in IEG_TYPES,
                     "public_from": _date(document["public_from"])})
        if proposal["document_type"] != ICR.document_type:
            continue
        for (restates, _), found in sorted(newest.items()):
            if restates == proposal["paragraph"]:
                rows.append({**{column: found[column] for column in ("passage_id", "document_id", "version",
                                                                     "project_id", "document_type", "report_number",
                                                                     "document_date", "paragraph", "cited_page",
                                                                     "quote", "public_from")},
                             "proposal_id": proposal["proposal_id"], "role": "restatement", "restated_by_ieg": True})
    return rows


def _queue(engine: Engine, projects: list[str], now: dt.datetime) -> int:
    """Each passing proposal not queued yet, for its project's region."""
    queued = {row["proposal_id"] for row in _rows(engine, "queued_proposals")}
    rows = []
    for project_id in projects:
        for found in _rows(engine, "to_queue", project_id=project_id):
            if found["proposal_id"] in queued:
                continue
            if not found["region"]:
                log.warning("I could not queue %s, because project %s has no region.", found["proposal_id"], project_id)
                continue
            rows.append((item_id("new", found["proposal_id"]), "new", found["proposal_id"], project_id,
                         found["region"], "proposed", now.date(), now, now.date()))
    return engine.insert_rows("strata.ops.lesson_review_items", ITEM_COLUMNS, rows) if rows else 0


def _measure(engine: Engine, run_id: str, projects: list[str], now: dt.datetime) -> int:
    rows = []
    for project_id in projects:
        result = engine.run("SELECT count(*) AS proposed, count_if(quote_check = :passed) AS verified "
                            "FROM strata.silver.lesson_proposals WHERE project_id = :project_id",
                            {"project_id": project_id, "passed": PASSED})
        proposed, verified = (int(value) for value in result.rows[0])
        if proposed:
            rows.append((run_id, SOURCE, project_id, "lessons_verified", "verified", verified, proposed, None,
                         "This counts the lessons the batch model proposed whose quote I found word for word on the "
                         "page and in the passage they cite, out of every lesson it proposed.", now, now.date()))
    return engine.insert_rows("strata.ops.data_readiness", MEASURE_COLUMNS, rows) if rows else 0


def run(engine: Engine, batch: Batch, run_id: str, clock: Callable[[], dt.datetime],
        lists: LessonLists | None = None, editions: Editions | None = None) -> int:
    """One propose_lessons run. Returns the rows it changed."""
    lists, editions = lists or load_lesson_lists(), editions or load_editions()
    now = clock()
    documents = _rows(engine, "documents_to_read", types=",".join(TYPES))
    states = {row["custom_id"]: row for row in _rows(engine, "batch_states")}
    changed = _send(engine, batch, documents, states, now, lists)
    changed += _collect(engine, batch, {row["custom_id"]: row for row in _rows(engine, "batch_states")}, clock())
    answered: dict[str, list[dict]] = {}
    for state in _rows(engine, "batch_states"):
        if state["status"] == "completed":
            answered.setdefault(state["project_id"], []).append(state)
    projects = sorted(answered)
    for project_id in projects:
        changed += rebuild(engine, project_id, answered[project_id], lists, editions)
    changed += _queue(engine, projects, now)
    return changed + _measure(engine, run_id, projects, now)


RECORDED_BATCH = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "azure" / "lesson_batch.json"


def run_on_fixture(engine: Engine, run_id: str, clock: Callable[[], dt.datetime], path: Path = RECORDED_BATCH) -> int:
    """The task on the fixture database, with the batch model's recorded answers, then the review-proposed-lessons
    workflow with the lesson review writer's recorded answers."""
    from strata.knowledge.lessons import writer

    changed = run(engine, RecordedBatch(path), run_id, clock)
    most = int(load_thresholds().value("lesson_review.likely_repeats_max"))
    return changed + writer.run(engine, writer.recorded_agent_for(), clock, most)
