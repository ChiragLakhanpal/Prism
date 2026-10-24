"""The Data readiness page as data_readiness_for builds it for one day, written to
strata.ops.readiness_snapshot for the dashboard (ticket 16; the 16 design brief, section 10).

Every run that measures data readiness writes one, after its measures: the nightly job's
measure_data_readiness task, and the fixture build once every reader has measured. The dashboard's
Data readiness page reads the newest snapshot on or before the date it is set to, so its headline,
statuses and fixes are the app's for that date, from the same function (CLAUDE.md rule 4).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from strata.config import load_thresholds
from strata.dbx import Viewer
from strata.lakehouse.engine import Engine
from strata.tools import data_readiness_for as readiness
from strata.tools.registry import Call

COLUMNS = ("run_id", "measured_on", "part", "position", "label", "text", "status", "latest_data", "updates",
           "days_late", "count", "denominator", "share_percent", "projects", "written_at", "public_from")
ROUTES = ("pages_read_route_a", "pages_read_route_b")  # the plan reader's pages read well, per route
# The run writes as the job's own identity, never a viewer's (ADR 0003 covers the app's reads).
JOB = Viewer(email=None, name="strata nightly", token=None)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _row_status(cells: dict) -> str | None:
    found = {cell.get("status") for cell in cells.values()}
    return "gap" if "gap" in found else "partial" if "partial" in found else None


def rows(result: dict, run_id: str, measured_on: dt.date, routes: list[dict], written_at: dt.datetime) -> list[tuple]:
    """The snapshot's rows for one result of data_readiness_for."""
    words = readiness.words()
    measures = result["rows"]
    out = []

    def add(part, position, label=None, text=None, status=None, latest=None, updates=None, late=None, count=None,
            denominator=None, share=None, projects=None):
        out.append((run_id, measured_on, part, position, label, text, words["badges"][status] if status else None,
                    latest, updates, late, count, denominator, share, projects, written_at, written_at.date()))

    if result["headline"]:
        add("headline", 1, text=result["headline"]["text"])
    links = 0
    for position, row in enumerate(result["sources"], 1):
        label = row["label"] + (f", {row['covers']}" if row.get("covers") else "")
        if row["type"] == "gap":
            add("gap", position, label=f"{row['label']}, FY{row['first_fiscal_year']}–{str(row['last_fiscal_year'])[2:]}",
                text=row["note"], status="gap")
            continue
        cells = row["cells"]
        fresh, linked = cells["fresh"], cells["linked"]
        fresh_row = measures[fresh["row"]] if fresh.get("row") is not None else None
        linked_row = measures[linked["row"]] if linked.get("row") is not None else None
        add("source", position, label=label, status=_row_status(cells),
            text=f"{linked_row['count']:,} of {linked_row['denominator']:,}" if linked_row and linked_row["denominator"]
            else None,
            latest=dt.date.fromisoformat(fresh_row["as_of"]) if fresh_row and fresh_row["as_of"] else None,
            updates=words["schedules"][fresh["schedule"]] if fresh.get("schedule") else None,
            late=fresh.get("late_days"), count=linked_row["count"] if linked_row else None,
            denominator=linked_row["denominator"] if linked_row else None,
            share=linked_row["share_percent"] if linked_row else None)
        if linked_row:
            links += 1
            add("link", links, label=f"{row['label']}: {linked['counts']}", count=linked_row["count"],
                denominator=linked_row["denominator"], share=linked_row["share_percent"])
    for fix in result["fixes"]:
        add("fix", fix["rank"], text=readiness.text_of(fix["sentence"]), projects=fix["projects"])
    for position, route in enumerate(routes, 1):
        add("route", position, label=words["routes"][route["measure"]], count=route["count"],
            denominator=route["denominator"], share=route["share_percent"])
    return out


def write(engine: Engine, run_id: str, clock: Callable[[], dt.datetime] = _now) -> int:
    """Build the page as of today, in UTC, and write it. Returns how many rows it wrote, none when the
    page has nothing to show yet."""
    written_at = clock()
    measured_on = written_at.astimezone(dt.UTC).date()
    call = Call(engine, JOB, "staff", measured_on, load_thresholds())
    result = readiness.data_readiness_for(call)
    if result["abstention"]:
        return 0
    fewest = int(call.thresholds.value("data_readiness.fewest_for_a_share"))
    routes = []
    for measure in ROUTES:
        found = [row for row in readiness._rows(call, "latest_measures.sql", as_of=measured_on)
                 if row["source"] == "documents" and row["measure"] == measure]
        if found:
            count = sum(int(row["count"]) for row in found)
            denominator = sum(int(row["denominator"]) for row in found)
            routes.append({"measure": measure, "count": count, "denominator": denominator,
                           "share_percent": readiness._share(count, denominator, fewest)})
    return engine.insert_rows("strata.ops.readiness_snapshot", COLUMNS,
                              rows(result, run_id, measured_on, routes, written_at))
