"""The app's deploy command: one command builds the web app, uploads the app with its lean
requirements, gives it its resources and grants, deploys it and prints its address.

A fake workspace stands in for Databricks. docs/workspace-catchup.md runs the real deploy.
"""

import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "app"))

import deploy_app  # noqa: E402

PROBE = "Strata day-one probe app"
PRINCIPAL = "6f1c2d3e-4b5a-4c6d-8e7f-90a1b2c3d4e5"
ENV = {"DATABRICKS_HOST": "https://dbc-1.cloud.databricks.com", "DATABRICKS_TOKEN": "not-a-real-key",
       "DATABRICKS_WAREHOUSE_ID": "wh-1"}
# The Foundry agent's four keys (src/strata/agent/runner.py), which the app reads from secret resources.
FOUNDRY = {"FOUNDRY_PROJECT_ENDPOINT": "https://wb-strata.services.ai.azure.com/api/projects/Strata",
           "FOUNDRY_TENANT_ID": "tenant-0001", "FOUNDRY_CLIENT_ID": "client-0001",
           "FOUNDRY_CLIENT_SECRET": "not-a-real-key"}


class FakeWorkspace:
    def __init__(self, app=None):
        self.apps = {} if app is None else {"strata": dict(app)}
        self.uploaded, self.deployed, self.configured, self.statements, self.started = {}, [], [], [], []
        self.secrets = {}
        self.databases = []

    def app_state_database(self, instance):
        self.databases.append(instance)

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

    def put_secret(self, scope, key, value):
        self.secrets[(scope, key)] = value


def built(dist):
    def build():
        (dist / "assets").mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<!doctype html><title>Strata</title>")
        (dist / "assets" / "app-1a2b.js").write_text("console.log('Strata')")
        return 0, ""
    return build


def deploy(workspace, tmp_path, capsys, build=None, env=None):
    code = deploy_app.deploy(workspace, env or ENV, build_web=build or built(tmp_path / "dist"), dist=tmp_path / "dist")
    return code, capsys.readouterr().out


def test_one_command_uploads_the_app_with_its_lean_requirements_deploys_it_and_prints_its_address(tmp_path, capsys):
    workspace = FakeWorkspace()

    code, out = deploy(workspace, tmp_path, capsys, env=ENV | FOUNDRY)

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
        # App state lives in Lakebase (ADR 0005): the database resource sets PGHOST, PGUSER and the rest for the
        # server, and lets the app's own principal make its tables there.
        {"name": "app-state", "database": {"instance_name": "strata-state", "database_name": "databricks_postgres",
                                           "permission": "CAN_CONNECT_AND_CREATE"}},
    ]
    assert scopes == ["sql"]
    assert workspace.databases == ["strata-state"]


def test_without_lakebase_the_app_deploys_with_no_app_state_and_says_so(tmp_path, capsys):
    """A workspace that cannot make or start the Lakebase instance still gets the app; planning a package
    then says there is no data service."""
    class NoLakebase(FakeWorkspace):
        def app_state_database(self, instance):
            raise RuntimeError("Lakebase is not enabled in this workspace")

    workspace = NoLakebase()

    code, out = deploy(workspace, tmp_path, capsys)

    assert code == 0
    [(_, _, resources, _)] = workspace.configured
    assert [resource["name"] for resource in resources] == ["sql-warehouse", "appinsights"]
    assert "Lakebase is not enabled in this workspace" in out and "no packages" in out


def test_the_app_gets_the_foundry_agent_s_four_keys_as_secrets_when_the_env_file_has_them(tmp_path, capsys):
    """Without the four keys the deployed /api/ask says there is no agent (ticket 13's verify)."""
    workspace = FakeWorkspace()

    code, _ = deploy(workspace, tmp_path, capsys, env=ENV | FOUNDRY)

    assert code == 0
    assert workspace.secrets == {("strata", key): value for key, value in FOUNDRY.items()}
    [(_, _, resources, _)] = workspace.configured
    assert resources[3:] == [
        {"name": name, "secret": {"scope": "strata", "key": key, "permission": "READ"}}
        for name, key in (("foundry-endpoint", "FOUNDRY_PROJECT_ENDPOINT"), ("foundry-tenant", "FOUNDRY_TENANT_ID"),
                          ("foundry-client-id", "FOUNDRY_CLIENT_ID"), ("foundry-client-secret", "FOUNDRY_CLIENT_SECRET"))]
    started = yaml.safe_load(workspace.uploaded["files"]["app.yaml"])
    assert {entry["name"]: entry.get("valueFrom") for entry in started["env"] if entry["name"].startswith("FOUNDRY_")} == {
        "FOUNDRY_PROJECT_ENDPOINT": "foundry-endpoint", "FOUNDRY_TENANT_ID": "foundry-tenant",
        "FOUNDRY_CLIENT_ID": "foundry-client-id", "FOUNDRY_CLIENT_SECRET": "foundry-client-secret"}


def test_the_deploy_says_it_saved_the_foundry_keys_only_after_saving_them(tmp_path, capsys):
    class Refusing(FakeWorkspace):
        def put_secret(self, scope, key, value):
            raise RuntimeError("the secret scope refused the write")

    with pytest.raises(RuntimeError):
        deploy(Refusing(), tmp_path, capsys, env=ENV | FOUNDRY)

    assert "I saved the Foundry agent's four keys" not in capsys.readouterr().out


def test_without_the_foundry_keys_the_app_deploys_with_no_agent_and_says_so(tmp_path, capsys):
    workspace = FakeWorkspace()
    env = ENV | {key: value for key, value in FOUNDRY.items() if key != "FOUNDRY_CLIENT_SECRET"}

    code, out = deploy(workspace, tmp_path, capsys, env=env)

    assert code == 0
    assert workspace.secrets == {}
    [(_, _, resources, _)] = workspace.configured
    assert [resource["name"] for resource in resources] == ["sql-warehouse", "appinsights", "app-state"]
    started = yaml.safe_load(workspace.uploaded["files"]["app.yaml"])
    assert [entry["name"] for entry in started["env"] if entry["name"].startswith("FOUNDRY_")] == []
    assert started["command"] == ["python", "-m", "strata.server"]
    assert "FOUNDRY_CLIENT_SECRET" in out and "there is no agent" in out


def test_the_app_s_own_principal_may_write_usage_events_agent_runs_opened_sources_drafts_and_supplier_decisions_and_nothing_more(tmp_path, capsys):
    workspace = FakeWorkspace()

    deploy(workspace, tmp_path, capsys)

    assert workspace.statements == [
        f"GRANT USE CATALOG ON CATALOG strata TO `{PRINCIPAL}`",
        f"GRANT USE SCHEMA ON SCHEMA strata.ops TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.usage_events TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.agent_runs TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.evidence_opened TO `{PRINCIPAL}`",
        # Ticket 35's drafts, their states, their exports and the exported files.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.drafts TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.draft_states TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.draft_exports TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.draft_files TO `{PRINCIPAL}`",
        f"GRANT SELECT ON TABLE strata.ops.supplier_pairs TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.supplier_review_decisions TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.supplier_pair_labels TO `{PRINCIPAL}`",
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
