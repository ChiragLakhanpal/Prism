# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Let the lesson reviewer groups write the lesson review tables on the shared workspace (ticket 29).

Run it from the main checkout once the deploy (ops/bundle/deploy.py) has made the strata catalog and its tables,
and again whenever config/roles.toml names a new reviewer group:

    uv run --script ops/lessons/grant_reviewers.py --env-file .env

It runs strata.knowledge.lessons.grants.reviewer_grants on the SQL warehouse: SELECT and MODIFY on the five
lesson review tables in strata.ops for each workspace group the roles file names for lesson review. The groups
must exist in the workspace first. It exits 0 when every grant ran and 2 when it could not run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.config import load_roles  # noqa: E402
from strata.knowledge.lessons.grants import reviewer_grants  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/lessons/grant_reviewers.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and sign-in")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    from bundle_live import LiveWorkspace  # the Databricks SDK, which only the live run needs

    engine = LiveWorkspace(env).engine()
    statements = reviewer_grants(load_roles())
    try:
        for statement in statements:
            engine.run(statement, {})
    except EngineError as error:
        print(f"The warehouse refused a grant: {error}")
        return 2
    print(f"I ran {len(statements)} grants for the lesson reviewer groups in config/roles.toml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
