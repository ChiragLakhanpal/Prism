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

from strata.server import settings
from strata.server.settings import app_from_env, app_state_file

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
        def do_GET(self):
            # The SCIM API's answer for the viewer whose token asks: Ana is on the Kenya water team.
            calls.append(("scim", self.headers["Authorization"], self.path))
            groups = [{"display": "strata-team-kenya-water"}] if "ana" in self.headers["Authorization"] else []
            return self.answer({"userName": "viewer@example.org", "groups": groups})

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
            if "strata.ops.uploads" in statement["statement"]:
                calls.append(("uploads", self.headers["Authorization"], json.dumps(statement.get("parameters"))))
                return self.answer({"statement_id": "s-4", "status": {"state": "SUCCEEDED"},
                                    "manifest": {"schema": {"columns": [{"name": "upload_id", "position": 0}]}},
                                    "result": {"data_array": []}})
            if "strata.ops.drafts" in statement["statement"]:
                calls.append(("drafts", self.headers["Authorization"], json.dumps(statement.get("parameters"))))
                return self.answer({"statement_id": "s-2", "status": {"state": "SUCCEEDED"},
                                    "manifest": {"schema": {"columns": [{"name": "draft_id", "position": 0}]}},
                                    "result": {"data_array": []}})
            if "strata.gold.country" in statement["statement"]:  # the package workspace's country list
                return self.answer({"statement_id": "s-3", "status": {"state": "SUCCEEDED"}, "manifest": {"schema": {
                    "columns": [{"name": "country_code", "position": 0}, {"name": "country_name", "position": 1}]}},
                    "result": {"data_array": [["KE", "Kenya"]]}})
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


def test_on_the_app_an_opened_source_is_recorded_with_the_app_s_own_token():
    """A source a viewer opens in the evidence drawer goes to strata.ops.evidence_opened (ticket 14), written
    by the app as itself, with the viewer's user id and never their token."""
    with fake_workspace() as (host, calls):
        app = app_from_env({"DATABRICKS_HOST": host, "DATABRICKS_WAREHOUSE_ID": "wh-1",
                            "DATABRICKS_CLIENT_ID": "strata-app", "DATABRICKS_CLIENT_SECRET": "not-a-real-key"})

        async def open_source():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                    return await client.post("/api/evidence/opened", headers=ANA, json={
                        "evidence_id": "strata.gold.passage:31525018/v1/54", "route": "/projects/P130164"})

        answer = asyncio.run(open_source())

    assert answer.json() == {"recorded": True}
    writes = [auth for kind, auth, text in calls if kind == "statement" and "strata.ops.evidence_opened" in text]
    assert writes == ["Bearer app-not-real"]


def test_on_the_app_drafts_are_read_with_the_app_s_own_token_for_the_team_the_viewer_s_own_groups_name():
    """Drafts live in strata.ops, written and read by the app as itself (ticket 35), and the one access rule
    reads the viewer's workspace groups from the SCIM API with the viewer's own token, so it learns the
    viewer's team (config/roles.toml) without any other identity."""
    with fake_workspace() as (host, calls):
        app = app_from_env({"DATABRICKS_HOST": host, "DATABRICKS_WAREHOUSE_ID": "wh-1",
                            "DATABRICKS_CLIENT_ID": "strata-app", "DATABRICKS_CLIENT_SECRET": "not-a-real-key"})

        ana, ben = serve(app, [("/api/drafts", ANA), ("/api/drafts", BEN)])

    assert ana.json()["total"] == ben.json()["total"] == 0
    assert [(auth, path) for kind, auth, path in calls if kind == "scim"] == [
        ("Bearer token-for-ana-only", "/api/2.0/preview/scim/v2/Me"),
        ("Bearer token-for-ben-only", "/api/2.0/preview/scim/v2/Me")]
    reads = [(auth, json.loads(params)) for kind, auth, params in calls if kind == "drafts"]
    assert [auth for auth, _ in reads] == ["Bearer app-not-real", "Bearer app-not-real"]
    # Ben is in no team's group, so his team is his own.
    assert [[p["value"] for p in params if p["name"] == "team_key"] for _, params in reads] == [
        ["team:kenya-water"], ["viewer:4022@1984"]]


def test_on_the_app_uploads_are_read_with_the_app_s_own_token_for_the_viewer_s_team():
    """Uploads live in strata.ops beside the drafts, written and read by the app as itself (ticket 38), for the
    team the viewer's own groups name."""
    with fake_workspace() as (host, calls):
        app = app_from_env({"DATABRICKS_HOST": host, "DATABRICKS_WAREHOUSE_ID": "wh-1",
                            "DATABRICKS_CLIENT_ID": "strata-app", "DATABRICKS_CLIENT_SECRET": "not-a-real-key"})

        ana, ben = serve(app, [("/api/uploads", ANA), ("/api/uploads", BEN)])

    assert ana.json() == ben.json() == {"uploads": [], "preview": False}
    reads = [(auth, json.loads(params)) for kind, auth, params in calls if kind == "uploads"]
    assert [auth for auth, _ in reads] == ["Bearer app-not-real", "Bearer app-not-real"]
    assert [[p["value"] for p in params if p["name"] == "team_key"] for _, params in reads] == [
        ["team:kenya-water"], ["viewer:4022@1984"]]


def test_on_this_computer_uploads_are_kept_in_the_app_state_file(fixture_db, tmp_path):
    """STRATA_APP_STATE_FILE keeps uploads too: an upload kept in the file for Ana's own team is the one the app
    lists for her, and Ben, on a team of his own, gets none of it."""
    import datetime as dt

    from strata.lakehouse.engine import DuckDBEngine
    from strata.uploads.store import NewUpload, UploadStore

    state = tmp_path / "state.duckdb"
    app = app_from_env({"STRATA_DATABASE_FILE": str(fixture_db), "STRATA_APP_STATE_FILE": str(state)})
    UploadStore(lambda: DuckDBEngine.open(state)).create(NewUpload(
        "upl-000000000001", "viewer:4021@1984", "4021@1984", "Ana Example", None, "P156634",
        "Northern Water Works Development Agency", "plan.csv", {"activities": 0}, dt.datetime(2026, 10, 22, 9, 30,
                                                                                               tzinfo=dt.UTC)))

    ana, ben = serve(app, [("/api/uploads", ANA), ("/api/uploads", BEN)])

    assert [upload["upload_id"] for upload in ana.json()["uploads"]] == ["upl-000000000001"]
    assert ben.json() == {"uploads": [], "preview": False}


def test_on_this_computer_the_app_reads_the_fixture_database_and_serves_the_built_web_app(fixture_db, tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Prism</title>")
    (tmp_path / "assets" / "app-1a2b.js").write_text("console.log('Prism')")

    stamp, page, asset, missing = serve(
        app_from_env({"STRATA_DATABASE_FILE": str(fixture_db), "STRATA_WEB_DIST": str(tmp_path)}),
        [("/api/freshness", ANA), ("/projects/P130164", ANA), ("/assets/app-1a2b.js", {}), ("/api/nothing", {})])

    assert stamp.json() == json.loads((RECORDED / "freshness.json").read_text())
    # Every page is the web app's index, which routes the address itself.
    assert page.status_code == 200 and page.text == "<!doctype html><title>Prism</title>"
    assert page.headers["cache-control"] == "no-cache"
    assert asset.text == "console.log('Prism')"
    assert "immutable" in asset.headers["cache-control"]
    assert missing.status_code == 404 and missing.json() == {"detail": "Not Found"}


def test_a_page_address_never_reaches_a_file_outside_the_web_app(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("index")
    (tmp_path / "secret.txt").write_text("not for viewers")

    [response] = serve(app_from_env({"STRATA_WEB_DIST": str(web)}), [("/%2e%2e/secret.txt", {})])

    assert "not for viewers" not in response.text


def plan_and_list(app, body):
    async def go():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                planned = await client.post("/api/planned-packages", headers=ANA, json=body)
                listed = await client.get("/api/planned-packages", headers=ANA)
                return planned, listed
    return asyncio.run(go())


def test_on_this_computer_packages_are_kept_in_the_app_state_file(fixture_db, tmp_path):
    """STRATA_APP_STATE_FILE keeps the packages a person plans (ticket 15), in the app state tables. With no
    Foundry project named, reading a sentence says there is no reader, and setting the criteria yourself works."""
    app = app_from_env({"STRATA_DATABASE_FILE": str(fixture_db), "STRATA_APP_STATE_FILE": str(tmp_path / "state.duckdb"),
                        "STRATA_WEB_DIST": str(tmp_path)})

    read, _ = plan_and_list(app, {"sentence": "rural roads, Kenya, about US$15 million"})
    yourself, listed = plan_and_list(app, {"sentence": "rural roads, Kenya, about US$15 million", "read": False})

    assert "event: error" in read.text and '"no_reader"' in read.text
    assert "event: package" in yourself.text
    assert [row["type"] for row in listed.json()["rows"]] == ["package"]


def test_on_this_computer_the_lessons_page_remembers_the_reader_s_visit_in_the_app_state_file(fixture_db, tmp_path,
                                                                                               monkeypatch):
    """STRATA_APP_STATE_FILE keeps the reader's visits to Lessons (ticket 39), so the second load in one visit
    belongs to the visit the first load started, and each load adds one row to strata.ops.lesson_visits."""
    # DuckDB attaches a file once per process, so the count reads through the app's own opener of the file.
    openers = []
    monkeypatch.setattr(settings, "app_state_file", lambda environ: openers.append(app_state_file(environ)) or openers[-1])
    app = settings.app_from_env({"STRATA_DATABASE_FILE": str(fixture_db),
                                 "STRATA_APP_STATE_FILE": str(tmp_path / "state.duckdb"), "STRATA_WEB_DIST": str(tmp_path)})

    first, again = serve(app, [("/api/lessons/page", ANA), ("/api/lessons/page", ANA)])

    assert first.status_code == 200 and again.status_code == 200
    assert first.json()["visit"]["first_visit"] is True
    assert again.json()["visit"]["started_at"] == first.json()["visit"]["started_at"]
    [opener] = openers
    with opener() as engine:
        rows = engine.run("SELECT viewer_id FROM strata.ops.lesson_visits").rows
    assert rows == (("4021@1984",), ("4021@1984",))


def test_on_this_computer_two_uses_of_the_app_state_file_at_once_both_work(tmp_path):
    """scripts/dev's StrictMode sends each list request twice, so two requests open the app state file at once
    (ticket 15's critique, round 2, and ticket 35's verify F3). Both must get an engine that works."""
    opener = app_state_file({"STRATA_APP_STATE_FILE": str(tmp_path / "state.duckdb")})

    with opener() as first, opener() as second:
        listed = [engine.run("SELECT count(*) FROM strata.ops.drafts").rows for engine in (first, second)]
        zone = second.run("SELECT current_setting('TimeZone')").rows

    assert listed == [((0,),), ((0,),)]
    assert zone == (("UTC",),)
    with opener() as again:
        assert again.run("SELECT count(*) FROM strata.ops.drafts").rows == ((0,),)


def test_on_the_app_a_package_is_saved_in_lakebase_signed_in_as_the_app_with_its_own_token(monkeypatch):
    """App state lives in Lakebase (ADR 0005). The app's database resource names the database, and the app signs
    in as its own service principal with its own token; the viewer's token never reaches Lakebase."""
    from strata.appstate import lakebase

    connections = []

    class Cursor:
        description = None

        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql, params=None):
            self.connection.statements.append((sql, params))

        def executemany(self, sql, params):
            self.connection.statements.append((sql, list(params)))

        def fetchall(self):
            return []

    class Connection:
        closed = broken = False

        def __init__(self, settings):
            self.settings, self.statements = settings, []

        def cursor(self):
            return Cursor(self)

        def close(self):
            self.closed = True

    monkeypatch.setattr(lakebase, "_psycopg_connect", lambda **settings: connections.append(Connection(settings)) or connections[-1])
    with fake_workspace() as (host, calls):
        app = app_from_env({"DATABRICKS_HOST": host, "DATABRICKS_WAREHOUSE_ID": "wh-1",
                            "DATABRICKS_CLIENT_ID": "strata-app", "DATABRICKS_CLIENT_SECRET": "not-a-real-key",
                            "PGHOST": "instance-1.database.cloud.databricks.com", "PGPORT": "5432",
                            "PGDATABASE": "databricks_postgres", "PGUSER": "strata-app", "PGSSLMODE": "require"})

        planned, _ = plan_and_list(app, {"sentence": "rural roads, Kenya, about US$15 million", "read": False})

    assert "event: package" in planned.text
    assert {connection.settings["password"] for connection in connections} == {"app-not-real"}
    assert {connection.settings["user"] for connection in connections} == {"strata-app"}
    statements = [sql for connection in connections for sql, _ in connection.statements]
    assert any(sql.startswith("INSERT INTO app.planned_packages") for sql in statements)
    params = json.dumps([params for connection in connections for _, params in connection.statements], default=str)
    assert "4021@1984" in params and "token-for-ana-only" not in params
