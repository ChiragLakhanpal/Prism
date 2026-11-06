"""procurement_notices: what the project's agencies published to the market lately (ticket 147). No network.

From strata.gold.notice, as of the run's day: the project's notices dated within settings.days (180) before it, of the
types settings.notice_types names (Contract Award, Invitation for Bids), newest first. Each is one item with its STEP
reference, its method and its date in the title, its text as silver keeps it (contact details stripped at ingestion),
and the notice's own page on projects.worldbank.org, so the brief can say what was awarded and when against the
closing date.

notice_dates() gives the notice's own dates as fields (ticket 155): its notice_date, its submission_date and its
signing_date when strata.gold.notice holds them, and the award_notification_date a STEP award notice prints on its
"Date Notification of Award Issued (YYYY/MM/DD)" line, so a sentence that states one is checked against a field, not
against the notice's words. research_evidence attaches them to each notice's row as it reads a kept run, so a run
kept before them has them too.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping

from strata.config import ResearchSource
from strata.research.items import iso, make_item
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of, long_date, rows

AWARD_NOTIFIED = re.compile(r"Date Notification of Award Issued \(YYYY/MM/DD\)\s*(\d{4})/(\d{1,2})/(\d{1,2})")


def notice_dates(notice: Mapping, text: str | None) -> dict:
    """A notice's own dates as ISO fields, each only when the notice holds it: notice_date, submission_date and
    signing_date from its strata.gold.notice record, and award_notification_date from its words."""
    found = {"notice_date": iso(notice.get("notice_date")), "submission_date": iso(notice.get("submission_deadline")),
             "signing_date": iso(notice.get("contract_signature_date"))}
    if match := AWARD_NOTIFIED.search(text or ""):
        try:
            found["award_notification_date"] = dt.date(*(int(part) for part in match.groups())).isoformat()
        except ValueError:
            pass
    return {name: day for name, day in found.items() if day}


def _title(notice: dict) -> str:
    reference = notice["step_reference"] or notice["bid_reference_no"]
    method = f" ({notice['procurement_method']})" if notice["procurement_method"] else ""
    head = f"{notice['notice_type']} {notice['notice_id']}"
    if reference:
        head += f", {reference}{method}"
    return f"{head}: {notice['bid_description']}" if notice["bid_description"] else head


def notice_item(source: ResearchSource, project: ProjectFacts, notice: dict, day: dt.date) -> dict:
    """One notice's item, from its row of strata.gold.notice with silver's text."""
    settings = source.settings
    register = settings.get("register_page", "").format(project_id=project.project_id) or None
    url = settings.get("notice_page", "{notice_id}").format(notice_id=notice["notice_id"])
    text = notice["notice_text"] or notice["bid_description"] or ""
    return make_item(project=project, source=source, item_key=notice["notice_id"], public_from=notice["public_from"],
                     published=notice["notice_date"], title=_title(notice), text=text, url=url, read_on=day,
                     author="World Bank procurement notices (STEP)", url_of_source=register)


def by_key(source: ResearchSource, project: ProjectFacts, engine, notice_id: str, day: dt.date) -> dict | None:
    """The item of one notice of the project named by its id, whatever its date, or None when the table has no row
    public by the day (ticket 152: the demo seed names notices older than the reader's window)."""
    found = rows(engine, "notice", project_id=project.project_id, notice_id=notice_id, as_of=day)
    return notice_item(source, project, found[0], day) if found else None


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    settings = source.settings
    if engine is None:
        return SourceResult(source.key, [], False, "no database", "Prism had no lakehouse to read the notices from.")
    day = as_of(now)
    since = day - dt.timedelta(days=int(settings.get("days", 180)))
    kinds = tuple(settings.get("notice_types", ("Contract Award", "Invitation for Bids")))
    items = [notice_item(source, project, notice, day)
             for notice in rows(engine, "recent_notices", project_id=project.project_id, since=since, as_of=day)
             if notice["notice_type"] in kinds]
    note = (f"Prism read {len(items)} contract awards and invitations for bids published from {long_date(since)} to "
            f"{long_date(day)}.")
    return SourceResult(source.key, items, True, "read", note)
