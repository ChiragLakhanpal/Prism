"""Where each step stands, for the tracker at the top of the package workspace (ticket 115).

The steps routes (src/strata/server/steps.py) add three columns to each step of estimate_time's step_dates, worked
out here from the package's own plan and the page's as-of date, so the browser adds no days (CLAUDE.md rule 1):

- actual_date: the step's Actual date in the plan, STEP's own record of when it happened, or None.
- state, one of STATES:
  - done: the plan gives the step's actual date.
  - unknown: the plan gives the step no date, or a later step is done while this one has no actual date, so the
    plan left it blank and does not say when it happened.
  - late: its planned date in the newest plan version is before the as-of date, and it has no actual date.
  - next: the first step after the last done one whose planned date has not passed, when no late step comes first.
  - planned: every step after that.
- late_days: for a late step, the calendar days from its planned date to the as-of date; otherwise None.

The plan is read as estimate_time reads a package's own plan (strata.estimates.step_dates.activities, with its SQL in
src/strata/estimates/sql/step_dates/steps.sql): its newest version public on the as-of date (ADR 0002). Only the plan
counts as the record of a step. A contract in the Contract Awards dataset does not mark the signing done, so the
tracker says what the plan check says about the same plan (check_plan's completion_passed_no_contract). A package
from a sentence has no plan, so each of its steps is unknown.
"""

from __future__ import annotations

import datetime as dt

from strata.estimates import step_dates as dated
from strata.lakehouse.engine import Engine

DONE, NEXT, PLANNED, LATE, UNKNOWN = "done", "next", "planned", "late", "unknown"
STATES = (DONE, NEXT, PLANNED, LATE, UNKNOWN)

Dates = tuple[dt.date | None, dt.date | None]  # (planned, actual) in the plan


def marks(steps: list[Dates], as_of: dt.date) -> list[dict]:
    """Each step's state, late days and actual date, from its planned and actual dates in STEP's order."""
    last_done = max((k for k, (_, actual) in enumerate(steps) if actual is not None), default=-1)
    current = False  # a late or next step came already: what follows waits behind it
    found = []
    for k, (planned, actual) in enumerate(steps):
        late_days = None
        if actual is not None:
            state = DONE
        elif k < last_done or planned is None:
            state = UNKNOWN
        elif planned < as_of:
            state, late_days, current = LATE, (as_of - planned).days, True
        elif not current:
            state, current = NEXT, True
        else:
            state = PLANNED
        found.append({"actual_date": actual.isoformat() if actual else None, "state": state, "late_days": late_days})
    return found


def plan_dates(engine: Engine, reference: str, as_of: dt.date, names: list[str]) -> list[Dates]:
    """Each named step's planned and actual date in the package's newest plan version public on the as-of date."""
    def rows(sql: str, **params) -> list[dict]:
        result = engine.run(sql, {**params, "as_of": as_of})
        return [dict(zip(result.columns, values)) for values in result.rows]

    own = dated.activities(rows, [reference]).get(reference)
    steps = own.steps if own else {}
    return [(steps[name].planned_on, steps[name].actual_on) if name in steps else (None, None) for name in names]


def track(step_dates: dict | None, engine: Engine, reference: str | None, as_of: dt.date) -> dict | None:
    """estimate_time's step_dates with each step's actual_date, state and late_days. reference is the package's STEP
    reference, or None for a package from a sentence."""
    if not step_dates or not step_dates.get("steps") or not step_dates.get("family"):
        return step_dates
    by_key = {entry["key"]: entry["step_name"] for entry in dated.families()[step_dates["family"]]["steps"]}
    names = [by_key[step["step_key"]] for step in step_dates["steps"]]
    found = plan_dates(engine, reference, as_of, names) if reference else [(None, None)] * len(names)
    return {**step_dates, "steps": [{**step, **mark} for step, mark in zip(step_dates["steps"], marks(found, as_of))]}
