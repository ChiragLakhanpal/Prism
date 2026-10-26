# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Pull the proposal's measures from the shared workspace into docs/proposal/snapshot.json (ticket 46).

Run it from the main checkout, after the nightly job, the full gate, the backtests, the hindsight test and the cost
pull have each run at least once:

    uv run --script ops/proposal/pull_live.py --env-file .env

It runs every query in docs/proposal/results.toml on the workspace's SQL warehouse, with the env file's token, and
writes one dated snapshot. Then `uv run python -m strata.proposal build` writes docs/proposal.md from it. It prints
each result the workspace has not measured yet, which the build would stop on, and exits 1 when there is one.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.lakehouse.engine import EngineError, WarehouseEngine, http_transport  # noqa: E402
from strata.proposal import snapshot  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

NEEDS = ("DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_TOKEN")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/proposal/pull_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and token")
    parser.add_argument("--out", default=str(snapshot.SNAPSHOT_FILE), help="where to write the snapshot")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    missing = [key for key in NEEDS if not env.get(key)]
    if missing:
        print(f"The env file has no value for {', '.join(missing)}. Run the setup wizard first "
              "(ops/wizard/strata-setup.sh).")
        return 2
    engine = WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"], http_transport(env["DATABRICKS_HOST"],
                                                                            env["DATABRICKS_TOKEN"]))
    try:
        found = snapshot.pull(engine, dt.date.today(), source="workspace")
    except EngineError as error:
        print(f"I could not pull the measures: {error}")
        return 2
    out = snapshot.write(found, Path(args.out))
    waiting = [key for key, result in found["results"].items() if not result["measured"]]
    print(f"Wrote {out}.")
    if waiting:
        print("The workspace has not measured these yet, so the build would stop on any sentence that cites them: "
              + ", ".join(waiting) + ".")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
