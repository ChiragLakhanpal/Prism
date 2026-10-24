"""The ISR rating history, read from the ISRs themselves (ticket 18; spec, "Data and the lakehouse run":
"duplicate ISR ratings from the projects API are removed and the rating history is read from ISR
text"). The projects API keeps only each project's latest ratings, so this is the only history.

Every ISR prints its overall ratings as a small table: each rating's name, then its previous and its
current rating, each after a bullet glyph. The text layer of each PDF page keeps that line whole
("Progress towards achievement of PDO \\uf06c Satisfactory \\uf06c Satisfactory"), or sets the table out
by column, or, in a project's first ISR, gives the current rating alone; the run reads each form from
bronze.document_pages, with the ISR's sequence number from its first page ("Seq No: 7"). A rating of
"--" is no rating. Each rating is one row of strata.silver.isr_ratings, rebuilt for the run's projects
on every run.
"""

from __future__ import annotations

import re

from strata.lakehouse.engine import Engine

ISR = "Implementation Status and Results Report"
# The ratings an ISR's overall ratings table names, word for word, and the values a rating takes.
RATINGS = ("Progress towards achievement of PDO", "Overall Implementation Progress (IP)", "Overall Risk Rating")
VALUES = ("Highly Satisfactory", "Moderately Satisfactory", "Satisfactory", "Highly Unsatisfactory",
          "Moderately Unsatisfactory", "Unsatisfactory", "Low", "Moderate", "Substantial", "High", "--")
BULLETS = "\uf06c\x80\u2022"  # the bullet glyph an ISR prints before each rating, as its text layer gives it
NAME = "|".join(re.escape(name) for name in RATINGS)
VALUE = "|".join(re.escape(value) for value in VALUES)
# One line per rating: its name, then its previous and its current rating, or its current rating alone,
# as the first ISR prints it.
LINE = re.compile(rf"^\s*({NAME})\s*[{BULLETS}]?\s*({VALUE})(?:\s*[{BULLETS}]?\s*({VALUE}))?\s*$")
VALUE_LINE = re.compile(rf"^\s*[{BULLETS}]\s*({VALUE})\s*$")
SEQUENCE = re.compile(r"Seq\.?\s*No:\s*(\d+)")  # "Seq No: 7", or "Seq.No: 1" in the oldest ISRs
COLUMNS = ("document_id", "project_id", "isr_date", "sequence", "rating_name", "previous_rating", "current_rating",
           "pdf_page", "public_from")
ISRS = """
SELECT d.document_id, d.project_id, d.document_date, d.public_from, p.pdf_page, p.text
FROM strata.silver.documents AS d
JOIN strata.bronze.document_pages AS p ON p.document_id = d.document_id
WHERE d.document_type = :document_type
ORDER BY d.document_id, p.pdf_page
"""


def _value(text: str | None) -> str | None:
    return None if text in (None, "", "--") else text


def ratings(pages: list[tuple[int, str]]) -> tuple[int | None, list[tuple[str, str | None, str | None, int]]]:
    """An ISR's sequence number and its overall ratings, each (name, previous, current, PDF page), from
    the text of its pages in order. Each rating counts once, on the first page that prints it. A rating
    is on one line with its values, or, where the text layer sets the table out by column, the names
    come first and then each column's values: the previous ratings, then the current ones."""
    sequence, found = None, {}
    for number, text in pages:
        lines = (text or "").splitlines()
        if sequence is None and (seq := SEQUENCE.search(text or "")):
            sequence = int(seq.group(1))
        names: list[str] = []
        for at, line in enumerate(lines):
            match = LINE.match(line)
            if match and match.group(1) not in found:
                previous, current = (match.group(2), match.group(3)) if match.group(3) else (None, match.group(2))
                found[match.group(1)] = (match.group(1), _value(previous), _value(current), number)
            elif line.strip() in RATINGS:
                names.append(line.strip())
            elif names and VALUE_LINE.match(line):
                values = [VALUE_LINE.match(item).group(1) for item in lines[at:at + 2 * len(names)]
                          if VALUE_LINE.match(item)]
                if len(values) == 2 * len(names):
                    for index, name in enumerate(names):
                        found.setdefault(name, (name, _value(values[index]), _value(values[len(names) + index]), number))
                names = []
    return sequence, [found[name] for name in RATINGS if name in found]


def write(engine: Engine, projects: list[str]) -> int:
    """Rebuild strata.silver.isr_ratings for the run's projects from the ISRs silver.documents holds.
    Returns how many ratings it wrote."""
    for project_id in projects:
        engine.run("DELETE FROM strata.silver.isr_ratings WHERE project_id = :project_id", {"project_id": project_id})
    documents: dict[str, dict] = {}
    for document_id, project_id, day, public, number, text in engine.run(ISRS, {"document_type": ISR}).rows:
        if project_id not in projects:
            continue
        held = documents.setdefault(str(document_id), {"project_id": project_id, "day": day, "public": public,
                                                       "pages": []})
        held["pages"].append((int(number), text))
    rows = []
    for document_id, held in documents.items():
        sequence, found = ratings(held["pages"])
        rows += [(document_id, held["project_id"], held["day"], sequence, name, previous, current, page,
                  held["public"]) for name, previous, current, page in found]
    return engine.insert_rows("strata.silver.isr_ratings", COLUMNS, rows)
