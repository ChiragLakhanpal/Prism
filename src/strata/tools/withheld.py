"""What a view leaves out of a tool's answer about a project still under way (ticket 40).

The roles file's [views] (config/roles.toml) names the capabilities a view has. The public view lacks three on active
projects: signals_on_active_projects, time_estimates_on_active_projects and disagreements_on_active_projects, so a
procurement still under way isn't prejudged (spec, user story 55). Each tool asks withheld() with its capability and
the project, and answers with WITHHELD as its reason when the view leaves it out.

project_status() is the one rule for whether a project was active on a date, the rule tickets 21 and 37 use: the
projects API's record once it was public by then (its status and closing date change in place, so they count from the
day the record was last updated), and before then the closing date from the monthly loan history, the project
counting as active while that date was still ahead. It reads only the as-of date, never the wall clock and never
today's status alone, so a page as of 2016 calls P130164 active, and P156634 stays active on its page dated October
23, 2026, whatever day the test runs.
"""

from __future__ import annotations

import datetime as dt
from functools import cache
from importlib import resources

from strata.config import Views, load_views
from strata.tools.check_plan import record_is_current

WITHHELD = "view_public_active"  # the reason code every tool gives, with one copy sentence per tool
STATUS_KIND = {"Active": "active", "Closed": "closed", "Pipeline": "pipeline", "Dropped": "dropped"}


@cache
def views() -> Views:
    return load_views()


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "project_signals" / name).read_text()


def _rows(engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def status_as_of(row: dict, history: list[dict], as_of: dt.date) -> tuple[str | None, dt.date | None, bool]:
    """The project's status and closing date on the as-of date, from its projects API record (project.sql) and its
    closing-date history (history.sql), and whether the record itself was public by then."""
    if record_is_current(row, as_of):
        return STATUS_KIND.get(row["status"] or "", None), _date(row["closing_date"]), True
    closing = _date(history[-1]["closing_date"]) if history else None
    return (None if closing is None else "active" if closing >= as_of else "closed"), closing, False


def project_status(engine, project_id: str, as_of: dt.date) -> str | None:
    """Whether the project was active, closed, pipeline or dropped on the as-of date, or None when Strata held no
    record of it then."""
    found = _rows(engine, "project.sql", project_id=project_id.strip().upper(), as_of=as_of)
    if not found:
        return None
    history = _rows(engine, "history.sql", project_id=found[0]["project_id"], as_of=as_of)
    return status_as_of(found[0], history, as_of)[0]


def lacks(view: str, capability: str) -> bool:
    """Whether the view lacks a capability that is withheld only on active projects, so a tool knows whether it needs
    to read the project at all."""
    return not views().capabilities[capability].values.get(view, True)


def withheld_in(engine, view: str, as_of: dt.date, capability: str, project_id: str | None) -> bool:
    """Whether the view leaves this capability out for the project: the view lacks it, and the project was active on
    the as-of date."""
    if project_id is None or not lacks(view, capability):
        return False
    return project_status(engine, project_id, as_of) == "active"


def withheld(call, capability: str, project_id: str | None) -> bool:
    """withheld_in for a tool's call: its view and its as-of date."""
    return withheld_in(call.engine, call.view, call.as_of, capability, project_id)



