"""Each document type's template: how Route A finds its headings and its numbered paragraphs.

This is the one place a document type is taught to the reader (CLAUDE.md rule 9): one Template per
type in TEMPLATES, keyed by the type's name in the documents API (its docty), in the order the reader
takes documents. Teaching the reader a new type is one entry here. A type's report in another
language, whose headings are in that language, has its own template in LANGUAGES, keyed by the type
and the language's ISO 639-1 code; template() picks it.

A template says:

- short_name   the name a passage's header uses, such as ICR (docs/PLAN.md section 5)
- stratum      the stratum its passages belong to (GLOSSARY.md): Why for the narrative documents that
               explain design choices and outcomes, How for the operational ones. The evidence card's
               eyebrow names it.
- body_start   the heading that starts the body. The pages before it hold the cover, the
               abbreviations and the contents, and give no passages. In a report with a data sheet,
               the pages from data_sheet to the body hold its tables, which go to Route B.
- levels       the heading levels, outermost first. Each is a pattern whose first group is the
               heading's id, such as III or B, and a section path joins the ids: III.B.
- annex        a heading that starts an annex. Inside one, the paragraphs are numbered from 1 again,
               and the levels nest under it: Annex 2.A.
- paragraph    the start of a numbered paragraph, whose first group is its number, such as 54. A
               report numbers its paragraphs one after another, so a line that does not follow the
               last number, or that runs into columns of a table, is not a new paragraph. IEG's PPAR
               numbers them within each chapter, 2.10, and starts each chapter again at 1.
- items        for a report whose numbered sections are its paragraphs, such as IEG's ICR Review
               (6. Outcome, then a. Outcome Rating), the lettered items inside each section. The
               paragraph is the section's number with the item's letter, 10.b, as IEG cites it.
- risk_table   for a PAD, the title of its risk table (the ORAF before 2014, the SORT after). Its pages,
               up to the next annex, go to Route B, whose rows each name a risk and its rating.
- headings     for a report that numbers no paragraph, such as an ISR, its template's headings word
               for word, and in levels a pattern for the numbered headings of its later template.
               Each section's text is then one paragraph, which Prism numbers.

The patterns read lines of the text the World Bank publishes (src/strata/reader/passages.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from strata.reader.layout import RISK_TITLE

ROMAN = r"(?:I|II|III|IV|V|VI|VII|VIII|IX|X)"


@dataclass(frozen=True)
class Template:
    document_type: str
    short_name: str
    stratum: str
    body_start: re.Pattern
    levels: tuple[re.Pattern, ...] = ()
    annex: re.Pattern | None = None
    paragraph: re.Pattern | None = None
    items: re.Pattern | None = None
    headings: tuple[str, ...] = ()
    data_sheet: re.Pattern | None = None
    risk_table: re.Pattern | None = None
    minor_headings: bool = False  # a short line on its own ends a numbered paragraph, as "Quality at Entry" does
    language: str = "en"  # the language of the headings it reads, as an ISO 639-1 code
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
    stratum="Why",
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
    stratum="Why",
    body_start=re.compile(r"^\s*(1)\.\s+Project Data\s*$"),
    paragraph=re.compile(r"^\s*(\d{1,2})\.\s+([A-Z][A-Za-z,&/()' -]*[A-Za-z)?])\s*$"),
    items=re.compile(r"^\s*([a-h])\.\s*([A-Z].*)$"),
)

# A PAD's body starts at "I. STRATEGIC CONTEXT", in capitals since about 2014 and in title case before
# ("I. Strategic Context", as the P130164 PAD of 2013 prints it).
PAD = Template(
    document_type="Project Appraisal Document",
    short_name="PAD",
    stratum="Why",
    body_start=_heading("I", TITLE_WORDS),
    levels=(_heading(ROMAN, TITLE_WORDS), _heading("[A-H]", TITLE_WORDS)),
    annex=re.compile(r"^\s*Annex\s+(\d+):\s+\S.*$"),
    paragraph=NUMBERED,
    data_sheet=re.compile(r"^\s*PAD DATA SHEET\s*$"),
    risk_table=RISK_TITLE,
    minor_headings=True,
)

# An ISR from before 2020 names its sections; a later one numbers them (4.1 Implementation Status and
# Key Decisions), and its section path is that number.
ISR = Template(
    document_type="Implementation Status and Results Report",
    short_name="ISR",
    stratum="How",
    body_start=re.compile(r"^\s*(Key Dates|1\.\s+OBJECTIVE)\s*$"),
    headings=("Key Dates", "Project Development Objectives", "Components", "Overall Ratings",
              "Implementation Status and Key Decisions", "Risks", "Results",
              "Project Development Objective Indicators", "Intermediate Results Indicators",
              "Data on Financial Performance", "Disbursements", "Key Decisions Regarding Implementation",
              "Restructuring History", "Related Project(s)"),
    levels=(re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2})?)\.?\s+([A-Z][A-Za-z&/(),' -]*[A-Za-z)])\s*$"),),
)

# A completion report written in French (the P127203 ICR of July 29, 2021): the same parts as the ICR,
# with French headings in capitals, accented letters included ("I. CONTEXTE DU PROJET ET OBJECTIFS DE
# DÉVELOPPEMENT", "A. CONTEXTE DE L’ÉVALUATION"), "ANNEXE" for an annex and "FICHE DE DONNÉES" for its
# data sheet.
UPPER_FR = r"[A-ZÀ-ÖØ-ÞŒ][A-ZÀ-ÖØ-ÞŒ0-9 ,&/()'’:\-]*[A-ZÀ-ÖØ-ÞŒ)]"
ICR_FR = Template(
    document_type="Implementation Completion and Results Report",
    short_name="ICR",
    stratum="Why",
    body_start=_heading("I", UPPER_FR),
    levels=(_heading(ROMAN, UPPER_FR), _heading("[A-H]", UPPER_FR)),
    annex=re.compile(r"^\s*ANNEXE\s+(\d+)\s*[.:]\s+\S.*$"),
    paragraph=NUMBERED,
    data_sheet=re.compile(r"^\s*FICHE DE DONNÉES\s*$"),
    minor_headings=True,
    abbreviations=("p. ex.", "c.-à-d.", "M.", "MM.", "Mme", "art.", "env.", "n°", "No.", "etc.", "cf.", "p.", "vol."),
    language="fr",
)

# A Project Paper, here a restructuring paper (P156634's of May 24, 2021): "I. PROJECT STATUS AND RATIONALE
# FOR RESTRUCTURING", then "A.      Project status", with its paragraphs numbered 1, 2, 3 through the
# paper. Its results framework tables come after, set out in columns, and give no paragraphs.
PROJECT_PAPER = Template(
    document_type="Project Paper",
    short_name="Project Paper",
    stratum="Why",
    body_start=_heading("I", TITLE_WORDS),
    levels=(_heading(ROMAN, TITLE_WORDS), _heading("[A-H]", TITLE_WORDS)),
    annex=re.compile(r"^\s*ANNEX\s+(\d+)[.:]?\s+\S.*$"),
    paragraph=NUMBERED,
    minor_headings=True,
)

# IEG's Project Performance Assessment Report numbers its chapters ("2. Results, What Worked, What Didn't
# Work, and Why?") and its paragraphs within each chapter ("2.1     The project results ..."), and closes
# with lettered appendixes. No fixture project lists one yet, so a test reads a hand-written one.
CHAPTER = r"([A-Z][^.…]*[A-Za-z)?])"
PPAR = Template(
    document_type="Project Performance Assessment Report",
    short_name="PPAR",
    stratum="Why",
    body_start=re.compile(rf"^\s*(1)\.\s+{CHAPTER}\s*$"),
    levels=(re.compile(rf"^\s*(\d{{1,2}})\.\s+{CHAPTER}\s*$"),),
    annex=re.compile(r"^\s*Appendix\s+([A-Z])\.?\s+\S.*$"),
    paragraph=re.compile(r"^\s*(\d{1,2}\.\d{1,2})\s+(\S.*)$"),
    minor_headings=True,
)

# The types the reader reads, in the order it takes them: the evaluations first, then the
# appraisal, the restructurings and the status reports. A Country Partnership Framework is listed by
# country, not by project, so the reader, which lists a project's documents, does not take it yet.
TEMPLATES: dict[str, Template] = {template.document_type: template
                                  for template in (PPAR, ICR_REVIEW, ICR, PAD, PROJECT_PAPER, ISR)}
# The reports in another language, by their type and language.
LANGUAGES: dict[tuple[str, str], Template] = {(t.document_type, t.language): t for t in (ICR_FR,)}


def template(document_type: str, language: str = "en") -> Template:
    """The template that reads a report of this type in this language: its own when LANGUAGES has one,
    else the type's."""
    return LANGUAGES.get((document_type, language), TEMPLATES[document_type])


def template_for(name: str) -> Template | None:
    """A template by the type's full name or its short name, in any case."""
    wanted = " ".join(name.split()).lower()
    return next((t for t in TEMPLATES.values() if wanted in (t.document_type.lower(), t.short_name.lower())), None)
