"""What the deploy uploads, started as the Databricks App starts it.

The App installs ops/app/requirements.txt and runs app.yaml's command in the uploaded folder.
These tests check, on this computer, that the lean requirements pin what uv.lock pins and leave
out the agent-framework metapackage (docs/PLAN.md section 12), that the server needs no other
package to start, and that the uploaded folder starts with app.yaml's settings and serves the web
app. The deploy to the workspace itself is a workspace step.
"""

import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "app"))

import deploy_app  # noqa: E402

APP = REPO / "ops" / "app"
LISTENING = re.compile(r"http://[\d.]+:(\d+)")


def normal(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def requirements():
    pins = {}
    for line in (APP / "requirements.txt").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, equals, version = line.partition("==")
            assert equals, f"{line!r} does not pin a version"
            pins[normal(name)] = version.strip()
    return pins


def locked():
    packages = tomllib.loads((REPO / "uv.lock").read_text())["package"]
    return {normal(p["name"]): p for p in packages}


def closure(names, lock):
    """The packages these names install, by uv.lock's dependency lists."""
    seen, todo = set(), [name for name in names if name in lock]
    while todo:
        name = todo.pop()
        if name not in seen:
            seen.add(name)
            todo += [normal(dep["name"]) for dep in lock[name].get("dependencies", [])]
    return seen


def test_the_lean_requirements_pin_each_package_at_its_uv_lock_version_and_leave_out_the_agent_framework():
    pins, lock = requirements(), locked()

    assert not [name for name in pins if name.startswith("agent-framework")]
    assert {name: version for name, version in pins.items() if name in lock} == {
        name: lock[name]["version"] for name in pins if name in lock}
    # The only pin uv.lock does not hold is the tracing package, which the app imports only with a
    # connection string, at the version the day-one probe app sends its trace with.
    assert [name for name in pins if name not in lock] == ["azure-monitor-opentelemetry"]
    probe = (REPO / "ops" / "dayone" / "workspace" / "probe_app" / "requirements.txt").read_text()
    assert f"azure-monitor-opentelemetry=={pins['azure-monitor-opentelemetry']}" in probe


BLOCKER = """
import importlib.metadata, json, re, sys
allowed = set(json.loads(sys.argv[1]))
owners = importlib.metadata.packages_distributions()

class OnlyTheLeanRequirements:
    def find_spec(self, name, path=None, target=None):
        top = name.split(".")[0]
        if top in sys.stdlib_module_names or top.startswith("_") or top == "strata":
            return None
        found = {re.sub(r"[-_.]+", "-", d).lower() for d in owners.get(top, [])}
        if found and not found & allowed:
            raise ImportError(f"{top} comes from {sorted(found)}, which the lean requirements do not install")
        return None

sys.meta_path.insert(0, OnlyTheLeanRequirements())
import strata.server.__main__
from strata.server.settings import app_from_env
app_from_env({"STRATA_WEB_DIST": sys.argv[2], "STRATA_LOCAL_DB": sys.argv[2] + "/none.duckdb"})
print("started")
"""


def test_the_server_starts_with_only_the_packages_the_lean_requirements_install(tmp_path):
    allowed = closure(requirements(), locked())

    done = subprocess.run([sys.executable, "-c", BLOCKER, json.dumps(sorted(allowed)), str(tmp_path)],
                          capture_output=True, text=True, timeout=60)

    assert done.returncode == 0, done.stderr[-2000:]
    assert done.stdout.strip() == "started"


@contextmanager
def started(folder, env):
    process = subprocess.Popen([sys.executable, "-m", "strata.server"], cwd=folder, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        line = process.stdout.readline()
        match = LISTENING.search(line)
        assert match, f"the server did not say where it listens: {line!r}"
        yield f"http://127.0.0.1:{match.group(1)}"
    finally:
        process.terminate()
        process.wait(timeout=10)


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def test_the_uploaded_folder_starts_with_app_yaml_s_settings_and_serves_the_web_app(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Strata</title>")
    folder = tmp_path / "strata-app"
    for name, content in deploy_app.package(dist).items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(content)
    settings = yaml.safe_load((folder / "app.yaml").read_text())
    assert settings["command"] == ["python", "-m", "strata.server"]
    # The platform sets the port and fills the resources; this computer picks a free port.
    env = {**os.environ, **{item["name"]: item["value"] for item in settings["env"] if "value" in item},
           "DATABRICKS_APP_PORT": "0", "STRATA_SERVER_PORT": ""}

    with started(folder, env) as address:
        health, page, stamp = fetch(f"{address}/api/health"), fetch(f"{address}/projects/P130164"), \
            fetch(f"{address}/api/freshness")

    assert health == (200, '{"status":"ok"}')
    assert page == (200, "<!doctype html><title>Strata</title>")
    # No viewer was forwarded, so the stamp says so instead of reading anything.
    assert stamp == (401, '{"code":"no_identity"}')
