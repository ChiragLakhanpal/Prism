"""The PAD probe (test 3): ai_parse_document reads every page of a PAD of 120 pages or more."""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402
import probe_parse_pad  # noqa: E402
from dayone import ProbeError, SetupError  # noqa: E402

PAD = {"project": "P160009", "url": "https://documents.worldbank.org/curated/en/212451501293669530/pdf/x.pdf",
       "pages": 131, "data": b"%PDF-1.4 fake"}


class FakeWorkspace:
    def __init__(self, pad=PAD, parsed=None, refuse=None, refuse_setup=None):
        self.pad, self.refuse, self.refuse_setup = pad, refuse, refuse_setup
        self.parsed = parsed if parsed is not None else {"pages": 131, "error": None}
        self.asked_for = None
        self.uploaded = None

    def find_pad(self, settings):
        self.asked_for = settings
        if self.pad is None:
            raise ProbeError("None of 6 PADs had 120 pages or more.")
        return dict(self.pad)

    def parse(self, name, data):
        self.uploaded = (name, data)
        if self.refuse_setup:
            raise SetupError(self.refuse_setup)
        if self.refuse:
            raise ProbeError(self.refuse)
        return {"statement": "01ef-77", "seconds": 212.0, "path": f"/Volumes/workspace/strata_dayone/files/{name}",
                **self.parsed}


@pytest.fixture
def place(tmp_path):
    # A probe's first run starts from the template, whatever results the committed document holds.
    dayone.ensure_document(tmp_path / "results.md", dayone.load_config())
    (tmp_path / "probe.env").write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\n"
                                        "DATABRICKS_TOKEN='dapi-x'\nDATABRICKS_WAREHOUSE_ID='wh1'\n")
    return tmp_path


def run(place, workspace):
    code = probe_parse_pad.main(["--env-file", str(place / "probe.env"), "--results", str(place / "results.md")],
                                service=workspace)
    return code, dayone.read_results(place / "results.md")["test-3"]


def test_every_page_read_passes_and_keeps_ai_parse_document(place):
    workspace = FakeWorkspace()
    code, test3 = run(place, workspace)
    assert code == 0
    assert test3["Status"] == "passed"
    assert test3["Chosen path"].startswith("Default")
    assert workspace.asked_for["min_pages"] == 120
    assert workspace.uploaded == ("P160009-pad.pdf", b"%PDF-1.4 fake")
    assert any("131 pages" in line for line in test3["Evidence"])


def test_some_pages_read_switches_to_content_understanding(place):
    code, test3 = run(place, FakeWorkspace(parsed={"pages": 40, "error": None}))
    assert code == 1
    assert test3["Status"] == "partly"
    assert "40 of 131" in test3["Result"]
    assert "Content Understanding" in test3["Chosen path"]


def test_an_error_from_ai_parse_document_switches_to_content_understanding(place):
    code, test3 = run(place, FakeWorkspace(parsed={"pages": None, "error": "[{\"error_message\": \"too large\"}]"}))
    assert test3["Status"] == "failed"
    assert "Content Understanding" in test3["Chosen path"]
    assert any("too large" in line for line in test3["Evidence"])


def test_a_refused_statement_is_recorded_as_a_failure(place):
    code, test3 = run(place, FakeWorkspace(refuse="The statement 01ef-78 ended FAILED: AI_FUNCTION_NOT_AVAILABLE"))
    assert test3["Status"] == "failed"
    assert any("AI_FUNCTION_NOT_AVAILABLE" in line for line in test3["Evidence"])


def test_no_long_pad_leaves_the_test_not_run_and_the_path_unchanged(place):
    code, test3 = run(place, FakeWorkspace(pad=None))
    assert code == 1
    assert test3["Status"] == "not run"
    assert "120 pages" in test3["Result"]
    assert test3["Chosen path"].startswith("Default")


def test_a_volume_the_warehouse_refuses_leaves_test_3_not_run(place):
    refused = "Running \"CREATE VOLUME IF NOT EXISTS ...\" on the warehouse failed: PERMISSION_DENIED"
    code, test3 = run(place, FakeWorkspace(refuse_setup=refused))
    assert code == 1
    assert test3["Status"] == "not run"
    assert test3["Chosen path"].startswith("Default")
    assert "Content Understanding" not in test3["Chosen path"]
    assert any("P160009" in line for line in test3["Evidence"])
    assert any("PERMISSION_DENIED" in line for line in test3["Evidence"])
