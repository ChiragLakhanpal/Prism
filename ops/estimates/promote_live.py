# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["databricks-sdk==0.156.0", "mlflow==3.16.1", "xgboost==3.4.1", "numpy==2.5.4", "pyyaml==6.0.3",
#                 "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Sign off a challenger of the time estimate, or decide whether it becomes the champion, on the shared workspace:
ticket 44's live promotion.

Run it from the main checkout once a quarterly retrain registered a challenger (ops/estimates/backtest_live.py, or
the nightly job's score task) and the challenger has scored in shadow for a quarter:

    uv run --script ops/estimates/promote_live.py --env-file .env sign-off --role model_owner --version 2
    uv run --script ops/estimates/promote_live.py --env-file .env sign-off --role lead --version 2
    uv run --script ops/estimates/promote_live.py --env-file .env promote --version 2

A sign-off is recorded for the person the env file signs in as, in strata.ops.model_signoffs, only when
config/roles.toml names them in that role's group ([model_sign_off]); the lead must be a different person from the
model owner. promote reads the stored backtests, the shadow quarter and the sign-offs
(src/strata/estimates/promotion.py), records its decision in strata.ops.model_promotions and, when nothing refuses
it, moves the champion alias in Unity Catalog and keeps the version as champion in strata.gold.time_estimate_model.
It prints the decision and every reason code that refused it. It exits 0 when it ran, 1 when it refused a sign-off
or a promotion, and 2 when it could not run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
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
    parser = argparse.ArgumentParser(prog="ops/estimates/promote_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and sign-in")
    actions = parser.add_subparsers(dest="action", required=True)
    signing = actions.add_parser("sign-off", help="record your sign-off on a challenger version")
    signing.add_argument("--role", choices=("model_owner", "lead"), required=True)
    signing.add_argument("--version", type=int, required=True)
    deciding = actions.add_parser("promote", help="decide whether a challenger version becomes the champion")
    deciding.add_argument("--version", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2

    from bundle_live import LiveWorkspace, cli_env  # the Databricks SDK, which only the live run needs

    from strata.config import load_roles
    from strata.estimates import promotion
    from strata.estimates.tracking import MlflowTracker

    os.environ.update({key: value for key, value in cli_env(env, {}).items() if key.startswith("DATABRICKS_")})
    model = load_time_estimate().registered_model
    now = dt.datetime.now(dt.UTC)
    try:
        workspace = LiveWorkspace(env)
        engine = workspace.engine()
        if args.action == "sign-off":
            email = workspace.w.current_user.me().user_name
            try:
                signed = promotion.sign_off(engine, load_roles(), email, model, args.version, args.role, now)
            except promotion.Refused as refused:
                print(f"I did not record a sign-off: {email} is not in the {args.role} group that config/roles.toml "
                      f"names ({refused.code}).")
                return 1
            print(f"Recorded {signed['signed_by']}'s sign-off as {args.role} on {model} version {args.version}.")
            return 0
        tracker = MlflowTracker(load_time_estimate().experiment, mkdirs=workspace.w.workspace.mkdirs)
        decision = promotion.promote(engine, tracker, model, args.version, now)
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2
    except Exception as error:  # MLflow and the SDK raise their own errors; the run stops with one sentence
        print(f"The promotion stopped before it finished: {type(error).__name__}: {str(error).rstrip('.')}.")
        return 2
    if decision.promoted:
        print(f"Promoted {model} version {args.version} to champion, in place of version {decision.champion_version}.")
    else:
        print(f"I did not promote {model} version {args.version}. Reason codes: {', '.join(decision.refusals)}.")
    print(json.dumps(decision.evidence, indent=2, sort_keys=True, default=str))
    return 0 if decision.promoted else 1


if __name__ == "__main__":
    sys.exit(main())
