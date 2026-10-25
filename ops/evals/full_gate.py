"""The full gate on the workspace (ticket 33; docs/PLAN.md section 10): one command for the offline gate, the Genie
benchmark, the benchmark through the live answer contract and Foundry evaluations.

Run it from the main checkout, after the bundle deploy (ops/bundle/deploy.py), the space deploy
(ops/genie/deploy_space.py) and the agent sync (ops/agent/sync.py):

    uv run --with azure-identity python ops/evals/full_gate.py --env-file .env

It needs DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID, FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_TENANT_ID,
AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in the env file, GENIE_SPACE_ID for the Genie benchmark, and az
signed in for the agent. In order (strata.evals.full_gate):

1. It checks the benchmark file, and stops naming what it lacks.
2. It runs the offline gate, .githooks/pre-commit. When that fails, nothing live runs.
3. The Genie benchmark: each Genie question through the space GENIE_SPACE_ID names, as the env file's token,
   against its ground-truth SQL on the SQL warehouse.
4. Every question in evals/benchmark.yaml through /api/ask with the Foundry agent, its tools as a viewer that
   carries the env file's token (the SQL warehouse, Genie and AI Search), and the verifier's judge.
5. Foundry evaluations of those answers. A browser opens for a Microsoft Entra sign-in to FOUNDRY_TENANT_ID: the
   project key gets 403 from the evaluations API, and the tenant blocks device-code sign-in.
6. It appends every result to strata.ops.evaluation_result under one run id, prints each tally against its target
   (config/thresholds.toml), and exits 1 naming each gap when a target is missed, 0 when every target is met, and
   2 when it could not run.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

NEEDS = ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID", "FOUNDRY_PROJECT_ENDPOINT",
         "FOUNDRY_TENANT_ID", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
# What the tools read from the process environment, as the App's app.yaml gives them: ask_genie the workspace and
# its Genie space, search_passages the workspace and Azure OpenAI.
TOOL_SETTINGS = ("DATABRICKS_HOST", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "GENIE_SPACE_ID")
FOUNDRY_SCOPE = "https://ai.azure.com/.default"


def entra_browser_token(tenant: str):
    """A Microsoft Entra token for Foundry from a browser sign-in to the tenant, kept for 45 minutes."""
    try:
        from azure.identity import InteractiveBrowserCredential
    except ImportError as error:
        raise RuntimeError("The Foundry sign-in needs azure-identity. Run the command with "
                           "uv run --with azure-identity, as its docstring says.") from error
    credential, lock, held = InteractiveBrowserCredential(tenant_id=tenant), threading.Lock(), {"until": 0.0}

    def token() -> str:
        with lock:
            if time.monotonic() >= held["until"]:
                held["token"] = credential.get_token(FOUNDRY_SCOPE).token
                held["until"] = time.monotonic() + 45 * 60
            return held["token"]
    return token


def agent_live():
    """ops/agent/live.py, the agent's live helpers, by its path: ops/dayone has a live.py too."""
    import importlib.util

    if "strata_agent_live" not in sys.modules:
        spec = importlib.util.spec_from_file_location("strata_agent_live", REPO / "ops" / "agent" / "live.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["strata_agent_live"] = module
        spec.loader.exec_module(module)
    return sys.modules["strata_agent_live"]


def stages_for(env: dict):
    live = agent_live()
    foundry_agent, warehouse_engine_for = live.foundry_agent, live.warehouse_engine_for

    from strata.agent import judge
    from strata.agent.refusals import restricted_values
    from strata.config import load_agent, load_evaluations, load_models, load_thresholds
    from strata.evals import answer_benchmark, foundry_evaluation, full_gate, genie_benchmark
    from strata.genie import space as genie_space
    from strata.genie.client import GenieClient, Waits
    from strata.lakehouse.engine import WarehouseEngine, http_transport

    thresholds, evaluations = load_thresholds(), load_evaluations()
    transport = http_transport(env["DATABRICKS_HOST"], env["DATABRICKS_TOKEN"])
    warehouse = WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"], transport)
    engine_for, spec = warehouse_engine_for(env), load_agent("orchestrator")
    space_id = (env.get("GENIE_SPACE_ID") or "").strip()
    # The env file's token as the viewer for this run only: the tools the agent calls and the reference answers
    # sign their calls with it, and no module global holds it (CLAUDE.md rule 7).
    viewer = dataclasses.replace(answer_benchmark.GATE, token=env["DATABRICKS_TOKEN"])

    def genie():
        client = GenieClient(transport, space_id, env["DATABRICKS_WAREHOUSE_ID"], Waits.from_thresholds(thresholds))
        return genie_benchmark.run(client, warehouse, genie_space.load().benchmarks)

    def answers(questions):
        return answer_benchmark.run(questions, lambda turn: foundry_agent(env, spec), engine_for,
                                    judge=judge.from_environment(env),
                                    restricted=restricted_values(REPO / "data" / "fixture" / "recorded" / "api"),
                                    viewer=viewer)

    def foundry(items):
        client = foundry_evaluation.FoundryEvaluations(env["FOUNDRY_PROJECT_ENDPOINT"], evaluations.api_version,
                                                       entra_browser_token(env["FOUNDRY_TENANT_ID"]))
        return foundry_evaluation.evaluate(
            client, items, evaluations, load_models()[evaluations.judge_role].deployment, "strata-full-gate",
            float(thresholds.value("foundry_evaluation.poll_seconds")),
            float(thresholds.value("foundry_evaluation.wait_seconds")))

    def offline_gate() -> int:
        return subprocess.run([str(REPO / ".githooks" / "pre-commit")], cwd=REPO).returncode

    return full_gate.Stages(offline_gate=offline_gate, answers=answers, genie=genie if space_id else None,
                            foundry=foundry), warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ops/evals/full_gate.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's env file, which the wizard filled. That file is the default.")
    args = parser.parse_args(argv)
    import dayone

    path = args.env_file or dayone.default_env_path()
    if not path.is_file():
        print(f"There is no env file at {path}. {dayone.WIZARD_FIRST}")
        return 2
    env = dayone.load_env(path)
    missing = dayone.missing_keys(env, list(NEEDS))
    if missing:
        print(f"{path} has no value for {', '.join(missing)}. {dayone.WIZARD_FIRST}")
        return 2
    from strata.evals import benchmark, full_gate

    # The tools read these from the environment, as the App's app.yaml gives them. update, not setdefault, so
    # ask_genie asks the same space as the Genie benchmark stage.
    os.environ.update({key: env[key] for key in TOOL_SETTINGS if env.get(key)})
    stages, store = stages_for(env)
    return full_gate.run(benchmark.load(), stages, store).exit_code


if __name__ == "__main__":
    sys.exit(main())
