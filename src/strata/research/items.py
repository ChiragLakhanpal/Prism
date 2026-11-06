"""The one shape of a deep research item (ticket 147), which every later ticket reads (148 writes the brief from
items, 149 shows and prints them, 150 adds field photos).

    evidence_id   strata.research.item:<project_id>/<source key>/<item key>, the key stable for the source
    public_from   the date the item became public (ADR 0002)
    source        {key, label, kind, license, url_of_source}
    kind          the registry's kind
    title         one line
    text          the source's own words, up to 4,000 characters, contact details stripped; never Prism's summary
    url           the page a person opens to see the item itself
    published     ISO date or None; date_known False when the source prints none
    date_known
    observed      ISO date the item is about when that differs, else None
    location      {geo_loc_id, name, latitude, longitude} or None
    image_urls    for a satellite item, the tile addresses of two years as two lists of nine, else empty
    author        the outlet, agency or account as the source prints it; never an email or a phone number
    read_on       ISO date of the fetch

make_item() builds one and is the only way a reader makes one, so every item's text goes through the stripper the
notices use (strata.lakehouse.contacts.strip_again) and is cut to 4,000 characters, and every evidence id has the
same form. An item whose source prints no date became public no later than the day Prism read it, so that day is
its public_from.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re

from strata.config import ResearchSource
from strata.lakehouse.contacts import REMOVED, strip_again

PREFIX = "strata.research.item:"
ITEM_KEYS = ("evidence_id", "public_from", "source", "kind", "title", "text", "url", "published", "date_known",
             "observed", "location", "image_urls", "author", "read_on")
TEXT_LIMIT = 4000
TITLE_LIMIT = 300
SPACES = re.compile(r"[ \t ]+")


def evidence_id(project_id: str, source_key: str, item_key: str) -> str:
    return f"{PREFIX}{project_id}/{source_key}/{item_key}"


def url_key(url: str) -> str:
    """An article's key: the first 16 hexadecimal digits of its address's SHA-256."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def iso(value) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return dt.date.fromisoformat(str(value)[:10]).isoformat()


def _cut(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    return cut[:space] if space > limit * 0.8 else cut


def clean(text: str | None, limit: int = TEXT_LIMIT) -> str:
    """The source's words with contact details stripped, spaces tidied and paragraphs kept, cut to limit."""
    stripped = strip_again(text or "") or ""
    paragraphs = [SPACES.sub(" ", part).strip() for part in re.split(r"\n\s*\n", stripped.replace("\r", ""))]
    joined = "\n\n".join(" ".join(line.strip() for line in part.splitlines() if line.strip())
                         for part in paragraphs if part)
    return _cut(joined, limit)


def one_line(text: str | None, limit: int = TITLE_LIMIT) -> str:
    return _cut(" ".join((strip_again(text or "") or "").split()), limit)


def _author(author: str | None) -> str | None:
    if not author:
        return None
    kept = one_line(author, 120)
    return None if REMOVED in kept or "@" in kept.lstrip("@") else kept or None


def make_item(*, project, source: ResearchSource, item_key: str, public_from, title: str, text: str, url: str,
              read_on, published=None, date_known: bool | None = None, observed=None, location=None,
              image_urls=(), author: str | None = None, url_of_source: str | None = None) -> dict:
    """One item in the one shape. location is a project Location or None; read_on the day of the fetch."""
    if not url or not url.startswith(("https://", "http://")):
        raise ValueError(f"An item needs an address a person can open, not {url!r}.")
    read_on = iso(read_on)
    published = iso(published)
    return {
        "evidence_id": evidence_id(project.project_id, source.key, item_key),
        "public_from": iso(public_from) or published or read_on,
        "source": {"key": source.key, "label": source.label, "kind": source.kind, "license": source.license,
                   "url_of_source": url_of_source or source.endpoint},
        "kind": source.kind,
        "title": one_line(title) or one_line(text, 120),
        "text": clean(text),
        "url": url,
        "published": published,
        "date_known": bool(published) if date_known is None else date_known,
        "observed": iso(observed),
        "location": location.as_dict() if location is not None else None,
        "image_urls": [list(urls) for urls in image_urls],
        "author": _author(author),
        "read_on": read_on,
    }


def location_named(project, *texts: str):
    """The project location the texts name first (the title before the text), as a word, or None."""
    joined = "\n".join(text or "" for text in texts)
    found = []
    for location in project.locations:
        match = re.search(rf"\b{re.escape(location.place)}\b", joined, re.I) if location.place else None
        if match:
            found.append((match.start(), -len(location.place), location))
    return min(found, key=lambda entry: entry[:2])[2] if found else None
