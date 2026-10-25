# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["fastapi==0.161.1", "httpx==0.28.1", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "pyyaml==6.0.3", "opentelemetry-api==1.45.1"]
# ///
"""Ask every must-refuse question of the live Foundry agent and check each refusal: ticket 24's live check.

Run it from the main checkout, after ops/agent/sync.py has synced the orchestrator's instructions with their
"What you turn down" section:

    uv run --script ops/agent/refuse_live.py --env-file .env

It asks each question of kind refusals in evals/benchmark.yaml through the same HTTP route and stream the app
runs, with the Foundry agent, its tools on the SQL warehouse as the env file's token, and the verifier's
judge (config/models.toml's draft role) when the env file names Azure OpenAI. For each it checks what the
offline gate checks of the scripted cases (strata.agent.refusals.refusal_problems): the refusal carries the
question's key and is not partial, no sentence is shown about the request, and the stream holds no email
address and none of the recorded notices' contact details. It prints one line per question and exits 0 when
every refusal holds, 1 when one does not, and 2 when it could not run. It needs FOUNDRY_PROJECT_ENDPOINT,
DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID and DATABRICKS_TOKEN in the env file, and az signed in.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402
from live import REPO, LiveSetupError, foundry_agent, load_env, warehouse_engine_for  # noqa: E402

from strata.agent import judge  # noqa: E402
from strata.agent.loop import answer_runner  # noqa: E402
from strata.agent.refusals import refusal_problems  # noqa: E402
from strata.config import load_agent  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402

NEEDS = ("FOUNDRY_PROJECT_ENDPOINT", "DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_TOKEN")


def recorded_contacts() -> set[str]:
    """The contact details the recorded notices hold, which ingestion strips and no answer may show."""
    values = set()
    for path in (REPO / "data" / "fixture" / "recorded" / "api" / "notices").glob("*.json"):
        for notice in json.loads(path.read_text())["response"].get("procnotices", []):
            values |= {(notice.get(field) or "").strip() for field in ("contact_email", "contact_phone_no")}
    return {value for value in values if len(value) >= 5}


def events(text: str) -> list[tuple[str, dict]]:
    parsed = []
    for block in text.strip().split("\n\n"):
        lines = [line for line in block.splitlines() if not line.startswith(":")]
        kind = next((line[7:] for line in lines if line.startswith("event: ")), None)
        data = next((json.loads(line[6:]) for line in lines if line.startswith("data: ")), None)
        if kind and data is not None:
            parsed.append((kind, data))
    return parsed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/agent/refuse_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the Foundry endpoint and the workspace's token")
    args = parser.parse_args(argv)
    try:
        env = load_env(args.env_file, NEEDS)
    except LiveSetupError as error:
        print(f"I could not ask the live agent: {error}")
        return 2

    import httpx

    from strata.server.app import create_app

    spec, engine_for = load_agent("orchestrator"), warehouse_engine_for(env)
    app = create_app(runner=answer_runner(lambda turn: foundry_agent(env, spec), engine_for), engine_for=engine_for,
                     judge=judge.from_environment(env))
    questions = [question for question in yaml.safe_load((REPO / "evals" / "benchmark.yaml").read_text())["questions"]
                 if question["kind"] == "refusals"]
    contacts = recorded_contacts()

    async def ask(question: dict) -> str:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.local", timeout=300) as client:
            response = await client.post("/api/ask", headers={"X-Forwarded-User": "refuse-live@strata"}, json={
                "question": question["question"], "scope": question.get("scope"), "asof": question.get("as_of")})
            return response.text

    failed = 0
    for question in questions:
        try:
            text = asyncio.run(ask(question))
        except EngineError as error:
            print(f"I could not ask the live agent: {error}")
            return 2
        problems = refusal_problems(question["expected"]["refusal"], events(text), text, contacts)
        failed += bool(problems)
        print(("Does not hold. " if problems else "Holds. ") + f"{question['id']}: " + (" ".join(problems) or
              f"refused with {question['expected']['refusal']}."))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
