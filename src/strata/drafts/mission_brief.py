"""The write-the-mission-brief workflow: a task team leader's brief before a mission (ticket 37).

"Add to mission brief" on a Following row starts it. The draft runtime (runtime.py) calls this module's steps, and
runs the writer agent and the verifier between them, so no kind of draft can skip the checks:

1. read() calls project_records through the tool registry as the viewer, as of today (a draft is never written as
   of a past date), and check_plan on each implementing agency's latest plan, keeping the activities that need a
   look or are worth watching, so the plans part can name them with their reasons.
2. message() is the writer agent's one message, which carries data only: the project and, for each of the five
   parts in order, its records, its totals and why it has none (src/strata/agent/instructions/
   mission_brief_writer.md says what to write).
3. items() gives the five parts, each with the records its sentences may cite: its own rows, the totals in
   project_records' summary record, and for the plans part the marked activities. A sentence that cites a record of
   another part is removed (id_not_returned), as a review note that cites another activity's row is.

The page shows each part's sentences first and its table second, from the records the draft keeps (extra), so every
number in a table is a tool's value. word() lays out the Word file: the heading, the project's line, the origin
paragraph, then for each part its heading, its sentences with a footnote where each citation was, its table title
and the table, and the not-visible line.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from strata.dbx import Viewer
from strata.lakehouse.engine import Engine
from strata.server.viewer_sql import data_through
from strata.tools import registry

TOOL = "project_records"
# The tools the check line names: project_records' "Not checked" clause covers the plans' records too, so
# check_plan's would only repeat it.
TOOLS = ("project_records",)
KEY = "part"
PARTS = ("plans", "awards", "ratings", "disbursement", "closing")
SIGNALS = ("needs_a_look", "watch")


class NotWritable(Exception):
    """There is nothing to write a mission brief from: no such project, or one no longer active."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Facts:
    """What the brief is written from: project_records' result and the plans' activities with a signal."""

    request: dict
    result: dict
    marked: list[dict]
    # The data-freshness day the records run through, never after the as-of date (ADR 0002).
    through: dt.date | None = None

    @property
    def rows(self) -> list[dict]:
        return [*self.result["rows"], self.result["summary"], *self.marked]


def read(engine: Engine, viewer: Viewer, request: dict, today: dt.date) -> Facts:
    context = registry.Context(engine, viewer, "staff", today)
    result = registry.call(TOOL, {"project_id": request["project_id"]}, context)
    if result["abstention"] or result["project"] is None:
        raise NotWritable("no_project")
    if result["project"]["status"] != "active":
        raise NotWritable("not_active")
    marked = []
    for row in result["rows"]:
        if row["part"] != "plans":
            continue
        agency = next(field["value"] for field in row["fields"] if field["key"] == "implementing_agency")
        checked = registry.call("check_plan", {"project_id": request["project_id"], "implementing_agency": agency},
                                context)
        marked += [activity for activity in checked["rows"] if any(mark["mark"] in SIGNALS for mark in activity["marks"])]
    through = data_through(engine)
    return Facts(request, result, marked, min(through, today) if through else None)


def cited_rows(facts: Facts) -> list[tuple[dict, str]]:
    """Every record the writer may cite, with the tool that returned it."""
    return [*((row, TOOL) for row in facts.result["rows"]), (facts.result["summary"], TOOL),
            *((row, "check_plan") for row in facts.marked)]


def read_done(facts: Facts) -> dict:
    """What the read step says it read: the plans, the contracts since the last ISR, the ISRs."""
    totals = facts.result["summary"]["totals"]
    return {"plans": totals["plans"]["agencies"], "awards": totals["awards"]["count"], "isrs": totals["ratings"]["isrs"]}


def question(facts: Facts) -> str:
    project = facts.result["project"]
    return f"Write a mission brief for {project['project_name']} ({project['project_id']})."


def _part_rows(facts: Facts, part: str) -> list[dict]:
    return [row for row in facts.result["rows"] if row["part"] == part]


def message(facts: Facts, language: str = "en") -> dict:
    result = facts.result
    totals = result["summary"]["totals"]
    return {"task": "mission_brief", "language": language,
            "project": {key: result["project"][key] for key in ("project_id", "project_name", "country", "closing_date")},
            "isr": result["isr"], "totals_evidence_id": result["summary"]["evidence_id"],
            "parts": [{"part": part, "reason": result["parts"][part]["reason"], "totals": totals.get(part),
                       "records": _part_rows(facts, part),
                       **({"marked_activities": facts.marked, "agencies_without_plans": result["unmatched_agencies"]}
                          if part == "plans" else {})} for part in PARTS]}


def items(facts: Facts) -> list[dict]:
    """The five parts, in the ticket's order, each with the records its sentences may cite and its table."""
    result = facts.result
    summary = result["summary"]["evidence_id"]
    found = []
    for part in PARTS:
        rows = _part_rows(facts, part)
        cites = [row["evidence_id"] for row in rows] + [summary]
        if part == "plans":
            cites += [row["evidence_id"] for row in facts.marked]
        found.append({"key": part, "evidence_id": summary, "evidence_ids": cites, "description": None, "mark": None,
                      "extra": {"reason": result["parts"][part]["reason"], "table": rows,
                                "totals": result["summary"]["totals"].get(part),
                                **({"agencies_without_plans": result["unmatched_agencies"]} if part == "plans" else {})}})
    return found


def subject(facts: Facts) -> dict:
    project, isr = facts.result["project"], facts.result["isr"]
    return {"project_id": project["project_id"], "project_name": project["project_name"], "country": project["country"],
            "closing_date": project["closing_date"], "as_of": facts.result["as_of"],
            "data_through": facts.through.isoformat() if facts.through else None,
            "isr_date": isr["isr_date"] if isr else None, "isr_sequence": isr["sequence"] if isr else None,
            "date": facts.result["as_of"], "signal": None}


def subject_key(facts: Facts) -> str:
    """What the draft is about, for the Following row that names a brief already started on the project."""
    return facts.result["project"]["project_id"]


# ── The Word file ────────────────────────────────────────────────────────

def _field(row: dict, key: str):
    return next((field["value"] for field in row["fields"] if field["key"] == key), None)


def _money(value) -> str:
    return "" if value in (None, "") else f"{float(value):,.2f}"


def _table(part: str, note: dict, layout: dict, say) -> tuple[list[str], list[list[str]], tuple[int, ...]] | None:
    rows = note.get("table") or []
    if not rows:
        return None
    columns = layout["columns"][part]
    if part == "plans":
        body = [[_field(row, "implementing_agency"), say(layout["planVersion"], date=say.date(_field(row, "plan_date"))),
                 str(_field(row, "activities")), str(_field(row, "needs_a_look")), str(_field(row, "watch"))] for row in rows]
        body += [[name, layout["noPlan"], "", "", ""] for name in note.get("agencies_without_plans") or []]
        return columns, body, (3200, 2000, 1300, 1300, 1226)
    if part == "awards":
        body = [[f"{_field(row, 'step_reference') or row['reference']} {_field(row, 'contract_description') or ''}".strip(),
                 say.date(_field(row, "signed_on")),
                 _field(row, "supplier") or (layout["individual"] if _field(row, "individual_consultant") else ""),
                 _money(_field(row, "signed_amount_usd")) or f"{_field(row, 'currency') or ''} {_field(row, 'signed_amount') or ''}".strip(),
                 _money(_field(row, "estimated_amount_usd"))] for row in rows]
        return columns, body, (2600, 1400, 2000, 1500, 1526)
    if part == "ratings":
        by_isr: dict[int, dict] = {}
        for row in rows:
            entry = by_isr.setdefault(_field(row, "sequence"), {"date": _field(row, "isr_date")})
            entry[_field(row, "rating_key")] = _field(row, "current_rating")
        body = [[say(layout["isr"], sequence=sequence), say.date(entry["date"]), entry.get("pdo") or layout["notRated"],
                 entry.get("implementation") or layout["notRated"]] for sequence, entry in sorted(by_isr.items())]
        return columns, body, (1400, 1800, 2900, 2926)
    if part == "disbursement":
        body = [[_field(row, "loan_number"), _field(row, "original_principal_millions"), _field(row, "disbursed_millions"),
                 _field(row, "undisbursed_millions"), _field(row, "cancelled_millions")] for row in rows]
        totals = note.get("totals") or {}
        if len(rows) > 1:
            body.append([layout["total"], totals.get("commitment_millions"), totals.get("disbursed_millions"),
                         totals.get("undisbursed_millions"), totals.get("canceled_millions")])
        return columns, body, (2200, 1700, 1700, 1700, 1726)
    moves = [row for row in rows if row["source"]["source_key"] == "loan_history"]
    after = [row for row in rows if row["source"]["source_key"] == "plans"]
    body = [[_field(row, "activity_reference_no"), _field(row, "implementing_agency"),
             say.date(_field(row, "planned_completion_on")), str(_field(row, "days_after_closing"))] for row in after]
    body += [[layout["moved"], say.date(_field(row, "previous_closing_date")), say.date(_field(row, "closing_date")),
              say.date(_field(row, "reported_on"))] for row in moves]
    return columns, body, (2600, 2400, 2000, 2026)


def _none(part: str, reason: str, about: dict, layout: dict, say) -> str:
    """Why a part has no records, by the reason project_records gave (the 37 brief, section 7.4, item 4)."""
    if part == "ratings" and reason == "no_isr":
        return layout["ratingsNone"]
    date = about.get("isr_date") if reason == "no_awards" else about.get("closing_date")
    return say(layout["none"][reason], date=say.date(date) if date else "")


def word(document, draft: dict, words: dict, say) -> None:
    """The Word file (the 37 brief, section 7.4), in Word's built-in styles. Text in it speaks in the document's
    voice; an abstaining part keeps its heading and its line, so the reader sees what is missing."""
    layout = words["files"]["word"]["mission_brief"]
    about = draft["subject"]
    document.heading(say(layout["heading"], project_name=about["project_name"], project_id=about["project_id"]))
    through = about.get("data_through") or about["as_of"]
    document.paragraph(say(layout["line"], country=about.get("country") or "", date=say.date(through)))
    checked = draft["checked"] or {}
    document.paragraph(say(layout["origin"], created=say.date(draft["created_at"]), checker=checked.get("by") or "",
                           checked=say.date(checked["at"]) if checked.get("at") else ""))
    for note in draft["notes"]:
        part = note["key"]
        document.subheading(layout["parts"][part])
        if not note["sentences"] and note.get("reason"):
            document.paragraph(_none(part, note["reason"], about, layout, say))
        for sentence in note["sentences"]:
            document.paragraph(sentence["text"], *[document.footnote(say.footnote(draft, evidence))
                                                   for evidence in sentence["evidence_ids"]])
        table = _table(part, note, layout, say)
        if table:
            header, body, widths = table
            document.bold(say(layout["tables"][part], date=say.date(about["isr_date"]) if about.get("isr_date") else ""))
            document.table(header, [[[[cell or ""]] for cell in row] for row in body], widths=widths)
        if part == "disbursement" and (note.get("totals") or {}).get("amounts_exceed_commitment"):
            document.paragraph(layout["exceeds"])
    document.paragraph(words["notVisible"])
