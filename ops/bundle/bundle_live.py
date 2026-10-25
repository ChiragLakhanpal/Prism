"""The bundle commands' live adapter: every call that reaches the shared workspace.

deploy.py and check.py take any object with these methods, and the offline tests pass fakes. This
one uses ticket 03's workspace client (ops/dayone/live.py), so it reads the host and the token or
service principal from the env file and never from a shell profile. It imports the Databricks SDK
inside the methods that need it, so importing this file needs only the standard library.
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from live import workspace as workspace_client  # noqa: E402  (ticket 03's client factory)
from strata.lakehouse.engine import WarehouseEngine  # noqa: E402

TARGET = "shared"
# How long job-run waits: the job stops after 150 minutes (bundle/nightly.yml), and the first live run
# on October 24, 2026 was still in bronze_to_gold after 60.
RUN_MINUTES = 160


def _text(value) -> str:
    return str(getattr(value, "value", value))


def bundle_vars(env: dict) -> list[str]:
    """The bundle variables the deploy fills from the env file, as the CLI's --var arguments: the SQL warehouse for
    the dashboard's queries, and the AI Search endpoint whose index the nightly job syncs, which is the name the
    wizard gives it (ops/dayone/dayone.toml) when the env file has none."""
    import dayone

    search = (env.get("AI_SEARCH_ENDPOINT") or "").strip() or dayone.config_value(dayone.load_config(),
                                                                                   "names.ai_search_endpoint")
    return ["--var", f"warehouse_id={env['DATABRICKS_WAREHOUSE_ID']}", "--var", f"ai_search_endpoint={search}"]


def cli_env(env: dict, environ: dict) -> dict:
    """The Databricks CLI's environment: the shell's, without its DATABRICKS_* keys, plus one way to sign in.

    The CLI stops when it sees more than one way, so a token wins over a service principal, as it
    does in ticket 03's workspace client (ops/dayone/live.py).
    """
    found = {key: value for key, value in environ.items() if not key.startswith("DATABRICKS_")}
    found["DATABRICKS_HOST"] = env["DATABRICKS_HOST"]
    if env.get("DATABRICKS_TOKEN"):
        return found | {"DATABRICKS_AUTH_TYPE": "pat", "DATABRICKS_TOKEN": env["DATABRICKS_TOKEN"]}
    return found | {"DATABRICKS_AUTH_TYPE": "oauth-m2m", "DATABRICKS_CLIENT_ID": env["DATABRICKS_CLIENT_ID"],
                    "DATABRICKS_CLIENT_SECRET": env["DATABRICKS_CLIENT_SECRET"]}


class LiveWorkspace:
    def __init__(self, env: dict):
        self.env = env
        self.w = workspace_client(env)

    # ── The SQL warehouse ──

    def engine(self) -> WarehouseEngine:
        """The warehouse, called through the SDK's client so a token and a service principal both work."""
        return WarehouseEngine(self.env["DATABRICKS_WAREHOUSE_ID"],
                               lambda method, path, body: self.w.api_client.do(method, path, body=body))

    # ── Unity Catalog ──

    def _grants(self, kind: str, name: str) -> dict:
        found = self.w.grants.get(securable_type=kind, full_name=name)
        return {assignment.principal: sorted(_text(p) for p in assignment.privileges or [])
                for assignment in found.privilege_assignments or []}

    def listing(self, name: str) -> dict | None:
        """A catalog's schemas, volumes, tables with their columns, and grants; None when it does not exist."""
        from databricks.sdk.errors import NotFound

        try:
            info = self.w.catalogs.get(name)
        except NotFound:
            return None
        schemas = {schema.name: schema.comment or "" for schema in self.w.schemas.list(catalog_name=name)
                   if schema.name != "information_schema"}
        volumes, tables = {}, {}
        for schema in schemas:
            for volume in self.w.volumes.list(catalog_name=name, schema_name=schema):
                volumes[f"{schema}.{volume.name}"] = _text(volume.volume_type)
            for table in self.w.tables.list(catalog_name=name, schema_name=schema):
                tables[f"{schema}.{table.name}"] = [f"{column.name} {column.type_text}" for column in table.columns or []]
        grants = {name: self._grants("catalog", name)}
        grants |= {f"{name}.{schema}": self._grants("schema", f"{name}.{schema}") for schema in schemas}
        grants |= {f"{name}.{volume}": self._grants("volume", f"{name}.{volume}") for volume in volumes}
        return {"catalog": {"name": info.name, "comment": info.comment or ""}, "schemas": schemas,
                "volumes": volumes, "tables": tables, "grants": grants}

    # ── Jobs ──

    def _job_id(self, name: str) -> int | None:
        for job in self.w.jobs.list(name=name):
            return job.job_id
        return None

    def job(self, name: str) -> dict | None:
        job_id = self._job_id(name)
        return self.w.jobs.get(job_id).settings.as_dict() if job_id is not None else None

    def dashboard(self, name: str) -> dict | None:
        """The AI/BI dashboard with this name, with its pages and its SQL warehouse, or None."""
        import json

        for found in self.w.lakeview.list():
            if found.display_name == name:
                full = self.w.lakeview.get(found.dashboard_id)
                pages = json.loads(full.serialized_dashboard or "{}").get("pages", [])
                return {"name": name, "pages": [page.get("displayName") for page in pages],
                        "warehouse_id": full.warehouse_id}
        return None

    def job_names(self) -> list[str]:
        return sorted(job.settings.name for job in self.w.jobs.list() if job.settings and job.settings.name)

    def job_facts(self, name: str) -> dict | None:
        job_id = self._job_id(name)
        if job_id is None:
            return None
        settings = self.w.jobs.get(job_id).settings
        durations = []
        for run in self.w.jobs.list_runs(job_id=job_id, completed_only=True, limit=25):
            if run.start_time and run.end_time:
                durations.append((run.end_time - run.start_time) / 60000)
            if len(durations) >= 25:
                break
        cron = settings.schedule
        return {"name": settings.name, "quartz": cron.quartz_cron_expression if cron else None,
                "timezone": cron.timezone_id if cron else None,
                "paused": bool(cron and _text(cron.pause_status) == "PAUSED"),
                "timeout_minutes": (settings.timeout_seconds or 0) // 60 or None, "durations": durations}

    def run_job(self, name: str) -> tuple[str, str, str]:
        """Start the job, wait for it, and return its run id, its result state and its page."""
        job_id = self._job_id(name)
        if job_id is None:
            raise SystemExit(f"I found no job named {name}. Deploy first: uv run --script ops/bundle/deploy.py "
                             "--env-file .env")
        waiter = self.w.jobs.run_now(job_id)
        try:
            waiter.result(timeout=dt.timedelta(minutes=RUN_MINUTES))
        except Exception:  # a failed run still has a state and a page, which are read next
            pass
        run = self.w.jobs.get_run(waiter.run_id)
        if run.state and run.state.result_state:
            state = _text(run.state.result_state)
        elif run.state and _text(run.state.life_cycle_state) in ("RUNNING", "PENDING", "QUEUED"):
            state = f"still {_text(run.state.life_cycle_state).lower()} after {RUN_MINUTES} minutes"
        else:
            state = "UNKNOWN"
        return str(waiter.run_id), state, run.run_page_url or ""

    # ── The bundle ──

    def deploy_bundle(self) -> tuple[int, str]:
        """Run `databricks bundle deploy` from the checkout's root with the env file's credentials and the bundle
        variables it fills (bundle_vars)."""
        cli = shutil.which("databricks")
        if cli is None:
            return 1, "The Databricks CLI is not on the path. Install version 0.287.0 or later."
        done = subprocess.run([cli, "bundle", "deploy", "--target", TARGET, *bundle_vars(self.env)], cwd=REPO,
                              env=cli_env(self.env, dict(os.environ)),
                              capture_output=True, text=True, timeout=1800)
        return done.returncode, (done.stdout + done.stderr).strip()
