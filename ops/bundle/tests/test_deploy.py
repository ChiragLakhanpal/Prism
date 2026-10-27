"""The deploy command: one command creates the catalog, its schemas, the volume, the tables, the
grants, the nightly job and the dashboard, and a second run reports no changes. fairshare's catalog
lists the same before and after.

The fake workspace stands in for Databricks: its bundle deploy creates what bundle/catalog.yml
and bundle/nightly.yml declare, and its SQL warehouse is DuckDB, so the real table definitions
run. The workspace step in docs/workspace-catchup.md runs the real thing.
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "bundle"))
sys.path.insert(0, str(REPO / "ops" / "app"))

import bundle_live  # noqa: E402
import deploy  # noqa: E402
import deploy_app  # noqa: E402

from strata.lakehouse import bundle, catalog, nightly  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402

FAIRSHARE = {"catalog": {"name": "fairshare", "comment": ""}, "schemas": {"gold": ""}, "volumes": {},
             "tables": {"gold.flights": ["flight_id STRING", "public_from DATE"]},
             "grants": {"fairshare": {"account users": ["USE_CATALOG"]}}}
# The passage index's id on the paid workspace, as its two tables carried it (docs/workspace-catchup.md, ticket 85).
INDEX_ID = "cd8058ce_42aa_4722_ac9a_3ee310032e31"
INDEX_OBJECTS = ("strata.gold.passage_index", f"strata.gold.event_log_{INDEX_ID}",
                 f"strata.gold.__{INDEX_ID}___online_index_view")


class FakeWorkspace:
    """A workspace that holds fairshare's catalog and, once the bundle deploys, Strata's. With app, it also holds
    the app that ops/dayone/dayone.toml names, as apps get returns it."""

    def __init__(self, deploy_fails=False, touch_fairshare=False, app=None):
        self.deploys = 0
        self.deploy_fails, self.touch_fairshare = deploy_fails, touch_fairshare
        self.deployed = None
        self.duckdb = DuckDBEngine.open()
        self.fairshare = dict(FAIRSHARE)
        self.apps = {"strata": app} if app else {}
        self.grants = {}  # securable -> principal -> privileges, as the workspace holds them now
        self.granted = []  # each grant the deploy wrote after the bundle's
        self.dashboards = {}  # display name -> the file the bundle wrote and when it wrote it
        self.edit = ""  # a change to every dashboard file, as a new commit of src/strata/dashboard makes one

    def deploy_bundle(self):
        self.deploys += 1
        if self.deploy_fails:
            return 1, "Error: cannot create catalog: PERMISSION_DENIED"
        declared = catalog.declared()
        for schema in declared.schemas:
            self.duckdb.run(f"CREATE SCHEMA IF NOT EXISTS strata.{schema}")
        self.deployed = declared
        # The bundle's grants replace every other grant on Strata's catalog, schemas and volume, the app's too.
        self.grants = {name: {who: list(what) for who, what in grants.items()}
                       for name, grants in declared.grants.items()}
        # The bundle rewrites a dashboard whose file changed, and the workspace stamps its update_time.
        for board in bundle.load().resources("dashboards").values():
            text = (REPO / "bundle" / board["file_path"]).read_text()
            if self.dashboards.get(board["display_name"], {}).get("text") != text + self.edit:
                self.dashboards[board["display_name"]] = {
                    "text": text + self.edit, "pages": [page["displayName"] for page in json.loads(text)["pages"]],
                    "update_time": f"2026-10-26T10:21:{self.deploys:02d}Z"}
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
                "grants": {name: {who: sorted(what) for who, what in grants.items()}
                           for name, grants in self.grants.items()}}

    def app(self, name):
        return self.apps.get(name)

    def grant(self, kind, name, principal, privileges):
        self.granted.append((kind, name, principal, tuple(privileges)))
        held = self.grants.setdefault(name, {}).setdefault(principal, [])
        held.extend(privilege for privilege in privileges if privilege not in held)

    def job(self, name):
        return {"name": name, "tasks": [task.key for task in nightly.job_tasks()]} if self.deployed else None

    def dashboard(self, name):
        """A dashboard the bundle deployed, with the pages of its file and when the bundle last wrote it."""
        if name not in self.dashboards:
            return None
        found = self.dashboards[name]
        return {"name": name, "pages": found["pages"], "update_time": found["update_time"]}


def sync_index(workspace, index_id=INDEX_ID):
    """The nightly's first sync_index, as it went on the paid workspace on October 27, 2026: the AI Search service
    made the index config/models.toml names and two tables beside it that carry the index's id, an event log and the
    view the index serves from, none with a public_from column (ticket 87). On Databricks the view has no columns at
    all; DuckDB needs one."""
    for name, columns in (("passage_index", "passage_id STRING, header STRING, text STRING"),
                          (f"event_log_{index_id}", "id STRING, timestamp TIMESTAMP, message STRING"),
                          (f"__{index_id}___online_index_view", "passage_id STRING")):
        workspace.duckdb.run(f"CREATE TABLE strata.gold.{name} ({columns})")


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
                 "The dashboard Strata operations is new.",
                 "The dashboard Strata operations (test) is new."):
        assert line in out
    assert ("fairshare's catalog lists the same before and after the deploy: "
            "one schema, one table and no volumes.") in out


APP_PRINCIPAL = "e796c089-0000-4000-8000-000000000079"


def strata_app(description=deploy_app.DESCRIPTION):
    """The app ops/app/deploy_app.py made, as apps get returns it: its description and its service principal's
    application id."""
    return {"description": description, "principal": APP_PRINCIPAL}


def test_with_an_app_the_deploy_gives_its_service_principal_back_use_catalog_and_use_schema(capsys):
    """The bundle's grants replace every other grant on strata and its schemas, so a bundle deploy used to take the
    app's USE CATALOG and USE SCHEMA away until the app was deployed again (ticket 79)."""
    workspace = FakeWorkspace(app=strata_app())
    deploy_into(workspace, capsys)

    code, out = deploy_into(workspace, capsys)
    grants = workspace.listing("strata")["grants"]

    assert code == 0
    assert grants["strata"] == {"account users": ["USE_CATALOG"], APP_PRINCIPAL: ["USE_CATALOG"]}
    assert grants["strata.ops"] == {"account users": ["SELECT", "USE_SCHEMA"], APP_PRINCIPAL: ["USE_SCHEMA"]}
    assert (f"   The bundle's grants replace every other grant on strata and its schemas, so I gave the app strata's "
            f"service principal {APP_PRINCIPAL} back USE CATALOG on strata and USE SCHEMA on strata.ops.\n") in out
    assert "No changes." in out


def test_with_no_app_the_grants_are_the_bundle_s_own_and_the_deploy_says_no_app_exists(capsys):
    workspace = FakeWorkspace()

    code, out = deploy_into(workspace, capsys)

    assert code == 0
    assert workspace.granted == []
    assert workspace.listing("strata")["grants"] == {
        "strata": {"account users": ["USE_CATALOG"]},
        **{f"strata.{schema}": {"account users": ["SELECT", "USE_SCHEMA"]}
           for schema in ("bronze", "silver", "gold", "ops")},
        "strata.bronze.files": {"account users": ["READ_VOLUME"]}}
    assert ("   I found no app named strata, so I granted nothing for it. Its deploy, ops/app/deploy_app.py, grants "
            "its service principal what it needs.\n") in out


def test_the_live_workspace_adds_the_app_s_privilege_and_removes_no_other_grant():
    """The live adapter answers every call the fake answers. Its grant is Unity Catalog's permissions update with
    one change that only adds, so the readers' grants the bundle just wrote stay."""
    calls = []
    live = object.__new__(bundle_live.LiveWorkspace)
    live.w = SimpleNamespace(api_client=SimpleNamespace(do=lambda method, path, body: calls.append((method, path, body))))

    for kind, name, privilege in deploy_app.ACCESS:
        live.grant(kind, name, APP_PRINCIPAL, [privilege])

    assert calls == [
        ("PATCH", "/api/2.1/unity-catalog/permissions/catalog/strata",
         {"changes": [{"principal": APP_PRINCIPAL, "add": ["USE_CATALOG"]}]}),
        ("PATCH", "/api/2.1/unity-catalog/permissions/schema/strata.ops",
         {"changes": [{"principal": APP_PRINCIPAL, "add": ["USE_SCHEMA"]}]})]
    called = {name for name in vars(FakeWorkspace) if not name.startswith("_")}
    assert called <= {name for name in vars(bundle_live.LiveWorkspace) if not name.startswith("_")}


@pytest.mark.parametrize("app, said", [
    ({"description": "Someone else's app", "principal": APP_PRINCIPAL},
     "The app strata is not Strata's: its description is \"Someone else's app\". I granted nothing for it."),
    ({"description": deploy_app.DESCRIPTION, "principal": None},
     "The app strata has no service principal yet, so I granted nothing for it.")])
def test_an_app_that_is_not_strata_s_or_has_no_service_principal_gets_no_grant(app, said, capsys):
    workspace = FakeWorkspace(app=app)

    code, out = deploy_into(workspace, capsys)

    assert code == 0
    assert workspace.granted == []
    assert said in out


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


def test_a_deploy_after_the_first_index_sync_creates_the_tables_and_says_what_changed(capsys):
    """On October 27, 2026 the deploy after the first sync_index stopped at the tables, naming the index service's
    three objects as tables without public_from, and never said what changed (ticket 87). The check leaves those
    three out, so the deploy creates the tables and prints its report."""
    workspace = FakeWorkspace()
    deploy_into(workspace, capsys)
    sync_index(workspace)

    code, out = deploy_into(workspace, capsys)

    assert code == 0
    assert "I could not create the tables" not in out
    assert "   Each of these exists now: strata.bronze." in out
    assert "3. What changed:\n   No changes.\n" in out
    assert set(INDEX_OBJECTS) <= {f"strata.{name}" for name in workspace.listing("strata")["tables"]}


@pytest.mark.parametrize("table", ["strata.gold.notes", "strata.gold.event_log_notes", f"strata.ops.event_log_{INDEX_ID}",
                                   f"strata.gold.__{INDEX_ID}___online_index_view_copy", "strata.gold.passage_index_v2"])
def test_after_the_index_sync_the_deploy_still_names_a_table_without_public_from(table, capsys):
    """The check leaves out the index's three objects and nothing else: a table with a name like theirs, in another
    schema or with another ending, is still named."""
    workspace = FakeWorkspace()
    deploy_into(workspace, capsys)
    sync_index(workspace)
    workspace.duckdb.run(f"CREATE TABLE {table} (id STRING)")

    code, out = deploy_into(workspace, capsys)

    assert code == 1
    assert (f"I could not create the tables. These tables have no public_from column of type DATE: {table}. Every "
            "table keeps the date each row became public (ADR 0002), so add a public_from DATE column.\n") in out


def test_a_deploy_that_rewrote_both_dashboards_names_each_one_as_changed(capsys):
    """On October 26, 2026 a deploy rewrote both dashboards with new tiles on the same pages, and the report named only
    the grants (ticket 79). The workspace stamps a rewritten dashboard's update_time, and the report reads it."""
    workspace = FakeWorkspace()
    deploy_into(workspace, capsys)
    workspace.edit = " "

    code, out = deploy_into(workspace, capsys)
    changed = out.split("What changed:\n")[1].split("\n")

    assert code == 0
    assert changed[:2] == ["   The dashboard Strata operations changed.", "   The dashboard Strata operations (test) changed."]
    assert "No changes." not in out


def test_the_live_listing_of_a_dashboard_holds_when_the_workspace_last_wrote_it():
    """The live listing held only the pages' names and the warehouse, which a rewrite on the same pages kept, so the
    report missed it. lakeview get's update_time moves with every write."""
    class Lakeview:
        def list(self):
            return [SimpleNamespace(display_name="Someone else's", dashboard_id="d0"),
                    SimpleNamespace(display_name="Strata operations", dashboard_id="d1")]

        def get(self, dashboard_id):
            assert dashboard_id == "d1"
            return SimpleNamespace(serialized_dashboard='{"pages": [{"displayName": "Data readiness"}]}',
                                   warehouse_id="wh-1", update_time="2026-10-26T10:21:52.000Z")

    live = object.__new__(bundle_live.LiveWorkspace)
    live.w = SimpleNamespace(lakeview=Lakeview())

    assert live.dashboard("Strata operations") == {"name": "Strata operations", "pages": ["Data readiness"],
                                                   "warehouse_id": "wh-1", "update_time": "2026-10-26T10:21:52.000Z"}


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

    assert bundle_live.cli_env(env, SHELL) == {"PATH": "/usr/bin", "DATABRICKS_HOST": HOST, "DATABRICKS_CONFIG_FILE": os.devnull,
                                               "DATABRICKS_AUTH_TYPE": "pat", "DATABRICKS_TOKEN": "not-a-real-key"}


def test_the_cli_gets_the_service_principal_when_the_env_file_has_no_token():
    env = {"DATABRICKS_HOST": HOST, "DATABRICKS_TOKEN": "",
           "DATABRICKS_CLIENT_ID": "sp-client", "DATABRICKS_CLIENT_SECRET": "not-a-real-secret"}

    assert bundle_live.cli_env(env, SHELL) == {"PATH": "/usr/bin", "DATABRICKS_HOST": HOST, "DATABRICKS_CONFIG_FILE": os.devnull,
                                               "DATABRICKS_AUTH_TYPE": "oauth-m2m", "DATABRICKS_CLIENT_ID": "sp-client",
                                               "DATABRICKS_CLIENT_SECRET": "not-a-real-secret"}


def test_the_cli_never_reads_the_config_file_s_default_profile():
    """The CLI's bundle commands take ~/.databrickscfg's default profile over the host and token in the environment,
    so a deploy meant for one workspace can land on another (October 26, 2026, ticket 82). The config file is pointed
    at nothing, and the shell's own profile choice never reaches the CLI."""
    env = {"DATABRICKS_HOST": HOST, "DATABRICKS_TOKEN": "not-a-real-key"}
    shell = SHELL | {"DATABRICKS_CONFIG_FILE": "/Users/someone/.databrickscfg", "HOME": "/Users/someone"}

    found = bundle_live.cli_env(env, shell)

    assert found["DATABRICKS_CONFIG_FILE"] == os.devnull
    assert "DATABRICKS_CONFIG_PROFILE" not in found
    assert found["HOME"] == "/Users/someone"


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
