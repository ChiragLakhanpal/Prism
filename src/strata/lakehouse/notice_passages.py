"""Procurement notices' scope and qualification text, read into passages (ticket 18; spec, "Reading
documents": "Notices' scope and qualification text is indexed as passages too, so criteria can be
compared").

A notice's text comes only from strata.silver.notices.notice_text, which ticket 07's fetch stripped
of contact names, emails and phone numbers, writing "[contact removed]" where it took one out. The
recorded notices keep their contact details on purpose, so this module never reads them.

notice_text holds one line per paragraph. A notice of a type that carries scope and qualification
text (config/slice.toml, notice_types) is divided into sections at each heading line: a short line
that ends with a colon ("The short listing criteria are:"), or a short line in title case with no
closing stop ("Selection Method"). A section keeps its heading as its name, and the lines before the
first heading form a section named by the notice's first line. A name is kept only when it reads as a
heading (label()): six words or fewer, no comma, and no lead-in word at its end, so a sentence that ends
in a colon ("Specifically, the successful candidate shall have the following qualifications:") starts a
section with no name, and the drawer never shows a sentence as a section (ticket 63). A section of a
few words only, such as "Country: Kenya", joins the section after it. A section over max_tokens tokens is divided at a line
end, and the parts share its name. Each section, or part, is one passage of the kind notice_text,
whose evidence id names the notice: strata.gold.passage:OP00118817/v1/s3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from strata.lakehouse.engine import Engine
from strata.reader import passages as route_a

# The newest copy of each notice of the run's projects and of the types that carry scope and
# qualification text. Notices cover every country, so the filters run in the query. :projects and :types
# are joined by commas, which no project ID or notice type contains.
NOTICES = """
SELECT notice_id, notice_type, notice_date, notice_language, project_id, notice_text, public_from
FROM strata.silver.notices
WHERE notice_text IS NOT NULL
  AND array_contains(split(:projects, ','), project_id)
  AND array_contains(split(:types, ','), notice_type)
QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC) = 1
"""
SHORTEST_SECTION = 12  # words: a section with fewer joins the one after it, as "Country: Kenya" does
HEADING_WORDS = 10  # a heading line has at most this many words
LABEL_WORDS = 6  # a section's name has at most this many words; a longer heading line is a sentence
# Words that end a sentence leading into what follows, never a heading: "The short listing criteria are:".
LEAD_INS = {"are", "is", "include", "includes", "from", "following", "follows", "below", "to", "of", "the"}


@dataclass(frozen=True)
class Notice:
    notice_id: str
    notice_type: str
    notice_date: object
    language: str | None
    project_id: str
    text: str
    public_from: object


@dataclass(frozen=True)
class Section:
    key: str  # s1, s2, ...; a part adds its number: s3/2
    name: str  # the heading, word for word, without its closing colon
    part: int
    parts: int
    text: str


def notices(engine: Engine, projects: list[str], notice_types: tuple[str, ...]) -> list[Notice]:
    """The newest copy of each notice of the given projects and types, in notice id order."""
    if not projects or not notice_types:
        return []
    result = engine.run(NOTICES, {"projects": ",".join(projects), "types": ",".join(notice_types)})
    return sorted((Notice(*row) for row in result.rows), key=lambda notice: notice.notice_id)


def _heading(line: str) -> bool:
    text = route_a.words(line)
    count = len(text.split())
    if not 0 < count <= HEADING_WORDS:
        return False
    if text.endswith(":"):
        return True
    title_case = all(word[:1].isupper() or not word[:1].isalpha() for word in text.split())
    return count <= 4 and title_case and text[-1] not in ".;,!?" and not any(ch.isdigit() for ch in text)


def label(line: str) -> str:
    """A heading line as a section's name, or "" when it reads as a sentence rather than a heading."""
    words = line.split()
    if not words or len(words) > LABEL_WORDS or "," in line or words[-1].lower() in LEAD_INS:
        return ""
    return line


def sections(text: str, max_tokens: int) -> list[Section]:
    """A notice's text divided into its sections, each with its heading as its name, or "" when its heading reads
    as a sentence."""
    lines = [route_a.words(line) for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    blocks: list[list] = [[lines[0].rstrip(":"), []]]
    for line in lines:
        if _heading(line) and blocks[-1][1]:
            blocks.append([line.rstrip(":").strip(), [line]])
        else:
            blocks[-1][1].append(line)
    merged: list[list] = []
    carried: list[str] = []
    for name, body in blocks:
        body = carried + body
        if len(" ".join(body).split()) < SHORTEST_SECTION:
            carried = body
            continue
        carried = []
        merged.append([name, body])
    if carried:
        if merged:
            merged[-1][1] += carried
        else:
            merged.append([blocks[0][0], carried])
    found = []
    for number, (name, body) in enumerate(merged, 1):
        parts, current = [], []
        for line in body:
            if current and route_a.tokens(" ".join(current + [line])) > max_tokens:
                parts.append(" ".join(current))
                current = []
            current.append(line)
        parts.append(" ".join(current))
        for index, part in enumerate(parts, 1):
            key = f"s{number}" if len(parts) == 1 else f"s{number}/{index}"
            found.append(Section(key, label(name), index, len(parts), part))
    return found
