"""ProjectFacts: what a deep research reader knows of the project, read from the project's own record (ticket 147).

project_facts() reads the record from, in this order: the fixture's recorded page (data/fixture/recorded/api/projects/
<project>.json), the newest bronze page of the projects source that holds the project with its locations, the live
projects API through the reader's own fetch (config/research.toml, [client] project_record), and last a bronze page
without locations. It never fills a fact from memory: a fact the record lacks is empty.

The agencies are the record's names, split as the projects API joins them (strata.tools.check_plan), each with the
short names the press uses: its initials when it has three or more capitalised words (Coast Water Works Development
Agency is CWWDA), and the names the registry's [press_names] lists for it (Mombasa Water and Sanitation Services
Company is MOWASSCO). The locations are the record's geo_locations, each with the place a story names: the name
without the word District, County, Sub-Location or Location after it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from strata.config import load_research_client, load_sectors
from strata.research.fetching import Fetch, Unreachable
from strata.tools.check_plan import implementing_agencies

ROOT = Path(__file__).resolve().parents[3]
RECORDED_PROJECTS = ROOT / "data" / "fixture" / "recorded" / "api" / "projects"
# The words after a place's name that a story leaves out: Baricho Sub-Location is Baricho in the press.
PLACE_SUFFIX = re.compile(r"\s+(?:Sub-Location|Sub Location|Location|District|County|Province|Region)$", re.I)
CONNECTORS = {"and", "of", "the", "for", "in", "on", "de", "-", "&"}
COMPANY_ENDINGS = {"Ltd", "Ltd.", "Limited", "PLC"}
BRONZE_PAGES = """
SELECT body
FROM strata.bronze.api_pages
WHERE source = 'projects'
  AND body LIKE :pattern
ORDER BY fetched_at DESC
LIMIT 20
"""


@dataclass(frozen=True)
class Location:
    """One of the project's locations, as the projects API's geo_locations give it."""

    geo_loc_id: str
    name: str
    latitude: float
    longitude: float

    @property
    def place(self) -> str:
        """The name a story uses: Baricho for Baricho Sub-Location, Turkana for Turkana County."""
        return PLACE_SUFFIX.sub("", self.name).strip()

    def as_dict(self) -> dict:
        return {"geo_loc_id": self.geo_loc_id, "name": self.name, "latitude": self.latitude,
                "longitude": self.longitude}


@dataclass(frozen=True)
class Agency:
    """An implementing agency as the record names it, with the short names the press uses for it."""

    name: str
    short_names: tuple[str, ...]


@dataclass(frozen=True)
class ProjectFacts:
    project_id: str
    project_name: str
    country_code: str
    country_name: str
    implementing_agencies: tuple[Agency, ...]
    sector_key: str | None  # Strata's one sector (config/sectors.toml)
    sector_name: str | None
    closing_date: str | None  # ISO date
    status: str | None
    locations: tuple[Location, ...]
    approval_date: str | None = None  # ISO date

    @property
    def short_names(self) -> tuple[str, ...]:
        """Every agency's short names, each once, in the record's order."""
        return tuple(dict.fromkeys(short for agency in self.implementing_agencies for short in agency.short_names))

    @property
    def place_names(self) -> tuple[str, ...]:
        """Each location's place name, once."""
        return tuple(dict.fromkeys(location.place for location in self.locations if location.place))


def initials(name: str) -> str | None:
    """The initials of a name's capitalised words, when there are three or more: CWWDA. A water company goes by the
    name the registry's [press_names] gives it (MOWASSCO), never by its initials, so a company has none here."""
    if re.search(r"\bCompany\b", name):
        return None
    words = [word for word in re.split(r"[\s,]+", name) if word and word not in CONNECTORS
             and word not in COMPANY_ENDINGS]
    letters = [word[0] for word in words if word[0].isupper()]
    return "".join(letters) if len(letters) >= 3 and len(letters) == len(words) else None


def _agencies(text: str | None, press_names: dict[str, tuple[str, ...]]) -> tuple[Agency, ...]:
    agencies = []
    for name in implementing_agencies(text):
        short = [initials(name), *press_names.get(name, ())]
        agencies.append(Agency(name, tuple(dict.fromkeys(item for item in short if item))))
    return tuple(agencies)


def _number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def facts_from_record(record: dict) -> ProjectFacts:
    """ProjectFacts from one record of the projects API."""
    client = load_research_client()
    sectors = load_sectors()
    sector_key, _ = sectors.of(record.get("major_sectors"))
    codes = record.get("countrycode") or []
    locations = []
    for place in record.get("geo_locations") or []:
        latitude, longitude = _number(place.get("geo_latitude_nbr")), _number(place.get("geo_longitude_nbr"))
        if place.get("geo_loc_name") and latitude is not None and longitude is not None:
            locations.append(Location(str(place.get("geo_loc_id")), place["geo_loc_name"].strip(), latitude, longitude))
    status = record.get("status")
    return ProjectFacts(
        project_id=record["id"], project_name=(record.get("project_name") or "").strip(),
        country_code=(codes[0] if isinstance(codes, list) and codes else codes or "") or "",
        country_name=(record.get("countryshortname") or "").strip(),
        implementing_agencies=_agencies(record.get("impagency"), client.press_names),
        sector_key=sector_key, sector_name=sectors.names.get(sector_key) if sector_key else None,
        closing_date=(record.get("closingdate") or "")[:10] or None,
        status=status[0] if isinstance(status, list) and status else status,
        locations=tuple(locations), approval_date=(record.get("boardapprovaldate") or "")[:10] or None)


def _record_in(body, project_id: str) -> dict | None:
    projects = (body or {}).get("projects") if isinstance(body, dict) else None
    record = (projects or {}).get(project_id)
    return record if isinstance(record, dict) else None


def project_facts(project_id: str, *, fetch: Fetch | None = None, engine=None,
                  recorded: Path = RECORDED_PROJECTS) -> ProjectFacts:
    """The project's facts from its record: recorded, then bronze, then the live projects API through fetch."""
    path = recorded / f"{project_id}.json"
    if path.is_file():
        record = _record_in(json.loads(path.read_text())["response"], project_id)
        if record:
            return facts_from_record(record)
    without_locations = None
    if engine is not None:
        result = engine.run(BRONZE_PAGES, {"pattern": f'%"{project_id}"%'})
        for (body,) in result.rows:
            record = _record_in(json.loads(body), project_id)
            if record and record.get("geo_locations"):
                return facts_from_record(record)
            without_locations = without_locations or record
    if fetch is not None:
        try:
            status, _, body = fetch(load_research_client().project_record.format(project_id=project_id))
        except Unreachable:
            status, body = None, b""
        if status == 200:
            record = _record_in(json.loads(body), project_id)
            if record:
                return facts_from_record(record)
    if without_locations:
        return facts_from_record(without_locations)
    raise LookupError(f"I found no record of {project_id} in the fixture, in bronze or from the projects API.")
