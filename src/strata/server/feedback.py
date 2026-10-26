"""The retrieval loop's routes (ticket 32; the 32 design brief, section 9).

The evidence drawer's feedback row:

- POST /api/feedback takes {evidence_id, run_id, sentence_id, kind, reason, view} and writes one passage report,
  a candidate label in strata.ops.candidate_labels, with the viewer the Databricks App forwarded and the
  question, sentence, kind of question and as-of date from the answer's own record. A preview is refused (403
  preview), and so is a source the answer did not cite (404 not_in_answer) or one no search found for the
  question (403 no_question). GET /api/feedback?evidence_id=&run_id= gives the viewer's report on that source in
  that answer, with what became of it, and POST /api/feedback/{report_id}/withdraw writes a withdrawal, refused
  once a reviewer has decided (409 decided).

Lessons > Passage reports, for passage reviewers (403 not_a_passage_reviewer for anyone else):

- GET /api/passage-reports?page= lists the groups waiting, for you and for another reviewer, and the decisions of
  the last decided_days days. GET /api/passage-reports/{group_id} gives one group with its passage and reports,
  naming each sender by role. POST .../decide takes {expected_state, outcome, reason}: rank_lower or keep, or
  leave_lower or restore on an audit sample, refused with own_report, stale or no_reason. POST .../reopen takes
  {reason} and puts a decided group back in the queue with its passage's earlier ranking.

Lessons > Judging, for query judges (403 not_a_judge):

- GET /api/judging/queries?show=&page= and GET /api/judging/queries/{query_id} give the queries and one query's
  pool in the judge's own order, never a rank, score or setup. PUT .../passages/{passage_id} takes {grade},
  refused for a query that is not the judge's (not_assigned) or whose grades are locked (locked).

Every write is made by the app's own service principal (record), with the viewer recorded in the row, so no one
needs write access to the loop's tables outside the app. Who sent each passage report and who asked each question
are masked for every reader (strata.lakehouse.masks; ticket 64), so the passage report routes read the reports and
decisions as the app's own service principal too, and the passages and everything else with the viewer's own token.
Without the app's own identity, nothing is recorded and no passage report is read (503 not_recorded).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from strata.dbx import Viewer, viewer_from_headers
from strata.knowledge.lessons.review import Refused
from strata.knowledge.retrieval.judging import Judging
from strata.knowledge.retrieval.reports import PassageReports
from strata.lakehouse.engine import Engine, EngineError, PermissionDenied
from strata.server.engines import EngineFor

log = logging.getLogger("strata.server.feedback")


class FeedbackRequest(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=512)
    run_id: str = Field(min_length=1, max_length=128)
    sentence_id: int | None = Field(default=None, ge=0, le=10_000)
    kind: Literal["wrong_passage", "not_useful"]
    reason: str | None = Field(default=None, max_length=4000)
    view: Literal["staff", "piu", "public"] = "staff"


class DecideRequest(BaseModel):
    expected_state: str = Field(min_length=1, max_length=128)
    outcome: Literal["rank_lower", "keep", "leave_lower", "restore"]
    reason: str | None = Field(default=None, max_length=4000)


class ReopenRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=4000)


class GradeRequest(BaseModel):
    grade: Annotated[str, StringConstraints(min_length=1, max_length=32)]


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, **details}, status_code=status, headers={"Cache-Control": "no-store"})


def refusal_response(refusal: Refused) -> JSONResponse:
    return JSONResponse(refusal.body(), status_code=refusal.status, headers={"Cache-Control": "no-store"})


def add_routes(app: FastAPI, *, engine_for: EngineFor | None, record: Callable[[], Engine | None] | None,
               reports: PassageReports, judging: Judging, reference: Callable[[], str]) -> None:
    def current_viewer(request: Request) -> Viewer:
        return viewer_from_headers(request.headers)

    def on_data(what: str, viewer: Viewer, work: Callable[[Engine], object]):
        if engine_for is None:
            return refused(503, "no_data_service")
        try:
            with engine_for(viewer) as engine:
                try:
                    found = work(engine)
                except Refused as refusal:
                    return refusal_response(refusal)
                return found if isinstance(found, JSONResponse) else JSONResponse(found, headers={"Cache-Control": "no-store"})
        except PermissionDenied:
            return refused(403, "permission")
        except EngineError:
            trace = reference()
            log.exception("The data service failed on %s, reference %s.", what, trace)
            return refused(503, "data_service", trace_id=trace)

    def read(what: str, viewer: Viewer, work: Callable[[Engine], object]):
        if not viewer.signed_in:
            return refused(401, "no_identity")
        return on_data(what, viewer, work)

    def recorded(what: str, viewer: Viewer, work: Callable[[Engine, Engine], object]):
        """The loop's record: the viewer's engine for what the viewer may read, such as the passages, and the app's own
        service principal's for the rows it writes, with the viewer in the row, and for the passage reports it reads
        back, which only it may read in full."""
        if not viewer.signed_in:
            return refused(401, "no_identity")
        if record is None:
            return refused(503, "not_recorded")

        def run(engine: Engine):
            writer = record()
            if writer is None:
                return refused(503, "not_recorded")
            try:
                return work(engine, writer)
            finally:
                close = getattr(writer, "close", None)
                if callable(close):
                    close()
        return on_data(what, viewer, run)

    # ── The evidence drawer's feedback row ───────────────────────────────

    @app.post("/api/feedback")
    def send_report(body: FeedbackRequest, viewer: Viewer = Depends(current_viewer)):
        # A preview never reaches this route: the view switch's guard refuses it (ticket 40).
        return recorded(f"a passage report on {body.evidence_id}", viewer,
                        lambda _engine, writer: reports.send(viewer, body.model_dump(), body.view, writer))

    @app.get("/api/feedback")
    def my_report(evidence_id: str = Query(min_length=1, max_length=512), run_id: str = Query(min_length=1, max_length=128),
                  viewer: Viewer = Depends(current_viewer)):
        return recorded(f"the viewer's report on {evidence_id}", viewer,
                        lambda _engine, the_app: reports.mine(viewer, evidence_id, run_id, the_app))

    @app.post("/api/feedback/{report_id}/withdraw")
    def withdraw_report(report_id: str, viewer: Viewer = Depends(current_viewer)):
        return recorded(f"withdrawing {report_id}", viewer,
                        lambda _engine, writer: reports.withdraw(viewer, report_id, writer))

    # ── Lessons > Passage reports ────────────────────────────────────────

    @app.get("/api/passage-reports")
    def passage_reports(page: int = Query(1, ge=1, le=10_000), viewer: Viewer = Depends(current_viewer)):
        return recorded("the passage reports", viewer,
                        lambda engine, the_app: reports.queue(engine, viewer, the_app, page))

    @app.get("/api/passage-reports/{group_id}")
    def passage_report(group_id: str, viewer: Viewer = Depends(current_viewer)):
        return recorded(f"passage report {group_id}", viewer,
                        lambda engine, the_app: reports.item(engine, viewer, group_id, the_app))

    @app.post("/api/passage-reports/{group_id}/decide")
    def decide_reports(group_id: str, body: DecideRequest, viewer: Viewer = Depends(current_viewer)):
        return recorded(f"a decision on {group_id}", viewer,
                        lambda engine, writer: reports.decide(engine, viewer, group_id, body.model_dump(), writer))

    @app.post("/api/passage-reports/{group_id}/reopen")
    def reopen_reports(group_id: str, body: ReopenRequest, viewer: Viewer = Depends(current_viewer)):
        return recorded(f"reopening {group_id}", viewer,
                        lambda engine, writer: reports.reopen(engine, viewer, group_id, body.reason or "", writer))

    # ── Lessons > Judging ────────────────────────────────────────────────

    @app.get("/api/judging/queries")
    def judging_queries(show: str = Query("to_judge", max_length=32), page: int = Query(1, ge=1, le=10_000),
                        viewer: Viewer = Depends(current_viewer)):
        return read("the judging queries", viewer, lambda engine: judging.queries(engine, viewer, show, page))

    @app.get("/api/judging/queries/{query_id}")
    def judging_query(query_id: str, viewer: Viewer = Depends(current_viewer)):
        return read(f"judging query {query_id}", viewer, lambda engine: judging.query(engine, viewer, query_id))

    @app.put("/api/judging/queries/{query_id}/passages/{passage_id:path}")
    def grade_passage(query_id: str, passage_id: str, body: GradeRequest, viewer: Viewer = Depends(current_viewer)):
        return recorded(f"a grade on {query_id}", viewer,
                        lambda engine, writer: judging.grade(engine, viewer, query_id, passage_id, body.grade, writer))
