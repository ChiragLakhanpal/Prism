# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3"]
# ///
"""Build Strata's web app and deploy Strata as the Databricks App that acts as each viewer.

Run it from the main checkout after the wizard and the bundle deploy (ops/bundle/deploy.py):

    uv run --script ops/app/deploy_app.py --env-file .env

It needs npm, which builds the web app. It does these things, in order:

1. It builds the web app into web/dist (npm --prefix web run build).
2. It finds the app that ops/dayone/dayone.toml names (names.app), or makes it. It replaces the
   day-one probe app that ran there, but it leaves an app that someone else made alone.
3. It gives the app its resources: the SQL warehouse in .env (CAN_USE) and the Application
   Insights connection string in the secret scope (READ), and the "sql" user authorization
   scope, so the App forwards each viewer's own token for the warehouse.
4. It uploads the app, laid out as in the repo: app.yaml and the lean requirements.txt from
   ops/app, src/strata, config and web/dist, to the folder strata-app in your workspace folder.
5. It deploys the app, starting it first if it is stopped, and waits for it.
6. It grants the app's own service principal what the server needs to write usage events, and
   nothing more: USE CATALOG on strata, USE SCHEMA on strata.ops, and SELECT and MODIFY on
   strata.ops.usage_events. Viewers read as themselves, through the bundle's grants.
7. It prints the app's address.

Run it again after every bundle deploy. The grants in bundle/catalog.yml replace any other
grants on the strata catalog and its schemas (bundle/README.md), so a bundle deploy removes the
app's USE CATALOG and USE SCHEMA, and its usage events stop being written.

This was written from docs/PLAN.md section 12's description of fairshare's lakehouse/app_deploy.py,
because fairshare could not be read on the build machine.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

DESCRIPTION = "Strata, procurement intelligence on World Bank open data"
PROBE_DESCRIPTION = "Strata day-one probe app"  # ops/dayone/live.py's PROBE_APP_DESCRIPTION
FOLDER = "strata-app"
DIST = REPO / "web" / "dist"
SCOPES = ["sql"]
# The secret's name in the scope, which the wizard saved (ops/wizard/strata-setup.sh).
APPINSIGHTS_NAME = "APPLICATIONINSIGHTS_CONNECTION_STRING"
PRINCIPAL = re.compile(r"[0-9a-fA-F-]{36}")
SKIPPED = ("__pycache__", ".DS_Store")


def build_web() -> tuple[int, str]:
    done = subprocess.run(["npm", "--prefix", "web", "run", "--silent", "build"], cwd=REPO,
                          capture_output=True, text=True, timeout=600)
    return done.returncode, (done.stdout + done.stderr).strip()


def _files(root: Path, under: str) -> dict[str, bytes]:
    return {f"{under}/{path.relative_to(root).as_posix()}": path.read_bytes() for path in sorted(root.rglob("*"))
            if path.is_file() and not any(part in SKIPPED for part in path.parts)}


def package(dist: Path) -> dict[str, bytes]:
    """The app's files, by their path in the app's folder."""
    return {"app.yaml": (HERE / "app.yaml").read_bytes(), "requirements.txt": (HERE / "requirements.txt").read_bytes(),
            **_files(REPO / "src" / "strata", "src/strata"),
            **{f"config/{path.name}": path.read_bytes() for path in sorted((REPO / "config").glob("*.toml"))},
            **_files(dist, "web/dist")}


def resources(env: dict, scope: str) -> list[dict]:
    return [
        {"name": "sql-warehouse", "sql_warehouse": {"id": env["DATABRICKS_WAREHOUSE_ID"], "permission": "CAN_USE"}},
        {"name": "appinsights", "secret": {"scope": scope, "key": APPINSIGHTS_NAME, "permission": "READ"}},
    ]


def grants(principal: str) -> list[str]:
    """What the app's own service principal needs to write usage events."""
    if not PRINCIPAL.fullmatch(principal):
        raise ValueError(f"{principal!r} is not a service principal's application id.")
    return [f"GRANT USE CATALOG ON CATALOG strata TO `{principal}`",
            f"GRANT USE SCHEMA ON SCHEMA strata.ops TO `{principal}`",
            f"GRANT SELECT, MODIFY ON TABLE strata.ops.usage_events TO `{principal}`"]


def deploy(workspace, env: dict, build_web: Callable[[], tuple[int, str]] = build_web, dist: Path = DIST) -> int:
    names = dayone.load_config()["names"]
    name = names["app"]

    print("1. Building the web app.")
    code, output = build_web()
    if code != 0 or not (dist / "index.html").is_file():
        print("The web app did not build, so I left the workspace alone. npm said:")
        print("".join(f"    {line}\n" for line in output.splitlines()), end="")
        return 1

    print(f"2. Finding the app {name}.")
    app = workspace.app(name)
    if app is None:
        workspace.create_app(name, DESCRIPTION)
        app = workspace.app(name)
        print(f"   I made the app {name}.")
    elif app["description"] not in (DESCRIPTION, PROBE_DESCRIPTION):
        print(f"The app {name} is not Strata's: its description is {app['description']!r} and it runs "
              f"{app['source'] or 'nothing yet'}. I left it alone. Set names.app in ops/dayone/dayone.toml "
              "to a free app name.")
        return 1

    print("3. Giving it the SQL warehouse, the Application Insights connection string and each viewer's SQL token.")
    workspace.configure_app(name, DESCRIPTION, resources(env, names["secret_scope"]), SCOPES)

    folder = f"/Workspace/Users/{workspace.me()}/{FOLDER}"
    files = package(dist)
    print(f"4. Uploading {len(files)} files to {folder}.")
    workspace.upload(folder, files)

    print("5. Deploying the app. This takes a few minutes.")
    if not app["running"]:
        workspace.start(name)
    url = workspace.deploy(name, folder)

    print("6. Letting the app's own service principal write usage events to strata.ops.usage_events.")
    for statement in grants(app["principal"]):
        workspace.run_sql(statement)

    print(f"Strata is running at {url}")
    return 0


def main(argv: list[str] | None = None, workspace=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's .env, which the wizard filled. That file is the default.")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(args.env_file)
    except WorkspaceEnvError as error:
        print(error, file=sys.stderr)
        return 2
    if workspace is None:
        from app_live import LiveApps

        workspace = LiveApps(env)
    return deploy(workspace, env)


if __name__ == "__main__":
    sys.exit(main())
