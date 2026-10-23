# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "pypdf==6.21.2"]
# ///
"""Read a project's Procurement Plans into STEP rows on the shared workspace: ticket 08's live run.

Run it from the main checkout, after the deploy (ops/bundle/deploy.py) has made the strata catalog,
its tables and the volume strata.bronze.files:

    uv run --script ops/plans/run_live.py --env-file .env

It runs the same plan reader as the gate (src/strata/lakehouse/plans.py) with the live adapters: it
fetches the project's document list and plans from the World Bank's hosts on this computer, puts
each chosen table page in the volume as a PDF of its own, runs the layout parser that
config/models.toml names (ai_parse_document, on the SQL warehouse, unless day-one test 3 chose another),
and writes bronze, silver and strata.ops on the warehouse, under the daily page cap in
config/thresholds.toml. It exits 0 when the run finished and 2 when it could not run.

Then check the plan's ground-truth queries on both engines, as for every file marked for databricks:

    uv run --script ops/bundle/check.py same-rows --env-file .env
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.config import load_layout_parser, load_slice  # noqa: E402
from strata.lakehouse import plans  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from strata.reader.documents import NotFetched  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/plans/run_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and sign-in")
    parser.add_argument("--project", default=load_slice().demo_plan.project_id, help="the project, P156634 by default")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2

    from bundle_live import LiveWorkspace  # the Databricks SDK, which only the live run needs

    from strata.fixture.record import fetch_url
    from strata.reader.documents import LiveDocuments
    from strata.reader.layout import PARSERS

    name = load_layout_parser()
    if name not in PARSERS:
        print(f"config/models.toml names the layout parser {name}, and Strata has no adapter for it. "
              f"Name one of these: {', '.join(sorted(PARSERS))}.")
        return 2

    workspace = LiveWorkspace(env)
    engine = workspace.engine()
    try:
        layout = PARSERS[name](
            engine, fetch=fetch_url,
            upload=lambda path, data: workspace.w.files.upload(path, io.BytesIO(data), overwrite=True))
        report = plans.run(engine, LiveDocuments(), layout, args.project)
        parsing = report.parsing
        print(f"Run {report.run_id} read {report.versions} plan versions of {args.project} and parsed "
              f"{parsing.parsed} of the {parsing.waiting} pages waiting for {parsing.parser}, under a cap of "
              f"{parsing.cap} pages a day. {report.versions_with_rows} versions have STEP rows.")
        if parsing.failed:
            document, page = parsing.failed[0]
            print(f"The layout parser could not read {len(parsing.failed)} of them. The first was page {page} "
                  f"of document {document}. strata.ops.parse_failures says why. A run on a later day, in UTC, "
                  "tries them again.")
        if parsing.stopped_at:
            print(f"It stopped at the cap, at page {parsing.stopped_at[1]} of document {parsing.stopped_at[0]}. "
                  "Run it again tomorrow to read the rest.")
        plans.print_measures(report)
        return 0
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2
    except (NotFetched, OSError) as error:  # urllib's errors and the Databricks SDK's are OSErrors
        print(f"The run stopped before it finished: {str(error).rstrip('.')}. The pages it parsed are kept, "
              "and the next run goes on from there.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
