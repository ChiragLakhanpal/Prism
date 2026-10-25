# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["databricks-sdk==0.156.0", "mlflow==3.16.1", "xgboost==3.4.1", "numpy==2.5.4", "pyyaml==6.0.3",
#                 "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Backtest the planned date for each STEP step for 2021 to 2025 on the shared workspace: ticket 27's live run.

Run it from the main checkout, after the live plan run (ops/plans/run_live.py, and ticket 18's run of the slice)
has filled strata.silver.plan_step_delays on the warehouse:

    uv run --script ops/estimates/step_backtest_live.py --env-file .env --years 2025

Time one test year first, as above: each step first planned that year calls find_comparables once on the
warehouse. When that year finishes in reasonable time, run all of config/models.toml's test years by leaving
--years out.

It runs the same backtests as the gate (strata.estimates.step_dates.backtest) with the live adapters: the SQL
warehouse for every read and for the results, which it appends to strata.ops.evaluation_result, and MLflow for
each test year's run, in config/models.toml's experiment. It prints each test year's counts with its MLflow run
id, then one line per step that the year scored. It exits 0 when the run finished and 2 when it could not run.
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

from strata.config import load_time_estimate  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/estimates/step_backtest_live.py", description=__doc__.split("\n\n")[0])
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

    from strata.estimates import step_dates
    from strata.estimates.tracking import MlflowTracker

    # MLflow signs in to the workspace the way the Databricks CLI does, from this process's environment.
    os.environ.update({key: value for key, value in cli_env(env, {}).items() if key.startswith("DATABRICKS_")})
    started = time.monotonic()
    try:
        engine = LiveWorkspace(env).engine()
        run_id = step_dates.backtest(engine, MlflowTracker(load_time_estimate().experiment),
                                     outcomes_through=args.outcomes_through,
                                     years=tuple(args.years) if args.years else None)
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2
    except Exception as error:  # MLflow and the SDK raise their own errors; the run stops with one sentence
        print(f"The backtest stopped before it finished: {type(error).__name__}: {str(error).rstrip('.')}.")
        return 2
    for year, record in sorted(step_dates.stored_years(engine, run_id).items()):
        print(f"{year}: {record['steps_inside_cautious']} of {record['steps_total']} steps came on or before their "
              f"cautious date, {record['steps_abstained']} got no date, MLflow run {record['mlflow_run_id']}.")
        for family, entry in step_dates.families().items():
            for step in entry["steps"]:
                key = f"{family}.{step['key']}"
                if record.get(f"{key}.n"):
                    print(f"  {key}: {record[f'{key}.inside_cautious']} of {record[f'{key}.n']} on or before the "
                          f"cautious date, typical error {record.get(f'{key}.error_cautious_days')} days against "
                          f"{record.get(f'{key}.error_plan_days')} for the plan.")
    print(f"Run {run_id} is in strata.ops.evaluation_result. It took {time.monotonic() - started:.0f} seconds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
