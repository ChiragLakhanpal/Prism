# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["databricks-sdk==0.156.0", "mlflow==3.16.1", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0",
#                 "pytz==2026.5"]
# ///
"""Run the hindsight test for a release, and gate it: ticket 34's release-gate command.

Run it from the main checkout on every release, after the nightly job has filled gold and silver, the deploy
(ops/bundle/deploy.py) has made the hindsight test's tables, and the coders have reconciled their codings
(ops/hindsight/code.py):

    uv run --script ops/hindsight/release_gate.py --env-file .env --release 2026.11

It finds the gate set (the pilot projects with an ICR, less those left out or waiting, each listed with its
reason), replays each project as of its approval date through the replay harness with the risk-table builder, and
appends every project's scores and the release's totals to strata.ops.evaluation_result under one run id, with an
MLflow run for each project and one for the release, in the /Shared/strata/hindsight_test experiment. It prints the
report sentence, which says how many projects it found when they are fewer than expected.

Then the release gate compares the run with the champion, the newest run the gate promoted, on the same blamed
risks: the run loses when it caught fewer and McNemar's exact test gives p below hindsight.mcnemar_alpha
(config/thresholds.toml), and it must catch more blamed risks than the checklist of each sector's five commonest
risks. It exits 0 when the run passed and became the champion, 1 when the gate blocks the release, 3 when there was
nothing to compare (no blamed risks yet), and 2 when it could not run.

--database PATH runs it on a DuckDB file instead, such as a copy of the fixture database, with MLflow's offline
stand-in.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import hindsight_store as store  # noqa: E402  (it puts src/ on the path)

EXPERIMENT = "/Shared/strata/hindsight_test"
EXIT = {"promoted": 0, "lost_to_champion": 1, "did_not_beat_checklist": 1, "nothing_to_compare": 3}


def verdict(decision, alpha: float) -> str:
    """The release gate's decision in words."""
    against = (f" Against the champion run {decision.champion_run_id}, it missed {decision.champion_only} of the "
               f"{decision.pairs} blamed risks that the champion caught and caught {decision.challenger_only} that the "
               f"champion missed (McNemar's exact test, p = {decision.p_value}).") if decision.champion_run_id else ""
    if decision.reason == "promoted":
        return f"The release gate passed, and this run is the new champion.{against}"
    if decision.reason == "lost_to_champion":
        return f"The release gate blocks this release: it lost the paired comparison, with p below {alpha}.{against}"
    if decision.reason == "did_not_beat_checklist":
        return (f"The release gate blocks this release: it caught {decision.caught} blamed risks, and the checklist "
                f"caught {decision.checklist_caught}.{against}")
    return "The release gate could not judge this release: there are no blamed risks to compare yet."


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/hindsight/release_gate.py", description=__doc__.split("\n\n")[0])
    store.add_arguments(parser)
    parser.add_argument("--release", required=True, help="the release's name, such as 2026.11")
    parser.add_argument("--now", type=dt.datetime.fromisoformat, help="the run's time, in ISO form; now by default")
    args = parser.parse_args(argv)
    now = args.now or dt.datetime.now(dt.UTC)

    from strata.config import load_thresholds
    from strata.estimates import harness, hindsight
    from strata.lakehouse.engine import EngineError

    try:
        tracker = store.tracker(args, EXPERIMENT)
        with store.opened(args) as engine:
            done = hindsight.run(engine, tracker, args.release, now)
            decision = hindsight.decide(engine, done.run_id, tracker)
            projects = {segment: record for (kind, segment), record in
                        harness.segments(harness.run_rows(engine, done.run_id)).items() if kind == "project"}
    except store.StoreError as error:
        print(error)
        return 2
    except EngineError as error:
        print(f"The warehouse could not run a statement: {error}")
        return 2
    except Exception as error:  # MLflow and the SDK raise their own errors; the run stops with one sentence
        print(f"The hindsight test stopped before it finished: {type(error).__name__}: {str(error).rstrip('.')}.")
        return 2
    for line in hindsight.funnel_lines(done.gate):
        print(line)
    for project, record in sorted(projects.items()):
        print(f"  {project}: approved {record['cutoff']}, caught {record['shown']} of {record['blamed']} blamed "
              f"risks, a lesson covered {record['covered']}; MLflow run {record['mlflow_run_id']}")
    print(hindsight.report_sentence(done.record))
    print(verdict(decision, load_thresholds().value("hindsight.mcnemar_alpha")))
    print(f"Run {done.run_id} is in strata.ops.evaluation_result, with the release's MLflow run "
          f"{done.record['mlflow_run_id']}")
    return EXIT[decision.reason]


if __name__ == "__main__":
    sys.exit(main())
