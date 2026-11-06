"""inspection_panel: whether people affected by the project have asked the World Bank's Inspection Panel for a case
(ticket 147).

One call to the Panel's case register (https://www.inspectionpanel.org/panel-cases/data), whose page embeds its cases
in the Drupal settings JSON, drupalSettings.extractCases: a map of each case's node id to its title, and a title holds
the project IDs it is about as P followed by six digits. A case that names the project is one item, linked to the
case's own page (settings.case_page) or, without one, to the register. No case gives no item and reached True.
"""

from __future__ import annotations

import datetime as dt
import json
import re

from strata.config import ResearchSource
from strata.research.fetching import body_of
from strata.research.items import make_item
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of

SETTINGS = re.compile(r'<script[^>]*data-drupal-selector="drupal-settings-json"[^>]*>(.*?)</script>', re.S)
PROJECT_ID = re.compile(r"P\d{6}")


def cases(body: bytes) -> dict[str, str] | None:
    """The register's cases, node id to title, or None when the page holds no case list."""
    found = SETTINGS.search(body.decode("utf-8", errors="replace"))
    if not found:
        return None
    try:
        listed = json.loads(found.group(1)).get("extractCases")
    except ValueError:
        return None
    return {str(node): str(title).strip() for node, title in listed.items()} if isinstance(listed, dict) else None


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    listed = cases(body_of(fetch, source.endpoint, source.label))
    if listed is None:
        return SourceResult(source.key, [], False, "200", "The Inspection Panel's register page held no list of cases.")
    day, page = as_of(now), source.settings.get("case_page")
    items = []
    for node, title in listed.items():
        if project.project_id not in PROJECT_ID.findall(title):
            continue
        items.append(make_item(project=project, source=source, item_key=node, public_from=None, title=title,
                               text=title, url=page.format(node=node) if page else source.endpoint, read_on=day,
                               author="World Bank Inspection Panel", url_of_source=source.endpoint))
    note = (f"The Inspection Panel's register lists {len(listed)} cases, {len(items)} of them naming "
            f"{project.project_id}.")
    return SourceResult(source.key, items, True, "200", note)
