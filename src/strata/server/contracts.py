"""A project's contracts (ticket 138): the one definition the Timeline tab's Records lane and the Connections tab both
read, so the two tabs never count a project's contracts two ways.

A project's contracts on a date are its rows in strata.gold.contract that were public then (ADR 0002), from every
source that table holds (src/strata/lakehouse/gold/contract.sql: the contract awards since FY2020, the prior-review
contract awards of FY2001 to FY2016, and the award notices of FY2017 to FY2019, which neither dataset covers). The
query is sql/contracts/project.sql; project_records and Home count a project's contracts from the same table.

held() is what both tabs show: how many contracts, and how many from each source. left_out() is what the Records lane
cannot place: it draws each package on its first signing, found by its STEP reference, so it leaves out a contract
with no STEP reference (most of the FY2001 to FY2016 awards, whose references were written before STEP), and a
package none of whose contracts has a signing date.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import Engine

SQL = Path(__file__).resolve().parent / "sql" / "contracts" / "project.sql"
NO_STEP_REFERENCE, NO_SIGNING_DATE = "no_step_reference", "no_signing_date"


@cache
def _query() -> str:
    return SQL.read_text()


def statement(project_id: str, as_of: dt.date) -> tuple[str, dict]:
    """The one statement that reads a project's contracts, for a page that sends its reads as one batch."""
    return _query(), {"project_id": project_id, "as_of": as_of}


def of_project(engine: Engine, project_id: str, as_of: dt.date) -> list[dict]:
    """The project's contracts that were public on the as-of date, one row each."""
    result = engine.run(*statement(project_id, as_of))
    return [dict(zip(result.columns, row)) for row in result.rows]


def by_source(rows: list[dict]) -> list[dict]:
    """How many of these contracts come from each source, the largest first."""
    counts = Counter(row["source"] for row in rows)
    return [{"source": source, "count": count}
            for source, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))]


def held(rows: list[dict]) -> dict:
    """The project's contracts as both tabs count them."""
    return {"count": len(rows), "sources": by_source(rows)}


def left_out(rows: list[dict], placed: set[str]) -> dict:
    """The contracts the Records lane leaves out, by why and by source, given the STEP references it placed."""
    no_reference = [row for row in rows if row["step_reference"] is None]
    no_date = [row for row in rows if row["step_reference"] is not None and row["step_reference"] not in placed]
    return {"count": len(no_reference) + len(no_date),
            NO_STEP_REFERENCE: by_source(no_reference), NO_SIGNING_DATE: by_source(no_date)}
