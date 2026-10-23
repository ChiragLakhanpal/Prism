# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0"]
# ///
"""Day-one test 2: Free Edition reaches the Foundry and Azure OpenAI endpoints from a job.

Run it from the main checkout after the wizard:

    uv run --script ops/dayone/probe_azure_from_job.py --env-file .env

It runs a small Python file as a job on serverless compute. The job asks the Foundry project
endpoint and the Azure OpenAI model list without a key, because any HTTP answer shows the network
allows the call. Then it lists the models with the key it reads from the app's secret scope, so
the key never travels with the job. It writes test 2 in docs/day-one-results.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dayone  # noqa: E402
from dayone import Outcome, ProbeError, SetupError  # noqa: E402

NEEDS = ["DATABRICKS_HOST", "FOUNDRY_PROJECT_ENDPOINT", "AZURE_OPENAI_ENDPOINT"]


def check(job, env: dict, config: dict) -> Outcome:
    settings = {"foundry_endpoint": env["FOUNDRY_PROJECT_ENDPOINT"], "openai_endpoint": env["AZURE_OPENAI_ENDPOINT"],
                "scope": config["names"]["secret_scope"]}
    try:
        link, answers = job.from_job(settings)
    except SetupError as error:
        return dayone.not_run(error)
    except ProbeError as error:
        return Outcome("failed", "The job failed, so it did not reach Foundry or Azure OpenAI.", [str(error)])
    foundry, openai, with_key = answers.get("foundry"), answers.get("openai"), answers.get("openai_with_key")
    evidence = [f"Job run: {link}",
                f"Foundry project endpoint, asked without a key: {foundry}.",
                f"Azure OpenAI model list, asked without a key: {openai}.",
                f"Azure OpenAI model list, asked with the key from the secret scope: {with_key}."]
    silent = [name for name, answer in (("Foundry", foundry), ("Azure OpenAI", openai)) if not isinstance(answer, int)]
    if silent:
        return Outcome("failed", f"The job got no answer from {' or '.join(silent)}.", evidence)
    if with_key == 200:
        return Outcome("passed", "The job reached Foundry and Azure OpenAI, and Azure OpenAI accepted the key.",
                       evidence)
    default = config["tests"]["2"]["default_path"]
    if isinstance(with_key, int):
        problem = f"Azure OpenAI answered {with_key} to the key from the secret scope, so fix that key."
    else:
        problem = "The job could not read the key from the secret scope, so save it there again with the wizard."
    return Outcome("partly", f"Both endpoints answered the job. {problem}", evidence,
                   f"Default. The network allows the calls from a job. {problem} {default}")


class CannedJob:
    """A job that reaches both endpoints, for --dry-run."""

    def __init__(self, env: dict, config: dict):
        self.link = f"{env['DATABRICKS_HOST']}/dry-run"

    def from_job(self, settings):
        return self.link, {"foundry": 401, "openai": 401, "openai_with_key": 200}


def live(env: dict, config: dict):
    from live import LiveAzureFromJob
    return LiveAzureFromJob(env, config)


def main(argv: list[str] | None = None, service=None) -> int:
    return dayone.run_probe(2, argv, __doc__, NEEDS, live, CannedJob, check, service)


if __name__ == "__main__":
    sys.exit(main())
