"""sentinel2_mosaic: the ground at each project location, seen from space in two years (ticket 147).

EOX's Sentinel-2 cloudless yearly mosaics, served as WMTS tiles in Web Mercator (EPSG:3857, the "g" grid, rows from
the north). For each location the reader builds the addresses of the 3 by 3 tiles at settings.zoom (15) around it, for
the oldest year after the project's approval and the newest year the registry lists (2018 and 2025 for P156634), as
two lists of nine, row by row from the north-west. It fetches nothing and reads no pixels: the item's text says what
the grids are, never what they show, and a person compares them.
"""

from __future__ import annotations

import datetime as dt
import math

from strata.config import ResearchSource
from strata.research.items import make_item
from strata.research.project import Location, ProjectFacts
from strata.research.sources import SourceResult, as_of


def tile(latitude: float, longitude: float, zoom: int) -> tuple[int, int]:
    """The (row, column) of the tile that holds the point, in the Web Mercator grid at zoom."""
    count = 2 ** zoom
    column = math.floor((longitude + 180.0) / 360.0 * count)
    radians = math.radians(latitude)
    row = math.floor((1.0 - math.asinh(math.tan(radians)) / math.pi) / 2.0 * count)
    return min(max(row, 0), count - 1), min(max(column, 0), count - 1)


def grid(endpoint: str, year: int, location: Location, zoom: int) -> list[str]:
    """The nine tile addresses around the location, row by row from the north-west."""
    row, column = tile(location.latitude, location.longitude, zoom)
    return [endpoint.format(year=year, zoom=zoom, row=row + down, col=column + across)
            for down in (-1, 0, 1) for across in (-1, 0, 1)]


def years(project: ProjectFacts, listed: list[int]) -> tuple[int, int]:
    """The oldest listed year after the project's approval, and the newest listed year."""
    approved = int(project.approval_date[:4]) if project.approval_date else None
    after = [year for year in listed if approved is None or year > approved]
    return min(after or listed), max(listed)


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    settings, day = source.settings, as_of(now)
    zoom = int(settings.get("zoom", 15))
    listed = sorted(int(year) for year in settings.get("years", ()) if int(year) < day.year)
    if not listed:
        return SourceResult(source.key, [], False, "no year", "The registry lists no mosaic year before the run's year.")
    first, last = years(project, listed)
    items = []
    for location in project.locations:
        grids = [grid(source.endpoint, year, location, zoom) for year in (first, last)]
        items.append(make_item(
            project=project, source=source, item_key=f"{location.geo_loc_id}-{first}-{last}",
            public_from=dt.date(last, 12, 31), observed=dt.date(last, 12, 31), date_known=False,
            title=f"Sentinel-2 cloudless mosaics of {first} and {last} around {location.name}",
            text=(f"Two grids of 3 by 3 Sentinel-2 cloudless tiles at zoom {zoom}, centred on {location.name} "
                  f"({location.latitude}, {location.longitude}): the {first} mosaic and the {last} mosaic. "
                  "Prism reads no pixels; the grids are for a person to compare."),
            url=grids[1][4], read_on=day, image_urls=grids, author="EOX IT Services GmbH", location=location,
            url_of_source=settings.get("viewer")))
    note = (f"Prism built the tile addresses of the {first} and {last} mosaics for {len(items)} locations and fetched "
            "no tile.")
    return SourceResult(source.key, items, True, "read", note)
