# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Ask search_passages its benchmark question on the shared workspace, through AI Search, and check
that ICR P130164 paragraph 54 comes back in the top three: ticket 11's live search check.

Run it from the main checkout, after ops/documents/run_live.py has synced the index:

    uv run --script ops/documents/search_live.py --env-file .env

It calls the tool by name through the tool registry, as the app does, with the env file's own token
as the viewer: AI Search ranks the passages with a hybrid query and its reranker, and the SQL warehouse
returns them. It prints the top three, and exits 0 when the benchmark question's expected passages
are among them, 1 when they are not, and 2 when it could not ask.

It needs DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_TOKEN, AZURE_OPENAI_ENDPOINT and
AZURE_OPENAI_API_KEY. A service principal's sign-in has no token to act as a viewer, so it is not enough.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import yaml  # noqa: E402

from strata.lakehouse.engine import EngineError, WarehouseEngine, http_transport  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

QUESTION = "search-passages-icr-rebidding"
NEEDS = ("DATABRICKS_TOKEN", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/documents/search_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse, token and keys")
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

    from strata.dbx import Viewer
    from strata.tools import registry

    questions = yaml.safe_load((REPO / "evals" / "benchmark.yaml").read_text())["questions"]
    question = next(q for q in questions if q["id"] == QUESTION)
    arguments = {name: given for name, given in question["arguments"].items() if name != "as_of"}
    engine = WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"], http_transport(env["DATABRICKS_HOST"],
                                                                            env["DATABRICKS_TOKEN"]))
    context = registry.Context(engine=engine, viewer=Viewer(name="the env file's token",
                                                            token=env["DATABRICKS_TOKEN"]))
    for key in ("DATABRICKS_HOST", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"):
        os.environ.setdefault(key, env[key])  # the searcher reads them from the environment, as the app does
    try:
        result = registry.call(question["tool"], arguments, context)
    except (EngineError, LookupError, RuntimeError) as error:
        print(f"I could not ask search_passages: {error}")
        return 2
    top = [row["evidence_id"] for row in result["rows"][:3]]
    print(f"search_passages ranked with {result['search']['searcher']}: {result['search']['method']}.")
    for rank, row in enumerate(result["rows"][:3], 1):
        print(f"  {rank}. {row['evidence_id']}  {row['header']}")
    expected = question["expected"]["top_three_include"]
    found = [evidence for evidence in expected if evidence in top]
    print(f"{len(found)} of the {len(expected)} expected passages are in the top three.")
    return 0 if len(found) == len(expected) else 1


if __name__ == "__main__":
    sys.exit(main())
