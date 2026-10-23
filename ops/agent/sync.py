# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5", "pyyaml==6.0.3"]
# ///
"""Make the Foundry agent strata-orchestrator and its guardrail match the repo: ticket 13's agent sync.

Run it from the main checkout, after the wizard, whenever the agent's instructions, its model, a tool or
the guardrail changes:

    uv run --script ops/agent/sync.py --env-file .env
    uv run --script ops/agent/sync.py --env-file .env --check

It builds the agent's definition from config/agents.toml, its instructions file, config/models.toml and
the tool registry, and its guardrail (content filters, and Prompt Shields on the question and on tool
results) as an RAI policy on the Foundry resource. It prints what differs from what Foundry holds, with a
diff of the instructions, then updates the guardrail and makes a new version of the agent. A second run
reports no difference. With --check it only reports. It exits 0 when Foundry matches the repo, 1 when
--check found a difference, and 2 when it could not run.

It needs FOUNDRY_PROJECT_ENDPOINT in the env file and the az command line signed in to the subscription
that holds the Foundry resource named in ops/dayone/dayone.toml.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live import LiveSetupError, foundry_project, load_env  # noqa: E402

from strata.agent import sync  # noqa: E402
from strata.agent.foundry import FoundryError  # noqa: E402
from strata.config import load_agent  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/agent/sync.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the Foundry project's endpoint")
    parser.add_argument("--check", action="store_true", help="report the difference and change nothing")
    parser.add_argument("--agent", default="orchestrator", help="the agent's key in config/agents.toml")
    args = parser.parse_args(argv)
    try:
        env = load_env(args.env_file, ("FOUNDRY_PROJECT_ENDPOINT",))
        report = sync.run(foundry_project(env, load_agent(args.agent)), args.agent, apply=not args.check)
    except (LiveSetupError, FoundryError) as error:
        print(f"I could not sync the agent: {error}")
        return 2
    print(report.text(), end="")
    return 1 if args.check and report.differences else 0


if __name__ == "__main__":
    sys.exit(main())
