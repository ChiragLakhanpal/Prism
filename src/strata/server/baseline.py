"""Saving and removing the baseline of an implementing agency's Procurement Plans (ticket 21; the 21 brief,
section 5.2), the first shared record World Bank staff make in Strata.

A baseline is one version of one agency's plans for a project, saved as the plan agreed at negotiations.
Every World Bank staff viewer who checks that agency's plans sees the same baseline and who saved it, and
check_plan then also measures delay from its planned dates (src/strata/tools/check_plan.py reads it, the
one place it is read). Saving copies the version's planned dates into strata.ops.plan_baseline_steps,
because the plan reader rebuilds silver.plan_steps on every run. Saving another version replaces the
baseline, and removing it deletes it, each with a DELETE that names the project and the agency
(CLAUDE.md rule 5). Each write runs as the viewer, with bound parameters and three-part names, in
sql/baseline/. The writes go in an order that a failure part way leaves safe: a save adds the new steps,
then merges the baseline's one row, and only then deletes the earlier save's steps; a save that a later one beat
takes its own steps back, since the row names the later save (ticket 60); a removal deletes the row before its
steps. check_plan reads only the steps of the save the row names.

Only a version the layout parser read can be a baseline, since a baseline is its planned dates. The
routes refuse a write from a preview of another view, or from no one signed in, before this module runs.
"""

from __future__ import annotations

import datetime as dt
from functools import cache
from pathlib import Path

from strata.dbx import Viewer
from strata.lakehouse.engine import Engine
from strata.server.summary import iso_day, record_event
from strata.tools.check_plan import agency_id, read_baseline

SQL = Path(__file__).resolve().parent / "sql" / "baseline"
TABLE = "strata.ops.plan_baselines"  # before the colon in a baseline's evidence id


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_query(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _remove(engine: Engine, project_id: str, agency: str) -> None:
    # The row first, so a failure before the steps leave shows no baseline rather than one with no dates.
    for name in ("remove", "remove_steps"):
        engine.run(_query(name), {"project_id": project_id, "agency_id": agency})


def save(engine: Engine, project_id: str, agency: str, plan_date: dt.date, viewer: Viewer,
         now: dt.datetime) -> dict | None:
    """Save the agency's version of this date as the baseline, in place of any other, and return the
    baseline as check_plan gives it; or None when the agency has no read version of that date."""
    today = now.astimezone(dt.UTC).date()
    found = [row for row in _rows(engine, "version", project_id=project_id, plan_date=plan_date, today=today)
             if row["implementing_agency"] and agency_id(row["implementing_agency"]) == agency and row["activities"]]
    if not found:
        return None
    version = found[-1]
    values = {"project_id": project_id, "agency_id": agency, "document_id": version["document_id"],
              "public_from": today, "saved_at": now}
    engine.run(_query("save_steps"), values)
    engine.run(_query("save"), {**values, "implementing_agency": version["implementing_agency"],
                                "plan_date": plan_date, "saved_by": viewer.user_id, "saved_by_name": viewer.name})
    # A later save that landed first keeps the row (save.sql), so this save's steps would wait for the next save to
    # leave: they leave now, and the statement itself checks the row (ticket 60).
    for name in ("remove_older_steps", "remove_lost_steps"):
        engine.run(_query(name), {"project_id": project_id, "agency_id": agency, "saved_at": now})
    saved = read_baseline(engine, project_id, agency, today, "staff")
    return saved.record if saved else None


def remove(engine: Engine, project_id: str, agency: str) -> None:
    """Remove the agency's baseline for this project, if there is one."""
    _remove(engine, project_id, agency)


def read_record(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    """The evidence drawer's reader for a baseline's evidence id ("P156634/{agency_id}"): the baseline as a
    record, once it was saved by the as-of date, or None. It never names who saved it, since the drawer is
    not told the view and the implementing agency view leaves the name out."""
    project_id, _, agency = key.partition("/")
    found = _rows(engine, "record", project_id=project_id, agency_id=agency, as_of=as_of) if agency else []
    if not found:
        return None
    row = found[0]
    event = record_event(f"{TABLE}:{key}", row["public_from"], "plan_baseline", project_id, row["public_from"],
                         row["implementing_agency"],
                         [("implementing_agency", row["implementing_agency"], "text"),
                          ("plan_date", iso_day(row["plan_date"]), "date"),
                          ("saved_on", iso_day(row["public_from"]), "date")])
    return {"kind": "record", "row": event["row"]}
