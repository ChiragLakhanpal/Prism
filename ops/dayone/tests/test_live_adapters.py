"""The live adapters: which failures only stop a test from starting, and how values reach the warehouse.

A step that only gets a test ready raises SetupError, so the probe records the test as not run and
keeps its default path. The az cases use a fake az command and need only the standard library. The
warehouse and job cases build the Databricks SDK's own types, so they run only where the SDK is
installed:

    uv run --python 3.12 --with pytest --with databricks-sdk==0.156.0 pytest ops/dayone/tests/test_live_adapters.py
"""

import datetime as dt
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402
import live  # noqa: E402
from dayone import ProbeError, SetupError  # noqa: E402

FAKE_AZ = """#!/bin/bash
case "$FAKE_AZ_MODE" in
  signed-out) echo "ERROR: Please run 'az login' to setup account." >&2; exit 1 ;;
  missing-resource) echo "ERROR: (ResourceNotFound) The resource wb-strata was not found." >&2; exit 3 ;;
  *) echo '{"id": "sub-0001"}' ;;
esac
"""


@pytest.fixture
def az(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "az").write_text(FAKE_AZ)
    (bin_dir / "az").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    return lambda mode: monkeypatch.setenv("FAKE_AZ_MODE", mode)


def test_a_signed_out_az_is_a_setup_error(az):
    az("signed-out")
    with pytest.raises(SetupError, match="az login"):
        live.az_json("account", "show")


def test_an_az_answer_about_a_missing_resource_is_a_result(az):
    az("missing-resource")
    with pytest.raises(ProbeError, match="ResourceNotFound") as raised:
        live.az_json("rest", "--method", "get")
    assert not isinstance(raised.value, SetupError)


def test_a_computer_without_az_is_a_setup_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(SetupError, match="Install the Azure command line"):
        live.az_json("account", "show")


def test_azure_that_can_read_nothing_stops_before_any_test(az):
    az("signed-out")
    with pytest.raises(SetupError, match="could not read your account"):
        live.LiveAzure(dayone.load_config())


# ── The warehouse: CREATE VOLUME and the upload only get the PAD ready ──

class FakeStatements:
    """A warehouse that refuses each statement containing one of `refuse`."""

    def __init__(self, refuse=()):
        self.refuse, self.calls = refuse, []

    def execute_statement(self, statement, warehouse_id, parameters=None, wait_timeout=None):
        from databricks.sdk.service.sql import StatementState

        self.calls.append((statement, {item.name: item.value for item in parameters or []}))
        refused = next((part for part in self.refuse if part in statement), None)
        error = SimpleNamespace(message=f"{refused}: PERMISSION_DENIED") if refused else None
        rows = [["131", None]] if "ai_parse_document" in statement else [["2048"]]
        return SimpleNamespace(statement_id=f"s{len(self.calls)}", result=SimpleNamespace(data_array=rows),
                               status=SimpleNamespace(state=StatementState.FAILED if refused
                                                      else StatementState.SUCCEEDED, error=error))


PAD_PATH = "/Volumes/workspace/strata_dayone/files/P160009-pad.pdf"


def live_pad(monkeypatch, statements):
    pytest.importorskip("databricks.sdk")
    uploads = []
    fake = SimpleNamespace(statement_execution=statements,
                           files=SimpleNamespace(upload=lambda path, data, overwrite: uploads.append(path)))
    monkeypatch.setattr(live, "workspace", lambda env: fake)
    return live.LivePad({"DATABRICKS_WAREHOUSE_ID": "wh1"}, dayone.load_config()), uploads


def test_a_volume_the_warehouse_refuses_is_a_setup_error(monkeypatch):
    pad, uploads = live_pad(monkeypatch, FakeStatements(refuse=("CREATE VOLUME",)))
    with pytest.raises(SetupError, match="PERMISSION_DENIED"):
        pad.parse("P160009-pad.pdf", b"%PDF")
    assert uploads == []


def test_a_parse_the_warehouse_refuses_is_a_result(monkeypatch):
    pad, uploads = live_pad(monkeypatch, FakeStatements(refuse=("ai_parse_document",)))
    with pytest.raises(ProbeError, match="PERMISSION_DENIED") as raised:
        pad.parse("P160009-pad.pdf", b"%PDF")
    assert not isinstance(raised.value, SetupError)
    assert uploads == [PAD_PATH]


def test_the_parse_binds_the_path_and_makes_the_probes_own_schema_first(monkeypatch):
    statements = FakeStatements()
    pad, _ = live_pad(monkeypatch, statements)
    assert pad.parse("P160009-pad.pdf", b"%PDF")["pages"] == 131
    assert statements.calls[0] == ("CREATE SCHEMA IF NOT EXISTS workspace.strata_dayone", {})
    parse = next(call for call in statements.calls if "ai_parse_document" in call[0])
    assert parse[1] == {"path": PAD_PATH} and PAD_PATH not in parse[0]



class RunningStatements:
    """A warehouse whose statements never finish, and which records each cancel it is asked for."""

    def __init__(self):
        self.cancelled = []

    def execute_statement(self, statement, warehouse_id, parameters=None, wait_timeout=None):
        from databricks.sdk.service.sql import StatementState

        return SimpleNamespace(statement_id="s1", result=None,
                               status=SimpleNamespace(state=StatementState.RUNNING, error=None))

    def get_statement(self, statement_id):
        return self.execute_statement("", "")

    def cancel_execution(self, statement_id):
        self.cancelled.append(statement_id)


def test_a_statement_past_its_deadline_is_cancelled():
    pytest.importorskip("databricks.sdk")
    statements = RunningStatements()
    with pytest.raises(ProbeError, match="ran longer than 0 minutes, so I asked the warehouse to cancel it"):
        live.sql(SimpleNamespace(statement_execution=statements), "wh1", "SELECT 1", minutes=0)
    assert statements.cancelled == ["s1"]

# ── Jobs: a run that never printed a result never tested anything ──

class FakeJobs:
    def __init__(self, refuse_submit=None, output=None):
        self.refuse_submit, self.output, self.timeout_seconds = refuse_submit, output, None
        self.waited = []

    def submit(self, run_name, tasks, environments, timeout_seconds=None):
        if self.refuse_submit:
            raise RuntimeError(self.refuse_submit)
        self.timeout_seconds = timeout_seconds
        return SimpleNamespace(run_id=7, result=lambda timeout: self.waited.append(timeout))

    def get_run(self, run_id):
        return SimpleNamespace(run_page_url="https://dbc-1.cloud.databricks.com/jobs/runs/7",
                               tasks=[SimpleNamespace(run_id=8)])

    def get_run_output(self, run_id):
        return self.output


def run_job(jobs):
    pytest.importorskip("databricks.sdk")
    w = SimpleNamespace(jobs=jobs,
                        current_user=SimpleNamespace(me=lambda: SimpleNamespace(user_name="person@example.org")),
                        workspace=SimpleNamespace(mkdirs=lambda path: None,
                                                  upload=lambda path, data, format, overwrite: None))
    return live.run_on_serverless(w, dayone.load_config(), "reach_hosts", "print(1)", notebook=False)


def test_a_job_that_cannot_start_is_a_setup_error():
    with pytest.raises(SetupError, match="QUOTA_EXCEEDED"):
        run_job(FakeJobs(refuse_submit="QUOTA_EXCEEDED: the daily serverless quota is used up"))


def test_a_job_that_fails_before_it_prints_a_result_is_a_setup_error():
    output = SimpleNamespace(error="Environment failed to install", logs="", notebook_output=None)
    with pytest.raises(SetupError, match="before it printed a result"):
        run_job(FakeJobs(output=output))


def test_a_job_that_prints_a_result_returns_it():
    output = SimpleNamespace(error=None, logs='STRATA_DAYONE_RESULT {"api.worldbank.org": 200}', notebook_output=None)
    link, text = run_job(FakeJobs(output=output))
    assert link.endswith("/jobs/runs/7")
    assert live.parse_result(text) == {"api.worldbank.org": 200}


def test_databricks_stops_a_job_run_at_the_same_30_minutes_the_probe_waits():
    output = SimpleNamespace(error=None, logs='STRATA_DAYONE_RESULT {}', notebook_output=None)
    jobs = FakeJobs(output=output)
    run_job(jobs)
    assert jobs.timeout_seconds == 1800
    assert jobs.waited == [dt.timedelta(seconds=jobs.timeout_seconds)]


# ── The probe app: never take over an app the probes did not make ──

class FakeApps:
    """An app named strata with no deployment yet, which someone else made."""

    def __init__(self, description):
        self.description, self.changed = description, []

    def get(self, name):
        return SimpleNamespace(name=name, description=self.description, active_deployment=None, url=None,
                               resources=[], compute_status=None)

    def update(self, name, app):
        self.changed.append("update")
        return app

    def start_and_wait(self, name, timeout):
        self.changed.append("start")

    def deploy_and_wait(self, name, deployment, timeout):
        self.changed.append("deploy")


def probe_app_in(apps):
    pytest.importorskip("databricks.sdk")
    w = SimpleNamespace(apps=apps,
                        current_user=SimpleNamespace(me=lambda: SimpleNamespace(user_name="person@example.org")),
                        workspace=SimpleNamespace(mkdirs=lambda path: apps.changed.append("mkdirs"),
                                                  upload=lambda path, data, format, overwrite: apps.changed.append(
                                                      "upload")))
    return live.ensure_probe_app(w, {}, dayone.load_config())


def test_an_app_the_probes_did_not_make_is_left_alone_even_with_no_deployment():
    apps = FakeApps(description="Strata, the procurement intelligence app")
    with pytest.raises(SetupError, match="^The probes did not make the app strata, so I left it alone. Set names.app in "):
        probe_app_in(apps)
    assert apps.changed == []


def test_the_probes_own_app_with_no_deployment_gets_the_probe_app():
    apps = FakeApps(description=live.PROBE_APP_DESCRIPTION)
    probe_app_in(apps)
    assert apps.changed == ["update", "start", "mkdirs", "upload", "upload", "upload", "deploy"]
