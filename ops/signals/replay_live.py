# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["databricks-sdk==0.156.0", "mlflow==3.16.1", "xgboost==3.4.1", "numpy==2.5.4", "pyyaml==6.0.3",
#                 "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Replay the signals' checks on the shared workspace, for the track record the Following page states: ticket 37's
live run.

Run it from the main checkout, after the nightly job has filled the loan history, the plans and the ISRs on the
warehouse:

    uv run --script ops/signals/replay_live.py --env-file .env

It runs the same replay as the gate (strata.estimates.signals_track.backtest) with the live adapters: the SQL
warehouse for every read and for the results, which it appends to strata.ops.evaluation_result, and MLflow for the
run, in config/models.toml's experiment. It prints the counts for each status with the MLflow run id. It exits 0
when the run finished and 2 when it could not run. The nightly job's score task runs it once the stored record is
signals.track_record_every_days old (ticket 43).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.config import load_time_estimate  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/signals/replay_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and sign-in")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2

    from bundle_live import LiveWorkspace, cli_env  # the Databricks SDK, which only the live run needs

    from strata.estimates import signals_track
    from strata.estimates.tracking import MlflowTracker

    os.environ.update({key: value for key, value in cli_env(env, {}).items() if key.startswith("DATABRICKS_")})
    try:
        workspace = LiveWorkspace(env)
        engine = workspace.engine()
        tracker = MlflowTracker(load_time_estimate().experiment, mkdirs=workspace.w.workspace.mkdirs)
        signals_track.backtest(engine, tracker)
        found = signals_track.stored(engine)
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2
    except Exception as error:  # MLflow and the SDK raise their own errors; the run stops with one sentence
        print(f"The replay stopped before it finished: {type(error).__name__}: {str(error).rstrip('.')}.")
        return 2
    print(f"Replayed on {', '.join(found['dates'])}, {found['cohort']} projects, MLflow run {found['mlflow_run_id']}.")
    for status, counts in found["status"].items():
        print(f"{status}: {counts['k']} of {counts['n']} projects later extended their closing date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
