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
        engine = WarehouseEngine(self.env["DATABRICKS_WAREHOUSE_ID"],
                                 lambda method, path, body: self.w.api_client.do(method, path, body=body))
        engine.run(statement)
