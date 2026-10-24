# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5", "pyyaml==6.0.3"]
# ///
"""Send five real passages that hold rule-like sentences through the live Foundry agent as tool results,
and fail on any Prompt Shields or content filter refusal: ticket 13's shield check.

Run it from the main checkout, after ops/agent/sync.py and after the gate has built the fixture database:

    uv run --script ops/agent/shields_live.py --env-file .env

The passages are listed in evals/shield_passages.toml. For each one, it asks search_passages on the fixture
database for the passage's own sentence, keeps that passage as the tool's result, asks the agent a
question, and answers the agent's tool call with that result. It prints how each one went, and exits 0
when all five reached the agent with no refusal, 1 when any was refused or never reached it, and 2 when it
could not run.

It needs FOUNDRY_PROJECT_ENDPOINT in the env file and the az command line signed in.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live import REPO, LiveSetupError, foundry_agent, load_env  # noqa: E402

from strata.agent import shields  # noqa: E402
from strata.config import load_agent  # noqa: E402
from strata.dbx import Viewer  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine, EngineError  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/agent/shields_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the Foundry project's endpoint")
    parser.add_argument("--database", type=Path, default=REPO / "data" / "out" / "fixture.duckdb",
                        help="the fixture database the gate builds")
    args = parser.parse_args(argv)
    today = dt.datetime.now(dt.UTC).date()
    try:
        env = load_env(args.env_file, ("FOUNDRY_PROJECT_ENDPOINT",))
        spec = load_agent("orchestrator")
        passages = shields.load_passages()
        with DuckDBEngine.open(args.database, read_only=True) as engine:
            results = {passage.evidence_id: shields.tool_result(passage, engine, Viewer(name="shield check"), today)
                       for passage in passages}
        outcomes = shields.check(passages, results, lambda: foundry_agent(env, spec), today)
    except (LiveSetupError, EngineError, LookupError) as error:
        print(f"I could not run the shield check: {error}")
        return 2
    for outcome in outcomes:
        print(f"{outcome.evidence_id}: {outcome.status}")
    print(shields.summary(outcomes), end="")
    return 0 if all(outcome.status == "passed" for outcome in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
