# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["databricks-sdk==0.156.0", "mlflow==3.16.1", "xgboost==3.4.1", "numpy==2.5.4", "pyyaml==6.0.3",
#                 "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Backtest the two rebidding models for 2021 to 2025 on the shared workspace, and register the better calibrated as
champion: ticket 28's live run.

Run it from the main checkout, after the deploy (ops/bundle/deploy.py) has made strata.ops.evaluation_result and
strata.ops.rebidding_scores and the nightly job has filled gold and silver:

    uv run --script ops/estimates/rebidding_backtest_live.py --env-file .env --years 2025

Time one test year first, as above: each package it tests calls rebidding_risk once on the warehouse, as of the
cutoff, for its baseline. When that year finishes in reasonable time, run all of config/models.toml's test years
by leaving --years out.

It runs the same backtests as the gate (src/strata/estimates/rebidding_backtest.py) with the live adapters: the SQL
warehouse for every read and for the results, which it appends to strata.ops.evaluation_result, and MLflow for each
test year's run and the champion with its model card and model_state.json, registered in Unity Catalog under
config/models.toml's rebidding registered_model (champion when no version holds that alias yet, else challenger).
It prints each test year's Brier scores and calibration errors with its MLflow run id, the champion and the version
it registered. It exits 0 when the run finished and 2 when it could not run. The nightly job's score task then
scores every planned package with the champion.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.config import load_rebidding  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/estimates/rebidding_backtest_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and sign-in")
    parser.add_argument("--outcomes-through", type=dt.date.fromisoformat,
                        help="read outcomes as of this date, such as 2026-10-24; today by default")
    parser.add_argument("--years", type=int, nargs="+",
                        help="backtest only these test years, such as 2025; config/models.toml's test_years by default")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2

    from bundle_live import LiveWorkspace, cli_env  # the Databricks SDK, which only the live run needs

    from strata.estimates import rebidding_backtest
    from strata.estimates.tracking import MlflowTracker

    os.environ.update({key: value for key, value in cli_env(env, {}).items() if key.startswith("DATABRICKS_")})
    settings = load_rebidding()
    started = time.monotonic()
    try:
        engine = LiveWorkspace(env).engine()
        run = rebidding_backtest.run(engine, MlflowTracker(settings.experiment), outcomes_through=args.outcomes_through,
                                     years=tuple(args.years) if args.years else None)
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2
    except Exception as error:  # MLflow and the SDK raise their own errors; the run stops with one sentence
        print(f"The backtest stopped before it finished: {type(error).__name__}: {str(error).rstrip('.')}.")
        return 2
    for year, record in sorted(rebidding_backtest.stored_years(engine, run.run_id).items()):
        parts = [f"{learner} Brier {record[f'{learner}_brier']}, calibration error {record[f'{learner}_calibration_error']}"
                 for learner in (*settings.learners, "baseline") if f"{learner}_brier" in record]
        print(f"{year}: {record['test_packages']} packages tested, {record['test_advertised_again']} advertised again, "
              f"{record['undecided_left_out']} undecided. {'; '.join(parts) or 'No results'}. "
              f"MLflow run {record['mlflow_run_id']}.")
    if run.version is None:
        print("No champion was trained, so none was registered. The model card says why.")
    else:
        print(f"The better calibrated model is {run.champion}. Registered {settings.registered_model} version "
              f"{run.version} as {run.alias}.")
    print(f"Run {run.run_id} is in strata.ops.evaluation_result. It took {time.monotonic() - started:.0f} seconds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
