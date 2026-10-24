"""The hosts probe (test 1): the four World Bank hosts from a notebook, a job and the app.

A host counts as reached from a place when that place gets an HTTP answer; a 403 there while
this computer gets something else counts as blocked.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402
import probe_hosts  # noqa: E402
from dayone import ProbeError, SetupError  # noqa: E402

HOSTS = ["search.worldbank.org", "documents1.worldbank.org", "datacatalogapi.worldbank.org", "api.worldbank.org"]
HERE = {"search.worldbank.org": 200, "documents1.worldbank.org": 200, "datacatalogapi.worldbank.org": 429,
        "api.worldbank.org": 200}


class FakePlaces:
    def __init__(self, notebook=HERE, job=HERE, app=HERE):
        self.answers = {"notebook": notebook, "job": job, "app": app}
        self.asked = []

    def _answer(self, place, hosts):
        self.asked.append((place, sorted(hosts)))
        answer = self.answers[place]
        if isinstance(answer, Exception):
            raise answer
        return f"https://dbc-1.cloud.databricks.com/{place}/run/7", answer

    def from_here(self, hosts):
        return dict(HERE)

    def from_notebook(self, hosts):
        return self._answer("notebook", hosts)

    def from_job(self, hosts):
        return self._answer("job", hosts)

    def from_app(self, hosts):
        return self._answer("app", hosts)


def blocked(*hosts):
    answer = dict(HERE)
    for host in hosts:
        answer[host] = "no answer (URLError: [Errno 111] Connection refused)"
    return answer


@pytest.fixture
def place(tmp_path):
    # A probe's first run starts from the template, whatever results the committed document holds.
    dayone.ensure_document(tmp_path / "results.md", dayone.load_config())
    (tmp_path / "probe.env").write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\n"
                                        "DATABRICKS_TOKEN='dapi-x'\nDATABRICKS_WAREHOUSE_ID='wh1'\n")
    return tmp_path


def run(place, places):
    code = probe_hosts.main(["--env-file", str(place / "probe.env"), "--results", str(place / "results.md")],
                            service=places)
    return code, dayone.read_results(place / "results.md")["test-1"]


def test_every_place_reaching_every_host_passes_and_keeps_ingestion_in_databricks(place):
    places = FakePlaces()
    code, test1 = run(place, places)
    assert code == 0
    assert test1["Status"] == "passed"
    assert test1["Chosen path"].startswith("Default")
    assert [asked for asked, _ in places.asked] == ["notebook", "job", "app"]
    assert all(hosts == sorted(HOSTS) for _, hosts in places.asked)
    assert any(line.startswith("The job (https://dbc-1.cloud.databricks.com/job/run/7)") for line in test1["Evidence"])


def test_no_place_reaching_a_host_switches_ingestion_to_container_apps(place):
    nothing = blocked(*HOSTS)
    code, test1 = run(place, FakePlaces(nothing, nothing, nothing))
    assert code == 1
    assert test1["Status"] == "failed"
    assert test1["Chosen path"].startswith("Gap fill")
    assert "Container Apps" in test1["Chosen path"]


def test_a_job_that_reaches_every_host_keeps_ingestion_in_databricks_when_the_app_cannot(place):
    code, test1 = run(place, FakePlaces(app=blocked("documents1.worldbank.org")))
    assert code == 1
    assert test1["Status"] == "partly"
    assert test1["Chosen path"].startswith("Default")
    assert "documents1.worldbank.org" in test1["Result"]


def test_a_job_that_misses_a_host_switches_ingestion_to_container_apps(place):
    code, test1 = run(place, FakePlaces(job=blocked("search.worldbank.org")))
    assert test1["Status"] == "partly"
    assert test1["Chosen path"].startswith("Gap fill")


def test_a_403_where_this_computer_gets_through_counts_as_blocked(place):
    proxy = dict(HERE, **{"api.worldbank.org": 403})
    code, test1 = run(place, FakePlaces(notebook=proxy, job=proxy, app=proxy))
    assert test1["Status"] == "partly"
    assert "api.worldbank.org" in test1["Result"]


def test_a_place_that_cannot_run_is_recorded_with_its_reason(place):
    code, test1 = run(place, FakePlaces(app=SetupError("Using the browser sign-in failed: no profile strata")))
    assert code == 1
    assert test1["Status"] == "waiting"
    assert test1["Chosen path"].startswith("Default")
    assert any("no profile strata" in line for line in test1["Evidence"])



def test_two_places_that_cannot_run_are_asked_to_run_again_together(place):
    down = SetupError("Starting the job run failed: QUOTA_EXCEEDED")
    code, test1 = run(place, FakePlaces(job=down, app=down))
    assert code == 1
    assert test1["Status"] == "waiting"
    assert test1["Result"] == ("The notebook reached all four World Bank hosts. The job and the app could not run. "
                               "Run this probe again once every place can run.")


def test_both_results_count_the_hosts_that_dayone_toml_lists():
    config = dayone.load_config()
    config["hosts"] = HOSTS + ["projects.worldbank.org"]
    every = dict(HERE, **{"projects.worldbank.org": 200})
    passed = probe_hosts.check(FakePlaces(every, every, every), {}, config)
    assert passed.result == "The notebook, the job and the app each reached all five World Bank hosts."
    down = SetupError("Using the browser sign-in failed: no profile strata")
    waiting = probe_hosts.check(FakePlaces(every, every, down), {}, config)
    assert waiting.result.startswith("The notebook and the job reached all five World Bank hosts. ")


def test_a_job_that_cannot_start_keeps_the_default_path(place):
    quota = SetupError("Starting the job run failed: QUOTA_EXCEEDED")
    code, test1 = run(place, FakePlaces(job=quota, app=blocked("documents1.worldbank.org")))
    assert code == 1
    assert test1["Status"] == "partly"
    assert test1["Chosen path"].startswith("Default, until the job runs")
    assert "Container Apps" not in test1["Chosen path"]
    assert any("QUOTA_EXCEEDED" in line for line in test1["Evidence"])


def test_no_place_that_can_run_leaves_test_1_not_run(place):
    down = SetupError("Reading the token's user failed: 401 Unauthorized")
    code, test1 = run(place, FakePlaces(down, down, down))
    assert code == 1
    assert test1["Status"] == "not run"
    assert test1["Chosen path"].startswith("Default")
    assert any("401 Unauthorized" in line for line in test1["Evidence"])


def test_a_place_whose_run_fails_after_it_starts_counts_as_missing_every_host(place):
    code, test1 = run(place, FakePlaces(app=ProbeError("The app answered 500 at /dayone/reach.")))
    assert test1["Status"] == "partly"
    assert test1["Chosen path"].startswith("Default. The job reached every host")


def test_a_run_that_cannot_start_keeps_an_earlier_result(place):
    run(place, FakePlaces())
    down = SetupError("Reading the token's user failed: 401 Unauthorized")
    code, test1 = run(place, FakePlaces(down, down, down))
    assert code == 1
    assert test1["Status"] == "passed"
