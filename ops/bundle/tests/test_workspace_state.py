"""The workspace's state, read through the SDK before a command changes anything (ticket 81).

The App deploy, the bundle deploy and the demo-ready command each test their own stop with a fake workspace. These
tests hold the live readers to the SDK's objects, as apps get, warehouses get and apps list-deployments return them,
with stand-ins for the SDK's client, since the gate runs without it. docs/workspace-catchup.md runs them live.
"""

import datetime as dt
import sys
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "bundle"))

import workspace_state  # noqa: E402


class SdkState(Enum):
    """The SDK's state enums (apps.ComputeState, sql.State, apps.AppDeploymentState) by their values."""

    STOPPED = "STOPPED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


def sdk_client(started=None):
    """The SDK client's apps and warehouses as the stopped Free Edition workspace answered them on October 26, 2026."""
    app = SimpleNamespace(compute_status=SimpleNamespace(
        state=SdkState.STOPPED, message="App compute was stopped due to workspace or account status.",
        active_instances=0))
    deployments = [
        SimpleNamespace(deployment_id="01f0b27c4e5d1a2b", create_time="2026-10-26T10:29:31.481Z",
                        status=SimpleNamespace(state=SdkState.SUCCEEDED, message="App started successfully")),
        SimpleNamespace(deployment_id="01f0b1a7f3c90e11", create_time="2026-10-26T05:46:02Z",
                        status=SimpleNamespace(state=SdkState.FAILED, message="Error installing packages"))]
    warehouse = SimpleNamespace(state=SdkState.STOPPED, health=SimpleNamespace(
        summary="no longer eligible for Serverless Compute", message=None, status=None))

    def start_and_wait(warehouse_id, timeout):
        started.append((warehouse_id, timeout))

    return SimpleNamespace(
        apps=SimpleNamespace(get=lambda name: app, list_deployments=lambda app_name: iter(deployments)),
        warehouses=SimpleNamespace(get=lambda warehouse_id: warehouse, start_and_wait=start_and_wait))


def test_the_live_readers_take_the_app_s_compute_and_the_warehouse_s_state_from_the_sdk():
    w = sdk_client()

    compute = workspace_state.app_compute(w, "strata")
    warehouse = workspace_state.warehouse_state(w, "d45865dbf2e0f97e")

    assert compute == {"state": "STOPPED", "message": "App compute was stopped due to workspace or account status."}
    assert workspace_state.app_stopped_by_the_workspace(compute)
    assert warehouse == {"id": "d45865dbf2e0f97e", "state": "STOPPED",
                         "message": "no longer eligible for Serverless Compute"}


def test_an_app_a_person_stopped_is_not_stopped_by_the_workspace():
    """A person, or the platform's 24-hour limit, stops an App that starts again, so only the workspace's own message
    counts as a refusal."""
    assert not workspace_state.app_stopped_by_the_workspace({"state": "STOPPED", "message": "App compute is stopped."})
    assert not workspace_state.app_stopped_by_the_workspace(None)


def test_the_live_start_waits_for_the_warehouse_to_run_for_a_bounded_time():
    started = []

    workspace_state.start_warehouse(sdk_client(started), "d45865dbf2e0f97e")

    assert started == [("d45865dbf2e0f97e", dt.timedelta(minutes=10))]


def test_the_live_reader_lists_each_deployment_with_its_state_and_its_time_in_utc():
    assert workspace_state.deployments(sdk_client(), "strata") == [
        {"id": "01f0b27c4e5d1a2b", "state": "SUCCEEDED", "message": "App started successfully",
         "created": dt.datetime(2026, 10, 26, 10, 29, 31, 481000, tzinfo=dt.UTC)},
        {"id": "01f0b1a7f3c90e11", "state": "FAILED", "message": "Error installing packages",
         "created": dt.datetime(2026, 10, 26, 5, 46, 2, tzinfo=dt.UTC)}]
