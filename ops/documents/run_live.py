# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "pypdf==6.21.2"]
# ///
"""Read the first documents into numbered passages on the shared workspace and sync their AI Search
index: ticket 11's live run.

Run it from the main checkout, after the deploy (ops/bundle/deploy.py) has made the strata catalog
and its tables, and after the nightly job has filled strata.gold.project:

    uv run --script ops/documents/run_live.py --env-file .env

It runs the same passage reader as the gate (src/strata/lakehouse/passages.py) with the live
adapters. It fetches the showcase project's and the demo plan project's documents from the World
Bank's hosts on this computer, reads the first ingestion.passage_documents of them whose published
text Route A can read (config/thresholds.toml), scans each passage with Prompt Shields on the
Foundry resource, embeds each one, with its header, with the deployment config/models.toml names
for the embed role, and writes bronze, silver, strata.gold.passage and strata.ops on the warehouse.
Then it makes the Delta Sync index that config/models.toml's [search] table names on the AI Search
endpoint the env file names (AI_SEARCH_ENDPOINT), when it is missing, syncs it, and waits until it
holds every passage.
It exits 0 when the index holds every passage, 1 when the run finished but the index did not catch
up in time, and 2 when it could not run.

It needs DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, a token or a service principal, AI_SEARCH_ENDPOINT,
AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY. Then check the passage's ground-truth query on both
engines, as for every file marked for databricks:

    uv run --script ops/bundle/check.py same-rows --env-file .env
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.config import load_models  # noqa: E402
from strata.lakehouse import passages  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

NEEDS = ("AI_SEARCH_ENDPOINT", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
WAIT_MINUTES = 30


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/documents/run_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse, sign-in and keys")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    missing = [key for key in NEEDS if not env.get(key)]
    if missing:
        print(f"The env file has no value for {', '.join(missing)}. Run the setup wizard first "
              "(ops/wizard/strata-setup.sh).")
        return 2

    from bundle_live import LiveWorkspace  # the Databricks SDK, which only the live run needs
    from databricks.sdk.errors import NotFound

    from strata.knowledge.embed import AzureOpenAIEmbeddings, EmbedError
    from strata.knowledge.search import AiSearchIndex
    from strata.knowledge.shields import PromptShields, ShieldError, content_safety_endpoint
    from strata.reader.documents import LiveDocuments

    workspace = LiveWorkspace(env)
    engine = workspace.engine()

    def rest(method: str, path: str, body: dict | None = None) -> dict:
        try:
            return workspace.w.api_client.do(method, path, body=body) or {}
        except NotFound as error:
            raise LookupError(str(error)) from error

    model = load_models()["embed"]
    try:
        shield = PromptShields(content_safety_endpoint(env["AZURE_OPENAI_ENDPOINT"]), env["AZURE_OPENAI_API_KEY"])
        embedder = AzureOpenAIEmbeddings(env["AZURE_OPENAI_ENDPOINT"], env["AZURE_OPENAI_API_KEY"], model.deployment,
                                         model.dimensions)
        report = passages.run(engine, LiveDocuments(), shield=shield, embedder=embedder)
    except (EngineError, ShieldError, EmbedError) as error:
        print(f"The run stopped: {error}")
        return 2
    print(f"Run {report.run_id} read {report.documents} documents into {report.passages} passages. "
          f"{report.scans} more had no text Route A could read, so their pages wait for Route B. Prompt Shields "
          f"scanned {report.scanned} new passage texts and {model.deployment} embedded {report.embedded}.")
    passages.print_measures(engine, report.run_id)

    held = int(engine.run("SELECT count(*) AS n FROM strata.gold.passage").rows[0][0])
    index = AiSearchIndex(rest, env["AI_SEARCH_ENDPOINT"], model.dimensions)
    made = index.ensure(lambda sql: engine.run(sql))
    if not made:
        index.sync()
    deadline = time.monotonic() + WAIT_MINUTES * 60
    state = index.state()
    while not (state.ready and state.rows >= held) and time.monotonic() < deadline:
        time.sleep(30)
        state = index.state()
    print(f"The index {index.index} on {index.endpoint} holds {state.rows} of the {held} passages in "
          f"{index.table}{' and is ready' if state.ready else ''}. {state.message}".strip())
    return 0 if state.ready and state.rows >= held else 1


if __name__ == "__main__":
    sys.exit(main())
