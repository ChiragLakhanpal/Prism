# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0"]
# ///
"""Day-one test 1: Free Edition reaches the four World Bank hosts from a notebook, a job and the app.

Run it from the main checkout after the wizard:

    uv run --script ops/dayone/probe_hosts.py --env-file .env

It asks each host once from this computer, then from a notebook and a job on serverless compute,
then from a small app it deploys under the app name in dayone.toml. The app call uses the browser
sign-in the wizard saved for the Databricks command line. A host counts as reached from a place
when that place gets an HTTP answer; a 403 there while this computer gets another answer counts
as blocked. It writes test 1 in docs/day-one-results.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dayone  # noqa: E402
from dayone import Outcome, ProbeError, SetupError  # noqa: E402

NEEDS = ["DATABRICKS_HOST"]
PLACES = (("notebook", "from_notebook"), ("job", "from_job"), ("app", "from_app"))


def reached(answer, here) -> bool:
    return isinstance(answer, int) and not (answer == 403 and here != 403)


def describe(answers: dict, hosts) -> str:
    return "; ".join(f"{host} {answers.get(host, 'no answer')}" for host in hosts) + "."


def check(places, env: dict, config: dict) -> Outcome:
    hosts, test = config["hosts"], config["tests"]["1"]
    here = places.from_here(hosts)
    evidence = [f"This computer: {describe(here, hosts)}"]
    missed: dict[str, list[str]] = {}  # only the places that ran
    could_not_run: list[str] = []
    for label, method in PLACES:
        try:
            link, answers = getattr(places, method)(hosts)
        except SetupError as error:
            evidence.append(f"The {label} could not run, so it did not ask the hosts. {error}")
            could_not_run.append(label)
            continue
        except ProbeError as error:  # it ran and then failed, so it reached no host
            evidence.append(f"The {label} ran and then failed. {error}")
            missed[label] = list(hosts)
            continue
        evidence.append(f"The {label} ({link}): {describe(answers, hosts)}")
        missed[label] = [host for host in hosts if not reached(answers.get(host), here.get(host))]

    if not missed:
        return Outcome("not run", "None of the notebook, the job and the app could run, so the test did not "
                                  "run. The evidence says why.", evidence)
    not_run_text = f"The {' and the '.join(could_not_run)} could not run." if could_not_run else ""
    if "job" in could_not_run:
        path = f"Default, until the job runs. {test['default_path']}"
    elif missed["job"]:
        path = f"Gap fill. The job did not reach every host. {test['gap_fill']}"
    else:
        path = f"Default. The job reached every host, and ingestion runs as a job. {test['default_path']}"

    if not any(missed.values()):
        ran = " and the ".join(missed)
        reach_all = f"reached all {dayone.count_words(len(hosts), 'World Bank host')}"
        if could_not_run:
            return Outcome("waiting", f"The {ran} {reach_all}. {not_run_text} Run this probe "
                                      "again once every place can run.", evidence, path)
        return Outcome("passed", f"The notebook, the job and the app each {reach_all}.", evidence)
    if not could_not_run and all(len(missed[label]) == len(hosts) for label in missed):
        return Outcome("failed", "None of the notebook, the job and the app reached a World Bank host.", evidence,
                       path)
    gaps = " ".join(f"The {label} did not reach {', '.join(missed[label])}." for label in missed if missed[label])
    return Outcome("partly", f"Not every place reached every World Bank host. {gaps} {not_run_text}".strip(),
                   evidence, path)


class CannedPlaces:
    """Every place reaches every host, for --dry-run."""

    def __init__(self, env: dict, config: dict):
        self.link = f"{env['DATABRICKS_HOST']}/dry-run"

    def from_here(self, hosts):
        return {host: 200 for host in hosts}

    def _everywhere(self, hosts):
        return self.link, {host: 200 for host in hosts}

    from_notebook = from_job = from_app = _everywhere


def live(env: dict, config: dict):
    from live import LiveHosts
    return LiveHosts(env, config)


def main(argv: list[str] | None = None, service=None) -> int:
    return dayone.run_probe(1, argv, __doc__, NEEDS, live, CannedPlaces, check, service)


if __name__ == "__main__":
    sys.exit(main())
