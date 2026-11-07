# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0"]
# ///
"""Bring Prism's workspace back after a pause, pause it again, or say what is running.

Run it from the main checkout:

    uv run --script ops/workspace/resume.py                          # resume, in order: the search endpoint, Lakebase,
                                                                       the App, the warehouse, the passage index
    uv run --script ops/workspace/resume.py --status                 # read the states and change nothing
    uv run --script ops/workspace/resume.py --pause                  # stop the App, Lakebase and the warehouse
    uv run --script ops/workspace/resume.py --pause --delete-search  # and delete the search endpoint with its indexes

It reads the env file (the main checkout's, or --env-file) for the workspace's address and the token, as
ops/app/deploy_app.py does, and never prints a secret. Each name comes from the file that defines it: the App, the
Lakebase instance and the search endpoint from ops/dayone/dayone.toml (names.app, names.app_state_instance,
names.ai_search_endpoint); the passage index and its embedding size from config/models.toml ([search].index,
[roles.embed].dimensions); the index's source table, key and embedding column from ops/workspace/search.toml.

What costs money while the workspace sits idle, and what the script does about each:

- The App's compute (MEDIUM, about $9 a day at list prices) runs until it is stopped. Resume starts it, and the last
  deployment serves again, so no deploy is needed.
- The Lakebase instance (CU_1, about $4 a day) runs until it is stopped. Resume starts it and waits until it is
  available, before the App, which keeps its app state there. Its data stays through a stop.
- The SQL warehouse costs only while it runs and stops itself after ten idle minutes. Resume starts it so the first
  visit is quick; pause stops it when it is running.
- The search endpoint (STANDARD, about 96 DBU a day) cannot be stopped, only deleted, so pause leaves it alone
  unless --delete-search is given. Resume makes it again when it is missing, waits until it is online, makes the
  passage index from its source table and waits until the index is ready.
- The four jobs stay as they are (paused since November 3, 2026); the script prints their states. A job is unpaused
  in the workspace, or by a bundle deploy whose nightly_pause_status is not PAUSED (ops/bundle/deploy.py).

The Azure side (the Foundry deployments, Application Insights, the Log Analytics workspace) bills per use, so nothing
there needs stopping or starting.

resume(), pause() and status() take any object with the Live adapter's methods below; the offline tests pass a fake.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402  (ops/dayone/dayone.py: dayone.toml's names)
import workspace_state  # noqa: E402  (ops/bundle/workspace_state.py: the App's and the warehouse's reads and starts)
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

MODELS = REPO / "config" / "models.toml"
SEARCH = HERE / "search.toml"
ENDPOINT_MINUTES = 40  # how long a new search endpoint may take to come online, as the day-one probe allows
INDEX_MINUTES = 30  # how long a new index may take to sync, as the day-one probe allows
LAKEBASE_MINUTES = 15  # how long the Lakebase instance may take to start or to stop
STOP_MINUTES = 10  # how long the App's compute or the warehouse may take to stop
POLL_SECONDS = 30
RUNNING = ("RUNNING", "STARTING")
AGAIN = "Run the script again later; it skips what is already done."


def names(config: dict | None = None, models: dict | None = None, search: dict | None = None) -> dict:
    """Every name the script needs, each read from the file that defines it."""
    config = config or dayone.load_config()
    models = models or tomllib.loads(MODELS.read_text())
    search = search or tomllib.loads(SEARCH.read_text())
    return {"app": dayone.config_value(config, "names.app"),
            "instance": dayone.config_value(config, "names.app_state_instance"),
            "endpoint": dayone.config_value(config, "names.ai_search_endpoint"),
            "endpoint_type": search["endpoint"]["type"],
            "index": models["search"]["index"],
            "dimensions": models["roles"]["embed"]["dimensions"],
            "source_table": search["index"]["source_table"],
            "primary_key": search["index"]["primary_key"],
            "embedding_column": search["index"]["embedding_column"]}


def _text(value) -> str | None:
    return None if value is None else getattr(value, "value", str(value))


class Live:
    """Every call that reaches the workspace, through ticket 03's client (ops/dayone/live.py), which signs in with the
    env file's token or service principal and never a shell profile. The SDK is imported inside the methods."""

    def __init__(self, env: dict):
        from live import workspace as workspace_client

        self.w = workspace_client(env)
        self.warehouse_id = env["DATABRICKS_WAREHOUSE_ID"]

    # The search endpoint and the index.

    def endpoint(self, name: str) -> dict | None:
        from databricks.sdk.errors import NotFound

        try:
            found = self.w.vector_search_endpoints.get_endpoint(name)
        except NotFound:
            return None
        status = found.endpoint_status
        return {"state": _text(status.state) if status else None}

    def make_endpoint(self, name: str, endpoint_type: str) -> None:
        from databricks.sdk.service.vectorsearch import EndpointType

        self.w.vector_search_endpoints.create_endpoint(name, EndpointType(endpoint_type))

    def indexes(self, endpoint: str) -> list[str]:
        return [index.name for index in self.w.vector_search_indexes.list_indexes(endpoint_name=endpoint)]

    def index(self, name: str) -> dict | None:
        from databricks.sdk.errors import NotFound

        try:
            found = self.w.vector_search_indexes.get_index(name)
        except NotFound:
            return None
        status = found.status
        return {"ready": bool(status and status.ready), "rows": (status.indexed_row_count or 0) if status else 0,
                "message": (status.message or "") if status else ""}

    def make_index(self, n: dict) -> None:
        from databricks.sdk.service import vectorsearch as vs

        self.w.vector_search_indexes.create_index(
            name=n["index"], endpoint_name=n["endpoint"], primary_key=n["primary_key"],
            index_type=vs.VectorIndexType.DELTA_SYNC, index_subtype=vs.IndexSubtype.HYBRID,
            delta_sync_index_spec=vs.DeltaSyncVectorIndexSpecRequest(
                source_table=n["source_table"], pipeline_type=vs.PipelineType.TRIGGERED,
                embedding_vector_columns=[vs.EmbeddingVectorColumn(name=n["embedding_column"],
                                                                   embedding_dimension=n["dimensions"])]))

    def delete_index(self, name: str) -> None:
        self.w.vector_search_indexes.delete_index(name)

    def delete_endpoint(self, name: str) -> None:
        self.w.vector_search_endpoints.delete_endpoint(name)

    # The Lakebase instance.

    def lakebase(self, name: str) -> dict | None:
        from databricks.sdk.errors import NotFound

        try:
            found = self.w.database.get_database_instance(name)
        except NotFound:
            return None
        return {"state": _text(found.state), "stopped": bool(found.stopped)}

    def start_lakebase(self, name: str) -> None:
        from databricks.sdk.service import database

        self.w.database.update_database_instance(name, database.DatabaseInstance(name=name, stopped=False), "stopped")
        self.w.database.wait_get_database_instance_database_available(name, timeout=dt.timedelta(minutes=LAKEBASE_MINUTES))

    def stop_lakebase(self, name: str) -> None:
        from databricks.sdk.service import database

        self.w.database.update_database_instance(name, database.DatabaseInstance(name=name, stopped=True), "stopped")

    # The App.

    def app(self, name: str) -> dict | None:
        from databricks.sdk.errors import NotFound

        try:
            found = self.w.apps.get(name)
        except NotFound:
            return None
        compute, status = found.compute_status, found.app_status
        return {"compute": _text(compute.state) if compute else None, "app": _text(status.state) if status else None,
                "url": found.url or ""}

    def start_app(self, name: str) -> None:
        workspace_state.start_app(self.w, name)

    def stop_app(self, name: str) -> None:
        self.w.apps.stop_and_wait(name, timeout=dt.timedelta(minutes=STOP_MINUTES))

    # The SQL warehouse and the jobs.

    def warehouse(self) -> dict:
        return workspace_state.warehouse_state(self.w, self.warehouse_id)

    def start_warehouse(self) -> None:
        self.w.warehouses.start(self.warehouse_id)

    def stop_warehouse(self) -> None:
        self.w.warehouses.stop_and_wait(self.warehouse_id, timeout=dt.timedelta(minutes=STOP_MINUTES))

    def jobs(self) -> list[dict]:
        found = []
        for job in self.w.jobs.list():
            settings = job.settings
            schedule = settings.schedule if settings else None
            found.append({"name": settings.name if settings and settings.name else str(job.job_id),
                          "pause": _text(schedule.pause_status) if schedule and schedule.pause_status else "no schedule"})
        return found


def index_words(index: dict | None) -> str:
    if index is None:
        return "missing"
    return f"{'ready' if index['ready'] else 'not ready'}, {index['rows']} rows"


def status(ws, n: dict, say=print) -> int:
    """What runs on the workspace, read and not changed."""
    say("What runs on the workspace:")
    endpoint = ws.endpoint(n["endpoint"])
    say(f"   The search endpoint {n['endpoint']}: {endpoint['state'] if endpoint else 'missing'}.")
    if endpoint:
        say(f"   The index {n['index']}: {index_words(ws.index(n['index']))}.")
    lakebase = ws.lakebase(n["instance"])
    say(f"   The Lakebase instance {n['instance']}: {lakebase['state'] if lakebase else 'missing'}.")
    app = ws.app(n["app"])
    say(f"   The App {n['app']}: " + (f"compute {app['compute']}, app {app['app']}." if app else "missing."))
    warehouse = ws.warehouse()
    say(f"   The SQL warehouse {warehouse['id']}: {warehouse['state']}.")
    for job in ws.jobs():
        say(f"   The job {job['name']}: {job['pause']}.")
    return 0


def resume(ws, n: dict, say=print, sleep=time.sleep, clock=time.monotonic) -> int:
    """Start what is stopped, in the order the parts need each other, and skip what already runs."""
    say(f"1. The search endpoint {n['endpoint']}.")
    endpoint = ws.endpoint(n["endpoint"])
    if endpoint is None:
        ws.make_endpoint(n["endpoint"], n["endpoint_type"])
        say("   It was missing, so I am making it. It comes online while the rest starts.")
    elif endpoint["state"] == "ONLINE":
        say("   It is online.")
    else:
        say(f"   It is {endpoint['state']}. I wait for it after the rest starts.")

    say(f"2. The Lakebase instance {n['instance']}.")
    lakebase = ws.lakebase(n["instance"])
    if lakebase is None:
        say("   There is no such instance. The App's deploy makes it: uv run --script ops/app/deploy_app.py --env-file .env")
        return 2
    if lakebase["state"] == "AVAILABLE" and not lakebase["stopped"]:
        say("   It is available.")
    else:
        say(f"   It is {lakebase['state']}. Starting it and waiting until it is available.")
        ws.start_lakebase(n["instance"])
        say("   It is available.")

    say(f"3. The App {n['app']}.")
    app = ws.app(n["app"])
    if app is None:
        say("   There is no such App. Deploy it: uv run --script ops/app/deploy_app.py --env-file .env")
        return 2
    if app["compute"] == "ACTIVE":
        say(f"   Its compute is active and the app is {app['app']}.")
    else:
        say(f"   Its compute is {app['compute']}. Starting it and waiting until it runs; the last deployment serves again.")
        ws.start_app(n["app"])
        app = ws.app(n["app"]) or app
        say(f"   Its compute is {app['compute']} and the app is {app['app']}.")

    say("4. The SQL warehouse.")
    warehouse = ws.warehouse()
    if warehouse["state"] in RUNNING:
        say(f"   It is {warehouse['state']}.")
    else:
        ws.start_warehouse()
        say("   It was stopped. It is starting, so the first visit is quick; it stops itself after ten idle minutes.")

    say(f"5. The index {n['index']} on the endpoint.")
    deadline = clock() + ENDPOINT_MINUTES * 60
    endpoint = ws.endpoint(n["endpoint"])
    while endpoint and endpoint["state"] != "ONLINE" and clock() < deadline:
        sleep(POLL_SECONDS)
        endpoint = ws.endpoint(n["endpoint"])
    if not endpoint or endpoint["state"] != "ONLINE":
        state = endpoint["state"] if endpoint else "missing"
        say(f"   The endpoint is {state} after {ENDPOINT_MINUTES} minutes, so the index waits. {AGAIN}")
        return 2
    index = ws.index(n["index"])
    if index is None:
        ws.make_index(n)
        say(f"   It was missing, so I am making it from {n['source_table']}, which keeps the embeddings, and waiting "
            "until it is ready.")
    elif not (index["ready"] and index["rows"] > 0):
        say("   It is not ready yet. Waiting.")
    deadline = clock() + INDEX_MINUTES * 60
    index = ws.index(n["index"])
    while not (index and index["ready"] and index["rows"] > 0) and clock() < deadline:
        sleep(POLL_SECONDS)
        index = ws.index(n["index"])
    if not (index and index["ready"] and index["rows"] > 0):
        say(f"   It is {index_words(index)} after {INDEX_MINUTES} minutes. {AGAIN}")
        return 2
    say(f"   It is ready with {index['rows']} rows.")

    say(f"6. Prism is running at {app['url']}")
    say("   Check: signed in, open Home and see a project's record load, then ask Search a question and see passages come "
        "back with their sources. The jobs:")
    for job in ws.jobs():
        say(f"   {job['name']}: {job['pause']}.")
    return 0


def pause(ws, n: dict, say=print, delete_search: bool = False, sleep=time.sleep, clock=time.monotonic) -> int:
    """Stop what bills while idle. The search endpoint goes only with delete_search, since it cannot be stopped."""
    say(f"1. The App {n['app']}.")
    app = ws.app(n["app"])
    if app is None:
        say("   There is no such App.")
    elif app["compute"] == "STOPPED":
        say("   Its compute is already stopped.")
    else:
        ws.stop_app(n["app"])
        say("   Its compute is stopped. The deployment stays, and resume starts it again.")

    say(f"2. The Lakebase instance {n['instance']}.")
    lakebase = ws.lakebase(n["instance"])
    if lakebase is None:
        say("   There is no such instance.")
    elif lakebase["state"] == "STOPPED" or lakebase["stopped"]:
        say("   It is already stopped.")
    else:
        ws.stop_lakebase(n["instance"])
        deadline = clock() + LAKEBASE_MINUTES * 60
        lakebase = ws.lakebase(n["instance"])
        while lakebase and lakebase["state"] != "STOPPED" and clock() < deadline:
            sleep(POLL_SECONDS)
            lakebase = ws.lakebase(n["instance"])
        say(f"   It is {lakebase['state'] if lakebase else 'missing'}. Its data stays.")

    say("3. The SQL warehouse.")
    warehouse = ws.warehouse()
    if warehouse["state"] in RUNNING:
        ws.stop_warehouse()
        say("   It was running. It is stopped.")
    else:
        say(f"   It is {warehouse['state']}.")

    say(f"4. The search endpoint {n['endpoint']}.")
    endpoint = ws.endpoint(n["endpoint"])
    if endpoint is None:
        say("   It is already gone.")
    elif not delete_search:
        say(f"   It is {endpoint['state']} and still bills, about 96 DBU a day. It cannot be stopped, only deleted: run "
            "again with --delete-search to delete it and its indexes. Resume makes them again from the source table.")
    else:
        for name in ws.indexes(n["endpoint"]):
            ws.delete_index(name)
            say(f"   Deleted the index {name}. Its source table stays.")
        ws.delete_endpoint(n["endpoint"])
        say("   Deleted the endpoint. Resume makes it again, with the passage index.")

    say("5. The jobs, left as they are.")
    for job in ws.jobs():
        say(f"   {job['name']}: {job['pause']}.")
    return 0


def main(argv: list[str] | None = None, workspace=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, default=None, help="the env file; the main checkout's by default")
    what = parser.add_mutually_exclusive_group()
    what.add_argument("--status", action="store_true", help="read the states and change nothing")
    what.add_argument("--pause", action="store_true", help="stop the App, the Lakebase instance and the warehouse")
    parser.add_argument("--delete-search", action="store_true",
                        help="with --pause: delete the search endpoint and its indexes too")
    args = parser.parse_args(argv)
    if args.delete_search and not args.pause:
        parser.error("--delete-search goes with --pause")
    try:
        env = load_workspace_env(args.env_file)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    ws = workspace or Live(env)
    n = names()
    try:
        if args.status:
            return status(ws, n)
        if args.pause:
            return pause(ws, n, delete_search=args.delete_search)
        return resume(ws, n)
    except Exception as error:  # the workspace refused a read or a start; one sentence, not a traceback
        print(f"The workspace answered: {workspace_state.one_line(str(error))}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
