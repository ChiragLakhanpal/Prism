"""The app as its environment sets it up: on the Databricks App, or on this computer.

`python -m strata.server` and the Databricks App start the server through app_from_env(), which
reads only the environment it is given:

- DATABRICKS_HOST and DATABRICKS_WAREHOUSE_ID (the app's sql-warehouse resource): each viewer's
  queries run on that warehouse with their own forwarded token. On this computer,
  STRATA_DATABASE_FILE names a DuckDB file, such as the gate's fixture database, to read instead
  (src/strata/server/engines.py decides).
- DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET, which the platform sets for the app's own
  service principal: usage events are written to strata.ops.usage_events, each answer stream's run
  to strata.ops.agent_runs, each source a viewer opens in the evidence drawer to
  strata.ops.evidence_opened, drafts to strata.ops.drafts and the tables beside it (ticket 35), and
  each decision or label a person gives a candidate pair of supplier name matching to
  strata.ops.supplier_review_decisions or supplier_pair_labels, and each lesson reviewer's act to the
  lesson review tables (ticket 29), with its token. Each row names the viewer the Databricks App
  forwarded. Without them, the server
  keeps no usage events, records no opened sources, decisions, labels or lesson reviews and keeps no drafts, and runs go
  to the server log only. On this computer, STRATA_APP_STATE_FILE can name a DuckDB file that keeps the
  opened sources and the drafts instead.
- PGHOST, PGPORT, PGDATABASE, PGUSER and PGSSLMODE, which the platform sets for the app's Lakebase database
  resource: app state lives there (ADR 0005; src/strata/appstate), starting with the packages a person
  plans and the plan checks they open (ticket 15). The app signs in as its own service principal, with the
  token its client id and secret get. Without a database, on this computer, STRATA_APP_STATE_FILE keeps
  packages too; without either, planning a package says there is no data service.
- DATABRICKS_HOST also gives the one access rule (src/strata/server/access.py) each viewer's workspace
  groups, read from the SCIM API with their own token, which config/roles.toml turns into a team.
- FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_TENANT_ID, FOUNDRY_CLIENT_ID and FOUNDRY_CLIENT_SECRET (the app's
  four foundry-* secret resources, which ops/app/deploy_app.py sets): /api/ask answers through the
  Foundry agent, and each draft kind's writer is its Foundry writer agent (src/strata/agent/runner.py).
  Without them, /api/ask says there is no agent, drafting says there is no writer, and planning a package
  from a sentence says there is no reader. The package reader is the agent config/agents.toml names
  package_reader, and section 5's criteria reader the one it names criteria_reader (ticket 31), whose
  runs the app state store keeps beside the packages.
- APPLICATIONINSIGHTS_CONNECTION_STRING (the app's appinsights secret resource): traces go to
  Application Insights (src/strata/server/tracing.py).
- STRATA_WEB_DIST: the built web app to serve, by default web/dist when it exists.

The settings are read once, when the server starts. They hold the app's own identity, never a
viewer's.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path

from fastapi import FastAPI

from strata.agent import runner as agent_runner
from strata.agent.runs import RunLog
from strata.appstate import lakebase
from strata.config import load_roles, load_thresholds
from strata.drafts.store import DraftStore
from strata.server.following import FollowStore
from strata.knowledge.lessons.review import LessonReview
from strata.lakehouse.engine import Engine, EngineError, Transport, WarehouseEngine, base_url, http_transport
from strata.packages.store import PackageStore
from strata.criteria.store import CriteriaStore
from strata.server import engines, tracing
from strata.server.access import Access, NoGroups, WorkspaceGroups
from strata.agent import judge as answer_judge
from strata.server.app import create_app
from strata.knowledge.retrieval.judging import Judging
from strata.knowledge.retrieval.reports import CitationLog, PassageReports
from strata.server.evidence import OpenedLog
from strata.server.suppliers import SupplierLog
from strata.server.usage import UsageLog

ROOT = Path(__file__).resolve().parents[3]
WEB_DIST = ROOT / "web" / "dist"
TOKEN_PATH = "/oidc/v1/token"
# A token is renewed this long before Databricks says it expires.
RENEW_SECONDS = 300


def app_token(host: str, client_id: str, client_secret: str, timeout: int = 30):
    """The app's own access token, from its service principal's client id and secret (OAuth
    machine-to-machine), kept until shortly before it expires."""
    lock, held = threading.Lock(), {"token": None, "until": 0.0}
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    def token() -> str:
        with lock:
            if held["token"] is None or time.monotonic() >= held["until"]:
                form = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "all-apis"}).encode()
                request = urllib.request.Request(base_url(host) + TOKEN_PATH, data=form, method="POST", headers={
                    "Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"})
                try:
                    with urllib.request.urlopen(request, timeout=timeout) as response:
                        reply = json.loads(response.read())
                except OSError as error:
                    raise EngineError(f"The workspace gave the app no token: {error}") from error
                held["token"] = reply["access_token"]
                held["until"] = time.monotonic() + max(0, int(reply.get("expires_in", 3600)) - RENEW_SECONDS)
            return held["token"]

    return token


def as_the_app(host: str, client_id: str, client_secret: str) -> Transport:
    """Calls to the workspace's REST API as the app's own service principal."""
    token = app_token(host, client_id, client_secret)
    return lambda method, path, body: http_transport(host, token())(method, path, body)


def _the_app_s_engine(environ: Mapping[str, str]) -> Callable[[], Engine] | None:
    """The SQL warehouse as the app's own service principal, for the rows the app writes itself."""
    host, warehouse = environ.get("DATABRICKS_HOST", "").strip(), environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    client_id, secret = environ.get("DATABRICKS_CLIENT_ID", ""), environ.get("DATABRICKS_CLIENT_SECRET", "")
    if not (host and warehouse and client_id and secret):
        return None
    transport = as_the_app(host, client_id, secret)
    return lambda: WarehouseEngine(warehouse, transport)


def app_state_file(environ: Mapping[str, str]) -> Callable[[], Engine] | None:
    """On this computer, STRATA_APP_STATE_FILE names a DuckDB file for the opened sources, the drafts and the
    packages, made with the catalog's tables, so scripts/dev can write a draft without the workspace.

    DuckDB refuses to attach one file twice in a process, and two requests can arrive at once (React's
    StrictMode sends each of scripts/dev's reads twice). So the file is opened once, on first use, and each use
    gets its own cursor of that connection, which closing leaves the file open for the next."""
    path = environ.get("STRATA_APP_STATE_FILE", "").strip()
    if not path:
        return None
    from strata.lakehouse import catalog
    from strata.lakehouse.engine import DuckDBEngine

    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    lock, held = threading.Lock(), {}

    def open_state() -> Engine:
        with lock:
            if "engine" not in held:
                held["engine"] = DuckDBEngine.open(path)
            return held["engine"].cursor()

    return open_state


def _app_state(environ: Mapping[str, str]) -> Callable[[], Engine] | None:
    """Lakebase, as the app's database resource names it, signed in with the app's own token (ADR 0005)."""
    host = environ.get("DATABRICKS_HOST", "").strip()
    client_id, secret = environ.get("DATABRICKS_CLIENT_ID", ""), environ.get("DATABRICKS_CLIENT_SECRET", "")
    if not (host and client_id and secret):
        return None
    return lakebase.from_environment(environ, app_token(host, client_id, secret))


def app_from_env(environ: Mapping[str, str] | None = None) -> FastAPI:
    environ = os.environ if environ is None else environ
    thresholds = load_thresholds()
    timeout = thresholds.value("app.stamp_timeout_seconds")
    web = Path(environ["STRATA_WEB_DIST"]) if environ.get("STRATA_WEB_DIST") else WEB_DIST
    engine_for = engines.from_environment(environ, timeout_seconds=timeout)
    the_app = _the_app_s_engine(environ)
    state_file = app_state_file(environ) if not the_app else None
    state = the_app or state_file
    app_state = _app_state(environ) or state_file
    host = environ.get("DATABRICKS_HOST", "").strip()
    return create_app(engine_for=engine_for, runner=agent_runner.from_environment(environ, engine_for),
                      stamp_timeout_seconds=timeout,
                      usage=UsageLog(the_app, thresholds.value("app.usage_flush_seconds")) if the_app else None,
                      runs=RunLog(the_app) if the_app else None,
                      opened=OpenedLog(state) if state else None,
                      drafts=DraftStore(state) if state else None,
                      follows=FollowStore(state) if state else None,
                      packages=PackageStore(app_state) if app_state else None,
                      package_reader=agent_runner.agent_from_environment(environ, "package_reader"),
                      criteria=CriteriaStore(app_state) if app_state else None,
                      criteria_reader=agent_runner.agent_from_environment(environ, "criteria_reader"),
                      writers=agent_runner.writers_from_environment(environ),
                      access=Access(load_roles(), WorkspaceGroups(host) if host else NoGroups()),
                      supplier_log=SupplierLog(the_app) if the_app else None,
                      lessons=LessonReview(load_roles()), lesson_record=the_app,
                      passage_reports=PassageReports(load_roles()), judging=Judging(load_roles()),
                      feedback_record=the_app, citations=CitationLog(the_app) if the_app else None,
                      lesson_writer=agent_runner.lesson_writer_from_environment(environ),
                      tracer_provider=tracing.from_env(environ), judge=answer_judge.from_environment(environ),
                      web_dist=web if (web / "index.html").is_file() else None)
