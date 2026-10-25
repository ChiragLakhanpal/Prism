# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["databricks-sdk==0.156.0", "mlflow==3.16.1", "xgboost==3.4.1", "numpy==2.5.4", "pyyaml==6.0.3",
#                 "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Backtest the time estimate for 2021 to 2025 on the shared workspace, and register its model: ticket 25's
live run.

Run it from the main checkout, after the deploy (ops/bundle/deploy.py) has made strata.ops.evaluation_result
and the nightly job has filled gold and silver:

    uv run --script ops/estimates/backtest_live.py --env-file .env --years 2025

Time one test year first, as above: each package it had not seen calls find_comparables once on the
warehouse, so a year can take many statements. When that year finishes in reasonable time, run all of
config/models.toml's test years by leaving --years out.

It runs the same backtests as the gate (src/strata/estimates/backtest.py) with the live adapters: the SQL
warehouse for every read and for the results, which it appends to strata.ops.evaluation_result, and
MLflow for each test year's run, the model and its model card, with the model registered in Unity
Catalog under config/models.toml's registered_model (champion when no version holds that alias yet,
else challenger). It prints each test year's counts with its MLflow run id, the version it registered,
the track record and the model card's coverage section. It exits 0 when the run finished and 2 when it
could not run.
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
    parser = argparse.ArgumentParser(prog="ops/estimates/backtest_live.py", description=__doc__.split("\n\n")[0])
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

    from strata.config import load_thresholds
    from strata.estimates import backtest, model_card
    from strata.estimates.tracking import MlflowTracker

    # MLflow signs in to the workspace the way the Databricks CLI does, from this process's environment.
    os.environ.update({key: value for key, value in cli_env(env, {}).items() if key.startswith("DATABRICKS_")})
    settings = load_time_estimate()
    started = time.monotonic()
    try:
        engine = LiveWorkspace(env).engine()
        run = backtest.run(engine, MlflowTracker(settings.experiment), outcomes_through=args.outcomes_through,
                           years=tuple(args.years) if args.years else None)
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2
    except Exception as error:  # MLflow and the SDK raise their own errors; the run stops with one sentence
        print(f"The backtest stopped before it finished: {type(error).__name__}: {str(error).rstrip('.')}.")
        return 2
    thresholds = load_thresholds()
    for year, record in sorted(backtest.stored_years(engine, run.run_id).items()):
        if "abstention" in record:
            print(f"{year}: no model, because {model_card.no_model_reason(record['abstention'], thresholds)}. "
                  f"MLflow run {record['mlflow_run_id']}.")
        else:
            print(f"{year}: {record['m']} of {record['n']} packages it had not seen finished inside the 8-in-10 range "
                  f"(coverage {record.get('coverage')}), MLflow run {record['mlflow_run_id']}.")
    if run.version is None:
        print("No model was trained for today, so none was registered. The model card says why.")
    else:
        print(f"Registered {settings.registered_model} version {run.version} as {run.alias}.")
    print(backtest.track_record_sentence(engine))
    print(run.card[run.card.index("## Coverage"):run.card.index("## Track record")].strip())
    print(f"Run {run.run_id} is in strata.ops.evaluation_result. It took {time.monotonic() - started:.0f} seconds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
