"""The project routes' reads, which the app runs as the viewer: All projects, and one project's page.

All projects lists every project Strata holds a record for, active ones first and then by name.
A project's page gives its header (name, country, status and implementing agencies) and the
Procurement tab: each implementing agency's Procurement Plan versions, newest first, with how many
activities each read version lists. Agencies with plans come first, the one with the newest plan
first; then each agency the project record names that has published no plan, in the record's
order. An agency's id is check_plan's, so a version's link opens that agency's plan check.

Each read uses only what was public on or before the as-of date (ADR 0002). The routes count,
sort and choose the latest version here, so the screen never does. Each query is one file in
sql/projects/, written once in Databricks SQL.
"""

from __future__ import annotations

import datetime as dt
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import Engine
from strata.tools.check_plan import agency_id, implementing_agencies

SQL = Path(__file__).resolve().parent / "sql" / "projects"
PROJECTS_SOURCE = "projects"  # the source registry's key for the projects API (config/sources.toml)


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_query(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _day(value) -> dt.date | None:
    """A date from DuckDB, or the text the warehouse writes it as."""
    if value is None or value == "" or isinstance(value, dt.date):
        return value or None
    return dt.date.fromisoformat(str(value)[:10])


def _iso(value) -> str | None:
    day = _day(value)
    return day.isoformat() if day else None


def _through(engine: Engine, name: str, as_of: dt.date, **params) -> str | None:
    """The day a source was last fetched, but never after the as-of date the page shows."""
    rows = _rows(engine, name, **params)
    fetched = _day(rows[0]["fetched_on"]) if rows else None
    return min(fetched, as_of).isoformat() if fetched else None


def all_projects(engine: Engine, as_of: dt.date) -> dict:
    rows = [{"project_id": row["project_id"], "project_name": row["project_name"], "country": row["country"],
             "status": row["status"]} for row in _rows(engine, "all_projects", as_of=as_of)]
    return {"as_of": as_of.isoformat(), "total": len(rows), "rows": rows,
            "records_through": _through(engine, "projects_through", as_of, source=PROJECTS_SOURCE)}


def _agencies(versions: list[dict], named: list[str]) -> list[dict]:
    """Each agency's versions, newest first, then the agencies the record names with no plan."""
    agencies: dict[str, dict] = {}
    for row in versions:  # newest first, so the first spelling of a name is its latest plan's
        if not row["implementing_agency"]:
            continue
        key = agency_id(row["implementing_agency"])
        agency = agencies.setdefault(key, {"implementing_agency": row["implementing_agency"], "agency_id": key,
                                           "versions": []})
        read = row["parse_reason"] is not None
        agency["versions"].append({
            "document_id": row["document_id"], "plan_date": _iso(row["plan_date"]),
            "disclosed_on": _iso(row["disclosed_on"]), "is_latest": not agency["versions"],
            "read": read, "activities": int(row["activities"]) if read else None})
    for name in named:
        agencies.setdefault(agency_id(name), {"implementing_agency": name, "agency_id": agency_id(name), "versions": []})
    return list(agencies.values())


def project_page(engine: Engine, project_id: str, as_of: dt.date) -> dict | None:
    """The project page's header and Procurement tab, or None when there is no such project as of then."""
    found = _rows(engine, "project", project_id=project_id, as_of=as_of)
    if not found:
        return None
    record = found[0]
    current = (_day(record["record_updated_on"]) or _day(record["public_from"])) <= as_of
    named = implementing_agencies(record["implementing_agency"]) if current else []
    versions = _rows(engine, "plan_versions", project_id=project_id, as_of=as_of)
    return {
        "as_of": as_of.isoformat(),
        "project": {"project_id": record["project_id"], "project_name": record["project_name"],
                    "country": record["country"], "status": record["status"] if current else None,
                    "implementing_agencies": named},
        "agencies": _agencies(versions, named),
        "documents_through": _through(engine, "documents_through", as_of, project_id=project_id),
    }
