"""What the check-your-criteria tools share (ticket 31): compare_criteria, rejected_bids and compare_cost_estimates.

Each takes the comparable packages find_comparables returned as STEP references joined by commas, so the
reference class is defined once, and each states the day its records run through as find_comparables does, so a
section that shows all three gives one date (CLAUDE.md rule 4).
"""

from __future__ import annotations

import datetime as dt
from importlib import resources

from strata.config import load_sources, load_tools
from strata.tools.registry import Call


def sql(folder: str, name: str) -> str:
    return (resources.files("strata.tools") / "sql" / folder / f"{name}.sql").read_text()


def rows(call: Call, folder: str, name: str, **params) -> list[dict]:
    """One query's rows as dicts, read as of the call's date."""
    result = call.engine.run(sql(folder, name), {"as_of": call.as_of, **params})
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def iso(value) -> str | None:
    if value is None or value == "":
        return None
    return value.isoformat()[:10] if isinstance(value, dt.date) else str(value)[:10]


def flag(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def references(text: str) -> list[str]:
    """The STEP references a call names, in order, each once."""
    return list(dict.fromkeys(part.strip() for part in text.split(",") if part.strip()))


def sources(tool: str) -> list[dict]:
    """The tool's sources from its registry entry, each with its dataset name for the source line."""
    registry = load_sources()
    return [{"key": key, "dataset_name": registry[key].dataset_name} for key in load_tools()[tool].sources]


def records_through(call: Call) -> str | None:
    """The day the records run through on the call's as-of date: find_comparables' own query, so the date is
    defined once ("Records run through ...")."""
    found = rows(call, "find_comparables", "records_through")
    return iso(found[0]["records_through"]) if found else None


def signed(call: Call, refs: list[str]) -> dict[str, bool]:
    """Whether each named package was signed by the as-of date, by find_comparables' rule (sql/shared)."""
    if not refs:
        return {}
    return {row["step_reference"]: flag(row["signed_in_awards"]) or flag(row["signed_in_award_notice"])
            for row in rows(call, "shared", "signed_packages", refs=",".join(refs))}
