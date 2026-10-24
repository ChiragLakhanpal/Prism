"""The draft routes (ticket 35): writing review notes, the draft page, its acts and files, and the Drafts tab.

- POST /api/drafts takes {"kind": "review_notes", "project_id": "P156634", "agency_id": "...",
  "plan_date": "2026-10-09", "idempotency_key": "...", "view": "staff"} and streams the writing as
  text/event-stream: step events (read, write, check, save), then a draft event with the saved draft's
  id, or a nothing_survived event with the removed sentences when none passed the checks (and nothing
  is saved), or an error event with a code from WRITE_ERRORS, and last a done event with the run id.
  A second request with the same idempotency key opens the same draft and writes nothing.
- GET /api/drafts lists the viewer's team's drafts in three groups, to_check, checked and exported,
  newest first by their last change, and the viewer's own discarded drafts.
- GET /api/drafts/existing?kind=&project_id=&agency_id=&plan_date= names the newest draft of that kind
  the viewer's team has open (in Draft or Checked by you) on that plan version, or null.
- GET /api/drafts/{draft_id} gives one draft as its page shows it, with how many of its sources the
  viewer opened since it was saved, and the holds that keep it from export.
- POST /api/drafts/{draft_id}/{check|export|discard|restore} takes {"expected_state": "draft",
  "view": "staff"} and moves the draft on, answering with the draft as its page now shows it. Export
  makes the Word file and the evidence pack's PDF and CSV, keeps them with the export record, and sends
  nothing anywhere.
- GET /api/drafts/{draft_id}/files/{name} downloads one of those files.

Every read and act asks the one access rule (src/strata/server/access.py): a draft another team made
is not found, and only its author acts. A refusal says why in the shape later tickets build on: 403
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

from strata.agent.runs import RunLog, run_row
from strata.config import DraftKinds
from strata.dbx import Viewer, viewer_from_headers
from strata.drafts import files as draft_files
from strata.drafts import runtime
from strata.drafts.store import DraftStore, NewExport, Saved, Stale
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import Event, Scope, TraceIds, Turn
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.server.access import Access, is_author
from strata.server.engines import EngineFor

log = logging.getLogger("strata.server.drafts")
STAFF = "staff"
VIEWS = Literal["staff", "piu", "public"]
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
GROUPS = {"draft": "to_check", "checked": "checked", "exported": "exported"}
KEEP_ALIVE = ": keep-alive\n\n"


class DraftRequest(BaseModel):
    kind: str = Field(min_length=1, max_length=64)
    project_id: str = Field(pattern=r"^P\d{6}$")
    agency_id: str = Field(min_length=1, max_length=200)
    plan_date: dt.date
    idempotency_key: str | None = Field(default=None, max_length=128)
    view: VIEWS = "staff"
    lang: Literal["en", "fr", "es", "pt"] = "en"


class ActRequest(BaseModel):
    expected_state: Literal["draft", "checked", "exported", "discarded"]
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
               heartbeat_seconds: float) -> None:
    running: set[tuple[str, str]] = set()  # (author, idempotency key) of the drafts being written now
    lock = threading.Lock()

    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def guarded(what: str, act: Callable[[], object]):
        """One use of the store, or the error a page can show: no store, permission, or the data service."""
        if store is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            return act()
        except PermissionDenied:
            return JSONResponse({"code": "permission"}, status_code=403)
        except EngineError:
            ref = reference()
            log.exception("The data service failed on %s, reference %s.", what, ref)
            return JSONResponse({"code": "data_service", "trace_id": ref}, status_code=503)

    def readable(viewer: Viewer, draft_id: str) -> Saved | None:
        saved = store.get(draft_id)
        return saved if saved is not None and access.may_read(viewer, saved.team_key) else None

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
        if body.view != STAFF:
            return refused(403, "preview", capability="draft", copy="preview")
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
                   "plan_date": body.plan_date.isoformat()}
        writing = runtime.Writing(kinds.kinds[body.kind], request, viewer, access.team(viewer).key, key,
                                  new_run_id(), body.lang)
        return StreamingResponse(_stream(writing, trace_ids()), media_type="text/event-stream", headers=STREAM_HEADERS)

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
            events = runtime.write(writing, engine_for, writers, store, today(), now, new_draft_id)
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
        """The writer's run for strata.ops.agent_runs, in the shape the answer stream logs its runs."""
        turn = Turn(question=writing.question or writing.kind.key, viewer=writing.viewer, run_id=writing.run_id,
                    scope=Scope(chip=writing.request.get("project_id"), as_of=today(), language=writing.language),
                    trace=trace)
        turn.notes.agent, turn.notes.agent_version, turn.notes.as_of = writing.agent, writing.agent_version, today()
        return run_row(turn, writing.verdict, error_code, started, dt.datetime.now(dt.UTC))

    # ── The Drafts tab ───────────────────────────────────────────────────

    @app.get("/api/drafts")
    def list_drafts(view: VIEWS = "staff", viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        if view != STAFF:
            return refused(403, "preview", capability="read", copy="preview", view=view)

        def read():
            team = access.team(viewer)
            saved = store.for_team(team.key)
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
    def existing_draft(kind: str = Query(max_length=64), project_id: str = Query(max_length=16),
                       agency_id: str = Query(max_length=200), plan_date: dt.date = Query(),
                       viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")

        def read():
            found = [draft for draft in store.for_team(access.team(viewer).key)
                     if draft.kind == kind and draft.state.state in runtime.OPEN_STATES
                     and draft.content["subject"].get("project_id") == project_id
                     and draft.content["subject"].get("agency_id") == agency_id
                     and draft.content["subject"].get("plan_date") == plan_date.isoformat()]
            if not found:
                return {"draft": None}
            newest = max(found, key=lambda draft: draft.created_at)
            return {"draft": {"draft_id": newest.draft_id, "created_at": runtime.iso(newest.created_at),
                              "author": {"name": newest.author_name, "you": is_author(viewer, newest.author_id)}}}
        return guarded("an open draft", read)

    # ── One draft ────────────────────────────────────────────────────────

    @app.get("/api/drafts/{draft_id}")
    def open_draft(draft_id: str, view: VIEWS = "staff", viewer: Viewer = Depends(current_viewer)):
        if not viewer.user_id:
            return refused(401, "no_identity")
        if view != STAFF:
            return refused(403, "preview", capability="read", copy="preview", view=view)

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
            if body.view != STAFF:
                return refused(403, "preview", capability=rule.capability, copy="preview")
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
        """The export record and its three files, from the stored draft and the author's opened sources."""
        kind = kinds.kinds[saved.kind]
        opened = store.opened_since(saved.author_id, [entry["evidence_id"] for entry in runtime.sources(saved.content)],
                                    saved.created_at)
        draft = runtime.draft_view(saved, viewer, STAFF, kinds, opened)
        made = draft_files.make(kind, draft, exporter=viewer.name, exported_at=moment)
        return NewExport(f"{saved.draft_id}-export-{moment:%Y%m%d%H%M%S}", moment, viewer.user_id, viewer.name,
                         made.footnotes, len(draft["sources"]), draft["opened"]["count"], made.snapshot, made.files)

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
