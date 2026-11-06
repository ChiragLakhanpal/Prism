"""agency_statements: what the project's implementing agencies say on their own news pages (ticket 154).

The registry lists each agency's page by the agency's short name (config/research.toml,
[[sources.agency_statements.pages]]). The reader reads the pages of the agencies the project record names, with the
named client, and lists each page's entries: a block of the page (an <article>, a Joomla blog post or a card) with a
heading, the link the heading or the block holds, and the date the entry prints, or else the date its title or its
address writes. For an entry whose link is a web page the reader opens it and keeps its paragraphs as the item's
text, with the date the page prints when the entry printed none; an entry that links a PDF or no page keeps the words
the list prints. Each entry is one item, its author the agency as the project record names it.

A page that refuses gives no entry, and the note says so; the source is reached when one page answered.
"""

from __future__ import annotations

import datetime as dt
import re
import urllib.parse

from strata.config import AgencyPage, ResearchSource
from strata.research.fetching import Unreachable, refusal
from strata.research.items import location_named, make_item, url_key
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of
from strata.research.sources.outlet_feeds import _article
from strata.research.text import plain

BLOCK = re.compile(r'<article\b|itemprop="blogPost"|class="card-body"', re.I)
HEADING = re.compile(r"<h([1-5])\b[^>]*>(.*?)</h\1>", re.S | re.I)
LINK = re.compile(r'<a\b[^>]*href="([^"#][^"]*)"', re.I)
TIME = re.compile(r'<time\b[^>]*datetime="([^"]+)"', re.I)
DATE_SPAN = re.compile(r'<(?:span|div|p)\b[^>]*class="[^"]*date[^"]*"[^>]*>(.*?)</(?:span|div|p)>', re.S | re.I)
PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
POST_TITLE = re.compile(r'class="[^"]*post__title[^"]*"[^>]*>\s*<a\b[^>]*>(.*?)</a>', re.S | re.I)
POST_TITLE_LINK = re.compile(r'class="[^"]*post__title[^"]*"[^>]*>\s*<a\b[^>]*href="([^"]+)"', re.I)
IMAGE_SOURCE = re.compile(r'<img\b[^>]*src="([^"]+)"', re.I)
IMAGE = (".jpg", ".jpeg", ".png", ".gif", ".webp")
MONTHS = {name: number for number, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
     "december"], 1)}
MONTH = "(" + "|".join(MONTHS) + ")"
DAY_MONTH_YEAR = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[\s-]+{MONTH}[\s,-]+(20\d\d)\b", re.I)
MONTH_DAY_YEAR = re.compile(rf"\b{MONTH}[\s-]+(\d{{1,2}})(?:st|nd|rd|th)?,?[\s-]+(20\d\d)\b", re.I)
ISO = re.compile(r"\b(20\d\d)-(\d{2})-(\d{2})\b")


def written_date(text: str | None) -> dt.date | None:
    """The first date a text writes, as 2nd June 2026, June 2, 2026 or 2026-06-02, or None."""
    if not text:
        return None
    found = []
    for pattern, order in ((DAY_MONTH_YEAR, "dmy"), (MONTH_DAY_YEAR, "mdy"), (ISO, "ymd")):
        for match in pattern.finditer(text):
            parts = dict(zip(order, match.groups()))
            month = MONTHS.get(parts["m"].lower()) if not parts["m"].isdigit() else int(parts["m"])
            try:
                found.append((match.start(), dt.date(int(parts["y"]), month, int(parts["d"]))))
            except (TypeError, ValueError):
                continue
    return min(found)[1] if found else None


def _text(fragment: str) -> str:
    return " ".join(plain(fragment).split())


def _absolute(page_url: str, link: str) -> str:
    return urllib.parse.urljoin(page_url, urllib.parse.quote(link, safe=":/?&=%#+,;@"))


def _entry_link(block: str, heading, page_url: str) -> str | None:
    """The entry's own address on the agency's site: the link its heading or its post title holds, else the first PDF
    the block links on the same site. A link to another site (a social post, a meeting) is not the entry's."""
    host = urllib.parse.urlsplit(page_url).netloc
    titled = (LINK.findall(heading.group(2)) if heading else []) + POST_TITLE_LINK.findall(block)
    pdfs = [link for link in LINK.findall(block) if link.lower().endswith(".pdf")]
    for link in [*titled, *pdfs]:
        absolute = _absolute(page_url, link)
        if absolute.startswith(("https://", "http://")) and urllib.parse.urlsplit(absolute).netloc == host \
                and not absolute.lower().endswith(IMAGE):
            return absolute
    return None


def entries(body: bytes | str, page_url: str) -> list[dict]:
    """The page's entries, each {title, link, printed, summary}: link is an absolute address or None, printed the date
    the entry prints or writes in its title or address."""
    page = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
    page = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", page, flags=re.S | re.I)
    starts = [match.start() for match in BLOCK.finditer(page)]
    found = []
    for start, end in zip(starts, [*starts[1:], len(page)]):
        block = page[start:end]
        heading = HEADING.search(block)
        titled = POST_TITLE.search(block)
        title = _text(heading.group(2) if heading else titled.group(1) if titled else "")
        if len(title.split()) < 2:
            continue
        link = _entry_link(block, heading, page_url)
        stamp = TIME.search(block)
        span = DATE_SPAN.search(block)
        image = IMAGE_SOURCE.search(block)
        printed = (written_date(stamp.group(1)) if stamp else None) or (written_date(_text(span.group(1))) if span
                                                                       else None)
        printed = (printed or written_date(title) or written_date(urllib.parse.unquote(link or "").replace("-", " "))
                   or (written_date(urllib.parse.unquote(image.group(1))) if image else None))
        summary = "\n\n".join(text for text in (_text(part) for part in PARAGRAPH.findall(block)) if text)
        found.append({"title": title, "link": link, "printed": printed, "summary": summary})
    return list({(entry["title"], entry["link"]): entry for entry in found}.values())


def _agency_name(project: ProjectFacts, page: AgencyPage) -> str | None:
    """The agency as the project record names it, when the record names the page's agency; else None."""
    for agency in project.implementing_agencies:
        if page.agency == agency.name or page.agency in agency.short_names:
            return agency.name
    return None


def _listing(fetch, page: AgencyPage) -> list[dict] | str:
    """The page's entries, or one sentence on why it gave none."""
    try:
        answer = fetch(page.url)
    except Unreachable as unreachable:
        return f"{page.agency}'s page could not be reached ({unreachable.reason})."
    refused = refusal(answer)
    if refused or answer[0] != 200:
        return f"{page.agency}'s page answered {refused or answer[0]}."
    return entries(answer[2], page.url)


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    day, limit = as_of(now), int(source.settings.get("max_entries", 12))
    pages = [(page, name) for page in source.pages if (name := _agency_name(project, page))]
    if not pages:
        return SourceResult(source.key, [], False, "no page",
                            "The registry lists no news page for the agencies the project record names.")
    items, problems, answered, opened = [], [], [], 0
    for page, agency in pages:
        listed = _listing(fetch, page)
        if isinstance(listed, str):
            problems.append(listed)
            continue
        answered.append(page.agency)
        for entry in listed:
            text, printed = None, None
            link = entry["link"]
            if link and not link.lower().endswith(".pdf") and urllib.parse.urlsplit(link).netloc == \
                    urllib.parse.urlsplit(page.url).netloc and opened < limit:
                opened += 1
                text, printed, _ = _article(fetch, link)
            published = entry["printed"] or printed
            if published and published > day:
                continue
            words = text or entry["summary"] or entry["title"]
            items.append(make_item(
                project=project, source=source, item_key=url_key(f"{link or page.url}#{entry['title']}"),
                public_from=published, published=published, title=entry["title"], text=words, url=link or page.url,
                read_on=day, author=agency, location=location_named(project, entry["title"], words),
                url_of_source=page.url))
    if not answered:
        return SourceResult(source.key, [], False, "no page", " ".join(problems))
    note = (f"Prism read the news pages of {', '.join(answered)} and kept {len(items)} entries.")
    if problems:
        note += " " + " ".join(problems)
    return SourceResult(source.key, items, True, "200", note)
