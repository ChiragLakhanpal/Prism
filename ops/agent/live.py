"""What the agent's live commands share: the env file, the Azure sign-in, the Foundry agent and project, and
the SQL warehouse as the env file's token.

The commands run from the main checkout after the setup wizard (ops/wizard/strata-setup.sh):

- ops/agent/sync.py      make the Foundry agent and its guardrail match the repo
- ops/agent/record.py    re-record every scripted case from the live agent
- ops/agent/ask_live.py  ask the showcase question through the live agent and check the answer
- ops/agent/shields_live.py  send five real passages that hold rule-like sentences through the live agent

Azure tokens come from the az command line the wizard signed in: one for the Foundry project's data plane,
and one for Azure Resource Manager, which keeps the guardrail's RAI policy. The tools run on the SQL
warehouse with the env file's Databricks token, as that person, the way the app runs them as each viewer.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402

from strata.agent.foundry import FoundryAgent, FoundryProject, account_id  # noqa: E402
from strata.config import AgentSpec  # noqa: E402

FOUNDRY_RESOURCE = "https://ai.azure.com"
ARM_RESOURCE = "https://management.azure.com"


class LiveSetupError(Exception):
    """The env file or the Azure sign-in is not ready, with what to do about it."""


def load_env(env_file: str | None, needs: tuple[str, ...]) -> dict[str, str]:
    path = Path(env_file) if env_file else dayone.default_env_path()
    if not path.is_file():
        raise LiveSetupError(f"There is no env file at {path}. {dayone.WIZARD_FIRST}")
    env = dayone.load_env(path)
    missing = dayone.missing_keys(env, list(needs))
    if missing:
        raise LiveSetupError(f"{path} has no value for {', '.join(missing)}. {dayone.WIZARD_FIRST}")
    return env


def az(*args: str) -> str:
    try:
        done = subprocess.run(["az", *args], capture_output=True, text=True, timeout=120)
    except OSError as error:
        raise LiveSetupError(f"The az command line could not start: {error}. {dayone.WIZARD_FIRST}") from error
    if done.returncode != 0:
        reason = (done.stderr.strip().splitlines() or ["no message"])[-1]
        raise LiveSetupError(f"az {args[0]} {args[1]} failed: {reason[:300]}. Sign in with az login.")
    return done.stdout.strip()


def az_token(resource: str):
    """A token for one Azure resource from the signed-in az command line, kept for 45 minutes."""
    lock, held = threading.Lock(), {"token": None, "until": 0.0}

    def token() -> str:
        with lock:
            if held["token"] is None or time.monotonic() >= held["until"]:
                held["token"] = az("account", "get-access-token", "--resource", resource, "--query", "accessToken",
                                   "-o", "tsv")
                held["until"] = time.monotonic() + 45 * 60
            return held["token"]
    return token


def foundry_project(env: dict, spec: AgentSpec) -> FoundryProject:
    names = dayone.load_config()["names"]
    subscription = az("account", "show", "--query", "id", "-o", "tsv")
    return FoundryProject(env["FOUNDRY_PROJECT_ENDPOINT"], spec, az_token(FOUNDRY_RESOURCE), az_token(ARM_RESOURCE),
                          account_id(subscription, names["resource_group"], names["foundry_resource"]))


def foundry_agent(env: dict, spec: AgentSpec) -> FoundryAgent:
    return FoundryAgent(env["FOUNDRY_PROJECT_ENDPOINT"], spec, az_token(FOUNDRY_RESOURCE))


def warehouse_engine_for(env: dict):
    """The SQL warehouse with the env file's token, opened for each tool call as the app opens it for a viewer."""
    from strata.lakehouse.engine import WarehouseEngine, http_transport

    @contextmanager
    def engine_for(viewer):
        yield WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"], http_transport(env["DATABRICKS_HOST"],
                                                                             env["DATABRICKS_TOKEN"]))
    return engine_for


def answer_app(env: dict, **options):
    """The app the live checks ask through, as the deployed App answers: the Foundry agent, its tools on the SQL
    warehouse as the env file's token, the verifier's judge when the env file names Azure OpenAI, and the env file
    as the settings every tool reads (search_passages's Azure OpenAI endpoint and key and the workspace's host), so
    one load of the env file serves them all (ticket 66). options go to create_app, such as runs."""
    from strata.agent import judge
    from strata.agent.loop import answer_runner
    from strata.config import load_agent
    from strata.server.app import create_app

    spec, engine_for = load_agent("orchestrator"), warehouse_engine_for(env)
    return create_app(runner=answer_runner(lambda turn: foundry_agent(env, spec), engine_for, environ=env),
                      engine_for=engine_for, judge=judge.from_environment(env), environ=env, **options)


def viewer_headers(env: dict, user: str | None = None) -> dict[str, str]:
    """The headers the Databricks Apps proxy forwards for a viewer, here the env file's token holder: their token,
    so the tools that call the workspace as the viewer (search_passages on AI Search) do so as that person, and the
    user id the run log keeps, when one is given."""
    return {"X-Forwarded-Access-Token": env["DATABRICKS_TOKEN"], **({"X-Forwarded-User": user} if user else {})}
