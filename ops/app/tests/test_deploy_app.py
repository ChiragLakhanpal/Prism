"""The app's deploy command: one command builds the web app, uploads the app with its lean
requirements, gives it its resources and grants, deploys it and prints its address.

A fake workspace stands in for Databricks. docs/workspace-catchup.md runs the real deploy.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "app"))

import deploy_app  # noqa: E402

PROBE = "Strata day-one probe app"
PRINCIPAL = "6f1c2d3e-4b5a-4c6d-8e7f-90a1b2c3d4e5"
ENV = {"DATABRICKS_HOST": "https://dbc-1.cloud.databricks.com", "DATABRICKS_TOKEN": "not-a-real-key",
       "DATABRICKS_WAREHOUSE_ID": "wh-1"}


class FakeWorkspace:
    def __init__(self, app=None):
        self.apps = {} if app is None else {"strata": dict(app)}
        self.uploaded, self.deployed, self.configured, self.statements, self.started = {}, [], [], [], []

    def me(self):
        return "owner@example.org"

    def app(self, name):
        return self.apps.get(name)

    def create_app(self, name, description):
        self.apps[name] = {"description": description, "source": None, "url": None, "principal": PRINCIPAL,
                           "running": True}

    def configure_app(self, name, description, resources, scopes):
        self.configured.append((name, description, resources, scopes))
        self.apps[name]["description"] = description

    def start(self, name):
        self.started.append(name)
        self.apps[name]["running"] = True

    def upload(self, folder, files):
        self.uploaded = {"folder": folder, "files": files}

    def deploy(self, name, folder):
        self.deployed.append((name, folder))
        self.apps[name] |= {"source": folder, "url": "https://strata-1.aws.databricksapps.com"}
        return self.apps[name]["url"]

    def run_sql(self, statement):
        self.statements.append(statement)


def built(dist):
    def build():
        (dist / "assets").mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<!doctype html><title>Strata</title>")
        (dist / "assets" / "app-1a2b.js").write_text("console.log('Strata')")
        return 0, ""
    return build


def deploy(workspace, tmp_path, capsys, build=None):
    code = deploy_app.deploy(workspace, ENV, build_web=build or built(tmp_path / "dist"), dist=tmp_path / "dist")
    return code, capsys.readouterr().out


def test_one_command_uploads_the_app_with_its_lean_requirements_deploys_it_and_prints_its_address(tmp_path, capsys):
    workspace = FakeWorkspace()

    code, out = deploy(workspace, tmp_path, capsys)

    assert code == 0
    files = workspace.uploaded["files"]
    assert workspace.uploaded["folder"] == "/Workspace/Users/owner@example.org/strata-app"
    assert files["app.yaml"] == (REPO / "ops" / "app" / "app.yaml").read_bytes()
    assert files["requirements.txt"] == (REPO / "ops" / "app" / "requirements.txt").read_bytes()
    assert files["web/dist/index.html"] == b"<!doctype html><title>Strata</title>"
    assert "src/strata/server/app.py" in files and "config/thresholds.toml" in files
    assert not [name for name in files if "__pycache__" in name or name.startswith(("tests/", "data/", "web/src/"))]
    assert workspace.deployed == [("strata", "/Workspace/Users/owner@example.org/strata-app")]
    assert out.rstrip().splitlines()[-1] == "Strata is running at https://strata-1.aws.databricksapps.com"


def test_the_app_gets_the_warehouse_the_connection_string_and_each_viewer_s_sql_token(tmp_path, capsys):
    workspace = FakeWorkspace()

    deploy(workspace, tmp_path, capsys)

    [(name, description, resources, scopes)] = workspace.configured
    assert (name, description) == ("strata", "Strata, procurement intelligence on World Bank open data")
    assert resources == [
        {"name": "sql-warehouse", "sql_warehouse": {"id": "wh-1", "permission": "CAN_USE"}},
        {"name": "appinsights", "secret": {"scope": "strata", "key": "APPLICATIONINSIGHTS_CONNECTION_STRING",
                                           "permission": "READ"}},
    ]
    assert scopes == ["sql"]


def test_the_app_s_own_principal_may_write_usage_events_and_nothing_more(tmp_path, capsys):
    workspace = FakeWorkspace()

    deploy(workspace, tmp_path, capsys)

    assert workspace.statements == [
        f"GRANT USE CATALOG ON CATALOG strata TO `{PRINCIPAL}`",
        f"GRANT USE SCHEMA ON SCHEMA strata.ops TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.usage_events TO `{PRINCIPAL}`",
    ]


def test_the_deploy_replaces_the_day_one_probe_app_and_starts_a_stopped_app(tmp_path, capsys):
    workspace = FakeWorkspace(app={"description": PROBE, "source": "/Workspace/Users/owner@example.org/strata-dayone/probe_app",
                                   "url": "https://strata-1.aws.databricksapps.com", "principal": PRINCIPAL,
                                   "running": False})

    code, out = deploy(workspace, tmp_path, capsys)

    assert code == 0
    assert workspace.started == ["strata"]
    assert workspace.apps["strata"]["source"] == "/Workspace/Users/owner@example.org/strata-app"
    assert "Strata is running at" in out


def test_the_deploy_leaves_an_app_someone_else_made_alone(tmp_path, capsys):
    workspace = FakeWorkspace(app={"description": "fairshare", "source": "/Workspace/Users/someone/fairshare",
                                   "url": "https://fairshare-1.aws.databricksapps.com", "principal": PRINCIPAL,
                                   "running": True})

    code, out = deploy(workspace, tmp_path, capsys)

    assert code == 1
    assert "left it alone" in out
    assert workspace.deployed == [] and workspace.uploaded == {} and workspace.statements == []


def test_a_web_app_that_does_not_build_stops_the_deploy_before_the_workspace(tmp_path, capsys):
    workspace = FakeWorkspace()

    code, out = deploy(workspace, tmp_path, capsys, build=lambda: (1, "error TS2304: Cannot find name 'Strata'."))

    assert code == 1
    assert "TS2304" in out
    assert workspace.apps == {} and workspace.uploaded == {}


def test_the_command_needs_the_workspace_keys_from_the_env_file(tmp_path, capsys):
    env = tmp_path / "strata.env"
    env.write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\n")

    code = deploy_app.main(["--env-file", str(env)], workspace=FakeWorkspace())

    assert code == 2
    assert "DATABRICKS_WAREHOUSE_ID" in capsys.readouterr().err


def test_the_command_s_help_says_how_to_run_it_and_to_run_it_again_after_a_bundle_deploy(capsys):
    with pytest.raises(SystemExit) as stopped:
        deploy_app.main(["--help"])

    out = " ".join(capsys.readouterr().out.split())
    assert stopped.value.code == 0
    assert "uv run --script ops/app/deploy_app.py --env-file .env" in out
    assert "Run it again after every bundle deploy" in out
