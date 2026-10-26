"""The number check (ticket 46; the 46 brief, sections 9.1 and 9.5).

Every number in the proposal links to its row in the results register (#r-<key>, Annex 1) or the settings register
(#s-<key>, Annex 2), and the rubric's points link to the assessment's rubric. Anything else that looks like a number
fails, unless it is one of the excepted kinds:

- dates, years and fiscal years ("October 20, 2026", "Oct 20, 2026", "fiscal 2017", "FY2017–19", "2019–23")
- sequence numbers: paragraph, section, module, figure, annex, page, ISR, report, component, phase, rule, decision,
  ticket and step numbers, and ¶ references
- identifiers: project IDs, STEP references, notice IDs, passage IDs, model names and anything in code
- standard names (WCAG 2.2, the 7th edition of the Regulations)
- the fixed names on the allow list, docs/proposal/number_check.toml, each with its reason, in any case
- a row of Annex 1 or Annex 2 itself (a line with an r- or s- anchor), which holds the value its links point at
- in the deck's HTML (ticket 47), its chrome: an element marked data-chrome, such as "4 of 16" under a slide

It counts numerals and number words, two to nine and ten and up. "One" is left out, because it is mostly a pronoun. Image alt text
holds no links, so the check leaves it to the build, which fills every number there from the snapshot.

unsourced() reads Markdown, as the proposal is written, or HTML, as the deck renders a slide, where an element with
a data-source-key attribute holds a number bound to its snapshot key. It is a plain function over text, so any
document can call it. The deck's screen tests call it as a command: `python -m strata.proposal.numbers` reads a JSON
object of HTML pieces by where each is ("Slide 4, notes"), prints a JSON list of the numbers with no source, and
exits 1 when there is one.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from strata.proposal import register

ALLOW_FILE = Path(__file__).resolve().parents[3] / "docs" / "proposal" / "number_check.toml"
RUBRIC_ANCHOR = "assessment.md#5-evaluation--assessment-rubric"

# The month names and their short forms, as in "October 20, 2026", "Oct 20" and "Sept 3".
MONTHS = "|".join((*register.MONTHS, *(month[:3] for month in register.MONTHS if month != "May"), "Sept"))
SEQUENCE = ("paragraphs?|Paragraphs?|sections?|Sections?|Modules?|modules?|Figures?|figures?|Annex(?:es)?|annex|"
            "pages?|Pages?|ISRs?|Components?|components?|Phases?|phases?|rules?|Rules?|decisions?|tickets?|Tickets?|"
            "steps?|Steps?|Slides?|slides?|ADRs?|version|Seq No|[Rr]ounds?|Reports?")
EXCEPTED = [re.compile(pattern) for pattern in (
    rf"\b(?:{MONTHS})\.? \d{{1,2}}(?:, \d{{4}})?\b",       # October 20, 2026; Oct 20
    rf"\b(?:{MONTHS}) \d{{4}}\b",                          # March 2022
    r"\b\d{4}-\d{2}-\d{2}\b",                             # 2026-10-09
    r"\bFY ?\d{2,4}(?:\s*[–-]\s*(?:FY ?)?\d{2,4})?\b",     # FY2017–19, FY01
    r"\b(?:19|20)\d{2}(?:\s*[–-]\s*\d{2,4})?\b",            # 2021, 2019–23
    rf"\b(?:{SEQUENCE})\s+\d+(?:\s*(?:[–-]|,|and|to)\s*\d+)*\b",   # paragraph 78, Components 2 and 3, pages 3 to 5
    r"¶\s*\d+(?:\s*[–-]\s*\d+)?",                           # ¶54, ¶12–19
    r"\bp\.\s?\d+\b",                                      # p.23, a passage header's page
    r"\bP\d{6}\b",                                         # project IDs
    r"\b[A-Z]{2}-[A-Z0-9]+(?:-[A-Z0-9]+)+\b",              # STEP references
    r"\bOP\d+\b",                                          # notice IDs
    r"\b\d{6,}/v\d+/\S+",                                  # passage IDs
    r"\bgpt-[\w.-]+|\btext-embedding-[\w.-]+",             # model names
    r"\bWCAG \d(?:\.\d)?\b",                               # standards
    r"\b\d+(?:st|nd|rd|th) edition\b",                     # the 7th edition
    r"\bCC BY \d\.\d\b",                                   # the license's name
    r"https?://[^\s\"<>)]+",                               # an address, as a link's text
)]
NUMERAL = re.compile(r"(?<![\w.])\d(?:[\d,]*\d)?(?:\.\d+)?(?![\w])")
# Number words: two to nine, and ten and up (ticket 49: the P3 gate found "in under ten minutes" unchecked). A word
# such as ninety-nine counts once. "One" is left out, because it is mostly a pronoun.
_UNITS = "one|two|three|four|five|six|seven|eight|nine"
_TENS = "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
WORD = re.compile(rf"\b(?:(?:{_TENS})(?:-(?:{_UNITS}))?|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                  r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|hundred|thousand|million|billion)\b",
                  re.I)

_SOURCED_LINK = re.compile(r"\[[^\]]*\]\((?:#[rs]-[^)\s]*|[^)\s]*" + re.escape(RUBRIC_ANCHOR) + r")(?:\s+\"[^\"]*\")?\)")
_SOURCED_ANCHOR = re.compile(r"<a\s[^>]*href=\"(?:#[rs]-[^\"]*|[^\"]*" + re.escape(RUBRIC_ANCHOR) + r")\"[^>]*>.*?</a>",
                             re.S)
_SOURCED_ELEMENT = re.compile(r"<(\w+)\b[^>]*\bdata-source-key=\"[^\"]*\"[^>]*>.*?</\1>", re.S)
# The deck's chrome (ticket 47; the 47 brief, section 6.3): slide numbers and the notes view's timer, which count
# slides and minutes, not anything Strata measured. The element holds no other element.
_CHROME = re.compile(r"<(\w+)\b[^>]*\bdata-chrome\b[^>]*>[^<]*</\1>")
# In HTML, a style or script block holds no words a reader reads, such as an inlined figure's CSS.
_STYLE = re.compile(r"<(style|script)\b[^>]*>.*?</\1>", re.S | re.I)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_CODE = re.compile(r"`[^`]*`|<code>.*?</code>")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_TAG = re.compile(r"<[^>]+>")
_ENTITY = re.compile(r"&[a-z]+;|&#\d+;")
_PARAGRAPH = re.compile(r"<a id=\"p(\d+)\"></a>")
# A register's own row, which holds the value every link to it points at.
_REGISTER_ROW = re.compile(r"<a id=\"[rs]-[^\"]+\"></a>")
_PARAGRAPH_MARK = re.compile(r"^\s*(?:\*\*\d+\.\*\*|\d+\.\s)")  # a paragraph's number, or an ordered list's
_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$")


@dataclass(frozen=True)
class Unsourced:
    """A number with no source: where it is, the number as written and the text around it."""

    where: str
    number: str
    excerpt: str

    def sentence(self) -> str:
        return (f"The number check failed. {self.where} has a number with no source: \"{self.excerpt}\". "
                "Link it to Annex 1 or Annex 2, or add it to the allow list with a reason.")


@cache
def allow_list(path: Path = ALLOW_FILE) -> tuple[str, ...]:
    """The fixed names that may hold a number, longest first, so a longer name is removed before a part of it."""
    with open(path, "rb") as handle:
        entries = tomllib.load(handle).get("allow", [])
    for entry in entries:
        if not entry.get("phrase") or not entry.get("reason"):
            raise ValueError(f"In {path.name}, every [[allow]] needs a phrase and a reason.")
    return tuple(sorted((entry["phrase"] for entry in entries), key=len, reverse=True))


def _clean(line: str, allow: Sequence[str]) -> str:
    """The line's readable words, with every sourced number and every excepted kind taken out."""
    for pattern in (_COMMENT, _IMAGE, _SOURCED_LINK, _SOURCED_ANCHOR, _SOURCED_ELEMENT):
        line = pattern.sub(" ", line)
    line = _LINK.sub(r"\1", line)
    line = _CODE.sub(" ", line)
    line = _PARAGRAPH.sub(" ", line)
    line = _TAG.sub(" ", line)
    line = _ENTITY.sub(" ", line)
    line = _PARAGRAPH_MARK.sub(" ", line)
    for phrase in allow:
        line = re.sub(re.escape(phrase), " ", line, flags=re.I)
    for pattern in EXCEPTED:
        line = pattern.sub(" ", line)
    return line


def _readable(line: str) -> str:
    """The line as a reader sees it, for the excerpt: links as their words, tags and marks left out."""
    line = _IMAGE.sub(" ", _COMMENT.sub(" ", line))
    line = _LINK.sub(r"\1", _PARAGRAPH.sub("", line))
    line = _PARAGRAPH_MARK.sub("", _TAG.sub("", line))
    return re.sub(r"\s+", " ", line).strip()


def unsourced(text: str, form: str = "markdown", allow: Sequence[str] | None = None) -> list[Unsourced]:
    """Every number in text that has no source and is not excepted, in reading order."""
    if form not in ("markdown", "html"):
        raise ValueError(f"The number check reads markdown or html, not {form}.")
    allow = allow_list() if allow is None else allow
    if form == "html":
        # Whole elements go before the text is cut into lines, so a sourced chart or table, which spans many block
        # elements, is taken out whole.
        for pattern in (_COMMENT, _STYLE, _SOURCED_ELEMENT, _CHROME):
            text = pattern.sub(" ", text)
        text = re.sub(r"</(?:p|li|tr|h[1-6]|div|section|td|th)>", "\n", text)
    found: list[Unsourced] = []
    where = "The text"
    for line in text.splitlines():
        heading = _HEADING.match(line) if form == "markdown" else None
        if heading:
            where = f"The block under \"{_TAG.sub('', heading.group(1)).strip()}\""
        marked = _PARAGRAPH.search(line)
        if marked:
            where = f"Paragraph {marked.group(1)}"
        if _REGISTER_ROW.search(line):
            continue
        cleaned = _clean(line, allow)
        numbers = sorted([(match.start(), match.group()) for match in NUMERAL.finditer(cleaned)]
                         + [(match.start(), match.group()) for match in WORD.finditer(cleaned)])
        excerpt = _readable(line)
        if len(excerpt) > 160:
            excerpt = excerpt[:157].rstrip() + "..."
        found += [Unsourced(where, number, excerpt) for _, number in numbers]
    return found


def main() -> int:
    """The check over named pieces of HTML, as the deck's screen tests give them on standard input."""
    import json
    import sys

    pieces = json.loads(sys.stdin.read())
    found = [{"where": where, "number": problem.number, "excerpt": problem.excerpt}
             for where, html in pieces.items() for problem in unsourced(html, form="html")]
    print(json.dumps(found))
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
