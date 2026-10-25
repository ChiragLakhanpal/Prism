"""Tables a nightly task rebuilds whole, written again only when their rows change (ticket 43).

Some tasks rebuild a table from scratch each night and stamp its rows with the run: the supplier pairs and their
resolution (strata.knowledge.suppliers.resolve), the contracts' links to report paragraphs
(strata.knowledge.links) and the assertions with their rejections (strata.knowledge.assertions). Running the same
night twice must change nothing, and the Governance page counts the rows each task changed, so each of them
compares what it would write with what the table holds, leaving out the run's id and time, and writes only when
the two differ. differing() counts the rows that would be added or removed.

Values are compared as text, the way both engines can give them: DuckDB gives typed values and the SQL warehouse
text, so a number or a date is written in one form before it is compared. A table the warehouse gives back as
text that does not match is simply written again, which is what happened before.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Iterable
from decimal import Decimal

from strata.lakehouse.engine import Engine


def _text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float | Decimal):
        number = Decimal(str(value)).normalize()
        return format(number, "f")
    if isinstance(value, dt.datetime):
        return (value.astimezone(dt.UTC) if value.tzinfo else value).replace(tzinfo=None).isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return str(value)


def comparable(rows: Iterable[tuple], leave_out: Iterable[int] = ()) -> Counter:
    """The rows as text, without the columns at the places in leave_out, counted."""
    skip = set(leave_out)
    return Counter(tuple(_text(value) for number, value in enumerate(row) if number not in skip) for row in rows)


def held(engine: Engine, table: str, columns: tuple[str, ...], where: str = "", params: dict | None = None) -> list:
    """The table's rows, in the columns given, optionally filtered by a WHERE clause with bound parameters."""
    query = f"SELECT {', '.join(columns)} FROM {table}" + (f" WHERE {where}" if where else "")  # sql-lint: names only
    return list(engine.run(query, params or {}).rows)


def differing(before: Counter, after: Counter) -> int:
    """How many rows the change adds or removes."""
    return sum((before - after).values()) + sum((after - before).values())
