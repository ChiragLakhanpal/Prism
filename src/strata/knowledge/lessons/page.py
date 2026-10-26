"""The Lessons page: what came in since the reader's last visit, what changed where they used it, what is new, what
their passage reports fixed, and the library (ticket 39; the 39 brief, sections 4 and 9).

Everything the page states is built here, on the server, from the stored rows, so the browser counts nothing, never
compares versions, never decides a tier and never picks a count word (the 39 brief, section 1):

- digest() is the opening sentence and its count words, each with the items it counts. A visit is a session
  (strata.knowledge.lessons.visits); the window runs from the start of the previous visit to the start of this one.
  Reports are the ICRs, ICR Reviews and PPARs Strata first fetched in the window; new, changed and retired lessons
  are the versions a lead decided in it; proposed lessons are those waiting in the review queue now, as a count only.
- changed_where_used() is "Changed where you used it": one notice per lesson and cited version in the reader's own
  open drafts (strata.knowledge.lessons.notices decides the tier, as it does for the draft page and the nightly job).
  Ticket 41's Home reads the same two functions, never a second computation.
- new_lessons(), feedback() and library() are the rest of the page.

A preview leaves out everything about the signed-in person and the proposed count; an as-of view shows only the
library, at the versions current then (the 39 brief, section 4.9).
"""

from __future__ import annotations

import datetime as dt
from functools import cache
from importlib import resources


from strata.knowledge.lessons.review import LessonReview, Store, _date, _int, _iso, lesson_words
from strata.knowledge.lessons.visits import Visit
from strata.lakehouse.engine import Engine
from strata.reader.templates import ICR, ICR_REVIEW, PPAR, template_for
from strata.tools.data_readiness_for import fill

REPORT_TYPES = {"icr": ICR.document_type, "review": ICR_REVIEW.document_type, "ppar": PPAR.document_type}


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.knowledge.lessons") / "sql" / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


# ── Sentences the server writes ──────────────────────────────────────────

def words() -> dict:
    return lesson_words()


def count_word(number: int) -> str:
    """DESIGN.md section 7, rule 12: one to nine in words, numerals from 10."""
    return words()["words"][number - 1] if 1 <= number <= 9 else f"{number:,}"


def count(number: int, popover: str | None = None, capital: bool = False) -> dict:
    """A count in a sentence, with the word the server chose and the items it opens, by their key in the page."""
    word = count_word(number)
    return {"number": number, "word": word[:1].upper() + word[1:] if capital else word, "capital": capital,
            "popover": popover}


def date(day: dt.date | None) -> dict:
    return {"date": day.isoformat() if day else None}


def form(forms: dict, number: int) -> str:
    return forms["one" if number == 1 else "many"]


def joined(parts: list[list[dict]]) -> list[dict]:
    """Parts as a list: "a and b", or "a, b, and c"."""
    found = words()["digest"]
    out: list[dict] = []
    for index, part in enumerate(parts):
        if index:
            last = index == len(parts) - 1
            out.append({"text": found["pairJoin"] if len(parts) == 2 else found["lastJoin"] if last else found["join"]})
        out.extend(part)
    return out


def capitalized(segments: list[dict]) -> list[dict]:
    """The sentence with its first count word capitalized, for a part that opens a sentence."""
    first = segments[0] if segments else None
    if first and "number" in first:
        return [count(first["number"], first.get("popover"), capital=True), *segments[1:]]
    return segments


# ── The window's rows ────────────────────────────────────────────────────

def decided_at(store: Store, version: dict) -> dt.datetime | None:
    """When the lead's decision that wrote a version was made: its decide act's time."""
    act = store.act(store.items.get(version["item_id"]) or {"item_id": version["item_id"]}, "decide")
    if act is None:
        return None
    value = act["acted_at"]
    if not isinstance(value, dt.datetime):
        value = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00").replace(" ", "T"))
    return value if value.tzinfo else value.replace(tzinfo=dt.UTC)


def in_window(when: dt.datetime | None, since: dt.datetime, until: dt.datetime) -> bool:
    return when is not None and since <= when < until


def added_in(store: Store, since: dt.datetime, until: dt.datetime) -> list[dict]:
    """Version 1 of each lesson decided in the window that is still current: the digest's "new" count and the New
    cards read this one rule, so a lesson added and retired in one window counts only as retired."""
    return [row for versions in store.versions.values() for row in versions[:1]
            if in_window(decided_at(store, row), since, until) and store.latest(row["lesson_id"])["state"] == "current"]


def current_versions(store: Store) -> list[dict]:
    return [versions[-1] for versions in store.versions.values() if versions[-1]["state"] == "current"]


def as_of_store(store: Store, as_of: dt.date | None) -> Store:
    """The store as of a date: each lesson at the version current then, and a lesson first decided later not there
    yet (ticket 40). The one place the Lessons page applies an as-of date, for the page, its library and its two
    versions view alike."""
    if as_of is not None:
        store.versions = {lesson_id: kept for lesson_id, versions in store.versions.items()
                          if (kept := [row for row in versions if _date(row["decided_on"]) <= as_of])}
    return store


def with_examples(versions: dict[str, list[dict]], extra: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Every lesson's versions with one reader's example versions after them (ticket 41), for that reader's notices and
    two-versions view only. The lead's versions are copied, never changed, so the library and the digest keep them."""
    if not extra:
        return versions
    merged = {lesson_id: list(rows) for lesson_id, rows in versions.items()}
    for lesson_id, rows in extra.items():
        if lesson_id in merged:
            known = {_int(row["version"]) for row in merged[lesson_id]}
            merged[lesson_id].extend(row for row in rows if _int(row["version"]) not in known)
            merged[lesson_id].sort(key=lambda row: _int(row["version"]))
    return merged


def with_versions(store: Store, extra: dict[str, list[dict]] | None) -> Store:
    """A shallow copy of the store whose versions include the reader's example versions, for "Changed where you used
    it" alone."""
    if not extra:
        return store
    import copy as copying

    shown = copying.copy(store)
    shown.versions = with_examples(store.versions, extra)
    return shown


def waiting_proposals(store: Store) -> int:
    """Proposed lessons waiting in the review queue now, in every region: a count, never a list."""
    return sum(1 for item in store.items.values() if item["kind"] == "new" and store.stage(item) != "decided")


class LessonsPage:
    """The page's reads. It keeps the lesson review, never a viewer; each call gets the viewer's engine."""

    def __init__(self, review: LessonReview):
        self.review = review

    # ── The digest ───────────────────────────────────────────────────────

    def reports(self, engine: Engine, since: dt.datetime, until: dt.datetime) -> list[dict]:
        """The completion reports and IEG's reports Strata first fetched in the window, oldest first."""
        found = []
        for row in _rows(engine, "reports_loaded", types=",".join(REPORT_TYPES.values()), since=since, until=until):
            template = template_for(row["document_type"] or "")
            found.append({"kind": next(key for key, value in REPORT_TYPES.items() if value == row["document_type"]),
                          "doc_type": row["document_type"],
                          "doc_short": template.short_name if template else row["document_type"],
                          "document_id": str(row["document_id"]), "doc_key": row["doc_key"], "pid": row["project_id"],
                          "project_name": row["project_name"], "disclosed_on": _iso(row["disclosed_on"])})
        return found

    def lesson_item(self, store: Store, version: dict) -> dict:
        return {"lesson_id": version["lesson_id"], "version": _int(version["version"]),
                "statement": version["statement"], "decided_on": _iso(version["decided_on"]),
                "change_kind": version["change_kind"], "state": version["state"]}

    def digest(self, engine: Engine, store: Store, visit: Visit, preview: bool) -> dict:
        """The opening sentence: its kind (first, since or nothing), its segments, its counts and the items each
        count opens."""
        found = words()["digest"]
        proposed = None if preview else waiting_proposals(store)
        current = current_versions(store)
        if visit.first:
            total = len(current)
            if total == 0:
                segments = fill(found["firstEmpty"], {})
            else:
                slots = {"total": fill(form(found["firstTotal"], total), {"count": count(total, "total")})}
                if proposed:
                    slots["proposed"] = fill(form(found["lessons"]["proposed"], proposed), {"count": count(proposed, "proposed")})
                segments = fill(found["firstProposed" if proposed else "first"], slots)
            return {"kind": "first", "segments": segments,
                    "counts": {"total": total, "rechecking": sum(1 for row in current if store.open_recheck(row["lesson_id"])),
                               "proposed": proposed},
                    "items": {}}

        since, until = visit.previous_started_at, visit.started_at
        reports = self.reports(engine, since, until)
        decided = [(version, decided_at(store, version)) for versions in store.versions.values() for version in versions]
        window = [version for version, when in decided if in_window(when, since, until)]
        new = {row["lesson_id"]: row for row in added_in(store, since, until)}
        changed = {row["lesson_id"]: row for row in sorted(window, key=lambda row: _int(row["version"]))
                   if _int(row["version"]) > 1 and row["change_kind"] != "retired"}
        retired = {row["lesson_id"]: row for row in window if row["change_kind"] == "retired"}
        by_kind = {kind: [row for row in reports if row["kind"] == kind] for kind in REPORT_TYPES}
        counts = {"reports": {kind: len(rows) for kind, rows in by_kind.items()}, "new": len(new),
                  "changed": len(changed), "retired": len(retired), "proposed": proposed}
        report_parts = [fill(form(found["reports"][kind], len(rows)), {"count": count(len(rows), "reports")})
                        for kind, rows in by_kind.items() if rows]
        lesson_parts = [fill(form(found["lessons"][key], number), {"count": count(number, key)})
                        for key, number in (("new", len(new)), ("changed", len(changed)), ("retired", len(retired)),
                                            ("proposed", proposed or 0)) if number]
        if not report_parts and not new and not changed and not retired:
            kind = "nothing"
            segments = fill(found["nothing"], {"date": date(since.date())})
            if proposed:
                segments += fill(found["nothingProposed"], {"proposed": capitalized(lesson_parts[-1])})
        else:
            kind = "since"
            segments = (fill(found["since"], {"date": date(since.date()), "reports": joined(report_parts)})
                        if report_parts else fill(found["noReports"], {"date": date(since.date())}))
            segments.append({"text": " "})
            if new or changed or retired:
                segments += capitalized(joined(lesson_parts)) + [{"text": found["lessonsEnd"]}]
            elif proposed:
                segments += fill(found["noneProposed"], {"proposed": lesson_parts[-1]})
            else:
                segments += fill(found["none"], {})
        items = {"reports": reports,
                 "new": [self.lesson_item(store, row) for row in new.values()],
                 "changed": [self.lesson_item(store, row) for row in changed.values()],
                 "retired": [self.lesson_item(store, row) for row in retired.values()]}
        return {"kind": kind, "segments": segments, "counts": counts, "items": items}

    # ── Changed where you used it ────────────────────────────────────────

    @staticmethod
    def use(draft, notice: dict, may_act: bool) -> dict:
        """One row of one draft that cites the lesson: what the "Used in" line names, and what its author may do."""
        from strata.drafts import runtime

        kind = runtime.load_kind(draft.kind)
        module = runtime.writer_module_for(draft.kind)
        label = getattr(module, "row_label", None) if kind and kind.row_label else None
        return {"draft_id": draft.draft_id, "kind": draft.kind, "subject": draft.content.get("subject") or {},
                "draft_state": draft.state.state, "row_key": notice["row_key"], "cites": notice["a"],
                "row_label": label(draft.content, notice["row_key"]) if label else None,
                "holds_export": notice["holds_export"], "can_act": may_act,
                "can_update": bool(kind and kind.rewrite_row)}

    def changed_where_used(self, store: Store, drafts: list) -> list[dict]:
        """One notice per lesson and cited version across the reader's own open drafts (Draft and Checked by you),
        each with every row that cites it. Retired as wrong first, since they hold an export, then the newest
        decision first (the 39 brief, section 2.3)."""
        from strata.drafts.runtime import OPEN_STATES, reason_max_chars
        from strata.knowledge.lessons.notices import row_notices

        # The keep route's limit, read where the route reads it, so the form counts against the same number.
        reason_max = reason_max_chars()
        grouped: dict[tuple[str, int], dict] = {}
        for draft in drafts:
            if draft.state.state not in OPEN_STATES:
                continue
            for notice in row_notices(draft.content, store.versions):
                key = (notice["lesson_id"], notice["a"])
                entry = grouped.setdefault(key, {
                    **{name: value for name, value in notice.items() if name not in ("row_key", "anchor", "kept")},
                    "anchor": f"notice-{notice['lesson_id']}-v{notice['a']}",
                    "actions": ["versions", "remove", "keep"] if notice["tier"].startswith("retired")
                    else ["versions", "update", "keep"], "uses": [],
                    "reason_max_chars": reason_max})
                entry["uses"].append(self.use(draft, notice, True))
                entry["holds_export"] = entry["holds_export"] or notice["holds_export"]
        found = list(grouped.values())
        found.sort(key=lambda notice: notice["decided_on"], reverse=True)
        found.sort(key=lambda notice: notice["tier"] != "retired_wrong")
        return found

    def strengthened(self, store: Store, drafts: list, visit: Visit) -> dict | None:
        """The digest's quiet line: lessons the reader's open drafts cite that only gained a quote in the window."""
        from strata.drafts.runtime import OPEN_STATES
        from strata.knowledge.lessons.notices import strengthened

        if visit.first:
            return None
        grouped: dict[tuple[str, int], dict] = {}
        for draft in drafts:
            if draft.state.state not in OPEN_STATES:
                continue
            gained = strengthened(draft.content, store.versions,
                                  lambda row: in_window(decided_at(store, row), visit.previous_started_at,
                                                        visit.started_at))
            for item in gained:
                entry = grouped.setdefault((item["lesson_id"], item["a"]),
                                           {**{key: value for key, value in item.items() if key != "row_key"},
                                            "uses": []})
                entry["uses"].append({"draft_id": draft.draft_id, "kind": draft.kind,
                                      "subject": draft.content.get("subject") or {}, "row_key": item["row_key"],
                                      "cites": item["a"]})
        if not grouped:
            return None
        lessons = len({lesson_id for lesson_id, _ in grouped})
        found = words()["digest"]
        return {"segments": fill(form(found["strengthened"], lessons),
                                 {"count": count(lessons, "strengthened", capital=True)}),
                "count": lessons, "items": list(grouped.values())}

    @staticmethod
    def exported_uses(store: Store, drafts: list, lesson_id: str) -> list[dict]:
        """The reader's exported drafts that cite a lesson, for the retired popover (the 39 brief, section 5.2)."""
        from strata.knowledge.lessons.notices import citations

        found = []
        for draft in drafts:
            if draft.state.state != "exported":
                continue
            for _row_key, cited_lesson, version in citations(draft.content):
                if cited_lesson == lesson_id:
                    found.append({"draft_id": draft.draft_id, "kind": draft.kind,
                                  "subject": draft.content.get("subject") or {}, "cites": version})
                    break
        return found

    # ── The library alone ────────────────────────────────────────────────

    def library(self, engine: Engine, viewer, page: int = 1, filters: dict | None = None, show: str | None = None,
                as_of: dt.date | None = None) -> dict:
        """The library for a filter or page change, as of the same date as the page it changes (ticket 40), so it
        always matches build()'s library for the same filters."""
        store = as_of_store(self.review._load(engine), as_of)
        return self.review.library(engine, viewer, page, filters, show, store=store)

    # ── The whole page ───────────────────────────────────────────────────

    # ── New ──────────────────────────────────────────────────────────────

    def new_lessons(self, store: Store, visit: Visit) -> dict | None:
        """Lessons that became current at version 1 in the window, newest first, as library cards: at most
        lessons.new_cards_max, then how many more the library holds. None on a first visit or with none new."""
        if visit.first:
            return None
        added = added_in(store, visit.previous_started_at, visit.started_at)
        if not added:
            return None
        added.sort(key=lambda row: (decided_at(store, row), row["lesson_id"]), reverse=True)
        most = int(self.review.thresholds.value("lessons.new_cards_max"))
        more = len(added) - most
        return {"cards": [self.review.card(store, row["lesson_id"]) for row in added[:most]],
                "more": max(more, 0),
                "more_segments": fill(form(words()["newMore"], more),
                                      {"count": count(more, capital=True),
                                       "link": {"link": words()["newMoreLink"], "href": "#library"}})
                if more > 0 else None}

    # ── Two versions of a lesson ─────────────────────────────────────────

    def versions(self, engine: Engine, lesson_id: str, a: int, b: int, as_of: dt.date | None = None,
                 extra: dict[str, list[dict]] | None = None) -> dict:
        """Version a of a lesson beside version b, for the evidence drawer's "Two versions of a lesson" (evidence id
        versions:{lesson_id}:{a}:{b}): each with its statement, tags, the quotes it rests on and its decision by role,
        the change between them with the changed words, the lead's reason on the later one, and the versions that came
        between. A retired lesson's last block says when and why. As of a date, a version decided later is not there
        yet, so asking for it is unknown_version (ticket 40)."""
        from strata.knowledge.lessons.notices import describe, tier
        from strata.knowledge.lessons.review import Refused

        store = as_of_store(self.review._load(engine), as_of)
        # One viewer's example lesson versions (ticket 41), which only their own two-versions view shows.
        store.versions = with_examples(store.versions, extra or {})
        rows = store.versions.get(lesson_id) or []
        numbers = {_int(row["version"]): row for row in rows}
        if a not in numbers or b not in numbers or a >= b:
            raise Refused(404, "unknown_version", {"lesson_id": lesson_id, "version": b if a in numbers else a})
        project = store.projects.get(numbers[b]["project_id"]) or {}

        def block(version: int) -> dict:
            row = numbers[version]
            evidence = self.review._proposal_evidence(store, store.lesson_proposals(lesson_id, version))
            return {"version": version, "statement": row["statement"], **self.review.tags(row),
                    "sector": project.get("sector_name"), "decided_on": _iso(row["decided_on"]),
                    "state": row["state"], "change_kind": row["change_kind"],
                    "reason": row["reason"] if version != 1 else None,
                    "evidence": [self.review.evidence_row(store, item) for item in evidence],
                    **self.review.ieg(store, evidence, row["project_id"]),
                    **({"example": True} if row.get("example") else {})}

        later = [row for row in rows if a < _int(row["version"]) <= b]
        return {"evidence_id": f"versions:{lesson_id}:{a}:{b}", "lesson_id": lesson_id,
                "current": _int(rows[-1]["version"]), "tier": tier(later), "versions": [block(a), block(b)],
                **describe(rows, a, b)}

    # ── Your reports ─────────────────────────────────────────────────────

    @staticmethod
    def feedback(counts: dict | None) -> dict:
        """What the reader's "Wrong passage" reports did, from the counts the weekly retrieval run stores (ticket 32's
        strata.ops.retrieval_feedback_viewers), in brief 32's sentence, with each count's word. None marked: the
        line that says where reporting lives."""
        if not counts or not int(counts.get("marked") or 0):
            return {"never": True, "segments": None, "counts": None}
        found = words()["feedback"]
        marked, fixed, waiting = int(counts["marked"]), int(counts["fixed"]), int(counts["waiting"])
        recited = int(counts["recited"])
        slots = {"marked": count(marked, "marked"), "fixed": count(fixed, "fixed"), "recited": count(recited, "recited"),
                 "isAre": form(found["isAre"], fixed), "themIt": form(found["themIt"], waiting)}
        if marked == 1 and fixed == 1:
            slots["recited"] = count(recited, "recited", capital=True)
            template = found["oneFixed"] if recited else found["oneFixedOnly"]
        elif fixed:
            template = found["fixedAndRecited"] if recited else found["fixed"]
        else:
            template = found["waiting"] if waiting else found["kept"]
        segments = fill(template, slots)
        return {"never": False, "segments": segments,
                "counts": {key: int(counts[key]) for key in ("marked", "fixed", "waiting", "kept", "recited")}}

    # ── The library alone ────────────────────────────────────────────────

    def library(self, engine: Engine, viewer, page: int = 1, filters: dict | None = None, show: str | None = None,
                as_of: dt.date | None = None) -> dict:
        """The library for a filter or page change, as of the same date as the page it changes (ticket 40), so it
        always matches build()'s library for the same filters."""
        store = as_of_store(self.review._load(engine), as_of)
        return self.review.library(engine, viewer, page, filters, show, store=store)

    # ── The whole page ───────────────────────────────────────────────────

    def build(self, engine: Engine, viewer, *, visit: Visit, preview: bool, drafts: list = (),
              feedback: dict | None = None, filters: dict | None = None, page: int = 1, show: str | None = None,
              as_of: dt.date | None = None, extra_versions: dict[str, list[dict]] | None = None) -> dict:
        """The whole Lessons tab in one answer. A preview leaves out what is about the signed-in person; an as-of view
        shows only the library (the 39 brief, section 4.9). extra_versions are the reader's own example lesson versions
        (ticket 41), which only their notices read: the library and the digest keep the lead's versions."""
        store = as_of_store(self.review._load(engine), as_of)
        library = self.review.library(engine, viewer, page, filters, show, store=store)
        if as_of is not None:
            return {"view": "preview" if preview else "staff", "as_of": as_of.isoformat(), "visit": None,
                    "digest": None, "notices": [], "new_lessons": None, "feedback": None, "library": library}
        drafts = [] if preview else list(drafts)
        digest = self.digest(engine, store, visit, preview)
        digest["strengthened"] = None if preview else self.strengthened(store, drafts, visit)
        for item in (digest.get("items") or {}).get("retired") or []:
            item["exported_uses"] = self.exported_uses(store, drafts, item["lesson_id"])
        return {"view": "preview" if preview else "staff", "as_of": None, "visit": visit.as_dict(), "digest": digest,
                "notices": self.changed_where_used(with_versions(store, extra_versions), drafts),
                "new_lessons": self.new_lessons(store, visit),
                "feedback": None if preview else self.feedback(feedback), "library": library}
