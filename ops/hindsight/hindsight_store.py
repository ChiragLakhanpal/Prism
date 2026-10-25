"""Where the hindsight test's commands read and write: a DuckDB file, or the shared workspace's SQL warehouse.

ops/hindsight/code.py and ops/hindsight/release_gate.py take either --database PATH, a DuckDB file such as a copy
of the fixture database, or --env-file PATH, the env file with the workspace's address, warehouse and sign-in,
which the setup wizard writes (ops/wizard/strata-setup.sh). With neither, they use the env file in the main
checkout's root.
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


class StoreError(RuntimeError):
    """The command cannot reach its store, with the sentence that says why."""


def add_arguments(parser: argparse.ArgumentParser) -> None:
    where = parser.add_mutually_exclusive_group()
    where.add_argument("--database", help="a DuckDB file to read and write, such as a copy of the fixture database")
    where.add_argument("--env-file", help="the env file with the workspace's address, warehouse and sign-in")


def live(args: argparse.Namespace) -> bool:
    return not args.database


@contextmanager
def opened(args: argparse.Namespace):
    """The engine the command reads and writes with, closed afterwards when it is a DuckDB file."""
    if args.database:
        from strata.lakehouse.engine import DuckDBEngine

        if not Path(args.database).is_file():
            raise StoreError(f"There is no DuckDB file at {args.database}.")
        with DuckDBEngine.open(Path(args.database)) as engine:
            yield engine
        return
    from workspace_env import WorkspaceEnvError, load_workspace_env

    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        raise StoreError(str(error)) from error
    from bundle_live import LiveWorkspace  # the Databricks SDK, which only the live run needs

    yield LiveWorkspace(env).engine()


def tracker(args: argparse.Namespace, experiment: str):
    """Where runs are logged: MLflow on the workspace for the env file, an in-memory stand-in for a DuckDB file."""
    from strata.estimates.tracking import MlflowTracker, OfflineTracker

    if args.database:
        return OfflineTracker()
    import os

    from bundle_live import cli_env
    from workspace_env import WorkspaceEnvError, load_workspace_env

    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        raise StoreError(str(error)) from error
    # MLflow signs in to the workspace the way the Databricks CLI does, from this process's environment.
    os.environ.update({key: value for key, value in cli_env(env, {}).items() if key.startswith("DATABRICKS_")})
    return MlflowTracker(experiment)
