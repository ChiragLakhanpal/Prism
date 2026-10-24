"""The one box's lookups (ticket 14), which the app runs as the viewer and as of the page's date.

The box's intent rules run in the browser (web/src/lib/intents.ts) and say what Enter will do. Two of its
options need a record to know where to go, and these reads give it:

- loan(engine, text, as_of): the project a loan or credit finances, from a loan number in any of the
  forms strata.lakehouse.clean reads (IDA60290, IDA-60290, IDA / 60290, 6029-KE, or bare digits, which
  may be any lender's).
- activity(engine, text, as_of): the latest published Procurement Plan that lists a STEP reference, its
  implementing agency and that agency's id in check_plan's links, and whether it is still the agency's
  latest plan, so the box opens that plan's check with the row in view.

Each query is one file in sql/lookup/, written once in Databricks SQL.
"""

from __future__ import annotations

import datetime as dt
from functools import cache
from pathlib import Path

from strata.lakehouse.clean import LENDERS, loan_number, step_reference
from strata.lakehouse.engine import Engine
from strata.tools.check_plan import agency_id

SQL = Path(__file__).resolve().parent / "sql" / "lookup"


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_query(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _iso(value) -> str | None:
    if value is None or value == "":
        return None
    return value.isoformat() if isinstance(value, dt.date) else str(value)[:10]


def loan_numbers(text: str) -> list[str]:
    """The normalized loan numbers the text can stand for: one when it names its lender, one per lender for
    bare digits, and none for text that holds no loan number of five digits or more."""
    found = loan_number(text)
    if found is None or len(found.digits) < 5:
        return []
    return [f"{found.lender}{found.digits}"] if found.lender else [f"{lender}{found.digits}" for lender in LENDERS]


def loan(engine: Engine, text: str, as_of: dt.date) -> dict | None:
    numbers = loan_numbers(text)
    if not numbers:
        return None
    rows = _rows(engine, "loan", loan_numbers=",".join(numbers), as_of=as_of)
    if not rows:
        return None
    row = rows[0]
    return {"loan_number": row["loan_number"], "loan_number_as_written": row["loan_number_as_written"],
            "project_id": row["project_id"], "project_name": row["project_name"]}


def activity(engine: Engine, text: str, as_of: dt.date) -> dict | None:
    reference = step_reference(text)
    if reference is None:
        return None
    rows = _rows(engine, "activity", reference=reference.reference, as_of=as_of)
    if not rows:
        return None
    row = rows[0]
    plan_date = _iso(row["plan_date"])
    return {"activity_reference_no": reference.reference, "project_id": row["project_id"],
            "implementing_agency": row["implementing_agency"], "agency_id": agency_id(row["implementing_agency"]),
            "plan_date": plan_date, "is_latest": plan_date == _iso(row["latest_plan_date"])}
