"""site_conditions: the disasters GDACS alerted on in the project's country while it was being carried out (ticket 154).

One call to GDACS's event search (config/research.toml, sources.site_conditions.endpoint) for the project's country,
from the project's approval date, or settings.years_back years before the run when that is later, to the run's day.
GDACS answers with GeoJSON: each feature's properties hold the event's type, its name ("Drought in Kenya, Somalia"),
its start and end, its alert level and its report's address. Each event whose name or area names the project's
country is one item, observed on the event's start, its alert level in the text and its report as the url. GDACS
alerts on a country or a region, never on a site, so an item has no location.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.parse

from strata.config import ResearchSource
from strata.research.fetching import body_of
from strata.research.items import make_item
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of

AUTHOR = "GDACS"


def _years_before(day: dt.date, years: int) -> dt.date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # February 29
        return day.replace(year=day.year - years, day=28)


def address(source: ResearchSource, project: ProjectFacts, day: dt.date) -> str:
    """The search for the project's country, from its approval date or years_back before day, whichever is later."""
    start = _years_before(day, int(source.settings.get("years_back", 2)))
    if project.approval_date:
        start = max(start, dt.date.fromisoformat(project.approval_date[:10]))
    return source.endpoint.format(country=urllib.parse.quote(project.country_name), from_date=start.isoformat(),
                                  to_date=day.isoformat())


def _names_country(properties: dict, country: str) -> bool:
    named = [properties.get("name") or "", properties.get("country") or "",
             *[place.get("countryname") or "" for place in properties.get("affectedcountries") or []]]
    return any(country.lower() in text.lower() for text in named)


def _day(value) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    day = as_of(now)
    url = address(source, project, day)
    try:
        events = json.loads(body_of(fetch, url, source.label)).get("features") or []
    except ValueError:
        return SourceResult(source.key, [], False, "200", "GDACS answered with something that is not a list of events.")
    items = []
    for event in events:
        properties = event.get("properties") or {}
        if not _names_country(properties, project.country_name):
            continue
        report = (properties.get("url") or {}).get("report") or ""
        start = _day(properties.get("fromdate"))
        if not report.startswith("https://") or start is None or start > day:
            continue
        level = properties.get("alertlevel") or "not given"
        severity = (properties.get("severitydata") or {}).get("severitytext")
        words = [properties.get("htmldescription") or properties.get("description") or properties.get("name") or "",
                 f"Alert level: {level}.", f"{severity}." if severity else ""]
        items.append(make_item(
            project=project, source=source, item_key=f"{properties.get('eventtype')}-{properties.get('eventid')}",
            public_from=start, published=start, observed=start, title=properties.get("name") or "",
            text=" ".join(word for word in words if word), url=report, read_on=day, author=AUTHOR,
            url_of_source=url))
    note = f"GDACS lists {len(events)} events for {project.country_name} in the window, {len(items)} of them naming it."
    return SourceResult(source.key, items, True, "200", note)
