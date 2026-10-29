"""Lesson review: who may act on each item of the queue, the business-day clock, and the acts that move a
lesson through its states (ticket 29; docs/PLAN.md section 11, "Lesson governance").

Strata proposes (strata.knowledge.lessons.propose). An accredited procurement specialist recommends, and a
different lead procurement specialist decides, each with a reason. Nobody recommends or decides on a lesson
from a project they work on. A lead may recommend, and then another lead decides. Who is who comes from the
roles file (config/roles.toml), for the viewer the Databricks App forwarded; the server decides every act
and says, for each item, what the viewer may do and, if nothing, why (a reason code, whose sentence is in
web/src/copy.ts). The browser decides nothing.

Every act is a new row (strata.ops.lesson_review_acts), and a decision that changes the library writes a new
lesson version (strata.ops.lesson_versions) and the proposals it rests on (strata.ops.lesson_sources). No
row changes or leaves: a change of mind is a re-check. A lesson's states follow from those rows: current at
its newest version, being re-checked while a re-check is open, retired when its newest version says so; a
proposal is rejected, or merged as evidence, by the decision on its item.

LessonReview reads as the viewer, through the engine a route opens with the viewer's own token (ADR 0003). It
writes every act through the writer engine the route passes, which is the app's own service principal, and
records as the actor the viewer the Databricks App forwarded. No reviewer has write access to the review
tables outside the app, so the two-person rule and recusal hold for every row. It keeps nothing about a viewer
between calls (CLAUDE.md rule 7).
"""

from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

from strata.agent.verifier import find_quote
from strata.config import (Editions, LessonLists, Person, Roles, Thresholds, load_editions, load_lesson_lists,
                           load_thresholds)
from strata.dbx import Viewer
from strata.knowledge.lessons import tags as lesson_tags
from strata.knowledge.lessons.propose import IEG_TYPES, PASSED, item_id
from strata.lakehouse.engine import Engine
from strata.reader.templates import template_for
from strata.tools.data_readiness_for import fill

PAGE = "lesson_review"  # the roles file's name for the review pages
STAGE_FOR = {"recommend": "recommendation", "decide": "decision", "cross_check": "cross_check"}
OUTCOMES = {
    ("new", "recommend"): ("add", "repeat", "reject"),
    ("new", "decide"): ("add", "repeat", "reject"),
    ("recheck", "recommend"): ("keep", "change", "retire_wrong", "retire_outdated"),
    ("recheck", "decide"): ("keep", "change", "retire_wrong", "retire_outdated"),
    ("cross_check", "cross_check"): ("agree", "disagree"),
}
RETIRED = {"retire_wrong": "retired_wrong", "retire_outdated": "retired_outdated"}
DECIDED_OUTCOME = {"add": "added", "repeat": "merged", "reject": "rejected", "keep": "kept", "change": "changed",
                   "retire_wrong": "retired_wrong", "retire_outdated": "retired_outdated"}
ACT_COLUMNS = ("act_id", "item_id", "act", "stage", "outcome", "repeat_of", "change", "reason", "actor",
               "actor_name", "actor_role", "actor_region", "acted_at", "public_from")
VERSION_COLUMNS = ("lesson_id", "version", "statement", "risk_factors", "stage", "kind", "edition_key",
                   "project_id", "state", "change_kind", "was", "now", "reason", "item_id", "decided_on",
                   "decided_by", "decided_by_name", "recommended_by", "recommended_by_name", "recommended_reason",
                   "published_on", "days_from_publication", "public_from")
SOURCE_COLUMNS = ("lesson_id", "version", "proposal_id", "item_id", "public_from")
ITEM_COLUMNS = ("item_id", "kind", "proposal_id", "lesson_id", "version", "decided_item_id", "project_id", "region",
                "decided_region", "origin", "origin_by", "origin_by_name", "origin_reason", "origin_item_id",
                "entered_on", "due_on", "created_at", "public_from")
TAGS = ("statement", "risk_factors", "stage", "kind")
TAG_COLUMNS = ("lesson_id", "version", "categories", "methods", "public_from")  # strata.ops.lesson_version_tags


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


def _iso(value) -> str | None:
    day = _date(value)
    return day.isoformat() if day else None


def _moment(value) -> dt.datetime | None:
    """A timestamp in UTC: DuckDB gives a datetime, the warehouse text such as 2026-10-27T14:00:00.000Z."""
    if value is None or value == "":
        return None
    found = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value))
    return found if found.tzinfo else found.replace(tzinfo=dt.UTC)


def _bool(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def _json(value, default):
    try:
        return json.loads(value) if value else default
    except ValueError:
        return default


@cache
def lesson_words() -> dict:
    """copy.lessons.server in web/src/copy.ts, as web/lint/server-copy.ts copied it."""
    return json.loads((resources.files("strata.knowledge.lessons") / "copy.json").read_text())


# ── The business-day clock ───────────────────────────────────────────────

def business_day(day: dt.date, holidays: frozenset[dt.date]) -> bool:
    return day.weekday() < 5 and day not in holidays


def business_days_between(start: dt.date, end: dt.date, holidays: frozenset[dt.date]) -> int:
    """How many business days there are from start to end, both included."""
    count, day = 0, start
    while day <= end:
        count += business_day(day, holidays)
        day += dt.timedelta(days=1)
    return count


def nth_business_day(start: dt.date, n: int, holidays: frozenset[dt.date]) -> dt.date:
    """The nth business day counting from start: day 1 is start itself, or the next business day after it."""
    day, counted = start, 0
    while True:
        if business_day(day, holidays):
            counted += 1
            if counted == n:
                return day
        day += dt.timedelta(days=1)


# ── IEG's part in the evidence ───────────────────────────────────────────

# The four values, in order of the evidence's strength: IEG wrote it, IEG restated it, IEG's review is out and
# did not restate it, IEG has not reviewed the project yet. get_lessons ranks by this order (strata.tools.get_lessons).
IEG_STATUSES = ("ieg_lesson", "restated", "not_restated", "awaiting")


def ieg_status(evidence: list[dict], reviewed_on) -> dict:
    """Which of the four evidence badges a lesson shows (the 29 brief, section 4.4): ieg_lesson ("IEG's
    lesson") when IEG wrote its evidence, restated ("Restated by IEG") when an ICR Review or PPAR restated it,
    not_restated ("Rests on the ICR alone") when IEG's review is out and did not, with that review's date, and
    awaiting ("Awaiting IEG review") when IEG has not reviewed the project yet. One field covers all four, so
    ticket 30 reads the same contract."""
    if any(row["role"] == "source" and _bool(row["restated_by_ieg"]) for row in evidence):
        return {"ieg_status": "ieg_lesson", "review_date": None}
    if any(row["role"] == "restatement" for row in evidence):
        return {"ieg_status": "restated", "review_date": None}
    if reviewed_on:
        return {"ieg_status": "not_restated", "review_date": _iso(reviewed_on)}
    return {"ieg_status": "awaiting", "review_date": None}


# ── The excerpt an evidence card shows ───────────────────────────────────

SENTENCE_END = re.compile(r"(?<=[.;:?])\s+(?=[A-Z(\"“‘])")
OWN_NUMBER = re.compile(r"\d+(\.\d+)*\.\s+")  # a paragraph's own number, "54. ", which its title already gives


def excerpt(text: str, span) -> dict | None:
    """The quote with at most one whole sentence before it and one after it, from the same passage, and where
    the quote sits in it (the 29 brief, section 2.5). None when the quote was not found in the passage."""
    if not text or not span:
        return None
    starts = [0] + [match.end() for match in SENTENCE_END.finditer(text)]
    first = max((index for index, start in enumerate(starts) if start <= span[0]), default=0)
    last = max((index for index, start in enumerate(starts) if start < span[1]), default=first)
    begin = starts[max(first - 1, 0)]
    end = starts[last + 2] if last + 2 < len(starts) else len(text)
    starts_inside = begin > 0
    if not starts_inside and (number := OWN_NUMBER.match(text)) and number.end() <= span[0]:
        begin = number.end()  # the quote never holds the number, so its highlight only moves
    shown = text[begin:end].rstrip()
    return {"text": shown, "highlight": [span[0] - begin, span[1] - begin], "starts_inside": starts_inside,
            "ends_inside": end < len(text)}


# ── Refusals ─────────────────────────────────────────────────────────────

@dataclass
class Refused(Exception):
    """An act the server will not take: its HTTP status, its reason code and the values its sentence names,
    and for a stale act, the item as it is now."""

    status: int
    code: str
    values: dict = field(default_factory=dict)
    item: dict | None = None

    def body(self) -> dict:
        found = {"code": self.code, "values": self.values}
        return found | ({"item": self.item} if self.item is not None else {})


# ── What the store holds ─────────────────────────────────────────────────

class Store:
    """Everything the review pages read, loaded once for a request. Each table is small: a queue, its acts,
    and the lessons the library holds."""

    def __init__(self, engine: Engine):
        self.items = {row["item_id"]: row for row in _rows(engine, "review_items")}
        self.acts: dict[str, list[dict]] = {}
        for row in _rows(engine, "review_acts"):
            self.acts.setdefault(row["item_id"], []).append(row)
        self.versions: dict[str, list[dict]] = {}
        for row in _rows(engine, "lesson_versions"):
            self.versions.setdefault(row["lesson_id"], []).append(row)
        self.sources: dict[str, list[dict]] = {}
        for row in _rows(engine, "lesson_sources"):
            self.sources.setdefault(row["lesson_id"], []).append(row)
        self.proposals = {row["proposal_id"]: row for row in _rows(engine, "proposals")}
        self.evidence: dict[str, list[dict]] = {}
        for row in _rows(engine, "proposal_evidence"):
            self.evidence.setdefault(row["proposal_id"], []).append(row)
        self.projects = {row["project_id"]: row for row in _rows(engine, "lesson_projects", types=",".join(IEG_TYPES))}
        self.notes: dict[str, dict] = {}  # the lesson review writer's newest note on each item
        for row in _rows(engine, "review_notes"):
            self.notes[row["item_id"]] = row

    def act(self, item: dict, verb: str) -> dict | None:
        """The act of this kind that counts: the first written, as act_taken.sql reads it. insert_act.sql keeps one act
        of each kind on an item, so a second is only ever one that lost a race (ticket 29's review round 3, P2)."""
        found = [act for act in self.acts.get(item["item_id"], []) if act["act"] == verb]
        return found[0] if found else None

    def written_by(self, lesson_id: str | None, item_id: str) -> dict | None:
        """The version of a lesson an item's decision wrote, or None for a decision that wrote none, such as a keep."""
        return next((row for row in self.versions.get(lesson_id or "", []) if row["item_id"] == item_id), None)

    def version_at(self, lesson_id: str | None, moment) -> int | None:
        """The version a lesson held at a moment: the newest whose own decision was made on or before it (ticket 29's
        review round 3, P1). A version whose item the queue no longer lists counts from its day."""
        at = _moment(moment)
        held = None
        for row in self.versions.get(lesson_id or "", []):
            item = self.items.get(row["item_id"])
            decision = self.act(item, "decide") if item else None
            made = _moment(decision["acted_at"]) if decision else None
            if (made <= at) if made else (_date(row["decided_on"]) <= at.date()):
                held = _int(row["version"])
        return held

    def stage(self, item: dict) -> str:
        """recommendation, decision, cross_check or decided, from the acts on the item."""
        if item["kind"] == "cross_check":
            return "decided" if self.act(item, "cross_check") else "cross_check"
        if self.act(item, "decide"):
            return "decided"
        return "decision" if self.act(item, "recommend") else "recommendation"

    def latest(self, lesson_id: str) -> dict | None:
        versions = self.versions.get(lesson_id)
        return versions[-1] if versions else None

    def at(self, lesson_id: str, version: int | None) -> dict | None:
        found = [row for row in self.versions.get(lesson_id, []) if _int(row["version"]) == version]
        return found[0] if found else self.latest(lesson_id)

    def lesson_proposals(self, lesson_id: str, version: int | None = None) -> list[str]:
        return [row["proposal_id"] for row in self.sources.get(lesson_id, [])
                if version is None or _int(row["version"]) <= version]

    def open_recheck(self, lesson_id: str) -> dict | None:
        return next((item for item in self.items.values() if item["kind"] == "recheck"
                     and item["lesson_id"] == lesson_id and self.stage(item) != "decided"), None)

    def note(self, item: dict) -> dict | None:
        """The writer's newest note on the item, its content read from JSON, or None while it is still writing."""
        found = self.notes.get(item["item_id"])
        if found is None:
            return None
        return {"status": found["status"], **(_json(found["content"], {}) or {})}

    def repeats(self, item: dict) -> list[dict]:
        """The current lessons the writer named as likely repeats of the item, with its kept sentences."""
        note = self.note(item) or {}
        return [repeat for repeat in note.get("repeats") or []
                if (self.latest(repeat["lesson_id"]) or {}).get("state") == "current"]

    def lesson_of(self, item: dict) -> str | None:
        """The lesson an item is about: a re-check's or cross-check's own, or the one a new lesson became."""
        if item["lesson_id"]:
            return item["lesson_id"]
        for lesson_id, sources in self.sources.items():
            if any(source["item_id"] == item["item_id"] for source in sources):
                return lesson_id
        return None


# ── The service ──────────────────────────────────────────────────────────

def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class LessonReview:
    """The review pages' reads and the reviewers' acts. It keeps the roles file and the settings, never a viewer;
    each call gets the engine that runs as the viewer who asked."""

    def __init__(self, roles: Roles, today: Callable[[], dt.date] | None = None,
                 now: Callable[[], dt.datetime] = _now, thresholds: Thresholds | None = None,
                 lists: LessonLists | None = None, editions: Editions | None = None):
        self.roles, self.now = roles, now
        self.today = today or (lambda: self.now().date())
        self.thresholds = thresholds or load_thresholds()
        self.lists, self.editions = lists or load_lesson_lists(), editions or load_editions()

    def value(self, name: str):
        return self.thresholds.value(f"lesson_review.{name}")

    @property
    def holidays(self) -> frozenset[dt.date]:
        return frozenset(self.value("holidays"))

    def reviewer(self, viewer: Viewer) -> Person | None:
        person = self.roles.person(viewer.email)
        return person if person is not None and PAGE in person.pages(self.roles) else None

    def _require(self, viewer: Viewer) -> Person:
        person = self.reviewer(viewer)
        if person is None:
            raise Refused(403, "not_a_reviewer")
        return person

    # ── Who may act ──────────────────────────────────────────────────────

    def _free_lead(self, store: Store, item: dict, recommender: str | None) -> bool:
        return any("decide" in person.acts(self.roles) and item["region"] in person.regions
                   and item["project_id"] not in person.projects and person.email.lower() != (recommender or "").lower()
                   for person in self.roles.people)

    def can(self, store: Store, item: dict, person: Person | None) -> dict:
        """What the viewer may do with the item now ({"act": verb}), or why not (a reason code and the values
        its sentence names)."""
        def no(code: str | None, **values) -> dict:
            return {"act": None, "reason_code": code, "values": values}

        if person is None:
            return no("not_a_reviewer")
        stage = store.stage(item)
        if stage == "decided":
            return no(None)
        acts = person.acts(self.roles)
        project = store.projects.get(item["project_id"], {})
        mine = {"project_name": project.get("project_name"), "pid": item["project_id"]}
        if stage == "cross_check":
            if item["decided_region"] in person.regions:
                return no("same_region", decided_region=item["decided_region"])
            if item["region"] not in person.regions or "cross_check" not in acts:
                return no("other_region", region=item["region"])
            return {"act": "cross_check", "reason_code": None, "values": {}}
        if item["region"] not in person.regions:
            return no("other_region", region=item["region"])
        if stage == "recommendation":
            if item["project_id"] in person.projects:
                return no("own_project", **mine)
            return {"act": "recommend", "reason_code": None, "values": {}}
        recommender = (store.act(item, "recommend") or {}).get("actor")
        if "decide" not in acts:
            # Someone who can't decide is told whether any lead can (the 29 brief, section 5.4).
            free = self._free_lead(store, item, recommender)
            return no("not_a_lead") if free else no("no_lead_free", region=item["region"], **mine)
        if (recommender or "").lower() == person.email.lower():
            return no("same_person")
        if item["project_id"] in person.projects:
            return no("own_project", **mine)
        return {"act": "decide", "reason_code": None, "values": {}}

    # ── Shapes the pages read ────────────────────────────────────────────

    def evidence_row(self, store: Store, row: dict, detail: bool = False) -> dict:
        template = template_for(row["document_type"] or "")
        short = template.short_name if template else row["document_type"]
        project = row["project_id"]
        found = {
            "evidence_id": f"strata.gold.passage:{row['passage_id']}", "passage_id": row["passage_id"],
            "role": row["role"], "doc_type": row["document_type"], "doc_short": short, "pid": project,
            "project_name": (store.projects.get(project) or {}).get("project_name"),
            "date": _iso(row["document_date"]), "report_number": row["report_number"],
            "locator": {"kind": "section" if short == "ICR Review" else "paragraph", "text": row["paragraph"]},
            "page": _int(row["cited_page"]), "quote": row["quote"], "restated_by_ieg": _bool(row["restated_by_ieg"]),
        }
        text = row.get("passage_text") or ""
        span = find_quote(row["quote"], text) if text else None
        # The quote's place in its passage's words, so the evidence drawer opens with it highlighted.
        found["highlight"] = list(span) if span else None
        if detail:
            found |= {"text": text, "language": row.get("language"), "excerpt": excerpt(text, span)}
        return found

    def ieg(self, store: Store, evidence: list[dict], project_id: str) -> dict:
        return ieg_status(evidence, (store.projects.get(project_id) or {}).get("ieg_reviewed_on"))

    def tags(self, row: dict) -> dict:
        factors = _json(row["risk_factors"], [])
        return {
            "risk_factors": [{"key": key, "label": item.label} for key in factors
                             if (item := self.lists.risk_factor(key))],
            "stage": self._item(self.lists.stage(row["stage"])), "kind": self._item(self.lists.kind(row["kind"])),
            "edition": self._edition(row.get("edition_key")),
            # Ticket 39: procurement categories and selection methods, from the package form's lists.
            "categories": [{"key": key, "label": lesson_tags.label("categories", key)} for key in _json(row.get("categories"), [])],
            "methods": [{"key": key, "label": lesson_tags.label("methods", key)} for key in _json(row.get("methods"), [])],
        }

    @staticmethod
    def _item(found) -> dict | None:
        return {"key": found.key, "label": found.label} if found else None

    def _edition(self, key: str | None) -> dict | None:
        found = self.editions.get(key)
        return {"key": found.key, "name": found.name, "short": found.short} if found else None

    def _proposal_evidence(self, store: Store, proposal_ids: Iterable[str]) -> list[dict]:
        rows = [row for proposal_id in proposal_ids for row in store.evidence.get(proposal_id, [])]
        seen, unique = set(), []
        for row in rows:  # two merged proposals may share a restatement
            if row["passage_id"] not in seen:
                seen.add(row["passage_id"])
                unique.append(row)
        # In the order the lesson gained them: the first proposal's quote and IEG's restatement of it, then each
        # merged proposal's, so a lesson's first quote stays its own.
        return unique

    def subject(self, store: Store, item: dict) -> dict:
        """What an item is about: its statement, tags, evidence rows and project, at the version it concerns."""
        if item["kind"] == "new" or (item["kind"] == "cross_check" and not item["lesson_id"]):
            # A new lesson, or the cross-check of a decision that rejected one: the proposal itself.
            proposal = store.proposals.get(item["proposal_id"]) or {}
            rows = self._proposal_evidence(store, [item["proposal_id"]])
            return {"statement": proposal.get("statement"), "row": proposal, "evidence": rows,
                    "project_id": item["project_id"], "version": None, "lesson_id": store.lesson_of(item)}
        lesson_id = item["lesson_id"]
        concerns = self._recheck_version(store, item) if item["kind"] == "recheck" else _int(item["version"])
        version = store.at(lesson_id, concerns) or {}
        rows = self._proposal_evidence(store, store.lesson_proposals(lesson_id, _int(version.get("version"))))
        return {"statement": version.get("statement"), "row": version, "evidence": rows,
                "project_id": version.get("project_id") or item["project_id"],
                "version": _int(version.get("version")), "lesson_id": lesson_id}

    @staticmethod
    def _recheck_version(store: Store, item: dict) -> int | None:
        """The version a re-check is about (ticket 29's review round 3, P1). A lead may merge a proposal into a lesson
        while its re-check is open, so an open re-check reads the version the lesson holds now, and a decided one the
        version the lesson held when the lead decided: the one its own decision replaced, or the one it kept."""
        lesson_id = item["lesson_id"]
        decision = store.act(item, "decide")
        if decision is None:
            latest = store.latest(lesson_id)
            return _int(latest["version"]) if latest else _int(item["version"])
        written = store.written_by(lesson_id, item["item_id"])
        if written is not None:
            return _int(written["version"]) - 1
        return store.version_at(lesson_id, decision["acted_at"]) or _int(item["version"])

    def clock(self, store: Store, item: dict) -> dict | None:
        if store.stage(item) == "decided":
            return None
        today = self.today()
        if item["kind"] == "cross_check":
            due = _date(item["due_on"])
            return {"day": None, "limit_days": None, "start_on": _iso(item["entered_on"]), "due_on": _iso(due),
                    "overdue_days": business_days_between(due + dt.timedelta(days=1), today, self.holidays)
                    if due and today > due else 0, "last_day": due == today}
        limit = int(self.value("business_days"))
        start = _date(item["entered_on"])
        due = nth_business_day(start, limit, self.holidays)
        day = max(1, business_days_between(start, today, self.holidays))
        overdue = business_days_between(due + dt.timedelta(days=1), today, self.holidays) if today > due else 0
        return {"day": min(day, limit), "limit_days": limit, "start_on": _iso(start), "due_on": _iso(due),
                "overdue_days": overdue, "last_day": due == today}

    def _act(self, act: dict | None) -> dict | None:
        if act is None:
            return None
        return {"name": act["actor_name"], "role": act["actor_role"], "phrase": act["outcome"],
                "on": _iso(act["acted_at"]), "reason": act["reason"], "region": act["actor_region"],
                "repeat_of": act["repeat_of"], "change": _json(act["change"], None)}

    def row(self, store: Store, item: dict, person: Person | None) -> dict:
        """One queue row: what the item is, where it came from, its clock, who acts next or why not you."""
        subject = self.subject(store, item)
        first = subject["evidence"][0] if subject["evidence"] else None
        can = self.can(store, item, person)
        project = store.projects.get(subject["project_id"]) or {}
        origin = None
        if item["kind"] == "recheck" or (item["kind"] == "new" and item["origin"] == "cross_check"):
            origin = {"kind": item["origin"], "name": item["origin_by_name"], "on": _iso(item["entered_on"]),
                      "reason": item["origin_reason"],
                      "region": (store.items.get(item["origin_item_id"]) or {}).get("region")}
        decided = None
        if item["kind"] == "cross_check":
            checked = store.items.get(item["decided_item_id"]) or {}
            decision = store.act(checked, "decide") if checked else None
            decided = {"region": item["decided_region"], "on": _iso(decision["acted_at"]) if decision else None}
        return {
            "item_id": item["item_id"], "kind": item["kind"], "stage": store.stage(item),
            "group": "you" if can["act"] else "others", "statement": subject["statement"],
            "source": self.evidence_row(store,first) if first else None, "region": item["region"],
            "project": {"pid": subject["project_id"], "name": project.get("project_name"),
                        "country": project.get("country_name"), "sector": project.get("sector_name")},
            **self.ieg(store,subject["evidence"], subject["project_id"]),
            "may_repeat": item["kind"] == "new" and bool(store.repeats(item)),
            "clock": self.clock(store, item), "recommendation": self._act(store.act(item, "recommend")),
            "origin": origin, "decided": decided, "can": can,
        }

    # ── Reads ────────────────────────────────────────────────────────────

    def _load(self, engine: Engine) -> Store:
        return Store(engine)

    def _waiting(self, store: Store, person: Person) -> int:
        return sum(item["region"] in person.regions and store.stage(item) != "decided" for item in store.items.values())

    def me(self, engine: Engine, viewer: Viewer) -> dict:
        person = self.reviewer(viewer)
        if person is None:
            return {"signed_in": viewer.signed_in, "tabs": ["library"], "acts": [], "regions": [], "role": None,
                    "waiting": None, "limit_days": None}
        store = self._load(engine)
        # The queue's purpose names the regions and the day limit, so it shows while the queue itself loads.
        return {"signed_in": True, "tabs": ["library", "review"], "acts": list(person.acts(self.roles)),
                "regions": list(person.regions), "role": person.role(self.roles), "waiting": self._waiting(store, person),
                "limit_days": int(self.value("business_days"))}

    def queue(self, engine: Engine, viewer: Viewer, page: int = 1) -> dict:
        person = self._require(viewer)
        store = self._load(engine)
        mine = [item for item in store.items.values() if item["region"] in person.regions]
        rows = [self.row(store, item, person) for item in mine if store.stage(item) != "decided"]
        decided = self._decided(store, person)
        size = int(self.value("decided_page_size"))
        pages = max(1, -(-len(decided) // size))
        page = min(max(page, 1), pages)
        shown = decided[(page - 1) * size: page * size]
        groups = {group: sorted((row for row in rows if row["group"] == group),
                                key=lambda row: ((row["clock"] or {}).get("start_on") or "", row["item_id"]))
                  for group in ("you", "others")}
        return {
            "as_of": self.today().isoformat(), "limit_days": int(self.value("business_days")),
            "regions": list(person.regions), "waiting": len(rows),
            "lead": self.lead(groups) if rows else None, "check": self.quote_check(store),
            "groups": groups,
            "decided": {"window_days": int(self.value("decided_window_days")), "total": len(decided), "page": page,
                        "pages": pages, "from": (page - 1) * size + 1 if shown else 0,
                        "to": (page - 1) * size + len(shown), "rows": shown},
        }

    def lead(self, groups: dict[str, list[dict]]) -> list[dict]:
        """The queue's lead sentence as segments (the 29 brief, section 5.3): how many items wait for you and for
        other reviewers, then how much of its limit the oldest has used, or how many are overdue. The server
        chooses each count's form, and each number is a segment the page writes with Num, as ticket 16's
        headline does (strata.tools.data_readiness_for.fill)."""
        words, forms = lesson_words()["lead"], lesson_words()["forms"]
        you, others = len(groups["you"]), len(groups["others"])
        limit = int(self.value("business_days"))

        def form(name: str, count: int) -> str:
            return forms[name]["one" if count == 1 else "many"]

        slots = {"you": {"number": you, "capital": True}, "lessonsYou": form("lesson", you), "beYou": form("be", you),
                 "others": {"number": others, "capital": you == 0}, "lessonsOthers": form("lesson", others),
                 "beOthers": form("be", others), "limit": {"number": limit}}
        template = words["both"] if you and others else words["youOnly"] if you else words["othersOnly"]
        segments = fill(template, slots)
        rows = groups["you"] + groups["others"]
        overdue = sum(1 for row in rows if (row["clock"] or {}).get("overdue_days"))
        if overdue:
            segments += fill(words["overdue"], {"overdue": {"number": overdue, "capital": True},
                                                "have": form("have", overdue), "itsTheir": form("itsTheir", overdue),
                                                "limit": {"number": limit}})
        else:
            days = [row["clock"]["day"] for row in rows if row["clock"] and row["clock"].get("day")]
            if days:
                segments += fill(words["oldest"], {"day": {"number": max(days)}, "limit": {"number": limit}})
        return segments

    def quote_check(self, store: Store) -> dict:
        """How many proposed lessons the quote check dropped in the last quote_check_window_days days, as a
        sentence in segments, and the Data readiness page's sources for its link (the 29 brief, section 5.3)."""
        window = int(self.value("quote_check_window_days"))
        since = self.today() - dt.timedelta(days=window)
        recent = [row for row in store.proposals.values() if (_date(row["proposed_on"]) or since) >= since]
        dropped = sum(1 for row in recent if row["quote_check"] != PASSED)
        words, forms = lesson_words()["check"], lesson_words()["forms"]
        many = "one" if dropped == 1 else "many"
        segments = (fill(words["dropped"], {"days": {"number": window}, "dropped": {"number": dropped},
                                            "lessons": forms["lesson"][many], "itsTheir": forms["itsTheir"][many]})
                    if dropped else fill(words["none"], {"days": {"number": window}}))
        return {"window_days": window, "proposed": len(recent), "dropped": dropped, "segments": segments,
                "readiness": {"sources": ["documents"], "from": "get_lessons"}}

    def _decided(self, store: Store, person: Person) -> list[dict]:
        """The decisions of the last decided_window_days days in the viewer's regions, newest first."""
        since = self.today() - dt.timedelta(days=int(self.value("decided_window_days")))
        found = []
        for item in store.items.values():
            decision = store.act(item, "decide")
            if item["kind"] == "cross_check" or decision is None or item["region"] not in person.regions:
                continue
            on = _date(decision["acted_at"])
            if on < since:
                continue
            subject = self.subject(store, item)
            lesson_id = store.lesson_of(item) or decision["repeat_of"]
            version = store.written_by(lesson_id, item["item_id"])
            published = _date((store.proposals.get(item["proposal_id"]) or {}).get("report_public_on"))
            found.append({
                "item_id": item["item_id"], "kind": item["kind"], "statement": subject["statement"],
                "pid": subject["project_id"], "project_name": (store.projects.get(subject["project_id"]) or {}).get(
                    "project_name"), "outcome": DECIDED_OUTCOME[decision["outcome"]],
                "version": _int(version["version"]) if version else subject["version"], "decided_on": on.isoformat(),
                "decided_at": decision["acted_at"],
                "days_from_publication": (on - published).days if item["kind"] == "new" and published else None,
                "published_on": _iso(published) if item["kind"] == "new" else None})
        found.sort(key=lambda row: (row["decided_at"], row["item_id"]), reverse=True)
        return [{key: value for key, value in row.items() if key != "decided_at"} for row in found]

    def item(self, engine: Engine, viewer: Viewer, wanted: str) -> dict:
        person = self._require(viewer)
        store = self._load(engine)
        item = store.items.get(wanted)
        if item is None:
            raise Refused(404, "unknown_item", {"item_id": wanted})
        return self.detail(store, item, person)

    def detail(self, store: Store, item: dict, person: Person | None) -> dict:
        """The review page: the row, then the evidence in full, the tags, the history and the outcome."""
        row = self.row(store, item, person)
        subject = self.subject(store, item)
        project = store.projects.get(subject["project_id"]) or {}
        ieg = self.ieg(store,subject["evidence"], subject["project_id"])
        tags = self.tags(subject["row"]) if subject["row"] else {}
        return {
            **row, "read_only": row["can"]["act"] is None,
            "evidence": [self.evidence_row(store,evidence, detail=True) for evidence in subject["evidence"]],
            "ieg_note": {"kind": "awaiting"} if ieg["ieg_status"] == "awaiting" else
                        {"kind": "alone", "review_date": ieg["review_date"]} if ieg["ieg_status"] == "not_restated"
                        else None,
            "tags": {**tags, "sector": project.get("sector_name")},
            "lesson": {"lesson_id": subject["lesson_id"], "version": subject["version"],
                       "next_version": self._next_version(store, item["lesson_id"]) if item["kind"] == "recheck" else None},
            "summary": self.summary(store, item), "repeats": self.likely_repeats(store, item),
            "history": self.history(store, item),
            "outcome": self.outcome(store, item), "lists": {**self.lists.as_dict(), **lesson_tags.as_dict()},
            "limits": {"reason_max_chars": int(self.value("reason_max_chars")),
                       "statement_max_chars": int(self.value("statement_max_chars")),
                       "sample_percent": round(float(self.value("cross_check_share")) * 100),
                       "summary_poll_seconds": int(self.value("summary_poll_seconds")),
                       "summary_poll_minutes": int(self.value("summary_poll_minutes"))},
        }

    def summary(self, store: Store, item: dict) -> dict:
        """The writer's verified summary of the evidence (the 29 brief, section 5.7): writing until its note
        is stored; then ready, nothing_to_add, nothing_survived or failed, with the kept sentences, the
        evidence they cite, the verifier's counts, the removed sentences, and the disagreements check 6 attached
        (ticket 61), each under the sentence it concerns."""
        note = store.note(item)
        if note is None:
            return {"status": "writing"}
        return {"status": note["status"], "sentences": note.get("sentences", []), "evidence": note.get("evidence", {}),
                "checks": note.get("checks"),
                "removed": note.get("removed", []), "disagreements": note.get("disagreements", [])}

    def likely_repeats(self, store: Store, item: dict) -> list[dict]:
        """Each current lesson the writer said the item may repeat, as a compact card with the writer's kept
        sentences about it. New lessons only (the 29 brief, section 5.8)."""
        if item["kind"] != "new":
            return []
        return [{**self.card(store, repeat["lesson_id"]), "sentences": repeat["sentences"],
                 "next_version": self._next_version(store, repeat["lesson_id"])}
                for repeat in store.repeats(item)]

    @staticmethod
    def _next_version(store: Store, lesson_id: str | None) -> int | None:
        """The version a decision that changes the lesson now would write: its newest plus one."""
        latest = store.latest(lesson_id) if lesson_id else None
        return _int(latest["version"]) + 1 if latest else None

    def history(self, store: Store, item: dict) -> list[dict]:
        """What happened to the item, in order, each event in the past tense."""
        events = []
        if item["kind"] == "cross_check":
            checked = store.items.get(item["decided_item_id"])
            events += self.history(store, checked) if checked else []
        elif item["kind"] == "new":
            proposal = store.proposals.get(item["proposal_id"]) or {}
            template = template_for(proposal.get("document_type") or "")
            events.append({"event": "proposed", "on": _iso(proposal.get("proposed_on")),
                           "doc_short": template.short_name if template else proposal.get("document_type"),
                           "pid": item["project_id"],
                           "project_name": (store.projects.get(item["project_id"]) or {}).get("project_name"),
                           "published_on": _iso(proposal.get("report_public_on"))})
            for evidence in store.evidence.get(item["proposal_id"], []):
                if evidence["role"] == "restatement":
                    events.append({"event": "restatement", "on": _iso(proposal.get("proposed_on")),
                                   "review_date": _iso(evidence["document_date"]),
                                   "doc_short": template_for(evidence["document_type"]).short_name})
        if item["kind"] == "recheck" or (item["kind"] == "new" and item["origin"] == "cross_check"):
            events.append({"event": {"asked": "recheck_asked", "edition": "recheck_edition"}.get(item["origin"],
                                                                                               "recheck_cross_check"),
                           "on": _iso(item["entered_on"]), "name": item["origin_by_name"],
                           "reason": item["origin_reason"]})
        for act in store.acts.get(item["item_id"], []):
            event = {"recommend": "recommended", "decide": "decided", "cross_check": "cross_checked"}[act["act"]]
            entry = {"event": event, "on": _iso(act["acted_at"]), "name": act["actor_name"], "role": act["actor_role"],
                     "region": act["actor_region"], "outcome": act["outcome"], "reason": act["reason"],
                     "changes": self._changes(store, item, act)}
            if act["act"] == "decide":
                lesson_id = act["repeat_of"] or store.lesson_of(item)
                version = store.written_by(lesson_id, item["item_id"])
                # A kept lesson writes no version, so its record names the version the lesson held when it was kept.
                entry["version"] = _int(version["version"]) if version else self._held(store, item, lesson_id, act)
                target = store.latest(act["repeat_of"]) if act["repeat_of"] else None
                entry["target"] = target["statement"] if target else None
            events.append(entry)
        return events

    @staticmethod
    def _held(store: Store, item: dict, lesson_id: str | None, decision: dict) -> int | None:
        """The version a decision that wrote none, such as a keep, left the lesson at: the one it held at that moment,
        which a merge during an open re-check may have moved past the version the re-check was asked on."""
        return store.version_at(lesson_id, decision["acted_at"]) or _int(item["version"])

    def _changes(self, store: Store, item: dict, act: dict) -> list[dict]:
        """The fields an act changed, each with its was and now, for the history's Was and Now lines."""
        if act["act"] == "decide":
            version = store.written_by(act["repeat_of"] or store.lesson_of(item), item["item_id"])
            if version is None or not version["was"]:
                return []
            was, now = _json(version["was"], {}), _json(version["now"], {})
            # A retirement's state is in the decided sentence already ("retired it because ..."), so no Was and Now.
            return [{"field": key, "was": was.get(key), "now": now.get(key)} for key in now
                    if key != "state" and was.get(key) != now.get(key)]
        change = _json(act["change"], None)
        if not change:
            return []
        current = self.subject(store, item)["row"] or {}
        was = {key: current.get(key) if key != "risk_factors" else _json(current.get(key), []) for key in TAGS}
        return [{"field": key, "was": was.get(key), "now": change.get(key)} for key in TAGS
                if key in change and change.get(key) != was.get(key)]

    def outcome(self, store: Store, item: dict) -> dict | None:
        """A decided item's result, for the outcome panel on its record."""
        if item["kind"] == "cross_check":
            check = store.act(item, "cross_check")
            return None if check is None else {"outcome": check["outcome"], "on": _iso(check["acted_at"]),
                                               "decided_region": item["decided_region"]}
        decision = store.act(item, "decide")
        if decision is None:
            return None
        lesson_id = decision["repeat_of"] or store.lesson_of(item)
        version = store.written_by(lesson_id, item["item_id"])
        target = store.latest(decision["repeat_of"]) if decision["repeat_of"] else None
        published = _date((store.proposals.get(item["proposal_id"]) or {}).get("report_public_on"))
        on = _date(decision["acted_at"])
        written = _int(version["version"]) if version else None
        return {"outcome": DECIDED_OUTCOME[decision["outcome"]], "on": on.isoformat(), "lesson_id": lesson_id,
                "version": written if written else self._held(store, item, lesson_id, decision),
                # The version a change or a retirement leaves on record: the one before the version it wrote.
                "previous_version": written - 1 if written and written > 1 else None,
                "target": target["statement"] if target else None,
                "days_from_publication": (on - published).days if item["kind"] == "new" and published else None,
                "published_on": _iso(published)}

    # ── The library ──────────────────────────────────────────────────────

    def card(self, store: Store, lesson_id: str) -> dict:
        """One lesson card, naming roles and never people (the 29 brief, section 4.1). A retired lesson's card says
        when and why a lead retired it, by role (ticket 39)."""
        latest = store.latest(lesson_id)
        retired = latest["state"] in RETIRED.values()
        evidence = self._proposal_evidence(store, store.lesson_proposals(lesson_id))
        project = store.projects.get(latest["project_id"]) or {}
        recheck = store.open_recheck(lesson_id)
        first = next((row for row in evidence if row["role"] == "source"), None)
        chips_max = int(self.value("card_chips_max"))
        return {
            "lesson_id": lesson_id, "version": _int(latest["version"]), "statement": latest["statement"],
            **self.tags(latest), "sector": project.get("sector_name"), "pid": latest["project_id"],
            **self.ieg(store,evidence, latest["project_id"]), "decided_on": _iso(latest["decided_on"]),
            "state": latest["state"] if retired else "rechecking" if recheck else "current",
            "rechecking_since": _iso(recheck["entered_on"]) if recheck else None,
            "retired": {"as": latest["state"], "on": _iso(latest["decided_on"]), "reason": latest["reason"]}
            if retired else None,
            "region": project.get("region"),
            "quote": first["quote"] if first else None,
            "evidence": [self.evidence_row(store,row) for row in evidence],
            # The most source chips the card shows, and how many fold behind "Show {n} more sources", so the browser
            # holds no threshold and counts nothing (ticket 29's review round 3, P5).
            "chips_max": chips_max, "folded": max(0, len(evidence) - chips_max),
        }

    # Ticket 39: the library's filters. Status sets the population; stage, method and sector narrow it.
    STATUSES = ("current", "rechecking", "retired")
    NARROWING = ("stage", "method", "sector")

    def library(self, engine: Engine, viewer: Viewer, page: int = 1, filters: dict | None = None,
                show: str | None = None, store: Store | None = None) -> dict:
        """The library, newest decision first, by date and never by use, eight cards a page (the 39 brief, section
        4.8). Status sets the population: current (the default, with lessons being re-checked), being re-checked, or
        retired, which only that status shows. Stage, method and sector narrow it; a lesson that names no method
        applies to every method, so each method keeps it. A proposed lesson is never in the library, for anyone.
        show opens the page that holds a lesson, under the status that holds it and no other filter. A filter value
        no closed list holds is left out, and unknown_filter says so. The count line is built here, with each
        count's form, so "N of M" always compares like with like."""
        store = store or self._load(engine)
        asked = {key: (value or None) for key, value in (filters or {}).items()}
        latest = {lesson_id: versions[-1] for lesson_id, versions in store.versions.items()}

        def status_of(row: dict) -> str:
            if row["state"] != "current":
                return "retired"
            return "rechecking" if store.open_recheck(row["lesson_id"]) else "current"

        def decided_at(row: dict) -> str:
            act = store.act(store.items.get(row["item_id"]) or {"item_id": row["item_id"]}, "decide")
            return str(act["acted_at"]) if act else ""

        ordered = sorted(latest.values(), key=lambda row: (_iso(row["decided_on"]), decided_at(row), row["lesson_id"]),
                         reverse=True)
        sectors = sorted({(store.projects.get(row["project_id"]) or {}).get("sector_name") for row in ordered} - {None})
        options = {"stage": [item.key for item in self.lists.stages], "method": [key for key, _ in lesson_tags.options("methods")],
                   "sector": sectors, "status": list(self.STATUSES)}
        unknown = any(value is not None and value not in options[key] for key, value in asked.items() if key in options)
        chosen = {key: asked.get(key) if asked.get(key) in options[key] else None for key in options}
        shown_id = show if show in latest else None
        if shown_id:
            chosen = {key: None for key in options}
            chosen["status"] = "retired" if status_of(latest[shown_id]) == "retired" else "current"
        status = chosen["status"] or "current"

        def in_status(row: dict) -> bool:
            found = status_of(row)
            return found == "retired" if status == "retired" else found == "rechecking" if status == "rechecking" \
                else found in ("current", "rechecking")

        def narrowed(row: dict) -> bool:
            methods = _json(row.get("methods"), [])
            sector = (store.projects.get(row["project_id"]) or {}).get("sector_name")
            return ((chosen["stage"] is None or row["stage"] == chosen["stage"])
                    and (chosen["method"] is None or not methods or chosen["method"] in methods)
                    and (chosen["sector"] is None or sector == chosen["sector"]))

        population = [row for row in ordered if in_status(row)]
        matching = [row for row in population if narrowed(row)]
        size = int(self.value("library_page_size"))
        pages = max(1, -(-len(matching) // size))
        if shown_id:
            page = next(index // size + 1 for index, row in enumerate(matching) if row["lesson_id"] == shown_id)
        shown = matching[(page - 1) * size: page * size] if 1 <= page <= pages else []
        person = self.reviewer(viewer)
        first, last = ((page - 1) * size + 1 if shown else 0), (page - 1) * size + len(shown)
        return {"as_of": self.today().isoformat(), "page": page, "pages": pages, "page_size": size,
                "total": len(matching), "of": len(population), "from": first, "to": last,
                "status": status, "filters": chosen, "narrowed": any(chosen[key] for key in self.NARROWING),
                "unknown_filter": unknown, "shown": shown_id,
                "options": {key: ([{"key": item.key, "label": item.label} for item in self.lists.stages] if key == "stage"
                                  else [{"key": value, "label": label} for value, label in lesson_tags.options("methods")]
                                  if key == "method" else [{"key": value, "label": value} for value in sectors]
                                  if key == "sector" else [{"key": value} for value in self.STATUSES])
                            for key in options},
                "count": self.count_line(status, len(matching), len(population), first, last, pages,
                                         any(chosen[key] for key in self.NARROWING)),
                "can_recheck": person is not None,
                "limits": {"reason_max_chars": int(self.value("reason_max_chars"))},
                "waiting": self._waiting(store, person) if person else None,
                "lessons": [self.card(store, row["lesson_id"]) for row in shown]}

    @staticmethod
    def count_line(status: str, n: int, m: int, first: int, last: int, pages: int, narrowed: bool) -> list[dict]:
        """The library's count line as segments (the 39 brief, section 5.6): status sets M, the other filters N."""
        found = lesson_words()["count"]
        noun = found["nouns"][status]["one" if m == 1 else "many"]
        numeral = {"from": {"number": first, "numeral": True}, "to": {"number": last, "numeral": True}}
        if narrowed:
            # A part of the whole keeps its numerals, "Showing 1 of 2 current lessons" (DESIGN.md section 7, rule 42, and
            # section 5, Tables; the 58 critique, follow-up 13).
            template = found["narrowedRange"] if pages > 1 else found["narrowed"]
            part = {"n": {"number": n, "numeral": True}, "m": {"number": m, "numeral": True}}
            return fill(template, {**part, "noun": noun, **numeral})
        # "both" for two and "the one" for one, as every count line (ticket 58; DESIGN.md section 5, Tables).
        whole = found["range"] if pages > 1 else found["one"] if m == 1 else found["both"] if m == 2 else found["all"]
        return fill(whole, {"m": {"number": m}, "noun": noun, **numeral})

    # ── Writes ───────────────────────────────────────────────────────────
    #
    # Every write goes through `writer`, the app's own service principal (ops/app/deploy_app.py grants it the
    # five review tables). The server checks the roles file before it writes, and the row names the viewer.

    def _change(self, given, base: dict) -> dict:
        """A lesson editor's change, checked against the closed lists, with every field filled from base."""
        if not isinstance(given, dict):
            raise Refused(422, "bad_change")
        statement = str(given.get("statement", base["statement"]) or "").strip()
        factors = given.get("risk_factors", _json(base["risk_factors"], []))
        stage, kind = given.get("stage", base["stage"]), given.get("kind", base["kind"])
        if not statement or len(statement) > int(self.value("statement_max_chars")):
            raise Refused(422, "bad_change", {"field": "statement"})
        if not isinstance(factors, list) or not factors or not all(self.lists.risk_factor(key) for key in factors):
            raise Refused(422, "bad_change", {"field": "risk_factors"})
        if self.lists.stage(stage) is None or self.lists.kind(kind) is None:
            raise Refused(422, "bad_change", {"field": "stage" if self.lists.stage(stage) is None else "kind"})
        found = {"statement": statement, "risk_factors": factors, "stage": stage, "kind": kind}
        # Ticket 39: procurement categories and selection methods, from the package form's closed lists.
        for name in lesson_tags.LISTS:
            value = given.get(name, _json(base.get(name), []))
            if not lesson_tags.valid(name, value):
                raise Refused(422, "bad_change", {"field": name})
            found[name] = list(value)
        return found

    def act(self, engine: Engine, viewer: Viewer, wanted: str, verb: str, body: dict, writer: Engine) -> dict:
        """One recommendation, decision or cross-check by the viewer, or the reason it is refused. It reads as
        the viewer and writes through writer."""
        person = self._require(viewer)
        store = self._load(engine)
        item = store.items.get(wanted)
        if item is None:
            raise Refused(404, "unknown_item", {"item_id": wanted})
        stage = store.stage(item)
        if body.get("expected_stage") != stage or STAGE_FOR[verb] != stage:
            raise Refused(409, "stale", item=self.detail(store, item, person))
        can = self.can(store, item, person)
        if can["act"] != verb:
            raise Refused(403, can["reason_code"] or "not_allowed", can["values"])
        outcome = ("agree" if body.get("agree") else "disagree") if verb == "cross_check" else body.get("outcome")
        if outcome not in OUTCOMES[(item["kind"], verb)]:
            raise Refused(422, "bad_outcome")
        reason = str(body.get("reason") or "").strip()
        if (not reason and outcome != "agree") or len(reason) > int(self.value("reason_max_chars")):
            raise Refused(422, "no_reason" if not reason else "reason_too_long")
        subject = self.subject(store, item)
        change = None
        if outcome == "change" or (outcome == "add" and verb == "decide" and body.get("change")):
            change = self._change(body.get("change"), subject["row"])
        repeat_of = body.get("repeat_of") if outcome == "repeat" else None
        if outcome == "repeat" and repeat_of not in self.repeats_of(store, item):
            raise Refused(422, "not_a_likely_repeat")
        now = self.now()
        act = {"act_id": uuid.uuid4().hex, "item_id": item["item_id"], "act": verb, "stage": stage,
               "outcome": outcome, "repeat_of": repeat_of, "change": json.dumps(change) if change else None,
               "reason": reason or None, "actor": person.email, "actor_name": person.name,
               "actor_role": person.role(self.roles),
               "actor_region": item["region"] if item["region"] in person.regions else person.regions[0],
               "acted_at": now, "public_from": now.date()}
        writer.run(_sql("insert_act"), {column: act[column] for column in ACT_COLUMNS})
        taken = [row["act_id"] for row in _rows(writer, "act_taken", item_id=item["item_id"], act=verb)]
        if taken[:1] != [act["act_id"]]:
            # Someone else acted on this stage in the same moment, and their act was written first.
            store = self._load(engine)
            raise Refused(409, "stale", item=self.detail(store, store.items[item["item_id"]], person))
        if verb == "decide":
            self._decided_effects(writer, store, item, act, subject, change, now)
        elif verb == "cross_check" and outcome == "disagree":
            self._disagreed(writer, store, item, person, reason, now)
        store = self._load(engine)
        return {"item": self.detail(store, store.items[item["item_id"]], person), "waiting": self._waiting(store, person),
                "next_item_id": self.next_for(store, person, item["item_id"])}

    def next_for(self, store: Store, person: Person, done: str) -> str | None:
        """The oldest other item waiting for this reviewer to act, for "Open the next lesson waiting for you"."""
        waiting = [item for item in store.items.values() if item["item_id"] != done and item["region"] in person.regions
                   and self.can(store, item, person)["act"]]
        waiting.sort(key=lambda item: (_iso(item["entered_on"]) or "", item["item_id"]))
        return waiting[0]["item_id"] if waiting else None

    def repeats_of(self, store: Store, item: dict) -> list[str]:
        """The current lessons the lesson review writer named as likely repeats of a new lesson: the only
        lessons a lead may merge it into (the 29 brief, section 4.2). Until it has written for an item, there
        are none."""
        return [repeat["lesson_id"] for repeat in store.repeats(item)]

    def _version_row(self, base: dict, **fields) -> tuple:
        row = {**{column: base.get(column) for column in VERSION_COLUMNS}, **fields}
        return tuple(row[column] for column in VERSION_COLUMNS)

    def _decided_effects(self, engine: Engine, store: Store, item: dict, act: dict, subject: dict, change,
                         now: dt.datetime) -> None:
        """What a lead's decision changes in the library: a new lesson version, and the proposals it rests on."""
        outcome, today = act["outcome"], now.date()
        recommended = store.act(item, "recommend")
        who = {"reason": act["reason"], "item_id": item["item_id"], "decided_on": today, "decided_by": act["actor"],
               "decided_by_name": act["actor_name"], "recommended_by": recommended["actor"],
               "recommended_by_name": recommended["actor_name"], "recommended_reason": recommended["reason"] or "",
               "published_on": None, "days_from_publication": None, "public_from": today}
        if item["kind"] == "new" and outcome == "add":
            proposal = store.proposals[item["proposal_id"]]
            proposed = {"statement": proposal["statement"], "risk_factors": _json(proposal["risk_factors"], []),
                        "stage": proposal["stage"], "kind": proposal["kind"]}
            final = change or proposed
            lesson_id = item_id("lesson", item["proposal_id"])
            published = _date(proposal["report_public_on"])
            changed = final != proposed
            engine.insert_rows("strata.ops.lesson_versions", VERSION_COLUMNS, [self._version_row(
                {}, lesson_id=lesson_id, version=1, statement=final["statement"],
                risk_factors=json.dumps(final["risk_factors"]), stage=final["stage"], kind=final["kind"],
                edition_key=proposal["edition_key"], project_id=proposal["project_id"], state="current",
                change_kind="added", was=json.dumps(proposed) if changed else None,
                now=json.dumps(final) if changed else None,
                **{**who, "published_on": published, "days_from_publication": (today - published).days
                   if published else None})])
            engine.insert_rows("strata.ops.lesson_sources", SOURCE_COLUMNS,
                               [(lesson_id, 1, item["proposal_id"], item["item_id"], today)])
            self._tag(engine, lesson_id, 1, final, today)
        elif item["kind"] == "new" and outcome == "repeat":
            target = store.latest(act["repeat_of"])
            before = self._proposal_evidence(store, store.lesson_proposals(act["repeat_of"]))
            after = self._proposal_evidence(store, [*store.lesson_proposals(act["repeat_of"]), item["proposal_id"]])
            version = _int(target["version"]) + 1
            engine.insert_rows("strata.ops.lesson_versions", VERSION_COLUMNS, [self._version_row(
                target, version=version, change_kind="merged", was=json.dumps(_counts(before)),
                now=json.dumps(_counts(after)), **who)])
            engine.insert_rows("strata.ops.lesson_sources", SOURCE_COLUMNS,
                               [(act["repeat_of"], version, item["proposal_id"], item["item_id"], today)])
            self._tag(engine, act["repeat_of"], version, target, today)
        elif item["kind"] == "recheck" and outcome != "keep":
            target = store.latest(item["lesson_id"])
            version = _int(target["version"]) + 1
            if outcome == "change":
                was = {key: target[key] if key != "risk_factors" else _json(target[key], []) for key in TAGS}
                was |= {name: _json(target.get(name), []) for name in lesson_tags.LISTS}
                engine.insert_rows("strata.ops.lesson_versions", VERSION_COLUMNS, [self._version_row(
                    target, version=version, statement=change["statement"],
                    risk_factors=json.dumps(change["risk_factors"]), stage=change["stage"], kind=change["kind"],
                    change_kind="wording" if change["statement"] != target["statement"] else "tags",
                    was=json.dumps(was), now=json.dumps(change), **who)])
                self._tag(engine, item["lesson_id"], version, change, today)
            else:
                engine.insert_rows("strata.ops.lesson_versions", VERSION_COLUMNS, [self._version_row(
                    target, version=version, state=RETIRED[outcome], change_kind="retired",
                    was=json.dumps({"state": target["state"]}), now=json.dumps({"state": RETIRED[outcome]}), **who)])
                self._tag(engine, item["lesson_id"], version, target, today)

    @staticmethod
    def _tag(engine: Engine, lesson_id: str, version: int, source: dict, today: dt.date) -> None:
        """Keep the categories and methods a new version names, from the change or the version it follows. A version
        that names none writes no row, so it applies to every category and method (ticket 39)."""
        found = {name: source.get(name) for name in lesson_tags.LISTS}
        found = {name: value if isinstance(value, list) else _json(value, []) for name, value in found.items()}
        if any(found.values()):
            engine.insert_rows("strata.ops.lesson_version_tags", TAG_COLUMNS, [(
                lesson_id, version, json.dumps(found["categories"]), json.dumps(found["methods"]), today)])

    def _disagreed(self, engine: Engine, store: Store, item: dict, person: Person, reason: str,
                   now: dt.datetime) -> None:
        """A cross-check that disagrees starts a re-check in the region that decided. A rejected proposal has no
        lesson to re-check, so it goes back to that region's queue as a new lesson."""
        checked = store.items[item["decided_item_id"]]
        lesson_id = store.lesson_of(checked) or (store.act(checked, "decide") or {}).get("repeat_of")
        latest = store.latest(lesson_id) if lesson_id else None
        if latest is not None and latest["state"] == "current":
            fields = {"item_id": item_id("recheck", f"{lesson_id}|{item['item_id']}"), "kind": "recheck",
                      "proposal_id": None, "lesson_id": lesson_id, "version": _int(latest["version"])}
        else:
            fields = {"item_id": item_id("new", f"{checked['proposal_id']}|{item['item_id']}"), "kind": "new",
                      "proposal_id": checked["proposal_id"], "lesson_id": None, "version": None}
        row = {**fields, "decided_item_id": None, "project_id": checked["project_id"],
               "region": item["decided_region"], "decided_region": None, "origin": "cross_check",
               "origin_by": person.email, "origin_by_name": person.name, "origin_reason": reason,
               "origin_item_id": item["item_id"], "entered_on": now.date(), "due_on": None, "created_at": now,
               "public_from": now.date()}
        engine.insert_rows("strata.ops.lesson_review_items", ITEM_COLUMNS, [tuple(row[c] for c in ITEM_COLUMNS)])

    def rewrite(self, engine: Engine, viewer: Viewer, wanted: str, agent, writer: Engine, six_checks=None) -> dict:
        """The review page's "Try again": the lesson review writer writes its note on one open item again,
        stored through writer, and the page gets the item with the new note. Any lesson reviewer may ask.
        six_checks are the app's six checks, with its judge (ticket 61), and check 6 asks as the reviewer."""
        from strata.knowledge.lessons import writer as notes

        person = self._require(viewer)
        store = self._load(engine)
        item = store.items.get(wanted)
        if item is None:
            raise Refused(404, "unknown_item", {"item_id": wanted})
        if agent is None:
            raise Refused(503, "no_agent")
        notes.write_one(writer, store, item, self.subject(store, item), agent, self.now(),
                        int(self.value("likely_repeats_max")), six_checks, reading=engine)
        store = self._load(engine)
        return {"item": self.detail(store, store.items[item["item_id"]], person)}

    def recheck(self, engine: Engine, viewer: Viewer, lesson_id: str, reason: str, writer: Engine) -> dict:
        """Ask for a re-check of a current lesson, as any lesson reviewer, once while none is open. It reads as
        the viewer and writes the queue item through writer."""
        person = self._require(viewer)
        reason = (reason or "").strip()
        if not reason or len(reason) > int(self.value("reason_max_chars")):
            raise Refused(422, "no_reason" if not reason else "reason_too_long")
        store = self._load(engine)
        latest = store.latest(lesson_id)
        if latest is None or latest["state"] != "current":
            raise Refused(404, "unknown_lesson", {"lesson_id": lesson_id})
        open_item = store.open_recheck(lesson_id)
        if open_item is not None:
            raise Refused(409, "recheck_open", {"on": _iso(open_item["entered_on"])})
        region = (store.projects.get(latest["project_id"]) or {}).get("region") or person.regions[0]
        now = self.now()
        row = {"item_id": item_id("recheck", f"{lesson_id}|{person.email}|{now.isoformat()}"),
               "lesson_id": lesson_id, "version": _int(latest["version"]), "project_id": latest["project_id"],
               "region": region, "origin_by": person.email, "origin_by_name": person.name, "origin_reason": reason,
               "entered_on": now.date(), "created_at": now, "public_from": now.date()}
        # Checked and written in one statement, then read back: a request that lost a race to another reviewer's finds
        # theirs open (ticket 29's review round 3, P3). Without a transaction both can land, so the later one takes
        # its own row back before it answers (ticket 62's review round 1, follow-up 1).
        writer.run(_sql("insert_recheck"), row)
        opened = _rows(writer, "open_recheck", lesson_id=lesson_id)
        if opened[:1] and opened[0]["item_id"] != row["item_id"]:
            writer.run(_sql("withdraw_recheck"), {"item_id": row["item_id"]})
            raise Refused(409, "recheck_open", {"on": _iso(opened[0]["entered_on"])})
        return {"item_id": row["item_id"], "region": region, "on": now.date().isoformat()}


def _counts(evidence: list[dict]) -> dict:
    """What a lesson rests on, for a merge's was and now: its quotes and the reports they come from."""
    return {"quotes": len(evidence), "reports": len({row["document_id"] for row in evidence})}
