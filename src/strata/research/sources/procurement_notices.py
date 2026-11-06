"""procurement_notices: what the project's agencies published to the market lately (ticket 147). No network.

From strata.gold.notice, as of the run's day: the project's notices dated within settings.days (180) before it, of the
types settings.notice_types names (Contract Award, Invitation for Bids), newest first. Each is one item with its STEP
reference, its method and its date in the title, its text as silver keeps it (contact details stripped at ingestion),
and the notice's own page on projects.worldbank.org, so the brief can say what was awarded and when against the
closing date.
"""

from __future__ import annotations

import datetime as dt

from strata.config import ResearchSource
from strata.research.items import make_item
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of, long_date, rows


def _title(notice: dict) -> str:
    reference = notice["step_reference"] or notice["bid_reference_no"]
    method = f" ({notice['procurement_method']})" if notice["procurement_method"] else ""
    head = f"{notice['notice_type']} {notice['notice_id']}"
    if reference:
        head += f", {reference}{method}"
    return f"{head}: {notice['bid_description']}" if notice["bid_description"] else head


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    settings = source.settings
    if engine is None:
        return SourceResult(source.key, [], False, "no database", "Prism had no lakehouse to read the notices from.")
    day = as_of(now)
    since = day - dt.timedelta(days=int(settings.get("days", 180)))
    kinds = tuple(settings.get("notice_types", ("Contract Award", "Invitation for Bids")))
    register = settings.get("register_page", "").format(project_id=project.project_id) or None
    items = []
    for notice in rows(engine, "recent_notices", project_id=project.project_id, since=since, as_of=day):
        if notice["notice_type"] not in kinds:
            continue
        url = settings.get("notice_page", "{notice_id}").format(notice_id=notice["notice_id"])
        text = notice["notice_text"] or notice["bid_description"] or ""
        items.append(make_item(project=project, source=source, item_key=notice["notice_id"],
                               public_from=notice["public_from"], published=notice["notice_date"], title=_title(notice),
                               text=text, url=url, read_on=day, author="World Bank procurement notices (STEP)",
                               url_of_source=register))
    note = (f"Prism read {len(items)} contract awards and invitations for bids published from {long_date(since)} to "
            f"{long_date(day)}.")
    return SourceResult(source.key, items, True, "read", note)
