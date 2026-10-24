"""Governance scores (CPIA and WGI) as they were public on a date.

strata.gold.governance_score keeps every version the Indicators API published. score_as_of() runs
the one definition of the join, src/strata/lakehouse/sql/governance_score_as_of.sql, so a model or a
tool asking about a past date sees the version public then and never a later revision.
"""

from __future__ import annotations

import datetime as dt
from importlib import resources

from strata.lakehouse.engine import Engine


def _sql() -> str:
    # importlib.resources rather than __file__, which serverless Python tasks do not set.
    return (resources.files("strata.lakehouse") / "sql" / "governance_score_as_of.sql").read_text()


def score_as_of(engine: Engine, country_code: str, indicator_id: str, as_of: dt.date) -> dict | None:
    """The score for the latest year public on as_of, at the version current then, or None."""
    result = engine.run(_sql(), {"country_code": country_code, "indicator_id": indicator_id, "as_of": as_of})
    return dict(zip(result.columns, result.rows[0], strict=True)) if result.rows else None
