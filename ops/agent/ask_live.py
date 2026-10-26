# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["fastapi==0.161.1", "httpx==0.28.1", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "pyyaml==6.0.3", "azure-monitor-opentelemetry==1.8.11", "py3langid==0.3.0"]
# ///
"""Ask the showcase question through the live Foundry agent and check the answer: ticket 13's live check.

Run it from the main checkout, after ops/agent/sync.py, the live passage run (ops/documents/run_live.py)
and the deploy that made strata.ops.agent_runs (ops/bundle/deploy.py):

    uv run --script ops/agent/ask_live.py --env-file .env

It sends "Why were works contracts in P130164 advertised again?" through the same HTTP route and stream
the app runs, inside one traced span that goes to Application Insights. The agent is the Foundry agent,
and its tools run on the SQL warehouse as the env file's token. The run is written to
strata.ops.agent_runs with the same token. It then checks four things and prints each:

1. The answer passed checks 1 to 3: every number matched, every quote was on its page, every source
   came back, and no sentence was removed.
2. A kept sentence cites ICR P130164 paragraph 54 (strata.gold.passage:31525018/v1/54).
3. strata.ops.agent_runs holds the run, with its Application Insights trace id.
4. Application Insights holds that trace, which can take a few minutes.

It exits 0 when all four hold, 1 when one does not, and 2 when it could not run. It needs
FOUNDRY_PROJECT_ENDPOINT, DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_TOKEN and
APPLICATIONINSIGHTS_CONNECTION_STRING (with its ApplicationId) in the env file, and az signed in.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live import LiveSetupError, az, foundry_agent, load_env, warehouse_engine_for  # noqa: E402

from strata.agent import judge  # noqa: E402
from strata.agent.loop import answer_runner  # noqa: E402
from strata.agent.runs import RunLog  # noqa: E402
from strata.agent.scripted import load_cases  # noqa: E402
from strata.config import load_agent  # noqa: E402
from strata.lakehouse.engine import EngineError, WarehouseEngine, http_transport  # noqa: E402

NEEDS = ("FOUNDRY_PROJECT_ENDPOINT", "DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_TOKEN",
         "APPLICATIONINSIGHTS_CONNECTION_STRING")
CASE = "p130164-rebidding"
ICR_54 = "strata.gold.passage:31525018/v1/54"
RUN_ROW = "SELECT run_id, status, application_insights_trace_id FROM strata.ops.agent_runs WHERE run_id = :run_id"
TRACE = "union requests, dependencies, traces | where operation_Id == '{trace_id}' | take 5"
TRACE_ID = re.compile(r"[0-9a-f]{32}")  # an OpenTelemetry trace id, the only text the query above may hold


def trace_query(trace_id: str | None) -> str | None:
    """The Application Insights query for a trace, or None when the text is not a trace id."""
    return TRACE.format(trace_id=trace_id) if trace_id and TRACE_ID.fullmatch(trace_id) else None


def events(text: str) -> list[tuple[str, dict]]:
    parsed = []
    for block in text.strip().split("\n\n"):
        lines = [line for line in block.splitlines() if not line.startswith(":")]
        kind = next((line[7:] for line in lines if line.startswith("event: ")), None)
        data = next((json.loads(line[6:]) for line in lines if line.startswith("data: ")), None)
        if kind and data is not None:
            parsed.append((kind, data))
    return parsed


def ask(env: dict) -> tuple[list[tuple[str, dict]], str]:
    import httpx
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry import trace

    from strata.server.app import create_app

    configure_azure_monitor(connection_string=env["APPLICATIONINSIGHTS_CONNECTION_STRING"])
    case, spec = load_cases()[CASE], load_agent("orchestrator")
    engine_for = warehouse_engine_for(env)
    writer = RunLog(lambda: WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"],
                                            http_transport(env["DATABRICKS_HOST"], env["DATABRICKS_TOKEN"])))
    app = create_app(runner=answer_runner(lambda turn: foundry_agent(env, spec), engine_for), engine_for=engine_for,
                     runs=writer, judge=judge.from_environment(env))

    async def post() -> str:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.local", timeout=300) as client:
            response = await client.post("/api/ask", json={"question": case.question, "scope": case.scope})
            return response.text

    with trace.get_tracer("strata.ops.agent").start_as_current_span("POST /api/ask (ops/agent/ask_live.py)"):
        text = asyncio.run(post())
    trace.get_tracer_provider().force_flush(30000)
    return events(text), text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/agent/ask_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the Foundry endpoint, the workspace and the traces")
    args = parser.parse_args(argv)
    try:
        env = load_env(args.env_file, NEEDS)
        parsed, _ = ask(env)
    except (LiveSetupError, EngineError) as error:
        print(f"I could not ask the live agent: {error}")
        return 2
    done = dict(parsed).get("done", {})
    checks = next((data for kind, data in parsed if kind == "checks"), None)
    sentences = [data for kind, data in parsed if kind == "sentence"]
    removed = [data for kind, data in parsed if kind == "removed"]
    for kind, data in parsed:
        if kind in ("sentence", "removed", "error"):
            print(f"{kind}: {data.get('text') or data.get('sentence') or data.get('code')}")
    results = []
    passed = bool(checks) and not removed and checks["numbers"]["matched"] == checks["numbers"]["total"] \
        and checks["quotes"]["found"] == checks["quotes"]["total"] \
        and checks["sources"]["returned"] == checks["sources"]["total"]
    results.append((passed, f"1. Checks 1 to 3: {json.dumps(checks)}"))
    results.append((any(ICR_54 in sentence["evidence_ids"] for sentence in sentences),
                    f"2. A kept sentence cites {ICR_54}."))
    run_id, trace_id = done.get("run_id"), (done.get("trace_ids") or {}).get("application_insights")
    engine = WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"], http_transport(env["DATABRICKS_HOST"],
                                                                            env["DATABRICKS_TOKEN"]))
    rows = engine.run(RUN_ROW, {"run_id": run_id}).as_text() if run_id else []
    results.append((bool(rows) and rows[0][2] == trace_id and trace_id is not None,
                    f"3. strata.ops.agent_runs holds run {run_id}: {rows}"))
    parts = dict(part.split("=", 1) for part in env["APPLICATIONINSIGHTS_CONNECTION_STRING"].split(";") if "=" in part)
    found, deadline, query = [], time.monotonic() + 600, trace_query(trace_id)
    while query and parts.get("ApplicationId") and not found:
        answer = json.loads(az("rest", "--method", "post", "--resource", "https://api.applicationinsights.io",
                                "--url", f"https://api.applicationinsights.io/v1/apps/{parts['ApplicationId']}/query",
                                "--body", json.dumps({"query": query})) or "{}")
        found = ((answer.get("tables") or [{}])[0].get("rows")) or []
        if found or time.monotonic() > deadline:
            break
        time.sleep(30)
    results.append((bool(found), f"4. Application Insights holds operation {trace_id}: {found[:2]}"))
    for ok, line in results:
        print(("Holds. " if ok else "Does not hold. ") + line)
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
