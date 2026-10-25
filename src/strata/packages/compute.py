"""Review type and market approach, computed from the thresholds file (config/thresholds.toml, [review] and
[market_approach]; ticket 15).

Each rule reads its values from the file, never from code, and returns the value with the threshold, the
rating it assumed and the file's source line, so the package workspace's computed note can state the rule
and its source. Review type is computed from the whole package's estimated amount, never per lot, so the
number of lots never changes it: Strata never suggests dividing a contract to stay under a review threshold.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from strata.config import Thresholds

PRIOR, POST = "Prior", "Post"
INTERNATIONAL, NATIONAL = "Open - International", "Open - National"


@dataclass(frozen=True)
class Computed:
    value: str
    rule: dict


def _day(value) -> str | None:
    if isinstance(value, dt.date):
        return value.isoformat()
    return str(value) if value else None


def _section(thresholds: Thresholds, name: str) -> dict:
    section = thresholds.values.get(name)
    return section if isinstance(section, dict) else {}


def review(thresholds: Thresholds, values: dict) -> Computed | None:
    """Prior when the whole estimated amount is at or above the category's prior review threshold for the
    assumed risk rating; Post below it. None when the category, the amount or the threshold is missing."""
    section = _section(thresholds, "review")
    rating = section.get("risk_rating")
    category, amount = values.get("category"), values.get("estimated_amount_usd")
    limit = ((section.get("prior_from_usd") or {}).get(rating) or {}).get(category)
    if category is None or amount is None or limit is None:
        return None
    rule = {"category": category, "threshold_usd": limit, "risk_rating": rating,
            "source": section.get("source"), "as_of": _day(section.get("as_of"))}
    return Computed(PRIOR if amount >= limit else POST, rule)


def market_approach(thresholds: Thresholds, values: dict) -> Computed | None:
    """Open - International when the estimated amount is at or above the country's threshold for its
    category; Open - National below it. None when the country has no threshold for the category."""
    section = _section(thresholds, "market_approach")
    country, category, amount = values.get("country"), values.get("category"), values.get("estimated_amount_usd")
    limit = ((section.get("international_from_usd") or {}).get(country) or {}).get(category)
    if country is None or category is None or amount is None or limit is None:
        return None
    rule = {"country": country, "category": category, "threshold_usd": limit,
            "source": section.get("source"), "as_of": _day(section.get("as_of"))}
    return Computed(INTERNATIONAL if amount >= limit else NATIONAL, rule)


RULES = {"review": review, "market_approach": market_approach}


def compute(rule: str, thresholds: Thresholds, values: dict) -> Computed | None:
    return RULES[rule](thresholds, values)
