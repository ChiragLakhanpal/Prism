"""The app deploy's live adapter: every call that reaches the shared workspace.

deploy_app.py takes any object with these methods, and the offline tests pass a fake. This one uses
ticket 03's workspace client (ops/dayone/live.py), so it reads the host and the token or service
principal from the env file and never from a shell profile, and it asks for personal-access-token
authentication explicitly when the env file has a token. It imports the Databricks SDK inside the
methods that need it, so importing this file needs only the standard library.
"""

from __future__ import annotations

import datetime as dt
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from live import workspace as workspace_client  # noqa: E402  (ticket 03's client factory)
from strata.lakehouse.engine import WarehouseEngine  # noqa: E402

MINUTES = 20  # how long creating, starting or deploying the app may take


class LiveApps:
    def __init__(self, env: dict):
        self.env = env
        self.w = workspace_client(env)

    def me(self) -> str:
        return self.w.current_user.me().user_name

    def app(self, name: str) -> dict | None:
        from databricks.sdk.errors import NotFound
        from databricks.sdk.service import apps

        try:
            app = self.w.apps.get(name)
        except NotFound:
            return None
        state = app.compute_status.state if app.compute_status else None
        return {"description": app.description or "",
                "source": getattr(app.active_deployment, "source_code_path", None),
                "url": app.url, "principal": app.service_principal_client_id,
                "running": state == apps.ComputeState.ACTIVE}

    def create_app(self, name: str, description: str) -> None:
        from databricks.sdk.service import apps

        self.w.apps.create_and_wait(apps.App(name=name, description=description),
                                    timeout=dt.timedelta(minutes=MINUTES))

    def configure_app(self, name: str, description: str, resources: list[dict], scopes: list[str]) -> None:
        from databricks.sdk.service import apps

        self.w.apps.update(name, apps.App(name=name, description=description,
                                          resources=[apps.AppResource.from_dict(r) for r in resources],
                                          user_api_scopes=scopes))

    def start(self, name: str) -> None:
        self.w.apps.start_and_wait(name, timeout=dt.timedelta(minutes=MINUTES))

    def upload(self, folder: str, files: dict[str, bytes]) -> None:
        from databricks.sdk.service import workspace as ws

        made = set()
        for path, content in files.items():
            parent = f"{folder}/{path}".rsplit("/", 1)[0]
            if parent not in made:
                self.w.workspace.mkdirs(parent)
                made.add(parent)
            self.w.workspace.upload(f"{folder}/{path}", content, format=ws.ImportFormat.AUTO, overwrite=True)

    def deploy(self, name: str, folder: str) -> str:
        from databricks.sdk.service import apps

        self.w.apps.deploy_and_wait(name, apps.AppDeployment(source_code_path=folder),
                                    timeout=dt.timedelta(minutes=MINUTES))
        return self.w.apps.get(name).url

    def run_sql(self, statement: str) -> None:
        warehouse(self.w, self.env).run(statement)


def warehouse(w, env: dict) -> WarehouseEngine:
    return WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"], lambda method, path, body: w.api_client.do(method, path, body=body))


# ── The Lakebase probe's two stores (ops/app/probe_lakebase.py) ──────────

LAKEBASE_INSTANCE = "strata-state-probe"
LAKEBASE_CAPACITY = "CU_1"  # the smallest instance
POSTGRES_DATABASE = "databricks_postgres"


class WarehouseStore:
    """A table in the day-one probes' own schema, on the SQL warehouse strata.ops uses."""

    def __init__(self, w, env: dict, config: dict):
        self.engine = warehouse(w, env)
        self.table = f"{config['names']['schema']}.state_probe"

    def prepare(self) -> None:
        self.engine.run("CREATE TABLE IF NOT EXISTS IDENTIFIER(:table) "
                        "(key STRING, value STRING, written_at TIMESTAMP, public_from DATE)", {"table": self.table})

    def write(self, key: str, value: str) -> None:
        self.engine.run("INSERT INTO IDENTIFIER(:table) VALUES (:key, :value, current_timestamp(), current_date())",
                        {"table": self.table, "key": key, "value": value})

    def read(self, key: str) -> str | None:
        rows = self.engine.run("SELECT value FROM IDENTIFIER(:table) WHERE key = :key",
                               {"table": self.table, "key": key}).rows
        return rows[0][0] if rows else None

    def finish(self) -> None:
        pass


class LakebaseStore:
    """A table in a small Lakebase database instance, which the probe stops when it is done."""

    def __init__(self, w):
        self.w, self.connection = w, None

    def prepare(self) -> None:
        from probe_lakebase import Unavailable
        from databricks.sdk.errors import NotFound
        from databricks.sdk.service import database
        import psycopg

        try:
            try:
                instance = self.w.database.get_database_instance(LAKEBASE_INSTANCE)
                if instance.stopped:
                    self.w.database.update_database_instance(
                        LAKEBASE_INSTANCE, database.DatabaseInstance(name=LAKEBASE_INSTANCE, stopped=False), "stopped")
                    instance = self.w.database.wait_get_database_instance_database_available(LAKEBASE_INSTANCE)
            except NotFound:
                instance = self.w.database.create_database_instance_and_wait(
                    database.DatabaseInstance(name=LAKEBASE_INSTANCE, capacity=LAKEBASE_CAPACITY),
                    timeout=dt.timedelta(minutes=MINUTES))
            credential = self.w.database.generate_database_credential(instance_names=[LAKEBASE_INSTANCE],
                                                                       request_id=uuid.uuid4().hex)
            self.connection = psycopg.connect(host=instance.read_write_dns, dbname=POSTGRES_DATABASE,
                                              user=self.w.current_user.me().user_name, password=credential.token,
                                              sslmode="require", autocommit=True)
            self.connection.execute("CREATE TABLE IF NOT EXISTS state_probe "
                                    "(key text PRIMARY KEY, value text, written_at timestamptz DEFAULT now())")
        except Exception as error:  # a workspace without Lakebase, a quota or a refused connection
            raise Unavailable(" ".join(str(error).split())[:300] or type(error).__name__) from error

    def write(self, key: str, value: str) -> None:
        self.connection.execute("INSERT INTO state_probe (key, value) VALUES (%s, %s)", (key, value))

    def read(self, key: str) -> str | None:
        row = self.connection.execute("SELECT value FROM state_probe WHERE key = %s", (key,)).fetchone()
        return row[0] if row else None

    def finish(self) -> None:
        from databricks.sdk.service import database

        if self.connection is not None:
            self.connection.close()
        try:
            self.w.database.update_database_instance(
                LAKEBASE_INSTANCE, database.DatabaseInstance(name=LAKEBASE_INSTANCE, stopped=True), "stopped")
        except Exception:  # an instance the probe never made has nothing to stop
            pass


def live_stores(env: dict, config: dict) -> dict:
    w = workspace_client(env)
    return {"strata.ops": WarehouseStore(w, env, config), "Lakebase": LakebaseStore(w)}
