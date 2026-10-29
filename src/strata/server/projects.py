"""The project routes' reads, which the app runs as the viewer: All projects, and one project's page.

All projects lists every project Strata holds a record for, active ones first and then by name, one
page at a time (config/thresholds.toml's app.page_size), and searches them by part of a name, a
project ID (with or without its P) or a country, ignoring case and accents. An exact project ID comes
first. The route counts the matches and the page's range, so the screen never does.

A project's page gives its header (name, country, status and implementing agencies) and the
Procurement tab: each implementing agency's Procurement Plan versions, newest first, with how many
activities each read version lists. Agencies with plans come first, the one with the newest plan
first; then each agency the project record names that has published no plan, in the record's
order. An agency's id is check_plan's, so a version's link opens that agency's plan check.

Ticket 21 adds, for each agency, what changed in its latest version since the version before it
(the counts of src/strata/server/changes.py), the baseline World Bank staff saved for its plans
(check_plan's read_baseline, which the view may take away), and which versions the tab shows
before "Show all": the newest app.versions_shown, plus the baseline. The header's name is the
project's display name: the projects API's name with a final "Project" left out, since the page
names it as a project ("Rajasthan Road Sector Modernization Project" reads "Rajasthan Road Sector
Modernization"). Tables keep the record's own name.

Each read uses only what was public on or before the as-of date (ADR 0002). The routes count,
sort and choose the latest version here, so the screen never does. Each query is one file in
sql/projects/, written once in Databricks SQL.
"""

from __future__ import annotations

import datetime as dt
import math
import re
import unicodedata
from decimal import Decimal
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import Engine
from strata.server import changes
from strata.tools.check_plan import agency_id, implementing_agencies, read_baseline, record_is_current

SQL = Path(__file__).resolve().parent / "sql" / "projects"
PROJECTS_SOURCE = "projects"  # the source registry's key for the projects API (config/sources.toml)
CENTS = Decimal("0.01")


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


def folded(text: str | None) -> str:
    """Text as a search compares it: in lower case, with its accents taken off, so "turkiye" finds Türkiye."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _found(row: dict, words: list[str]) -> bool:
    """Whether every word of the search is part of the project's ID, name or country. A word of
    digits alone matches a project ID without its P."""
    held = folded(" ".join(str(row[key] or "") for key in ("project_id", "project_name", "country")))
    return all(word in held or (word.isdigit() and f"p{word}" in held) for word in words)


def page_of(rows: list, page: int, size: int) -> dict:
    """One page of rows, with the range it shows and how many there are. A page past the last is the last."""
    total = len(rows)
    pages = math.ceil(total / size)
    page = min(max(page, 1), max(pages, 1))
    first = (page - 1) * size
    shown = rows[first:first + size]
    return {"total": total, "page": page, "pages": pages, "page_size": size,
            "first": first + 1 if shown else 0, "last": first + len(shown), "rows": shown}


def all_projects(engine: Engine, as_of: dt.date, query: str = "", page: int = 1, size: int = 20) -> dict:
    rows = [{"project_id": row["project_id"], "project_name": row["project_name"], "country": row["country"],
             "status": row["status"]} for row in _rows(engine, "all_projects", as_of=as_of)]
    words = folded(query).split()
    if words:
        rows = [row for row in rows if _found(row, words)]
        asked = re.sub(r"^p", "", words[0]) if len(words) == 1 else None
        rows.sort(key=lambda row: row["project_id"].casefold() != f"p{asked}")  # an exact ID first; sorted is stable
    return {"as_of": as_of.isoformat(), "query": query, **page_of(rows, page, size),
            "records_through": _through(engine, "projects_through", as_of, source=PROJECTS_SOURCE)}


def display_name(name: str | None) -> str | None:
    """The project's name as its page's header gives it: without a final word "Project"."""
    return re.sub(r"\s+Project$", "", name) if name else name


def _changes(engine: Engine, all_versions: list[dict], document_id: str, as_of: dt.date) -> dict | None:
    """What changed in the agency's latest version, as counts, for the Procurement tab's sentence."""
    version = next((row for row in all_versions if row["document_id"] == document_id), None)
    if version is None:
        return None
    found = changes.compare(engine, all_versions, version, as_of, detail=False)
    previous = found["previous"]
    return {"state": found["state"], "previous_plan_date": previous["plan_date"] if previous else None,
            "counts": found["counts"]}


def _agencies(engine: Engine, project_id: str, versions: list[dict], named: list[str], as_of: dt.date, view: str,
              shown: int) -> list[dict]:
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
    all_versions = changes.versions(engine, project_id) if agencies else []
    for agency in agencies.values():
        saved = read_baseline(engine, project_id, agency["agency_id"], as_of, view)
        agency["baseline"] = saved.record if saved else None
        for index, version in enumerate(agency["versions"]):
            version["is_baseline"] = bool(saved) and version["document_id"] == saved.record["document_id"]
            version["shown"] = index < shown or version["is_baseline"]
        agency["changes"] = _changes(engine, all_versions, agency["versions"][0]["document_id"], as_of)
    for name in named:
        agencies.setdefault(agency_id(name), {"implementing_agency": name, "agency_id": agency_id(name), "versions": [],
                                              "baseline": None, "changes": None})
    for agency in agencies.values():
        agency["version_count"] = len(agency["versions"])
        agency["shown_count"] = sum(1 for version in agency["versions"] if version["shown"])
    return list(agencies.values())


def packages_reads(project_id: str, as_of: dt.date) -> list[tuple[str, dict]]:
    """The statements packages() runs, for the route that sends them as one batch (ticket 125)."""
    return [(_query("packages"), {"project_id": project_id, "as_of": as_of}),
            (_query("documents_through"), {"project_id": project_id})]


def packages(engine: Engine, project_id: str, as_of: dt.date, query: str = "", page: int = 1, size: int = 20) -> dict:
    """Every activity in each agency's latest read plan, a page at a time, found by part of its STEP
    reference or its description. A description keeps each place the PDF cell wrapped as a space
    ("Exploratory Bo reholes"), so the search compares both with every space taken out."""
    rows = []
    for row in _rows(engine, "packages", project_id=project_id, as_of=as_of):
        amount = row["estimated_amount_usd"]
        rows.append({"activity_reference_no": row["activity_reference_no"], "description": row["description"],
                     "implementing_agency": row["implementing_agency"],
                     "agency_id": agency_id(row["implementing_agency"]), "plan_date": _iso(row["plan_date"]),
                     "method": row["method"], "market_approach": row["market_approach"],
                     "estimated_amount_usd": None if amount is None else str(Decimal(str(amount)).quantize(CENTS)),
                     "process_status": row["process_status"]})
    wanted = folded(query).replace(" ", "")
    if wanted:
        rows = [row for row in rows if wanted in folded(f"{row['activity_reference_no']}{row['description'] or ''}")
                .replace(" ", "")]
    return {"as_of": as_of.isoformat(), "query": query, **page_of(rows, page, size),
            "read_through": _through(engine, "documents_through", as_of, project_id=project_id)}


def project_page(engine: Engine, project_id: str, as_of: dt.date, view: str = "staff",
                 shown: int = 5) -> dict | None:
    """The project page's header and Procurement tab, or None when there is no such project as of then."""
    found = _rows(engine, "project", project_id=project_id, as_of=as_of)
    if not found:
        return None
    record = found[0]
    current = record_is_current(record, as_of)
    named = implementing_agencies(record["implementing_agency"]) if current else []
    versions = _rows(engine, "plan_versions", project_id=project_id, as_of=as_of)
    return {
        "as_of": as_of.isoformat(),
        "project": {"project_id": record["project_id"], "project_name": record["project_name"],
                    "display_name": display_name(record["project_name"]),
                    "country": record["country"], "status": record["status"] if current else None,
                    "implementing_agencies": named},
        "agencies": _agencies(engine, project_id, versions, named, as_of, view, shown),
        "documents_through": _through(engine, "documents_through", as_of, project_id=project_id),
    }
