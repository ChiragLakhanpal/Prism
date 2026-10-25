# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5", "pyyaml==6.0.3", "fastapi==0.161.1",
#                 "httpx==0.28.1", "opentelemetry-api==1.45.1"]
# ///
"""Re-record every scripted case from the live Foundry agent, and print the change as a diff: ticket 13's
recording command.

Run it from the main checkout, after ops/agent/sync.py and after the live passage run
(ops/documents/run_live.py), so the agent and the passages it cites are on the workspace:

    uv run --script ops/agent/record.py --env-file .env

It asks each recording's question in tests/fixtures/agent/cases.toml through the same answer loop the app
runs, with the Foundry agent, and with the tools on the SQL warehouse as the env file's token. It writes
each recording over its file in tests/fixtures/agent/recorded and prints a unified diff of what changed,
with the verifier's counts on each answer. Then review it with git diff tests/fixtures/agent, run the gate
(the scripted cases replay the new recordings on the fixture), and commit them. It exits 0 when every
recording was made, and 2 when it could not run.

With --writers it re-records the draft writers' cases in tests/fixtures/agent/writers.toml instead, such as
the review notes on the NWWDA plan (ticket 35): each kind's workflow reads its facts on the SQL warehouse,
and its Foundry writer (after ops/agent/sync.py --agent review_notes_writer) writes the answer.

With --packages it re-records the package reader's cases in tests/fixtures/agent/packages.toml instead
(ticket 15): the Foundry package reader (after ops/agent/sync.py --agent package_reader) reads each sentence
with the package form's fields, as the plan-a-package workflow sends it.

With --criteria it re-records the criteria reader's cases in tests/fixtures/agent/criteria.toml instead
(ticket 31): the Foundry criteria reader (after ops/agent/sync.py --agent criteria_reader) reads each pasted
text with the item registry's items, as the check-your-criteria workflow sends it.

With --judge it re-records the judge of the verifier's check 4 instead (ticket 24): it replays every scripted
case in tests/fixtures/agent/cases.toml through the answer stream, and every writer case in writers.toml through
its draft workflow's six checks, with the tools on the SQL warehouse, and keeps the answer of config/models.toml's
draft role for each case that asks the judge, in tests/fixtures/agent/judged. Run it after the plain run, since the judge is asked about the recorded answers.
It also needs AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.

It needs FOUNDRY_PROJECT_ENDPOINT, DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID and DATABRICKS_TOKEN in the env
file, and the az command line signed in.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live import REPO, LiveSetupError, foundry_agent, load_env, warehouse_engine_for  # noqa: E402

from strata.agent import judge, record  # noqa: E402
from strata.agent.loop import AgentError  # noqa: E402
from strata.agent.scripted import CRITERIA_CASES, PACKAGE_CASES, WRITER_CASES, load_cases  # noqa: E402
from strata.config import load_agent, load_draft_kinds  # noqa: E402
from strata.dbx import Viewer  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402

NEEDS = ("FOUNDRY_PROJECT_ENDPOINT", "DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_TOKEN")
JUDGE_NEEDS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/agent/record.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the Foundry endpoint and the workspace's token")
    parser.add_argument("--writers", action="store_true",
                        help="re-record the draft writers' cases in tests/fixtures/agent/writers.toml instead")
    parser.add_argument("--packages", action="store_true",
                        help="re-record the package reader's cases in tests/fixtures/agent/packages.toml instead")
    parser.add_argument("--criteria", action="store_true",
                        help="re-record the criteria reader's cases in tests/fixtures/agent/criteria.toml instead")
    parser.add_argument("--judge", action="store_true",
                        help="re-record check 4's judge for the cases in tests/fixtures/agent/cases.toml instead")
    args = parser.parse_args(argv)
    try:
        env = load_env(args.env_file, NEEDS + (JUDGE_NEEDS if args.judge else ()))
        viewer = Viewer(name="the env file's token", token=env["DATABRICKS_TOKEN"])
        if args.criteria:
            spec = load_agent("criteria_reader")
            done = record.record_criteria(load_cases(CRITERIA_CASES), lambda: foundry_agent(env, spec),
                                          warehouse_engine_for(env), viewer)
        elif args.judge:
            live_judge = judge.from_environment(env)
            done = record.record_judged(load_cases() | load_cases(WRITER_CASES), live_judge, warehouse_engine_for(env))
        elif args.packages:
            spec = load_agent("package_reader")
            done = record.record_packages(load_cases(PACKAGE_CASES), lambda: foundry_agent(env, spec),
                                          warehouse_engine_for(env), viewer)
        elif args.writers:
            cases = load_cases(WRITER_CASES)
            kinds = load_draft_kinds().kinds
            specs = {case.recording: load_agent(kinds[case.request["kind"]].agent) for case in cases.values()}
            spec = next(iter(specs.values()))  # one writer kind so far: review notes
            done = record.record_writers(cases, lambda: foundry_agent(env, spec), warehouse_engine_for(env), viewer)
        else:
            spec = load_agent("orchestrator")
            done = record.record_all(load_cases(), lambda: foundry_agent(env, spec), warehouse_engine_for(env), viewer)
    except (LiveSetupError, AgentError, EngineError, judge.JudgeError) as error:
        print(f"I could not re-record the scripted cases: {error}")
        return 2
    print(record.report_text(done, REPO), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
