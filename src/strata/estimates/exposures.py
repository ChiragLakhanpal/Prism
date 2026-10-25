"""The exposure log (ticket 44; docs/PLAN.md section 11, "Loops through the world"): what Strata showed whom, so its
influence on plans can be told apart from its accuracy.

An exposure is one past range (find_comparables) or one time estimate (estimate_time) the server sent a viewer for a
package with a STEP reference, in the World Bank staff view. The server's routes write it at the moment the range
reaches the viewer through the answer contract (src/strata/server/estimates.py and app.py), never the tools
themselves: the replay harness, batch scoring, the hindsight test and the nightly job call the same tools, and none
of them may write an exposure. So:

- A range shown in a preview of another view is not an exposure (the 45 design brief, decision 13). The view is the
  tool contract's view argument (ticket 09), and only staff counts.
- An abstention shows no range, so it writes nothing: below 20 comparable packages, outside what the model learned
  from, before its training date.
- A package planned from a sentence has no STEP reference, so no later plan row can be matched to it.

Each row keeps the range shown (q25 to q80, in months and days), the option chosen (the plan-date choice, middle or
eight_in_ten, with the cautious eight_in_ten when none is saved: the 26 design brief, section 6.3), the viewer's user
id and the day, and the two dates Strata offered: the middle and the 8-in-10 point counted in days from the
package's first specific procurement notice when it had been published by the as-of date, or else from the
planned notice date of its newest public plan row. A later plan row is "dated within 14 days of a date I offered"
when its planned signing date falls within estimates_loop.anchored_within_days of either
(src/strata/estimates/sql/loop/anchored.sql).

The log writes as the app's own service principal, from a background task after the answer has gone, so the page
never waits for it and a failed write never changes the answer.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources

from strata.lakehouse.engine import Engine

log = logging.getLogger("strata.estimates.exposures")
TABLE = "strata.ops.exposures"
COLUMNS = ("exposure_id", "shown_at", "exposed_on", "viewer_id", "view", "route", "as_of", "step_reference",
           "project_id", "country_code", "shown", "range_shown", "model", "model_version", "option_chosen",
           "option_saved", "start_date", "start_from", "offered_middle_on", "offered_eight_in_ten_on", "public_from")
# What each tool shows, by the name the registry gives it.
SHOWN = {"find_comparables": "past_range", "estimate_time": "time_estimate"}
POINTS = ("q25", "q50", "q75", "q80")
STAFF = "staff"  # the one view whose ranges are exposures
OPTIONS = ("middle", "eight_in_ten")
DEFAULT_OPTION = "eight_in_ten"  # the cautious date, when no choice is saved (the 26 design brief, section 6.3)


def _sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "exposures" / f"{name}.sql").read_text()


def range_shown(tool: str, result: dict) -> dict | None:
    """The points a tool's answer showed, or None when it showed no range: an abstention, or no middle."""
    if tool not in SHOWN or result.get("abstention") is not None:
        return None
    points = result.get("estimate") if tool == "estimate_time" else result.get("past_range")
    if not points or points.get("q50") is None or not points.get("days"):
        return None
    return {**{name: points[name] for name in POINTS}, "days": dict(points["days"])}


@dataclass(frozen=True)
class Shown:
    """One answer a route sent a viewer: the tool, its result, and what the request said."""

    tool: str
    result: dict
    step_reference: str | None
    view: str
    as_of: dt.date
    route: str
    viewer_id: str | None
    saved_option: str | None  # the viewer's saved plan-date choice for the package, if any

    def counts(self) -> bool:
        """Whether this answer is an exposure: a range, for a package with a STEP reference, in the staff view."""
        return (self.view == STAFF and bool(self.step_reference)
                and range_shown(self.tool, self.result) is not None)


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def package_facts(engine: Engine, step_reference: str, as_of: dt.date) -> dict:
    """The package's project and country from its newest public plan row, and the day its offered dates count from:
    its first specific procurement notice when public by as_of, else that plan row's planned notice date."""
    from strata.tools.find_comparables import read_package

    package = read_package(engine, step_reference, as_of) or {}
    result = engine.run(_sql("first_notice"), {"step_reference": step_reference, "as_of": as_of})
    notice = _date(result.rows[0][1]) if result.rows else None
    planned = _date(package.get("planned_notice_on"))
    start, start_from = (notice, "first_notice") if notice else (planned, "planned_notice") if planned else (None, None)
    return {"project_id": package.get("project_id"), "country_code": package.get("country_code"),
            "start_date": start, "start_from": start_from}


def row(shown: Shown, facts: dict, exposure_id: str, shown_at: dt.datetime) -> tuple:
    """The exposure's row in strata.ops.exposures."""
    points = range_shown(shown.tool, shown.result)
    estimate = shown.result.get("estimate") if shown.tool == "estimate_time" else None
    start = facts["start_date"]

    def offered(point: str) -> dt.date | None:
        return None if start is None else start + dt.timedelta(days=int(points["days"][point]))

    option = shown.saved_option if shown.saved_option in OPTIONS else DEFAULT_OPTION
    values = {"exposure_id": exposure_id, "shown_at": shown_at, "exposed_on": shown_at.astimezone(dt.UTC).date(),
              "viewer_id": shown.viewer_id, "view": shown.view, "route": shown.route, "as_of": shown.as_of,
              "step_reference": shown.step_reference, "project_id": facts["project_id"],
              "country_code": facts["country_code"], "shown": SHOWN[shown.tool],
              "range_shown": json.dumps(points, sort_keys=True),
              "model": estimate.get("model") if estimate else None,
              "model_version": int(estimate["model_version"]) if estimate and estimate.get("model_version") is not None
              else None,
              "option_chosen": option, "option_saved": shown.saved_option in OPTIONS, "start_date": start,
              "start_from": facts["start_from"], "offered_middle_on": offered("q50"),
              "offered_eight_in_ten_on": offered("q80"), "public_from": shown_at.astimezone(dt.UTC).date()}
    return tuple(values[column] for column in COLUMNS)


def _close(engine) -> None:
    close = getattr(engine, "close", None)
    if callable(close):
        close()


class ExposureLog:
    """The exposures on their way to strata.ops.exposures. engine() opens the engine that writes them, the app's own
    service principal on the App; now is the clock and new_id gives each exposure its id."""

    def __init__(self, engine: Callable[[], Engine], now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC),
                 new_id: Callable[[], str] = lambda: uuid.uuid4().hex):
        self.engine, self.now, self.new_id = engine, now, new_id

    def record(self, reader: Engine, shown: Shown) -> bool:
        """Write one exposure, reading the package's facts with reader, the viewer's own engine. Returns whether a
        row was written: nothing is written for an answer that is no exposure, or when the warehouse fails."""
        if not shown.counts():
            return False
        try:
            facts = package_facts(reader, shown.step_reference, shown.as_of)
            engine = self.engine()
            try:
                engine.insert_rows(TABLE, COLUMNS, [row(shown, facts, self.new_id(), self.now())])
            finally:
                _close(engine)
        except Exception:  # the warehouse, the network or a token: none of them may change an answer
            log.exception("I could not record that %s was shown a %s for %s.", shown.viewer_id,
                          SHOWN[shown.tool], shown.step_reference)
            return False
        return True
