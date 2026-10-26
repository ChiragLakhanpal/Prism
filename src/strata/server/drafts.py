"""The draft routes (ticket 35): writing review notes, the draft page, its acts and files, and the Drafts tab.

- POST /api/drafts takes {"kind": "review_notes", "project_id": "P156634", "agency_id": "...",
  "plan_date": "2026-10-09", "idempotency_key": "...", "view": "staff"} and streams the writing as
  text/event-stream: step events (read, write, check, save), then a draft event with the saved draft's
  id, or a nothing_survived event with the removed sentences when none passed the checks (and nothing
  is saved), or an error event with a code from WRITE_ERRORS, and last a done event with the run id.
  A second request with the same idempotency key opens the same draft and writes nothing.
- GET /api/drafts lists the viewer's team's drafts and the viewer's own in three groups, to_check, checked
  and exported, newest first by their last change, and the viewer's own discarded drafts.
- GET /api/drafts/existing?kind=&project_id=&agency_id=&plan_date= names the newest draft of that kind
  the viewer's team has open (in Draft or Checked by you) on that plan version, or null. With no plan_date,
  it answers {"by_plan_date": {...}}: the newest open draft on each version of that agency's plans.
- GET /api/drafts/{draft_id} gives one draft as its page shows it, with how many of its sources the
  viewer opened since it was saved, and the holds that keep it from export.
- POST /api/drafts/{draft_id}/{check|export|discard|restore} takes {"expected_state": "draft",
  "view": "staff"} and moves the draft on, answering with the draft as its page now shows it. Export
  makes the Word file and the evidence pack's PDF and CSV, keeps them with the export record, and sends
  nothing anywhere.
- GET /api/drafts/{draft_id}/files/{name} downloads one of those files.

Every read and act asks the one access rule (src/strata/server/access.py): an author always sees their
own drafts, a draft another team made is not found, and only its author acts. A refusal says why in the shape later tickets build on: 403
with error not_author, or preview with its capability and the copy key of its reason (the 40 brief),
409 with error stale or draft_state and the state the draft is in now (the 39 brief), or held with the
holds left. App state is written by the app's own service principal, like the opened sources it reads.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import threading
from collections.abc import AsyncIterator, Callable
from typing import Literal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from strata.agent.answer_check import SixChecks
from strata.agent.runs import RunLog, run_row
from strata.config import DraftKinds
from strata.dbx import Viewer, viewer_from_headers
from strata.drafts import files as draft_files
from strata.drafts import runtime
from strata.drafts.store import DraftStore, NewExport, Saved, Stale
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event, Scope, TraceIds, Turn
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.packages.store import PackageStore
from strata.server import uploads as upload_routes
from strata.server.access import Access, is_author
from strata.server.engines import EngineFor
from strata.uploads.store import UploadStore

log = logging.getLogger("strata.server.drafts")
STAFF = "staff"
PLANNED_PREFIX = "pkg-"  # a planned package's id (src/strata/server/packages.py, new_package_id); a STEP reference never starts so
VIEWS = Literal["staff", "piu", "public"]
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
GROUPS = {"draft": "to_check", "checked": "checked", "exported": "exported"}
KEEP_ALIVE = ": keep-alive\n\n"


class DraftRequest(BaseModel):
    kind: str = Field(min_length=1, max_length=64)
    # Suggested PPSD rows (ticket 36) name a package, which may have no project yet.
    project_id: str | None = Field(default=None, pattern=r"^P\d{6}$")
    # The plan version review notes and a Project Paper summary are written on; a mission brief (ticket 37) names
    # only its project.
    agency_id: str | None = Field(default=None, min_length=1, max_length=200)
    plan_date: dt.date | None = None
    # Suggested PPSD rows (ticket 36): the package, by its STEP reference or a planned package's id, and for a
    # package from a STEP row, section 1's criteria as find_comparables' own parameter names. The server reads the
    # risks selected in section 3 itself; the request never carries risk keys.
    package: str | None = Field(default=None, min_length=1, max_length=128)
    criteria: dict[str, str | int | float] | None = None
    # Planned dates (ticket 38): what they are drafted from, by id only, never a file name or the file's words:
    # upload:{upload_id} for the team's upload, or plan:{project_id}:{agency_id}:{plan_date} for a published plan.
    source: str | None = Field(default=None, min_length=1, max_length=300)
    idempotency_key: str | None = Field(default=None, max_length=128)
    view: VIEWS = "staff"
    lang: Literal["en", "fr", "es", "pt"] = "en"


class ActRequest(BaseModel):
    expected_state: Literal["draft", "checked", "exported", "discarded"]
    view: VIEWS = "staff"


class FieldRequest(BaseModel):
    """A value a person sets on a field only people fill (ticket 36), or its removal (value null)."""

    row_key: str = Field(max_length=128)
    field: str = Field(min_length=1, max_length=64)
    value: str | None = Field(default=None, max_length=500)
    view: VIEWS = "staff"


class FormRequest(BaseModel):
    form: str = Field(min_length=1, max_length=32)
    view: VIEWS = "staff"


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def refused(status: int, code: str, **details) -> JSONResponse:
    """A refusal, with its code under both names the screens and later tickets read."""
    return JSONResponse({"code": code, "error": code, **details}, status_code=status,
                        headers={"Cache-Control": "no-store"})


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, store: DraftStore | None, access: Access,
               writers: Callable[[str], object | None], kinds: DraftKinds, today: Callable[[], dt.date],
               now: Callable[[], dt.datetime], new_draft_id: Callable[[], str], new_run_id: Callable[[], str],
               runs: RunLog | None, trace_ids: Callable[[], TraceIds], reference: Callable[[], str],
               heartbeat_seconds: float, six_checks: SixChecks, packages: PackageStore | None = None,
               planned_view: Callable[[object], dict] | None = None, uploads: UploadStore | None = None) -> None:
    """six_checks runs the verifier's checks 4 to 6 on every draft, with the app's judge, as the answer stream does.
    packages keeps planned packages and each viewer's risk selection (ticket 30), which suggested PPSD rows read;
    planned_view shows a planned package as the package workspace does (strata.packages.workflow.package_view)."""
    running: set[tuple[str, str]] = set()  # (author, idempotency key) of the drafts being written now
    lock = threading.Lock()

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def guarded(what: str, act: Callable[[], object]):
        """One use of the store, or the error a page can show: no store, the store refused, or the data
        service. The app's own account reads and writes drafts, so a refusal is its grant, not the viewer's."""
        if store is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            return act()
        except PermissionDenied:
            ref = reference()
            log.exception("The app's account was refused on %s, reference %s.", what, ref)
            return JSONResponse({"code": "draft_store", "trace_id": ref}, status_code=503)
        except EngineError:
            ref = reference()
            log.exception("The data service failed on %s, reference %s.", what, ref)
            return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)

    def readable(viewer: Viewer, draft_id: str) -> Saved | None:
        saved = store.get(draft_id)
        return saved if saved is not None and access.may_read(viewer, saved.team_key, saved.author_id) else None

    def opened_by(viewer_id: str | None, saved: Saved) -> dict[str, dt.datetime]:
        ids = [entry["evidence_id"] for entry in runtime.sources(saved.content)]
        return store.opened_since(viewer_id or "", ids, saved.created_at)

    def shown(saved: Saved, viewer: Viewer, view: str) -> dict:
        return runtime.draft_view(saved, viewer, view, kinds, opened_by(viewer.user_id, saved))

    # ── Writing ──────────────────────────────────────────────────────────

    @app.post("/api/drafts")
    async def start_draft(body: DraftRequest, viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        if body.kind not in kinds.kinds:
            return refused(422, "unknown_kind")
        if kinds.kinds[body.kind].staff_only and not access.is_staff(viewer):
            return refused(403, "not_staff")
        if kinds.kinds[body.kind].agency_only and access.agency(viewer) is None:
            return refused(403, "not_agency_team")
        if store is None or engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        key = body.idempotency_key
        if key:
            made = guarded("an earlier draft", lambda: store.by_key(viewer.user_id, key))
            if isinstance(made, JSONResponse):
                return made
            if made is not None:
                return StreamingResponse(_already(made, new_run_id()), media_type="text/event-stream",
                                         headers=STREAM_HEADERS)
            with lock:
                if (viewer.user_id, key) in running:
                    return refused(409, "in_progress")
                running.add((viewer.user_id, key))
        request = {"kind": body.kind, "project_id": body.project_id, "agency_id": body.agency_id,
                   "plan_date": body.plan_date.isoformat() if body.plan_date else None}
        prepared = prepare(body, viewer)
        if isinstance(prepared, JSONResponse):
            if key:
                with lock:
                    running.discard((viewer.user_id, key))
            return prepared
        request |= prepared
        writing = runtime.Writing(kinds.kinds[body.kind], request, viewer, access.team(viewer).key, key,
                                  new_run_id(), body.lang)
        return StreamingResponse(_stream(writing, trace_ids()), media_type="text/event-stream", headers=STREAM_HEADERS)

    def prepare(body: DraftRequest, viewer: Viewer) -> dict | JSONResponse:
        """What a kind's workflow reads beside the viewer's tables, by the kind's writer, so a kind registered with
        an existing writer, such as ticket 38's agency variant of suggested PPSD rows, is prepared as that writer's
        kind (CLAUDE.md rule 9): for suggested PPSD rows, the package and the risks the viewer selected in section 3,
        from the package store; for a Project Paper summary, the PPSD rows the viewer's team checked for the
        project's packages, from the drafts store (ticket 36)."""
        by_writer = {"strata.drafts.ppsd_rows": ppsd_request, "strata.drafts.project_paper": paper_request,
                     "strata.drafts.step_rows": dates_request}
        prepared = by_writer.get(kinds.kinds[body.kind].writer)
        if prepared is not None:
            return prepared(body, viewer)
        if not body.project_id:
            return refused(422, "no_project")
        return {}

    def dates_request(body: DraftRequest, viewer: Viewer) -> dict | JSONResponse:
        """Planned dates (ticket 38): the team's upload, read here through the one access rule, so the writer and its
        tools get that upload and nothing else; or the officer's own agency's published plan. Another team's upload
        is not found, as it is on every route; another agency's plan is refused."""
        source = body.source or ""
        if source.startswith("upload:"):
            if uploads is None:
                return JSONResponse({"code": "no_data_service"}, status_code=503)
            try:
                saved = upload_routes.readable(uploads, access, viewer, source.removeprefix("upload:"))
            except EngineError:
                ref = reference()
                log.exception("The data service failed on the upload of %s, reference %s.", viewer.user_id, ref)
                return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)
            if saved is None:
                return refused(404, "unknown_upload")
            return {"project_id": saved.project_id, "agency_id": None, "plan_date": None,
                    "upload": upload_routes.as_mapping(saved)}
        parts = source.split(":")
        if len(parts) != 4 or parts[0] != "plan":
            return refused(422, "no_plan")
        _, project_id, agency, plan_date = parts
        try:
            dt.date.fromisoformat(plan_date)
        except ValueError:
            return refused(422, "no_plan")
        from strata.tools.check_plan import agency_id

        if agency_id(access.agency(viewer) or "") != agency:
            return refused(403, "not_own_agency")
        return {"project_id": project_id, "agency_id": agency, "plan_date": plan_date}

    def paper_request(body: DraftRequest, viewer: Viewer) -> dict | JSONResponse:
        if not body.project_id or not body.agency_id or not body.plan_date:
            return refused(422, "no_plan")
        found = guarded("the team's checked PPSD rows", lambda: checked_ppsd_rows(viewer, body.project_id))
        return found if isinstance(found, JSONResponse) else {"ppsd": found}

    def ppsd_request(body: DraftRequest, viewer: Viewer) -> dict | JSONResponse:
        if not body.package:
            return refused(422, "no_package")
        if packages is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            saved = packages.get(body.package) if body.package.startswith(PLANNED_PREFIX) else None
            if body.package.startswith(PLANNED_PREFIX) and (saved is None or saved.author_id != viewer.user_id):
                return refused(404, "unknown_package")
            kind, key = ("planned", body.package) if saved else ("step_reference", body.package)
            selected = packages.selected_risks(viewer.user_id, kind, key)
        except Exception:  # Lakebase or the network: nothing is drafted from a selection I can't read
            ref = reference()
            log.exception("I could not read %s's risk selection for %s, reference %s.", viewer.user_id, body.package, ref)
            return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)
        if saved is None:
            return {"package": {"step_reference": body.package}, "criteria": dict(body.criteria or {}),
                    "selected": selected, "words": None, "missing": []}
        shown = planned_view(saved) if planned_view else {"fields": [], "comparables_query": None, "missing": []}
        values = {entry["key"]: entry["value"] for entry in shown["fields"]}
        title = values.get("description") or saved.sentence
        return {"package": {"package_id": saved.package_id, "step_reference": None, "title": title,
                            "project_id": None, "project_name": None, "category": values.get("category"),
                            "country": values.get("country"), "estimated_amount_usd": values.get("estimated_amount_usd")},
                "criteria": shown["comparables_query"], "words": title, "missing": shown["missing"],
                "selected": selected}

    def checked_ppsd_rows(viewer: Viewer, project_id: str) -> list[dict]:
        """The suggested PPSD rows the viewer's team checked or exported for this project's packages, each draft with
        its rows' kept sentences and the records they cite (the 36 brief, 5.7). A draft still in Draft is left out."""
        found = []
        for draft in store.for_team(access.team(viewer).key, viewer.user_id):
            subject = draft.content["subject"]
            if (draft.kind != "ppsd_rows" or draft.state.state not in ("checked", "exported")
                    or subject.get("project_id") != project_id):
                continue
            checked = draft.last("checked")
            notes = {note["key"]: note for note in draft.content["notes"]}
            rows = [{"risk_label": row["risk_label"], "row_key": row["row_key"],
                     "sentences": [sentence for cell in row["cells"].values()
                                   for sentence in (notes.get(cell) or {}).get("sentences") or ()]}
                    for row in draft.content["ppsd"]["rows"]]
            cited = {evidence for row in rows for sentence in row["sentences"] for evidence in sentence["evidence_ids"]}
            found.append({"draft_id": draft.draft_id, "package_title": subject.get("package_title"),
                          "checked_by": checked.actor_name if checked else None,
                          "checked_at": runtime.iso(checked.changed_at) if checked else None, "rows": rows,
                          "evidence": {key: value for key, value in draft.content["evidence"].items() if key in cited}})
        return found

    async def _already(draft_id: str, run_id: str) -> AsyncIterator[str]:
        yield frame(Event("draft", {"draft_id": draft_id}))
        yield frame(Event("done", {"run_id": run_id}))

    async def _stream(writing: runtime.Writing, trace: TraceIds) -> AsyncIterator[str]:
        """The writing's events, then its row in the run log, even when the person stops it part way."""
        started, outcome = dt.datetime.now(dt.UTC), {"error_code": "stopped"}
        try:
            async for chunk in _events(writing, trace, outcome):
                yield chunk
        finally:
            if writing.idempotency_key:
                with lock:
                    running.discard((writing.viewer.user_id, writing.idempotency_key))
            row = _run_row(writing, trace, outcome["error_code"], started)
            if runs is not None:  # its own thread, so a dropped connection cannot stop the write
                writer = threading.Thread(target=runs.record, args=(row,), name=f"strata-run-{writing.run_id}")
                writer.start()
                await asyncio.to_thread(writer.join, 60)

    async def _events(writing: runtime.Writing, trace: TraceIds, outcome: dict) -> AsyncIterator[str]:
        error_code = None
        try:
            events = runtime.write(writing, engine_for, writers, store, today(), now, new_draft_id, six_checks)
            async for item in with_heartbeats(events, heartbeat_seconds):
                yield KEEP_ALIVE if item is HEARTBEAT else frame(item)
        except runtime.WriteError as error:
            error_code = error.code if error.code in runtime.WRITE_ERRORS else "internal"
            log.warning("Run %s could not write a draft (%s).", writing.run_id, error.code)
            yield frame(Event("error", {"code": error_code}))
        except Exception:
            error_code = "internal"
            log.exception("Run %s failed while writing a draft.", writing.run_id)
            yield frame(Event("error", {"code": "internal"}))
        outcome["error_code"] = error_code or (None if writing.draft_id else "no_answer")
        done = {"run_id": writing.run_id}
        if trace.application_insights or trace.mlflow:
            done["trace_ids"] = {"application_insights": trace.application_insights, "mlflow": trace.mlflow}
        yield frame(Event("done", done))

    def _run_row(writing: runtime.Writing, trace: TraceIds, error_code: str | None, started: dt.datetime) -> dict:
        """The writer's run for strata.ops.agent_runs, in the shape the answer stream logs its runs. Every account user
        can read that table, so an implementing agency team's run keeps the kind's key for its question and only each
        removed sentence's reason, never the team's words (CLAUDE.md rule 8)."""
        private = writing.kind.agency_only
        turn = Turn(question=writing.kind.key if private else (writing.question or writing.kind.key),
                    viewer=writing.viewer, run_id=writing.run_id,
                    scope=Scope(chip=writing.request.get("project_id"), as_of=today(), language=writing.language),
                    trace=trace)
        turn.notes.agent, turn.notes.agent_version, turn.notes.as_of = writing.agent, writing.agent_version, today()
        row = run_row(turn, writing.verdict, error_code, started, dt.datetime.now(dt.UTC))
        if private:
            row["removed"] = json.dumps([{"reason": sentence.reasons[0].code}
                                         for sentence in (writing.verdict.removed if writing.verdict else [])])
        return row

    # ── The Drafts tab ───────────────────────────────────────────────────

    @app.get("/api/drafts")
    def list_drafts(view: VIEWS = "staff", viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")

        def read():
            team = access.team(viewer)
            saved = store.for_team(team.key, viewer.user_id)
            groups: dict[str, list[dict]] = {group: [] for group in GROUPS.values()}
            discarded = []
            for draft in saved:
                state = draft.state.state
                mine = is_author(viewer, draft.author_id)
                if state == "discarded":
                    if mine:
                        discarded.append(runtime.list_row(draft, viewer, None))
                    continue
                opened = opened_by(viewer.user_id, draft) if mine and state == "draft" else None
                groups[GROUPS[state]].append(runtime.list_row(draft, viewer, opened))
            for rows in [*groups.values(), discarded]:
                rows.sort(key=lambda row: row["changed"]["at"], reverse=True)
            return {"groups": groups, "counts": {group: len(rows) for group, rows in groups.items()},
                    "discarded": discarded, "discarded_count": len(discarded),
                    "total": sum(len(rows) for rows in groups.values()) + len(discarded)}
        return guarded("the team's drafts", read)

    @app.get("/api/drafts/existing")
    def existing_draft(kind: str = Query(max_length=64), project_id: str | None = Query(None, max_length=16),
                       agency_id: str | None = Query(None, max_length=200), plan_date: dt.date | None = Query(None),
                       package: str | None = Query(None, max_length=128), viewer: Viewer = Depends(current_viewer)):
        """The newest open draft of that kind on that plan version, or, with no plan date, on each version of
        that agency's plans, by its date: the plan check with no version in its address asks before it knows
        which version it shows, so the answer is there by the time the check is (the 35 review). With a package,
        the newest open draft of suggested PPSD rows on that package (ticket 36)."""
        if not viewer.user_id:
            return refused(401, "no_identity")

        def named(draft: Saved) -> dict:
            return {"draft_id": draft.draft_id, "created_at": runtime.iso(draft.created_at),
                    "author": {"name": draft.author_name, "you": is_author(viewer, draft.author_id)}}

        def on_package():
            found = None
            for draft in store.for_team(access.team(viewer).key, viewer.user_id):
                subject = draft.content["subject"]
                if (draft.kind == kind and draft.state.state in runtime.OPEN_STATES
                        and package in (subject.get("package_id"), subject.get("step_reference"))
                        and (found is None or draft.created_at > found.created_at)):
                    found = draft
            return {"draft": named(found) if found else None}

        if package is not None:
            return guarded("an open draft", on_package)
        if not project_id or not agency_id:
            return refused(422, "no_plan")

        def read():
            newest: dict[str, Saved] = {}
            for draft in store.for_team(access.team(viewer).key, viewer.user_id):
                subject = draft.content["subject"]
                if (draft.kind != kind or draft.state.state not in runtime.OPEN_STATES
                        or subject.get("project_id") != project_id or subject.get("agency_id") != agency_id):
                    continue
                version = subject.get("plan_date")
                if version not in newest or draft.created_at > newest[version].created_at:
                    newest[version] = draft
            if plan_date is None:
                return {"by_plan_date": {version: named(draft) for version, draft in sorted(newest.items())}}
            found = newest.get(plan_date.isoformat())
            return {"draft": named(found) if found else None}
        return guarded("an open draft", read)

    @app.get("/api/drafts/project-paper-inputs")
    def project_paper_inputs(project_id: str = Query(pattern=r"^P\d{6}$"), viewer: Viewer = Depends(current_viewer)):
        """What the "Drafts from this check" panel says before the click (the 36 brief, 3.6 and 5.7): how many PPSD
        rows the viewer's team checked for this project's packages, in which drafts, and how many of the project's
        implementing agencies published a Procurement Plan Strata read."""
        if not viewer.user_id:
            return refused(401, "no_identity")
        if not access.is_staff(viewer):
            return refused(403, "not_staff")
        drafts = guarded("the team's checked PPSD rows", lambda: checked_ppsd_rows(viewer, project_id))
        if isinstance(drafts, JSONResponse):
            return drafts
        agencies = None
        if engine_for is not None:
            from strata.drafts.project_paper import agencies_with_plans

            try:
                with engine_for(viewer) as engine:
                    agencies = agencies_with_plans(engine, project_id, today())
            except PermissionDenied:
                return refused(403, "permission")
            except EngineError:
                ref = reference()
                log.exception("The data service failed on the agencies of %s, reference %s.", project_id, ref)
                return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)
        return {"qualifying_ppsd_rows": {"count": sum(len(draft["rows"]) for draft in drafts),
                                         "draft_ids": [draft["draft_id"] for draft in drafts]},
                "agencies_with_plans": agencies}

    # ── One draft ────────────────────────────────────────────────────────

    @app.get("/api/drafts/{draft_id}")
    def open_draft(draft_id: str, view: VIEWS = "staff", viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")

        def read():
            saved = readable(viewer, draft_id)
            return shown(saved, viewer, view) if saved else JSONResponse({"code": "unknown_draft"}, status_code=404)
        return guarded(f"draft {draft_id}", read)

    @app.post("/api/drafts/{draft_id}/{action}")
    def act_on_draft(draft_id: str, action: str, body: ActRequest, viewer: Viewer = Depends(current_viewer)):
        if action not in runtime.ACTIONS:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if not viewer.user_id:
            return refused(401, "no_identity")
        rule = runtime.ACTIONS[action]

        def act():
            saved = readable(viewer, draft_id)
            if saved is None:
                return JSONResponse({"code": "unknown_draft"}, status_code=404)
            if not is_author(viewer, saved.author_id):
                return refused(403, "not_author")
            state = saved.state.state
            if state != body.expected_state:
                return refused(409, "stale", state=state)
            left = runtime.holds(saved, kinds, body.view)
            if state not in rule.starts:
                return refused(409, "draft_state", state=state, holds=[hold["key"] for hold in left])
            if action == "export" and left:
                return refused(409, "held", state=state, holds=[hold["key"] for hold in left])
            moment = now()
            if action == "export":
                store.save_export(draft_id, _export(saved, viewer, moment))
            target = rule.to or saved.state.from_state
            try:
                store.change(draft_id, state, target, viewer.user_id, viewer.name, moment)
            except Stale as stale:
                return refused(409, "stale", state=stale.state)
            return shown(store.get(draft_id), viewer, body.view)
        return guarded(f"{action} on draft {draft_id}", act)

    def _export(saved: Saved, viewer: Viewer, moment: dt.datetime) -> NewExport:
        """The export record and its three files, from the stored draft and the author's opened sources, with every
        value a person set on its fields, which the evidence pack records (ticket 36)."""
        kind = kinds.kinds[saved.kind]
        opened = store.opened_since(saved.author_id, [entry["evidence_id"] for entry in runtime.sources(saved.content)],
                                    saved.created_at)
        draft = runtime.draft_view(saved, viewer, STAFF, kinds, opened)
        draft["field_history"] = store.field_history(saved.draft_id) if "ppsd" in draft else []
        made = draft_files.make(kind, draft, exporter=viewer.name, exported_at=moment)
        return NewExport(f"{saved.draft_id}-export-{moment:%Y%m%d%H%M%S}", moment, viewer.user_id, viewer.name,
                         made.footnotes, len(draft["sources"]), draft["opened"]["count"], made.snapshot, made.files)

    # ── What people fill, and the reports they keep (ticket 36) ──────────

    def fillable(viewer: Viewer, draft_id: str):
        """The draft its author may change now, or the refusal: not the author (403), or a state
        where nothing changes (409: exported, discarded). Owners, ratings and the form stay open in Draft and in
        Checked by you, and lock at export (the 36 brief, 6.2)."""
        saved = readable(viewer, draft_id)
        if saved is None:
            return JSONResponse({"code": "unknown_draft"}, status_code=404)
        if not is_author(viewer, saved.author_id):
            return refused(403, "not_author")
        if saved.state.state not in runtime.OPEN_STATES:
            return refused(409, "draft_state", state=saved.state.state)
        return saved

    def set_value(viewer: Viewer, draft_id: str, view: str, row_key: str, name: str, value: str | None):
        if not viewer.user_id:
            return refused(401, "no_identity")

        def act():
            saved = fillable(viewer, draft_id)
            if isinstance(saved, JSONResponse):
                return saved
            module = runtime.writer_module(kinds.kinds[saved.kind])
            if not hasattr(module, "check_value"):
                return refused(422, "unknown_field")
            # A field set only in Draft, such as planned dates' one choice (ticket 38): once checked, the export uses
            # the checked value.
            if name in getattr(module, "DRAFT_ONLY_FIELDS", ()) and saved.state.state != "draft":
                return refused(409, "draft_state", state=saved.state.state)
            text = value.strip() if isinstance(value, str) else None
            problem = module.check_value(saved.content, row_key, name, text)
            if problem:
                return refused(422, problem)
            store.set_field(draft_id, row_key, name, text or None, viewer.user_id, viewer.name, now())
            return shown(store.get(draft_id), viewer, view)
        return guarded(f"a field of draft {draft_id}", act)

    @app.put("/api/drafts/{draft_id}/fields")
    def set_field(draft_id: str, body: FieldRequest, viewer: Viewer = Depends(current_viewer)):
        """A person's own value on a field only people fill, from the author's session: a risk owner, or in the Long
        Form a rating, the overall risk score or the stage. Strata never writes one (CLAUDE.md rule 1)."""
        if body.field == "form":
            return refused(422, "unknown_field")
        return set_value(viewer, draft_id, body.view, body.row_key, body.field, body.value)

    @app.put("/api/drafts/{draft_id}/form")
    def set_form(draft_id: str, body: FormRequest, viewer: Viewer = Depends(current_viewer)):
        """The risk table form the draft uses: the Short Form, or the Long Form where Table I offers it."""
        return set_value(viewer, draft_id, body.view, "", "form", body.form)

    @app.get("/api/drafts/{draft_id}/files/{name}")
    def download(draft_id: str, name: str, viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")

        def read():
            saved = readable(viewer, draft_id)
            found = store.file(draft_id, saved.export.export_id, name) if saved and saved.export else None
            if found is None:
                return JSONResponse({"code": "unknown_file"}, status_code=404)
            media_type, content = found
            return Response(content, media_type=media_type, headers={
                "Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})
        return guarded(f"a file of draft {draft_id}", read)
