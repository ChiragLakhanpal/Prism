# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["databricks-sdk==0.156.0", "mlflow==3.16.1", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0",
#                 "pytz==2026.5"]
# ///
"""Measure retrieval on the shared workspace, and gate a search setup: ticket 32's live run.

Run it from the main checkout, after the deploy (ops/bundle/deploy.py) has made the retrieval loop's tables, the
weekly retrieval job (bundle/retrieval.yml) has built the labeled set, and ops/documents/run_live.py has synced
the AI Search index:

    uv run --script ops/retrieval/evaluate_live.py --env-file .env --load-queries
    uv run --script ops/retrieval/evaluate_live.py --env-file .env
    uv run --script ops/retrieval/evaluate_live.py --env-file .env --gate --no-rerank

With --load-queries it loads each query in evals/retrieval_queries.toml not yet in strata.ops.retrieval_queries,
with its two query judges and its pool, which AI Search finds as the env file's token. The weekly job cannot,
because its own identity has no AI Search token, so run this whenever the search owner adds queries. It prints how
many it loaded; the rows are in strata.ops.retrieval_queries and strata.ops.retrieval_pool.

The first scores each evaluation set of the labeled set (the ICR Reviews' citations, the PADs' lessons sections and
the judged notice queries) through the replay harness with the live adapters: AI Search's hybrid query with its
reranker, as the env file's token, for the rankings; the SQL warehouse for every read and for the results, which
it appends to strata.ops.evaluation_result as the retrieval_evaluation scorer; and MLflow for each set's run. It
prints each set's precision at 10, recall at 20 and nDCG at 10.

With --gate it runs the tuning gate instead: production's setup (config/models.toml, [search.setup]) against the
candidate the flags describe, on the held-out queries. On AI Search only the reranker can change; the weights
apply where Prism fuses the rankings itself. The hindsight set is ticket 34's, so the gate says it was not
compared. It prints the verdict, and exits 0 when the candidate may ship, 1 when the gate blocks it and 2 when it
could not run.

It needs DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_TOKEN, AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import os
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.lakehouse.engine import EngineError, WarehouseEngine, http_transport  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

NEEDS = ("DATABRICKS_TOKEN", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
EXPERIMENT = "/Shared/strata/retrieval"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/retrieval/evaluate_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse, token and keys")
    parser.add_argument("--load-queries", action="store_true",
                        help="load the new queries written from award notices, with their judges and pools")
    parser.add_argument("--gate", action="store_true", help="run the tuning gate on a candidate setup")
    parser.add_argument("--no-rerank", action="store_true", help="the candidate turns the reranker off")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    missing = [key for key in NEEDS if not env.get(key)]
    if missing:
        print(f"The env file has no value for {', '.join(missing)}. Run the setup wizard first (ops/wizard/strata-setup.sh).")
        return 2

    from types import SimpleNamespace

    from bundle_live import cli_env  # the Databricks SDK, which only the live run needs

    from strata.config import load_roles, load_search
    from strata.dbx import Viewer
    from strata.estimates import retrieval
    from strata.estimates.tracking import MlflowTracker
    from strata.knowledge.search import searcher_for

    os.environ.update({key: value for key, value in cli_env(env, {}).items() if key.startswith("DATABRICKS_")})
    for key in ("DATABRICKS_HOST", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"):
        os.environ.setdefault(key, env[key])  # the searcher reads them from the environment, as the app does
    engine = WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"], http_transport(env["DATABRICKS_HOST"], env["DATABRICKS_TOKEN"]))
    viewer = Viewer(name="the env file's token", token=env["DATABRICKS_TOKEN"])
    ran_at = dt.datetime.now(dt.UTC)
    run_id = f"retrieval-{ran_at:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    current = load_search().setup
    try:
        if args.load_queries:
            from strata.knowledge.retrieval.judging import Judging

            loaded = Judging(load_roles()).load(
                engine, engine, lambda e, setup: searcher_for(SimpleNamespace(engine=e, viewer=viewer), setup=setup))
            print(f"I loaded {loaded} new queries into strata.ops.retrieval_queries, with their pools in "
                  "strata.ops.retrieval_pool.")
            return 0
        tracker = MlflowTracker(EXPERIMENT)
        if not args.gate:
            found = retrieval.evaluate(engine, tracker, run_id, ran_at, engine, setup=current,
                                       searcher=lambda e: searcher_for(SimpleNamespace(engine=e, viewer=viewer), setup=current))
            for name, measured in found.items():
                print(f"{name}: {measured.queries} queries, {measured.labels} labels; precision at 10 "
                      f"{measured.precision:.2f}, recall at 20 {measured.recall:.2f}, nDCG at 10 {measured.ndcg:.2f}.")
            print(f"Run {run_id} is in strata.ops.evaluation_result.")
            return 0
        candidate = dataclasses.replace(current, rerank=not args.no_rerank)
        verdict = retrieval.gate(engine, candidate, tracker, run_id, ran_at, engine, current=current)
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2
    except Exception as error:  # MLflow, AI Search and the SDK raise their own errors; the run stops with one sentence
        print(f"The run stopped before it finished: {type(error).__name__}: {str(error).rstrip('.')}.")
        return 2
    for loss in verdict.losses:
        print(f"Lost on {loss.query_set}, {loss.measure}: {loss.candidate:.4f} against {loss.current:.4f}.")
    print(f"Held-out set: {verdict.held_out.replace('_', ' ')}. Hindsight set: {verdict.hindsight.replace('_', ' ')}. "
          f"{'The candidate may ship.' if verdict.ships else 'The gate blocks the candidate.'} Run {run_id}.")
    return 0 if verdict.ships else 1


if __name__ == "__main__":
    sys.exit(main())
