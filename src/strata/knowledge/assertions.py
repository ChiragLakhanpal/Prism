"""Assertions, disagreements and the evidence ladder (ticket 20; docs/PLAN.md section 5).

Ratings, dates and amounts from records and documents become dated assertions in
strata.gold.assertion. Each records its subject (a project, or a package by its STEP reference), its
attribute (config/evidence_ladder.toml, [attributes]), its value, the period it describes, when it was
made, its public date, its source document and passage, and its evidence tier. They come from:

- the ISRs' ratings, which ticket 18 read from each ISR's own ratings table (strata.silver.isr_ratings).
  Each ISR rates the period since the ISR before it, so the ratings of one series never overlap and form
  a trajectory, not a disagreement.
- the records of a package's signing: the awards datasets' contracts, Contract Award notices and each
  version of a Procurement Plan, each giving the signing date and, where it gives one, the signed amount
  in US dollars. The subject is the package, by its STEP reference.
- each version's plan row that says the package's contract is not signed yet: its Process Status before
  signing, which stands until the agency's next plan version replaces it (ticket 132). A record that dates the
  signing before then disagrees with it, and the plan check names that row as moved on since the plan.
- the IEG ratings dataset, which repeats IEG's ratings of a closed project, each for the whole project.
- the ICRs, ICR Reviews, PPARs and PADs, read by the batch model (strata.knowledge.batch). An assertion
  read from text is kept only when its quote is word for word in the passage it cites, on the page it
  cites; the rest go to strata.ops.assertion_rejections with their reason.

The nightly job's detect_disagreements task runs run() for every project Strata holds documents or records
for, and the fixture build runs it after the passage reader (gates/build_fixture.py). Every table it writes
is rebuilt for each project of the run. The run sends every project's reports to the batch model in one call,
so the live run waits for one batch. A request a finished batch did not answer, or a batch that can no longer
be read, is asked again (ask()).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import astuple, dataclass, fields
from decimal import Decimal
from importlib import resources

from strata.agent.verifier import find_quote  # ticket 13's word-for-word quote match, defined once
from strata.config import SIDES, Ladder, Thresholds, load_ladder, load_sources, load_thresholds
from strata.knowledge.batch import Answer, BatchError, BatchModel, BatchPending, RecordedBatch, Request
from strata.lakehouse import rewrites
from strata.lakehouse.engine import Engine
from strata.reader.passages import TABLE_SUMMARY
from strata.tools.check_plan import PENDING_STATUSES

PASSAGES = "strata.gold.passage"  # the table a passage's evidence id names, as search_passages returns it
ISR = "Implementation Status and Results Report"
ISR_READER = "isr_ratings"  # ticket 18's reader of each ISR's ratings table (src/strata/lakehouse/isr_ratings.py)
# The periods an assertion can describe.
REPORT_PERIOD, WHOLE_PROJECT, CONTRACT_SIGNING = "report_period", "whole_project", "contract_signing"
MID_TERM_REVIEW, APPRAISAL = "mid_term_review", "appraisal"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _sql(name: str) -> str:
    return (resources.files("strata.knowledge") / "sql" / "assertions" / name).read_text()


def _rows(engine: Engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _date(value) -> dt.date | None:
    """A date from DuckDB (a date or a timestamp) or from the warehouse (ISO text)."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _int(value) -> int | None:
    return None if value is None or value == "" else int(value)


# A run with more projects than this reads every project and keeps the ones it needs; a run with fewer, such as
# one project's, names them in the query.
NAMED_MAX = 200
PROJECT_DATES = """
SELECT project_id, approval_date, closing_date FROM strata.gold.project
WHERE (:every_project OR array_contains(split(:projects, ','), project_id))
"""


class ProjectRows:
    """Each family of rows the run's assertions come from, read with one query for all the run's projects and kept
    by project (ticket 43): the ISRs' ratings, the records of each package's signing, the IEG ratings, the projects'
    dates, the ISRs' key dates and the reports. On October 24, 2026 the run read each project with about seven
    queries of its own, which for the workspace's 15,933 projects was about eleven hours against the nightly job's
    150-minute stop; this way the queries are the same few whatever the number of projects."""

    def __init__(self, engine: Engine, projects: list[str], ladder: Ladder, contracts: tuple[str, ...] | None = None):
        self.projects = list(dict.fromkeys(projects))
        wanted = set(self.projects)
        every = len(wanted) > NAMED_MAX
        scope = {"every_project": every, "projects": "" if every else ",".join(self.projects) or "-"}

        def kept(sql: str, **params) -> dict[str, list[dict]]:
            found: dict[str, list[dict]] = {}
            for row in _rows(engine, sql, **scope, **params):
                if row["project_id"] in wanted:
                    found.setdefault(row["project_id"], []).append(row)
            return found

        types = [kind for tier in REPORT_TIERS if tier in ladder.tiers for kind in ladder.tiers[tier].document_types]
        self.isr = kept(_sql("isr_ratings.sql"))
        self.records = kept(_sql("records.sql"), contract_sources=",".join(contracts or contract_sources()),
                            award_notice=AWARD_NOTICE, contract_record=CONTRACT_RECORD,
                            award_notice_form=AWARD_NOTICE_FORM, notices_source="notices", plan_row=PLAN_ROW,
                            documents_source="documents", plan_type=PLAN_TYPE, signed_step=SIGNED_STEP)
        self.statuses = kept(_sql("plan_statuses.sql"), contract_sources=",".join(contracts or contract_sources()),
                             award_notice=AWARD_NOTICE, signed_step=SIGNED_STEP, pending=",".join(PENDING_STATUSES))
        self.ieg = kept(_sql("ieg_ratings.sql"))
        self.dates = kept(PROJECT_DATES)
        self.key_dates = kept(_sql("key_dates.sql"), document_type=ISR, label="Review Date")
        self.reports = kept(_sql("reports.sql"), document_types=",".join(types))


def _of(engine: Engine, rows: ProjectRows | None, project_id: str, ladder: Ladder) -> ProjectRows:
    """The rows of the run, or, for one project on its own, that project's."""
    return rows if rows is not None and project_id in rows.projects else ProjectRows(engine, [project_id], ladder)


@dataclass(frozen=True)
class Assertion:
    """One row of strata.gold.assertion (its table definition says what each column holds)."""

    assertion_id: str
    subject_kind: str
    subject_id: str
    project_id: str
    attribute: str
    attribute_kind: str
    field_name: str
    value: str
    value_form: str
    judgment: str | None
    period_event: str
    period_start: dt.date
    period_end: dt.date
    made_at: dt.date
    replaced_on: dt.date | None
    evidence_tier: str
    form: str
    source_key: str
    document_id: str
    document_type: str | None
    report_number: str | None
    version: int | None
    sequence: int | None
    passage_id: str
    evidence_id: str
    pdf_page: int | None
    quote: str | None
    read_by: str
    public_from: dt.date


ASSERTION_COLUMNS = tuple(f.name for f in fields(Assertion))


def assertion_id(evidence_id: str, subject_id: str, attribute: str) -> str:
    """A stable id: the evidence it rests on, then its subject and attribute."""
    return f"{evidence_id}#{subject_id}/{attribute}"


# ── The ISRs' ratings ────────────────────────────────────────────────────

def isr_assertions(engine: Engine, project_id: str, ladder: Ladder, rows: ProjectRows | None = None
                   ) -> list[Assertion]:
    """Each ISR's rating of each attribute the ladder knows, for the period since the ISR before it. The
    first ISR's period starts on the day the Board approved the project."""
    found: dict[tuple[str, str], dict] = {}
    for row in _of(engine, rows, project_id, ladder).isr.get(project_id, []):
        found.setdefault((row["rating_name"], str(row["document_id"])), row)  # the first passage that prints it
    made = []
    by_name: dict[str, list[dict]] = {}
    for (name, _), row in found.items():
        by_name.setdefault(name, []).append(row)
    for name, series in by_name.items():
        attribute = ladder.attribute_named(name)
        if attribute is None:
            continue
        series.sort(key=lambda row: (_date(row["isr_date"]), str(row["document_id"])))
        previous = None
        for row in series:
            day = _date(row["isr_date"])
            approved = _date(row["approval_date"])
            start = previous + dt.timedelta(days=1) if previous else approved if approved and approved < day else day
            previous = day
            rating = ladder.rating(attribute.key, row["current_rating"])
            if rating is None or not row["passage_id"]:
                continue  # no rating ("--"), or no passage to cite for it
            evidence = f"{PASSAGES}:{row['passage_id']}"
            made.append(Assertion(
                assertion_id=assertion_id(evidence, project_id, attribute.key), subject_kind="project",
                subject_id=project_id, project_id=project_id, attribute=attribute.key,
                attribute_kind=attribute.kind, field_name=name, value=rating, value_form="rating",
                judgment=ladder.side(attribute.key, rating), period_event=REPORT_PERIOD,
                period_start=start, period_end=day, made_at=day, replaced_on=_date(row["replaced_on"]),
                evidence_tier=ladder.tier_of(row["document_type"]) or "isr", form="rating_field",
                source_key="documents", document_id=str(row["document_id"]),
                document_type=row["document_type"], report_number=row["report_number"],
                version=_int(row["version"]), sequence=_int(row["sequence"]),
                passage_id=row["passage_id"], evidence_id=evidence, pdf_page=_int(row["pdf_page"]),
                quote=None, read_by=ISR_READER, public_from=_date(row["public_from"])))
    return made


# ── The records of a package's signing ───────────────────────────────────

AWARD_NOTICE, SIGNED_STEP, PLAN_TYPE = "Contract Award", "Signed Contract", "Procurement Plan"
CONTRACT_RECORD, AWARD_NOTICE_FORM, PLAN_ROW = "contract_record", "award_notice", "plan_row"
# A plan row's Process Status before signing (ticket 132): the plan's own field name, and the value form of an
# assertion that gives a state rather than a date or an amount.
PROCESS_STATUS, STATUS = "Process Status", "status"

# Each record's own name for the signing date and the signed amount, word for word: the awards datasets'
# field, the award notice's label, and the Procurement Plan's step and column. The awards datasets give an
# amount per supplier, so a contract's amount is gold.contract's column, which adds a joint venture's
# members' shares. Each is one of its attribute's names in config/evidence_ladder.toml.
RECORD_FIELDS = {
    CONTRACT_RECORD: {"signed_on": "contract_signing_date", "signed_amount_usd": "contract_amount_usd"},
    AWARD_NOTICE_FORM: {"signed_on": "Contract Signature Date"},
    PLAN_ROW: {"signed_on": "Signed Contract", "signed_amount_usd": "Actual Amount (US$)"},
}
# The table each record is a row of, which its evidence id names, as the tools return it.
RECORD_TABLES = {CONTRACT_RECORD: "strata.gold.contract", AWARD_NOTICE_FORM: "strata.gold.notice",
                 PLAN_ROW: "strata.silver.plan_rows"}


def contract_sources() -> tuple[str, ...]:
    """The datasets of signed contracts: the sources config/sources.toml marks assertion_form = contract_record."""
    return tuple(key for key, source in load_sources().items() if source.assertion_form == CONTRACT_RECORD)


def _record_key(row: dict) -> str:
    """The record's key in its table: the contract's or notice's id, or a plan row's version and reference,
    as check_plan's evidence id gives it."""
    if row["form"] == PLAN_ROW:
        return f"{row['document_id']}/{row['step_reference']}"
    return str(row["document_id"])


def record_assertions(engine: Engine, project_id: str, ladder: Ladder, rows: ProjectRows | None = None
                      ) -> list[Assertion]:
    """Each record's signing date and signed amount for each of the project's packages, about the signing,
    which each record dates for itself. A plan whose Actual Amount reads 0 gives no amount: the borrower has
    not filled it in, and a missing amount is never a difference."""
    made = []
    for row in _of(engine, rows, project_id, ladder).records.get(project_id, []):
        signed = _date(row["signed_on"])
        amount = None if row["amount_usd"] in (None, "") else Decimal(str(row["amount_usd"]))
        values = {"signed_on": signed.isoformat()}
        if amount and "signed_amount_usd" in RECORD_FIELDS[row["form"]]:
            values["signed_amount_usd"] = f"{amount:.2f}"
        key = _record_key(row)
        evidence = f"{RECORD_TABLES[row['form']]}:{key}"
        for attribute_key, value in values.items():
            attribute = ladder.attribute(attribute_key)
            made.append(Assertion(
                assertion_id=assertion_id(evidence, row["step_reference"], attribute.key),
                subject_kind="package", subject_id=row["step_reference"], project_id=project_id,
                attribute=attribute.key, attribute_kind=attribute.kind,
                field_name=RECORD_FIELDS[row["form"]][attribute.key], value=value,
                value_form=attribute.kind, judgment=None, period_event=CONTRACT_SIGNING,
                period_start=signed, period_end=signed, made_at=_date(row["made_at"]),
                replaced_on=_date(row["replaced_on"]), evidence_tier="record", form=row["form"],
                source_key=row["source_key"], document_id=str(row["document_id"]),
                document_type=row["document_type"], report_number=None, version=None, sequence=None,
                passage_id=key, evidence_id=evidence, pdf_page=_int(row["pdf_page"]), quote=None,
                read_by=RECORD_TABLES[row["form"]], public_from=_date(row["public_from"])))
    return made


def status_assertions(engine: Engine, project_id: str, ladder: Ladder, rows: ProjectRows | None = None
                      ) -> list[Assertion]:
    """Each plan row that says its package's contract is not signed yet (ticket 132): its Process Status, word for
    word, as an assertion about the signing, made on the plan's date and standing until the agency's next version
    replaces it. A record that dates the signing before that day disagrees with it (cannot_both_be_true): the plan
    still said pending when the contract had been signed. The row is the one check_plan checks, by the same evidence
    id, so the plan check reads the disagreement rather than working it out again (CLAUDE.md rule 4)."""
    attribute = ladder.attribute("signed_on")
    made: dict[str, Assertion] = {}
    for row in _of(engine, rows, project_id, ladder).statuses.get(project_id, []):
        key = f"{row['document_id']}/{row['step_reference']}"
        evidence = f"{RECORD_TABLES[PLAN_ROW]}:{key}"
        planned = _date(row["plan_date"])
        found = Assertion(
            assertion_id=assertion_id(evidence, row["step_reference"], attribute.key), subject_kind="package",
            subject_id=row["step_reference"], project_id=project_id, attribute=attribute.key,
            attribute_kind=attribute.kind, field_name=PROCESS_STATUS, value=row["process_status"], value_form=STATUS,
            judgment=None, period_event=CONTRACT_SIGNING, period_start=planned, period_end=planned, made_at=planned,
            replaced_on=_date(row["replaced_on"]), evidence_tier="record", form=PLAN_ROW, source_key="documents",
            document_id=str(row["document_id"]), document_type=PLAN_TYPE, report_number=None, version=None,
            sequence=None, passage_id=key, evidence_id=evidence, pdf_page=_int(row["pdf_page"]), quote=None,
            read_by=RECORD_TABLES[PLAN_ROW], public_from=_date(row["public_from"]))
        made.setdefault(found.assertion_id, found)  # a reference a version lists twice keeps its first row
    return list(made.values())


# ── The IEG ratings dataset ──────────────────────────────────────────────

IEG_READER = "strata.gold.ieg_rating"
IEG_COLUMNS = ("outcome", "bank_performance", "quality_at_entry", "quality_of_supervision", "me_quality")


def ieg_assertions(engine: Engine, project_id: str, ladder: Ladder, dates: Periods, rows: ProjectRows | None = None
                   ) -> list[Assertion]:
    """Each rating the IEG ratings dataset gives the project, for the whole project, under each attribute the
    ladder names by the dataset's field name. The dataset repeats IEG's own evaluations, so its rows are in
    the ieg tier, and each is made on the day it became public, as the dataset gives no date."""
    if dates.whole_project is None:
        return []
    start, end = dates.whole_project
    made = []
    for row in _of(engine, rows, project_id, ladder).ieg.get(project_id, []):
        key = f"{project_id}/{row['evaluation_type']}/{row['evaluation_fy']}"
        evidence = f"{IEG_READER}:{key}"
        public = _date(row["public_from"])
        for column in IEG_COLUMNS:
            attribute = ladder.attribute_named(column)
            rating = ladder.rating(attribute.key, row[column]) if attribute and attribute.kind == "rating" else None
            if rating is None:
                continue  # an attribute the ladder does not know, or no rating
            made.append(Assertion(
                assertion_id=assertion_id(evidence, project_id, attribute.key), subject_kind="project",
                subject_id=project_id, project_id=project_id, attribute=attribute.key,
                attribute_kind=attribute.kind, field_name=column, value=rating, value_form="rating",
                judgment=ladder.side(attribute.key, rating), period_event=WHOLE_PROJECT,
                period_start=start, period_end=end, made_at=public, replaced_on=None,
                evidence_tier="ieg", form="rating_field", source_key="ieg_ratings", document_id=key,
                document_type=row["evaluation_type"], report_number=None, version=None, sequence=None,
                passage_id=key, evidence_id=evidence, pdf_page=None, quote=None, read_by=IEG_READER,
                public_from=public))
    return made


# ── Assertions read from text, by the batch model ────────────────────────

INSTRUCTIONS = """You read one World Bank report about one project and list the ratings it gives and its
accounts of how the project was going at a named moment. The message gives the report's passages, each
with its passage_id, its PDF pages and its text, the attributes you may report with the ratings each
takes, and the periods an assertion may describe. Use only what the passages say.
For each assertion give: passage_id, the passage it is in; pdf_page, the PDF page its words are on;
quote, the shortest run of the passage's words that states it, copied word for word; attribute, one of
the attributes given; field_name, the report's own name for what it rates, word for word; value, the
rating as the report writes it, or, for an account that gives no rating, an empty value and side,
satisfactory or unsatisfactory, for the side of the line it falls on; form, rating_field when the rating
sits in its own field or table,
narrative when a sentence tells it; period, whole_project for a rating of the whole project, or the
named moment the account is about, such as mid_term_review.
Never guess a value, never join words from two places, and leave out what does not fit.
Answer with one JSON object and nothing else: {"assertions": [...]}, with an empty list when there is none."""
# The periods a report's assertion may describe: the whole project, from the Board's approval to closing,
# or a moment whose date the ISRs' key dates give.
TEXT_PERIODS = (WHOLE_PROJECT, MID_TERM_REVIEW, APPRAISAL)
KEY_DATE_LABELS = {MID_TERM_REVIEW: re.compile(r"Actual Mid[- ]Term Review Date:?\s*(\d{1,2}-[A-Za-z]{3}-\d{4})")}
REPORT_TIERS = ("pad", "icr", "ieg")  # the tiers whose reports the batch model reads; ISRs come from their tables
CUSTOM_ID = "assertions:{document_id}/v{version}"


@dataclass(frozen=True)
class Rejection:
    """One row of strata.ops.assertion_rejections (its table definition says what each column holds)."""

    run_id: str
    project_id: str
    document_id: str
    version: int | None
    passage_id: str | None
    pdf_page: int | None
    attribute: str | None
    value: str | None
    quote: str | None
    reason: str
    read_by: str
    rejected_at: dt.datetime
    public_from: dt.date


REJECTION_COLUMNS = tuple(f.name for f in fields(Rejection))


@dataclass(frozen=True)
class Report:
    """A report the batch model is asked about, with the passages it is given."""

    document_id: str
    project_id: str
    document_type: str
    report_number: str | None
    version: int | None
    document_date: dt.date
    replaced_on: dt.date | None
    public_from: dt.date
    passages: dict[str, dict]

    @property
    def custom_id(self) -> str:
        return CUSTOM_ID.format(document_id=self.document_id, version=self.version or 1)


def reports(engine: Engine, project_id: str, ladder: Ladder, rows: ProjectRows | None = None) -> list[Report]:
    found = []
    for row in _of(engine, rows, project_id, ladder).reports.get(project_id, []):
        passages = {passage["passage_id"]: passage for passage in _rows(
            engine, _sql("report_passages.sql"), document_id=str(row["document_id"]), table_summary=TABLE_SUMMARY)}
        if passages:
            found.append(Report(str(row["document_id"]), project_id, row["document_type"], row["report_number"],
                                _int(row["version"]), _date(row["document_date"]), _date(row["replaced_on"]),
                                _date(row["public_from"]), passages))
    return found


def request(report: Report, ladder: Ladder) -> Request:
    """What the batch model is asked about one report: its passages, the attributes it may report and the
    periods an assertion may describe."""
    attributes = [{"attribute": attribute.key, "ratings": list(ladder.scales[attribute.scale].ratings)}
                  for attribute in ladder.attributes.values() if attribute.kind == "rating"]
    passages = [{"passage_id": key, "pdf_page": _int(passage["pdf_page"]), "last_pdf_page": _int(passage["last_pdf_page"]),
                 "section": passage["section_path"], "text": passage["text"]} for key, passage in report.passages.items()]
    return Request(report.custom_id, INSTRUCTIONS, {
        "project_id": report.project_id, "document_type": report.document_type, "report_number": report.report_number,
        "document_date": report.document_date.isoformat(), "attributes": attributes, "periods": list(TEXT_PERIODS),
        "passages": passages})


@dataclass(frozen=True)
class Periods:
    """The dates of the periods a project's reports describe, from its records and its ISRs' key dates."""

    whole_project: tuple[dt.date, dt.date] | None
    moments: dict[str, dt.date]
    # The document types written at appraisal: the ladder's pad tier (config/evidence_ladder.toml), defined there once.
    appraisal_types: tuple[str, ...] = ()

    def dates(self, period: str, report: Report) -> tuple[dt.date, dt.date] | None:
        if period == WHOLE_PROJECT:
            return self.whole_project
        if period == APPRAISAL:
            return ((report.document_date, report.document_date) if report.document_type in self.appraisal_types
                    else None)
        day = self.moments.get(period)
        return (day, day) if day else None



def periods(engine: Engine, project_id: str, rows: ProjectRows | None = None, ladder: Ladder | None = None) -> Periods:
    ladder = ladder or load_ladder()
    held = _of(engine, rows, project_id, ladder)
    project = held.dates.get(project_id, [])
    approved, closing = (_date(project[0]["approval_date"]), _date(project[0]["closing_date"])) if project else (None,
                                                                                                                 None)
    moments = {}
    for period, label in KEY_DATE_LABELS.items():
        for row in held.key_dates.get(project_id, []):
            found = label.search(row["text"] or "")
            if found:
                moments[period] = dt.datetime.strptime(found.group(1), "%d-%b-%Y").date()
                break
    return Periods((approved, closing) if approved and closing and approved <= closing else None, moments,
                   ladder.tiers["pad"].document_types)


PENDING = "pending:"  # how bronze holds a request in a batch still running: this, then the batch's id


def _keep(engine: Engine, model: BatchModel, answers: list[Answer], hashes: dict[str, str], public: dict[str, dt.date],
          when: dt.datetime) -> None:
    engine.insert_rows("strata.bronze.batch_answers", ("custom_id", "request_hash", "read_by", "content", "error",
                                                       "answered_at", "public_from"),
                       [(answer.custom_id, hashes[answer.custom_id], model.name, answer.content, answer.error, when,
                         public[answer.custom_id]) for answer in answers])


def ask(engine: Engine, model: BatchModel, asked: list[tuple[Report, Request]], clock: Callable[[], dt.datetime]
        ) -> tuple[dict[str, Answer], int]:
    """The model's answer to each request: one held in bronze for the same request from the same reader, or a
    new one, which is kept there; and how many requests wait on a batch still running. Only requests with no
    answer held go to the model, and an error is no answer, so its request is asked again. A request held as
    pending in a batch an earlier run sent is waited for in that batch rather than asked again."""
    hashes = {request.custom_id: request.digest(model.deployment) for _, request in asked}
    joined = ",".join(hashes.values()) or "-"
    held: dict[str, Answer] = {}
    for row in _rows(engine, _sql("answers_held.sql"), read_by=model.name, hashes=joined):
        held.setdefault(row["request_hash"], Answer(row["custom_id"], row["content"], row["error"]))
    answers = {custom_id: held[digest] for custom_id, digest in hashes.items() if digest in held}
    latest: dict[str, str] = {}  # each request's newest row with no answer: an error, or pending in a batch
    for row in _rows(engine, _sql("answers_pending.sql"), read_by=model.name, hashes=joined):
        latest.setdefault(row["request_hash"], row["error"] or "")
    batches: dict[str | None, list[tuple[Report, Request]]] = {}
    for report, request in asked:
        if request.custom_id not in answers:
            error = latest.get(hashes[request.custom_id], "")
            batches.setdefault(error.removeprefix(PENDING) if error.startswith(PENDING) else None, []).append(
                (report, request))
    pending = 0
    for resume, waiting in batches.items():
        public = {request.custom_id: report.public_from for report, request in waiting}
        requests = [request for _, request in waiting]
        try:
            try:
                given = model.answer(requests, resume=resume)
            except BatchError:
                if resume is None:
                    raise
                # The batch an earlier run sent cannot be read, as when its files expired: send its requests again.
                resume = None
                given = model.answer(requests, resume=None)
            new = [answer for answer in given if answer.custom_id in public]
        except BatchPending as running:
            pending += len(waiting)
            if running.batch_id and running.batch_id != resume:
                _keep(engine, model, [Answer(custom_id, None, f"{PENDING}{running.batch_id}") for custom_id in public],
                      hashes, public, clock())
            continue
        if resume is not None:
            # A request the finished batch did not answer gets a row that says so, so the next run asks for it in a
            # new batch rather than resuming this one for ever (ticket 20's review, F4).
            answered = {answer.custom_id for answer in new}
            new += [Answer(custom_id, None, f"no answer in batch {resume}") for custom_id in public
                    if custom_id not in answered]
        _keep(engine, model, new, hashes, public, clock())
        answers |= {answer.custom_id: answer for answer in new}
    return answers, pending


def _page_of(passage: dict, page) -> bool:
    first, last = _int(passage["pdf_page"]), _int(passage["last_pdf_page"])
    try:
        page = int(page)
    except (TypeError, ValueError):
        return False
    return first is not None and first <= page <= (last or first)


def read_answer(report: Report, answer: Answer, ladder: Ladder, dates: Periods, read_by: str, run_id: str,
                when: dt.datetime) -> tuple[list[Assertion], list[Rejection]]:
    """The assertions in one answer that pass the checks, and those rejected with their reason. The check
    rejects; it never repairs."""
    try:
        items = json.loads(answer.content or "{}").get("assertions") or []
    except (ValueError, AttributeError):
        items = []
    kept, rejected = [], []

    def reject(item: dict, reason: str):
        rejected.append(Rejection(run_id, report.project_id, report.document_id, report.version,
                                  item.get("passage_id"), _int(item.get("pdf_page")), item.get("attribute"),
                                  item.get("value"), item.get("quote"), reason, read_by, when, report.public_from))

    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        passage = report.passages.get(str(item.get("passage_id")))
        if passage is None:
            reject(item, "passage_not_found")
            continue
        quote = str(item.get("quote") or "")
        if not quote.strip() or not _page_of(passage, item.get("pdf_page")) or find_quote(quote, passage["text"]) is None:
            reject(item, "quote_not_on_page")
            continue
        attribute = ladder.attributes.get(str(item.get("attribute")))
        if attribute is None or attribute.kind != "rating":
            reject(item, "unknown_attribute")
            continue
        period = dates.dates(str(item.get("period")), report) if item.get("period") in TEXT_PERIODS else None
        if period is None:
            reject(item, "unknown_period")
            continue
        value, side = str(item.get("value") or "").strip(), str(item.get("side") or "").strip().lower()
        if value in ladder.no_rating:
            continue  # the report gives no rating here, such as "Efficiency Rating ---"
        rating = ladder.rating(attribute.key, value) if value else None
        side = side if not value and side in SIDES else None
        if rating is None and side is None:
            reject(item, "value_not_on_scale")
            continue
        form = item.get("form") if item.get("form") in ("rating_field", "narrative") else "narrative"
        evidence = f"{PASSAGES}:{passage['passage_id']}"
        kept.append(Assertion(
            assertion_id=assertion_id(evidence, report.project_id, attribute.key),
            subject_kind="project", subject_id=report.project_id, project_id=report.project_id,
            attribute=attribute.key, attribute_kind=attribute.kind,
            field_name=str(item.get("field_name") or attribute.names[0]), value=rating or side,
            value_form="rating" if rating else "judgment",
            judgment=ladder.side(attribute.key, rating) if rating else side,
            period_event=str(item["period"]), period_start=period[0], period_end=period[1],
            made_at=report.document_date, replaced_on=report.replaced_on,
            evidence_tier=ladder.tier_of(report.document_type) or "record", form=form,
            source_key="documents", document_id=report.document_id, document_type=report.document_type,
            report_number=report.report_number, version=report.version, sequence=None,
            passage_id=passage["passage_id"], evidence_id=evidence, pdf_page=_int(item.get("pdf_page")),
            quote=quote, read_by=read_by, public_from=report.public_from))
    return once_a_page(kept, list(report.passages)), rejected


def once_a_page(kept: list[Assertion], order: list[str]) -> list[Assertion]:
    """One assertion for each thing a page of a report states: two read from one page that name the same subject,
    attribute, period and value are one, the one from the passage that comes first on the page (ticket 136). On the
    workspace the layout parser read the PAD's risk table twice, as table65.1 and table65b.1, so the batch model
    rated the overall risk from both cells, and each ISR that rated otherwise disagreed with the PAD twice."""
    rank = {passage_id: at for at, passage_id in enumerate(order)}
    first: dict[tuple, Assertion] = {}
    for assertion in sorted(kept, key=lambda one: rank.get(one.passage_id, len(rank))):
        first.setdefault((assertion.document_id, assertion.version, assertion.pdf_page, assertion.subject_kind,
                          assertion.subject_id, assertion.attribute, assertion.period_event, assertion.period_start,
                          assertion.period_end, assertion.value), assertion)
    held = {id(assertion) for assertion in first.values()}
    return [assertion for assertion in kept if id(assertion) in held]


def read_answers(asked: list[tuple[Report, Request]], answers: dict[str, Answer], ladder: Ladder, dates: Periods,
                 model: BatchModel, run_id: str, when: dt.datetime) -> tuple[list[Assertion], list[Rejection]]:
    """The assertions in the answers to one project's requests, and the ones rejected."""
    kept, rejected = [], []
    for report, question in asked:
        answer = answers.get(question.custom_id)
        if answer is not None and answer.content is not None:
            more, less = read_answer(report, answer, ladder, dates, model.name, run_id, when)
            kept += more
            rejected += less
    # One passage can state one attribute once: a second assertion of the same id is a repeat.
    unique = {assertion.assertion_id: assertion for assertion in reversed(kept)}
    return [assertion for assertion in kept if unique[assertion.assertion_id] is assertion], rejected


# ── Disagreements and the evidence ladder ────────────────────────────────

# A period that names one event of its subject, which each source dates for itself: two sources about a
# package's signing describe the same moment, whatever date each gives it.
ONE_TIME_EVENTS = (CONTRACT_SIGNING,)


@dataclass(frozen=True)
class Disagreement:
    """One row of strata.gold.disagreement (its table definition says what each column holds)."""

    disagreement_id: str
    project_id: str
    subject_kind: str
    subject_id: str
    attribute: str
    first_assertion_id: str
    second_assertion_id: str
    period_event: str
    period_start: dt.date
    period_end: dt.date
    lean_assertion_id: str | None
    rule_id: str | None
    replaced_on: dt.date | None
    public_from: dt.date


DISAGREEMENT_COLUMNS = tuple(f.name for f in fields(Disagreement))


def overlap(a: Assertion, b: Assertion) -> tuple[str, dt.date, dt.date] | None:
    """The period two assertions both describe, or None when their periods do not meet. An ISR's period
    starts the day after the ISR before it, so two ISRs never meet."""
    if a.period_event == b.period_event and a.period_event in ONE_TIME_EVENTS:
        return a.period_event, min(a.period_start, b.period_start), max(a.period_end, b.period_end)
    start, end = max(a.period_start, b.period_start), min(a.period_end, b.period_end)
    if start > end:
        return None
    narrower = b if (b.period_start, b.period_end) == (start, end) else a
    return narrower.period_event, start, end


def cannot_both_be_true(a: Assertion, b: Assertion, amount_tolerance: Decimal = Decimal(0)) -> bool:
    """Two ratings of one scale that differ, a rating and an account (or two accounts) on different sides of
    the line, two different dates, two amounts that differ by more than the tolerance share of the larger
    one (config/thresholds.toml, disagreements.amount_tolerance_share), or a plan row that says the contract is not
    signed yet and a record that dates its signing before the agency's next plan replaced that row (ticket 132)."""
    if STATUS in (a.value_form, b.value_form):
        status, other = (a, b) if a.value_form == STATUS else (b, a)
        if other.value_form != "date":
            return False
        return status.replaced_on is None or dt.date.fromisoformat(other.value) < status.replaced_on
    if "judgment" in (a.value_form, b.value_form):
        return a.judgment is not None and b.judgment is not None and a.judgment != b.judgment
    if a.value_form == "amount":
        first, second = Decimal(a.value), Decimal(b.value)
        return abs(first - second) > amount_tolerance * max(abs(first), abs(second))
    return a.value.strip().lower() != b.value.strip().lower()


def _same_report(a: Assertion, b: Assertion) -> bool:
    """Two assertions of one report, or of two versions of it: a report re-issued under the same number
    replaces its earlier version rather than disagreeing with it (ticket 11's rule), as a new version of a
    Procurement Plan replaces the one before."""
    if a.document_id == b.document_id:
        return True
    if a.form == b.form == PLAN_ROW:
        return True  # a package has one row in its agency's plan, and each version replaces the one before
    return (a.source_key == b.source_key == "documents" and a.report_number is not None
            and (a.project_id, a.document_type, a.report_number) == (b.project_id, b.document_type, b.report_number))


def lean(a: Assertion, b: Assertion, ladder: Ladder) -> tuple[str | None, str | None]:
    """The side the ladder leans on and the rule that decided, or (None, None) when it ranks both the same."""
    rule = ladder.rule_for(a.attribute)
    if rule is not None and rule.tiers:
        rank = {side.assertion_id: rule.tiers.index(side.evidence_tier) if side.evidence_tier in rule.tiers
                else len(rule.tiers) for side in (a, b)}
        if rank[a.assertion_id] != rank[b.assertion_id]:
            return min((a, b), key=lambda side: rank[side.assertion_id]).assertion_id, rule.id
    elif rule is not None:
        def at_the_moment(side: Assertion) -> bool:
            return side.evidence_tier in rule.at_the_moment or side.period_start <= side.made_at <= side.period_end

        if at_the_moment(a) != at_the_moment(b):
            return (a if at_the_moment(a) else b).assertion_id, rule.id
    for tie in ladder.ties:
        if tie == "tieSpecific" and ladder.specificity_of(a.form) != ladder.specificity_of(b.form):
            return min((a, b), key=lambda side: ladder.specificity_of(side.form)).assertion_id, tie
        if tie == "tieRecent" and (a.made_at, a.public_from) != (b.made_at, b.public_from):
            return max((a, b), key=lambda side: (side.made_at, side.public_from)).assertion_id, tie
    return None, None


def written_order(a: Assertion, b: Assertion) -> tuple[Assertion, Assertion]:
    """The two sides in the order they were written."""
    first, second = sorted((a, b), key=lambda side: (side.made_at, side.public_from, side.assertion_id))
    return first, second


def detect(assertions: list[Assertion], ladder: Ladder, thresholds: Thresholds | None = None) -> list[Disagreement]:
    """Every disagreement among the assertions, each decided by the ladder."""
    tolerance = Decimal(str((thresholds or load_thresholds()).value("disagreements.amount_tolerance_share")))
    groups: dict[tuple[str, str, str], list[Assertion]] = {}
    for assertion in assertions:
        groups.setdefault((assertion.subject_kind, assertion.subject_id, assertion.attribute), []).append(assertion)
    found = []
    for group in groups.values():
        for at, a in enumerate(group):
            for b in group[at + 1:]:
                period = overlap(a, b)
                if period is None or _same_report(a, b) or not cannot_both_be_true(a, b, tolerance):
                    continue
                first, second = written_order(a, b)
                leaned, rule = lean(first, second, ladder)
                replaced = [day for day in (first.replaced_on, second.replaced_on) if day is not None]
                key = hashlib.sha256(f"{first.assertion_id}\n{second.assertion_id}".encode()).hexdigest()[:16]
                found.append(Disagreement(key, first.project_id, first.subject_kind, first.subject_id, first.attribute,
                                          first.assertion_id, second.assertion_id, *period, leaned, rule,
                                          min(replaced) if replaced else None,
                                          max(first.public_from, second.public_from)))
    return found


# ── The run ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RunReport:
    assertions: int
    rejected: int
    disagreements: int
    pending: int = 0  # reports whose answers wait on a batch still running, which a later run waits for
    changed: int = 0  # assertions and disagreements the run added or removed


REJECTION_STAMPS = tuple(REJECTION_COLUMNS.index(column) for column in ("run_id", "rejected_at", "public_from"))
WRITTEN = (("strata.gold.assertion", ASSERTION_COLUMNS, ()), ("strata.gold.disagreement", DISAGREEMENT_COLUMNS, ()),
           ("strata.ops.assertion_rejections", REJECTION_COLUMNS, REJECTION_STAMPS))


def write(engine: Engine, projects: list[str], assertions: list[Assertion], rejections: list[Rejection],
          disagreements: list[Disagreement]) -> int:
    """Rebuild strata.gold.assertion, strata.gold.disagreement and strata.ops.assertion_rejections for the run's
    projects whose rows differ from what the tables hold (leaving out a rejection's run and time,
    strata.lakehouse.rewrites), so a night with nothing new changes no row. It sends one DELETE a table for all
    those projects together, not one a project: for the workspace's 15,933 projects, three a project would be
    hours of statements (ticket 43, review B2). Returns the assertions and disagreements it added or removed."""
    where = "array_contains(split(:projects, ','), project_id)"
    new = {"strata.gold.assertion": [astuple(row) for row in assertions],
           "strata.gold.disagreement": [astuple(row) for row in disagreements],
           "strata.ops.assertion_rejections": [astuple(row) for row in rejections]}
    differing, counted = set(), {}
    for table, columns, stamps in WRITTEN:
        at = columns.index("project_id")
        before = rewrites.by_key(rewrites.held(engine, table, columns, where, {"projects": ",".join(projects)}),
                                 at, stamps)
        after = rewrites.by_key(new[table], at, stamps)
        changes = {project: rewrites.differing(before.get(project, Counter()), after.get(project, Counter()))
                   for project in set(before) | set(after)}
        differing |= {project for project, count in changes.items() if count}
        counted[table] = sum(changes.values())
    if not differing:
        return 0
    chosen = ",".join(sorted(differing))
    for table, columns, _ in WRITTEN:
        engine.run(f"DELETE FROM {table} WHERE {where}", {"projects": chosen})  # sql-lint: names only, from WRITTEN
        at = columns.index("project_id")
        engine.insert_rows(table, columns, [row for row in new[table] if row[at] in differing])
    return counted["strata.gold.assertion"] + counted["strata.gold.disagreement"]


def run(engine: Engine, projects: list[str], *, model: BatchModel, ladder: Ladder | None = None,
        thresholds: Thresholds | None = None, run_id: str = "local", clock: Callable[[], dt.datetime] = _now
        ) -> RunReport:
    """Every assertion of the run's projects, rebuilt, with the rejected ones counted and the disagreements
    between the rest decided by the ladder. A run with no live model passes HeldAnswers, so the assertions
    read from text come from the answers bronze holds."""
    ladder = ladder or load_ladder()
    made, rejected = [], []
    rows = ProjectRows(engine, projects, ladder)  # each family read once for every project of the run
    # Every project's requests go to the model in one call, so the live run waits for one batch, not one a project
    # (ticket 20's review, F6).
    asked = {project_id: [(report, request(report, ladder)) for report in reports(engine, project_id, ladder, rows)]
             for project_id in projects}
    answers, pending = ask(engine, model, [pair for pairs in asked.values() for pair in pairs], clock)
    when = clock()
    for project_id in projects:
        dates = periods(engine, project_id, rows, ladder)
        made += isr_assertions(engine, project_id, ladder, rows) + record_assertions(engine, project_id, ladder, rows)
        made += status_assertions(engine, project_id, ladder, rows)
        made += ieg_assertions(engine, project_id, ladder, dates, rows)
        more, less = read_answers(asked[project_id], answers, ladder, dates, model, run_id, when)
        made += more
        rejected += less
    found = detect(made, ladder, thresholds)
    changed = write(engine, projects, made, rejected, found)
    return RunReport(len(made), len(rejected), len(found), pending, changed)


def redetect(engine: Engine, projects: list[str], ladder: Ladder, thresholds: Thresholds | None = None) -> int:
    """Decide the run's projects' disagreements again from the assertions held, as a change to the ladder or to
    the thresholds needs no new reading. Returns how many it found."""
    held = [from_row(row) for project_id in projects
            for row in _rows(engine, "SELECT * FROM strata.gold.assertion WHERE project_id = :project_id",
                             project_id=project_id)]
    found = detect(held, ladder, thresholds)
    for project_id in projects:
        engine.run("DELETE FROM strata.gold.disagreement WHERE project_id = :project_id", {"project_id": project_id})
    return engine.insert_rows("strata.gold.disagreement", DISAGREEMENT_COLUMNS, [astuple(row) for row in found])


DATES = {"period_start", "period_end", "made_at", "replaced_on", "public_from"}
INTS = {"version", "sequence", "pdf_page"}


def typed(column: str, value):
    """A column of strata.gold.assertion or strata.gold.disagreement as Python holds it, from typed values or
    from text."""
    if column in DATES:
        return _date(value)
    if column in INTS:
        return _int(value)
    return None if value is None else str(value)


def from_row(row: dict) -> Assertion:
    """An assertion as a query of strata.gold.assertion returns it."""
    return Assertion(**{column: typed(column, row[column]) for column in ASSERTION_COLUMNS})


def default_projects(engine: Engine) -> list[str]:
    """The projects whose documents the passage reader read, and those with records: a contract, a notice, a
    Procurement Plan or an IEG rating. The run reads them all with one query a family (ProjectRows)."""
    return [row["project_id"] for row in _rows(engine, _sql("projects.sql")) if row["project_id"]]


def run_on_fixture(engine: Engine, run_id: str = "fixture", clock: Callable[[], dt.datetime] = _now) -> RunReport:
    """The run over the fixture database, as the gate builds it, with the batch model's recorded answers."""
    return run(engine, default_projects(engine), model=RecordedBatch(), run_id=run_id, clock=clock)
