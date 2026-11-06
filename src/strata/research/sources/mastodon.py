"""mastodon: what people post in public about the project's places (ticket 147).

Mastodon's public tag timelines on mastodon.social, for the tags settings.tags names: the country's name, the sector's
first word and each location's place name (kenya, water, wajir, westpokot). A post is kept only when its text names a
project place or an agency's short name together with a sector word (strata.research.matching), so a tag alone never
brings a post in. The post's author is the name the account shows, never its address. The brief says when no post is
about the works.
"""

from __future__ import annotations

import datetime as dt
import json

from strata.config import ResearchSource
from strata.research.fetching import Unreachable, refusal, refusal_note
from strata.research.items import location_named, make_item
from strata.research.matching import about_the_project, sector_words, tag
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of
from strata.research.text import plain


def tags(project: ProjectFacts, asked: list[str]) -> list[str]:
    words = sector_words(project)
    found = []
    for kind in asked:
        if kind == "country" and project.country_name:
            found.append(tag(project.country_name))
        elif kind == "sector" and words:
            found.append(tag(words[0]))
        elif kind == "locations":
            found += [tag(place) for place in project.place_names]
    return [name for name in dict.fromkeys(found) if name]


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    day = as_of(now)
    asked = tags(project, list(source.settings.get("tags", ("country", "sector"))))
    items, seen, problems, answered = [], set(), [], 0
    for name in asked:
        url = source.endpoint.format(tag=name)
        try:
            answer = fetch(url)
        except Unreachable as unreachable:
            problems.append(unreachable.reason)
            continue
        refused = refusal(answer)
        if refused or answer[0] != 200:
            problems.append(refused or str(answer[0]))
            continue
        try:
            posts = json.loads(answer[2])
        except ValueError:
            problems.append("not a list of posts")
            continue
        answered += 1
        for post in posts if isinstance(posts, list) else []:
            text, link = plain(post.get("content")), post.get("url") or post.get("uri")
            if post.get("id") in seen or not link or not about_the_project(project, text, agency_alone=False):
                continue
            seen.add(post.get("id"))
            created = (post.get("created_at") or "")[:10] or None
            account = post.get("account") or {}
            author = account.get("display_name") or (f"@{account['username']}" if account.get("username") else None)
            items.append(make_item(project=project, source=source, item_key=str(post["id"]), public_from=created,
                                   published=created, title=text.split("\n")[0], text=text, url=link, read_on=day,
                                   author=author, location=location_named(project, text),
                                   url_of_source=source.endpoint.format(tag=name)))
    if not answered:
        status = problems[0] if problems else "no tag"
        return SourceResult(source.key, [], False, status,
                            refusal_note(source.label, status) if status in ("403", "429", "bot check") else
                            f"Mastodon answered no tag timeline ({status}).")
    note = (f"Prism read {answered} tag timelines and kept {len(items)} posts that name a project place or agency "
            "together with a sector word.")
    return SourceResult(source.key, items, True, "200", note)
