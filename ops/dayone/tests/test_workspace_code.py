"""The code the probes run inside Databricks, run here against a local HTTP server.

The reach script, the Azure script and the probe app use only the standard library, so they run
the same way on this computer. Only localhost is used, so these tests need no network.
"""

import ast
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import live  # noqa: E402
from dayone import ProbeError  # noqa: E402

APP = REPO / "ops" / "dayone" / "workspace" / "probe_app" / "app.py"


class Answers(BaseHTTPRequestHandler):
    CODES = {"/ok": 200, "/missing": 404, "/locked": 401}

    def do_GET(self):
        self.send_response(self.CODES.get(self.path, 500))
        self.end_headers()

    def log_message(self, *args):
        pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Answers)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def hosts(server):
    return {"open": f"{server}/ok", "missing": f"{server}/missing", "closed": f"http://127.0.0.1:{free_port()}/"}


def run_script(tmp_path, source):
    script = tmp_path / "probe_copy.py"
    script.write_text(source)
    done = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True, timeout=60, cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_the_job_copy_of_the_reach_script_reports_each_hosts_answer(tmp_path, server):
    source = live.render_source("reach_hosts.py", {"hosts": hosts(server)}, notebook=False)
    assert not source.startswith(live.NOTEBOOK_HEADER)
    result = live.parse_result(run_script(tmp_path, source))
    assert result["open"] == 200
    assert result["missing"] == 404
    assert result["closed"].startswith("no answer")


def test_the_notebook_copy_keeps_its_header():
    source = live.render_source("reach_hosts.py", {"hosts": {}}, notebook=True)
    assert source.splitlines()[0] == live.NOTEBOOK_HEADER


def test_the_azure_script_counts_a_401_as_an_answer_and_reports_a_missing_key(tmp_path, server):
    settings = {"foundry_endpoint": f"{server}/locked", "openai_endpoint": f"{server}/openai/v1", "scope": "strata"}
    source = live.render_source("azure_from_job.py", settings, notebook=False)
    result = live.parse_result(run_script(tmp_path, source))
    assert result["foundry"] == 401
    assert isinstance(result["openai"], int)
    assert result["openai_with_key"].startswith("no key")


def test_a_notebook_exit_value_and_a_printed_line_both_parse():
    assert live.parse_result('{"a": 1}') == {"a": 1}
    assert live.parse_result('starting\nSTRATA_DAYONE_RESULT {"a": 2}\n') == {"a": 2}
    with pytest.raises(ProbeError):
        live.parse_result("Traceback (most recent call last): ...")


@pytest.fixture
def probe_app(server):
    port = free_port()
    env = {"PATH": os.environ["PATH"], "DATABRICKS_APP_PORT": str(port),
           "STRATA_DAYONE_SETTINGS": json.dumps({"hosts": hosts(server), "version": "v-test"})}
    app = subprocess.Popen([sys.executable, "-I", str(APP)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/dayone", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    yield base
    app.terminate()
    app.wait(timeout=10)


def get(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())


def test_the_probe_app_reports_its_version_and_that_tracing_is_off_without_a_connection_string(probe_app):
    answer = get(probe_app + "/dayone")
    assert answer["version"] == "v-test"
    assert answer["tracing"].startswith("off")


def test_the_probe_app_reports_each_hosts_answer(probe_app):
    answer = get(probe_app + "/dayone/reach")
    assert answer["open"] == 200 and answer["missing"] == 404
    assert answer["closed"].startswith("no answer")


def test_the_probe_app_explains_why_it_cannot_send_a_trace(probe_app):
    answer = get(probe_app + "/dayone/trace?marker=m-1")
    assert "connection string" in answer["error"]


# ── The probes' SQL binds its values instead of writing them into the statement ──

AWKWARD = "The bidder's offer ended in a backslash \\ and a quote ' here."


def test_passages_go_into_the_merge_as_bound_parameters():
    passages = [("p1", AWKWARD, [0.5, 0.25]), ("p2", "Plain text.", [0.0, 1.0])]
    statement, parameters = live.merge_passages("workspace.strata_dayone.passages", passages)
    assert AWKWARD not in statement and "0.25" not in statement and "p1" not in statement
    assert "IDENTIFIER(:table)" in statement
    assert parameters["table"] == "workspace.strata_dayone.passages"
    assert parameters["text0"] == AWKWARD and parameters["id1"] == "p2"
    assert json.loads(parameters["vec0"]) == [0.5, 0.25]
    assert all(f":{name}" in statement for name in parameters)


def test_the_passage_table_is_named_by_a_bound_identifier():
    statement, parameters = live.create_passage_table("workspace.strata_dayone.passages")
    assert "IDENTIFIER(:table)" in statement and "strata_dayone" not in statement
    assert parameters == {"table": "workspace.strata_dayone.passages"}


def test_the_parse_statements_bind_the_file_path():
    for statement in (live.PARSE_SQL, live.READABLE_SQL):
        assert "READ_FILES(:path" in statement and "{" not in statement


def test_a_name_from_dayone_toml_that_is_not_a_plain_name_is_refused():
    assert live.setting_name("workspace.strata_dayone", 2) == "workspace.strata_dayone"
    for bad in ("workspace.strata_dayone; SELECT 1", "workspace.default.files", "workspace.`odd`"):
        with pytest.raises(ProbeError):
            live.setting_name(bad, 2)
    with pytest.raises(ProbeError, match="is not a name of two plain parts, such as workspace.strata_dayone."):
        live.setting_name("workspace", 2)
    with pytest.raises(ProbeError, match="is not a name of three plain parts, such as workspace.strata_dayone.files."):
        live.setting_name("workspace.files", 3)


# ── The four copies of fetch_status stay the same ──

class SameShape(ast.NodeTransformer):
    """Undo the two allowed differences: live.py names its user agent, and the Azure copy adds headers."""

    def visit_Name(self, node):
        return ast.Constant(live.USER_AGENT) if node.id == "USER_AGENT" else node

    def visit_Dict(self, node):
        self.generic_visit(node)
        kept = [(key, value) for key, value in zip(node.keys, node.values) if key is not None]
        return ast.Dict(keys=[key for key, _ in kept], values=[value for _, value in kept])


def fetch_status_shape(path):
    tree = ast.parse(path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "fetch_status")
    body = function.body
    if ast.get_docstring(function):
        body = body[1:]
    arguments = [arg.arg for arg in function.args.args if arg.arg != "headers"]
    return arguments, [ast.dump(SameShape().visit(statement)) for statement in body]


def test_the_four_copies_of_fetch_status_match():
    """The workspace copies must stand alone, so this keeps them the same. Timeout defaults may differ."""
    copies = [REPO / "ops" / "dayone" / name for name in
              ("live.py", "workspace/reach_hosts.py", "workspace/azure_from_job.py", "workspace/probe_app/app.py")]
    first = fetch_status_shape(copies[0])
    for copy in copies[1:]:
        assert fetch_status_shape(copy) == first, copy
