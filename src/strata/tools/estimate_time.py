"""estimate_time: the planned date for each STEP step of one package (ticket 27).

The registry (config/tools.toml) defines the tool; this module is its adapter. It finds the package's comparable
packages with find_comparables' own adapter, for the same criteria, and dates each step with
strata.estimates.step_dates, which picks the package's method family from the step-label registry (by its plan's
STEP table, or with no plan row by its category and Method) and holds the model, its thresholds and its rules. The
result's step_dates field carries both choices, middle and cautious, so a screen switches between them with no
second call, and its summary makes every date and count citable. Ticket 26 adds the time estimate itself to this
tool; the step dates stay in step_dates.

The call's view is returned with the result but not applied until ticket 40.
"""

from __future__ import annotations

import datetime as dt
import logging

from strata.config import load_sources, load_tools
from strata.estimates import step_dates as model
from strata.lakehouse.engine import EngineError
from strata.tools.find_comparables import find_comparables
from strata.tools.registry import Call, ToolError

TOOL = "estimate_time"
log = logging.getLogger("strata.tools.estimate_time")


def _sources() -> list[dict]:
    registry = load_sources()
    return [{"key": key, "dataset_name": registry[key].dataset_name} for key in load_tools()[TOOL].sources]


def estimate_time(call: Call, step_reference: str | None = None, method: str | None = None,
                  category: str | None = None, market_approach: str | None = None, review_type: str | None = None,
                  size_from_usd: float | None = None, size_to_usd: float | None = None, country: str | None = None,
                  notice_from: dt.date | None = None, notice_to: dt.date | None = None,
                  start_date: dt.date | None = None) -> dict:
    """Section 2's planned date for each step, as of call.as_of. With no step_reference, for a package someone is
    planning, the category and method come from the call."""
    settings = model.Settings.read(call.thresholds)
    window = settings.start_range(call.as_of)
    if start_date is not None and not window["from"] <= start_date.isoformat() <= window["to"]:
        raise ToolError(f"estimate_time takes a start_date from {window['from']} to {window['to']}, not {start_date}.")
    found = find_comparables(call, step_reference=step_reference, method=method, category=category,
                             market_approach=market_approach, review_type=review_type, size_from_usd=size_from_usd,
                             size_to_usd=size_to_usd, country=country, notice_from=notice_from, notice_to=notice_to)
    package, sources = found["package"], _sources()
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "package": package,
             "sources": sources, "records_through": found["records_through"]}
    if found["abstention"] and found["abstention"]["reason"] == "unknown_package":
        return {**empty, "step_dates": None, "abstention": found["abstention"]}
    criteria = found["criteria"] or {}
    category_now = package["category"] if package else criteria.get("category")
    method_now = package["method"] if package else criteria.get("method")

    def rows(sql: str, **params) -> list[dict]:
        result = call.engine.run(sql, {**params, "as_of": call.as_of})
        return [dict(zip(result.columns, values)) for values in result.rows]

    comparables = [row["step_reference"] for row in found["rows"]]
    try:
        track = model.track_record(call.engine, call.as_of, settings)
    except EngineError:  # a viewer who cannot read strata.ops still gets the dates, with no track record line
        log.warning("I could not read the step backtests' track record for %s.", call.viewer.name, exc_info=True)
        track = None
    dated = model.step_dates(rows, category=category_now, method=method_now,
                             package_reference=package["step_reference"] if package else None,
                             comparables=comparables, as_of=call.as_of, start_date=start_date, settings=settings,
                             track=track, sources=[source["key"] for source in sources])
    left_out = dated.pop("not_used", [])
    coverage = {"matched": len(comparables), "used": len(comparables) - len(left_out),
                "not_used": [{"reason": model.NO_PLAN_DATES, "count": len(left_out),
                              "evidence_ids": [f"strata.gold.package:{reference}" for reference in left_out]}]
                if left_out else []}
    return {**empty, "coverage": coverage, "step_dates": dated, "abstention": None}
