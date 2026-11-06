"""Reading an outlet's page (ticket 147): the article's own paragraphs, its title and the date it prints.

Only the standard library's HTML parser: a page's paragraphs are the text of its <p> elements, those inside <article>
when it has any, each of eight words or more, so a menu, a caption or a share button is left out; when they hold less
than an article, the articleBody the page's JSON-LD publishes stands in, if it is longer. The date is the one
the page prints for itself: its JSON-LD datePublished, its article:published_time, its first <time datetime>, or the
date in its address (/2026-01-14-, /2026/01/20/). No date is guessed.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
from html.parser import HTMLParser

# Elements whose text a reader never sees. A page's menus and footers are left out by their paragraphs' length instead,
# since a page that never closes its <nav>, <form> or <noscript> would otherwise hide its whole article (People
# Daily's page of November 5, 2026 opens a <noscript> in its head that the parser never sees close).
SKIPPED = {"script", "style", "svg"}
SHORTEST = 8  # the fewest words a paragraph of an article has
ENOUGH = 600  # the characters of paragraphs that make an article; with fewer, the page's JSON-LD articleBody may be it
URL_DATE = re.compile(r"/(20\d{2})[-/](\d{2})[-/](\d{2})(?:[-/]|$)")


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.article = 0
        self.paragraph: list[str] | None = None
        self.paragraphs: list[tuple[bool, str]] = []
        self.meta: dict[str, str] = {}
        self.title: list[str] | None = None
        self.titles: list[str] = []
        self.h1: list[str] | None = None
        self.h1s: list[str] = []
        self.times: list[str] = []
        self.json_ld: list[str] = []
        self.in_json_ld = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self.in_json_ld = True
            self.json_ld.append("")
            return
        if tag in SKIPPED:
            self.skip += 1
        elif tag == "article":
            self.article += 1
        elif tag == "p" and not self.skip:
            self.paragraph = []
        elif tag == "br" and self.paragraph is not None:
            self.paragraph.append(" ")
        elif tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
            if key and attrs.get("content") and key not in self.meta:
                self.meta[key] = attrs["content"]
        elif tag == "title":
            self.title = []
        elif tag == "h1":
            self.h1 = []
        elif tag == "time" and attrs.get("datetime"):
            self.times.append(attrs["datetime"])

    def handle_endtag(self, tag):
        if tag == "script" and self.in_json_ld:
            self.in_json_ld = False
            return
        if tag in SKIPPED:
            self.skip = max(0, self.skip - 1)
        elif tag == "article":
            self.article = max(0, self.article - 1)
        elif tag == "p" and self.paragraph is not None:
            self.paragraphs.append((self.article > 0, " ".join("".join(self.paragraph).split())))
            self.paragraph = None
        elif tag == "title" and self.title is not None:
            self.titles.append(" ".join("".join(self.title).split()))
            self.title = None
        elif tag == "h1" and self.h1 is not None:
            self.h1s.append(" ".join("".join(self.h1).split()))
            self.h1 = None

    def handle_data(self, data):
        if self.in_json_ld:
            self.json_ld[-1] += data
            return
        if self.title is not None:
            self.title.append(data)
        if self.h1 is not None:
            self.h1.append(data)
        if self.paragraph is not None and not self.skip:
            self.paragraph.append(data)


def _page(body: bytes | str) -> _Page:
    page = _Page()
    page.feed(body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body)
    page.close()
    return page


def paragraphs(body: bytes | str) -> list[str]:
    """The article's paragraphs, in order, each once: its <p> elements, or the articleBody its JSON-LD publishes when
    the <p> elements hold less than an article (a page that sets its story in other elements, as The Standard's)."""
    page = _page(body)
    long = [(inside, text) for inside, text in page.paragraphs if len(text.split()) >= SHORTEST]
    chosen = list(dict.fromkeys([text for inside, text in long if inside] or [text for _, text in long]))
    if sum(len(text) for text in chosen) >= ENOUGH:
        return chosen
    published = article_body(page)
    return published if sum(map(len, published)) > sum(map(len, chosen)) else chosen


def _bodies(value) -> list[str]:
    if isinstance(value, list):
        return [found for item in value for found in _bodies(item)]
    if isinstance(value, dict):
        own = [value["articleBody"]] if isinstance(value.get("articleBody"), str) else []
        return own + _bodies(value.get("@graph", []))
    return []


def article_body(page: _Page) -> list[str]:
    """The paragraphs of the articleBody the page's JSON-LD publishes, or none."""
    for block in page.json_ld:
        try:
            parsed = json.loads(block)
        except ValueError:
            continue
        for text in _bodies(parsed):
            parts = [" ".join(html.unescape(part).split()) for part in re.split(r"\n\s*\n|\r\n\r\n|\n", text)]
            parts = [part for part in parts if part]
            if parts:
                return parts
    return []


def _json_ld_dates(blocks: list[str]) -> list[str]:
    dates = []
    for block in blocks:
        dates += re.findall(r'"datePublished"\s*:\s*"([^"]+)"', block)
    return dates


def _day(value: str | None) -> dt.date | None:
    if not value:
        return None
    match = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", value)
    if not match:
        return None
    try:
        return dt.date(*(int(part) for part in match.groups()))
    except ValueError:
        return None


def page_date(body: bytes | str, url: str = "") -> dt.date | None:
    """The date the page prints for itself, or the date in its address, or None."""
    page = _page(body)
    for value in (*_json_ld_dates(page.json_ld), page.meta.get("article:published_time"),
                  page.meta.get("datepublished"), page.meta.get("date"), *page.times):
        day = _day(value)
        if day:
            return day
    match = URL_DATE.search(url)
    if match:
        try:
            return dt.date(*(int(part) for part in match.groups()))
        except ValueError:
            return None
    return None


def page_title(body: bytes | str) -> str | None:
    """The article's headline: its og:title, else its first <h1>, else its <title>."""
    page = _page(body)
    for value in (page.meta.get("og:title"), *(page.h1s[:1]), *(page.titles[:1])):
        if value and value.strip():
            return html.unescape(value.strip())
    return None


def plain(fragment: str | None) -> str:
    """A fragment of HTML, such as a feed's summary or a post's content, as plain text with its paragraphs."""
    if not fragment:
        return ""
    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", fragment)
    text = re.sub(r"(?i)</\s*p\s*>", "\n\n", text)
    text = re.sub(r"(?i)</?(?:a|span|b|i|em|strong|u|small|mark)\b[^>]*>", "", text)  # inside a word: #<span>Kenya
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text).strip()


def json_ld(body: bytes | str) -> list:
    """The page's JSON-LD blocks, parsed; a block that does not parse is left out."""
    found = []
    for block in _page(body).json_ld:
        try:
            found.append(json.loads(block))
        except ValueError:
            continue
    return found
