"""The traces probe (test 10): a span the app sends shows up in Application Insights."""

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402
import probe_traces  # noqa: E402
from dayone import ProbeError, SetupError  # noqa: E402

RESULTS = REPO / "docs" / "day-one-results.md"
APP = "https://strata-42.aws.databricksapps.com"


class FakeTraces:
    def __init__(self, sent=None, found=True, refuse_send=None, refuse_find=None, app_missing=None):
        self.sent, self.app_missing = sent, app_missing
        self.found, self.refuse_send, self.refuse_find = found, refuse_send, refuse_find
        self.markers = []

    def send(self, marker):
        self.markers.append(marker)
        if self.app_missing:
            raise SetupError(self.app_missing)
        if self.refuse_send:
            raise ProbeError(self.refuse_send)
        return self.sent or {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "flushed": True, "app": APP}

    def find(self, marker):
        if self.refuse_find:
            raise ProbeError(self.refuse_find)
        return [["2026-10-24T09:00:00Z", "dependency", "4bf92f3577b34da6a3ce929d0e0e4736"]] if self.found else []


@pytest.fixture
def place(tmp_path):
    shutil.copy(RESULTS, tmp_path / "results.md")
    (tmp_path / "probe.env").write_text(
        "DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\nDATABRICKS_TOKEN='dapi-x'\n"
        "APPLICATIONINSIGHTS_CONNECTION_STRING='InstrumentationKey=secret-ik;ApplicationId=app-0042'\n")
    return tmp_path


def run(place, traces):
    code = probe_traces.main(["--env-file", str(place / "probe.env"), "--results", str(place / "results.md")],
                             service=traces)
    return code, dayone.read_results(place / "results.md")["test-10"]


def test_a_trace_found_by_its_marker_passes(place):
    traces = FakeTraces()
    code, test10 = run(place, traces)
    assert code == 0
    assert test10["Status"] == "passed"
    assert len(traces.markers) == 1 and traces.markers[0].startswith("strata-dayone-")
    assert any("4bf92f3577b34da6a3ce929d0e0e4736" in line for line in test10["Evidence"])
    assert any(traces.markers[0] in line for line in test10["Evidence"])


def test_each_run_uses_a_new_marker(place):
    traces = FakeTraces()
    run(place, traces)
    run(place, traces)
    assert len(set(traces.markers)) == 2


def test_a_trace_that_never_arrives_fails(place):
    code, test10 = run(place, FakeTraces(found=False))
    assert code == 1
    assert test10["Status"] == "failed"
    assert test10["Chosen path"].startswith("Undecided")


def test_an_app_without_tracing_fails_with_its_reason(place):
    sent = {"error": "Tracing is off: the app has no Application Insights connection string.", "app": APP}
    code, test10 = run(place, FakeTraces(sent=sent))
    assert test10["Status"] == "failed"
    assert any("Tracing is off" in line for line in test10["Evidence"])


def test_an_app_that_cannot_be_reached_fails_with_its_reason(place):
    code, test10 = run(place, FakeTraces(refuse_send="Using the browser sign-in saved under the profile strata failed"))
    assert test10["Status"] == "failed"
    assert any("profile strata" in line for line in test10["Evidence"])


def test_the_connection_string_stays_out_of_the_document(place):
    run(place, FakeTraces())
    assert "secret-ik" not in (place / "results.md").read_text()


def test_an_app_that_cannot_deploy_leaves_test_10_not_run(place):
    code, test10 = run(place, FakeTraces(app_missing="Deploying the app strata failed: quota of apps reached"))
    assert code == 1
    assert test10["Status"] == "not run"
    assert any("quota of apps reached" in line for line in test10["Evidence"])
