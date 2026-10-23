"""Each document type's template: how Route A finds its headings and its numbered paragraphs.

This is the one place a document type is taught to the reader (CLAUDE.md rule 9): one Template per
type in TEMPLATES, keyed by the type's name in the documents API (its docty), in the order the reader
takes documents. Teaching the reader a new type is one entry here.

A template says:

- short_name   the name a passage's header uses, such as ICR (docs/PLAN.md section 5)
- body_start   the heading that starts the body. The pages before it hold the cover, the
               abbreviations and the contents, and give no passages. In a report with a data sheet,
               the pages from data_sheet to the body hold its tables, which go to Route B.
- levels       the heading levels, outermost first. Each is a pattern whose first group is the
               heading's id, such as III or B, and a section path joins the ids: III.B.
- annex        a heading that starts an annex. Inside one, the paragraphs are numbered from 1 again,
               and the levels nest under it: Annex 2.A.
- paragraph    the start of a numbered paragraph, whose first group is its number, such as 54. A
               report numbers its paragraphs one after another, so a line that does not follow the
               last number, or that runs into columns of a table, is not a new paragraph.
- items        for a report whose numbered sections are its paragraphs, such as IEG's ICR Review
               (6. Outcome, then a. Outcome Rating), the lettered items inside each section. The
               paragraph is the section's number with the item's letter, 10.b, as IEG cites it.
- headings     for a report that numbers no paragraph, such as an ISR, its template's headings word
               for word, and in levels a pattern for the numbered headings of its later template.
               Each section's text is then one paragraph, which Strata numbers.

The patterns read lines of the text the World Bank publishes (src/strata/reader/passages.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ROMAN = r"(?:I|II|III|IV|V|VI|VII|VIII|IX|X)"


@dataclass(frozen=True)
class Template:
    document_type: str
    short_name: str
    body_start: re.Pattern
    levels: tuple[re.Pattern, ...] = ()
    annex: re.Pattern | None = None
    paragraph: re.Pattern | None = None
    items: re.Pattern | None = None
    headings: tuple[str, ...] = ()
    data_sheet: re.Pattern | None = None
    minor_headings: bool = False  # a short line on its own ends a numbered paragraph, as "Quality at Entry" does
    abbreviations: tuple[str, ...] = field(default=("e.g.", "i.e.", "No.", "Nos.", "para.", "paras.", "Mr.", "Ms.",
                                                    "Dr.", "Rs.", "St.", "vs.", "etc.", "cf.", "Fig.", "approx."))

    @property
    def numbered(self) -> bool:
        """Whether the report numbers its paragraphs, so a citation can name the report's own number."""
        return self.paragraph is not None


# A heading of a report's body: an id, a full stop, then words in capitals or in title case, with no
# dotted leader to a page number, which marks a line of the contents.
def _heading(ids: str, words: str) -> re.Pattern:
    return re.compile(rf"^\s*({ids})\.\s+({words})\s*$")


UPPER_WORDS = r"[A-Z][A-Z0-9 ,&/()'’:-]*[A-Z)]"
TITLE_WORDS = r"[A-Z][A-Za-z0-9 ,&/()'’:-]*[A-Za-z)]"
NUMBERED = re.compile(r"^\s*(\d{1,3})\.\s+(\S.*)$")

ICR = Template(
    document_type="Implementation Completion and Results Report",
    short_name="ICR",
    body_start=_heading("I", UPPER_WORDS),
    levels=(_heading(ROMAN, UPPER_WORDS), _heading("[A-H]", UPPER_WORDS)),
    annex=re.compile(r"^\s*ANNEX\s+(\d+)\.\s+\S.*$"),
    paragraph=NUMBERED,
    data_sheet=re.compile(r"^\s*DATA SHEET\s*$"),
    minor_headings=True,
)

ICR_REVIEW = Template(
    document_type="Implementation Completion Report Review",
    short_name="ICR Review",
    body_start=re.compile(r"^\s*(1)\.\s+Project Data\s*$"),
    paragraph=re.compile(r"^\s*(\d{1,2})\.\s+([A-Z][A-Za-z,&/()' -]*[A-Za-z)?])\s*$"),
    items=re.compile(r"^\s*([a-h])\.\s*([A-Z].*)$"),
)

PAD = Template(
    document_type="Project Appraisal Document",
    short_name="PAD",
    body_start=_heading("I", UPPER_WORDS),
    levels=(_heading(ROMAN, UPPER_WORDS), _heading("[A-H]", TITLE_WORDS)),
    annex=re.compile(r"^\s*Annex\s+(\d+):\s+\S.*$"),
    paragraph=NUMBERED,
    data_sheet=re.compile(r"^\s*PAD DATA SHEET\s*$"),
    minor_headings=True,
)

# An ISR from before 2020 names its sections; a later one numbers them (4.1 Implementation Status and
# Key Decisions), and its section path is that number.
ISR = Template(
    document_type="Implementation Status and Results Report",
    short_name="ISR",
    body_start=re.compile(r"^\s*(Key Dates|1\.\s+OBJECTIVE)\s*$"),
    headings=("Key Dates", "Project Development Objectives", "Components", "Overall Ratings",
              "Implementation Status and Key Decisions", "Risks", "Results",
              "Project Development Objective Indicators", "Intermediate Results Indicators",
              "Data on Financial Performance", "Disbursements", "Key Decisions Regarding Implementation",
              "Restructuring History", "Related Project(s)"),
    levels=(re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2})?)\.?\s+([A-Z][A-Za-z&/(),' -]*[A-Za-z)])\s*$"),),
)

# The types the reader reads, in the order it takes them: the evaluations first, then the
# appraisal, then the status reports.
TEMPLATES: dict[str, Template] = {template.document_type: template for template in (ICR_REVIEW, ICR, PAD, ISR)}


def template_for(name: str) -> Template | None:
    """A template by the type's full name or its short name, in any case."""
    wanted = " ".join(name.split()).lower()
    return next((t for t in TEMPLATES.values() if wanted in (t.document_type.lower(), t.short_name.lower())), None)
