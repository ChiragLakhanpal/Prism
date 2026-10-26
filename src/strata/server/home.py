"""Home (ticket 41; the 41 design brief): the briefing, the Start here strip, "Worth knowing" and "Waiting for you".

- GET /api/home?view=&asof= is the whole page in one answer, so it renders once, from fixed checks and no model: the
  briefing's sentences, each count with the lines it counts, the lines, the viewer's drafts to check and the Start
  here strip's links. World Bank staff get the activities check_plan marked in the Procurement Plans disclosed in the
  window (the projects they follow), the new project-level signals project_signals found in it, the lesson notices on
  their own open drafts (strata.knowledge.lessons.page, the same function as the Lessons tab), and their own drafts in
  Draft. An implementing agency officer, and the agency preview, get the activities behind their planned dates in the
  team's latest plans. The public preview gets the closed projects whose contracts Strata holds, latest to close first,
  with how many of their contracts it traced. As of a past date, the window ends on that date and the lesson lines, the drafts and the strip are left
  out. A preview can only take things away, and a read records nothing.
- POST /api/home/start-here {"visible": false} removes the strip for the viewer, and {"visible": true} shows it again:
  one new row in strata.ops.start_here_choices, written as the app's own service principal, so the choice follows the
  viewer from browser to browser. The view switch's guard refuses it in a preview (403 preview, the roles file's
  start_here capability). GET /api/me says whether the strip shows (start_here_visible), so the page reserves its room
  before it loads.
- GET /api/examples/{key} gives the sentence of a package planned from a sentence in the examples registry
  (config/examples.toml), which "Plan a package from a sentence" fills into the box: the address carries the key, never
  the sentence.

The window is home.window_days in the thresholds file, ending on the data-through date (the freshness stamp's day), or
on the as-of date. Every sentence is a copy-file template (copy.home.server, read from home_copy.json) filled on the
server with tool values; every count word the server chooses. Nothing about a viewer lives in a module global.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from collections.abc import Callable
from decimal import Decimal
from functools import cache
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from strata.config import Examples, Views, load_examples
from strata.dbx import Viewer, viewer_from_headers
from strata.drafts import runtime
from strata.lakehouse.engine import Engine, EngineError, PermissionDenied
from strata.server import uploads as upload_routes
from strata.server import views as view_routes
from strata.server.access import Access, is_author
from strata.server.engines import EngineFor
from strata.server.viewer_sql import data_through
from strata.tools import registry
from strata.tools.check_plan import agency_id as agency_key
from strata.tools.data_readiness_for import fill

log = logging.getLogger("strata.server.home")
HERE = Path(__file__).resolve().parent
SQL = HERE / "sql" / "home"
STAFF, PIU, PUBLIC = view_routes.STAFF, view_routes.PIU, view_routes.PUBLIC
SIGNALS = ("needs_a_look", "watch")
# The project-level signals that become project lines (the 41 brief, section 4.1). The plan checks' signals are left
# out: their activities already show as activity lines when their plan changed.
PROJECT_CHECKS = ("closing_moves", "restructured", "isr_lowered", "disbursement")
# The reasons that put an activity behind its planned dates, for an implementing agency officer's Home.
BEHIND = ("completion_passed_no_contract", "pending_near_closing", "pending_on_closing_day", "pending_after_closing")
LESSON_ORDER = ("retired_wrong", "narrowed", "retired_outdated")
MILLION = Decimal(1_000_000)


@cache
def words() -> dict:
    return json.loads((HERE / "home_copy.json").read_text())


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _close(engine) -> None:
    close = getattr(engine, "close", None)
    if callable(close):
        close()


def _day(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _iso(value) -> str | None:
    day = _day(value)
    return day.isoformat() if day else None


# ── Sentences ────────────────────────────────────────────────────────────

def count_word(number: int, capital: bool = False) -> str:
    """DESIGN.md section 7, rule 12: one to nine in words, numerals from 10, with a capital at a sentence's start."""
    word = words()["words"][number - 1] if 1 <= number <= 9 else f"{number:,}"
    return word[:1].upper() + word[1:] if capital else word


def count(number: int, kind: str | None = None, ids: list[str] | None = None, capital: bool = False) -> dict:
    """A count in a sentence: its value, the word the server chose, and, for the briefing, the kind of thing it counts
    and the ids of what it counts, which its window lists."""
    found = {"count": number, "word": count_word(number, capital)}
    if kind is not None:
        found |= {"kind": kind, "ids": list(ids or [])}
    return found


def form(forms: dict, number: int) -> str:
    return forms["one" if number == 1 else "many"]


def written(amount) -> str | None:
    """A STEP amount as a sentence writes it: to the cent, with a trailing .00 dropped ("300,000", "1,245,092.76")."""
    if amount is None or amount == "":
        return None
    value = Decimal(str(amount))
    text = f"{value:,.2f}"
    return text[:-3] if text.endswith(".00") else text


def _date(value, style: str | None = None) -> dict:
    found = {"date": _iso(value)}
    if style:
        found["style"] = style
    return found


def text_of(segments: list[dict]) -> str:
    """A line's words as plain text, as a test or a screen reader reads them."""
    out = []
    for segment in segments:
        if "text" in segment:
            out.append(segment["text"])
        elif "word" in segment:
            out.append(segment["word"])
        elif "ref" in segment:
            out.append(segment["ref"])
        elif "pid" in segment:
            out.append(segment["pid"])
        elif "written" in segment:
            out.append(segment["written"])
        elif "number" in segment:
            out.append(f"{segment['number']:,}")
        elif "year" in segment:
            out.append(str(segment["year"]))
        elif "date" in segment:
            day = _day(segment["date"])
            out.append(f"{day:%B} {day.day}, {day.year}" if day else "")
    return "".join(out)


# ── The store: the strip, the examples set up and the example lesson versions ──

class HomeStore:
    """What Home keeps per viewer, in strata.ops. engine() opens the engine that reads and writes it, as the app."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    def _run(self, name: str, params: dict):
        engine = self.engine()
        try:
            return engine.run(_query(name), params)
        finally:
            _close(engine)

    @staticmethod
    def _at(at: dt.datetime) -> dt.datetime:
        return at.astimezone(dt.UTC).replace(tzinfo=None)

    def start_here_visible(self, viewer_id: str) -> bool:
        """Whether the viewer keeps the strip: their latest choice, or yes when they never chose."""
        rows = self._run("chosen", {"viewer_id": viewer_id}).rows
        if not rows:
            return True
        value = rows[0][0]
        return value if isinstance(value, bool) else str(value).lower() == "true"

    def choose(self, viewer_id: str, visible: bool, at: dt.datetime) -> None:
        self._run("choose", {"viewer_id": viewer_id, "visible": visible, "chosen_at": self._at(at)})

    def seed(self, viewer_id: str, example_key: str, item_kind: str, item_id: str, at: dt.datetime) -> None:
        """Record one example set up for a viewer, once: a second call for the same example writes nothing."""
        self._run("seed", {"viewer_id": viewer_id, "example_key": example_key, "item_kind": item_kind,
                           "item_id": item_id, "seeded_at": self._at(at)})

    def seeded(self, viewer_id: str) -> list[dict]:
        found = self._run("seeded", {"viewer_id": viewer_id})
        return [dict(zip(found.columns, row)) for row in found.rows]

    def add_lesson_version(self, viewer_id: str, lesson_id: str, version: int, row: dict, at: dt.datetime) -> None:
        self._run("add_lesson_version", {"viewer_id": viewer_id, "lesson_id": lesson_id, "version": version,
                                         "version_row": json.dumps(row, default=str), "seeded_at": self._at(at)})

    def lesson_versions(self, viewer_id: str) -> dict[str, list[dict]]:
        """The example lesson versions only this viewer sees, by lesson id."""
        found: dict[str, list[dict]] = {}
        for lesson_id, _version, row in self._run("lesson_versions", {"viewer_id": viewer_id}).rows:
            found.setdefault(lesson_id, []).append(json.loads(row))
        return found


# ── Lines ────────────────────────────────────────────────────────────────

def strongest(row: dict) -> tuple[str, dict] | None:
    """An activity's strongest signal and that mark's first reason: Needs a look, then Watch."""
    for wanted in SIGNALS:
        for mark in row["marks"]:
            if mark["mark"] == wanted and mark["reasons"]:
                return wanted, mark["reasons"][0]
    return None


def _subject(row: dict, project: dict, first: bool, own: bool) -> list[dict]:
    """How a line names its activity: with its amount, category and project when it opens its plan's group, as "In
    the same plan, {ref}" after that, or by its reference alone on an officer's Home."""
    line = words()["line"]
    ref = {"ref": row["activity_reference_no"]}
    if own:
        return fill(line["own"], {"ref": ref})
    if not first:
        return fill(line["same"], {"ref": ref})
    category = line["categories"].get(row.get("section") or "", line["categoryOther"])
    slots = {"ref": ref, "category": category, "project": project.get("project_name") or project["project_id"],
             "pid": {"pid": project["project_id"]}}
    estimate = row.get("estimated_amount_usd")
    if estimate in (None, ""):
        return fill(line["introNoEstimate"], slots)
    if Decimal(str(estimate)) >= MILLION:
        return fill(line["intro"], {**slots, "millions": {"written": row["estimated_millions"]}})
    return fill(line["introFull"], {**slots, "amount": {"written": written(estimate)}})


def _predicate(code: str, reason: dict) -> list[dict]:
    line = words()["line"]
    if code == "completion_passed_no_contract":
        out = fill(line[code], {"date": _date(reason["planned_completion_on"])})
        if reason.get("closing_date"):
            closed = (reason.get("days_to_close") or 0) < 0
            out += fill(line["closed" if closed else "closes"], {"date": _date(reason["closing_date"])})
        return out
    if code in ("signed_over_estimate", "signed_late_over_estimate"):
        return fill(line[code], {"actual": {"written": written(reason["actual_amount_usd"])},
                                 "estimated": {"written": written(reason["estimated_amount_usd"])}})
    if code == "pending_near_closing":
        days = int(reason["days_to_close"])
        return fill(form(line[code], days), {"days": {"number": days}, "date": _date(reason["closing_date"])})
    if code == "pending_after_closing":
        return fill(line[code], {"date": _date(reason["closing_date"])})
    return fill(line[code], {})


def activity_lines(result: dict, project: dict, own: bool = False, codes: tuple[str, ...] | None = None) -> list[dict]:
    """The lines of one checked plan: each activity marked Needs a look or Watch (or, for an officer, behind its
    planned dates), Needs a look first and then in check_plan's order, the first introducing the activity in full."""
    plan = result["plan"]
    marked = []
    for row in result["rows"]:
        found = strongest(row)
        if found is None or (codes is not None and found[1]["code"] not in codes):
            continue
        marked.append((row, *found))
    marked.sort(key=lambda item: SIGNALS.index(item[1]))
    lines = []
    for index, (row, mark, reason) in enumerate(marked):
        ref = row["activity_reference_no"]
        segments = _subject(row, project, index == 0, own) + _predicate(reason["code"], reason)
        lines.append({
            "kind": "activity", "id": f"line-activity-{ref}", "key": ref, "status": mark, "reason": reason["code"],
            "example": False, "plan": plan["document_id"], "segments": segments,
            "source": {"evidence_id": row["evidence_id"], "kind": "plan", "date": plan["plan_date"],
                       "agency": plan["implementing_agency"], "pid": project["project_id"]},
            "action": {"key": "openActivity", "href": f"/projects/{project['project_id']}/packages/{ref}",
                       "hidden": ref},
            "differs": None})
    return lines


def project_line(row: dict, project: dict, status: str) -> dict | None:
    """A project-level signal as a line (the 41 brief, section 5.3)."""
    line = words()["line"]
    values, pid = row.get("values") or {}, project["project_id"]
    slots = {"project": project.get("project_name") or pid, "pid": {"pid": pid}}
    source = row.get("source") or {}
    check = row["check"]
    if check == "closing_moves":
        segments = fill(line[check], {**slots, "date": _date(source.get("date")), "count": count(int(row["count"])),
                                      "year": {"year": int(values["since_year"])}})
        action, kind = "openProject", "loanHistory"
    elif check == "restructured":
        segments = fill(line[check], {**slots, "date": _date(values.get("latest_on"))})
        action, kind = "seeTimeline", "isr"
    elif check == "isr_lowered":
        segments = fill(line[check], {**slots, "date": _date(values.get("isr_date"))})
        action, kind = "seeTimeline", "isr"
    elif check == "disbursement":
        segments = fill(line[check], {**slots, "date": _date(values.get("as_of_date")),
                                      "percent": {"number": int(values["percent"])},
                                      "millions": {"written": values["available_millions"]},
                                      "months": count(int(values["months_left"]))})
        action, kind = "openProject", "disbursement"
    else:
        return None
    href = f"/projects/{pid}/timeline" if action == "seeTimeline" else f"/projects/{pid}"
    return {"kind": "project", "id": f"line-project-{pid}-{check}", "key": f"{pid}/{check}", "status": status,
            "reason": check, "example": False, "segments": segments, "public_from": row.get("public_from"),
            "source": {"evidence_id": source.get("evidence_id") or row["evidence_id"], "kind": kind,
                       "date": source.get("date"), "pid": pid},
            "action": {"key": action, "href": href, "hidden": pid}, "differs": None}


def _cites(uses: list[dict]) -> list[dict]:
    """Which of the viewer's drafts cite a lesson: the one draft by its kind's phrase, or how many."""
    line = words()["line"]
    drafts = {use["draft_id"]: use for use in uses}
    if len(drafts) > 1:
        return fill(line["lesson"]["several"], {"count": count(len(drafts), capital=True)})
    use = next(iter(drafts.values()))
    subject = use.get("subject") or {}
    # Every kind in config/drafts.toml has its words (tests/test_home.py checks it), so none is named as another.
    template = line["cites"][use["kind"]]
    package = subject.get("package_title") or subject.get("description") or subject.get("activity_reference_no") or ""
    return fill(template, {"agency": subject.get("implementing_agency") or "",
                           "date": _date(subject.get("plan_date"), "short") if subject.get("plan_date") else "",
                           "project": subject.get("project_name") or "", "package": package})


def lesson_line(notice: dict) -> dict:
    """A notice under "Changed where you used it" as a line (the 41 brief, section 5.3)."""
    lesson = words()["line"]["lesson"]
    tier = notice["tier"]
    cites = _cites(notice["uses"])
    drafts = len({use["draft_id"] for use in notice["uses"]})
    if tier == "narrowed":
        segments = fill(lesson["narrowed"], {"statement": notice["statement_a"], "date": _date(notice["decided_on"]),
                                             "cites": cites, "version": {"number": int(notice["a"])}})
    else:
        segments = fill(lesson[tier], {"statement": notice["statement_a"],
                                       "date": _date(notice.get("retired_on") or notice["decided_on"]), "cites": cites,
                                       "drafts": lesson["thatDraft" if drafts == 1 else "thoseDrafts"]})
    return {"kind": "lesson", "id": f"line-lesson-{notice['lesson_id']}-v{notice['a']}",
            "key": f"{notice['lesson_id']}/v{notice['a']}", "status": "changed" if tier == "narrowed" else tier,
            "reason": tier, "example": bool(notice.get("example")), "segments": segments,
            "decided_on": notice["decided_on"],
            "source": {"evidence_id": f"versions:{notice['lesson_id']}:{notice['a']}:{notice['b']}",
                       "kind": "lesson" if tier == "narrowed" else "retired", "version": int(notice["b"])},
            "action": {"key": "seeChange", "href": f"/lessons#{notice['anchor']}", "hidden": notice["statement_a"]},
            "differs": None}


# ── The briefing ─────────────────────────────────────────────────────────

def window_phrase(days: int, as_of: dt.date | None) -> list[dict]:
    found = words()
    if as_of is not None:
        return fill(found["windowAsOf"], {"window": count(days), "date": _date(as_of)})
    return fill(found["window"], {"window": count(days)})


def drafts_sentence(rows: list[dict]) -> list[dict]:
    forms = words()["drafts"]
    total = len(rows)
    if total == 0:
        return fill(forms["none"], {})
    return fill(form(forms, total), {"count": count(total, "drafts", [row["draft_id"] for row in rows], capital=True)})


def staff_briefing(plans: list[dict], lines: list[dict], followed: int, window: list[dict],
                   waiting: list[dict] | None, following: int | None = None,
                   as_of: dt.date | None = None) -> list[list[dict]]:
    """The briefing's sentences, in the order of the lines they count (the 41 brief, section 5.2). waiting is None as of
    a past date, when the drafts sentence is left out. following is how many projects the viewer follows in the follow
    store, and followed how many of those were public by the as-of date, so a viewer whose follows all came later is
    never told they follow none (it defaults to followed)."""
    found = words()
    sentences: list[list[dict]] = []
    activity = [line for line in lines if line["kind"] == "activity"]
    projects = [line for line in lines if line["kind"] == "project"]
    # Lesson lines come from the viewer's own drafts, not their follows, so they are counted on a first run too.
    changed = [line for line in lines if line["kind"] == "lesson" and line["status"] == "changed"]
    retired = [line for line in lines if line["kind"] == "lesson" and line["status"] != "changed"]
    following = followed if following is None else following
    if not following:
        sentences.append(fill(found["firstRun"], {}))
    elif not followed:
        sentences.append(fill(form(found["notPublicYet"], following),
                              {"count": count(following), "date": _date(as_of)}))
    elif not plans and not projects and not changed and not retired:
        sentences.append(fill(form(found["quiet"], followed), {"count": count(followed), "window": window}))
    else:
        if plans:
            sentences.append(fill(form(found["plans"], len(plans)), {
                "count": count(len(plans), "plans", [plan["document_id"] for plan in plans], capital=True),
                "window": window}))
            look = [line["id"] for line in activity if line["status"] == "needs_a_look"]
            watch = [line["id"] for line in activity if line["status"] == "watch"]
            verbs = found["activities"]
            its = form(verbs["its"], len(plans))
            if look and watch:
                template, slots = verbs["lookAndWatch"], {
                    "look": count(len(look), "look", look, capital=True), "watch": count(len(watch), "watch", watch),
                    "its": its, "needs": form(verbs["needs"], len(look)), "is": form(verbs["is"], len(watch))}
            elif look:
                template, slots = verbs["lookOnly"], {"look": count(len(look), "look", look, capital=True),
                                                      "its": its, "needs": form(verbs["needs"], len(look))}
            elif watch:
                template, slots = verbs["watchOnly"], {"watch": count(len(watch), "watch", watch, capital=True),
                                                       "its": its, "is": form(verbs["is"], len(watch))}
            else:
                template, slots = verbs["none"], {"its": its}
            sentences.append(fill(template, slots))
        else:
            sentences.append(fill(found["plans"]["none"], {"window": window}))
        if projects:
            sentences.append(fill(form(found["projects"], len(projects)), {
                "count": count(len(projects), "projects", [line["id"] for line in projects], capital=True)}))
    if changed:
        sentences.append(fill(form(found["lessonsChanged"], len(changed)), {
            "count": count(len(changed), "lessonsChanged", [line["id"] for line in changed], capital=True)}))
    if retired:
        sentences.append(fill(form(found["lessonsRetired"], len(retired)), {
            "count": count(len(retired), "lessonsRetired", [line["id"] for line in retired], capital=True)}))
    if waiting is not None:
        sentences.append(drafts_sentence(waiting))
    return sentences


# ── The routes ───────────────────────────────────────────────────────────

class StartHereRequest(BaseModel):
    visible: bool
    view: str = STAFF


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, access: Access, views: Callable[[], Views],
               thresholds, today: Callable[[], dt.date], now: Callable[[], dt.datetime], reference: Callable[[], str],
               store: HomeStore | None, follows, drafts, lessons_page, examples: Callable[[], Examples] = load_examples,
               environ=None) -> Callable[[Viewer, str, bool, dt.date | None], bool]:
    """Home's routes. follows is the follow store (ticket 37), drafts the draft store (ticket 35) and lessons_page the
    Lessons page's server (ticket 39). It gives back start_here_visible(viewer, own, preview, as_of) for GET /api/me."""

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def refused(status: int, code: str, **details) -> JSONResponse:
        return JSONResponse({"code": code, "error": code, **details}, status_code=status,
                            headers={"Cache-Control": "no-store"})

    def start_here_visible(viewer: Viewer, own: str, preview: bool, as_of: dt.date | None) -> bool:
        """The strip shows for World Bank staff in their own view, today, until they remove it."""
        if own != STAFF or preview or as_of is not None or not viewer.user_id or not access.is_staff(viewer):
            return False
        if store is None:
            return True
        try:
            return store.start_here_visible(viewer.user_id)
        except EngineError:
            log.exception("I could not read whether %s keeps the Start here strip.", viewer.user_id)
            return True

    def window_days() -> int:
        return int(thresholds.value("home.window_days"))

    def in_view() -> int:
        return int(thresholds.value("home.lines_in_view"))

    def seeded_ids(viewer: Viewer) -> dict[str, dict]:
        if store is None or not viewer.user_id:
            return {}
        try:
            return {row["example_key"]: row for row in store.seeded(viewer.user_id) if row.get("example_key")}
        except EngineError:
            log.exception("I could not read the examples set up for %s.", viewer.user_id)
            return {}

    def example_drafts(seeded: dict[str, dict]) -> set[str]:
        return {row.get("item_id") for row in seeded.values() if row.get("item_kind") == "draft"}

    def own_drafts(viewer: Viewer) -> list:
        if drafts is None or not viewer.user_id:
            return []
        return [draft for draft in drafts.for_team(access.team(viewer).key, viewer.user_id)
                if is_author(viewer, draft.author_id)]

    def waiting_rows(viewer: Viewer, mine: list, examples_seeded: set[str]) -> list[dict]:
        rows = []
        for draft in mine:
            if draft.state.state != "draft":
                continue
            ids = [entry["evidence_id"] for entry in runtime.sources(draft.content)]
            opened = drafts.opened_since(viewer.user_id or "", ids, draft.created_at)
            row = runtime.list_row(draft, viewer, opened)
            row["example"] = draft.draft_id in examples_seeded
            rows.append(row)
        rows.sort(key=lambda row: row["changed"]["at"], reverse=True)
        return rows

    def plan_check(engine: Engine, viewer: Viewer, view: str, as_of: dt.date, project_id: str, agency: str,
                   plan_date) -> dict:
        return registry.call("check_plan", {"project_id": project_id, "implementing_agency": agency,
                                            "plan_date": _iso(plan_date)},
                             registry.Context(engine, viewer, view, as_of, thresholds=thresholds, environ=environ))

    def lesson_notices(engine: Engine, viewer: Viewer, mine: list) -> list[dict]:
        """"Changed where you used it" for the viewer's own open drafts, with their example lesson versions, through
        the Lessons tab's own function, never a second computation."""
        if lessons_page is None or not mine:
            return []
        extra = store.lesson_versions(viewer.user_id) if store is not None and viewer.user_id else {}
        return lessons_page.notices_for(engine, mine, extra)

    def staff_home(engine: Engine, viewer: Viewer, as_of: dt.date | None, start_here: bool) -> dict:
        day = as_of or today()
        end = as_of or data_through(engine) or day
        days = window_days()
        start = end - dt.timedelta(days=days - 1)
        # following is the follow store's answer; followed narrows it to the projects public by the as-of date
        # (ADR 0002). The two stay apart so a viewer whose follows all came later is not read as following none.
        following = follows.followed(viewer.user_id) if follows is not None and viewer.user_id else {}
        followed = following
        if as_of is not None and following:
            public = {row[0] for row in engine.run(_query("public_projects"), {"as_of": as_of}).rows}
            followed = {project_id: at for project_id, at in following.items() if project_id in public}
        found = engine.run(_query("plans_disclosed"), {"start": start, "end": end})
        disclosed = [dict(zip(found.columns, row)) for row in found.rows]
        plans, lines, partial = [], [], 0
        for version in disclosed:
            if version["project_id"] not in followed:
                continue
            result = plan_check(engine, viewer, STAFF, day, version["project_id"], version["implementing_agency"],
                                version["plan_date"])
            if result.get("abstention") is not None or not result.get("plan"):
                continue
            project = result["project"] or {"project_id": version["project_id"]}
            plans.append({"document_id": result["plan"]["document_id"], "project_id": project["project_id"],
                          "project_name": project.get("project_name"),
                          "implementing_agency": result["plan"]["implementing_agency"],
                          "agency_id": result["plan"]["agency_id"], "plan_date": result["plan"]["plan_date"],
                          "disclosed_on": result["plan"]["disclosed_on"]})
            lines += activity_lines(result, project)
            partial += int(result["counts"].get("not_fully_checked") or 0)
        projects_lines = []
        for project_id in sorted(followed):
            signals = registry.call("project_signals", {"project_id": project_id},
                                    registry.Context(engine, viewer, STAFF, day, thresholds=thresholds,
                                                     environ=environ))
            status = signals.get("status")
            if status not in SIGNALS:
                continue
            for row in signals["rows"]:
                if row["check"] in PROJECT_CHECKS and start <= _day(row["public_from"]) <= end:
                    line = project_line(row, signals["project"], status)
                    if line is not None:
                        projects_lines.append(line)
        projects_lines.sort(key=lambda line: line["public_from"] or "", reverse=True)
        projects_lines.sort(key=lambda line: SIGNALS.index(line["status"]))
        seeded = seeded_ids(viewer) if as_of is None else {}
        mine = own_drafts(viewer) if as_of is None else []
        lesson_lines = []
        if as_of is None:
            notices = lesson_notices(engine, viewer, mine)
            lesson_lines = [lesson_line(notice) for notice in notices]
            lesson_lines.sort(key=lambda line: line["decided_on"] or "", reverse=True)
            lesson_lines.sort(key=lambda line: LESSON_ORDER.index(line["reason"]))
        lines = lines + projects_lines + lesson_lines
        waiting = waiting_rows(viewer, mine, example_drafts(seeded)) if as_of is None else None
        window = window_phrase(days, as_of)
        sentences = staff_briefing(plans, lines, len(followed), window, waiting, following=len(following), as_of=as_of)
        lesson_notice = ""
        if "lesson_change" in seeded:
            lesson_id, cited, _version = seeded["lesson_change"]["item_id"].split(":")
            lesson_notice = f"#notice-{lesson_id}-v{cited}"
        chosen = examples()
        # The examples are World Bank staff's alone: anyone else gets no links, so the page never reads a strip they
        # never had as one they removed.
        links = (chosen.links(agency_key(chosen.demo_plan.implementing_agency), lesson_notice)
                 if access.is_staff(viewer) else [])
        # A plan that changed with nothing marked is not a quiet window: the briefing has just said it changed.
        empty = None if lines else ("first_run" if not following else "nothing_marked" if plans else "quiet")
        return {
            "view": STAFF, "preview": False, "today": day.isoformat(), "as_of": _iso(as_of),
            "window": {"days": days, "start": start.isoformat(), "end": end.isoformat(),
                       "data_through": end.isoformat() if as_of is None else None, "phrase": window},
            "briefing": {"sentences": sentences, "plans": plans},
            "start_here": {"visible": start_here, "links": links},
            "worth": {"kind": "staff", "lines": lines, "fold_after": in_view(), "partial": partial or None,
                      "checked_on": day.isoformat(), "through": end.isoformat(), "empty": empty,
                      "followed": len(followed)},
            "waiting": waiting_block(waiting, "asof" if as_of is not None else None),
            "public": None,
        }

    def waiting_block(rows: list[dict] | None, reason: str | None) -> dict:
        if rows is None:
            return {"rows": [], "total": 0, "more": False, "reason": reason}
        most = in_view()
        return {"rows": rows[:most], "total": len(rows), "more": len(rows) > most, "reason": None}

    def agency_home(engine: Engine, viewer: Viewer, agency: str, preview: bool, as_of: dt.date | None) -> dict:
        day = as_of or today()
        view = PIU
        listed = [project for project in upload_routes.agency_projects(engine, agency, day) if project["latest_plan"]]
        lines, checked = [], []
        for project in listed:
            plan = project["latest_plan"]
            result = plan_check(engine, viewer, view, day, project["project_id"], plan["agency_id"], plan["plan_date"])
            if result.get("abstention") is not None:
                continue
            shown = result["project"] or {"project_id": project["project_id"]}
            checked.append({"project_id": project["project_id"], "project_name": shown.get("project_name"),
                            "plan_date": plan["plan_date"], "document_id": result["plan"]["document_id"]})
            lines += activity_lines(result, shown, own=True, codes=BEHIND)
        found = words()["agency"]
        sentences: list[list[dict]] = []
        if not checked:
            sentences.append(fill(found["noPlan"], {}))
        else:
            if len(checked) == 1:
                one = checked[0]
                sentences.append(fill(found["plan"], {"date": _date(one["plan_date"]), "project": one["project_name"] or "",
                                                      "pid": {"pid": one["project_id"]}}))
            else:
                sentences.append(fill(found["plans"], {"count": count(len(checked))}))
            behind = [line["id"] for line in lines]
            its = form(words()["activities"]["its"], len(checked))
            if behind:
                sentences.append(fill(form(found["behind"], len(behind)),
                                      {"count": count(len(behind), "behind", behind, capital=True), "its": its}))
            else:
                sentences.append(fill(found["behind"]["none"], {"its": its}))
        waiting = None
        reason = None
        if preview:
            reason = "preview"
        elif as_of is not None:
            reason = "asof"
        else:
            waiting = waiting_rows(viewer, own_drafts(viewer), set())
            sentences.append(drafts_sentence(waiting))
        through = as_of or data_through(engine) or day
        return {
            "view": PIU, "preview": preview, "today": day.isoformat(), "as_of": _iso(as_of),
            "window": None, "briefing": {"sentences": sentences, "plans": checked},
            "start_here": {"visible": False, "links": []},
            "worth": {"kind": "agency", "lines": lines, "fold_after": in_view(), "partial": None,
                      "checked_on": day.isoformat(), "through": through.isoformat(),
                      "empty": None if lines else ("no_plan" if not checked else "nothing_behind"),
                      "agency": {"name": agency, "agency_id": agency_key(agency)}},
            "waiting": waiting_block(waiting, reason),
            "public": None,
        }

    def public_home(engine: Engine, viewer: Viewer, as_of: dt.date | None) -> dict:
        day = as_of or today()
        most = in_view()
        totals = engine.run(_query("projects_held"), {"as_of": day})
        total = int(totals.rows[0][0]) if totals.rows else 0
        found = engine.run(_query("closed_projects"), {"as_of": day})
        rows = [dict(zip(found.columns, row)) for row in found.rows][:most]
        line = words()["line"]["public"]
        lines = []
        for row in rows:
            pid = row["project_id"]
            segments = fill(line, {"project": row["project_name"] or pid, "pid": {"pid": pid},
                                   "country": row["country_name"] or row["country_code"] or "",
                                   "date": _date(row["closing_date"]), "traced": {"number": int(row["traced"])},
                                   "contracts": {"number": int(row["contracts"])}})
            lines.append({"kind": "public", "id": f"line-public-{pid}", "key": pid, "status": "closed",
                          "reason": "closed", "example": False, "segments": segments,
                          "source": {"evidence_id": f"strata.gold.project:{pid}", "kind": "record", "pid": pid},
                          "action": {"key": "seeContracts", "href": f"/projects/{pid}/procurement#packages",
                                     "hidden": row["project_name"] or pid},
                          "differs": None})
        public = words()
        sentence = (fill(form(public["public"], len(lines)), {"total": {"number": total}, "count": count(len(lines))})
                    if lines else fill(public["publicNone"], {"total": {"number": total}}))
        through = as_of or data_through(engine) or day
        return {
            "view": PUBLIC, "preview": True, "today": day.isoformat(), "as_of": _iso(as_of), "window": None,
            "briefing": {"sentences": [sentence], "plans": []},
            "start_here": {"visible": False, "links": []},
            "worth": {"kind": "public", "lines": lines, "fold_after": most, "partial": None,
                      "checked_on": day.isoformat(), "through": through.isoformat(),
                      "empty": None if lines else "no_closed"},
            "waiting": {"rows": [], "total": 0, "more": False, "reason": "public"},
            "public": {"total": total},
        }

    def read_home(viewer: Viewer, build: Callable[[Engine], dict]):
        if engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            with engine_for(viewer) as engine:
                return JSONResponse(build(engine), headers={"Cache-Control": "no-store"})
        except PermissionDenied:
            return JSONResponse({"code": "permission"}, status_code=403)
        except EngineError:
            ref = reference()
            log.exception("The data service failed on Home, reference %s.", ref)
            return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)

    @app.get("/api/home")
    def home(request: Request, view: str = STAFF, asof: dt.date | None = None,
             viewer: Viewer = Depends(current_viewer)):
        agency = access.agency(viewer)
        own = PIU if agency else STAFF
        # ViewParams keeps ?view= only for a preview the person may have (ticket 40), so piu or public here is one.
        preview = view in view_routes.PREVIEWS and view != own
        as_of = asof if asof is not None and asof < today() else None
        if view == PUBLIC:
            return read_home(viewer, lambda engine: public_home(engine, viewer, as_of))
        if view == PIU or own == PIU:
            shown = views().preview_agency if preview else agency
            return read_home(viewer, lambda engine: agency_home(engine, viewer, shown, preview, as_of))
        strip = start_here_visible(viewer, own, False, as_of)
        return read_home(viewer, lambda engine: staff_home(engine, viewer, as_of, strip))

    @app.post("/api/home/start-here")
    def choose_start_here(body: StartHereRequest, viewer: Viewer = Depends(current_viewer)):
        # A preview never reaches here: the view switch's guard refuses it (the roles file's start_here capability).
        if not viewer.user_id:
            return refused(401, "no_identity")
        if store is None:
            return refused(503, "not_recorded")
        try:
            store.choose(viewer.user_id, body.visible, now())
        except EngineError:
            ref = reference()
            log.exception("I could not record %s's Start here choice, reference %s.", viewer.user_id, ref)
            return refused(503, "data_service", trace_id=ref)
        return {"recorded": True, "visible": body.visible}

    @app.get("/api/examples/{key}")
    def example_sentence(key: str):
        sentence = examples().sentences.get(key)
        if sentence is None:
            return refused(404, "unknown_example")
        return {"key": key, "sentence": sentence}

    return start_here_visible
