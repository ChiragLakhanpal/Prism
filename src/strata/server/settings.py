"""The app as its environment sets it up: on the Databricks App, or on this computer.

`python -m strata.server` and the Databricks App start the server through app_from_env(), which
reads only the environment it is given:

- DATABRICKS_HOST and DATABRICKS_WAREHOUSE_ID (the app's sql-warehouse resource): each viewer's
  queries run on that warehouse with their own forwarded token. Without them, STRATA_LOCAL_DB or
  the gate's fixture database (data/out/fixture.duckdb) stands in, read-only, on this computer.
- DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET, which the platform sets for the app's own
  service principal: usage events are written to strata.ops.usage_events with its token.
  Without them, the server keeps no usage events.
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
from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI

from strata.config import load_thresholds
from strata.lakehouse.engine import DuckDBEngine, EngineError, Transport, WarehouseEngine, http_transport
from strata.server import tracing
from strata.server.app import create_app
from strata.server.usage import UsageLog
from strata.server.viewer_sql import SqlAs, warehouse_as_viewer

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
WEB_DIST = ROOT / "web" / "dist"
TOKEN_PATH = "/oidc/v1/token"
# A token is renewed this long before Databricks says it expires.
RENEW_SECONDS = 300


def _base(host: str) -> str:
    return host.rstrip("/") if host.startswith("http") else f"https://{host.rstrip('/')}"


def app_token(host: str, client_id: str, client_secret: str, timeout: int = 30):
    """The app's own access token, from its service principal's client id and secret (OAuth
    machine-to-machine), kept until shortly before it expires."""
    lock, held = threading.Lock(), {"token": None, "until": 0.0}
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    def token() -> str:
        with lock:
            if held["token"] is None or time.monotonic() >= held["until"]:
                form = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "all-apis"}).encode()
                request = urllib.request.Request(_base(host) + TOKEN_PATH, data=form, method="POST", headers={
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


def _sql_as(environ: Mapping[str, str], timeout: float) -> SqlAs | None:
    host, warehouse = environ.get("DATABRICKS_HOST", "").strip(), environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    if host and warehouse:
        return warehouse_as_viewer(host, warehouse, timeout)
    local = Path(environ.get("STRATA_LOCAL_DB") or FIXTURE_DB)
    if local.is_file():
        return lambda viewer: DuckDBEngine.open(local, read_only=True)
    return None


def _usage(environ: Mapping[str, str], flush_seconds: float) -> UsageLog | None:
    host, warehouse = environ.get("DATABRICKS_HOST", "").strip(), environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    client_id, secret = environ.get("DATABRICKS_CLIENT_ID", ""), environ.get("DATABRICKS_CLIENT_SECRET", "")
    if not (host and warehouse and client_id and secret):
        return None
    transport = as_the_app(host, client_id, secret)
    return UsageLog(lambda: WarehouseEngine(warehouse, transport), flush_seconds)


def app_from_env(environ: Mapping[str, str] | None = None) -> FastAPI:
    environ = os.environ if environ is None else environ
    thresholds = load_thresholds()
    timeout = thresholds.value("app.stamp_timeout_seconds")
    web = Path(environ["STRATA_WEB_DIST"]) if environ.get("STRATA_WEB_DIST") else WEB_DIST
    return create_app(sql_as=_sql_as(environ, timeout), stamp_timeout_seconds=timeout,
                      usage=_usage(environ, thresholds.value("app.usage_flush_seconds")),
                      tracer_provider=tracing.from_env(environ),
                      web_dist=web if (web / "index.html").is_file() else None)
