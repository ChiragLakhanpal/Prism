"""The demo-ready command's live adapter: every call that reaches the shared workspace, Foundry or Azure OpenAI.

ops/demo/ready.py takes any object with these attributes and methods, and the offline tests pass a fake. This one
reuses what earlier tickets wrote, and writes no second copy of it:

- ticket 03's workspace client and the app's sign-in (ops/dayone/live.py: workspace, call_app, app_headers), so it
  reads the host and the token from the env file and calls the app with the browser sign-in the wizard saved;
- ticket 04's workspace listing (ops/bundle/bundle_live.py, LiveWorkspace), which the bundle deploy lists before
  and after it changes anything;
- ticket 33's agent helpers (ops/agent/live.py, through ops/evals/full_gate.py's agent_live): the Foundry agent and
  the SQL warehouse as the env file's token, opened as the app opens it for a viewer, and the judge of check 4.

It imports the Databricks SDK inside the methods that need it, through those modules.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle", REPO / "ops" / "app", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
import deploy as bundle_deploy  # noqa: E402  (ops/bundle/deploy.py)
from bundle_live import LiveWorkspace  # noqa: E402
from fresh_workspace import SEED_MODULE  # noqa: E402
from live import call_app  # noqa: E402  (ops/dayone/live.py)

from strata.dbx import Viewer  # noqa: E402
from strata.lakehouse import catalog  # noqa: E402

MINUTES = 20  # how long stopping or starting the app may take, as ops/dayone/live.py and ops/app/app_live.py allow


def full_gate():
    """ops/evals/full_gate.py, by its path, for agent_live() and TOOL_SETTINGS."""
    if "strata_full_gate" not in sys.modules:
        spec = importlib.util.spec_from_file_location("strata_full_gate", REPO / "ops" / "evals" / "full_gate.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["strata_full_gate"] = module
        spec.loader.exec_module(module)
    return sys.modules["strata_full_gate"]


def row_counts_sql(tables: list[str]) -> str:
    """One statement that counts the rows of each table, one column per table, so the listing costs one query."""
    columns = ", ".join(f"(SELECT count(*) FROM {name}) AS {name.split('.')[-1]}"  # sql-lint: names only
                        for name in tables)
    return f"SELECT {columns}"  # sql-lint: names only, from the table definitions


def ops_rows(engine, found: dict) -> dict:
    """How many rows each strata.ops table holds, keyed ("rows", name), for the tables the listing found, so a run
    that wrote a row shows up as a change. A table the repo defines and the listing lacks is keyed ("missing", name)
    instead: the workspace is a bundle deploy behind, and one missing table would fail the whole count. The offline
    tests run this on the fixture database, as the live listing runs it on the warehouse."""
    defined = [definition.full_name for definition in catalog.table_definitions() if definition.schema == "ops"]
    have = [name for name in defined if ("tables", name) in found]
    counted = engine.run(row_counts_sql(have)).rows[0] if have else ()
    return {**{("rows", name): count for name, count in zip(have, counted, strict=True)},
            **{("missing", name): True for name in defined if ("tables", name) not in found}}


class LiveDemo:
    def __init__(self, env: dict, env_path: Path):
        from strata.agent import judge
        from strata.config import load_agent

        gate = full_gate()
        self.env, self.env_path, self.config = env, env_path, dayone.load_config()
        # The tools read these from the environment, as the App's app.yaml gives them (ops/evals/full_gate.py).
        self.tool_settings = {key: env[key] for key in gate.TOOL_SETTINGS if env.get(key)}
        self.listing = LiveWorkspace(env)
        self.w = self.listing.w
        me = self.w.current_user.me()
        # The env file's token as the viewer for this run only: the tools sign their calls with it (CLAUDE.md rule 7).
        self.viewer = Viewer(email=me.user_name, name=me.display_name or me.user_name, user_id=str(me.id),
                             token=env["DATABRICKS_TOKEN"])
        self.agents = gate.agent_live()
        self.warehouse_for = self.agents.warehouse_engine_for(env)
        self.spec = load_agent("orchestrator")
        self.judge = judge.from_environment(env)

    def engine_for(self, viewer):
        """The SQL warehouse as the env file's token, with the tools' settings in the environment again: ticket 03's
        workspace client and the app's sign-in clear every DATABRICKS_ variable each time they run."""
        os.environ.update(self.tool_settings)
        return self.warehouse_for(viewer)

    # ── The answer contract ──

    def agent_for(self, turn):
        os.environ.update(self.tool_settings)
        return self.agents.foundry_agent(self.env, self.spec)

    # ── The app ──

    def app(self, name: str) -> dict | None:
        from databricks.sdk.errors import NotFound
        from databricks.sdk.service import apps

        try:
            found = self.w.apps.get(name)
        except NotFound:
            return None
        state = found.compute_status.state if found.compute_status else None
        return {"description": found.description or "",
                "source": getattr(found.active_deployment, "source_code_path", None),
                "url": found.url, "running": state == apps.ComputeState.ACTIVE}

    def stop_app(self, name: str) -> None:
        self.w.apps.stop_and_wait(name, timeout=dt.timedelta(minutes=MINUTES))

    def start_app(self, name: str) -> None:
        self.w.apps.start_and_wait(name, timeout=dt.timedelta(minutes=MINUTES))

    def health(self, url: str) -> dict:
        return call_app(self.env, self.config, url, "/api/health", attempts=1)

    # ── Home's examples ──

    def seed(self) -> tuple[int, str]:
        done = subprocess.run([sys.executable, "-m", SEED_MODULE, "--env-file", str(self.env_path)], cwd=REPO,
                              capture_output=True, text=True, timeout=1800)
        return done.returncode, (done.stdout + done.stderr).strip()

    # ── The listing before and after ──

    def snapshot(self) -> dict:
        """The app, Strata's catalog with its jobs and dashboard as the bundle deploy lists them, the Genie space,
        and how many rows each table in strata.ops holds (ops_rows)."""
        from strata.lakehouse import bundle

        name = self.config["names"]["app"]
        found: dict = {("apps", name): self.app(name)}
        loaded = bundle.load()
        jobs = [loaded.resolve(job["name"]) for job in loaded.resources("jobs").values()]
        boards = [loaded.resolve(board["display_name"]) for board in loaded.resources("dashboards").values()]
        found |= bundle_deploy.flatten(self.listing.listing(catalog.CATALOG))
        for job in jobs:
            if (settings := self.listing.job(job)) is not None:
                found[("jobs", job)] = settings
        for board in boards:
            if (dashboard := self.listing.dashboard(board)) is not None:
                found[("dashboards", board)] = dashboard
        space = (self.env.get("GENIE_SPACE_ID") or "").strip()
        if space:
            answer = self.w.api_client.do("GET", f"/api/2.0/genie/spaces/{space}")
            found[("genie", space)] = {"title": answer.get("title"), "description": answer.get("description")}
        with self.engine_for(self.viewer) as engine:
            return found | ops_rows(engine, found)
