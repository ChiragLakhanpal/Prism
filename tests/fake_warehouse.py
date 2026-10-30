"""A workspace on this computer for the scripts that write as the App (ticket 129), shared by
tests/test_app_secret_fallback.py's tests.

Its token endpoint (/oidc/v1/token) hands the App's client id and secret a token, or refuses them the way the workspace
does once the platform has restarted the App and made its service principal a new secret: 401 with OAuth's
invalid_client. Its SQL warehouse (the Statement Execution API's POST /api/2.0/sql/statements/) runs each statement on
a DuckDB database, a copy of the fixture database when a test gives one, and answers in the API's JSON_ARRAY form with
a manifest of types, which WarehouseEngine reads back (ticket 128). Without a database, every statement succeeds with
no rows. Each call is kept with the token it carried, so a test can see whose token wrote each row.
"""

from __future__ import annotations

import datetime as dt
import decimal
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from strata.lakehouse.engine import STATEMENTS, DuckDBEngine, typed

TOKEN_PATH = "/oidc/v1/token"
APP_TOKEN = "not-a-real-key"
# What the workspace answered on October 28 and 29, 2026, once the platform had replaced the App's secret.
REFUSED = {"error": "invalid_client", "error_description": "Client authentication failed"}


def _kind(values) -> str:
    """The type the warehouse's manifest would name for a column holding these Python values."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            return "BOOLEAN"
        if isinstance(value, int):
            return "LONG"
        if isinstance(value, float):
            return "DOUBLE"
        if isinstance(value, decimal.Decimal):
            return "DECIMAL"
        if isinstance(value, dt.datetime):
            return "TIMESTAMP" if value.tzinfo else "TIMESTAMP_NTZ"
        if isinstance(value, dt.date):
            return "DATE"
        return "STRING"
    return "STRING"


def _text(value):
    """One value as the warehouse writes it in JSON_ARRAY: text, or null."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=str)
    return str(value)


@contextmanager
def workspace(database: Path | None = None, token_status: int = 200):
    """The workspace's address and the list of its calls: ("token", authorization) for each token request and
    ("statement", authorization, sql) for each statement. token_status 401 refuses the App's client id and secret;
    another status that is not 200 is the endpoint failing for some other reason."""
    calls: list[tuple] = []
    lock = threading.Lock()
    engine = DuckDBEngine.open(database) if database else None

    def run(statement: dict) -> dict:
        if engine is None:
            return {"statement_id": "s-0", "status": {"state": "SUCCEEDED"},
                    "manifest": {"schema": {"columns": []}}, "result": {"data_array": []}}
        params = {given["name"]: typed(given.get("value"), given.get("type"))
                  for given in statement.get("parameters") or []}
        with lock:
            try:
                result = engine.run(statement["statement"], params)
            except Exception as error:  # noqa: BLE001 - the warehouse says why a statement failed
                return {"statement_id": "s-1", "status": {"state": "FAILED", "error": {"message": str(error)}}}
        columns = [{"name": name, "position": at, "type_name": _kind(row[at] for row in result.rows)}
                   for at, name in enumerate(result.columns)]
        return {"statement_id": "s-1", "status": {"state": "SUCCEEDED"}, "manifest": {"schema": {"columns": columns}},
                "result": {"data_array": [[_text(value) for value in row] for row in result.rows]}}

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
                return self.answer(run(statement))
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
