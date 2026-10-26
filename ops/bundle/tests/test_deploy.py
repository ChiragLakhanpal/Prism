"""The deploy command: one command creates the catalog, its schemas, the volume, the tables, the
grants, the nightly job and the dashboard, and a second run reports no changes. fairshare's catalog
lists the same before and after.

The fake workspace stands in for Databricks: its bundle deploy creates what bundle/catalog.yml
and bundle/nightly.yml declare, and its SQL warehouse is DuckDB, so the real table definitions
run. The workspace step in docs/workspace-catchup.md runs the real thing.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "bundle"))

import bundle_live  # noqa: E402
import deploy  # noqa: E402

from strata.lakehouse import bundle, catalog, nightly  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402

FAIRSHARE = {"catalog": {"name": "fairshare", "comment": ""}, "schemas": {"gold": ""}, "volumes": {},
             "tables": {"gold.flights": ["flight_id STRING", "public_from DATE"]},
             "grants": {"fairshare": {"account users": ["USE_CATALOG"]}}}


class FakeWorkspace:
    """A workspace that holds fairshare's catalog and, once the bundle deploys, Strata's."""

    def __init__(self, deploy_fails=False, touch_fairshare=False):
        self.deploys = 0
        self.deploy_fails, self.touch_fairshare = deploy_fails, touch_fairshare
        self.deployed = None
        self.duckdb = DuckDBEngine.open()
        self.fairshare = dict(FAIRSHARE)

    def deploy_bundle(self):
        self.deploys += 1
        if self.deploy_fails:
            return 1, "Error: cannot create catalog: PERMISSION_DENIED"
        declared = catalog.declared()
        for schema in declared.schemas:
            self.duckdb.run(f"CREATE SCHEMA IF NOT EXISTS strata.{schema}")
        self.deployed = declared
        if self.touch_fairshare:
            self.fairshare = {**self.fairshare, "tables": {}}
        return 0, "Deployment complete!"

    def engine(self):
        return self.duckdb

    def listing(self, name):
        if name == "fairshare":
            return self.fairshare
        if self.deployed is None:
            return None
        tables = self.duckdb.run(
            "SELECT table_schema, table_name, column_name, data_type FROM system.information_schema.columns "
            "WHERE table_catalog = 'strata' ORDER BY table_schema, table_name, ordinal_position").as_text()
        listed = {}
        for schema, table, column, kind in tables:
            listed.setdefault(f"{schema}.{table}", []).append(f"{column} {kind}")
        return {"catalog": {"name": "strata", "comment": ""},
                "schemas": {schema: "" for schema in self.deployed.schemas},
                "volumes": {volume: "MANAGED" for volume in self.deployed.volumes},
                "tables": listed,
                "grants": {name: {who: list(what) for who, what in grants.items()}
                           for name, grants in self.deployed.grants.items()}}

    def job(self, name):
        return {"name": name, "tasks": [task.key for task in nightly.job_tasks()]} if self.deployed else None

    def dashboard(self, name):
        """The dashboard the bundle declares, with the pages of the file it deploys."""
        if not self.deployed:
            return None
        import json

        declared = bundle.load().resources("dashboards")["strata_dashboard"]
        pages = json.loads((REPO / "bundle" / declared["file_path"]).read_text())["pages"]
        return {"name": name, "pages": [page["displayName"] for page in pages]}


def deploy_into(workspace, capsys):
    code = deploy.deploy(workspace)
    return code, capsys.readouterr().out


def test_the_first_deploy_creates_the_catalog_its_schemas_the_volume_the_tables_and_the_job(capsys):
    workspace = FakeWorkspace()

    code, out = deploy_into(workspace, capsys)

    assert code == 0
    assert workspace.deploys == 1
    for line in ("The catalog strata is new.",
                 "The schema strata.bronze is new.", "The schema strata.silver is new.",
                 "The schema strata.gold is new.", "The schema strata.ops is new.",
                 "The volume strata.bronze.files is new.",
                 "The table strata.ops.pipeline_runs is new.",
                 "The grants on strata are new.",
                 "The job strata nightly is new.",
                 "The dashboard Strata operations is new."):
        assert line in out
    assert ("fairshare's catalog lists the same before and after the deploy: "
            "one schema, one table and no volumes.") in out


class Warehouse:
    """The fake workspace's DuckDB as the SQL warehouse: it runs every statement but the metric views, which only
    Databricks has, and keeps those."""

    name = "databricks"

    def __init__(self, duckdb):
        self.duckdb, self.metric_views = duckdb, []

    def run(self, sql, params=None):
        if "WITH METRICS" in sql:
            self.metric_views.append(sql.split("\n")[0])
            return self.duckdb.run("SELECT 1")
        return self.duckdb.run(sql, params)

    def insert_rows(self, *args, **kwargs):
        return self.duckdb.insert_rows(*args, **kwargs)


def test_the_deploy_creates_the_metric_views_genie_reads_after_the_tables(capsys):
    workspace = FakeWorkspace()
    warehouse = Warehouse(workspace.duckdb)
    workspace.engine = lambda: warehouse

    code, out = deploy_into(workspace, capsys)

    assert code == 0
    assert warehouse.metric_views == ["CREATE OR REPLACE VIEW strata.gold.contract_metrics",
                                      "CREATE OR REPLACE VIEW strata.gold.package_metrics"]
    assert ("The metric views Genie reads exist now: strata.gold.contract_metrics, strata.gold.package_metrics."
            in out)


def test_a_second_deploy_reports_no_changes(capsys):
    workspace = FakeWorkspace()
    deploy_into(workspace, capsys)

    code, out = deploy_into(workspace, capsys)

    assert code == 0
    assert "No changes." in out
    assert "is new" not in out


def test_the_plan_lists_from_the_repo_alone_everything_a_first_deploy_reports_as_new(capsys):
    """The demo-ready command's dry run (ops/demo/ready.py --fresh-workspace) prints this plan, so it cannot drift
    from what the deploy makes. The plan also holds what the fake cannot list: the metric views and every job."""
    code, out = deploy_into(FakeWorkspace(), capsys)
    new = {line.strip() for line in out.splitlines() if line.strip().endswith((" is new.", " are new."))}
    planned = set(deploy.changes({}, dict.fromkeys(deploy.plan(), True)))

    assert code == 0 and new
    assert new <= planned
    assert {"The table strata.gold.contract_metrics is new.", "The job strata lesson cross-check is new.",
            "The job strata retrieval weekly is new."} <= planned


def test_a_deploy_that_changes_fairshare_s_catalog_fails_and_says_what_changed(capsys):
    code, out = deploy_into(FakeWorkspace(touch_fairshare=True), capsys)

    assert code == 1
    assert "fairshare's catalog changed during the deploy" in out
    assert "The table fairshare.gold.flights is gone." in out


def test_a_failed_bundle_deploy_stops_before_the_tables_and_shows_why(capsys):
    workspace = FakeWorkspace(deploy_fails=True)

    code, out = deploy_into(workspace, capsys)

    assert code == 1
    assert "PERMISSION_DENIED" in out
    assert workspace.duckdb.run("SELECT count(*) AS n FROM system.information_schema.tables "
                                "WHERE table_catalog = 'strata'").as_text() == [("0",)]


def test_the_command_needs_the_workspace_keys_from_the_env_file(tmp_path, capsys):
    env = tmp_path / "strata.env"
    env.write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\n")

    code = deploy.main(["--env-file", str(env)], workspace=FakeWorkspace())

    assert code == 2
    assert "DATABRICKS_WAREHOUSE_ID" in capsys.readouterr().err


def test_the_command_runs_with_a_complete_env_file(tmp_path, capsys):
    env = tmp_path / "strata.env"
    env.write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\nDATABRICKS_TOKEN='not-a-real-key'\n"
                   "DATABRICKS_WAREHOUSE_ID='wh-1'\n")

    assert deploy.main(["--env-file", str(env)], workspace=FakeWorkspace()) == 0
    assert "The catalog strata is new." in capsys.readouterr().out


SHELL = {"PATH": "/usr/bin", "DATABRICKS_CONFIG_PROFILE": "someone-else"}
HOST = "https://dbc-1.cloud.databricks.com"


def test_the_cli_gets_the_token_alone_when_the_env_file_has_both_ways_to_sign_in():
    env = {"DATABRICKS_HOST": HOST, "DATABRICKS_TOKEN": "not-a-real-key",
           "DATABRICKS_CLIENT_ID": "sp-client", "DATABRICKS_CLIENT_SECRET": "not-a-real-secret"}

    assert bundle_live.cli_env(env, SHELL) == {"PATH": "/usr/bin", "DATABRICKS_HOST": HOST,
                                               "DATABRICKS_AUTH_TYPE": "pat", "DATABRICKS_TOKEN": "not-a-real-key"}


def test_the_cli_gets_the_service_principal_when_the_env_file_has_no_token():
    env = {"DATABRICKS_HOST": HOST, "DATABRICKS_TOKEN": "",
           "DATABRICKS_CLIENT_ID": "sp-client", "DATABRICKS_CLIENT_SECRET": "not-a-real-secret"}

    assert bundle_live.cli_env(env, SHELL) == {"PATH": "/usr/bin", "DATABRICKS_HOST": HOST,
                                               "DATABRICKS_AUTH_TYPE": "oauth-m2m", "DATABRICKS_CLIENT_ID": "sp-client",
                                               "DATABRICKS_CLIENT_SECRET": "not-a-real-secret"}


def test_the_deploy_passes_every_bundle_variable_the_job_s_tasks_name_that_has_no_default():
    """The nightly job's sync_index task syncs the AI Search index the env file names, which is no secret and so
    travels as a bundle variable, as the SQL warehouse does (review B4). Without the env file's value, the deploy
    passes the name the wizard gives it (ops/dayone/dayone.toml, names.ai_search_endpoint)."""
    import re

    env = {"DATABRICKS_WAREHOUSE_ID": "wh-1", "AI_SEARCH_ENDPOINT": "my-search"}
    passed = dict(part.split("=", 1) for part in bundle_live.bundle_vars(env)[1::2])
    variables = bundle.load().data["variables"]
    named = {name for task in nightly.job_tasks() for part in task.parameters
             for name in re.findall(r"\$\{var\.(\w+)\}", part)}

    assert bundle_live.bundle_vars(env)[::2] == ["--var"] * len(passed)
    assert passed == {"warehouse_id": "wh-1", "ai_search_endpoint": "my-search"}
    assert "ai_search_endpoint" in named
    assert {name for name in named if "default" not in variables[name]} <= set(passed)
    assert dict(part.split("=", 1) for part in bundle_live.bundle_vars({"DATABRICKS_WAREHOUSE_ID": "wh-1"})[1::2])[
        "ai_search_endpoint"] == "strata-search"


@pytest.mark.parametrize("name", ["deploy.py", "check.py"])
def test_each_command_says_how_to_run_it_from_the_main_checkout(name):
    text = (REPO / "ops" / "bundle" / name).read_text()

    assert f"uv run --script ops/bundle/{name}" in text
    assert text.startswith("# /// script")
