# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "psycopg[binary]==3.3.6"]
# ///
"""The Lakebase probe: strata.ops or a Lakebase database for app state (docs/PLAN.md section 18).

Run it from the main checkout after the wizard, before ticket 15 writes the first app state:

    uv run --script ops/app/probe_lakebase.py --env-file .env

It times the same small job in each store: write one row, then read it back, ten times, after
one first statement that wakes the store up. It applies the rule in docs/app-state.md, with the
budget in config/thresholds.toml (app_state.round_trip_budget_ms), and writes the times and the
chosen store into docs/app-state.md. When Lakebase wins, it also writes
docs/adr/0005-app-state-lives-in-lakebase.md. --dry-run prints a result from canned times and
writes nothing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import statistics
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
from strata.config import load_thresholds  # noqa: E402

DOCUMENT = REPO / "docs" / "app-state.md"
ADR = "adr/0005-app-state-lives-in-lakebase.md"
OPS, LAKEBASE = "strata.ops", "Lakebase"
ROUNDS = 10
BLOCK = re.compile(r"(<!-- app-state:result -->\n).*?(<!-- /app-state:result -->)", re.S)


class Unavailable(Exception):
    """The store could not be made or reached, with the reason the workspace gave."""


@dataclass
class Timing:
    store: str
    first_ms: float | None = None
    round_trips_ms: list[float] = field(default_factory=list)
    unavailable: str | None = None

    @property
    def middle_ms(self) -> float | None:
        return statistics.median(self.round_trips_ms) if self.round_trips_ms else None

    def sentence(self) -> str:
        if self.unavailable:
            return f"{self.store}: I could not make a database. {self.unavailable}"
        return (f"{self.store}: the first statement took {self.first_ms:,.0f} ms; a write and a read took "
                f"{self.middle_ms:,.0f} ms in the middle of {len(self.round_trips_ms)} tries, and "
                f"{max(self.round_trips_ms):,.0f} ms at most.")


@dataclass
class Outcome:
    chosen: str
    budget_ms: int
    timings: list[Timing]

    def reason(self) -> str:
        ops, lakebase = self.timings
        if self.chosen == LAKEBASE:
            return (f"strata.ops took {ops.middle_ms:,.0f} ms in the middle, over the budget of {self.budget_ms:,} ms, "
                    f"and Lakebase took {lakebase.middle_ms:,.0f} ms, within it.")
        if ops.middle_ms is not None and ops.middle_ms <= self.budget_ms:
            return f"strata.ops took {ops.middle_ms:,.0f} ms in the middle, within the budget of {self.budget_ms:,} ms."
        if lakebase.unavailable:
            return "strata.ops was over the budget, and I could not make a Lakebase database to compare."
        return (f"Neither store was within the budget of {self.budget_ms:,} ms, so strata.ops stays, because "
                "Lakebase would add a second store without making state feel immediate.")


def budget_ms() -> int:
    return load_thresholds().value("app_state.round_trip_budget_ms")


def time_store(name: str, store, clock: Callable[[], float], rounds: int = ROUNDS) -> Timing:
    timing = Timing(name)
    try:
        started = clock()
        store.prepare()
        timing.first_ms = (clock() - started) * 1000
        for _ in range(rounds):
            key = uuid.uuid4().hex
            started = clock()
            store.write(key, "probe")
            if store.read(key) != "probe":
                raise Unavailable("A row I wrote did not come back.")
            timing.round_trips_ms.append((clock() - started) * 1000)
    except Unavailable as reason:
        timing.unavailable, timing.round_trips_ms = str(reason), []
    finally:
        store.finish()
    return timing


def check(stores: dict, budget: int, clock: Callable[[], float] = time.monotonic) -> Outcome:
    ops, lakebase = time_store(OPS, stores[OPS], clock), time_store(LAKEBASE, stores[LAKEBASE], clock)
    ops_over = ops.middle_ms is None or ops.middle_ms > budget
    lakebase_within = lakebase.middle_ms is not None and lakebase.middle_ms <= budget
    return Outcome(LAKEBASE if ops_over and lakebase_within else OPS, budget, [ops, lakebase])


def fields(outcome: Outcome, day: str) -> list:
    return [("Status", "run"),
            ("Chosen store", f"{outcome.chosen}. {outcome.reason()}"),
            ("Times", [timing.sentence() for timing in outcome.timings]),
            ("Last run", dayone.long_date(dt.date.fromisoformat(day)))]


def adr(outcome: Outcome, day: str) -> str:
    ops, lakebase = outcome.timings
    return f"""# App state lives in Lakebase

On {dayone.long_date(dt.date.fromisoformat(day))}, the Lakebase probe (`ops/app/probe_lakebase.py`) timed a write and a read of one row in each store. {ops.sentence()} {lakebase.sentence()} The budget for following a project or marking a draft as checked is {outcome.budget_ms:,} ms (`app_state.round_trip_budget_ms` in `config/thresholds.toml`), so app state lives in a Lakebase database instead of `strata.ops`, as the rule in `docs/app-state.md` says.

## Consequences

- Follows, packages, drafts and their states, uploads and feedback live in Lakebase. Usage events, agent runs and every measure stay in `strata.ops`, because the dashboard reads them there.
- The app reaches Lakebase with a database credential for each viewer, and each table keeps the uploader's team rule (CLAUDE.md rule 8) in the database itself.
- Every row still keeps the day it became public (ADR 0002), and the deploy creates the tables from one definition each.
"""


def record(document: Path, outcome: Outcome, day: str | None = None) -> None:
    """Write the result block, and the ADR when Lakebase wins."""
    day = day or dt.date.today().isoformat()
    text = document.read_text()
    if not BLOCK.search(text):
        raise dayone.DayOneError(f"{document} has no app-state:result block.")
    document.write_text(BLOCK.sub(lambda m: m[1] + dayone.render_fields(fields(outcome, day)) + m[2], text))
    if outcome.chosen == LAKEBASE:
        path = document.parent / ADR
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(adr(outcome, day))


class CannedClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Canned:
    """A store with the times a run might give, on a clock of its own, for --dry-run."""

    def __init__(self, clock: CannedClock, first_ms: float, each_ms: float):
        self.clock, self.first_ms, self.each_ms, self.rows = clock, first_ms, each_ms, {}

    def prepare(self):
        self.clock.now += self.first_ms / 1000

    def write(self, key, value):
        self.clock.now += self.each_ms / 2000
        self.rows[key] = value

    def read(self, key):
        self.clock.now += self.each_ms / 2000
        return self.rows.get(key)

    def finish(self):
        pass


def main(argv: list[str] | None = None, stores: dict | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's .env, which the wizard filled. That file is the default.")
    parser.add_argument("--document", type=Path, default=DOCUMENT, help="Where to write the result.")
    parser.add_argument("--dry-run", action="store_true", help="Use canned stores, print the result, write nothing.")
    args = parser.parse_args(argv)

    clock = time.monotonic
    if args.dry_run:
        clock = CannedClock()
        stores = {OPS: Canned(clock, 4000, 400), LAKEBASE: Canned(clock, 900, 30)}
    elif stores is None:
        from workspace_env import WorkspaceEnvError, load_workspace_env

        try:
            env = load_workspace_env(args.env_file)
        except WorkspaceEnvError as error:
            print(error, file=sys.stderr)
            return 2
        from app_live import live_stores

        stores = live_stores(env, dayone.load_config())
    outcome = check(stores, budget_ms(), clock)
    print(dayone.render_fields(fields(outcome, dt.date.today().isoformat())), end="")
    if args.dry_run:
        print("This was a dry run, so I wrote nothing.")
        return 0
    record(args.document, outcome)
    print(f"I wrote this result in {args.document}.")
    if outcome.chosen == LAKEBASE:
        print(f"Lakebase won, so I also wrote {args.document.parent / ADR}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
