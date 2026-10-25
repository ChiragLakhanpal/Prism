"""The server shell: health, identity, the data-freshness stamp, the answer stream and the plan check.

- GET /api/health says the server is up.
- GET /api/me names the viewer the Databricks App forwarded, and never returns the token.
- GET /api/me/warehouse runs one query as the viewer and returns the user the warehouse says
  ran it, so a deploy can show that each person's queries run as that person.
- GET /api/freshness returns the data-freshness stamp's day ({"data_through": "2026-10-21"},
  or null before any daily source has loaded), read from strata.ops as the viewer. It answers
  401 with no forwarded identity, 403 with the code permission when the warehouse refuses the
  viewer, 504 when the warehouse takes longer than the thresholds file's
  app.stamp_timeout_seconds, and 502 when it fails, with the details only in the server log.
- POST /api/ask takes a question, with the page's scope chip, as-of date, view and language, and
  streams a run's events as text/event-stream: steps, then the refusal when the agent turned the
  request down, the answer's sentences with their evidence ids, the evidence they cite, the
  disagreements check 6 shows, the check counts and the removed sentences, then a final done event
  with the run id and its trace ids. The verifier's six checks run here, in the stream, on every
  answer the runner hands over, so no runner can send a sentence the checks did not see: checks 1 to
  3 and 5 at once, check 6 with get_disagreements asked as the viewer, and check 4 with one call to
  the judge (src/strata/agent/judge.py). A run that breaks ends with an error event whose details
  stay in the server log. Each run is written to strata.ops.agent_runs (src/strata/agent/runs.py).
- GET /api/projects lists every project Strata holds a record for, and GET /api/projects/{project_id}
  gives a project page's header and each agency's Procurement Plan versions (src/strata/server/
  projects.py), as the viewer and as of ?asof=; an unknown project gets 404 with the code
  unknown_project.
- GET /api/projects/{project_id}/timeline gives a project's Timeline tab (ticket 23; src/strata/server/timeline.py):
  its reports, events and records in three lanes, the ISRs' rating bands and the disagreements get_disagreements
  found, as the viewer, as of ?asof= and in ?view=, whose public view shows no disagreement on an active project.
- POST /api/disagreements/{id}/choices keeps one side of a disagreement for an answer (run_id) or a draft
  (draft_id), with a reason when it is the side Strata does not lean on: one new row in
  strata.ops.disagreement_choices with the forwarded viewer, written as the app's own service principal. A preview
  records nothing ({"recorded": false}). GET with ?run_id= or ?draft_id= gives the latest choice
  (src/strata/server/choices.py).
- GET /api/data/readiness runs the tool registry's data_readiness_for as the viewer, for every
  source or for ?sources= (registry keys, separated by commas) from the coverage line of ?from=, as
  of ?asof=. It answers like the stamp when it cannot: 401, 403 with the code permission, 504 with
  the seconds it waited, and 502.
- GET /api/data/sources lists each dataset's attribution and the document collections, and counts
  the Data readiness page's rows, from the registries alone, so it answers with the warehouse down.
- GET /api/projects/{project_id}/procurement/{agency_id}[/{version}] checks one implementing
  agency's Procurement Plan, its latest version or the one dated version, through the tool
  registry's check_plan, as the viewer. It takes the page's ?asof= and ?view=. A viewer whose
  token cannot read strata gets 403 with the code permission and no rows.
- GET /api/lookup/loan?q= and GET /api/lookup/activity?q= are the one box's lookups, as the viewer and as
  of ?asof=: the project a loan number finances, and the latest published Procurement Plan that lists a
  STEP reference (src/strata/server/lookup.py). One that finds nothing gets 404 with the code
  unknown_loan or unknown_activity.
- GET /api/evidence?id= gives one source by its evidence id, as the viewer and as of ?asof=, in the shape
  the answer stream's evidence event carries, for an evidence drawer opened from a link; an id no source
  has, or one not public by then, gets 404 with the code unknown_evidence (src/strata/server/evidence.py).
- POST /api/evidence/opened records that the viewer opened a source in the evidence drawer, one row per
  viewer and evidence id in strata.ops.evidence_opened, written as the app's own service principal. A
  preview of another view, or a request no one is signed in for, records nothing, and the answer says
  {"recorded": false}. GET /api/evidence/opened?id=...&id=... says which of those the viewer has opened.
- GET /api/packages/{step_reference} gives the package workspace's header: the package as its newest
  public Procurement Plan row states it, with that plan and its project, or 404 with the code
  unknown_package. GET /api/packages/{step_reference}/comparables runs find_comparables through the
  tool registry for the workspace's section 1, with the tool's criteria as query parameters
  (?review_type=Prior, ?category=any), ?asof= and ?view=, as the viewer.
- POST, GET /api/planned-packages and GET, POST /api/planned-packages/{package_id} plan a package from a
  sentence, list a viewer's packages and the plans they checked, and open or change one package, and GET
  /api/comparables runs find_comparables for a package with no STEP row (ticket 15; src/strata/server/
  packages.py). Each plan check a signed-in viewer opens is recorded for their Packages tab.
- GET .../criteria, POST .../criteria/run and POST .../criteria/compare under /api/packages/{step_reference}
  and /api/planned-packages/{package_id} are section 5 of the package workspace, "Check your criteria"
  (ticket 31; src/strata/server/criteria.py): the collapsed summary, the package-level run and the comparison
  of a person's pasted qualification criteria, whose text only they read back.
- GET /api/packages/{step_reference}/risks and GET /api/planned-packages/{package_id}/risks run the risk-table
  builder for the workspace's section 3, procurement risks and what helped, and PUT .../risk-selection keeps the
  risks a viewer selected for the PPSD (ticket 30; src/strata/server/risks.py).
- GET /api/packages/{step_reference}/rebidding and GET /api/rebidding run rebidding_risk through the tool
  registry for section 1's "Advertised again" block, for a STEP row and for a package planned from a sentence,
  with find_comparables' criteria as query parameters, ?asof= and ?view=, as the viewer (ticket 28).
- GET /api/suppliers/review is the review list for supplier name matching (ticket 19): each candidate
  pair that waits for a person, with both names, countries and contracts, read as the viewer. POST
  /api/suppliers/review records a person's decision on one, merge or no merge with a reason, and the
  viewer as the reviewer; the next nightly run applies it. GET /api/suppliers/labels gives the labeling
  tool's next unlabeled pairs, without where Strata sent them, and POST /api/suppliers/labels records a
  label (src/strata/server/suppliers.py). A write needs a signed-in viewer (401 no_identity) and a pair
  the latest run found (404 unknown_pair), and is made as the app's own service principal; without it,
  nothing is recorded (503 not_recorded). No roles file names reviewers yet, so any signed-in viewer
  may decide.
- The Lessons tab (ticket 29; src/strata/knowledge/lessons/review.py). GET /api/lessons/me says which
  Lessons pages the viewer may open (tabs), from the roles file, and how many items wait in their regions.
  GET /api/lessons?page= is the library: current lessons and those being re-checked, eight a page, newest
  decision first, naming roles and never people. GET /api/lessons/review?page= is the review queue and
  GET /api/lessons/review/{item_id} one item's review page; both answer 403 not_a_reviewer to anyone the
  roles file does not name as a lesson reviewer. POST /api/lessons/review/{item_id}/recommend, /decide and
  /cross-check record a reviewer's act, and POST /api/lessons/{lesson_id}/recheck asks for a re-check; each
  is refused with a reason code (same_person, own_project, not_a_lead, other_region, same_region, stale,
  recheck_open). Every read is the viewer's, with their own token; every act is written as the app's own
  service principal, with the viewer the Databricks App forwarded recorded as the actor, so no reviewer
  needs write access to the review record outside the app. Without the app's own identity, nothing is
  recorded (503 not_recorded).
- Every other address outside /api gets the built web app, when create_app is given one.

Each request a viewer makes, except /api/health and the web app's files, writes one usage event
(src/strata/server/usage.py) and sends one trace (src/strata/server/tracing.py), whose id the
event keeps, whatever the route answers. An error no route expects answers 500 with the code
internal and a reference, and its details stay in the server log. An /api span is named by its route, such as GET /api/projects/{project_id}/..., and
an error's reference is the request's trace id.

Each request builds its own Viewer, Turn and engine; create_app keeps only settings, never a viewer.
"""

import asyncio
import datetime as dt
import json
import logging
import threading
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.middleware.gzip import GZipMiddleware
from opentelemetry import trace
from pydantic import BaseModel, Field, StringConstraints

from strata.agent import traces
from strata.agent.answer_check import Asker, SixChecks
from strata.agent.judge import Judge
from strata.agent.runs import RunLog, run_row
from strata.agent.verifier import Verdict, answer_events
from strata.config import DraftKinds, load_draft_kinds, load_roles, load_thresholds, load_tools
from strata.dbx import Viewer, viewer_from_headers
from strata.drafts.store import DraftStore
from strata.knowledge.lessons.review import LessonReview, Refused
from strata.harness.aio import HEARTBEAT, with_heartbeats
from strata.harness.turn import (ERROR_CODES, Event, RunError, Runner, Scope, TraceIds, Turn,
                                 new_run_id as random_run_id, no_agent)
from strata.lakehouse.engine import Engine, EngineError, PermissionDenied
from strata.config import PackageForm, load_package_form
from strata.packages.store import PackageStore
from strata.knowledge.retrieval.judging import Judging
from strata.knowledge.retrieval.reports import CitationLog, PassageReports
from strata.server import steps as step_routes
from strata.server import drafts as draft_routes
from strata.server import feedback as feedback_routes
from strata.server import (baseline, changes, choices as choice_routes, documents, edges, engines, evidence, lookup,
                           projects, summary, suppliers, timeline, tracing, trail)
from strata.server import packages as package_routes
from strata.server import criteria as criteria_routes
from strata.criteria.store import CriteriaStore
from strata.criteria.workflow import Package as CriteriaPackage
from strata.server import risks as risk_routes
from strata.server import following as following_routes
from strata.server.following import FollowStore
from strata.estimates import signals_track
from strata.server.access import Access, NoGroups
from strata.server.choices import REASON_LIMIT, ChoiceLog
from strata.server.evidence import OpenedLog
from strata.server.suppliers import SupplierLog
from strata.server.usage import UsageEvent, UsageLog
from strata.server.viewer_sql import data_through, warehouse_user
from strata.tools import registry
from strata.tools.data_readiness_for import registry_page
from strata.tools.find_comparables import read_package

log = logging.getLogger("strata.server")
KEEP_ALIVE = ": keep-alive\n\n"
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
# Only the verifier writes these, from the claims a runner hands over.
ANSWER_EVENTS = {"refusal", "sentence", "evidence", "disagreement", "checks", "removed", "done"}
# The platform's check that the app is up. It is not a viewer's request, so it is not counted.
UNCOUNTED = {"/api/health"}
# The view the server applies. Until ticket 40 adds the implementing agency and public previews,
# every request sees the World Bank staff view, whatever ?view= asks for.
STAFF = "staff"
IMMUTABLE = "public, max-age=31536000, immutable"
# The tag on every route that calls a model: the answer stream now, and the draft writers when they
# land. A project's Summary must render without a request to one (ticket 21), and the screen test
# checks that against the list model_routes() gives, recorded in tests/fixtures/api/model-routes.json.
MODEL = "model"


def model_routes(app: FastAPI) -> list[dict]:
    """Every route the app tags as calling a model, as {method, path}, sorted."""
    found = [{"method": method, "path": route.path} for route in app.routes
             if MODEL in (getattr(route, "tags", None) or []) for method in sorted(getattr(route, "methods", []))]
    return sorted(found, key=lambda route: (route["path"], route["method"]))


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    scope: str | None = Field(default=None, max_length=64)  # the page's scope chip: a P-code or STEP reference
    asof: dt.date | None = None
    view: Literal["staff", "piu", "public"] = "staff"
    lang: Literal["en", "fr", "es", "pt"] = "en"


class OpenedRequest(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=512)
    run_id: str | None = Field(default=None, max_length=128)  # the answer it was opened from, if any
    route: str | None = Field(default=None, max_length=512)  # the page it was opened on
    view: Literal["staff", "piu", "public"] = "staff"


class ChoiceRequest(BaseModel):
    """Keeping one side of a disagreement for an answer or a draft (ticket 23). The person is the forwarded viewer,
    never a field here."""

    kept_assertion_id: str = Field(min_length=1, max_length=512)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=REASON_LIMIT)] = ""
    run_id: str | None = Field(default=None, max_length=128)
    draft_id: str | None = Field(default=None, max_length=128)
    view: Literal["staff", "piu", "public"] = "staff"


class DecisionRequest(BaseModel):
    pair_id: str = Field(min_length=1, max_length=512)
    decision: Literal["merge", "no_merge"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class LabelRequest(BaseModel):
    pair_id: str = Field(min_length=1, max_length=512)
    label: Literal["merge", "no_merge"]


class BaselineRequest(BaseModel):
    plan_date: dt.date  # the version of the agency's plans to save as the baseline


class LessonActRequest(BaseModel):
    """A recommendation, decision or cross-check on a queue item. The person is the forwarded viewer, never a
    field here; the server checks every value again."""

    expected_stage: str = Field(min_length=1, max_length=32)  # the stage the person saw
    outcome: str | None = Field(default=None, max_length=32)
    repeat_of: str | None = Field(default=None, max_length=128)
    change: dict | None = None  # the lesson editor's statement and tags
    reason: str | None = Field(default=None, max_length=4000)
    agree: bool | None = None  # a cross-check's answer


class RecheckRequest(BaseModel):
    reason: str = Field(max_length=4000)


def current_viewer(request: Request) -> Viewer:
    return viewer_from_headers(request.headers)


def frame(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def request_reference() -> str:
    """The reference an error gives the page: the request's trace id, which finds it in Application
    Insights and in its usage event, or a random one when the request has no trace."""
    return tracing.trace_id(trace.get_current_span()) or uuid.uuid4().hex


def refused(status: int, code: str, **details) -> JSONResponse:
    return JSONResponse({"code": code, **details}, status_code=status, headers={"Cache-Control": "no-store"})


def new_draft_id() -> str:
    return f"draft-{uuid.uuid4().hex[:12]}"


def create_app(runner: Runner | None = None, heartbeat_seconds: float = 15.0,
               new_run_id: Callable[[], str] = random_run_id, engine_for: engines.EngineFor | None = None,
               stamp_timeout_seconds: float | None = None, usage: UsageLog | None = None,
               tracer_provider: trace.TracerProvider | None = None, web_dist: Path | None = None,
               runs: RunLog | None = None, trace_ids: Callable[[], TraceIds] = traces.current,
               opened: OpenedLog | None = None, supplier_log: SupplierLog | None = None,
               drafts: DraftStore | None = None,
               writers: Callable[[str], object | None] | None = None, access: Access | None = None,
               kinds: DraftKinds | None = None, today: Callable[[], dt.date] = registry.today,
               now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC),
               new_draft_id: Callable[[], str] = new_draft_id, packages: PackageStore | None = None,
               package_reader: Callable[[], object | None] | None = None, package_thresholds=None,
               package_form: PackageForm | None = None, new_package_id: Callable[[], str] = package_routes.new_package_id,
               new_save_id: Callable[[], str] = package_routes.new_save_id, lessons: LessonReview | None = None,
               lesson_writer: Callable[[], object | None] = lambda: None,
               lesson_record: Callable[[], Engine] | None = None, criteria: CriteriaStore | None = None,
               criteria_reader: Callable[[], object | None] | None = None,
               new_check_id: Callable[[], str] = criteria_routes.new_check_id, judge: Judge | None = None,
               passage_reports: PassageReports | None = None, judging: Judging | None = None,
               feedback_record: Callable[[], Engine] | None = None,
               citations: CitationLog | None = None, choices: ChoiceLog | None = None,
               follows: FollowStore | None = None) -> FastAPI:
    """The app.

    engine_for makes the engine for each request's viewer; without it, the environment names one.
    runner answers /api/ask; without it, the stream says there is no agent (app_from_env in
    src/strata/server/settings.py gives it the Foundry agent its environment names). usage
    receives one event per request, and tracer_provider (the process's global one when None) one
    span. runs writes each answer stream's run to strata.ops.agent_runs; without it, runs go to the
    server log only. trace_ids reads the request's trace ids while its span is open. opened keeps the
    sources each viewer opened in the evidence drawer; without it, nothing is recorded. supplier_log
    keeps the decisions and labels people give candidate pairs of supplier name matching; without it,
    none is recorded. lessons is the lesson review (strata.knowledge.lessons.review) with its roles file and
    clock; without it, config/roles.toml and today. lesson_writer gives the lesson review writer agent, whose note on
    an item the review page's "Try again" writes again; without it, there is none. lesson_record opens the
    engine that writes the lesson review record as the app's own service principal; without it, no act is
    recorded. web_dist is
    the built web app: its files are served as they are, and every other address outside /api gets
    its index.html, whose router shows the page or the not-found page.

    judge answers the verifier's check 4 for every answer (src/strata/agent/judge.py; app_from_env gives
    the draft role's deployment). Without it, every sentence that needed the judge is removed, never shown
    unchecked. Check 6 asks get_disagreements with engine_for, as the viewer.

    drafts keeps the drafts (src/strata/drafts/store.py), written as the app's own service principal;
    without it, the draft routes say there is no data service. writers gives each draft kind's writer
    agent, or None when none is connected. access is the one access rule (src/strata/server/access.py);
    without it, every viewer is on a team of their own. kinds is the draft-kind registry, today the day
    a draft's facts are read as of, now the clock (also for when a baseline was saved) and new_draft_id
    the ids drafts get.

    passage_reports and judging are the retrieval loop (ticket 32; src/strata/knowledge/retrieval): the evidence
    drawer's passage reports, Lessons > Passage reports and Lessons > Judging, with the roles file; without them,
    config/roles.toml. feedback_record opens the engine that writes their rows as the app's own service
    principal; without it, nothing is recorded. citations keeps the sources each answer cited
    (strata.ops.answer_citations), which a passage report reads its question and sentence from; without it, an
    answer's sources are not kept and no passage in it can be reported.

    packages keeps planned packages and the plan checks each viewer opened (src/strata/packages/store.py),
    written as the app's own service principal; without it, planning a package says there is no data service
    and no plan check is recorded. package_reader gives the package reader agent, or None when none is
    connected; package_thresholds and package_form stand in for config/thresholds.toml and
    config/package_form.toml, so a test can change a threshold or a field; new_package_id and new_save_id are
    the ids packages and their saves get.

    choices keeps the side of a disagreement each person kept for an answer or a draft, with their reason
    (strata.ops.disagreement_choices, ticket 23), written as the app's own service principal; without it, keeping
    the other report says nothing was recorded.

    criteria keeps the runs of "Check your criteria", section 5 of the package workspace (src/strata/criteria/
    store.py), with each person's pasted text readable only by them, written as the app's own service principal;
    without it, comparing criteria says there is no data service and no run is kept. criteria_reader gives the
    criteria reader agent, or None when none is connected; new_check_id the ids its runs get (ticket 31).
    """
    engine_for = engine_for or engines.from_environment()
    runner = runner or no_agent
    lessons = lessons or LessonReview(load_roles())
    access = access or Access(load_roles(), NoGroups())
    passage_reports = passage_reports or PassageReports(load_roles())
    judging = judging or Judging(load_roles())
    web = web_dist.resolve() if web_dist is not None else None

    def web_file(path: str) -> Path | None:
        """The built web app's file at this address, if there is one inside it."""
        if web is None:
            return None
        try:
            candidate = (web / path.lstrip("/")).resolve()
            return candidate if candidate.is_file() and web in candidate.parents else None
        except (OSError, ValueError):  # an address no file can have: a NUL byte, or a name over 255 bytes
            return None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if usage is not None:
            usage.start()
        try:
            yield
        finally:
            if usage is not None:
                await asyncio.to_thread(usage.stop)

    app = FastAPI(title="Strata", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    # The built app and the larger answers go compressed, so the Summary keeps its cold 3G budget (the 21
    # brief, section 3.5). Starlette leaves text/event-stream alone, so /api/ask still streams.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    thresholds = load_thresholds()
    tools = load_tools()
    six_checks = SixChecks(engine_for, judge, tools, thresholds)
    timeout = stamp_timeout_seconds or thresholds.value("app.stamp_timeout_seconds")
    labeled_pairs_target = int(thresholds.value("supplier_matching.labeled_pairs_target"))
    tracer = (tracer_provider or trace.get_tracer_provider()).get_tracer("strata.server")

    @app.middleware("http")
    async def observe(request: Request, call_next):
        """One span and one usage event for each request a viewer makes."""
        path = request.url.path
        if path in UNCOUNTED or web_file(path) is not None:
            return await call_next(request)
        viewer = viewer_from_headers(request.headers)
        requested_at = dt.datetime.now(dt.UTC)
        name = f"{request.method} {path if path.startswith('/api/') else 'page'}"
        with tracer.start_as_current_span(name, kind=trace.SpanKind.SERVER) as span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("url.path", path)
            span.set_attribute("strata.view", STAFF)
            try:
                response = await call_next(request)
            except Exception:  # an error no route expected: its details stay in the server log
                reference = request_reference()
                log.exception("%s failed in a way I did not expect, reference %s.", name, reference)
                response = JSONResponse({"code": "internal", "trace_id": reference}, status_code=500)
            finally:  # whatever the route did, the request is counted
                if usage is not None:
                    usage.record(UsageEvent(viewer.user_id, path, STAFF, requested_at, tracing.trace_id(span)))
            # One operation per route in Application Insights, not one per project or agency.
            route = getattr(request.scope.get("route"), "path", None)
            if route and path.startswith("/api/"):
                span.update_name(f"{request.method} {route}")
            span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(trace.StatusCode.ERROR)
        return response

    def read_as(viewer: Viewer, read: Callable[[Engine], object]):
        with engine_for(viewer) as engine:
            return read(engine)

    async def as_viewer(viewer: Viewer, read: Callable[[Engine], object], answer: Callable[[object], dict],
                        say_timeout: bool = False):
        """One read as the viewer, within the stamp's timeout, or the reason it could not run."""
        if not viewer.token:
            return refused(401, "no_identity")
        if engine_for is None:
            return refused(503, "no_data_service")
        try:
            value = await asyncio.wait_for(asyncio.to_thread(read_as, viewer, read), timeout)
        except TimeoutError:
            return refused(504, "timeout", **({"timeout_seconds": timeout} if say_timeout else {}))
        except PermissionDenied:
            log.warning("The warehouse refused %s.", viewer.email or viewer.user_id)
            return refused(403, "permission")
        except EngineError:
            log.exception("A query for %s failed.", viewer.email or viewer.user_id)
            return refused(502, "unreadable")
        return JSONResponse(answer(value), headers={"Cache-Control": "no-store"})

    def read_for(what: str, viewer: Viewer, read: Callable[[Engine], object]):
        """One read as the viewer, or the error a page can show: permission, or the data service,
        which keeps its details in the server log and gives the page a reference to it."""
        if engine_for is None:
            return JSONResponse({"code": "no_data_service"}, status_code=503)
        try:
            with engine_for(viewer) as engine:
                return read(engine)
        except PermissionDenied:
            return JSONResponse({"code": "permission"}, status_code=403)
        except EngineError:
            reference = request_reference()
            log.exception("The data service failed on %s, reference %s.", what, reference)
            return JSONResponse({"code": "data_service", "trace_id": reference}, status_code=503)

    def run_tool(name: str, arguments: dict, viewer: Viewer, view: str, as_of: dt.date | None):
        """One tool call as the viewer, or the error a page can show: a bad request, permission, a tool
        that broke its contract, or the data service. The last two keep their details in the server log
        and give the page a reference to it."""
        def call(engine: Engine):
            try:
                return registry.call(name, arguments, registry.Context(engine, viewer, view, as_of))
            except registry.ToolError as error:  # a view or an argument the tool does not take
                return JSONResponse({"code": "bad_request", "detail": str(error)}, status_code=422)
            except registry.ToolContractError:
                reference = request_reference()
                log.exception("The tool %s broke its contract, reference %s.", name, reference)
                return JSONResponse({"code": "tool_contract", "trace_id": reference}, status_code=500)
        return read_for(name, viewer, call)

    page_size = int(thresholds.value("app.page_size"))

    @app.get("/api/projects")
    def list_projects(asof: dt.date | None = None, q: str = Query("", max_length=200), page: int = Query(1, ge=1),
                      viewer: Viewer = Depends(current_viewer)):
        as_of = asof or registry.today()
        return read_for("all projects", viewer,
                        lambda engine: projects.all_projects(engine, as_of, q.strip(), page, page_size))

    versions_shown = int(thresholds.value("app.versions_shown"))

    @app.get("/api/projects/{project_id}")
    def open_project(project_id: str, asof: dt.date | None = None, view: str = "staff",
                     viewer: Viewer = Depends(current_viewer)):
        as_of = asof or registry.today()

        def read(engine: Engine):
            found = projects.project_page(engine, project_id, as_of, view, versions_shown)
            return found if found is not None else JSONResponse({"code": "unknown_project"}, status_code=404)
        return read_for(f"project {project_id}", viewer, read)

    @app.get("/api/projects/{project_id}/summary")
    def project_summary(project_id: str, asof: dt.date | None = None, viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            found = summary.summary(engine, project_id, as_of_for(asof))
            return found if found is not None else JSONResponse({"code": "unknown_project"}, status_code=404)
        return read_for(f"the summary of {project_id}", viewer, read)

    @app.get("/api/projects/{project_id}/timeline")
    def project_timeline(project_id: str, asof: dt.date | None = None, view: Literal["staff", "piu", "public"] = "staff",
                         viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            # The page's as-of date, never later than today, by the clock create_app was given (today), so a
            # recording of the plain page holds still.
            as_of = min(asof, today()) if asof else today()
            found = timeline.timeline(engine, viewer, project_id, as_of, view, asof)
            return found if found is not None else JSONResponse({"code": "unknown_project"}, status_code=404)
        return read_for(f"the timeline of {project_id}", viewer, read)

    documents_shown = int(thresholds.value("app.documents_shown"))

    @app.get("/api/projects/{project_id}/packages")
    def project_packages(project_id: str, asof: dt.date | None = None, q: str = Query("", max_length=200),
                         page: int = Query(1, ge=1), viewer: Viewer = Depends(current_viewer)):
        return read_for(f"the packages of {project_id}", viewer,
                        lambda engine: projects.packages(engine, project_id, as_of_for(asof), q.strip(), page, page_size))

    @app.get("/api/projects/{project_id}/packages/{step_reference}")
    def activity(project_id: str, step_reference: str, asof: dt.date | None = None,
                 viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            found = trail.activity_trail(engine, project_id, step_reference, as_of_for(asof))
            return found if found is not None else JSONResponse({"code": "unknown_activity"}, status_code=404)
        return read_for(f"the trail of {step_reference}", viewer, read)

    @app.get("/api/projects/{project_id}/connections")
    def connections(project_id: str, asof: dt.date | None = None, viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            found = edges.neighbourhood(engine, project_id, as_of_for(asof))
            return found if found is not None else JSONResponse({"code": "unknown_project"}, status_code=404)
        return read_for(f"the connections of {project_id}", viewer, read)

    @app.get("/api/projects/{project_id}/documents")
    def project_documents(project_id: str, asof: dt.date | None = None, viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            found = documents.documents_tab(engine, project_id, as_of_for(asof), documents_shown)
            return found if found is not None else JSONResponse({"code": "unknown_project"}, status_code=404)
        return read_for(f"the documents of {project_id}", viewer, read)

    @app.get("/api/projects/{project_id}/documents/{doc}")
    def source_page(project_id: str, doc: str, page: int | None = Query(None, ge=0, le=100_000),
                    para: str | None = Query(None, max_length=32), passage: str | None = Query(None, max_length=256),
                    asof: dt.date | None = None, viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            found = documents.source_page(engine, project_id, doc, page, para, passage, as_of_for(asof))
            return found if found is not None else JSONResponse({"code": "unknown_project"}, status_code=404)
        return read_for(f"{doc} of {project_id}", viewer, read)

    def named(result):
        """A plan check with the project's name as its page header gives it, by the server's rule, so Check a
        plan's crumb reads as the project's tabs do (the 21 critique, round 3); the tool's own row is kept."""
        if isinstance(result, dict) and result.get("project"):
            result["project"]["display_name"] = projects.display_name(result["project"]["project_name"])
        return result

    def checked(result, viewer: Viewer, view: str, latest: bool, background: BackgroundTasks):
        """A plan check the viewer opened, recorded for their Packages tab (ticket 15) as the app's own service
        principal, after the answer is sent, so a slow or absent Lakebase never holds Check a plan. A preview
        records nothing, and a failed write changes nothing the viewer sees."""
        if packages is None or not isinstance(result, dict) or result.get("abstention") or view != STAFF \
                or not viewer.user_id or not result.get("plan"):
            return result
        plan, at = result["plan"], now()

        def record():
            try:
                packages.record_plan_check(viewer.user_id, plan["project_id"], plan["agency_id"],
                                           plan.get("implementing_agency"), dt.date.fromisoformat(plan["plan_date"]),
                                           latest, (result.get("counts") or {}).get("checked"), at)
            except Exception:  # the warehouse, the network or a token: none of them may change the page
                log.exception("I could not record that %s opened the plan check of %s.", viewer.user_id, plan["document_id"])
        background.add_task(record)
        return result

    @app.get("/api/projects/{project_id}/procurement/{agency_id}")
    def check_latest_plan(project_id: str, agency_id: str, background: BackgroundTasks, asof: dt.date | None = None,
                          view: str = "staff", viewer: Viewer = Depends(current_viewer)):
        return named(checked(run_tool("check_plan", {"project_id": project_id, "implementing_agency": agency_id},
                                      viewer, view, asof), viewer, view, latest=True, background=background))

    @app.get("/api/projects/{project_id}/procurement/{agency_id}/{version}")
    def check_plan_version(project_id: str, agency_id: str, version: dt.date, background: BackgroundTasks,
                           asof: dt.date | None = None, view: str = "staff", viewer: Viewer = Depends(current_viewer)):
        return named(checked(run_tool("check_plan", {"project_id": project_id, "implementing_agency": agency_id,
                                                     "plan_date": version}, viewer, view, asof), viewer, view, latest=False,
                             background=background))

    @app.get("/api/projects/{project_id}/procurement/{agency_id}/{version}/changes")
    def plan_changes(project_id: str, agency_id: str, version: dt.date, asof: dt.date | None = None,
                     viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            found = changes.plan_changes(engine, project_id, agency_id, version, as_of_for(asof))
            return found if found is not None else JSONResponse({"code": "unknown_plan"}, status_code=404)
        return read_for(f"the changes in {project_id}'s plan of {version}", viewer, read)

    def write_baseline(viewer: Viewer, view: str, what: str, write: Callable[[Engine], object]):
        """A write to an agency's baseline as the viewer, or why it was not made. Only a signed-in viewer
        in the World Bank staff view writes: a preview can only take things away (the 40 brief)."""
        if not viewer.user_id:
            return refused(401, "no_identity")
        if view != STAFF:
            return refused(403, "preview")
        return read_for(what, viewer, write)

    @app.put("/api/projects/{project_id}/procurement/{agency_id}/baseline")
    def save_baseline(project_id: str, agency_id: str, body: BaselineRequest, view: str = "staff",
                      viewer: Viewer = Depends(current_viewer)):
        def write(engine: Engine):
            saved = baseline.save(engine, project_id, agency_id, body.plan_date, viewer, now())
            return {"baseline": saved} if saved is not None else refused(404, "unknown_plan")
        return write_baseline(viewer, view, f"saving the baseline of {project_id}, {agency_id}", write)

    @app.delete("/api/projects/{project_id}/procurement/{agency_id}/baseline")
    def remove_baseline(project_id: str, agency_id: str, view: str = "staff", viewer: Viewer = Depends(current_viewer)):
        def write(engine: Engine):
            baseline.remove(engine, project_id, agency_id)
            return {"baseline": None}
        return write_baseline(viewer, view, f"removing the baseline of {project_id}, {agency_id}", write)

    @app.get("/api/data/readiness")
    async def data_readiness(sources: str | None = None, from_tool: str | None = Query(None, alias="from"),
                             asof: dt.date | None = None, view: str = "staff",
                             viewer: Viewer = Depends(current_viewer)):
        # An empty value reads as left out, so a link that writes sources= or from= opens the page.
        arguments = {"sources": sources or None, "from_tool": from_tool or None}
        return await as_viewer(viewer, lambda engine: registry.call(
            "data_readiness_for", arguments, registry.Context(engine, viewer, view, asof)),
            lambda result: result, say_timeout=True)

    @app.get("/api/data/sources")
    def data_sources() -> dict:
        return registry_page()

    def as_of_for(asof: dt.date | None) -> dt.date:
        """The page's as-of date, never later than today (ADR 0002)."""
        return min(asof, registry.today()) if asof else registry.today()

    @app.get("/api/lookup/loan")
    def look_up_loan(q: str = Query(min_length=1, max_length=64), asof: dt.date | None = None,
                     viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            found = lookup.loan(engine, q, as_of_for(asof))
            return found if found is not None else JSONResponse({"code": "unknown_loan"}, status_code=404)
        return read_for(f"loan {q}", viewer, read)

    @app.get("/api/lookup/activity")
    def look_up_activity(q: str = Query(min_length=1, max_length=128), asof: dt.date | None = None,
                         viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine):
            found = lookup.activity(engine, q, as_of_for(asof))
            return found if found is not None else JSONResponse({"code": "unknown_activity"}, status_code=404)
        return read_for(f"activity {q}", viewer, read)

    @app.get("/api/evidence")
    def open_evidence(evidence_id: str = Query(alias="id", min_length=1, max_length=512), asof: dt.date | None = None,
                      view: Literal["staff", "piu", "public"] = STAFF,
                      step_ref: str | None = Query(None, max_length=128), viewer: Viewer = Depends(current_viewer)):
        # The public view hides the baseline, and a preview only takes things away (the 21 review, round 3).
        if view == "public" and evidence_id.startswith(f"{baseline.TABLE}:"):
            return JSONResponse({"code": "unknown_evidence"}, status_code=404)

        def read(engine: Engine):
            found = evidence.read(engine, evidence_id, as_of_for(asof), step_ref, view=view)
            return found if found is not None else JSONResponse({"code": "unknown_evidence"}, status_code=404)
        return read_for(f"evidence {evidence_id}", viewer, read)

    @app.post("/api/evidence/opened")
    def record_opened(body: OpenedRequest, viewer: Viewer = Depends(current_viewer)) -> dict:
        # A preview can only take things away: someone looking through another view is not checking
        # sources as themselves, so nothing is recorded (the 14 brief, section 5.10).
        if opened is None or body.view != STAFF or not viewer.user_id:
            return {"recorded": False}
        return {"recorded": opened.record(viewer.user_id, body.evidence_id, body.run_id, body.route)}

    @app.get("/api/evidence/opened")
    def opened_sources(evidence_ids: list[str] = Query(default=[], alias="id", max_length=200),
                       viewer: Viewer = Depends(current_viewer)) -> dict:
        if opened is None or not viewer.user_id:
            return {"opened": []}
        return {"opened": opened.opened(viewer.user_id, evidence_ids)}

    @app.post("/api/disagreements/{disagreement_id}/choices")
    def keep_a_side(disagreement_id: str, body: ChoiceRequest, viewer: Viewer = Depends(current_viewer)):
        """Keep one side of a disagreement for an answer or a draft (ticket 23): one new row, with the viewer and the
        reason. Keeping the side Strata does not lean on needs a reason; keeping Strata's side is going back to it.
        A preview of another view records nothing."""
        if not viewer.token or not viewer.user_id:
            return refused(401, "no_identity")
        if body.view != STAFF:
            return {"recorded": False}
        if bool(body.run_id) == bool(body.draft_id):
            return refused(422, "bad_request", detail="Give the answer's run_id or the draft's draft_id, not both.")
        found = read_for(f"disagreement {disagreement_id}", viewer,
                         lambda engine: choice_routes.sides(engine, disagreement_id))
        if isinstance(found, JSONResponse):
            return found
        if found is None:
            return refused(404, "unknown_disagreement")
        if body.kept_assertion_id not in found["sides"]:
            return refused(422, "bad_request", detail="The kept assertion is not a side of this disagreement.")
        if body.kept_assertion_id != found["leaned"] and not body.reason:
            return refused(422, "reason_required")
        if choices is None:
            return refused(503, "not_recorded")
        reason = body.reason if body.kept_assertion_id != found["leaned"] else ""
        choice = choices.record(viewer.user_id, disagreement_id, body.kept_assertion_id, found["leaned"], reason,
                                body.run_id, body.draft_id)
        return {"recorded": True, "choice": choice} if choice else refused(503, "not_recorded")

    @app.get("/api/disagreements/{disagreement_id}/choices")
    def kept_side(disagreement_id: str, run_id: str | None = Query(default=None, max_length=128),
                  draft_id: str | None = Query(default=None, max_length=128), viewer: Viewer = Depends(current_viewer)):
        """The latest side this viewer kept for the answer or the draft, so the card shows it again after Back."""
        if choices is None or not viewer.user_id or bool(run_id) == bool(draft_id):
            return {"choice": None}
        try:
            return {"choice": choices.latest(viewer.user_id, disagreement_id, run_id, draft_id)}
        except Exception:  # the page shows Strata's choice, as for a new answer
            log.exception("I could not read %s's choice on disagreement %s.", viewer.user_id, disagreement_id)
            return {"choice": None}

    draft_routes.add_routes(app, engine_for=engine_for, store=drafts,
                            access=access, writers=writers or (lambda kind: None),
                            kinds=kinds or load_draft_kinds(), today=today, now=now, new_draft_id=new_draft_id,
                            new_run_id=new_run_id, runs=runs, trace_ids=trace_ids, reference=request_reference,
                            heartbeat_seconds=heartbeat_seconds, six_checks=six_checks)

    # Following and the follow buttons (ticket 37).
    following_routes.add_routes(app, engine_for=engine_for, store=follows, access=access, drafts=drafts, today=today,
                                now=now, reference=request_reference, track_record=signals_track.stored)

    package_routes.add_routes(app, engine_for=engine_for, store=packages, reader_for=package_reader or (lambda: None),
                              form=package_form or load_package_form(), thresholds=package_thresholds or thresholds,
                              today=today, now=now, new_package_id=new_package_id, new_save_id=new_save_id,
                              new_run_id=new_run_id, runs=runs, trace_ids=trace_ids, reference=request_reference,
                              heartbeat_seconds=heartbeat_seconds)
    # Section 2, the planned date for each STEP step (ticket 27).
    step_routes.add_routes(app, engine_for=engine_for, store=packages, form=package_form or load_package_form(),
                           thresholds=package_thresholds or thresholds, today=today, now=now,
                           reference=request_reference)
    risk_routes.add_routes(app, engine_for=engine_for, store=packages, form=package_form or load_package_form(),
                           thresholds=package_thresholds or thresholds, today=today, now=now,
                           reference=request_reference)
    feedback_routes.add_routes(app, engine_for=engine_for, record=feedback_record, reports=passage_reports,
                               judging=judging, reference=request_reference)

    def planned_criteria_package(viewer: Viewer, package_id: str) -> CriteriaPackage | None:
        """A planned package as section 5 reads it, for the person who made it only: its comparables' criteria,
        its cost estimate and its description (ticket 31)."""
        if packages is None:
            return None
        saved = packages.get(package_id)
        if saved is None or saved.author_id != viewer.user_id:
            return None
        from strata.packages.workflow import package_view

        shown = package_view(saved, package_form or load_package_form(), package_thresholds or thresholds)
        values = {entry["key"]: entry["value"] for entry in shown["fields"]}
        amount = values.get("estimated_amount_usd")
        return CriteriaPackage(f"planned:{package_id}", None, shown["comparables_query"],
                               float(amount) if isinstance(amount, int | float) else None, values.get("description"))

    criteria_routes.add_routes(app, engine_for=engine_for, store=criteria, reader_for=criteria_reader or (lambda: None),
                               planned=planned_criteria_package, thresholds=thresholds, today=today, now=now,
                               new_check_id=new_check_id, reference=request_reference,
                               heartbeat_seconds=heartbeat_seconds, six_checks=six_checks)

    @app.get("/api/packages/{step_reference}")
    def open_package(step_reference: str, asof: dt.date | None = None, viewer: Viewer = Depends(current_viewer)):
        as_of = asof or registry.today()

        def read(engine: Engine):
            found = read_package(engine, step_reference, as_of)
            if found is None:
                return JSONResponse({"code": "unknown_package"}, status_code=404)
            return {"as_of": as_of.isoformat(), "package": found}
        return read_for(f"package {step_reference}", viewer, read)

    @app.get("/api/packages/{step_reference}/comparables")
    def comparables(step_reference: str, request: Request, asof: dt.date | None = None, view: str = "staff",
                    viewer: Viewer = Depends(current_viewer)):
        # The criteria come from the query as the tool's own parameter names; the registry checks them.
        criteria = package_routes.comparables_criteria(request)
        if isinstance(criteria, JSONResponse):
            return criteria
        return run_tool("find_comparables", {**criteria, "step_reference": step_reference}, viewer, view, asof)

    @app.get("/api/packages/{step_reference}/rebidding")
    def rebidding(step_reference: str, request: Request, asof: dt.date | None = None, view: str = "staff",
                  viewer: Viewer = Depends(current_viewer)):
        # Section 1's "Advertised again" block (ticket 28): rebidding_risk with section 1's own criteria.
        criteria = package_routes.comparables_criteria(request)
        if isinstance(criteria, JSONResponse):
            return criteria
        return run_tool("rebidding_risk", {**criteria, "step_reference": step_reference}, viewer, view, asof)

    @app.get("/api/rebidding")
    def planned_rebidding(request: Request, asof: dt.date | None = None, view: str = "staff",
                          viewer: Viewer = Depends(current_viewer)):
        # The same for a package planned from a sentence, with its criteria as /api/comparables takes them.
        criteria = package_routes.comparables_criteria(request)
        if isinstance(criteria, JSONResponse):
            return criteria
        if "step_reference" in criteria:
            return JSONResponse({"code": "bad_request", "detail": "This route is for a package with no STEP reference."},
                                status_code=422)
        return run_tool("rebidding_risk", criteria, viewer, view, asof)

    def write_about_a_pair(viewer: Viewer, write: Callable[[SupplierLog, str], None]):
        """A decision or a label on a candidate pair, recorded with the viewer's user id, or why it was not."""
        if not viewer.user_id:
            return refused(401, "no_identity")
        if supplier_log is None:
            return refused(503, "not_recorded")
        try:
            write(supplier_log, viewer.user_id)
        except suppliers.UnknownPair:
            return refused(404, "unknown_pair")
        except EngineError:
            reference = request_reference()
            log.exception("I could not record a decision or label of %s, reference %s.", viewer.user_id, reference)
            return refused(503, "data_service", trace_id=reference)
        return {"recorded": True}

    @app.get("/api/suppliers/review")
    def supplier_review_list(viewer: Viewer = Depends(current_viewer)):
        return read_for("the supplier review list", viewer, suppliers.review_list)

    @app.post("/api/suppliers/review")
    def decide_supplier_pair(body: DecisionRequest, viewer: Viewer = Depends(current_viewer)):
        return write_about_a_pair(viewer, lambda log_, reviewer: log_.decide(body.pair_id, body.decision, reviewer,
                                                                            body.reason))

    @app.get("/api/suppliers/labels")
    def supplier_labeling_list(limit: int = Query(20, ge=1, le=100), viewer: Viewer = Depends(current_viewer)):
        return read_for("the supplier labeling list", viewer,
                        lambda engine: suppliers.labeling_list(engine, limit, labeled_pairs_target))

    @app.post("/api/suppliers/labels")
    def label_supplier_pair(body: LabelRequest, viewer: Viewer = Depends(current_viewer)):
        return write_about_a_pair(viewer, lambda log_, labeler: log_.label(body.pair_id, body.label, labeler))

    # ── Lessons (ticket 29): the library, the review queue and the reviewers' acts ──

    def lesson_read(what: str, viewer: Viewer, read: Callable[[Engine], object]):
        """A Lessons read as the viewer, or the refusal the review gives: not_a_reviewer, unknown_item."""
        def run(engine: Engine):
            try:
                return read(engine)
            except Refused as refusal:
                return refusal_response(refusal)
        return read_for(what, viewer, run)

    def refusal_response(refusal: Refused) -> JSONResponse:
        return JSONResponse(refusal.body(), status_code=refusal.status, headers={"Cache-Control": "no-store"})

    def lesson_write(what: str, viewer: Viewer, write: Callable[[Engine, Engine], dict]):
        """A reviewer's act: read as the viewer, and written as the app's own service principal with the viewer
        recorded as the actor, so the review record holds only acts the server allowed. Or why not."""
        if not viewer.email:
            return refused(401, "no_identity")
        if lesson_record is None:
            return refused(503, "not_recorded")

        def run(engine: Engine):
            record = lesson_record()
            try:
                return JSONResponse(write(engine, record), headers={"Cache-Control": "no-store"})
            except Refused as refusal:
                return refusal_response(refusal)
            finally:
                close = getattr(record, "close", None)
                if callable(close):
                    close()
        return read_for(what, viewer, run)

    @app.get("/api/lessons/me")
    def lessons_me(viewer: Viewer = Depends(current_viewer)):
        def read(engine: Engine) -> dict:
            # Each Lessons page the viewer may open, with its count, so the frame decides its sub-tabs before
            # any content renders (the 32 brief, section 2.3): Passage reports and Judging join brief 29's tabs.
            found = {**lessons.me(engine, viewer), **passage_reports.me(engine, viewer), **judging.me(engine, viewer)}
            found["tabs"] = [*found["tabs"], *(["reports"] if found["can_review_reports"] else []),
                             *(["judging"] if found["is_judge"] else [])]
            return found
        return lesson_read("the viewer's lesson tabs", viewer, read)

    @app.get("/api/lessons")
    def lesson_library(page: int = Query(1, ge=1, le=10_000), viewer: Viewer = Depends(current_viewer)):
        return lesson_read("the lesson library", viewer, lambda engine: lessons.library(engine, viewer, page))

    @app.get("/api/lessons/review")
    def lesson_queue(page: int = Query(1, ge=1, le=10_000), viewer: Viewer = Depends(current_viewer)):
        return lesson_read("the lesson review queue", viewer, lambda engine: lessons.queue(engine, viewer, page))

    @app.get("/api/lessons/review/{item_id}")
    def lesson_review_item(item_id: str, viewer: Viewer = Depends(current_viewer)):
        return lesson_read(f"lesson review item {item_id}", viewer, lambda engine: lessons.item(engine, viewer, item_id))

    @app.post("/api/lessons/review/{item_id}/summary")
    def rewrite_lesson_summary(item_id: str, viewer: Viewer = Depends(current_viewer)):
        return lesson_write(f"the summary of {item_id}", viewer,
                            lambda engine, record: lessons.rewrite(engine, viewer, item_id, lesson_writer(), record))

    @app.post("/api/lessons/review/{item_id}/{verb}")
    def lesson_review_act(item_id: str, verb: Literal["recommend", "decide", "cross-check"], body: LessonActRequest,
                          viewer: Viewer = Depends(current_viewer)):
        return lesson_write(f"a {verb} on {item_id}", viewer, lambda engine, record: lessons.act(
            engine, viewer, item_id, verb.replace("-", "_"), body.model_dump(), record))

    @app.post("/api/lessons/{lesson_id}/recheck")
    def ask_for_a_recheck(lesson_id: str, body: RecheckRequest, viewer: Viewer = Depends(current_viewer)):
        return lesson_write(f"a re-check of {lesson_id}", viewer,
                            lambda engine, record: lessons.recheck(engine, viewer, lesson_id, body.reason, record))

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/me")
    def me(viewer: Viewer = Depends(current_viewer)) -> dict:
        # Whether the viewer has the World Bank staff role (ticket 37): the navy bar's Projects tab then opens
        # Following, and the project page offers Follow.
        return {"email": viewer.email, "name": viewer.name, "signed_in": viewer.signed_in,
                "has_token": viewer.token is not None, "staff": access.is_staff(viewer)}

    @app.get("/api/me/warehouse")
    async def me_on_the_warehouse(viewer: Viewer = Depends(current_viewer)):
        return await as_viewer(viewer, warehouse_user, lambda user: {"warehouse_user": user})

    @app.get("/api/freshness")
    async def freshness(viewer: Viewer = Depends(current_viewer)):
        return await as_viewer(viewer, data_through,
                               lambda day: {"data_through": day.isoformat() if day else None})

    @app.post("/api/ask", tags=[MODEL])
    async def ask(body: AskRequest, viewer: Viewer = Depends(current_viewer)) -> StreamingResponse:
        scope = Scope(chip=body.scope.strip().upper() if body.scope and body.scope.strip() else None,
                      as_of=body.asof, view=body.view, language=body.lang)
        turn = Turn(question=body.question, viewer=viewer, run_id=new_run_id(), scope=scope, trace=trace_ids())
        return StreamingResponse(stream(turn), media_type="text/event-stream", headers=STREAM_HEADERS)

    async def stream(turn: Turn) -> AsyncIterator[str]:
        """The run's events, then its row in the run log, even when the viewer leaves part way."""
        started, outcome = dt.datetime.now(dt.UTC), {"verdict": None, "error_code": "stopped"}
        try:
            async for chunk in run_events(turn, outcome):
                yield chunk
        finally:
            row = run_row(turn, outcome["verdict"], outcome["error_code"], started, dt.datetime.now(dt.UTC))
            log.info("Run %s ended: %s.", turn.run_id, row["error_code"] or row["status"])
            # Each write in its own thread, so a dropped connection cannot stop it. The run row and the sources the
            # answer cited (ticket 32) are written side by side, so a report sent right after the answer finds them.
            # The run row starts first, so a fault while listing the cited sources never keeps it from being written.
            writers = []
            if runs is not None:
                writers.append(threading.Thread(target=runs.record, args=(row,), name=f"strata-run-{turn.run_id}"))
                writers[-1].start()
            if citations is not None and outcome["verdict"] is not None:
                try:
                    cited = cited_rows(turn, outcome["verdict"], row["as_of"], row["finished_at"])
                except Exception:  # a fact in a shape the list doesn't expect: the answer and its run row stand
                    log.exception("Run %s could not list its cited sources.", turn.run_id)
                else:
                    writers.append(threading.Thread(target=citations.record, args=(cited,),
                                                    name=f"strata-cited-{turn.run_id}"))
                    writers[-1].start()
            for writer in writers:
                await asyncio.to_thread(writer.join, 60)

    def cited_rows(turn: Turn, verdict: Verdict, as_of: dt.date, at: dt.datetime) -> list[tuple]:
        def project_of(evidence: str):
            found = turn.facts.get(evidence) or {}
            return found.get("project_id") or (found.get("source") or {}).get("project_id")
        return passage_reports.citation_rows(
            turn.run_id, turn.viewer.user_id, turn.question, as_of, turn.scope.view,
            [(sentence.index, sentence.claim.sentence, list(sentence.claim.evidence_ids)) for sentence in verdict.kept],
            turn.facts.tool, project_of, at, kind_of=turn.facts.kind)

    def as_of_of(turn: Turn) -> dt.date:
        return turn.notes.as_of or min(turn.scope.as_of or today(), today())

    async def verified(claims: list, turn: Turn) -> AsyncIterator[Event | Verdict]:
        """The six checks on the claims (src/strata/agent/answer_check.py), inside the verifier's step, with the two
        steps it may take inside it: getting the other side of a disagreement, and asking the judge. Ends with the
        verdict."""
        yield Event("step", {"id": "check", "kind": "check", "status": "running"})
        verdict = None
        asker = Asker(turn.viewer, turn.scope.view, as_of_of(turn), turn.run_id)
        async for item in six_checks.finish(six_checks.check(claims, turn.facts), turn.facts, asker):
            if isinstance(item, Verdict):
                verdict = item
            else:
                yield item
        yield Event("step", {"id": "check", "kind": "check", "status": "done", "removed": len(verdict.removed)})
        yield verdict

    async def run_events(turn: Turn, outcome: dict) -> AsyncIterator[str]:
        verdict, error_code = None, None
        try:
            async for item in with_heartbeats(runner(turn), heartbeat_seconds):
                if item is HEARTBEAT:
                    yield KEEP_ALIVE
                elif item.type == "claims":  # the verifier, with its own step, then the answer's events
                    refusal = item.data.get("refusal")
                    if refusal is not None:
                        yield frame(Event("refusal", {"key": refusal.key, "partial": refusal.partial}))
                    if refusal is not None and not refusal.partial:
                        verdict = Verdict((), ())  # nothing was written, so no check ran
                    else:
                        # Checks 6 and 4 can wait on the data service and the judge, so the stream keeps the
                        # connection alive while they run, as it does while the agent works.
                        async for event in with_heartbeats(verified(item.data["claims"], turn), heartbeat_seconds):
                            if event is HEARTBEAT:
                                yield KEEP_ALIVE
                            elif isinstance(event, Verdict):
                                verdict = event
                            else:
                                yield frame(event)
                    ran = [call["tool"] for call in turn.notes.tool_calls if call.get("ran")]
                    for event in answer_events(verdict, turn.facts, ran, six_checks.cited_only):
                        if event.type == "evidence":  # whether the drawer offers "Was this the right passage?"
                            event = Event("evidence", {**event.data, "feedback": passage_reports.feedback(
                                event.data, turn.run_id, turn.scope.view)})
                        yield frame(event)
                elif item.type in ANSWER_EVENTS:
                    raise RuntimeError(f"A runner sent a {item.type} event, which only the verifier writes.")
                else:
                    error_code = item.data.get("code") if item.type == "error" else error_code
                    yield frame(item)
        except RunError as error:
            log.warning("Run %s could not answer (%s): %s", turn.run_id, error.code, error)
            error_code = error.code if error.code in ERROR_CODES else "internal"
            yield frame(Event("error", {"code": error_code}))
        except Exception:
            log.exception("Run %s failed.", turn.run_id)
            error_code = "internal"
            yield frame(Event("error", {"code": "internal"}))
        done = {"run_id": turn.run_id}
        if turn.trace is not None and (turn.trace.application_insights or turn.trace.mlflow):
            done["trace_ids"] = {"application_insights": turn.trace.application_insights, "mlflow": turn.trace.mlflow}
        outcome.update(verdict=verdict, error_code=error_code or (None if verdict else "no_answer"))
        yield frame(Event("done", done))

    if web is not None:
        @app.get("/{address:path}", include_in_schema=False)
        def page(address: str):
            if address == "api" or address.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            file = web_file(address)
            if file is not None:
                lasting = file.parent.name == "assets"  # Vite names each asset by its content
                return FileResponse(file, headers={"Cache-Control": IMMUTABLE if lasting else "no-cache"})
            return FileResponse(web / "index.html", headers={"Cache-Control": "no-cache"})

    return app
