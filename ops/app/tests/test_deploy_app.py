"""The app's deploy command: one command builds the web app, uploads the app with its lean
requirements, gives it its resources and grants, deploys it and prints its address.

A fake workspace stands in for Databricks. docs/workspace-catchup.md runs the real deploy.
"""

import datetime as dt
import sys
from pathlib import Path
from types import SimpleNamespace

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
# The judge of the verifier's check 4 (src/strata/agent/judge.py), on Azure OpenAI.
JUDGE = {"AZURE_OPENAI_ENDPOINT": "https://wb-strata.openai.azure.com/openai/deployments/gpt-5.4",
         "AZURE_OPENAI_API_KEY": "not-a-real-key"}


class FakeWorkspace:
    def __init__(self, app=None, secrets=None, compute=None, warehouse="RUNNING", warehouse_answer=None,
                 deployments=()):
        self.apps = {} if app is None else {"strata": dict(app)}
        self.uploaded, self.deployed, self.configured, self.statements, self.started = {}, [], [], [], []
        self.secrets = dict(secrets or {})  # the secret scope, by (scope, key)
        self.written = []  # each put_secret call's (scope, key)
        self.databases = []
        # Ticket 81: the App's compute as apps get gives it, when a test sets it, and the env file's SQL warehouse, which
        # answers a start with warehouse_answer when a test sets it.
        self.compute = compute
        self.warehouse = {"id": "wh-1", "state": warehouse, "message": ""}
        self.warehouse_answer, self.warehouse_starts = warehouse_answer, 0
        # The app's deployments, as apps list-deployments gives them. Each deploy registers one that succeeded, made at
        # the workspace's clock.
        self.registered = [dict(deployment) for deployment in deployments]
        self.clock = lambda: dt.datetime.now(dt.UTC)

    def deployments(self, name):
        return [dict(deployment) for deployment in self.registered]

    def app_compute(self, name):
        if name not in self.apps:
            return None
        if self.compute:
            return dict(self.compute)
        running = self.apps[name]["running"]
        return {"state": "ACTIVE" if running else "STOPPED",
                "message": "App compute is running." if running else "App compute is stopped."}

    def warehouse_state(self):
        return dict(self.warehouse)

    def start_warehouse(self):
        self.warehouse_starts += 1
        if self.warehouse_answer:
            raise RuntimeError(self.warehouse_answer)
        self.warehouse["state"] = "RUNNING"

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
        self.registered.append({"id": f"01f0b2deploy{len(self.registered):04d}", "state": "SUCCEEDED",
                                "message": "App started successfully", "created": self.clock()})
        return self.apps[name]["url"]

    def run_sql(self, statement):
        self.statements.append(statement)

    def put_secret(self, scope, key, value):
        self.written.append((scope, key))
        self.secrets[(scope, key)] = value

    def secret_keys(self, scope):
        """The scope's keys, never their values, as the live adapter lists them."""
        return [key for (named, key) in self.secrets if named == scope]


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

    code, out = deploy(workspace, tmp_path, capsys, env=ENV | FOUNDRY | JUDGE)

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
    assert "The app existed before this deploy." not in out  # a first deploy has no old sessions to warn about


def test_the_plan_names_from_the_repo_alone_what_a_first_deploy_makes(tmp_path, capsys):
    """The demo-ready command's dry run (ops/demo/ready.py --fresh-workspace) prints this plan, so it cannot drift
    from what the deploy makes."""
    workspace = FakeWorkspace()
    code, _ = deploy(workspace, tmp_path, capsys, env=ENV | FOUNDRY | JUDGE)
    planned = deploy_app.plan()

    def named(label):
        return {name for kind, name in planned if kind == label}

    [(name, description, resources, scopes)] = workspace.configured
    assert code == 0
    assert named("The app") == {f"{name} ({description})"}
    assert {resource["name"] for resource in resources} == named("The app resource")
    assert set(scopes) == named("The user authorization scope")
    assert {f"{scope}/{key}" for scope, key in workspace.secrets} == named("The secret")
    assert set(workspace.databases) == named("The Lakebase instance")
    assert {workspace.uploaded["folder"].replace("owner@example.org", "<you>")} == named("Its code")


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
    assert scopes == ["sql", "dashboards.genie"]
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


def test_the_app_gets_the_judge_s_two_keys_as_secrets_when_the_env_file_has_them(tmp_path, capsys):
    """Without them, every sentence the verifier's check 4 must judge is removed (ticket 24's review)."""
    workspace = FakeWorkspace()

    code, out = deploy(workspace, tmp_path, capsys, env=ENV | FOUNDRY | JUDGE)

    assert code == 0
    assert {key: value for (_, key), value in workspace.secrets.items() if key in JUDGE} == JUDGE
    [(_, _, resources, _)] = workspace.configured
    assert resources[-2:] == [
        {"name": name, "secret": {"scope": "strata", "key": key, "permission": "READ"}}
        for name, key in (("azure-openai-endpoint", "AZURE_OPENAI_ENDPOINT"), ("azure-openai-key", "AZURE_OPENAI_API_KEY"))]
    started = yaml.safe_load(workspace.uploaded["files"]["app.yaml"])
    assert {entry["name"]: entry.get("valueFrom") for entry in started["env"] if entry["name"].startswith("AZURE_")} == {
        "AZURE_OPENAI_ENDPOINT": "azure-openai-endpoint", "AZURE_OPENAI_API_KEY": "azure-openai-key"}
    assert "the model that judges sentences" in out


def test_without_the_judge_s_keys_the_app_deploys_with_no_judge_and_says_so(tmp_path, capsys):
    workspace = FakeWorkspace()

    code, out = deploy(workspace, tmp_path, capsys, env=ENV | FOUNDRY)

    assert code == 0
    assert [key for (_, key) in workspace.secrets if key in JUDGE] == []
    started = yaml.safe_load(workspace.uploaded["files"]["app.yaml"])
    assert [entry["name"] for entry in started["env"] if entry["name"].startswith("AZURE_")] == []
    assert "AZURE_OPENAI_ENDPOINT" in out and "removes every sentence" in out


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


def test_the_app_s_own_principal_may_write_usage_events_agent_runs_opened_sources_drafts_supplier_decisions_and_lesson_reviews_and_nothing_more(tmp_path, capsys):
    workspace = FakeWorkspace()

    deploy(workspace, tmp_path, capsys)

    assert [statement for statement in workspace.statements if statement.startswith("GRANT")] == [
        f"GRANT USE CATALOG ON CATALOG strata TO `{PRINCIPAL}`",
        f"GRANT USE SCHEMA ON SCHEMA strata.ops TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.usage_events TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.agent_runs TO `{PRINCIPAL}`",
        # Ticket 84: each run's tool calls, the tables they read and its removed sentences (ticket 45's lineage),
        # written beside the run row. Without them the paid workspace refused every run's lineage on October 26.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.tool_calls TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.tool_call_reads TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.answer_removals TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.evidence_opened TO `{PRINCIPAL}`",
        # Ticket 35's drafts, their states, their exports and the exported files.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.drafts TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.draft_states TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.draft_exports TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.draft_files TO `{PRINCIPAL}`",
        # Ticket 37: the projects each World Bank staff viewer follows.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.follows TO `{PRINCIPAL}`",
        # Ticket 23: the side of a disagreement each person kept, with their reason, for the evidence pack.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.disagreement_choices TO `{PRINCIPAL}`",
        # Ticket 36: the values people set on a draft's fields, and their latest values.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.draft_fields TO `{PRINCIPAL}`",
        # Ticket 44: each past range or time estimate the app showed in the World Bank staff view.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.exposures TO `{PRINCIPAL}`",
        # Ticket 38: an implementing agency team's uploads and their activities.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.uploads TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.upload_rows TO `{PRINCIPAL}`",
        # Ticket 39: each reader's visits to Lessons, and the choices on rows whose lesson changed.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.lesson_visits TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.draft_lesson_choices TO `{PRINCIPAL}`",
        # Ticket 41: each viewer's Start here choice, the examples the seed command set up and the example lesson
        # versions only their viewer sees.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.start_here_choices TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.seeded_examples TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.example_lesson_versions TO `{PRINCIPAL}`",
        # Ticket 42: the language of answers and drafts each viewer chose (found by ticket 84's test_app_grants.py).
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.viewer_settings TO `{PRINCIPAL}`",
        f"GRANT SELECT ON TABLE strata.ops.draft_fields_latest TO `{PRINCIPAL}`",
        f"GRANT SELECT ON TABLE strata.ops.supplier_pairs TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.supplier_review_decisions TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.supplier_pair_labels TO `{PRINCIPAL}`",
        # Ticket 29's lesson review record: the reviewers' acts, the queue, the versions, what each rests on
        # and the writer's notes. No reviewer group may write them outside the app.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.lesson_review_acts TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.lesson_review_items TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.lesson_versions TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.lesson_sources TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.lesson_review_notes TO `{PRINCIPAL}`",
        # Ticket 39: the categories and methods each lesson version names.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.lesson_version_tags TO `{PRINCIPAL}`",
        # Ticket 32's retrieval loop: passage reports, the decisions on them, each answer's sources, the query
        # judges' grades and each query's pair of judges. No one may write them outside the app.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.candidate_labels TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.label_decisions TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.answer_citations TO `{PRINCIPAL}`",
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.retrieval_grades TO `{PRINCIPAL}`",
        # The pair of judges a query loaded before the roles file named any keeps at its first grade.
        f"GRANT SELECT, MODIFY ON TABLE strata.ops.retrieval_queries TO `{PRINCIPAL}`",
        # Ticket 39: the Lessons page's "Your reports" reads each reader's own counts.
        f"GRANT SELECT ON TABLE strata.ops.retrieval_feedback_viewers TO `{PRINCIPAL}`",
    ]


def test_after_its_grants_the_deploy_masks_who_sent_each_report_and_who_asked_each_question_from_every_reader(
        tmp_path, capsys):
    """Ticket 64. The readers group may read all of strata.ops (bundle/catalog.yml), so the deploy puts one column mask
    on each column that says who (strata.lakehouse.masks): the app's own principal, which reads the reports back, and
    the user who deploys, whose identity runs the weekly retrieval job, read the value; everyone else reads NULL."""
    workspace = FakeWorkspace()

    deploy(workspace, tmp_path, capsys)

    grants = len(deploy_app.grants(PRINCIPAL))
    function, *columns = workspace.statements[grants:]
    assert function.startswith("CREATE OR REPLACE FUNCTION strata.ops.mask_viewer(value STRING) RETURNS STRING")
    assert function.endswith(f"RETURN CASE WHEN current_user() IN ('{PRINCIPAL}', 'owner@example.org') THEN value END")
    assert columns == [
        "ALTER TABLE strata.ops.candidate_labels ALTER COLUMN viewer_id SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.candidate_labels ALTER COLUMN viewer_email SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.answer_citations ALTER COLUMN viewer_id SET MASK strata.ops.mask_viewer",
        # Ticket 38: an implementing agency's upload and every team's drafts keep their words from every reader.
        "ALTER TABLE strata.ops.uploads ALTER COLUMN uploader_name SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.uploads ALTER COLUMN file_name SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.uploads ALTER COLUMN reading SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.upload_rows ALTER COLUMN activity_reference_no SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.upload_rows ALTER COLUMN description SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.upload_rows ALTER COLUMN content SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.drafts ALTER COLUMN content SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.draft_exports ALTER COLUMN snapshot SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.draft_files ALTER COLUMN content SET MASK strata.ops.mask_viewer",
        # Ticket 39: a draft's lesson choices keep the author's reason and the rewritten row, the draft's words too.
        "ALTER TABLE strata.ops.draft_lesson_choices ALTER COLUMN reason SET MASK strata.ops.mask_viewer",
        "ALTER TABLE strata.ops.draft_lesson_choices ALTER COLUMN rewrite SET MASK strata.ops.mask_viewer",
    ]


@pytest.mark.parametrize("owner", ["o'brien@example.org", "owner@example.org') OR (1 = 1", ""])
def test_the_masks_name_only_a_principal_and_an_owner_the_deploy_could_check(owner):
    """The mask's two names are written into its SQL, as the grants write the principal, so each is checked first."""
    with pytest.raises(ValueError, match="not a user name"):
        deploy_app.masks(PRINCIPAL, owner)


def test_the_deploy_replaces_the_day_one_probe_app_and_starts_a_stopped_app(tmp_path, capsys):
    workspace = FakeWorkspace(app={"description": PROBE, "source": "/Workspace/Users/owner@example.org/strata-dayone/probe_app",
                                   "url": "https://strata-1.aws.databricksapps.com", "principal": PRINCIPAL,
                                   "running": False})

    code, out = deploy(workspace, tmp_path, capsys)

    assert code == 0
    assert workspace.started == ["strata"]
    assert workspace.apps["strata"]["source"] == "/Workspace/Users/owner@example.org/strata-app"
    assert "Strata is running at" in out
    # The probe app's address was open in a browser before it had the sql scope (ticket 83): the deploy says what to do.
    assert "The app existed before this deploy." in out
    assert "sign out of the app once" in out
    assert out.rstrip().splitlines()[-1].startswith("Strata is running at")


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


def test_the_command_s_help_says_how_to_run_it_and_when_a_bundle_deploy_needs_it_again(capsys):
    """Since ticket 79 the bundle deploy gives the app back its USE CATALOG and USE SCHEMA, so only a bundle deploy
    that makes a new table the app writes needs this deploy again, for that table's grant."""
    with pytest.raises(SystemExit) as stopped:
        deploy_app.main(["--help"])

    out = " ".join(capsys.readouterr().out.split())
    assert stopped.value.code == 0
    assert "uv run --script ops/app/deploy_app.py --env-file .env" in out
    assert "Run it again after every bundle deploy" not in out
    assert ("Run it again after a bundle deploy that makes a table the app writes, so the app gets that table's "
            "grant.") in out


def test_with_a_genie_space_the_app_asks_it_as_each_viewer():
    """Ticket 33: ask_genie reads GENIE_SPACE_ID, and the viewer's token needs the dashboards.genie scope."""
    import yaml

    started = yaml.safe_load(deploy_app.app_yaml(True, True, "01f0aaaabbbbccccddddeeeeffff0000"))

    assert {"name": "GENIE_SPACE_ID", "value": "01f0aaaabbbbccccddddeeeeffff0000"} in started["env"]
    assert deploy_app.app_yaml(True, True) == (deploy_app.HERE / "app.yaml").read_bytes()
    assert "dashboards.genie" in deploy_app.SCOPES


# Ticket 70: only the user may write secrets in the shared workspace, so a session that may not still redeploys new
# code with --keep-secrets once the user has written them.
APPINSIGHTS = "APPLICATIONINSIGHTS_CONNECTION_STRING"
WRITTEN_BY_THE_USER = {("strata", key): "written by the user" for key in (APPINSIGHTS, *FOUNDRY, *JUDGE)}


def env_file(tmp_path, env):
    path = tmp_path / "strata.env"
    path.write_text("".join(f"{key}='{value}'\n" for key, value in env.items()))
    return path


@pytest.mark.parametrize("keys", [{}, FOUNDRY, FOUNDRY | JUDGE], ids=["no agent", "agent", "agent and judge"])
def test_with_keep_secrets_the_deploy_writes_no_secret_and_gives_the_app_what_a_run_without_it_gives(
        tmp_path, capsys, keys):
    env = ENV | keys
    kept = FakeWorkspace(secrets=WRITTEN_BY_THE_USER)
    dist = tmp_path / "dist"

    code = deploy_app.main(["--env-file", str(env_file(tmp_path, env)), "--keep-secrets"], workspace=kept,
                           build_web=built(dist), dist=dist)
    out = capsys.readouterr().out
    rewritten = FakeWorkspace()
    deploy(rewritten, tmp_path, capsys, env=env)

    assert code == 0
    assert kept.written == [] and kept.secrets == WRITTEN_BY_THE_USER
    assert kept.configured == rewritten.configured
    assert kept.uploaded == rewritten.uploaded and kept.deployed == rewritten.deployed
    assert kept.statements == rewritten.statements
    expected = " ".join(out.split()).split("I expect these secrets in the scope strata: ")[1].split(".")[0]
    assert expected.split(", ") == [APPINSIGHTS, *keys]
    assert not [value for value in keys.values() if value in out]
    assert out.rstrip().splitlines()[-1] == "Strata is running at https://strata-1.aws.databricksapps.com"


@pytest.mark.parametrize(("lacks", "like"), [("FOUNDRY_TENANT_ID", ENV | JUDGE), ("AZURE_OPENAI_API_KEY", ENV | FOUNDRY)],
                         ids=["no agent", "no judge"])
def test_with_keep_secrets_a_secret_the_scope_lacks_is_named_and_the_app_deploys_as_without_its_key_in_the_env_file(
        tmp_path, capsys, lacks, like):
    """The app comes up and says it has no agent or no judge, and the line before the upload says what to write into
    the scope. (Ticket 70's criterion 2 changed on October 25, 2026 from a stop: the scope lacked FOUNDRY_TENANT_ID.)"""
    lacking = {named: value for named, value in WRITTEN_BY_THE_USER.items() if named[1] != lacks}
    workspace = FakeWorkspace(secrets=lacking)
    dist = tmp_path / "dist"

    code = deploy_app.main(["--env-file", str(env_file(tmp_path, ENV | FOUNDRY | JUDGE)), "--keep-secrets"],
                           workspace=workspace, build_web=built(dist), dist=dist)
    out = " ".join(capsys.readouterr().out.split())
    without_the_key = FakeWorkspace()
    deploy(without_the_key, tmp_path, capsys, env=like)

    assert code == 0
    named = out.index(f"The secret scope strata has no {lacks}, so the app gets no ")
    assert named < out.index(f"databricks secrets put-secret strata {lacks}") < out.index("4. Uploading")
    assert workspace.written == [] and workspace.secrets == lacking
    assert workspace.configured == without_the_key.configured
    assert workspace.uploaded == without_the_key.uploaded and workspace.deployed == without_the_key.deployed
    assert "not-a-real-key" not in out
    assert out.endswith("Strata is running at https://strata-1.aws.databricksapps.com")


def test_with_keep_secrets_a_scope_without_the_connection_string_gives_an_app_that_sends_no_traces(tmp_path, capsys):
    """An app resource or an app.yaml entry that names a secret the scope lacks would stop the app from starting."""
    lacking = {named: value for named, value in WRITTEN_BY_THE_USER.items() if named[1] != APPINSIGHTS}
    workspace = FakeWorkspace(secrets=lacking)
    dist = tmp_path / "dist"

    code = deploy_app.main(["--env-file", str(env_file(tmp_path, ENV)), "--keep-secrets"],
                           workspace=workspace, build_web=built(dist), dist=dist)
    out = " ".join(capsys.readouterr().out.split())

    assert code == 0
    [(_, _, resources, _)] = workspace.configured
    assert [resource["name"] for resource in resources] == ["sql-warehouse", "app-state"]
    started = yaml.safe_load(workspace.uploaded["files"]["app.yaml"])
    assert APPINSIGHTS not in [entry["name"] for entry in started["env"]]
    assert started["command"] == ["python", "-m", "strata.server"]
    assert f"The secret scope strata has no {APPINSIGHTS}, so the app sends no traces to Application Insights" in out
    assert f"databricks secrets put-secret strata {APPINSIGHTS}" in out


def test_the_command_s_help_says_when_to_keep_the_secrets(capsys):
    with pytest.raises(SystemExit):
        deploy_app.main(["--help"])

    out = " ".join(capsys.readouterr().out.split())
    assert "uv run --script ops/app/deploy_app.py --env-file .env --keep-secrets" in out
    assert "once the user has written the secrets" in out


def test_the_live_workspace_lists_the_scope_s_keys_and_never_their_values():
    """The live adapter answers every call the fake workspace answers, and reads only the keys' names, which the
    Databricks secrets API returns without their values."""
    import app_live

    class Secrets:
        def list_secrets(self, scope):
            assert scope == "strata"
            return [SimpleNamespace(key=APPINSIGHTS, last_updated_timestamp=1761400000000),
                    SimpleNamespace(key="FOUNDRY_CLIENT_ID", last_updated_timestamp=1761400000000)]

    live = object.__new__(app_live.LiveApps)
    live.w = SimpleNamespace(secrets=Secrets())

    assert live.secret_keys("strata") == [APPINSIGHTS, "FOUNDRY_CLIENT_ID"]
    called = {name for name in vars(FakeWorkspace) if not name.startswith("_")}
    assert called <= {name for name in vars(app_live.LiveApps) if not name.startswith("_")}


# Ticket 81: on October 26, 2026 at about 14:55 UTC a deploy ran while Free Edition's daily limit had stopped the SQL
# warehouse (12:53 UTC) and the App's compute (12:57). It printed steps 1 to 5 as if they had passed, registered no
# deployment, and failed in step 6 with TABLE_DOES_NOT_EXIST for a table that existed. So the deploy reads the
# workspace's state first, checks after step 5 that a new deployment succeeded, and names the warehouse's state before
# a refused statement's message.
STRATA_APP = {"description": deploy_app.DESCRIPTION, "source": "/Workspace/Users/owner@example.org/strata-app",
              "url": "https://strata-1.aws.databricksapps.com", "principal": PRINCIPAL, "running": False}
# What apps get strata answered at 13:01 UTC on October 26, 2026 (docs/workspace-catchup.md, ticket 06).
STOPPED_BY_THE_WORKSPACE = {"state": "STOPPED", "message": "App compute was stopped due to workspace or account status."}


def test_an_app_whose_compute_the_workspace_stopped_stops_the_deploy_before_step_1_with_one_sentence(tmp_path, capsys):
    workspace = FakeWorkspace(app=STRATA_APP, compute=STOPPED_BY_THE_WORKSPACE)

    code, out = deploy(workspace, tmp_path, capsys)

    assert code == 2
    assert out.splitlines() == [
        "I changed nothing, because the app strata's compute is STOPPED with the message \"App compute was stopped due "
        "to workspace or account status.\", which on Free Edition usually means the workspace reached its daily compute "
        "limit."]
    assert workspace.uploaded == {} and workspace.configured == [] and workspace.deployed == []
    assert workspace.statements == [] and workspace.written == [] and workspace.started == []


# What databricks warehouses start answered at 10:33 UTC on October 25, 2026 (docs/workspace-catchup.md, ticket 11).
FREE_DAILY_LIMIT = "Sorry, cannot run the resource because you have hit your free daily limit. Please come back again tomorrow."


def test_a_stopped_warehouse_that_will_not_start_stops_the_deploy_before_step_1_with_one_sentence(tmp_path, capsys):
    workspace = FakeWorkspace(app=STRATA_APP, warehouse="STOPPED", warehouse_answer=FREE_DAILY_LIMIT)

    code, out = deploy(workspace, tmp_path, capsys)

    assert code == 2
    assert out.splitlines() == [
        "I changed nothing, because the SQL warehouse wh-1 is STOPPED and would not start when I asked, saying \"Sorry, "
        "cannot run the resource because you have hit your free daily limit. Please come back again tomorrow.\", which "
        "on Free Edition usually means the workspace reached its daily compute limit."]
    assert workspace.warehouse_starts == 1
    assert workspace.uploaded == {} and workspace.configured == [] and workspace.deployed == []
    assert workspace.statements == [] and workspace.written == [] and workspace.started == []


def test_a_warehouse_that_stopped_when_it_sat_idle_starts_and_the_deploy_goes_on(tmp_path, capsys):
    """A warehouse stops after it sits idle and starts again when asked, so only one that will not start stops the
    deploy. A stopped App starts in step 5, as before."""
    workspace = FakeWorkspace(app=STRATA_APP, warehouse="STOPPED")

    code, out = deploy(workspace, tmp_path, capsys)

    assert code == 0
    assert workspace.warehouse_starts == 1 and workspace.started == ["strata"]
    assert out.splitlines()[0] == "1. Building the web app."


RUN_STARTED = dt.datetime(2026, 10, 26, 14, 55, 2, tzinfo=dt.UTC)
# The newest deployment apps list-deployments showed at 15:00 UTC on October 26, 2026: none after 10:29 UTC.
BEFORE_THE_RUN = {"id": "01f0b27c4e5d1a2b", "state": "SUCCEEDED", "message": "App started successfully",
                  "created": dt.datetime(2026, 10, 26, 10, 29, 31, tzinfo=dt.UTC)}


class RegistersNothing(FakeWorkspace):
    """Step 5 on a stopped workspace: the deploy call came back, and the app lists no deployment made since."""

    def deploy(self, name, folder):
        self.deployed.append((name, folder))
        return self.apps[name]["url"]


def deploy_at(workspace, tmp_path, capsys, now):
    code = deploy_app.deploy(workspace, ENV, build_web=built(tmp_path / "dist"), dist=tmp_path / "dist", now=now)
    return code, capsys.readouterr().out


def test_a_step_5_that_registers_no_new_deployment_fails_there_and_names_the_newest_deployment_it_found(
        tmp_path, capsys):
    workspace = RegistersNothing(app=STRATA_APP | {"running": True}, deployments=[BEFORE_THE_RUN])

    code, out = deploy_at(workspace, tmp_path, capsys, now=lambda: RUN_STARTED)

    assert code == 1
    assert out.split("5. Deploying the app. This takes a few minutes.\n")[1].splitlines() == [
        "The app strata has no deployment made since this run started at 14:55:02 UTC on October 26, 2026, so step 5 "
        "registered nothing. Its newest deployment is 01f0b27c4e5d1a2b, made at 10:29:31 UTC on October 26, 2026, "
        "with the state SUCCEEDED. I stopped here and granted nothing."]
    assert workspace.deployed == [("strata", "/Workspace/Users/owner@example.org/strata-app")]
    assert workspace.statements == []


def test_after_step_5_the_deploy_names_the_new_deployment_that_succeeded(tmp_path, capsys):
    workspace = FakeWorkspace(app=STRATA_APP | {"running": True}, deployments=[BEFORE_THE_RUN])
    workspace.clock = lambda: RUN_STARTED + dt.timedelta(minutes=4, seconds=31)

    code, out = deploy_at(workspace, tmp_path, capsys, now=lambda: RUN_STARTED)

    assert code == 0
    assert out.split("5. Deploying the app. This takes a few minutes.\n")[1].splitlines()[0] == (
        "   The deployment 01f0b2deploy0001, made at 14:59:33 UTC on October 26, 2026, succeeded.")
    assert out.rstrip().splitlines()[-1] == "Strata is running at https://strata-1.aws.databricksapps.com"


def test_a_new_deployment_that_failed_stops_the_deploy_at_step_5_with_its_state_and_message(tmp_path, capsys):
    """On October 26, 2026 two deployments failed with "Error installing packages" (docs/workspace-catchup.md)."""
    class Fails(FakeWorkspace):
        def deploy(self, name, folder):
            self.deployed.append((name, folder))
            self.registered.append({"id": "01f0b2a7f3c90e11", "state": "FAILED", "message": "Error installing packages",
                                    "created": RUN_STARTED + dt.timedelta(minutes=3)})
            return self.apps[name]["url"]

    workspace = Fails(app=STRATA_APP | {"running": True}, deployments=[BEFORE_THE_RUN])

    code, out = deploy_at(workspace, tmp_path, capsys, now=lambda: RUN_STARTED)

    assert code == 1
    assert out.split("5. Deploying the app. This takes a few minutes.\n")[1].splitlines() == [
        "Step 5's deployment 01f0b2a7f3c90e11, made at 14:58:02 UTC on October 26, 2026, has the state FAILED with the "
        "message \"Error installing packages\". I stopped here and granted nothing."]
    assert workspace.statements == []


# What the deploy of 14:55 UTC on October 26, 2026 printed in step 6, for a table that existed.
NOT_A_MISSING_TABLE = ("The warehouse did not run the statement. Its state was FAILED: TABLE_DOES_NOT_EXIST: Table "
                       "'strata.ops.exposures' does not exist")


class StoppedByStep6(FakeWorkspace):
    """The warehouse ran when the deploy started and stopped before step 6, as Free Edition's daily limit stops it
    partway through a day (12:53 UTC on October 26, 2026). It then refuses every statement with an error."""

    def run_sql(self, statement):
        if "exposures" in statement:
            self.warehouse |= {"state": "STOPPED", "message": "no longer eligible for Serverless Compute"}
        if self.warehouse["state"] != "RUNNING":
            raise RuntimeError(NOT_A_MISSING_TABLE)
        self.statements.append(statement)


def test_a_statement_the_warehouse_refuses_in_step_6_is_named_after_the_warehouse_s_state(tmp_path, capsys):
    workspace = StoppedByStep6(app=STRATA_APP)

    code, out = deploy(workspace, tmp_path, capsys)
    step_6 = out.split("6. Letting the app's own service principal")[1].splitlines()[1:]

    assert code == 1
    assert step_6 == [
        "   The SQL warehouse wh-1 was STOPPED when it refused this statement, with the message \"no longer eligible "
        "for Serverless Compute\". A warehouse that is not running refuses every statement, so its answer below may not "
        "mean what it says.",
        f"   The statement: GRANT SELECT, MODIFY ON TABLE strata.ops.exposures TO `{PRINCIPAL}`",
        f"   The warehouse said: {NOT_A_MISSING_TABLE}",
        "I stopped at step 6, so the app's own service principal may lack some of its grants. Deploy again once the "
        "SQL warehouse runs."]
    assert out.index("was STOPPED") < out.index("TABLE_DOES_NOT_EXIST")
    assert "7. Masking" not in out and "Strata is running at" not in out


def test_a_statement_a_running_warehouse_refuses_is_named_as_the_statement_s_own_error(tmp_path, capsys):
    """A running warehouse's answer is about the statement, such as a grant the deploy's identity may not give."""
    class Refuses(FakeWorkspace):
        def run_sql(self, statement):
            if statement.startswith("CREATE OR REPLACE FUNCTION"):
                raise RuntimeError("PERMISSION_DENIED: User does not have CREATE FUNCTION on Schema 'strata.ops'.")
            self.statements.append(statement)

    code, out = deploy(Refuses(app=STRATA_APP), tmp_path, capsys)
    step_7 = out.split("7. Masking who sent each passage report")[1].splitlines()[1:]

    assert code == 1
    assert step_7[0] == ("   The SQL warehouse wh-1 was RUNNING when it refused this statement, so its answer below is "
                         "about the statement.")
    assert step_7[2] == ("   The warehouse said: PERMISSION_DENIED: User does not have CREATE FUNCTION on Schema "
                         "'strata.ops'.")
    assert step_7[3] == "I stopped at step 7, so some columns may lack their mask."
