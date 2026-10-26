"""Passage reports from the evidence drawer, the passage reviewers' decisions, the scale rules and the loop's
measures (ticket 32; docs/PLAN.md section 11, "Feedback"; the 32 design brief, sections 4 and 9).

A person who reads a passage a search found for their question can mark it "Wrong passage" or "Not useful",
with an optional reason. The app writes one candidate label (strata.ops.candidate_labels) with the viewer the
Databricks App forwarded and, from the answer's own record (strata.ops.answer_citations), the question, the
sentence that cited the passage, the question's kind and the as-of date. The browser sends only the evidence
id, the answer's run id, the sentence, the kind and the reason. Withdrawing writes a new row.

Nothing a report says reaches production ranking until a passage reviewer accepts it. Reports are grouped by
passage and kind of question, and one decision covers every report waiting in the group: "Rank it lower"
(accepted) or "Keep its ranking" (declined), each with a required reason. A reviewer never decides a group that
holds a report they sent (own_report). A decided group can be reopened with a reason, which puts its reports
back in the queue and gives the passage its earlier ranking. Every act is a new row of
strata.ops.label_decisions; nothing changes or leaves (CLAUDE.md rule 5).

At scale (config/thresholds.toml, retrieval.mode = "scale"), the weekly run applies the rules for scale to the
week's waiting reports (triage()): reports about the sender's own project always go to a person; no person's
reports count for more than max_user_share of the batch; a group with silver_min_agreeing different people
making the same report, and no dissent, becomes a silver label (accepted_by_agreement) weighted by its
reporters' reliability as in Dawid and Skene; and one in audit_every of those goes to a passage reviewer as an
audit sample, who leaves it ranked lower or restores its ranking.

The server decides every act and says, for each item, what the viewer may do and, if nothing, a reason code
whose sentence is in web/src/copy.ts. PassageReports keeps the roles file and the settings, never a viewer: each
call gets the engine that reads as the viewer, for the passages a page shows, and the app's own engine, for the
loop's record. Who sent each report and who asked each question are masked for every reader (strata.lakehouse.masks;
ticket 64), so the record is read as well as written by the app's own identity, which alone can tell whether a
report is the viewer's own. A page names every other sender by role only.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from strata.config import Person, RetrievalLists, Roles, Thresholds, load_retrieval, load_thresholds
from strata.dbx import Viewer
from strata.knowledge.lessons.review import Refused
from strata.knowledge.retrieval.demotion import LOWERING, RESTORING
from strata.knowledge.retrieval.kinds import query_kind
from strata.knowledge.retrieval.labels import as_date, new_id, rows, utc_now
from strata.lakehouse.engine import Engine

PAGE = "passage_reports"  # the roles file's name for the Passage reports pages
KINDS = ("wrong_passage", "not_useful")
REPORTS_TABLE, DECISIONS_TABLE = "strata.ops.candidate_labels", "strata.ops.label_decisions"
CITATIONS_TABLE = "strata.ops.answer_citations"
REPORT_COLUMNS = ("report_id", "event", "viewer_id", "viewer_email", "viewer_role", "evidence_id", "passage_id",
                  "project_id", "run_id", "sentence_index", "sentence", "question", "query_kind", "kind", "reason",
                  "as_of", "own_project", "reported_at", "public_from")
DECISION_COLUMNS = ("decision_id", "group_id", "passage_id", "query_kind", "act", "reason", "reviewer_email",
                    "reviewer_name", "report_ids", "agreeing", "label_weight", "expected_state", "decided_at",
                    "public_from")
CITATION_COLUMNS = ("run_id", "viewer_id", "question", "query_kind", "as_of", "view", "sentence_index", "sentence",
                    "evidence_id", "tool", "project_id", "asked_at", "public_from")
PASSAGE_PREFIX = "strata.gold.passage:"
SEARCH_TOOL = "search_passages"

# A covering act: one that decides the reports it names. reopened and routed put them back in the queue.
COVERING = ("accepted", "declined", "accepted_by_agreement", "audit", "left_lower", "restored", "reopened", "routed")
# A report's status, from the latest act that covers it.
STATUS = {"accepted": "ranked_lower", "left_lower": "ranked_lower", "accepted_by_agreement": "ranked_lower_by_agreement",
          "audit": "ranked_lower_by_agreement", "declined": "kept", "restored": "kept"}
# What a decided group's record says happened (the 32 brief, section 5.3, Outcome values).
OUTCOMES = {"accepted": "ranked_lower", "declined": "kept", "accepted_by_agreement": "ranked_lower_by_agreement",
            "left_lower": "left_lower", "restored": "restored"}
# A reviewer's outcome, by the button: on a waiting group, and on an audit sample.
ACTS = {"rank_lower": "accepted", "keep": "declined", "leave_lower": "left_lower", "restore": "restored"}
WAITING_OUTCOMES, AUDIT_OUTCOMES = ("rank_lower", "keep"), ("leave_lower", "restore")
STAFF = "staff"


def group_id(passage_id: str, kind: str) -> str:
    """One passage and one kind of question, as one id."""
    return "grp-" + hashlib.sha256(f"{passage_id}|{kind}".encode()).hexdigest()[:12]


def passage_of(evidence_id: str) -> str | None:
    return evidence_id[len(PASSAGE_PREFIX):] if evidence_id.startswith(PASSAGE_PREFIX) else None


def _iso(value) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")
    return value.isoformat() if isinstance(value, dt.date) else str(value)


def _when(value) -> dt.datetime:
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.UTC)
    return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _bool(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


# ── What the store holds ─────────────────────────────────────────────────

@dataclass
class Report:
    report_id: str
    viewer_id: str
    viewer_email: str | None
    viewer_role: str
    evidence_id: str
    passage_id: str
    project_id: str | None
    run_id: str
    sentence_index: int | None
    sentence: str | None
    question: str
    query_kind: str
    kind: str
    reason: str | None
    as_of: dt.date | None
    own_project: bool
    reported_at: dt.datetime
    withdrawn_at: dt.datetime | None = None

    @property
    def group_id(self) -> str:
        return group_id(self.passage_id, self.query_kind)


@dataclass
class Act:
    decision_id: str
    group_id: str
    passage_id: str
    query_kind: str
    act: str
    reason: str | None
    reviewer_email: str | None
    reviewer_name: str | None
    report_ids: list[str]
    agreeing: int | None
    label_weight: float | None
    decided_at: dt.datetime


@dataclass
class Group:
    group_id: str
    passage_id: str
    query_kind: str
    reports: list[Report] = field(default_factory=list)  # every report not withdrawn, oldest first
    acts: list[Act] = field(default_factory=list)  # every act on the group, oldest first


class Ledger:
    """Every report and every act, read once for a request. Both tables stay small: one row per report and
    per decision."""

    def __init__(self, engine: Engine):
        self.reports: dict[str, Report] = {}
        for row in rows(engine, "reports"):
            if row["event"] == "withdrawn":
                if row["report_id"] in self.reports:
                    self.reports[row["report_id"]].withdrawn_at = _when(row["reported_at"])
                continue
            self.reports[row["report_id"]] = Report(
                row["report_id"], row["viewer_id"], row["viewer_email"], row["viewer_role"], row["evidence_id"],
                row["passage_id"], row["project_id"], row["run_id"],
                None if row["sentence_index"] in (None, "") else int(row["sentence_index"]), row["sentence"],
                row["question"], row["query_kind"], row["kind"], row["reason"] or None,
                as_date(row["as_of"]) if row["as_of"] not in (None, "") else None, _bool(row["own_project"]),
                _when(row["reported_at"]))
        self.acts = [Act(row["decision_id"], row["group_id"], row["passage_id"], row["query_kind"], row["act"],
                         row["reason"] or None, row["reviewer_email"] or None, row["reviewer_name"] or None,
                         json.loads(row["report_ids"] or "[]"),
                         None if row["agreeing"] in (None, "") else int(row["agreeing"]),
                         None if row["label_weight"] in (None, "") else float(row["label_weight"]),
                         _when(row["decided_at"])) for row in rows(engine, "decisions")]
        self.groups: dict[str, Group] = {}
        for report in self.reports.values():
            if report.withdrawn_at is None:
                self._group(report.group_id, report.passage_id, report.query_kind).reports.append(report)
        for act in self.acts:
            self._group(act.group_id, act.passage_id, act.query_kind).acts.append(act)

    def _group(self, key: str, passage_id: str, kind: str) -> Group:
        return self.groups.setdefault(key, Group(key, passage_id, kind))

    def covering(self, report: Report) -> Act | None:
        """The latest act that names the report."""
        found = [act for act in self.acts if act.act in COVERING and report.report_id in act.report_ids]
        return found[-1] if found else None

    def status(self, report: Report) -> str:
        """waiting, ranked_lower, ranked_lower_by_agreement or kept."""
        act = self.covering(report)
        return STATUS.get(act.act, "waiting") if act else "waiting"

    def waiting(self, group: Group) -> list[Report]:
        """The group's reports no act decides: never decided, reopened, or routed to a person."""
        return [report for report in group.reports if self.status(report) == "waiting"]

    def audit(self, group: Group) -> Act | None:
        """The audit sample waiting for a reviewer's check, when the group's latest deciding act is one."""
        deciding = [act for act in group.acts if act.act != "routed"]
        return deciding[-1] if deciding and deciding[-1].act == "audit" else None

    def latest(self, group: Group) -> Act | None:
        return group.acts[-1] if group.acts else None

    def decided(self, group: Group) -> Act | None:
        """The act a decided record shows: the group's latest act that decided its reports, while nothing waits
        and no audit is open."""
        if self.waiting(group) or self.audit(group):
            return None
        found = [act for act in group.acts if act.act in OUTCOMES]
        return found[-1] if found else None

    def lowered(self, group: Group) -> bool:
        changing = [act for act in group.acts if act.act in LOWERING | RESTORING]
        return bool(changing) and changing[-1].act in LOWERING

    def state(self, group: Group) -> str:
        """What a reviewer saw: the id of the group's latest act, or none. An act sent with another state is
        stale."""
        latest = self.latest(group)
        return latest.decision_id if latest else "none"


# ── The rules for scale: weighting, the share cap and the audit ──────────

def reliability(ledger: Ledger, viewer_id: str, thresholds: Thresholds) -> float:
    """A person's reliability in the one-coin form of Dawid and Skene: how often a passage reviewer agreed with
    their reports, from a prior of prior_agreed in prior_reviews."""
    value = thresholds.value
    agreed, reviewed = float(value("retrieval.prior_agreed")), float(value("retrieval.prior_reviews"))
    for report in ledger.reports.values():
        if report.viewer_id != viewer_id:
            continue
        act = ledger.covering(report)
        if act is None or act.reviewer_email is None or act.act not in {"accepted", "declined", "left_lower", "restored"}:
            continue
        reviewed += 1
        agreed += act.act in {"accepted", "left_lower"}
    return agreed / reviewed


def label_weight(reliabilities: Iterable[float]) -> float:
    """The chance the passage is wrong for that kind of question, given that people of these reliabilities all
    said so and a prior of one in two (Dawid and Skene's one-coin model), at two decimals, a tool column."""
    yes = no = 1.0
    for value in reliabilities:
        value = min(max(value, 1e-6), 1 - 1e-6)
        yes, no = yes * value, no * (1 - value)
    return round(yes / (yes + no), 2)


def audit_sample(groups: list[str], every: int) -> set[str]:
    """One in every of the groups made silver labels in a batch, at least one: those whose id hashes lowest."""
    if not groups:
        return set()
    count = max(1, math.ceil(len(groups) / every))
    return set(sorted(groups, key=lambda key: hashlib.sha256(key.encode()).hexdigest())[:count])


def share_cap(batch: int, share: float) -> int:
    """The most of a batch's reports one person may supply: share of the batch, rounded down, and at least one."""
    return max(1, math.floor(batch * share))


# ── The reads and acts ───────────────────────────────────────────────────

@dataclass
class PassageReports:
    roles: Roles
    now: Callable[[], dt.datetime] = utc_now
    thresholds: Thresholds | None = None
    lists: RetrievalLists | None = None
    new_id: Callable[[str], str] = new_id  # a report's or decision's id, from its prefix

    def __post_init__(self):
        self.thresholds = self.thresholds or load_thresholds()
        self.lists = self.lists or load_retrieval()

    def value(self, name: str):
        return self.thresholds.value(f"retrieval.{name}")

    @property
    def mode(self) -> str:
        return str(self.value("mode"))

    # ── Who may act ──────────────────────────────────────────────────────

    def reviewer(self, viewer: Viewer) -> Person | None:
        person = self.roles.person(viewer.email)
        return person if person is not None and PAGE in person.pages(self.roles) else None

    def _require(self, viewer: Viewer) -> Person:
        person = self.reviewer(viewer)
        if person is None:
            raise Refused(403, "not_a_passage_reviewer")
        return person

    @staticmethod
    def sent_by(report: Report, viewer: Viewer) -> bool:
        return bool((viewer.user_id and report.viewer_id == viewer.user_id)
                    or (viewer.email and (report.viewer_email or "").lower() == viewer.email.lower()))

    def can(self, ledger: Ledger, group: Group, viewer: Viewer) -> dict:
        waiting = ledger.waiting(group) or ([] if ledger.audit(group) is None else group.reports)
        if any(self.sent_by(report, viewer) for report in waiting):
            return {"decide": False, "reason_code": "own_report"}
        return {"decide": True, "reason_code": None}

    def own_project(self, viewer: Viewer, project_id: str | None) -> bool:
        person = self.roles.person(viewer.email)
        return bool(person and project_id and project_id in person.projects)

    # ── The evidence drawer's row ────────────────────────────────────────

    def feedback(self, evidence: dict, run_id: str | None, view: str) -> dict:
        """The drawer's feedback block for one source of an answer (the 32 brief, section 9): whether the row
        shows, and why not. Only a passage that search_passages found for the question has one; a preview shows
        it with both buttons disabled."""
        kind = evidence.get("kind")
        why_not = None
        if kind != "passage":
            why_not = "record"
        elif evidence.get("tool") != SEARCH_TOOL or not run_id:
            why_not = "no_question"
        elif view != STAFF:
            why_not = "preview"
        return {"allowed": why_not is None, "why_not": why_not, "run_id": run_id, "mode": self.mode,
                "my_report": None, "limits": {"reason_max_chars": int(self.value("reason_max_chars"))}}

    def my_report(self, ledger: Ledger, report: Report | None) -> dict | None:
        if report is None:
            return None
        act = ledger.covering(report)
        status = STATUS.get(act.act, "waiting") if act else "waiting"
        decided = act if status != "waiting" else None
        return {"report_id": report.report_id, "kind": report.kind, "reason": report.reason, "status": status,
                "reported_on": _iso(report.reported_at), "decided_on": _iso(decided.decided_at) if decided else None,
                "reviewer_reason": decided.reason if decided and decided.reviewer_email else None,
                "agreeing_count": decided.agreeing if decided and decided.act in {"accepted_by_agreement", "audit"} else None,
                "query_kind": report.query_kind}

    def _mine(self, ledger: Ledger, viewer: Viewer, evidence_id: str, run_id: str) -> Report | None:
        found = [report for report in ledger.reports.values() if report.withdrawn_at is None
                 and report.evidence_id == evidence_id and report.run_id == run_id and self.sent_by(report, viewer)]
        return found[-1] if found else None

    def mine(self, viewer: Viewer, evidence_id: str, run_id: str, record: Engine) -> dict:
        ledger = Ledger(record)
        return {"my_report": self.my_report(ledger, self._mine(ledger, viewer, evidence_id, run_id)),
                "mode": self.mode}

    def send(self, viewer: Viewer, body: dict, view: str, writer: Engine) -> dict:
        """Write one passage report from the answer's own record, or refuse it."""
        if body.get("kind") not in KINDS:
            raise Refused(422, "bad_kind")
        reason = (body.get("reason") or "").strip()
        if len(reason) > int(self.value("reason_max_chars")):
            raise Refused(422, "reason_too_long")
        evidence_id, run_id = body["evidence_id"], body["run_id"]
        cited = rows(writer, "citation", run_id=run_id, evidence_id=evidence_id)
        sentence = body.get("sentence_id")
        chosen = [row for row in cited if sentence is None or int(row["sentence_index"]) == int(sentence)] or cited
        if not chosen:
            raise Refused(404, "not_in_answer")
        citation = chosen[0]
        if citation["view"] != STAFF:  # the view the answer was asked in, as the server stored it
            raise Refused(403, "preview")
        passage = passage_of(evidence_id)
        if passage is None or citation["tool"] != SEARCH_TOOL:
            raise Refused(403, "no_question")
        if citation["viewer_id"] and viewer.user_id and citation["viewer_id"] != viewer.user_id:
            raise Refused(403, "not_your_answer")
        ledger = Ledger(writer)
        held = self._mine(ledger, viewer, evidence_id, run_id)
        if held is not None:
            raise Refused(409, "already_sent", {"my_report": self.my_report(ledger, held)})
        at = self.now()
        report = Report(self.new_id("rep"), viewer.user_id or viewer.email, viewer.email, STAFF,
                        evidence_id, passage, citation["project_id"], run_id, int(citation["sentence_index"]),
                        citation["sentence"], citation["question"], citation["query_kind"], body["kind"],
                        reason or None, as_date(citation["as_of"]), self.own_project(viewer, citation["project_id"]), at)
        writer.insert_rows(REPORTS_TABLE, REPORT_COLUMNS, [self._report_row(report, "sent", at)])
        return {"my_report": self.my_report(ledger, report), "mode": self.mode}

    @staticmethod
    def _report_row(report: Report, event: str, at: dt.datetime) -> tuple:
        return (report.report_id, event, report.viewer_id, report.viewer_email, report.viewer_role, report.evidence_id,
                report.passage_id, report.project_id, report.run_id, report.sentence_index, report.sentence,
                report.question, report.query_kind, report.kind, report.reason, report.as_of, report.own_project, at,
                at.astimezone(dt.UTC).date())

    def withdraw(self, viewer: Viewer, report_id: str, writer: Engine) -> dict:
        ledger = Ledger(writer)
        report = ledger.reports.get(report_id)
        if report is None or not self.sent_by(report, viewer) or report.withdrawn_at is not None:
            raise Refused(404, "unknown_report")
        if ledger.status(report) != "waiting":
            raise Refused(409, "decided", {"my_report": self.my_report(ledger, report)})
        writer.insert_rows(REPORTS_TABLE, REPORT_COLUMNS, [self._report_row(report, "withdrawn", self.now())])
        return {"my_report": None, "withdrawn": True, "mode": self.mode}

    # ── The record each answer leaves ────────────────────────────────────

    def citation_rows(self, run_id: str, viewer_id: str | None, question: str, as_of: dt.date, view: str,
                      sentences: Iterable[tuple[int, str, list[str]]], tool_of: Callable[[str], str | None],
                      project_of: Callable[[str], str | None], at: dt.datetime,
                      kind_of: Callable[[str], str | None] = lambda _evidence: None) -> list[tuple]:
        """One row per source each kept sentence cited. A passage search_passages found keeps the kind of question of
        that search (kind_of, from the turn's Facts), since search ranks lower by the kind of its own query, which can
        differ from the person's question's; any other source takes the kind of the question."""
        asked = query_kind(question, self.lists)

        def kind(evidence: str) -> str:
            return (kind_of(evidence) if tool_of(evidence) == SEARCH_TOOL else None) or asked

        return [(run_id, viewer_id, question, kind(evidence), as_of, view, index, text, evidence, tool_of(evidence),
                 project_of(evidence), at, at.astimezone(dt.UTC).date())
                for index, text, evidence_ids in sentences for evidence in evidence_ids]

    # ── Passage reports: the queue, a group, and the decided table ───────

    def me(self, viewer: Viewer, record: Engine | None) -> dict:
        """Whether the viewer reviews passage reports, and how many groups wait for them; without the app's own
        identity, which alone can tell their own reports, the count is not known."""
        person = self.reviewer(viewer)
        if person is None:
            return {"can_review_reports": False, "reports_waiting": None}
        if record is None:
            return {"can_review_reports": True, "reports_waiting": None}
        ledger = Ledger(record)
        return {"can_review_reports": True,
                "reports_waiting": sum(1 for group in self._open(ledger) if self.can(ledger, group, viewer)["decide"])}

    def _open(self, ledger: Ledger) -> list[Group]:
        return [group for group in ledger.groups.values() if ledger.waiting(group) or ledger.audit(group)]

    def _passages(self, engine: Engine, passage_ids: Iterable[str]) -> dict[str, dict]:
        """The passages a page shows, read in one statement, by id."""
        from strata.tools.search_passages import read_passages

        wanted = sorted(set(passage_ids))
        held = read_passages(engine, wanted, self.now().date())
        return {passage_id: self._fields(passage_id, held.get(passage_id) or {}) for passage_id in wanted}

    def _passage(self, engine: Engine, passage_id: str) -> dict:
        return self._passages(engine, [passage_id])[passage_id]

    @staticmethod
    def _fields(passage_id: str, found: dict) -> dict:
        source = found.get("source") or {}
        return {"passage_id": passage_id, "evidence_id": f"{PASSAGE_PREFIX}{passage_id}",
                "project_name": source.get("project_name"), "pid": source.get("project_id"),
                "doc_type": source.get("document_type"), "doc_date": source.get("document_date"),
                "para": found.get("paragraph"), "paragraph_numbered": found.get("paragraph_numbered"),
                "section": found.get("section_path"), "page": found.get("pdf_page"), "pages": source.get("pdf_pages"),
                "row": found or None}

    @staticmethod
    def kind_label(reports: list[Report], audit: bool) -> str:
        if audit:
            return "audit"
        kinds = {report.kind for report in reports}
        return "both" if kinds == set(KINDS) else next(iter(kinds), "wrong_passage")

    def row(self, ledger: Ledger, group: Group, viewer: Viewer, passages: dict[str, dict]) -> dict:
        audit = ledger.audit(group)
        reports = ledger.waiting(group) or (group.reports if audit else [])
        can = self.can(ledger, group, viewer)
        agreement = audit
        passage = {key: value for key, value in passages[group.passage_id].items() if key != "row"}
        return {"group_id": group.group_id, "kind_label": self.kind_label(reports, audit is not None),
                "group": "you" if can["decide"] else "others", "audit": audit is not None,
                **passage, "query_kind": group.query_kind,
                "report_count": len(reports), "first_on": _iso(min(report.reported_at for report in reports)) if reports else None,
                "own_project": any(report.own_project for report in reports),
                "decided_on": _iso(agreement.decided_at) if agreement else None,
                "agreeing": agreement.agreeing if agreement else None,
                "can": can["decide"], "reason_code": can["reason_code"], "state": ledger.state(group)}

    def queue(self, engine: Engine, viewer: Viewer, record: Engine, page: int = 1) -> dict:
        self._require(viewer)
        ledger = Ledger(record)
        waiting, since = self._open(ledger), self._since()
        decided_groups = [group for group in ledger.groups.values()
                          if (act := ledger.decided(group)) is not None and act.decided_at >= since]
        passages = self._passages(engine, [group.passage_id for group in waiting + decided_groups])
        open_rows = sorted((self.row(ledger, group, viewer, passages) for group in waiting),
                           key=lambda row: (row["first_on"] or row["decided_on"] or "", row["group_id"]))
        groups = {key: [row for row in open_rows if row["group"] == key] for key in ("you", "others")}
        decided = self._decided(ledger, decided_groups, passages)
        size = int(self.value("page_size"))
        pages = max(1, -(-len(decided) // size))
        page = min(max(page, 1), pages)
        shown = decided[(page - 1) * size: page * size]
        oldest = min((row["first_on"] or row["decided_on"] for row in open_rows), default=None)
        return {"mode": self.mode, "audit_every": int(self.value("audit_every")),
                "silver_min": int(self.value("silver_min_agreeing")),
                "lead": {"you": len(groups["you"]), "others": len(groups["others"]), "oldest_on": oldest},
                "groups": groups,
                "decided": {"window_days": int(self.value("decided_days")), "total": len(decided), "page": page,
                            "pages": pages, "from": (page - 1) * size + 1 if shown else 0,
                            "to": (page - 1) * size + len(shown), "rows": shown}}

    def _since(self) -> dt.datetime:
        return self.now() - dt.timedelta(days=int(self.value("decided_days")))

    def _decided(self, ledger: Ledger, decided: list[Group], passages: dict[str, dict]) -> list[dict]:
        found = []
        for group in decided:
            act = ledger.decided(group)
            passage = passages[group.passage_id]
            found.append({"group_id": group.group_id, "project_name": passage["project_name"], "pid": passage["pid"],
                          "para": passage["para"], "paragraph_numbered": passage["paragraph_numbered"],
                          "section": passage["section"], "query_kind": group.query_kind,
                          "outcome": OUTCOMES[act.act], "decided_on": _iso(act.decided_at),
                          "report_count": len(act.report_ids)})
        return sorted(found, key=lambda row: (row["decided_on"], row["group_id"]), reverse=True)

    def _role(self, report: Report, viewer: Viewer) -> str:
        return "you" if self.sent_by(report, viewer) else report.viewer_role

    def item(self, engine: Engine, viewer: Viewer, wanted: str, record: Engine) -> dict:
        self._require(viewer)
        ledger = Ledger(record)
        group = ledger.groups.get(wanted)
        if group is None:
            raise Refused(404, "unknown_group", {"group_id": wanted})
        return self.detail(engine, ledger, group, viewer)

    def detail(self, engine: Engine, ledger: Ledger, group: Group, viewer: Viewer) -> dict:
        audit = ledger.audit(group)
        waiting = ledger.waiting(group)
        decided = ledger.decided(group)
        shown = waiting or (group.reports if audit else [report for report in group.reports
                                                          if decided and report.report_id in decided.report_ids])
        can = self.can(ledger, group, viewer) if (waiting or audit) else {"decide": False, "reason_code": None}
        stage = "audit" if audit else "waiting" if waiting else "decided"
        outcome = None
        if decided is not None:
            outcome = {"outcome": OUTCOMES[decided.act], "decided_on": _iso(decided.decided_at),
                       "reviewer_name": decided.reviewer_name, "reason": decided.reason,
                       "agreeing": decided.agreeing}
        return {"group_id": group.group_id, "stage": stage, "kind_label": self.kind_label(shown, audit is not None),
                "query_kind": group.query_kind, "state": ledger.state(group), "mode": self.mode,
                "passage": self._passage(engine, group.passage_id),
                "report_count": len(shown), "first_on": _iso(min(r.reported_at for r in shown)) if shown else None,
                "own_project": any(report.own_project for report in shown),
                "audit": None if audit is None else {"decided_on": _iso(audit.decided_at), "agreeing": audit.agreeing},
                "reports": [{"report_id": report.report_id, "role": self._role(report, viewer),
                             "is_you": self.sent_by(report, viewer), "kind": report.kind,
                             "reported_on": _iso(report.reported_at), "question": report.question,
                             "sentence": report.sentence, "reason": report.reason, "run_id": report.run_id,
                             "own_project": report.own_project} for report in shown],
                "can": {"decide": can["decide"], "reopen": stage == "decided" and decided is not None,
                        "reason_code": can["reason_code"]},
                "outcome": outcome,
                "limits": {"reason_max_chars": int(self.value("reason_max_chars"))}}

    def _write_act(self, writer: Engine, group: Group, act: str, reason: str | None, person: Person | None,
                   report_ids: list[str], expected: str | None, agreeing: int | None = None,
                   weight: float | None = None, at: dt.datetime | None = None) -> Act:
        at = at or self.now()
        found = Act(self.new_id("dec"), group.group_id, group.passage_id, group.query_kind, act, reason,
                    person.email if person else None, person.name if person else None, report_ids, agreeing, weight, at)
        writer.insert_rows(DECISIONS_TABLE, DECISION_COLUMNS, [(
            found.decision_id, found.group_id, found.passage_id, found.query_kind, found.act, found.reason,
            found.reviewer_email, found.reviewer_name, json.dumps(found.report_ids), found.agreeing, found.label_weight,
            expected, at, at.astimezone(dt.UTC).date())])
        return found

    def decide(self, engine: Engine, viewer: Viewer, wanted: str, body: dict, writer: Engine) -> dict:
        person = self._require(viewer)
        ledger = Ledger(writer)
        group = ledger.groups.get(wanted)
        if group is None:
            raise Refused(404, "unknown_group", {"group_id": wanted})
        if body.get("expected_state") != ledger.state(group):
            latest = ledger.latest(group)
            raise Refused(409, "stale", {"name": latest.reviewer_name if latest else None,
                                         "time": _iso(latest.decided_at) if latest else None},
                          item=self.detail(engine, ledger, group, viewer))
        audit, waiting = ledger.audit(group), ledger.waiting(group)
        outcome = body.get("outcome")
        allowed = AUDIT_OUTCOMES if audit else WAITING_OUTCOMES if waiting else ()
        if not allowed:
            raise Refused(409, "nothing_waiting")
        if outcome not in allowed:
            raise Refused(422, "bad_outcome")
        can = self.can(ledger, group, viewer)
        if not can["decide"]:
            raise Refused(403, can["reason_code"])
        reason = (body.get("reason") or "").strip()
        if not reason:
            raise Refused(422, "no_reason")
        if len(reason) > int(self.value("reason_max_chars")):
            raise Refused(422, "reason_too_long")
        covered = [report.report_id for report in (waiting or audit_reports(ledger, group, audit))]
        self._write_act(writer, group, ACTS[outcome], reason, person, covered, body.get("expected_state"),
                        agreeing=audit.agreeing if audit else None)
        fresh = Ledger(writer)
        return {"saved": {"outcome": outcome, "next": self._next(fresh, viewer, group.group_id)},
                "item": self.detail(engine, fresh, fresh.groups[group.group_id], viewer)}

    def _next(self, ledger: Ledger, viewer: Viewer, done: str) -> str | None:
        """The oldest group still waiting that this reviewer may decide, for "Open the next report waiting for you"."""
        for group in sorted(self._open(ledger), key=lambda g: min((r.reported_at for r in g.reports), default=self.now())):
            if group.group_id != done and self.can(ledger, group, viewer)["decide"]:
                return group.group_id
        return None

    def reopen(self, engine: Engine, viewer: Viewer, wanted: str, reason: str, writer: Engine) -> dict:
        person = self._require(viewer)
        ledger = Ledger(writer)
        group = ledger.groups.get(wanted)
        if group is None:
            raise Refused(404, "unknown_group", {"group_id": wanted})
        decided = ledger.decided(group)
        if decided is None:
            raise Refused(409, "not_decided")
        reason = (reason or "").strip()
        if not reason:
            raise Refused(422, "no_reason")
        self._write_act(writer, group, "reopened", reason, person, list(decided.report_ids), ledger.state(group))
        fresh = Ledger(writer)
        return {"item": self.detail(engine, fresh, fresh.groups[group.group_id], viewer)}

    # ── The weekly run: the rules for scale, and the loop's measures ─────

    def triage(self, engine: Engine, writer: Engine) -> dict:
        """At scale, apply the rules to every waiting report: own project to a person, the share cap, silver
        labels from agreement with no dissent, and the audit sample. In the pilot it does nothing."""
        if self.mode != "scale":
            return {"routed": 0, "silver": 0, "audit": 0}
        ledger = Ledger(engine)
        routed, silver = 0, []
        batch: list[Report] = []
        for group in ledger.groups.values():
            for report in ledger.waiting(group):
                covering = ledger.covering(report)
                if covering is not None and covering.act == "routed":
                    continue  # an earlier run sent it to a person, who decides it
                if report.own_project:
                    self._write_act(writer, group, "routed", "own_project", None, [report.report_id], None)
                    routed += 1
                else:
                    batch.append(report)
        cap = share_cap(len(batch), float(self.value("max_user_share")))
        counted: list[Report] = []
        for viewer_id, theirs in _by(batch, lambda report: report.viewer_id).items():
            ordered = sorted(theirs, key=lambda report: report.reported_at)
            counted += ordered[:cap]
            for report in ordered[cap:]:
                self._write_act(writer, ledger.groups[report.group_id], "routed", "user_share", None,
                                [report.report_id], None)
                routed += 1
        minimum = int(self.value("silver_min_agreeing"))
        made: dict[str, tuple[list[Report], float]] = {}
        for key, theirs in _by(counted, lambda report: report.group_id).items():
            group = ledger.groups[key]
            people = {report.viewer_id for report in theirs}
            # Dissent: a reviewer kept or restored this passage's ranking for this kind of question before, or
            # someone withdrew a report on it.
            dissent = any(act.act in {"declined", "restored"} for act in group.acts) or any(
                report.withdrawn_at is not None and report.group_id == key for report in ledger.reports.values())
            if len(people) >= minimum and not dissent:
                weight = label_weight(reliability(ledger, person, self.thresholds) for person in people)
                made[key] = (theirs, weight)
        sampled = audit_sample(list(made), int(self.value("audit_every")))
        for key, (theirs, weight) in made.items():
            group = ledger.groups[key]
            ids = [report.report_id for report in theirs]
            agreeing = len({report.viewer_id for report in theirs})
            self._write_act(writer, group, "accepted_by_agreement", None, None, ids, None, agreeing, weight)
            if key in sampled:
                self._write_act(writer, group, "audit", None, None, ids, None, agreeing, weight)
            silver.append(key)
        return {"routed": routed, "silver": len(silver), "audit": len(sampled)}

    def labels(self, engine: Engine):
        """The feedback set of the labeled set: each passage now ranked lower for a kind of question, labeled as
        not answering questions of that kind, from a reviewer (feedback_reviewed) or an agreement at scale
        (feedback_agreement), with its weight. Only these train anything; no evaluation set takes them."""
        from strata.knowledge.retrieval.labels import Label

        ledger, found = Ledger(engine), []
        for group in ledger.groups.values():
            if not ledger.lowered(group):
                continue
            act = [act for act in group.acts if act.act in LOWERING][-1]
            first = min(group.reports, key=lambda report: report.reported_at, default=None)
            origin = "feedback_agreement" if act.act in {"accepted_by_agreement", "audit"} else "feedback_reviewed"
            found.append(Label("feedback", f"fb:{group.group_id}", first.question if first else group.query_kind,
                               act.decided_at.date(), first.project_id if first else None, group.passage_id, 0, origin,
                               act.label_weight if act.label_weight is not None else 1.0))
        return found, None

    def measure(self, engine: Engine, writer: Engine) -> dict:
        """The loop's measures: each week's reports per 100 sources opened, by kind, and what each person's
        "Wrong passage" reports did. Appended under the run's time; the latest row of each wins."""
        ledger, at = Ledger(engine), self.now()
        day = at.astimezone(dt.UTC).date()
        sent = [report for report in ledger.reports.values() if report.withdrawn_at is None and report.viewer_role == STAFF]
        reports = Counter((_monday(report.reported_at), report.kind) for report in sent)
        opened = Counter(_monday(_when(row["first_opened_at"])) for row in rows(engine, "opened"))
        least = int(self.value("min_opened"))
        weekly = [(week, kind, reports[(week, kind)], opened[week],
                   round(100 * reports[(week, kind)] / opened[week], 1) if opened[week] >= least else None, at, day)
                  for week in sorted({week for week, _ in reports} | set(opened)) for kind in KINDS]
        writer.insert_rows("strata.ops.retrieval_feedback_weekly",
                           ("week_start", "kind", "reports", "opened", "per_100", "computed_at", "public_from"), weekly)
        citations = rows(engine, "citations")
        people = []
        for viewer_id, theirs in _by([report for report in sent if report.kind == "wrong_passage"],
                                     lambda report: report.viewer_id).items():
            counts = Counter()
            runs: set[str] = set()
            passages = {}
            for report in theirs:
                passages.setdefault((report.passage_id, report.query_kind), report)
            for (passage, kind), report in passages.items():
                group = ledger.groups[group_id(passage, kind)]
                if ledger.lowered(group):
                    counts["fixed"] += 1
                    since = [act for act in group.acts if act.act in LOWERING][-1].decided_at
                    runs |= recited(citations, passage, kind, report.project_id, since)
                elif ledger.status(report) == "waiting":
                    counts["waiting"] += 1
                else:
                    counts["kept"] += 1
            people.append((viewer_id, len({passage for passage, _ in passages}), counts["fixed"], counts["waiting"],
                           counts["kept"], len(runs), at, day))
        writer.insert_rows("strata.ops.retrieval_feedback_viewers",
                           ("viewer_id", "marked", "fixed", "waiting", "kept", "recited", "computed_at", "public_from"),
                           people)
        return {"weeks": len(weekly) // len(KINDS), "viewers": len(people)}


class CitationLog:
    """The sources each answer cited, on their way to strata.ops.answer_citations, written as the app's own
    service principal beside the run log. engine() opens the engine that writes them. A write that fails is
    logged and changes nothing the viewer sees."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    def record(self, found: list[tuple]) -> bool:
        if not found:
            return True
        import logging

        try:
            engine = self.engine()
            try:
                engine.insert_rows(CITATIONS_TABLE, CITATION_COLUMNS, found)
            finally:
                close = getattr(engine, "close", None)
                if callable(close):
                    close()
        except Exception:  # the warehouse, the network or a token: none of them may change an answer
            logging.getLogger("strata.retrieval").exception("I could not write the citations of run %s.", found[0][0])
            return False
        return True


def _monday(when: dt.datetime) -> dt.date:
    day = when.astimezone(dt.UTC).date()
    return day - dt.timedelta(days=day.weekday())


def recited(citations: list[dict], passage: str, kind: str, project_id: str | None, since: dt.datetime) -> set[str]:
    """The answers to the same kind of question, on the same project, asked after a passage was ranked lower,
    that cite a paragraph search found and not that passage (the 39 brief, section 5.5)."""
    by_run: dict[str, list[dict]] = {}
    for row in citations:
        if row["query_kind"] == kind and _when(row["asked_at"]) > since:
            by_run.setdefault(row["run_id"], []).append(row)
    found = set()
    for run, cited in by_run.items():
        searched = [row for row in cited if row["tool"] == SEARCH_TOOL and passage_of(row["evidence_id"])]
        if not searched or (project_id and not any(row["project_id"] == project_id for row in searched)):
            continue
        if all(passage_of(row["evidence_id"]) != passage for row in searched):
            found.add(run)
    return found


def audit_reports(ledger: Ledger, group: Group, audit: Act | None) -> list[Report]:
    """The reports an open audit sample covers."""
    if audit is None:
        return []
    return [report for report in group.reports if report.report_id in audit.report_ids]


def _by(items: Iterable, key: Callable) -> dict:
    found: dict = {}
    for item in items:
        found.setdefault(key(item), []).append(item)
    return found
