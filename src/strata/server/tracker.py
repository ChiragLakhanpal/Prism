"""Where each step stands, for the tracker at the top of the package workspace (ticket 115).

The steps routes (src/strata/server/steps.py) add four columns to each step of estimate_time's step_dates, and one
value to step_dates, worked out here from STEP's records and the page's as-of date, so the browser adds no days
(CLAUDE.md rule 1):

- actual_date: when the step happened, or None. It is the step's Actual date in the package's plan. For the Signed
  Contract step, when the plan gives no actual date, it is the signing date of the package's first contract in
  strata.gold.contract that was public and signed by the as-of date (sql/tracker/signed.sql): the World Bank's
  contract awards data, or an award notice for the years those data skip. A contract from a source CONTRACT_SOURCES
  does not name is logged and left out, so the plan's own dates stand.
- actual_source: where actual_date comes from: "plan", "contract_awards" or "award_notice"; None with no date.
- state, one of STATES:
  - done: the step has an actual date.
  - unknown: the plan gives the step no date; or a later step is done while this one has no actual date, so the
    record left it blank and does not say when it happened; or the plan's Process Status says the activity ended
    (Canceled or Terminated, ENDED in strata.estimates.step_dates, or Completed) or its contract was signed (Signed,
    for the steps up to and including Signed Contract) and the step has no actual date. Such a step is never late,
    because the plan says it is no longer owed.
  - late: its planned date in the newest plan version is before the as-of date, and it has no actual date.
  - next: the first step after the last done one whose planned date has not passed, when no late step comes first.
  - planned: every step after that.
- late_days: for a late step, the calendar days from its planned date to the as-of date; otherwise None.
- status_reason (on step_dates): the plan's Process Status when it left a step with no actual date unknown, so the
  screen can say why once; otherwise None.

The plan is read as estimate_time reads a package's own plan (strata.estimates.step_dates.activities, with its SQL in
src/strata/estimates/sql/step_dates/steps.sql): its newest version public on the as-of date (ADR 0002). The Process
Status lists are check_plan's (CONTRACT_STATUSES) and step_dates' (ENDED), each defined once (CLAUDE.md rule 4). A
package from a sentence has no plan, so each of its steps is unknown.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

from strata.estimates import step_dates as dated
from strata.estimates.past_range import as_date
from strata.lakehouse.engine import Engine
from strata.tools.check_plan import CONTRACT_STATUSES, SIGNING

DONE, NEXT, PLANNED, LATE, UNKNOWN = "done", "next", "planned", "late", "unknown"
STATES = (DONE, NEXT, PLANNED, LATE, UNKNOWN)
# Where a done step's actual date comes from, by record; strata.gold.contract's source names the contract's record.
PLAN, AWARDS, NOTICE = "plan", "contract_awards", "award_notice"
CONTRACT_SOURCES = {"awards": AWARDS, "awards_fy2001_2016": AWARDS, "notices": NOTICE}
SIGNED, COMPLETED = CONTRACT_STATUSES  # in STEP's order: the contract signed, then completed

SQL = Path(__file__).resolve().parent / "sql" / "tracker"
log = logging.getLogger("strata.server.tracker")

Dates = tuple[dt.date | None, dt.date | None, str | None]  # (planned, actual, where the actual date comes from)


def settled_through(status: str | None, names: list[str]) -> int:
    """The index of the last step the plan's Process Status says is behind the activity, or -1: every step for an
    activity that ended or whose contract was completed, the steps up to the signing for a signed contract."""
    if status in dated.ENDED or status == COMPLETED:
        return len(names) - 1
    if status == SIGNED and SIGNING in names:
        return names.index(SIGNING)
    return -1


def marks(steps: list[Dates], as_of: dt.date, settled: int = -1) -> list[dict]:
    """Each step's state, late days and actual date, from its dates in STEP's order. settled is settled_through's
    index: a step up to it with no actual date is unknown, never late."""
    last_done = max((k for k, (_, actual, _) in enumerate(steps) if actual is not None), default=-1)
    current = False  # a late or next step came already: what follows waits behind it
    found = []
    for k, (planned, actual, source) in enumerate(steps):
        late_days = None
        if actual is not None:
            state = DONE
        elif k < last_done or k <= settled or planned is None:
            state = UNKNOWN
        elif planned < as_of:
            state, late_days, current = LATE, (as_of - planned).days, True
        elif not current:
            state, current = NEXT, True
        else:
            state = PLANNED
        found.append({"actual_date": actual.isoformat() if actual else None,
                      "actual_source": source if actual else None, "state": state, "late_days": late_days})
    return found


def read(engine: Engine, reference: str, as_of: dt.date, names: list[str]) -> tuple[list[Dates], str | None]:
    """Each named step's dates in the package's newest plan version public on the as-of date, with the signing from
    its contract when the plan gives none, and the plan's Process Status."""
    def rows(sql: str, **params) -> list[dict]:
        result = engine.run(sql, {**params, "as_of": as_of})
        return [dict(zip(result.columns, values)) for values in result.rows]

    own = dated.activities(rows, [reference]).get(reference)
    steps = own.steps if own else {}
    found: list[Dates] = [(steps[name].planned_on, steps[name].actual_on, PLAN) if name in steps else (None, None, None)
                          for name in names]
    if SIGNING in names and found[names.index(SIGNING)][1] is None:
        signed = rows((SQL / "signed.sql").read_text(), reference=reference)
        kind = CONTRACT_SOURCES.get(signed[0]["source"]) if signed else None
        if signed and kind is None:
            log.warning("The step tracker skipped %s's signing: strata.gold.contract source %r is not in "
                        "CONTRACT_SOURCES.", reference, signed[0]["source"])
        if kind:
            k = names.index(SIGNING)
            found[k] = (found[k][0], as_date(signed[0]["signed_on"]), kind)
    return found, own.process_status if own else None


def track(step_dates: dict | None, engine: Engine, reference: str | None, as_of: dt.date) -> dict | None:
    """estimate_time's step_dates with each step's actual_date, actual_source, state and late_days, and the
    status_reason. reference is the package's STEP reference, or None for a package from a sentence."""
    if not step_dates or not step_dates.get("steps") or not step_dates.get("family"):
        return step_dates
    by_key = {entry["key"]: entry["step_name"] for entry in dated.families()[step_dates["family"]]["steps"]}
    names = [by_key[step["step_key"]] for step in step_dates["steps"]]
    found, status = read(engine, reference, as_of, names) if reference else ([(None, None, None)] * len(names), None)
    settled = settled_through(status, names)
    marked = marks(found, as_of, settled)
    reason = status if any(mark["actual_date"] is None for mark in marked[:settled + 1]) else None
    return {**step_dates, "status_reason": reason,
            "steps": [{**step, **mark} for step, mark in zip(step_dates["steps"], marked)]}
