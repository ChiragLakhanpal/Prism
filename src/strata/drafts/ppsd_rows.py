"""The suggest-PPSD-rows workflow: suggested risk rows for the borrower's PPSD (ticket 36).

A World Bank procurement specialist selects risks in section 3 of the package workspace, "Procurement risks and
what helped", and "Suggest {n} PPSD risk rows" starts this workflow. The draft runtime (runtime.py) calls its steps
and runs the writer agent and the verifier between them, so no kind of draft can skip the checks:

1. read() runs the risk-table builder (src/strata/packages/risks.py) as the viewer, as of today, with the package's
   criteria, and keeps the rows the person selected that are still in the table, in the builder's order. A selected
   risk that dropped out of the table is not drafted (the 30 brief, decision 4). The route reads the selection
   itself (src/strata/server/drafts.py); the address never carries risk keys. It also compares the whole package's
   cost estimate with the PPSD guidance's Table I (table_i), which decides whether the Long Form is offered.
2. message() is the writer's one message, data only: each row's risk, its count of comparable completion reports
   (k of m, from get_lessons' summary), its lesson and the passages the lesson rests on. The writer fills two cells
   per row, Risk Description and Description of mitigation (config/ppsd_templates.toml's columns with filled_by =
   "strata"); its answer has no place for an owner, a rating, a reference or an actual date, and anything else it
   writes is dropped when it is read (runtime.parse_notes keeps only claims or a refusal per cell).
3. items() gives two items per row, one per cell, each with the records its sentences may cite: the Risk
   Description the counts summary, the mitigation the lesson and its passages. finish() puts the cells back into
   rows and leaves out a row whose two cells both failed; a row with one failed cell stays, and that cell is empty.

Footnotes: each kept sentence has one citation marker and becomes one Word footnote, whose text footnotes() builds
once, here, from the tools' stored values: "Seen in {k} of {m} comparable completion reports." for a count, and the
source pills of the passages a lesson rests on for a mitigation, "ICR P130164 ¶54, page 23; ICR Review 10.b." The
page shows the same string as its "In Word:" line, so the two cannot differ. word() lays out the Word file in the
template's columns for the form the person chose.

table_i() compares a package's cost estimate with the PPSD guidance's Table I (config/thresholds.toml's
[ppsd_table_i]) to say whether the Long Form may be offered. missing() counts what the owners and ratings holds wait
for (src/strata/drafts/holds.py).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from decimal import Decimal

from strata.config import Thresholds, load_ppsd_templates, load_thresholds
from strata.drafts.files import written_runs
from strata.dbx import Viewer
from strata.lakehouse.engine import Engine

TOOL = "get_lessons"
TOOLS = ("find_comparables", "get_lessons")  # the tools the check line names: the builder's
KEY = "cell_key"  # what names each note in the writer's answer: a row's risk key and its cell
VIEW_KEY = "ppsd"  # where the draft page finds what view() adds
CELLS = ("risk_description", "mitigation")  # the cells Strata writes, by their registry keys
FORM = ("", "form")  # the field that holds the form the person chose


class NotWritable(Exception):
    """There is nothing to draft from: no such package, no risk selected that is still in the table."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ── Table I ──────────────────────────────────────────────────────────────

def _money(value: Decimal | None) -> str | None:
    return None if value is None else f"{Decimal(value):.2f}"


def table_i(limits: Thresholds, category: str | None, amount: Decimal | None) -> dict:
    """Whether the package's whole cost estimate is at or above Table I's threshold for its category, at the
    risk level the thresholds file offers the Long Form from. The amount and the threshold come back as text with
    two decimals, as tools write amounts; with no cost estimate or no category, nothing is compared."""
    level = limits.value("ppsd_table_i.offer_long_form_at")
    rows = limits.value("ppsd_table_i.row")
    if amount is None or category not in rows:
        return {"applies": False, "amount": _money(amount), "threshold": None, "currency": "USD", "category": category,
                "risk_level": level}
    threshold = Decimal(limits.value(f"ppsd_table_i.from_usd.{rows[category]}")[level])
    return {"applies": Decimal(amount) >= threshold, "amount": _money(amount), "threshold": _money(threshold),
            "currency": "USD", "category": category, "risk_level": level}


# ── Reading what the rows are written from ───────────────────────────────

@dataclass(frozen=True)
class Facts:
    """What the rows are written from: the package, the builder's section with every row its tools returned, the
    selected rows still in the table, and the Table I result."""

    request: dict
    package: dict
    table: object  # strata.packages.risks.RiskTable
    selected: list[dict]
    table_i: dict


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-") or "package"


def _package(engine: Engine, request: dict, today: dt.date) -> dict:
    """The package as the draft names it. A package from a STEP row is read from its plan row; a package planned
    from a sentence comes from the route, which read it from the person's own saved package."""
    given = request.get("package") or {}
    if given.get("step_reference") and not given.get("package_id"):
        from strata.tools.find_comparables import read_package

        found = read_package(engine, given["step_reference"], today)
        if found is None:
            raise NotWritable("no_package")
        return {"package_id": None, "step_reference": found["step_reference"], "title": found["description"],
                "project_id": found.get("project_id"), "project_name": found.get("project_name"),
                "category": found.get("category"), "country": found.get("country_name"),
                "estimated_amount_usd": found.get("estimated_amount_usd")}
    if not given.get("package_id"):
        raise NotWritable("no_package")
    return {"package_id": given["package_id"], "step_reference": given.get("step_reference"),
            "title": given.get("title"), "project_id": given.get("project_id"),
            "project_name": given.get("project_name"), "category": given.get("category"),
            "country": given.get("country"), "estimated_amount_usd": given.get("estimated_amount_usd")}


def read(engine: Engine, viewer: Viewer, request: dict, today: dt.date) -> Facts:
    from strata.packages import risks

    package = _package(engine, request, today)
    criteria = request.get("criteria")
    if package["step_reference"] and not package["package_id"]:
        criteria = {**(criteria or {}), "step_reference": package["step_reference"]}
    selected = list(request.get("selected") or ())
    table = risks.build(engine, viewer, as_of=today, criteria=criteria, words=request.get("words"), view="staff",
                        selected=selected, missing=request.get("missing") or ())
    rows = [row for row in table.payload["rows"] if row["risk_key"] in selected]
    if not rows:
        raise NotWritable("no_selected_risks")
    amount = package["estimated_amount_usd"]
    found = table_i(load_thresholds(), package["category"], Decimal(str(amount)) if amount not in (None, "") else None)
    return Facts(request, package, table, rows, found)


def read_done(facts: Facts) -> dict:
    """What the read step says it read: how many selected risks, with their lessons."""
    return {"selected": len(facts.selected)}


def question(facts: Facts) -> str:
    return f"Write suggested PPSD risk rows for {facts.package['title']}."


def _cell(row: dict, cell: str) -> str:
    return f"{row['risk_key']}/{cell}"


def _cites(row: dict, cell: str, counts_id: str) -> list[str]:
    if cell == "risk_description":
        return [counts_id]
    return [row["lesson"]["evidence_id"], *(source["evidence_id"] for source in row["sources"])]


def message(facts: Facts, language: str = "en") -> dict:
    payload = facts.table.payload
    counts_id = payload["counts_evidence_id"]
    short = load_ppsd_templates().forms["short"]
    headers = {column.key: column.header for column in short.columns}
    return {"task": "ppsd_rows", "language": language,
            "package": {key: facts.package[key] for key in ("title", "step_reference", "category", "country")},
            "reports_read": payload["m"], "counts_evidence_id": counts_id,
            "rows": [{"risk_key": row["risk_key"], "risk_label": row["risk_label"], "reports_raised": row["k"],
                      "lesson": {"evidence_id": row["lesson"]["evidence_id"], "text": row["lesson"]["text"]},
                      "sources": [{key: source[key] for key in ("evidence_id", "doc_short", "pcode", "locator", "page",
                                                                "quote")} for source in row["sources"]],
                      "cells": [{"cell_key": _cell(row, cell), "column": headers[cell],
                                 "evidence_ids": _cites(row, cell, counts_id)} for cell in CELLS]}
                     for row in facts.selected]}


def written_rows(cells: list[str]) -> int:
    """How many rows the writer wrote a cell of, for the writing step's "I wrote two rows." Only the cells Strata
    writes count: a cell key the message never named is dropped."""
    return len({key.split("/", 1)[0] for key in cells if key.split("/", 1)[-1] in CELLS})


def cited_rows(facts: Facts) -> list[tuple[dict, str]]:
    """Every record the builder's tools returned, with the tool that returned it."""
    held = facts.table.facts
    return [(row, held.tool(evidence_id)) for evidence_id, row in held.items()]


def items(facts: Facts) -> list[dict]:
    """Two items per row, one per cell Strata writes, each with the records its sentences may cite."""
    counts_id = facts.table.payload["counts_evidence_id"]
    found = []
    for row in facts.selected:
        for cell in CELLS:
            cites = _cites(row, cell, counts_id)
            found.append({"key": _cell(row, cell), "evidence_id": cites[0], "evidence_ids": cites,
                          "description": row["risk_label"], "mark": None,
                          "extra": {"row_key": row["risk_key"], "cell": cell}})
    return found


def subject(facts: Facts) -> dict:
    package = facts.package
    return {"package_id": package["package_id"], "step_reference": package["step_reference"],
            "package_title": package["title"], "package_slug": _slug(package["title"] or ""),
            "project_id": package["project_id"], "project_name": package["project_name"],
            "category": package["category"], "estimated_amount_usd": package["estimated_amount_usd"],
            "as_of": facts.table.payload["as_of"], "created_date": facts.table.payload["as_of"],
            "agency_id": None, "implementing_agency": None, "plan_date": None, "signal": None}


def subject_key(facts: Facts) -> str:
    """What the draft is about, for the notice that names a draft already started on the same package."""
    return facts.package["package_id"] or facts.package["step_reference"]


def finish(content: dict, facts: Facts) -> dict:
    """The cells back in their rows, in the builder's order. A row whose two cells both failed is left out, and its
    sentences stay in the removed box; a row with one failed cell stays, with that cell empty."""
    payload = facts.table.payload
    notes = {note["key"]: note for note in content["notes"]}
    rows, kept_notes = [], []
    for row in facts.selected:
        cells = {cell: notes[_cell(row, cell)] for cell in CELLS}
        if not any(note["state"] == "written" for note in cells.values()):
            continue
        kept_notes += cells.values()
        rows.append({"row_key": row["risk_key"], "risk_key": row["risk_key"], "risk_label": row["risk_label"],
                     "k": row["k"], "m": payload["m"], "counts_evidence_id": payload["counts_evidence_id"],
                     "lesson": {key: row["lesson"][key] for key in ("id", "evidence_id", "version", "decided_on")},
                     "sources": [{key: source[key] for key in ("evidence_id", "doc_short", "doc_type", "pcode",
                                                               "locator", "page", "date")} for source in row["sources"]],
                     "cells": {cell: _cell(row, cell) for cell in CELLS}})
    content["notes"] = kept_notes
    content["ppsd"] = {"form": load_ppsd_templates().default_form, "table_i": facts.table_i,
                       "selected": len(facts.selected), "rows": rows}
    return content


# ── What the page and the Word file show ─────────────────────────────────

def form_of(content: dict, fields: dict) -> str:
    """The form the person chose, or the form the draft was written in."""
    return fields.get(FORM) or content["ppsd"]["form"]


def pill(source: dict, with_project: bool, words: dict) -> str:
    """A passage's short name, as the source pill writes it: "ICR P130164 ¶54, page 23", or "ICR Review 10.b"
    for a later source from the same project. A paragraph's page follows it; a section stands alone."""
    pills, footnote = words["pill"], words["files"]["word"]["ppsd_rows"]["footnote"]
    locator = source["locator"]
    if locator["kind"] == "paragraph":
        place = _fill(pills["pillParagraph"], para=locator["text"])
        if source.get("page"):
            place += _fill(footnote["page"], page=source["page"])
    else:
        place = locator["text"]
    template = pills["pill"] if with_project else pills["pillNoProject"]
    return _fill(template, doc=source["doc_short"], pcode=source["pcode"], locator=place)


def _fill(template: str, **values) -> str:
    for name, value in values.items():
        template = template.replace("{" + name + "}", "" if value is None else str(value))
    return template


def footnote_text(row: dict, evidence_ids: list[str], words: dict) -> str:
    """One footnote's text, from the row's stored tool values: a count ("Seen in 1 of 1 comparable completion
    reports."), or the passages the lesson rests on, joined, each later one from the same project without its P-code
    ("ICR P130164 ¶54, page 23; ICR Review 10.b.")."""
    footnote = words["files"]["word"]["ppsd_rows"]["footnote"]
    if row["counts_evidence_id"] in evidence_ids:
        return _fill(footnote["count"], k=row["k"], m=row["m"])
    cited = [source for source in row["sources"] if source["evidence_id"] in evidence_ids] or row["sources"]
    seen, parts = set(), []
    for source in cited:
        parts.append(pill(source, source["pcode"] not in seen, words))
        seen.add(source["pcode"])
    return footnote["join"].join(parts) + footnote["end"]


def footnotes(content: dict, words: dict) -> list[dict]:
    """Every footnote the draft makes, one per kept sentence, in reading order: row by row, the Risk Description's
    then the mitigation's. Each has its number, the sources its marker carries, its text and where it is cited."""
    notes = {note["key"]: note for note in content["notes"]}
    found = []
    for row in content["ppsd"]["rows"]:
        for cell in CELLS:
            note = notes.get(row["cells"][cell])
            for index, sentence in enumerate((note or {}).get("sentences") or ()):
                found.append({"number": len(found) + 1, "evidence_ids": list(sentence["evidence_ids"]),
                              "text": footnote_text(row, sentence["evidence_ids"], words), "row_key": row["row_key"],
                              "cell": cell, "sentence": sentence["index"], "position": index})
    return found


def view(content: dict, fields: dict, words: dict) -> dict:
    """What the draft page adds for suggested PPSD rows: the form, its columns, the fields people set and the
    counts the progress line states, and the footnotes."""
    templates = load_ppsd_templates()
    form = templates.forms[form_of(content, fields)]
    rows = [row for row in content["ppsd"]["rows"] if not row.get("removed")]
    people = [column for column in form.columns if column.filled_by == "people"]
    rated = [column.key for column in form.columns if column.hold == "ratings"]
    owners_set = sum(1 for row in rows if fields.get((row["row_key"], "risk_owner")))
    rows_rated = sum(1 for row in rows if rated and all(fields.get((row["row_key"], key)) for key in rated))
    return {"form": form.key,
            "forms": {key: {"name": shape.name, "columns": [{"key": column.key, "header": column.header,
                                                              "letter": column.letter, "filled_by": column.filled_by,
                                                              "control": column.control, "hold": column.hold,
                                                              "max_length": column.max_length}
                                                             for column in shape.columns]}
                      for key, shape in templates.forms.items()},
            "ratings": [{"value": level.value, "label": level.label, "short": level.short} for level in templates.ratings],
            "score": {"definition": templates.score.definition, "minimum": templates.score.minimum,
                      "maximum": templates.score.maximum},
            "stages": list(templates.stages),
            "table_i": content["ppsd"]["table_i"], "selected": content["ppsd"]["selected"],
            "rows": rows,
            "values": [{"row_key": row["row_key"], "field": column.key, "value": fields.get((row["row_key"], column.key))}
                       for row in rows for column in people],
            "counts": {"total": len(rows), "owners_set": owners_set, "rated": rows_rated}}


def missing(draft, hold: str):
    """How many rows wait for a person on the owners or ratings hold, and the first field's anchor. Ratings hold
    only in the Long Form. A removed row (ticket 39) is not counted."""
    from strata.drafts.holds import Held

    content = draft.content
    if "ppsd" not in content:
        return None
    templates = load_ppsd_templates()
    form = templates.forms[form_of(content, draft.fields)]
    columns = [column.key for column in form.columns if column.hold == hold]
    if not columns:
        return None
    waiting = []
    for row in content["ppsd"]["rows"]:
        if row.get("removed"):
            continue
        empty = [key for key in columns if not draft.fields.get((row["row_key"], key))]
        if empty:
            waiting.append(f"fill-{row['row_key']}-{empty[0]}")
    return Held(len(waiting), waiting[0]) if waiting else None


def check_value(content: dict, row_key: str, field: str, value: str | None) -> str | None:
    """Why a person's value for a field cannot be saved, as an error code, or None when it can. Only the fields
    people fill (filled_by = "people") take a value; Strata's own cells never do."""
    templates = load_ppsd_templates()
    if row_key == "" and field == "form":
        if value not in templates.forms:
            return "unknown_form"
        if value != templates.default_form and not content["ppsd"]["table_i"]["applies"]:
            return "form_not_offered"
        return None
    column = templates.people_column(field)
    if column is None:
        return "unknown_field"
    if row_key not in {row["row_key"] for row in content["ppsd"]["rows"]}:
        return "unknown_row"
    if value is None:
        return None
    text = value.strip()
    if column.control == "text":
        return "empty" if not text else "too_long" if len(text) > (column.max_length or 120) else None
    if column.control == "rating":
        return None if text in {str(level.value) for level in templates.ratings} else "not_a_rating"
    if column.control == "score":
        if not re.fullmatch(r"\d+", text):
            return "not_a_score"
        return None if templates.score.minimum <= int(text) <= templates.score.maximum else "not_a_score"
    if column.control == "stage":
        return "empty" if not text else "too_long" if len(text) > (column.max_length or 80) else None
    return "unknown_field"


# ── The Word file ────────────────────────────────────────────────────────

def word(document, draft: dict, words: dict, say) -> None:
    """The Word file (the 36 brief, section 6.6), in Word's built-in styles: the heading, the package's line, the
    origin paragraph, one table with the template's header row for the form the person chose, with a footnote where
    each marker was, and the not-visible line. Text in it speaks in the document's voice."""
    layout = words["files"]["word"]["ppsd_rows"]
    about, shown = draft["subject"], draft["ppsd"]
    form = shown["forms"][shown["form"]]
    document.heading(layout["heading"])
    reference = about["step_reference"] or layout["noReference"]
    project = _fill(layout["project"], project_name=about["project_name"], project_id=about["project_id"]) \
        if about.get("project_id") else ""
    document.paragraph(" ".join(part for part in (
        _fill(layout["line"], package_title=about["package_title"], reference=reference), project,
        _fill(layout["form"], form_name=form["name"])) if part))
    checked = draft["checked"] or {}
    rated = any(column["hold"] == "ratings" for column in form["columns"])
    document.paragraph(_fill(layout["origin"], created=say.date(draft["created_at"]), checker=checked.get("by") or "",
                             checked=say.date(checked["at"]) if checked.get("at") else "",
                             author=draft["author"]["name"] or "",
                             set_what=layout["setOwnersRatings"] if rated else layout["setOwners"]))
    notes = {note["key"]: note for note in draft["notes"]}
    numbered = {(entry["row_key"], entry["cell"], entry["position"]): entry for entry in draft["footnotes"]}
    values = {(entry["row_key"], entry["field"]): entry["value"] for entry in shown["values"]}
    rows = []
    for row in shown["rows"]:
        cells = []
        for column in form["columns"]:
            if column["filled_by"] == "strata":
                note = notes.get(row["cells"][column["key"]]) or {}
                runs = []
                for position, sentence in enumerate(note.get("sentences") or ()):
                    entry = numbered[(row["row_key"], column["key"], position)]
                    runs += [*written_runs(sentence, draft), document.footnote(entry["text"]), " "]
                cells.append([runs[:-1]] if runs else [[]])
            else:
                cells.append([[values.get((row["row_key"], column["key"])) or ""]])
        rows.append(cells)
    total = 9026
    widths = tuple(int(total / len(form["columns"])) for _ in form["columns"])
    # The template's header cells, word for word: the Long Form puts each rating's letter above its name.
    headers = [[column["letter"], column["header"]] if column["letter"] else column["header"] for column in form["columns"]]
    document.table(headers, rows, widths=widths)
    document.paragraph(words["notVisible"])
