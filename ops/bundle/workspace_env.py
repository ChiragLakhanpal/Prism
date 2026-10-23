"""The env file the bundle commands read: the workspace's address, its SQL warehouse and a way to sign in.

deploy.py and check.py both call load_workspace_env(), so they stop the same way, with one
sentence, before anything reaches the workspace. It uses ticket 03's reader (ops/dayone/dayone.py)
and only the standard library.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAYONE = HERE.parents[1] / "ops" / "dayone"
if str(DAYONE) not in sys.path:
    sys.path.insert(0, str(DAYONE))

import dayone  # noqa: E402

NEEDS = ["DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID"]
SIGN_IN = "DATABRICKS_TOKEN (or DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET)"


class WorkspaceEnvError(Exception):
    """An env file the bundle commands cannot use, with what to do about it."""


def load_workspace_env(path: Path | None) -> dict[str, str]:
    """The env file's values, once it names the host, the warehouse, and a token or a service principal."""
    path = path or dayone.default_env_path()
    if not Path(path).is_file():
        raise WorkspaceEnvError(f"There is no env file at {path}. {dayone.WIZARD_FIRST}")
    env = dayone.load_env(path)
    missing = dayone.missing_keys(env, NEEDS)
    if not env.get("DATABRICKS_TOKEN") and not (env.get("DATABRICKS_CLIENT_ID") and env.get("DATABRICKS_CLIENT_SECRET")):
        missing.append(SIGN_IN)
    if missing:
        raise WorkspaceEnvError(f"{path} has no value for {', '.join(missing)}. {dayone.WIZARD_FIRST}")
    return env
