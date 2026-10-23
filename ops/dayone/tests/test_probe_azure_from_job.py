"""The Azure-from-a-job probe (test 2): a Databricks job reaches Foundry and Azure OpenAI."""

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402
import probe_azure_from_job  # noqa: E402
from dayone import ProbeError, SetupError  # noqa: E402

RESULTS = REPO / "docs" / "day-one-results.md"
FOUNDRY = "https://wb-strata.services.ai.azure.com/api/projects/Strata"
OPENAI = "https://wb-strata.openai.azure.com/openai/v1"


class FakeJob:
    def __init__(self, answer=None, refuse=None, refuse_setup=None):
        self.answer = answer if answer is not None else {"foundry": 401, "openai": 401, "openai_with_key": 200}
        self.refuse, self.refuse_setup = refuse, refuse_setup
        self.settings = None

    def from_job(self, settings):
        self.settings = settings
        if self.refuse_setup:
            raise SetupError(self.refuse_setup)
        if self.refuse:
            raise ProbeError(self.refuse)
        return "https://dbc-1.cloud.databricks.com/jobs/runs/9", self.answer


@pytest.fixture
def place(tmp_path):
    shutil.copy(RESULTS, tmp_path / "results.md")
    (tmp_path / "probe.env").write_text(
        "DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\nDATABRICKS_TOKEN='dapi-x'\n"
        f"FOUNDRY_PROJECT_ENDPOINT='{FOUNDRY}'\nAZURE_OPENAI_ENDPOINT='{OPENAI}'\n"
        "AZURE_OPENAI_API_KEY='never-sent-to-the-job'\n")
    return tmp_path


def run(place, job):
    code = probe_azure_from_job.main(["--env-file", str(place / "probe.env"), "--results", str(place / "results.md")],
                                     service=job)
    return code, dayone.read_results(place / "results.md")["test-2"]


def test_both_endpoints_answering_from_a_job_passes(place):
    job = FakeJob()
    code, test2 = run(place, job)
    assert code == 0
    assert test2["Status"] == "passed"
    assert job.settings == {"foundry_endpoint": FOUNDRY, "openai_endpoint": OPENAI, "scope": "strata"}
    assert any("jobs/runs/9" in line for line in test2["Evidence"])


def test_the_key_never_travels_with_the_job(place):
    job = FakeJob()
    run(place, job)
    assert "never-sent-to-the-job" not in repr(job.settings)
    assert "never-sent-to-the-job" not in (place / "results.md").read_text()


def test_an_endpoint_that_does_not_answer_fails(place):
    timed_out = "no answer (URLError: timed out)"
    code, test2 = run(place, FakeJob({"foundry": 401, "openai": timed_out, "openai_with_key": timed_out}))
    assert code == 1
    assert test2["Status"] == "failed"
    assert "Azure OpenAI" in test2["Result"]


def test_a_refused_key_still_shows_the_network_allows_the_call(place):
    code, test2 = run(place, FakeJob({"foundry": 401, "openai": 401, "openai_with_key": 401}))
    assert test2["Status"] == "partly"
    assert test2["Chosen path"].startswith("Default")
    assert "key" in test2["Chosen path"]


def test_a_key_the_job_cannot_read_still_shows_the_network_allows_the_call(place):
    no_key = "no key (SecretNotFound: AZURE_OPENAI_API_KEY)"
    code, test2 = run(place, FakeJob({"foundry": 401, "openai": 401, "openai_with_key": no_key}))
    assert test2["Status"] == "partly"
    assert "secret scope" in test2["Result"]


def test_a_job_that_cannot_run_is_recorded_with_its_reason(place):
    code, test2 = run(place, FakeJob(refuse_setup="Starting the job run failed: QUOTA_EXCEEDED"))
    assert code == 1
    assert test2["Status"] == "not run"
    assert test2["Chosen path"].startswith("Default")
    assert any("QUOTA_EXCEEDED" in line for line in test2["Evidence"])


def test_a_job_that_fails_after_it_starts_is_a_failure(place):
    code, test2 = run(place, FakeJob(refuse="Reading the job run's output failed: 500"))
    assert test2["Status"] == "failed"
    assert any("500" in line for line in test2["Evidence"])
