# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "pypdf==6.21.2"]
# ///
"""Read the document slice into numbered passages on the shared workspace, with Route B, and sync
their AI Search index: tickets 11 and 18's live run.

Run it from the main checkout, after the deploy (ops/bundle/deploy.py) has made the strata catalog
and its tables, and after the nightly job has filled strata.gold.project:

    uv run --script ops/documents/run_live.py --env-file .env

It runs the same readers as the gate with the live adapters. First the plan reader
(src/strata/lakehouse/plans.py) reads each slice project's Procurement Plans. Then the passage reader
(src/strata/lakehouse/passages.py) counts the projects the slice criteria select from
strata.gold.project (config/slice.toml) and fetches their documents, with the showcase's, the demo
plan's and the stress shelf's, from the World Bank's hosts on this computer. Route A reads the published
text; every page the page router sends to Route B goes, one page at a time, to the layout parser that
config/models.toml names ([layout] parser: ai_parse_document until day-one test 3 chooses), under the
daily page cap both readers share (config/thresholds.toml, ingestion.daily_page_cap). Each passage is
scanned with Prompt Shields on the Foundry resource; only a passage whose header or text changed is
embedded again, with the deployment config/models.toml names for the embed role. The run writes bronze,
silver, strata.gold.passage and strata.ops on the warehouse, with the stress shelf's outcomes in
strata.ops.stress_shelf. Then it makes the Delta Sync index that config/models.toml's [search] table
names on the AI Search endpoint the env file names (AI_SEARCH_ENDPOINT), when it is missing, syncs it,
and waits until it holds every passage. A second run the same day parses no page it read.
It exits 0 when the index holds every passage, 1 when the run finished but the index did not catch
up in time, and 2 when it could not run or stopped before it finished, as when a World Bank host refuses
a PDF: the pages parsed before that are kept, and the next run goes on from there.

It needs DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, a token or a service principal, AI_SEARCH_ENDPOINT,
AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY. Then check the ground-truth queries on both engines, as
for every file marked for databricks, among them the slice's project count:

    uv run --script ops/bundle/check.py same-rows --env-file .env
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.config import load_layout_parser, load_models  # noqa: E402
from strata.lakehouse import passages, plans  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from strata.reader.documents import NotFetched  # noqa: E402
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

    from strata.fixture.record import fetch_url
    from strata.knowledge.embed import AzureOpenAIEmbeddings, EmbedError
    from strata.knowledge.search import AiSearchIndex
    from strata.knowledge.shields import PromptShields, ShieldError, content_safety_endpoint
    from strata.reader.documents import LiveDocuments
    from strata.reader.layout import PARSERS

    name = load_layout_parser()
    if name not in PARSERS:
        print(f"config/models.toml names the layout parser {name}, and Strata has no adapter for it. "
              f"Name one of these: {', '.join(sorted(PARSERS))}.")
        return 2
    workspace = LiveWorkspace(env)
    engine = workspace.engine()
    layout = PARSERS[name](engine, fetch=fetch_url,
                           upload=lambda path, data: workspace.w.files.upload(path, io.BytesIO(data), overwrite=True))

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
        projects = passages.default_projects(engine)
        for project_id in projects:
            plans.run(engine, LiveDocuments(), layout, project_id)
        report = passages.run(engine, LiveDocuments(), projects, shield=shield, embedder=embedder, layout=layout)
    except (EngineError, ShieldError, EmbedError) as error:
        print(f"The run stopped: {error}")
        return 2
    except (NotFetched, OSError) as error:  # urllib's errors and the Databricks SDK's are OSErrors
        print(f"The run stopped before it finished: {str(error).rstrip('.')}. The pages it parsed are kept, "
              "and the next run goes on from there.")
        return 2
    print(f"Run {report.run_id} counted {report.slice_projects} projects in the slice and read {report.documents} "
          f"documents into {report.passages} passages, with {report.scans} scans read by {layout.name}, and "
          f"{report.notice_passages} passages of notices' text. Prompt Shields scanned {report.scanned} new "
          f"passage texts and {model.deployment} embedded {report.embedded}.")
    passages.print_measures(engine, report.run_id)
    for outcome in report.shelf:
        shown = f"{outcome.count} of {outcome.denominator}" if outcome.count is not None else outcome.state
        print(f"  stress shelf {outcome.shelf_key}: {outcome.document_id or 'no document'}, {shown}")

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
