# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Code which risks each completion report blamed, for the hindsight test: ticket 34's coding tool.

Two people read each gate-set project's ICR on their own. Each stores which risk factors on the closed list
(config/lessons.toml) it blamed; every other factor is stored as not blamed:

    uv run --script ops/hindsight/code.py --env-file .env code --project P123456 \\
        --coder name@worldbank.org --name "Their Name" --blamed cost_estimates,permits_before_award

Where the two differ, one person reads the ICR Review on the factors they differ on, and it settles them:

    uv run --script ops/hindsight/code.py --env-file .env review --project P123456 \\
        --coder name@worldbank.org --name "Their Name" --blamed permits_before_award

Then reconcile stores each project's blamed risks and each pair of coders' agreement (Cohen's kappa, withheld below
20 pairs of answers), and status lists the gate-set projects with how far each has got, never what anyone coded:

    uv run --script ops/hindsight/code.py --env-file .env reconcile
    uv run --script ops/hindsight/code.py --env-file .env status

--database PATH works on a DuckDB file instead, such as a copy of the fixture database. The command exits 0 when it
did what was asked, 2 when it refused or could not reach its store.
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ops/hindsight/code.py", description=__doc__.split("\n\n")[0])
    store.add_arguments(parser)
    parser.add_argument("--now", type=dt.datetime.fromisoformat, help="the time to store, in ISO form; now by default")
    actions = parser.add_subparsers(dest="action", required=True)
    for name, about in (("code", "store your reading of a project's ICR"),
                        ("review", "store the ICR Review's reading where the two coders differ")):
        action = actions.add_parser(name, help=about)
        action.add_argument("--project", required=True, help="the project ID, such as P123456")
        action.add_argument("--coder", required=True, help="your email")
        action.add_argument("--name", required=True, help="your name")
        action.add_argument("--blamed", default="", help="the blamed risk factors' keys, separated by commas")
    actions.add_parser("reconcile", help="store each project's blamed risks and the coders' agreement")
    actions.add_parser("status", help="list the gate-set projects and how far each has got")
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    now = args.now or dt.datetime.now(dt.UTC)
    from strata.estimates import hindsight_coding

    try:
        with store.opened(args) as engine:
            if args.action in ("code", "review"):
                reading = "icr" if args.action == "code" else "icr_review"
                blamed = [key for key in args.blamed.split(",") if key.strip()]
                coding = hindsight_coding.code(engine, args.project, hindsight_coding.Coder(args.coder, args.name),
                                               blamed, now=now, reading=reading)
                what = "ICR" if reading == "icr" else "ICR Review"
                print(f"Stored your reading of {args.project}'s {what} ({coding}): "
                      f"{len(blamed)} blamed risk factors.")
                return 0
            if args.action == "reconcile":
                done = hindsight_coding.reconcile(engine, now)
                print(f"Reconciled {len(done.reconciled)} projects; {len(done.waiting)} are waiting.")
                for row in done.waiting:
                    print(f"  {row['project_id']}: {WAITING[row['reason']]}")
                for pair in done.agreement:
                    kappa = (f"Cohen's kappa {pair['kappa']:.2f}" if pair["kappa"] is not None
                             else "Cohen's kappa withheld, too few pairs")
                    print(f"  {pair['coder_a']} and {pair['coder_b']} agreed on {pair['agree']} of {pair['pairs']} "
                          f"answers over {pair['projects']} projects; {kappa}.")
                return 0
            from strata.estimates import hindsight

            gate = hindsight.gate_set(engine, now.date())
            for line in hindsight.funnel_lines(gate):
                print(line)
            return 0
    except (store.StoreError, hindsight_coding.Refused) as error:
        print(error)
        return 2


WAITING = {"one_coder": "one coder has read its ICR so far.",
           "icr_review_unread": "the coders differ, and no one has read its ICR Review yet."}


if __name__ == "__main__":
    sys.exit(main())
