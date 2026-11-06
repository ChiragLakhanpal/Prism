"""gdelt_news: what GDELT's news index holds about the project (ticket 147).

One call to the GDELT DOC 2.0 API, in article list mode, over the last 24 months, newest first. The query is quoted
phrases joined with OR: the agencies' short names, the project's name, and each place with the sector's first word
(Baricho water), at most settings.max_phrases of them. Each article is one item with its title, the day GDELT saw it
and the outlet's domain; GDELT gives no article's text. A 429 gives reached False and the note "GDELT limited calls
from this network", and Prism does not try again.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.parse

from strata.config import ResearchSource
from strata.research.fetching import body_of
from strata.research.items import location_named, make_item, url_key
from strata.research.matching import sector_words
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of


def query(project: ProjectFacts, max_phrases: int = 12) -> str:
    words = sector_words(project)
    phrases = [project.project_name, *project.short_names,
               *(f"{place} {words[0]}" for place in project.place_names if words)]
    phrases = [phrase for phrase in dict.fromkeys(phrases) if phrase][:max_phrases]
    return "(" + " OR ".join(f'"{phrase}"' for phrase in phrases) + ")"


def _seen(value: str | None) -> dt.date | None:
    try:
        return dt.datetime.strptime((value or "")[:8], "%Y%m%d").date()
    except ValueError:
        return None


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    url = source.endpoint.format(query=urllib.parse.quote(query(project, int(source.settings.get("max_phrases", 12)))))
    body = body_of(fetch, url, source.label)
    try:
        articles = json.loads(body or b"{}").get("articles") or []
    except ValueError:
        message = " ".join(body.decode("utf-8", errors="replace").split())[:160]
        return SourceResult(source.key, [], False, "200",
                            f"GDELT answered with a message, not a list of articles: {message}")
    items = []
    for article in articles:
        link, title = article.get("url"), article.get("title")
        if not link or not title:
            continue
        seen = _seen(article.get("seendate"))
        items.append(make_item(project=project, source=source, item_key=url_key(link), public_from=seen,
                               published=seen, title=title, text=title, url=link, read_on=as_of(now),
                               author=article.get("domain"), location=location_named(project, title),
                               url_of_source="https://www.gdeltproject.org/"))
    return SourceResult(source.key, items, True, "200", f"GDELT listed {len(items)} articles for the project's names.")
