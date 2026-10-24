"""The app as it starts from its environment, at seam 3: the Databricks App's settings, or this
computer's.

On the App, the platform sets DATABRICKS_HOST, the app's own client id and secret, and the
warehouse id its resource names. A fake workspace on this computer stands in for Databricks here,
so the tests can see which token each call carried: each viewer's query goes with their own
forwarded token, and the usage events go with the app's own. The real workspace is a workspace
step (docs/workspace-catchup.md).
"""

import asyncio
import base64
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import httpx

from strata.server.settings import app_from_env

RECORDED = Path(__file__).parent / "fixtures" / "api"
ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}
BEN = {
    "X-Forwarded-Email": "ben.example@worldbank.org",
    "X-Forwarded-User": "4022@1984",
    "X-Forwarded-Access-Token": "token-for-ben-only",
}


def serve(app, requests):
    async def go():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                return [await client.get(path, headers=headers) for path, headers in requests]
    return asyncio.run(go())


@contextmanager
def fake_workspace():
    """A workspace that hands the app a token for its own client id and secret, and runs statements."""
    calls = []

    class Workspace(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"] or 0))
            if self.path == "/oidc/v1/token":
                calls.append(("token", self.headers["Authorization"], parse_qs(body.decode())))
                return self.answer({"access_token": "app-not-real", "token_type": "Bearer",
                                    "expires_in": 3600})
            statement = json.loads(body)
            calls.append(("statement", self.headers["Authorization"], statement["statement"]))
            if "strata.ops.agent_runs" in statement["statement"]:
                calls.append(("run", self.headers["Authorization"], json.dumps(statement.get("parameters"))))
            return self.answer({"statement_id": "s-1", "status": {"state": "SUCCEEDED"},
                                "manifest": {"schema": {"columns": [{"name": "data_through", "position": 0}]}},
                                "result": {"data_array": [["2026-10-21"]]}})

        def answer(self, reply):
            data = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Workspace)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", calls
    finally:
        server.shutdown()
        server.server_close()


def test_on_the_app_each_viewer_s_query_carries_their_own_token_and_usage_events_carry_the_app_s():
    with fake_workspace() as (host, calls):
        app = app_from_env({"DATABRICKS_HOST": host, "DATABRICKS_WAREHOUSE_ID": "wh-1",
                            "DATABRICKS_CLIENT_ID": "strata-app", "DATABRICKS_CLIENT_SECRET": "not-a-real-key",
                            "DATABRICKS_APP_NAME": "strata"})

        ana, ben = serve(app, [("/api/freshness", ANA), ("/api/freshness", BEN)])

    assert ana.json() == ben.json() == {"data_through": "2026-10-21"}
    statements = [(auth, text) for kind, auth, text in calls if kind == "statement"]
    assert [auth for auth, text in statements if "data_readiness" in text] == [
        "Bearer token-for-ana-only", "Bearer token-for-ben-only"]
    [(token_auth, form)] = [(auth, form) for kind, auth, form in calls if kind == "token"]
    assert token_auth == "Basic " + base64.b64encode(b"strata-app:not-a-real-key").decode()
    assert form["grant_type"] == ["client_credentials"]
    assert [auth for auth, text in statements if "usage_events" in text] == ["Bearer app-not-real"]


def test_on_the_app_each_answer_stream_s_run_is_logged_with_the_app_s_own_token():
    """Every run goes to strata.ops.agent_runs (ticket 13). The app writes it as itself, so no viewer's token
    can write another person's run. With no Foundry agent named, the run is logged as one that failed."""
    with fake_workspace() as (host, calls):
        app = app_from_env({"DATABRICKS_HOST": host, "DATABRICKS_WAREHOUSE_ID": "wh-1",
                            "DATABRICKS_CLIENT_ID": "strata-app", "DATABRICKS_CLIENT_SECRET": "not-a-real-key"})

        async def ask():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                    return await client.post("/api/ask", headers=ANA, json={"question": "Why was P130164 rebid?"})

        answer = asyncio.run(ask())

    assert "no_agent" in answer.text
    runs = [(auth, params) for kind, auth, params in calls if kind == "run"]
    assert [auth for auth, _ in runs] == ["Bearer app-not-real"]
    assert "4021@1984" in runs[0][1] and "token-for-ana-only" not in runs[0][1]


def test_on_this_computer_the_app_reads_the_fixture_database_and_serves_the_built_web_app(fixture_db, tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Strata</title>")
    (tmp_path / "assets" / "app-1a2b.js").write_text("console.log('Strata')")

    stamp, page, asset, missing = serve(
        app_from_env({"STRATA_DATABASE_FILE": str(fixture_db), "STRATA_WEB_DIST": str(tmp_path)}),
        [("/api/freshness", ANA), ("/projects/P130164", ANA), ("/assets/app-1a2b.js", {}), ("/api/nothing", {})])

    assert stamp.json() == json.loads((RECORDED / "freshness.json").read_text())
    # Every page is the web app's index, which routes the address itself.
    assert page.status_code == 200 and page.text == "<!doctype html><title>Strata</title>"
    assert page.headers["cache-control"] == "no-cache"
    assert asset.text == "console.log('Strata')"
    assert "immutable" in asset.headers["cache-control"]
    assert missing.status_code == 404 and missing.json() == {"detail": "Not Found"}


def test_a_page_address_never_reaches_a_file_outside_the_web_app(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("index")
    (tmp_path / "secret.txt").write_text("not for viewers")

    [response] = serve(app_from_env({"STRATA_WEB_DIST": str(web)}), [("/%2e%2e/secret.txt", {})])

    assert "not for viewers" not in response.text
