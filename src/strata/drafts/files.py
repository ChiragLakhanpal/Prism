"""The files an export makes (ticket 35; the 35 brief, section 6.7): the Word file with every citation as a
footnote, and the evidence pack as a PDF and a CSV listing every source the draft cites, whether its
author opened it, and any reason given for keeping another source.

Strata sends nothing itself. These functions only build bytes; the draft routes keep them with the export
record and the person's browser downloads them.

- Word is a small writer for .docx files: Word's built-in styles (Normal, Heading 1, Table Grid, footnote
  text and footnote reference) in Arial 11 pt, black, with real footnotes in word/footnotes.xml, which
  python-docx cannot write. It uses only the standard library.
- The PDF is set in Open Sans on Strata's tokens with fpdf2, from the TTF files in fonts/ (SIL Open Font
  License 1.1, converted from @fontsource's files, whose licenses sit beside them).
- The CSV quotes a field that holds a comma, a quote or a line break, with CRLF line ends (RFC 4180),
  so it reads back cell for cell in a spreadsheet.

Every word comes from web/src/copy.ts through copy.json beside this file.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import zipfile
from dataclasses import dataclass
from functools import cache
from importlib import resources
from xml.sax.saxutils import escape

from strata.config import DraftKind
from strata.drafts.holds import disagreement_key

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF = "application/pdf"
CSV = "text/csv"
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
STATE_COLORS = {"ink": (24, 31, 37), "ink_heading": (1, 39, 64), "ink_muted": (75, 94, 113), "line": (218, 227, 235),
                "surface_2": (231, 237, 243)}


@cache
def words() -> dict:
    return json.loads((resources.files("strata.drafts") / "copy.json").read_text())


def _fill(template: str, **values) -> str:
    for name, value in values.items():
        template = template.replace("{" + name + "}", "" if value is None else str(value))
    return template


def iso_moment(value) -> str | None:
    """A moment as ISO text in UTC, whether it came as a datetime or as text."""
    if value is None or isinstance(value, str):
        return value
    return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


def _day(value) -> dt.date:
    return value if isinstance(value, dt.date) and not isinstance(value, dt.datetime) else \
        dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


class Say:
    """Fills the copy's templates, as DESIGN.md section 7 writes dates and the sources' lines."""

    def __call__(self, template: str, **values) -> str:
        return _fill(template, **values)

    @staticmethod
    def date(value) -> str:
        """October 9, 2026."""
        day = _day(value)
        return f"{MONTHS[day.month - 1]} {day.day}, {day.year}"

    @staticmethod
    def moment(value: str | None) -> str:
        """October 23, 2026, 14:05 UTC."""
        if not value:
            return ""
        at = dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.UTC)
        return _fill(words()["files"]["pack"]["moment"], date=Say.date(at.date()), time=f"{at:%H:%M}")

    def source(self, draft: dict, evidence_id: str) -> str:
        """The source line of a record, without "Source:": "Procurement Plan, Northern Water Works
        Development Agency, P156634, version of October 9, 2026, page 3." (the 14 brief, section 5.11)."""
        row = draft["evidence"][evidence_id]["row"]
        source = row.get("source") or {}
        date = source.get("plan_date") or source.get("document_date")
        if row.get("passage_id") and row.get("document_type"):
            # A passage a lesson rests on (ticket 36): "Implementation Completion and Results Report, P130164,
            # October 10, 2019, paragraph 54, page 23."
            locator = row.get("locator") or "paragraph"
            place = _fill(words()["passageSection" if locator == "section" else "passageParagraph"],
                          para=row.get("paragraph"), section=row.get("paragraph"))
            return _fill(words()["passageSource"], doc=row["document_type"], pid=row.get("project_id"),
                         date=self.date(row["document_date"]) if row.get("document_date") else "", place=place,
                         page=row.get("page") or row.get("pdf_page") or "")
        if source.get("table") == "strata.ops.lesson_versions":
            return _fill(words()["lessonSource"], version=source.get("version"),
                         date=self.date(source["decided_on"]) if source.get("decided_on") else "")
        if source.get("tool") == "get_lessons":
            return _fill(words()["countsSource"], date=self.date(row["public_from"]))
        # A record a project's Summary or a mission brief cites names its source by its key (ticket 37).
        # The file is about one project, which its heading names, so the line adds no project ID.
        keyed = words()["summaryRecordSources"].get(source.get("source_key") or "")
        if keyed and not source.get("implementing_agency"):
            return _fill(keyed, date=self.date(date) if date else "")
        if isinstance(source, dict) and source.get("tool"):  # a tool's summary record: the tool and its sources
            return _fill(words()["toolSource"], date=self.date(row["public_from"]))
        if source.get("implementing_agency") and source.get("pdf_page") and date:
            return _fill(words()["recordSource"], doc=source.get("document_type"), agency=source["implementing_agency"],
                         pid=source.get("project_id"), date=self.date(date), page=source["pdf_page"])
        return _fill(words()["recordSourceShort"], doc=source.get("document_type"), pid=source.get("project_id"),
                     date=self.date(date) if date else evidence_id)

    def footnote(self, draft: dict, evidence_id: str) -> str:
        """A footnote: the source line, then the public address of its document when the tool gave one."""
        url = draft["subject"].get("pdf_url")
        return f"{self.source(draft, evidence_id)} {url}" if url else self.source(draft, evidence_id)


# ── Word ─────────────────────────────────────────────────────────────────

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


@dataclass(frozen=True)
class Footnote:
    number: int


@dataclass(frozen=True)
class Spoken:
    """A run of text in a language other than the Normal style's English, which Word proofs in its locale (ticket 42):
    a writer's sentence in French carries fr-FR, and the words it quotes carry their source's locale."""

    text: str
    locale: str


def _locale(code: str | None) -> str:
    """The Word proofing locale of a language (config/languages.toml), English's for a language Strata does not
    write in or for a record, which STEP writes in English."""
    from strata import languages

    return languages.language(code).word_locale


def written_runs(sentence: dict, draft: dict) -> list:
    """A kept sentence as Word runs: the sentence in its draft's language, with each run of quoted words in the
    language of the source it quotes (a passage's own language, or English for a record). A draft in English is one
    plain run, as before."""
    from strata.agent.verifier import quoted_spans

    language = draft.get("lang") or "en"
    text = sentence["text"]
    if language == "en":
        return [text]
    quote = sentence.get("quote") or {}
    row = ((draft.get("evidence") or {}).get(quote.get("evidence_id") or "") or {}).get("row") or {}
    source = _locale(row.get("language") if quote else "en")
    runs, at = [], 0
    for start, end in quoted_spans(text):
        runs += [Spoken(text[at:start], _locale(language)), Spoken(text[start:end], source)]
        at = end
    runs.append(Spoken(text[at:], _locale(language)))
    return [run for run in runs if run.text]


class Word:
    """A .docx file built from headings, paragraphs and tables, with footnotes numbered in order."""

    def __init__(self, created: dt.datetime):
        self.title, self.created = "", created
        self.body: list[str] = []
        self.notes: list[str] = []

    def footnote(self, text: str) -> Footnote:
        self.notes.append(text)
        return Footnote(len(self.notes))

    @staticmethod
    def _runs(runs: list, bold: bool = False) -> str:
        out = []
        for run in runs:
            if isinstance(run, Footnote):
                out.append(f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>'
                           f'<w:footnoteReference w:id="{run.number}"/></w:r>')
            elif isinstance(run, Spoken):
                weight = "<w:b/>" if bold else ""
                out.append(f'<w:r><w:rPr>{weight}<w:lang w:val="{run.locale}"/></w:rPr>'
                           f'<w:t xml:space="preserve">{escape(run.text)}</w:t></w:r>')
            elif run:
                weight = "<w:rPr><w:b/></w:rPr>" if bold else ""
                out.append(f'<w:r>{weight}<w:t xml:space="preserve">{escape(run)}</w:t></w:r>')
        return "".join(out)

    def _paragraph(self, runs: list, style: str | None = None, bold: bool = False) -> str:
        properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        return f"<w:p>{properties}{self._runs(runs, bold)}</w:p>"

    def heading(self, text: str) -> None:
        """A Heading 1. The first one is the file's title, which the evidence pack repeats."""
        self.title = self.title or text
        self.body.append(self._paragraph([text], "Heading1"))

    def subheading(self, text: str) -> None:
        """A Heading 2, such as each part of a mission brief (ticket 37)."""
        self.body.append(self._paragraph([text], "Heading2"))

    def paragraph(self, *runs) -> None:
        self.body.append(self._paragraph(list(runs)))

    def bold(self, text: str) -> None:
        """A bold Normal paragraph, such as a table's title."""
        self.body.append(self._paragraph([text], bold=True))

    def table(self, header: list[str | list[str]], rows: list[list[list[list]]], widths: tuple[int, ...]) -> None:
        """A Table Grid table: a header row repeated on each page, then rows of cells, each a list of
        paragraphs, each a list of runs (text, or a footnote). A header cell is its text, or its lines, as the PPSD
        Long Form template puts "A" above "Likelihood Rating" (ticket 36)."""
        grid = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)

        def cell(paragraphs: list[list], width: int, bold: bool = False) -> str:
            inside = "".join(self._paragraph(paragraph, bold=bold) for paragraph in paragraphs) or "<w:p/>"
            return f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>{inside}</w:tc>'

        head = "".join(cell([[text]] if isinstance(text, str) else [[line] for line in text], width, bold=True)
                       for text, width in zip(header, widths, strict=True))
        body = "".join("<w:tr>" + "".join(cell(paragraphs, width) for paragraphs, width in zip(row, widths, strict=True))
                       + "</w:tr>" for row in rows)
        self.body.append(f'<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/>'
                         f'<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" '
                         f'w:noHBand="0" w:noVBand="1"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
                         f'<w:tr><w:trPr><w:tblHeader/></w:trPr>{head}</w:tr>{body}</w:tbl>')

    def _footnotes(self) -> str:
        separators = ('<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
                      '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/>'
                      '</w:r></w:p></w:footnote>')
        notes = "".join(f'<w:footnote w:id="{number}"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/></w:pPr>'
                        f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>'
                        f'<w:r><w:t xml:space="preserve"> {escape(text)}</w:t></w:r></w:p></w:footnote>'
                        for number, text in enumerate(self.notes, 1))
        return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes xmlns:w="{W}">{separators}{notes}</w:footnotes>'

    def bytes(self) -> bytes:
        stamp = self.created.astimezone(dt.UTC)
        section = ('<w:sectPr><w:footnotePr><w:numFmt w:val="decimal"/></w:footnotePr><w:pgSz w:w="11906" w:h="16838"/>'
                   '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" '
                   'w:gutter="0"/></w:sectPr>')
        parts = {
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                f'<Override PartName="/word/document.xml" ContentType="{DOCX}.main+xml"/>'
                '<Override PartName="/word/styles.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                '<Override PartName="/word/settings.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
                '<Override PartName="/word/footnotes.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>'
                '<Override PartName="/docProps/core.xml" '
                'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>'),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'officeDocument" Target="word/document.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/'
                'core-properties" Target="docProps/core.xml"/></Relationships>'),
            "word/_rels/document.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Type="{R}/styles" Target="styles.xml"/>'
                f'<Relationship Id="rId2" Type="{R}/settings" Target="settings.xml"/>'
                f'<Relationship Id="rId3" Type="{R}/footnotes" Target="footnotes.xml"/></Relationships>'),
            "word/document.xml": (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="{R}">'
                f'<w:body>{"".join(self.body)}{section}</w:body></w:document>'),
            "word/styles.xml": STYLES,
            "word/settings.xml": (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}">'
                '<w:footnotePr><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr></w:settings>'),
            "word/footnotes.xml": self._footnotes(),
            "docProps/core.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                f'<dc:title>{escape(self.title)}</dc:title><dc:creator>Strata</dc:creator>'
                f'<dcterms:created xsi:type="dcterms:W3CDTF">{stamp:%Y-%m-%dT%H:%M:%SZ}</dcterms:created>'
                '</cp:coreProperties>'),
        }
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, text in parts.items():
                info = zipfile.ZipInfo(name, date_time=stamp.timetuple()[:6])
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, text.encode("utf-8"))
        return out.getvalue()


# Word's built-in styles, in Arial 11 pt and black (DESIGN.md section 3: the recipient's Word may not have
# Open Sans, and the notes should paste into any template without restyling).
STYLES = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}">'
    '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="Arial" w:cs="Arial"/>'
    '<w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
    '<w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="240" '
    'w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="28"/>'
    '<w:szCs w:val="28"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>'
    '<w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="240" '
    'w:after="80"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="24"/>'
    '<w:szCs w:val="24"/></w:rPr></w:style>'
    '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/>'
    '<w:uiPriority w:val="1"/><w:semiHidden/></w:style>'
    '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:semiHidden/>'
    '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/>'
    '<w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/>'
    '</w:tblCellMar></w:tblPr></w:style>'
    '<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:basedOn w:val="TableNormal"/>'
    '<w:uiPriority w:val="39"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:tblPr>'
    '<w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tblBorders></w:tblPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/>'
    '<w:uiPriority w:val="99"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
    '<w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>'
    '<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/>'
    '<w:uiPriority w:val="99"/><w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>'
    '</w:styles>')


# ── The evidence pack ────────────────────────────────────────────────────

COUNT_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")


def _count(value: int) -> str:
    """A count standing alone, as the page writes it: a word from one to nine, then numerals (DESIGN.md section 7)."""
    return COUNT_WORDS[value - 1] if 1 <= value <= 9 else f"{value:,}"


def check_line(checks: dict, kind: DraftKind) -> str:
    """The check line, word for word as the page writes it (web/src/components/Checks.tsx): its counts over the
    sentences on screen, the model's part when a sentence on screen was judged (check 4), and what was not
    checked."""
    line = words()["checkLine"]

    def ratio(forms: dict, part: int, whole: int) -> str:
        return _fill(forms["one"] if whole == 1 else forms["many"], part=f"{part:,}", whole=f"{whole:,}")

    shown = checks.get("shown") or checks
    parts = [ratio(line[name], shown[name][found], shown[name]["total"])
             for name, found in (("numbers", "matched"), ("dates", "matched"), ("quotes", "found"))
             if shown[name]["total"] > 0]
    clauses = [key for key in ([] if 4 in checks["checks_run"] else ["sentences"])]
    clauses += [key for key in line["notCheckedClauses"] if key in checks["tools"]]
    clauses += [key for key in kind.not_checked if key in line["notCheckedClauses"]]
    said = [line["notCheckedClauses"][key] for key in clauses]
    joined = line["notCheckedJoin"].join(said) if len(said) <= 2 else \
        line["notCheckedComma"].join(said[:-1]) + line["notCheckedJoin"] + said[-1]
    text = f"{line['checked']} {line['clauseJoin'].join(parts) if parts else line['sourcesOnly']}{line['end']}"
    judged, proven = shown.get("judged", 0), shown.get("proven", 0)
    if judged:
        text += f" {line['judged']} {ratio(line['judgedSentences'], judged, judged)}{line['end']}"
        if proven:
            others = line["provenOthers"]
            text += " " + (others["one"] if proven == 1 else _fill(others["many"], count=_count(proven)))
    return f"{text} {line['notChecked']} {joined or line['notCheckedFallback']}{line['end']}"


def _cited_in(draft: dict) -> dict[str, str]:
    """Where a suggested PPSD row's cell is, as the pack names it: the risk, then the template's column (ticket 36)."""
    shown = draft.get("ppsd")
    if not shown:
        return {}
    headers = {column["key"]: column["header"] for column in shown["forms"][shown["form"]]["columns"]}
    return {key: f"{row['risk_label']}, {headers.get(cell, cell)}" for row in shown["rows"]
            for cell, key in row["cells"].items()}


def snapshot(draft: dict, say: Say) -> dict:
    """The evidence pack's rows: every source the draft cites, where, and whether its author opened it, and the
    reason its author gave for keeping another report on a disagreement it rests on (ticket 36)."""
    named = _cited_in(draft)
    kept = {choice["disagreement_id"]: choice for choice in draft.get("choices") or () if choice["kept"] == "other"}
    sides = {side["evidence_id"]: disagreement_key(found) for found in draft.get("disagreements") or ()
             for side in found.get("sides") or () if not side.get("leaned")}
    return {"sources": [{
        "number": entry["number"], "evidence_id": entry["evidence_id"], "source": say.source(draft, entry["evidence_id"]),
        "cited_in": [named.get(key, key) for key in entry["cited_in"]], "opened": entry["opened"],
        "last_opened_at": entry["last_opened_at"],
        "kept_another": sides.get(entry["evidence_id"]) in kept or None,
        "reason": (kept.get(sides.get(entry["evidence_id"])) or {}).get("reason")} for entry in draft["sources"]]}


def pack_csv(rows: list[dict]) -> bytes:
    """The evidence pack as a CSV. The source line's no-break space keeps "page" with its number on a page; a
    CSV has no line ends, and a search for "page 3" in a spreadsheet must find it, so it gets a plain space."""
    pack = words()["files"]["pack"]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(pack["csvColumns"])
    for row in rows:
        source = row["source"].replace("\u00a0", " ")
        writer.writerow([row["number"], row["evidence_id"], source, pack["citedJoin"].join(row["cited_in"]),
                         pack["yes"] if row["opened"] else pack["no"], Say.moment(row["last_opened_at"]),
                         pack["yes"] if row["kept_another"] else pack["no"], row["reason"] or ""])
    return out.getvalue().encode("utf-8")


FONTS = {"": "OpenSans-Regular.ttf", "B": "OpenSans-Bold.ttf", "I": "OpenSans-SemiBold.ttf"}


def pack_pdf(kind: DraftKind, draft: dict, rows: list[dict], title: str, exporter: str | None,
             exported_at: dt.datetime, say: Say) -> bytes:
    """The evidence pack in Open Sans: the title, the draft's record, the check line and every removed
    sentence, the sources table, then the footer disclaimer and the data caveat (DESIGN.md section 8)."""
    from fpdf import FPDF  # only an export needs it, so the server starts without loading it
    from fpdf.fonts import FontFace

    copy, pack = words(), words()["files"]["pack"]
    folder = resources.files("strata.drafts") / "fonts"
    pdf = FPDF(format="A4", unit="pt")
    pdf.set_creator("Strata")
    pdf.set_title(f"{pack['title']}: {title}")
    pdf.set_creation_date(exported_at.astimezone(dt.UTC))
    for style, name in FONTS.items():
        pdf.add_font("OpenSans", style, str(folder / name))
    pdf.add_font("RobotoMono", "", str(folder / "RobotoMono-Regular.ttf"))
    pdf.set_margins(56, 56, 56)
    pdf.set_auto_page_break(True, 56)
    pdf.add_page()

    def text(words_: str, size: float = 11, style: str = "", color: str = "ink", gap: float = 6):
        pdf.set_font("OpenSans", style, size)
        pdf.set_text_color(*STATE_COLORS[color])
        pdf.multi_cell(0, size * 1.45, words_, align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(gap)

    text(pack["title"], 24, "B", "ink_heading", 4)
    text(title, 14, "B", "ink_heading", 12)
    # "Draft ID draft-0001", with the ID in Roboto Mono, as DESIGN.md section 3 sets every ID.
    label, _, after = pack["draftId"].partition("{id}")
    pdf.set_text_color(*STATE_COLORS["ink"])
    pdf.set_font("OpenSans", "", 11)
    pdf.write(11 * 1.45, label)
    pdf.set_font("RobotoMono", "", 10.5)
    pdf.write(11 * 1.45, draft["draft_id"])
    pdf.set_font("OpenSans", "", 11)
    pdf.write(11 * 1.45, after)
    pdf.ln(11 * 1.45 + 2)
    checked = draft["checked"] or {}
    export_line = _fill(pack["exported"], author=exporter or "", date=say.date(exported_at.date()))
    record = [_fill(pack["drafted"], date=say.date(draft["created_at"]), author=draft["author"]["name"] or ""),
              _fill(pack["checked"], author=checked.get("by") or "", date=say.date(checked["at"])) if checked else None,
              export_line,
              _fill(pack["opened"], author=draft["author"]["name"] or "", opened=draft["opened"]["count"],
                    total=draft["opened"]["of"])]
    for line in record:
        if line:
            text(line, 11, gap=2)
    pdf.ln(10)
    text(check_line(draft["checks"], kind), 10, color="ink", gap=8)
    text(pack["removedTitle"], 13, "B", "ink_heading", 4)
    reasons = {**copy["removed"]["reasons"], **copy["removedReasons"].get(kind.key, {})}
    if not draft["removed"]:
        text(pack["removedNone"], 10, gap=8)
    for item in draft["removed"]:
        reason = reasons.get(item["reason"], copy["removed"]["unknownReason"])["item"]
        text(_fill(pack["removedItem"], sentence=item["sentence"], reason=reason), 10, gap=4)
    pdf.ln(8)
    text(pack["sourcesTitle"], 13, "B", "ink_heading", 6)
    pdf.set_font("OpenSans", "", 9)
    pdf.set_text_color(*STATE_COLORS["ink"])
    pdf.set_draw_color(*STATE_COLORS["line"])
    heading = FontFace(emphasis="BOLD", color=STATE_COLORS["ink_heading"], fill_color=STATE_COLORS["surface_2"])
    # STEP references in Roboto Mono, as every ID Strata writes (DESIGN.md section 3), in a column wide
    # enough that a 22-character reference keeps to one line. Number needs little room; the reason a
    # source was kept needs more.
    mono = FontFace(family="RobotoMono", size_pt=8)
    with pdf.table(col_widths=(6, 33, 24, 9, 14, 14), headings_style=heading, line_height=13,
                   text_align="LEFT", padding=4) as table:
        header = table.row()
        for name in pack["columns"]:
            header.cell(name)
        for row in rows:
            cells = table.row()
            cells.cell(str(row["number"]))
            cells.cell(row["source"])
            cells.cell(pack["citedJoin"].join(row["cited_in"]), style=mono)
            for value in (pack["yes"] if row["opened"] else pack["no"], Say.moment(row["last_opened_at"]),
                          row["reason"] or ""):
                cells.cell(value)
    saves = draft.get("field_history") or []
    if saves:
        # Suggested PPSD rows (ticket 36): who set each owner and rating, and when, one line per save, so the pack
        # records that people set them and Strata did not.
        pdf.ln(16)
        text(pack["fieldsTitle"], 13, "B", "ink_heading", 6)
        pdf.set_font("OpenSans", "", 9)
        pdf.set_text_color(*STATE_COLORS["ink"])
        labels = {row["row_key"]: row["risk_label"] for row in (draft.get("ppsd") or {}).get("rows", [])}
        headers = {column["key"]: column["header"] for form in (draft.get("ppsd") or {}).get("forms", {}).values()
                   for column in form["columns"]}
        with pdf.table(col_widths=(26, 20, 22, 16, 16), headings_style=heading, line_height=13, text_align="LEFT",
                       padding=4) as table:
            header = table.row()
            for name in pack["fieldsColumns"]:
                header.cell(name)
            for save in saves:
                cells = table.row()
                cells.cell(labels.get(save["row_key"], ""))
                cells.cell(pack["fieldsForm"] if save["field"] == "form" else headers.get(save["field"], save["field"]))
                cells.cell(save["value"] or pack["fieldsRemoved"])
                cells.cell(save["set_by_name"] or "")
                cells.cell(Say.moment(iso_moment(save["set_at"])))
    pdf.ln(16)
    text(copy["footer"], 9, color="ink_muted", gap=2)
    text(pack["dataCaveat"], 9, color="ink_muted", gap=0)
    return bytes(pdf.output())


@dataclass(frozen=True)
class Made:
    files: list[tuple[str, str, bytes]]
    footnotes: int
    snapshot: dict


def names(kind: DraftKind, subject: dict) -> dict[str, str]:
    stem = _fill(kind.files, **subject)
    return {"word": f"{stem}.docx", "pdf": f"{stem}-evidence-pack.pdf", "csv": f"{stem}-evidence-pack.csv"}


def make(kind: DraftKind, draft: dict, exporter: str | None, exported_at: dt.datetime) -> Made:
    """The Word file and the evidence pack's PDF and CSV for one export of a draft, as its author sees it."""
    from strata.drafts.runtime import function

    say = Say()
    document = Word(exported_at)
    function(kind.word)(document, draft, words(), say)  # the kind lays out its file, its heading first
    heading = document.title
    taken = snapshot(draft, say)
    named = names(kind, draft["subject"])
    files = [(named["word"], DOCX, document.bytes()),
             (named["pdf"], PDF, pack_pdf(kind, draft, taken["sources"], heading, exporter, exported_at, say)),
             (named["csv"], CSV, pack_csv(taken["sources"]))]
    return Made(files, len(document.notes), taken)
