# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "pypdf==6.21.2"]
# ///
"""Propose lessons on the shared workspace: ticket 29's live run of the nightly job's propose_lessons task.

Run it from the main checkout, after the passage run (ops/documents/run_live.py) has read the slice's ICRs,
ICR Reviews and PPARs into strata.silver.passages:

    uv run --script ops/lessons/run_live.py --env-file .env

It runs the same task as the gate (strata.knowledge.lessons.propose) with the live adapters: Azure OpenAI's
Global Batch on the batch role's deployment (config/models.toml, gpt-5.4-nano), from AZURE_OPENAI_ENDPOINT and
AZURE_OPENAI_API_KEY, and the quote check, the review queue and the lessons verified measure on the warehouse.
A batch takes up to a day, so the first run sends the documents and a later run collects the answers; run it
again until it reports no batch still running. Once proposals are queued, it runs the review-proposed-lessons
workflow with the Foundry lesson review writer (config/agents.toml, lesson_review_writer, synced first with
`uv run --script ops/agent/sync.py --env-file .env --agent lesson_review_writer`), from the four FOUNDRY_ keys.
It exits 0 when the run finished and 2 when it could not run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.config import load_thresholds  # noqa: E402
from strata.knowledge.lessons import batch, propose, writer  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/lessons/run_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and keys")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    model = batch.from_environment(env)
    if model is None:
        print("The env file has no AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY, so I can't reach the batch model.")
        return 2
    from bundle_live import LiveWorkspace  # the Databricks SDK, which only the live run needs

    from strata.agent.runner import lesson_writer_from_environment

    engine = LiveWorkspace(env).engine()
    clock = lambda: dt.datetime.now(dt.UTC)  # noqa: E731
    run_id = f"lessons-{clock():%Y%m%dT%H%M%S}"
    try:
        changed = propose.run(engine, model, run_id, clock)
        agent = lesson_writer_from_environment(env)()
        notes = 0
        if agent is not None:
            most = int(load_thresholds().value("lesson_review.likely_repeats_max"))
            notes = writer.run(engine, lambda item, subject: agent, clock, most)
    except (EngineError, batch.BatchError) as error:
        print(f"The run stopped: {error}")
        return 2
    print(f"Run {run_id} changed {changed} rows and wrote {notes} lesson review notes."
          + ("" if agent is not None else " The env file names no Foundry project, so the review notes wait."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
