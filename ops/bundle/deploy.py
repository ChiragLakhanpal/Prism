# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3"]
# ///
"""Deploy Strata's catalog and nightly job to the shared workspace, and say what changed.

Run it from the main checkout after the wizard:

    uv run --script ops/bundle/deploy.py --env-file .env

It needs the Databricks CLI 0.287.0 or later on the path. It does these things, in order:

1. It lists what the workspace holds: the strata catalog, its schemas, the volume, the tables, the
   grants, the nightly job that bundle/nightly.yml names and both dashboards with the time each was
   last written, and also fairshare's catalog.
2. It runs `databricks bundle deploy`, which creates or updates the catalog, the bronze, silver,
   gold and ops schemas, the bronze files volume, the read grants, the nightly job and the AI/BI
   dashboards that src/strata/dashboard defines (bundle/dashboard.yml), with the env file's SQL
   warehouse for the dashboards' queries. The bundle's grants replace every other grant on strata
   and its schemas, so right after, it gives the app's own service principal (the app that
   ops/dayone/dayone.toml names, as apps get returns it) back USE CATALOG on strata and USE SCHEMA
   on strata.ops (ticket 79). With no app yet, it says so and grants nothing for it.
3. It creates the tables from src/strata/lakehouse/tables on the SQL warehouse. Each one is
   CREATE TABLE IF NOT EXISTS, so a table that holds rows is never replaced. Then it creates or
   replaces the metric views the Genie space reads, from src/strata/lakehouse/metric_views (ticket 33),
   which hold no rows.
4. It lists the same things again and prints what changed, a dashboard the bundle rewrote among
   them. A second run prints "No changes."
   It also checks that fairshare's catalog lists the same as before, and fails if it does not.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "app", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
import deploy_app  # noqa: E402  (ops/app/deploy_app.py, which says what the app's service principal holds)
from strata.lakehouse import bundle, catalog, nightly  # noqa: E402
from strata.lakehouse.catalog import CatalogError  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

FAIRSHARE = "fairshare"
KINDS = {"catalog": "The catalog", "schemas": "The schema", "volumes": "The volume", "tables": "The table",
         "grants": "The grants on", "jobs": "The job", "dashboards": "The dashboard"}


def dashboard_names() -> list[str]:
    """Each dashboard's name in the workspace, as bundle/dashboard.yml gives it: the dashboard and its test copy."""
    loaded = bundle.load()
    return [loaded.resolve(board["display_name"]) for board in loaded.resources("dashboards").values()]


def flatten(listing: dict | None, job: dict | None = None, dashboards: list[dict | None] = ()) -> dict:
    """One entry per thing the deploy can change, keyed by its kind and full name. A dashboard's entry holds its
    update_time, so one the bundle rewrote reads as changed even when its pages kept their names."""
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
    found |= {("dashboards", dashboard["name"]): dashboard for dashboard in dashboards if dashboard}
    return found


def plan(loaded: bundle.Bundle | None = None) -> list[tuple[str, str]]:
    """What a first deploy makes on a fresh workspace, read from the repo alone and keyed as flatten() keys what
    the workspace lists: the catalog, its schemas and volume, every table, view and metric view, the grants, every
    job in bundle/*.yml and the dashboard. The demo-ready command's dry run prints it (ops/demo/ready.py
    --fresh-workspace), so its list cannot drift from this deploy."""
    loaded = loaded or bundle.load()
    declared = catalog.declared(loaded)
    defined = catalog.table_definitions() + catalog.view_definitions() + catalog.metric_view_definitions()
    return ([("catalog", declared.catalog)]
            + [("schemas", f"{declared.catalog}.{schema}") for schema in declared.schemas]
            + [("volumes", f"{declared.catalog}.{volume}") for volume in declared.volumes]
            + [("tables", definition.full_name) for definition in defined]
            + [("grants", securable) for securable in declared.grants]
            + [("jobs", loaded.resolve(job["name"])) for job in loaded.resources("jobs").values()]
            + [("dashboards", loaded.resolve(board["display_name"])) for board in loaded.resources("dashboards").values()])


def changes(before: dict, after: dict, kinds: dict[str, str] = KINDS) -> list[str]:
    """One sentence per thing that is new, gone or changed, in the order of kinds: KINDS, or the demo-ready
    command's listing (ops/demo/ready.py), which adds the app and the rows of strata.ops."""
    lines = []
    order = list(kinds)
    for kind, name in sorted(set(before) | set(after), key=lambda key: (order.index(key[0]), key[1])):
        label, plural = kinds[kind], kind in ("grants", "rows")
        if (kind, name) not in before:
            lines.append(f"{label} {name} {'are' if plural else 'is'} new.")
        elif (kind, name) not in after:
            lines.append(f"{label} {name} {'are' if plural else 'is'} gone.")
        elif before[(kind, name)] != after[(kind, name)]:
            lines.append(f"{label} {name} changed.")
    return lines


def give_app_access(workspace) -> str:
    """Give the app's own service principal back its way in to the catalog and to strata.ops (deploy_app.ACCESS),
    which the bundle's grants replace, and say what I did (ticket 79). The app is the one ops/dayone/dayone.toml
    names, as apps get returns it. No app yet, or an app that is not Strata's, gets nothing."""
    name = dayone.load_config()["names"]["app"]
    app = workspace.app(name)
    if app is None:
        return (f"I found no app named {name}, so I granted nothing for it. Its deploy, ops/app/deploy_app.py, "
                "grants its service principal what it needs.")
    if not deploy_app.is_strata(app):
        return f"The app {name} is not Strata's: its description is {app['description']!r}. I granted nothing for it."
    principal = app.get("principal") or ""
    if not deploy_app.PRINCIPAL.fullmatch(principal):
        return f"The app {name} has no service principal yet, so I granted nothing for it."
    for kind, securable, privilege in deploy_app.ACCESS:
        workspace.grant(kind, securable, principal, [privilege])
    held = " and ".join(f"{privilege.replace('_', ' ')} on {securable}" for _, securable, privilege in deploy_app.ACCESS)
    return (f"The bundle's grants replace every other grant on {catalog.CATALOG} and its schemas, so I gave the app "
            f"{name}'s service principal {principal} back {held}.")


def summary(listing: dict) -> str:
    counts = [dayone.count_words(len(listing.get(kind, {})), noun)
              for kind, noun in (("schemas", "schema"), ("tables", "table"), ("volumes", "volume"))]
    return f"{counts[0]}, {counts[1]} and {counts[2]}"


def deploy(workspace, fairshare: str = FAIRSHARE) -> int:
    job, boards = nightly.job_name(), dashboard_names()
    before = flatten(workspace.listing(catalog.CATALOG), workspace.job(job), [workspace.dashboard(b) for b in boards])
    neighbour_before = workspace.listing(fairshare)

    print("1. Deploying the bundle: the catalog, its four schemas, the volume, the grants, the jobs and the "
          "dashboards.")
    code, output = workspace.deploy_bundle()
    if code != 0:
        print("The bundle deploy failed, so I created no tables. The Databricks CLI said:")
        print("".join(f"    {line}\n" for line in output.splitlines()), end="")
        return 1
    print(f"   {give_app_access(workspace)}")

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
    after = flatten(workspace.listing(catalog.CATALOG), workspace.job(job), [workspace.dashboard(b) for b in boards])
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
