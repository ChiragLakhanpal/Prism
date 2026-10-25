"""The labeled set retrieval is measured on (ticket 32; the spec's "Evaluation").

Four query sets, each built again by the weekly retrieval run into strata.ops.retrieval_labels, with each
set's size in strata.ops.retrieval_label_builds:

- icr_review_citations, silver labels. Each "ICR para N" citation in an ICR Review is a query: the sentence
  that cites the paragraph, with the one before it when that one cites nothing, and without the citation
  itself. The paragraphs it names are the passages that answer it. A re-issue under the same report number
  cites the same paragraphs, so a query is kept once, dated by the first version.
- pad_lessons, silver labels. Each PAD's section headed "Lessons Learned and Reflected in the Project Design"
  answers the query "lessons learned from earlier projects reflected in the project design" about its
  project. The heading in the table of contents, with its dot leaders, is not the section.
- notice_queries: the queries written from award notices, labeled by both query judges once they have both
  finished (strata.knowledge.retrieval.judging).
- bilingual_en_fr and bilingual_fr_en: English queries whose answers are in a French completion report, and French
  queries whose answers are in an English one (evals/bilingual_queries.toml; ticket 42), so retrieval across
  languages is measured like any other set.
- feedback: the passages passage reviewers ranked lower from passage reports, or that people agreed on at
  scale (strata.knowledge.retrieval.reports). Only these train anything, and evaluation_set() refuses them,
  so an evaluation set never takes live feedback.

A query's date is the first day it could be asked: retrieval for it uses only documents public before it. An
ICR Review's citation is dated the day the review became public. A PAD's lessons query is dated the day after
the PAD became public, the first day such a search can find it.
"""

from __future__ import annotations

import datetime as dt
import re
import tomllib
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from pathlib import Path

from strata.lakehouse.engine import Engine

# The bilingual query set (ticket 42): English queries over a French report and French queries over an English one.
BILINGUAL_SETS = ("bilingual_en_fr", "bilingual_fr_en")
EVALUATION_SETS = ("icr_review_citations", "pad_lessons", "notice_queries", *BILINGUAL_SETS)
FEEDBACK_SET = "feedback"
EVALUATION_ORIGINS = frozenset({"icr_review_citation", "pad_lessons", "judged", "bilingual_labeled"})
BILINGUAL_FILE = Path(__file__).resolve().parents[4] / "evals" / "bilingual_queries.toml"
FEEDBACK_ORIGINS = frozenset({"feedback_reviewed", "feedback_agreement"})
REVIEW_TYPE = "Implementation Completion Report Review"
ICR_TYPE = "Implementation Completion and Results Report"
PAD_TYPE = "Project Appraisal Document"
PAD_QUERY = "lessons learned from earlier projects reflected in the project design"

LABEL_COLUMNS = ("build_id", "query_set", "query_id", "query_text", "query_date", "project_id", "passage_id",
                 "grade", "origin", "weight", "built_at", "public_from")
BUILD_COLUMNS = ("build_id", "query_set", "queries", "labels", "documents", "built_at", "public_from")
LABELS_TABLE, BUILDS_TABLE = "strata.ops.retrieval_labels", "strata.ops.retrieval_label_builds"

# "(ICR para 54)", "(ICR para 11 and 43)", "(ICR para 18 and Restructuring Paper para 8c)": the ICR's
# paragraphs a citation names, and nothing of another document's.
CITATION = re.compile(r"\(ICR para (\d+)((?:\s*(?:,|and)\s*\d+)*)[^)]*\)")
SENTENCE_END = re.compile(r"(?<=[.?!])\s+(?=[A-Z(\"“])")
LESSONS_HEADING = re.compile(r"^\s*[A-Z]\.\s+Lessons\s+Learned\s+and\s+Reflected\s+in\s+the\s+Project\s+Design\s*$",
                             re.IGNORECASE | re.MULTILINE)
NUMBERED = re.compile(r"^\s*(\d+)\.\s+\S")
HEADING = re.compile(r"^\s*(?:[IVX]+|[A-Z])\.\s+[A-Za-z]")


class LiveFeedbackError(ValueError):
    """An evaluation set was asked to take a label that came from live feedback (the spec's "Evaluation":
    evaluation sets never take live feedback)."""


@dataclass(frozen=True)
class Label:
    query_set: str
    query_id: str
    query_text: str
    query_date: dt.date
    project_id: str | None
    passage_id: str
    grade: int
    origin: str
    weight: float = 1.0


@dataclass(frozen=True)
class Query:
    """One query of an evaluation set, with the passages labeled for it and their grades."""

    query_set: str
    query_id: str
    text: str
    date: dt.date
    project_id: str | None
    relevant: dict[str, int] = field(default_factory=dict)


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.knowledge.retrieval") / "sql" / f"{name}.sql").read_text()


def rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def utc_now() -> dt.datetime:
    """Now, in UTC: the clock the retrieval loop's writes take unless a test gives its own."""
    return dt.datetime.now(dt.UTC)


def new_id(prefix: str) -> str:
    """A new id for a report, a decision or a grade, from its prefix, such as "rep-3f9c0a1b2d4e"."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def as_date(value) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


# ── The ICR Reviews' citations ───────────────────────────────────────────

def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _uncited(sentence: str) -> str:
    return _flat(CITATION.sub("", sentence)).replace(" .", ".").strip()


def citing_query(text: str, at: int) -> str:
    """The query a citation at this place makes: the sentence that holds it and the sentence before it, each
    without its citation, back to two sentences or to a sentence that cites a paragraph of its own."""
    sentences, start, found = SENTENCE_END.split(text), 0, 0
    for index, sentence in enumerate(sentences):
        if start <= at < start + len(sentence) + 1:
            found = index
            break
        start += len(sentence) + 1
    kept: list[str] = []
    for index in range(found, -1, -1):
        sentence = sentences[index]
        if index != found and CITATION.search(sentence):
            break
        words = _uncited(sentence)
        if words:
            kept.insert(0, words)
        if len(kept) == 2:
            break
    return " ".join(kept)


def icr_review_citations(engine: Engine) -> tuple[list[Label], int]:
    """The silver labels from every ICR Review's "ICR para N" citations, and how many reports gave them."""
    seen: set[tuple] = set()
    queries: list[tuple[str, str, dt.date, str, list[int]]] = []
    for passage in rows(engine, "citing_passages", review_type=REVIEW_TYPE, marker="%ICR para%"):
        text = _flat(passage["text"])
        for match in CITATION.finditer(text):
            paragraphs = [int(match.group(1))] + [int(n) for n in re.findall(r"\d+", match.group(2))]
            key = (passage["report_number"] or passage["document_id"], tuple(paragraphs))
            if key in seen:
                continue
            seen.add(key)
            query_id = f"icrr:{key[0]}:{'+'.join(str(n) for n in paragraphs)}"
            queries.append((query_id, citing_query(text, match.start()), as_date(passage["public_from"]),
                            passage["project_id"], paragraphs))
    labels, reports = [], set()
    for query_id, text, date, project_id, paragraphs in queries:
        held = rows(engine, "numbered_paragraphs", project_id=project_id, document_type=ICR_TYPE, before=date)
        for paragraph in paragraphs:
            for found in (row for row in held if row["paragraph"] == str(paragraph)):
                labels.append(Label("icr_review_citations", query_id, text, date, project_id, found["passage_id"], 2,
                                    "icr_review_citation"))
                reports.add(query_id.split(":")[1])
    return labels, len(reports)


# ── The PADs' lessons sections ───────────────────────────────────────────

def lessons_paragraphs(text: str) -> list[int]:
    """The numbered paragraphs of a PAD's "Lessons Learned and Reflected in the Project Design" section, from
    its heading over the section (a line that is the heading alone, never the contents' line with its dot
    leaders) to the next heading."""
    for heading in LESSONS_HEADING.finditer(text):
        numbers: list[int] = []
        for line in text[heading.end():].splitlines()[1:]:
            if HEADING.match(line) and not NUMBERED.match(line):
                break
            numbered = NUMBERED.match(line)
            if numbered:
                numbers.append(int(numbered.group(1)))
        if numbers:
            return numbers
    return []


def pad_lessons(engine: Engine) -> tuple[list[Label], int]:
    """The silver labels from every PAD's lessons section, and how many PADs gave them."""
    labels, pads = [], set()
    for pad in rows(engine, "pad_texts", pad_type=PAD_TYPE):
        numbers = {str(n) for n in lessons_paragraphs(pad["text"])}
        if not numbers:
            continue
        date = as_date(pad["public_from"]) + dt.timedelta(days=1)
        query_id = f"pad:{pad['project_id']}:{pad['document_id']}"
        for found in rows(engine, "numbered_paragraphs", project_id=pad["project_id"], document_type=PAD_TYPE,
                          before=date):
            if found["document_id"] == pad["document_id"] and found["paragraph"] in numbers:
                labels.append(Label("pad_lessons", query_id, PAD_QUERY, date, pad["project_id"], found["passage_id"],
                                    2, "pad_lessons"))
                pads.add(pad["document_id"])
    return labels, len(pads)


# ── The bilingual query set (ticket 42) ──────────────────────────────────

def bilingual(engine: Engine, path: Path = BILINGUAL_FILE) -> dict[str, tuple[list[Label], int]]:
    """The bilingual query set's labels, by query set, each with how many documents its labels come from. A labeled
    passage the documents do not hold before its query's date is left out, as the other silver labels are."""
    queries = tomllib.loads(path.read_text())["query"]
    sets: dict[str, tuple[list[Label], set]] = {name: ([], set()) for name in BILINGUAL_SETS}
    for query in queries:
        if query["set"] not in sets:
            raise ValueError(f"{path.name}: query {query['id']} names the set {query['set']}, which is not one of "
                             f"{', '.join(BILINGUAL_SETS)}.")
        found = {row["passage_id"]: row["document_id"] for row in rows(
            engine, "passages_before", ids=",".join(query["relevant"]), before=query["date"])}
        found_labels, documents = sets[query["set"]]
        for passage_id, grade in query["relevant"].items():
            if passage_id in found:
                found_labels.append(Label(query["set"], query["id"], query["text"], query["date"], query["project_id"],
                                          passage_id, int(grade), "bilingual_labeled"))
                documents.add(found[passage_id])
    return {name: (found_labels, len(documents)) for name, (found_labels, documents) in sets.items()}


# ── Evaluation sets ──────────────────────────────────────────────────────

def evaluation_set(labels: Iterable[Label]) -> list[Query]:
    """An evaluation set's queries from its labels. A label from live feedback is refused: evaluation sets
    never take live feedback."""
    queries: dict[str, Query] = {}
    for label in labels:
        if label.origin in FEEDBACK_ORIGINS or label.query_set == FEEDBACK_SET or label.origin not in EVALUATION_ORIGINS:
            raise LiveFeedbackError(
                f"The label for {label.passage_id} on query {label.query_id} came from {label.origin}, and an "
                "evaluation set takes only labels read from documents or given by two query judges, never live "
                "feedback.")
        query = queries.setdefault(label.query_id, Query(label.query_set, label.query_id, label.query_text,
                                                         label.query_date, label.project_id))
        if label.grade > 0:
            query.relevant[label.passage_id] = max(label.grade, query.relevant.get(label.passage_id, 0))
    return list(queries.values())


def latest(engine: Engine) -> list[Label]:
    """Every label of the labeled set's latest build."""
    return [Label(row["query_set"], row["query_id"], row["query_text"], as_date(row["query_date"]), row["project_id"],
                  row["passage_id"], int(row["grade"]), row["origin"], float(row["weight"]))
            for row in rows(engine, "latest_labels")]


# ── The build ────────────────────────────────────────────────────────────

def build(engine: Engine, writer: Engine, built_at: dt.datetime, extra: dict[str, tuple[list[Label], int | None]]
          | None = None) -> dict[str, tuple[int, int, int | None]]:
    """Build the labeled set again: read the silver labels from the documents engine holds, add the other
    sets given (extra, by query set: their labels and how many documents they came from), and append them
    with each set's size under a new build id through writer. Returns each set's queries, labels and
    documents."""
    build_id = f"labels-{built_at.astimezone(dt.UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
    citations, reviews = icr_review_citations(engine)
    lessons, pads = pad_lessons(engine)
    sets = {"icr_review_citations": (citations, reviews), "pad_lessons": (lessons, pads), **bilingual(engine),
            **(extra or {})}
    day = built_at.astimezone(dt.UTC).date()
    sizes, label_rows, build_rows = {}, [], []
    for name, (labels, documents) in sets.items():
        queries = len({label.query_id for label in labels})
        sizes[name] = (queries, len(labels), documents)
        build_rows.append((build_id, name, queries, len(labels), documents, built_at, day))
        for label in labels:
            public = label.query_date if label.origin in {"icr_review_citation", "pad_lessons", "bilingual_labeled"} \
                else max(label.query_date, day)
            label_rows.append((build_id, name, label.query_id, label.query_text, label.query_date, label.project_id,
                               label.passage_id, label.grade, label.origin, label.weight, built_at, public))
    writer.insert_rows(LABELS_TABLE, LABEL_COLUMNS, label_rows)
    writer.insert_rows(BUILDS_TABLE, BUILD_COLUMNS, build_rows)
    return sizes
