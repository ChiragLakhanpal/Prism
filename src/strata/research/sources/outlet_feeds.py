"""outlet_feeds: what the outlets that cover the project's region published lately (ticket 147).

Each feed the registry lists (config/research.toml, [[sources.outlet_feeds.feeds]]) is read with the named client,
as RSS 2.0 or Atom, and its entries are kept when their title or summary names an agency's short name or the
project's name, or a project place together with a sector word (strata.research.matching). For a kept entry the
reader opens the article's own page and keeps its paragraphs as the item's text, with the date the page prints. An
outlet whose page answers 403, 429 or a bot check keeps the feed's own summary as the text, and the note says its
page could not be read. A feed that refuses, or answers with something that is not a feed, gives no item, and the
note says which; the source is reached when one feed answered.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import xml.etree.ElementTree as ElementTree

from strata.config import Feed, ResearchSource
from strata.research.fetching import Unreachable, refusal
from strata.research.items import location_named, make_item, url_key
from strata.research.matching import about_the_project
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of
from strata.research.text import page_date, paragraphs, plain

ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return email.utils.parsedate_to_datetime(value.strip()).date()
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return dt.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def entries(body: bytes) -> list[dict] | None:
    """A feed's entries, each {title, link, published, summary}, or None when the body is no RSS or Atom feed."""
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        return None
    found = []
    if root.tag == "rss" or root.find("channel") is not None:
        for item in root.iter("item"):
            found.append({"title": (item.findtext("title") or "").strip(), "link": (item.findtext("link") or "").strip(),
                          "published": _date(item.findtext("pubDate")),
                          "summary": plain(item.findtext("description") or item.findtext(CONTENT) or "")})
        return found
    if root.tag == f"{ATOM}feed":
        for entry in root.iter(f"{ATOM}entry"):
            link = next((node.get("href") for node in entry.findall(f"{ATOM}link")
                         if node.get("rel") in (None, "alternate")), "")
            found.append({"title": (entry.findtext(f"{ATOM}title") or "").strip(), "link": (link or "").strip(),
                          "published": _date(entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated")),
                          "summary": plain(entry.findtext(f"{ATOM}summary") or entry.findtext(f"{ATOM}content") or "")})
        return found
    return None


def _article(fetch, link: str) -> tuple[str | None, dt.date | None, str | None]:
    """The article page's paragraphs and printed date, or why it could not be read."""
    try:
        answer = fetch(link)
    except Unreachable as unreachable:
        return None, None, f"could not be reached ({unreachable.reason})"
    refused = refusal(answer)
    if refused or answer[0] != 200:
        return None, None, "answered a bot check page" if refused == "bot check" else f"answered {refused or answer[0]}"
    found = paragraphs(answer[2])
    return ("\n\n".join(found) if found else None), page_date(answer[2], link), None


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    day, limit = as_of(now), int(source.settings.get("max_articles", 20))
    items, problems, unread, answered, opened = [], [], [], 0, 0
    for feed in source.feeds:
        problem = _feed_problem(fetch, feed)
        if isinstance(problem, str):
            problems.append(problem)
            continue
        answered += 1
        for entry in problem:
            if not entry["link"].startswith(("https://", "http://")) or not about_the_project(
                    project, f"{entry['title']}\n{entry['summary']}", agency_alone=True):
                continue
            text, printed, why = (None, None, "was not opened: the run's limit of articles was reached")
            if opened < limit:
                opened += 1
                text, printed, why = _article(fetch, entry["link"])
            if why:
                unread.append(feed.outlet)
            published = printed or entry["published"]
            if published and published > day:
                continue
            items.append(make_item(
                project=project, source=source, item_key=url_key(entry["link"]), public_from=published,
                published=published, title=entry["title"], text=text or entry["summary"] or entry["title"],
                url=entry["link"], read_on=day, author=feed.outlet,
                location=location_named(project, entry["title"], text or entry["summary"]), url_of_source=feed.url))
    if not answered:
        return SourceResult(source.key, [], False, "no feed", " ".join(problems) or "No feed is listed.")
    note = (f"Prism read {answered} of {len(source.feeds)} feeds and kept {len(items)} entries that name the project, "
            "its agencies or its places.")
    if unread:
        note += (f" The pages of {', '.join(dict.fromkeys(unread))} could not be read, so the feed's own summary "
                 "stands in for the article.")
    if problems:
        note += " " + " ".join(problems)
    return SourceResult(source.key, items, True, "200", note)


def _feed_problem(fetch, feed: Feed) -> list[dict] | str:
    """The feed's entries, or one sentence on why it gave none."""
    try:
        answer = fetch(feed.url)
    except Unreachable as unreachable:
        return f"{feed.outlet}'s feed could not be reached ({unreachable.reason})."
    refused = refusal(answer)
    if refused or answer[0] != 200:
        return f"{feed.outlet}'s feed answered {refused or answer[0]}."
    found = entries(answer[2])
    return found if found is not None else f"{feed.outlet}'s feed address answered a web page, not a feed."
