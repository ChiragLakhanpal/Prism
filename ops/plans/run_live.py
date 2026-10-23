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
each chosen table page in the volume as a PDF of its own, runs ai_parse_document on the SQL warehouse,
and writes bronze, silver and strata.ops on the warehouse, under the daily page cap in
config/thresholds.toml. Then it runs the plan's ground-truth queries on the warehouse and checks that
they return the rows the files expect, as they do on the fixture.

Pass --check-only to skip the run and only check. It exits 0 when the checks pass, 1 when one fails,
and 2 when it could not run.
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

from strata.config import load_slice  # noqa: E402
from strata.lakehouse import ground_truth, plans  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

CHECKS = ("delay_from_first_published_planned_date.sql", "data_notes_actual_amount_zero.sql")


def check(engine) -> int:
    """The plan's ground-truth queries on the warehouse. Returns how many returned other rows."""
    failed = 0
    for name in CHECKS:
        case = ground_truth.read(REPO / "tests" / "ground_truth" / name)
        result = engine.run(case.sql, case.params)
        found = [result.columns, *result.as_text()]
        if found == case.expected:
            print(f"{name}: the SQL warehouse returned the rows the file expects.")
            continue
        failed += 1
        print(f"{name}: the SQL warehouse returned other rows.")
        for label, rows in (("The SQL warehouse", found), ("The file expects", case.expected)):
            print(f"  {label}:")
            for row in rows:
                print(f"    {', '.join(map(str, row))}")
    return failed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/plans/run_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and sign-in")
    parser.add_argument("--project", default=load_slice().demo_plan.project_id, help="the project, P156634 by default")
    parser.add_argument("--check-only", action="store_true", help="skip the run and only run the checks")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2

    from bundle_live import LiveWorkspace  # the Databricks SDK, which only the live run needs

    from strata.fixture.record import fetch_url
    from strata.reader.documents import LiveDocuments
    from strata.reader.layout import AiParseDocument

    workspace = LiveWorkspace(env)
    engine = workspace.engine()
    try:
        if not args.check_only:
            layout = AiParseDocument(
                engine, fetch=fetch_url,
                upload=lambda path, data: workspace.w.files.upload(path, io.BytesIO(data), overwrite=True))
            report = plans.run(engine, LiveDocuments(), layout, args.project)
            parsing = report.parsing
            print(f"Run {report.run_id} read {report.versions} plan versions of {args.project} and parsed "
                  f"{parsing.parsed} of the {parsing.waiting} pages waiting for {parsing.parser}, under a cap of "
                  f"{parsing.cap} pages a day. {report.versions_with_rows} versions have STEP rows.")
            if parsing.stopped_at:
                print(f"It stopped at the cap, at page {parsing.stopped_at[1]} of document {parsing.stopped_at[0]}. "
                      "Run it again tomorrow to read the rest.")
            for _, _, subject, name, _, count, denominator, _, _ in report.measures:
                print(f"  {subject} {name}: {count} of {denominator}")
        return 1 if check(engine) else 0
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
