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

LessonReview reads and writes as the viewer, through the engine a route opens with the viewer's own token
(ADR 0003), and keeps nothing about a viewer between calls (CLAUDE.md rule 7).
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

from strata.agent.verifier import find_quote
from strata.config import (Editions, LessonLists, Person, Roles, Thresholds, load_editions, load_lesson_lists,
                           load_thresholds)
from strata.dbx import Viewer
from strata.knowledge.lessons.propose import IEG_TYPES, PASSED, item_id
from strata.lakehouse.engine import Engine
from strata.reader.templates import template_for

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


def _bool(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def _json(value, default):
    try:
        return json.loads(value) if value else default
    except ValueError:
        return default


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

    def act(self, item: dict, verb: str) -> dict | None:
        found = [act for act in self.acts.get(item["item_id"], []) if act["act"] == verb]
        return found[-1] if found else None

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
        if detail:
            text = row.get("passage_text") or ""
            span = find_quote(row["quote"], text) if text else None
            found |= {"text": text, "highlight": list(span) if span else None, "language": row.get("language")}
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
        }

    @staticmethod
    def _item(found) -> dict | None:
        return {"key": found.key, "label": found.label} if found else None

    def _edition(self, key: str | None) -> dict | None:
        found = self.editions.get(key)
        return {"key": found.key, "name": found.name} if found else None

    def _proposal_evidence(self, store: Store, proposal_ids: Iterable[str]) -> list[dict]:
        rows = [row for proposal_id in proposal_ids for row in store.evidence.get(proposal_id, [])]
        seen, unique = set(), []
        for row in rows:  # two merged proposals may share a restatement
            if row["passage_id"] not in seen:
                seen.add(row["passage_id"])
                unique.append(row)
        return sorted(unique, key=lambda row: (row["role"] != "source", _iso(row["document_date"]) or ""))

    def subject(self, store: Store, item: dict) -> dict:
        """What an item is about: its statement, tags, evidence rows and project, at the version it concerns."""
        if item["kind"] == "new":
            proposal = store.proposals.get(item["proposal_id"]) or {}
            rows = self._proposal_evidence(store, [item["proposal_id"]])
            return {"statement": proposal.get("statement"), "row": proposal, "evidence": rows,
                    "project_id": item["project_id"], "version": None, "lesson_id": store.lesson_of(item)}
        lesson_id = item["lesson_id"]
        version = store.at(lesson_id, _int(item["version"])) or {}
        rows = self._proposal_evidence(store, store.lesson_proposals(lesson_id, _int(version.get("version"))))
        return {"statement": version.get("statement"), "row": version, "evidence": rows,
                "project_id": version.get("project_id") or item["project_id"],
                "version": _int(version.get("version")), "lesson_id": lesson_id}

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
            **self.ieg(store,subject["evidence"], subject["project_id"]), "may_repeat": False,
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
                    "waiting": None}
        store = self._load(engine)
        return {"signed_in": True, "tabs": ["library", "review"], "acts": list(person.acts(self.roles)),
                "regions": list(person.regions), "role": person.role(self.roles), "waiting": self._waiting(store, person)}

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
        return {
            "as_of": self.today().isoformat(), "limit_days": int(self.value("business_days")),
            "regions": list(person.regions), "waiting": len(rows),
            "groups": {group: [row for row in rows if row["group"] == group] for group in ("you", "others")},
            "decided": {"window_days": int(self.value("decided_window_days")), "total": len(decided), "page": page,
                        "pages": pages, "from": (page - 1) * size + 1 if shown else 0,
                        "to": (page - 1) * size + len(shown), "rows": shown},
        }

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
            version = next((row for row in store.versions.get(lesson_id or "", [])
                            if row["item_id"] == item["item_id"]), None)
            published = _date((store.proposals.get(item["proposal_id"]) or {}).get("report_public_on"))
            found.append({
                "item_id": item["item_id"], "kind": item["kind"], "statement": subject["statement"],
                "pid": subject["project_id"], "project_name": (store.projects.get(subject["project_id"]) or {}).get(
                    "project_name"), "outcome": DECIDED_OUTCOME[decision["outcome"]],
                "version": _int(version["version"]) if version else subject["version"], "decided_on": on.isoformat(),
                "decided_at": decision["acted_at"],
                "days_from_publication": (on - published).days if item["kind"] == "new" and published else None})
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
            "lesson": {"lesson_id": subject["lesson_id"], "version": subject["version"]},
            "summary": None, "repeats": [], "history": self.history(store, item),
            "outcome": self.outcome(store, item), "lists": self.lists.as_dict(),
            "limits": {"reason_max_chars": int(self.value("reason_max_chars")),
                       "statement_max_chars": int(self.value("statement_max_chars")),
                       "sample_percent": round(float(self.value("cross_check_share")) * 100),
                       "summary_poll_seconds": int(self.value("summary_poll_seconds")),
                       "summary_poll_minutes": int(self.value("summary_poll_minutes"))},
        }

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
                version = next((row for row in store.versions.get(lesson_id or "", [])
                                if row["item_id"] == item["item_id"]), None)
                entry["version"] = _int(version["version"]) if version else None
                target = store.latest(act["repeat_of"]) if act["repeat_of"] else None
                entry["target"] = target["statement"] if target else None
            events.append(entry)
        return events

    def _changes(self, store: Store, item: dict, act: dict) -> list[dict]:
        """The fields an act changed, each with its was and now, for the history's Was and Now lines."""
        if act["act"] == "decide":
            lesson_id = act["repeat_of"] or store.lesson_of(item)
            version = next((row for row in store.versions.get(lesson_id or "", []) if row["item_id"] == item["item_id"]),
                           None)
            if version is None or not version["was"]:
                return []
            was, now = _json(version["was"], {}), _json(version["now"], {})
            return [{"field": key, "was": was.get(key), "now": now.get(key)} for key in now if was.get(key) != now.get(key)]
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
        version = next((row for row in store.versions.get(lesson_id or "", []) if row["item_id"] == item["item_id"]),
                       None)
        target = store.latest(decision["repeat_of"]) if decision["repeat_of"] else None
        published = _date((store.proposals.get(item["proposal_id"]) or {}).get("report_public_on"))
        on = _date(decision["acted_at"])
        return {"outcome": DECIDED_OUTCOME[decision["outcome"]], "on": on.isoformat(), "lesson_id": lesson_id,
                "version": _int(version["version"]) if version else _int(item["version"]),
                "target": target["statement"] if target else None,
                "days_from_publication": (on - published).days if item["kind"] == "new" and published else None,
                "published_on": _iso(published)}

    # ── The library ──────────────────────────────────────────────────────

    def card(self, store: Store, lesson_id: str) -> dict:
        """One lesson card, naming roles and never people (the 29 brief, section 4.1)."""
        latest = store.latest(lesson_id)
        evidence = self._proposal_evidence(store, store.lesson_proposals(lesson_id))
        project = store.projects.get(latest["project_id"]) or {}
        recheck = store.open_recheck(lesson_id)
        first = next((row for row in evidence if row["role"] == "source"), None)
        return {
            "lesson_id": lesson_id, "version": _int(latest["version"]), "statement": latest["statement"],
            **self.tags(latest), "sector": project.get("sector_name"), "pid": latest["project_id"],
            **self.ieg(store,evidence, latest["project_id"]), "decided_on": _iso(latest["decided_on"]),
            "state": "rechecking" if recheck else "current",
            "rechecking_since": _iso(recheck["entered_on"]) if recheck else None,
            "quote": first["quote"] if first else None,
            "evidence": [self.evidence_row(store,row) for row in evidence],
        }

    def library(self, engine: Engine, viewer: Viewer, page: int = 1) -> dict:
        """The library's current lessons, and those being re-checked, newest decision first. Retired lessons
        are left out. The order is by date, never by use."""
        store = self._load(engine)
        current = [versions[-1] for versions in store.versions.values() if versions[-1]["state"] == "current"]
        current.sort(key=lambda row: (_iso(row["decided_on"]), row["lesson_id"]), reverse=True)
        size = int(self.value("library_page_size"))
        pages = max(1, -(-len(current) // size))
        shown = current[(page - 1) * size: page * size] if 1 <= page <= pages else []
        person = self.reviewer(viewer)
        return {"as_of": self.today().isoformat(), "page": page, "pages": pages, "page_size": size,
                "total": len(current), "from": (page - 1) * size + 1 if shown else 0,
                "to": (page - 1) * size + len(shown), "can_recheck": person is not None,
                "waiting": self._waiting(store, person) if person else None,
                "lessons": [self.card(store, row["lesson_id"]) for row in shown]}

    # ── Writes ───────────────────────────────────────────────────────────
    #
    # A reviewer's act is written with their own token (ADR 0003), so the warehouse holds the same line the
    # roles file draws: only the reviewer groups' members may write the review tables (ops/lessons/
    # grant_reviewers.py grants them), and the server checks the roles file first in any case.

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
        return {"statement": statement, "risk_factors": factors, "stage": stage, "kind": kind}

    def act(self, engine: Engine, viewer: Viewer, wanted: str, verb: str, body: dict) -> dict:
        """One recommendation, decision or cross-check, as the viewer, or the reason it is refused."""
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
        engine.insert_rows("strata.ops.lesson_review_acts", ACT_COLUMNS, [tuple(act[c] for c in ACT_COLUMNS)])
        if verb == "decide":
            self._decided_effects(engine, store, item, act, subject, change, now)
        elif verb == "cross_check" and outcome == "disagree":
            self._disagreed(engine, store, item, person, reason, now)
        store = self._load(engine)
        return {"item": self.detail(store, store.items[item["item_id"]], person), "waiting": self._waiting(store, person)}

    def repeats_of(self, store: Store, item: dict) -> list[str]:
        """The current lessons the lesson review writer named as likely repeats of a new lesson: the only
        lessons a lead may merge it into (the 29 brief, section 4.2). The writer arrives with ticket 29's
        workflow; until it has written for an item, there are none."""
        return []

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
        elif item["kind"] == "recheck" and outcome != "keep":
            target = store.latest(item["lesson_id"])
            version = _int(target["version"]) + 1
            if outcome == "change":
                was = {key: target[key] if key != "risk_factors" else _json(target[key], []) for key in TAGS}
                engine.insert_rows("strata.ops.lesson_versions", VERSION_COLUMNS, [self._version_row(
                    target, version=version, statement=change["statement"],
                    risk_factors=json.dumps(change["risk_factors"]), stage=change["stage"], kind=change["kind"],
                    change_kind="wording" if change["statement"] != target["statement"] else "tags",
                    was=json.dumps(was), now=json.dumps(change), **who)])
            else:
                engine.insert_rows("strata.ops.lesson_versions", VERSION_COLUMNS, [self._version_row(
                    target, version=version, state=RETIRED[outcome], change_kind="retired", was=None, now=None,
                    **who)])

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

    def recheck(self, engine: Engine, viewer: Viewer, lesson_id: str, reason: str) -> dict:
        """Ask for a re-check of a current lesson, as any lesson reviewer, once while none is open."""
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
        row = {"item_id": item_id("recheck", f"{lesson_id}|{uuid.uuid4().hex}"), "kind": "recheck",
               "proposal_id": None, "lesson_id": lesson_id, "version": _int(latest["version"]),
               "decided_item_id": None, "project_id": latest["project_id"], "region": region,
               "decided_region": None, "origin": "asked", "origin_by": person.email, "origin_by_name": person.name,
               "origin_reason": reason, "origin_item_id": None, "entered_on": now.date(), "due_on": None,
               "created_at": now, "public_from": now.date()}
        engine.insert_rows("strata.ops.lesson_review_items", ITEM_COLUMNS, [tuple(row[c] for c in ITEM_COLUMNS)])
        return {"item_id": row["item_id"], "region": region, "on": now.date().isoformat()}


def _counts(evidence: list[dict]) -> dict:
    """What a lesson rests on, for a merge's was and now: its quotes and the reports they come from."""
    return {"quotes": len(evidence), "reports": len({row["document_id"] for row in evidence})}
