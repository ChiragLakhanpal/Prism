"""A workspace on this computer for the scripts that write as the App (ticket 129), shared by
tests/test_app_secret_fallback.py's tests.

Its token endpoint (/oidc/v1/token) hands the App's client id and secret a token, or refuses them the way the workspace
does once the platform has restarted the App and made its service principal a new secret: 401 with OAuth's
invalid_client. Its SQL warehouse (the Statement Execution API's POST /api/2.0/sql/statements/) is
tests/warehouse_over_fixture.py's (ticket 128), on a copy of the fixture database that a test gives and the statements
may write to. Without a database, every statement succeeds with no rows. Each call is kept with the token it carried,
so a test can see whose token wrote each row.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from warehouse_over_fixture import WarehouseOverFixture

from strata.lakehouse.engine import STATEMENTS, DuckDBEngine

TOKEN_PATH = "/oidc/v1/token"
APP_TOKEN = "not-a-real-key"
# What the workspace answered on October 28 and 29, 2026, once the platform had replaced the App's secret.
REFUSED = {"error": "invalid_client", "error_description": "Client authentication failed"}
NO_ROWS = {"statement_id": "s-0", "status": {"state": "SUCCEEDED"}, "manifest": {"schema": {"columns": []}},
           "result": {"data_array": []}}


@contextmanager
def workspace(database: Path | None = None, token_status: int = 200):
    """The workspace's address and the list of its calls: ("token", authorization) for each token request and
    ("statement", authorization, sql) for each statement. token_status 401 refuses the App's client id and secret;
    another status that is not 200 is the endpoint failing for some other reason."""
    calls: list[tuple] = []
    warehouse = WarehouseOverFixture(database) if database else None
    engine = DuckDBEngine.open(database) if database else None

    class Workspace(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"] or 0))
            if self.path == TOKEN_PATH:
                calls.append(("token", self.headers["Authorization"]))
                if token_status == 401:
                    return self.answer(REFUSED, status=401)
                if token_status != 200:
                    return self.answer({"error": "temporarily_unavailable"}, status=token_status)
                return self.answer({"access_token": APP_TOKEN, "token_type": "Bearer", "expires_in": 3600})
            if self.path == STATEMENTS:
                statement = json.loads(body)
                calls.append(("statement", self.headers["Authorization"], statement["statement"]))
                return self.answer(warehouse.answer(engine, "POST", STATEMENTS, statement) if warehouse else NO_ROWS)
            return self.answer({"error_code": "NOT_FOUND"}, status=404)

        def answer(self, reply: dict, status: int = 200):
            data = json.dumps(reply).encode()
            self.send_response(status)
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
        if engine is not None:
            engine.close()
