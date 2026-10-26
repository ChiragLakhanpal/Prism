# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3"]
# ///
"""Deploy Strata's catalog and nightly job to the shared workspace, and say what changed.

Run it from the main checkout after the wizard:

    uv run --script ops/bundle/deploy.py --env-file .env

It needs the Databricks CLI 0.287.0 or later on the path. It does these things, in order:

1. It lists what the workspace holds: the strata catalog, its schemas, the volume, the tables, the
   grants, the nightly job that bundle/nightly.yml names and the dashboard, and also fairshare's
   catalog.
2. It runs `databricks bundle deploy`, which creates or updates the catalog, the bronze, silver,
   gold and ops schemas, the bronze files volume, the read grants, the nightly job and the AI/BI
   dashboard that src/strata/dashboard defines (bundle/dashboard.yml), with the env file's SQL
   warehouse for the dashboard's queries.
3. It creates the tables from src/strata/lakehouse/tables on the SQL warehouse. Each one is
   CREATE TABLE IF NOT EXISTS, so a table that holds rows is never replaced. Then it creates or
   replaces the metric views the Genie space reads, from src/strata/lakehouse/metric_views (ticket 33),
   which hold no rows.
4. It lists the same things again and prints what changed. A second run prints "No changes."
   It also checks that fairshare's catalog lists the same as before, and fails if it does not.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
from strata.lakehouse import bundle, catalog, nightly  # noqa: E402
from strata.lakehouse.catalog import CatalogError  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

FAIRSHARE = "fairshare"
KINDS = {"catalog": "The catalog", "schemas": "The schema", "volumes": "The volume", "tables": "The table",
         "grants": "The grants on", "jobs": "The job", "dashboards": "The dashboard"}


def dashboard_name() -> str:
    """The dashboard's name in the workspace, as bundle/dashboard.yml gives it."""
    return bundle.load().resources("dashboards")["strata_dashboard"]["display_name"]


def flatten(listing: dict | None, job: dict | None = None, dashboard: dict | None = None) -> dict:
    """One entry per thing the deploy can change, keyed by its kind and full name."""
    if not listing:
        found = {}
    else:
        name = listing["catalog"]["name"]
        found = {("catalog", name): listing["catalog"]}
        for kind in ("schemas", "volumes", "tables"):
            found |= {(kind, f"{name}.{item}"): value for item, value in listing.get(kind, {}).items()}
        found |= {("grants", securable): value for securable, value in listing.get("grants", {}).items()}
    if job:
        found[("jobs", job["name"])] = job
    if dashboard:
        found[("dashboards", dashboard["name"])] = dashboard
    return found


def changes(before: dict, after: dict) -> list[str]:
    """One sentence per thing that is new, gone or changed, in the order of KINDS."""
    lines = []
    order = list(KINDS)
    for kind, name in sorted(set(before) | set(after), key=lambda key: (order.index(key[0]), key[1])):
        label, plural = KINDS[kind], kind == "grants"
        if (kind, name) not in before:
            lines.append(f"{label} {name} {'are' if plural else 'is'} new.")
        elif (kind, name) not in after:
            lines.append(f"{label} {name} {'are' if plural else 'is'} gone.")
        elif before[(kind, name)] != after[(kind, name)]:
            lines.append(f"{label} {name} changed.")
    return lines


def summary(listing: dict) -> str:
    counts = [dayone.count_words(len(listing.get(kind, {})), noun)
              for kind, noun in (("schemas", "schema"), ("tables", "table"), ("volumes", "volume"))]
    return f"{counts[0]}, {counts[1]} and {counts[2]}"


def deploy(workspace, fairshare: str = FAIRSHARE) -> int:
    job, board = nightly.job_name(), dashboard_name()
    before = flatten(workspace.listing(catalog.CATALOG), workspace.job(job), workspace.dashboard(board))
    neighbour_before = workspace.listing(fairshare)

    print("1. Deploying the bundle: the catalog, its four schemas, the volume, the grants, the jobs and the "
          "dashboards.")
    code, output = workspace.deploy_bundle()
    if code != 0:
        print("The bundle deploy failed, so I created no tables. The Databricks CLI said:")
        print("".join(f"    {line}\n" for line in output.splitlines()), end="")
        return 1

    print("2. Creating the tables and views from src/strata/lakehouse/tables and views on the SQL warehouse.")
    try:
        built = catalog.build(workspace.engine(), create_schemas=False)
    except (CatalogError, EngineError) as error:
        print(f"I could not create the tables. {error}")
        return 1
    print(f"   Each of these exists now: {', '.join(built)}.")
    engine = workspace.engine()
    if getattr(engine, "name", "") == "databricks":
        try:
            views = catalog.build_metric_views(engine)
        except (CatalogError, EngineError) as error:
            print(f"I could not create the metric views Genie reads. {error}")
            return 1
        print(f"   The metric views Genie reads exist now: {', '.join(views)}.")
    else:
        print("   This engine has no metric views, so I made none of the ones Genie reads.")

    print("3. What changed:")
    after = flatten(workspace.listing(catalog.CATALOG), workspace.job(job), workspace.dashboard(board))
    for line in changes(before, after) or ["No changes."]:
        print(f"   {line}")

    neighbour_after = workspace.listing(fairshare)
    if neighbour_before is None and neighbour_after is None:
        print(f"I found no catalog named {fairshare}, so I could not compare it. Pass fairshare's catalog "
              "with --fairshare-catalog.")
        return 0
    if neighbour_before == neighbour_after:
        print(f"{fairshare}'s catalog lists the same before and after the deploy: {summary(neighbour_after)}.")
        return 0
    print(f"{fairshare}'s catalog changed during the deploy. Check whether fairshare's own job ran meanwhile:")
    for line in changes(flatten(neighbour_before), flatten(neighbour_after)):
        print(f"   {line}")
    return 1


def main(argv: list[str] | None = None, workspace=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's .env, which the wizard filled. That file is the default.")
    parser.add_argument("--fairshare-catalog", default=FAIRSHARE,
                        help="fairshare's catalog, which must list the same before and after. The default is fairshare.")
    args = parser.parse_args(argv)

    try:
        env = load_workspace_env(args.env_file)
    except WorkspaceEnvError as error:
        print(error, file=sys.stderr)
        return 2

    if workspace is None:
        from bundle_live import LiveWorkspace

        workspace = LiveWorkspace(env)
    return deploy(workspace, args.fairshare_catalog)


if __name__ == "__main__":
    sys.exit(main())
