"""The check-a-plan workflow: review notes on a borrower's Procurement Plan (ticket 35).

A World Bank procurement specialist turns a plan check into review notes in one action. The draft
runtime (runtime.py) calls this module's three steps, and runs the writer agent and the verifier
between them, so no kind of draft can skip the checks:

1. read() runs check_plan through the tool registry as the viewer, as of today (a draft is never written
   as of a past date), and keeps the activities with a signal (needs a look or watch) in the plan check's
   order: needs a look first, then watch, then check_plan's own order. Data notes describe the record,
   not the activity's progress, so they get no note (the 35 brief, section 2).
2. message() is the writer agent's one message, which carries data only: the plan, the project and the
   rows with a signal, each with its evidence id and marks (src/strata/agent/instructions/
   review_notes_writer.md says what to write).
3. subject() is what the draft keeps about what it was written from: the project and the plan version,
   with the count of activities with a signal from check_plan's counts.

word() lays out the Word file: a heading, the plan's line, the origin paragraph, the two-column table
(Activity, Review note) with a footnote where each citation was, and the not-visible line (section 6.7).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from strata.dbx import Viewer
from strata.lakehouse.engine import Engine
from strata.tools import registry

TOOL = "check_plan"
KEY = "activity_reference_no"  # what names each note in the writer's answer and on the page
RANK = {"needs_a_look": 0, "watch": 1}


class NotWritable(Exception):
    """There is nothing to write review notes from: no such plan version, or no activity with a signal."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Facts:
    """What the draft is written from: check_plan's result and its rows with a signal, in note order."""

    request: dict
    result: dict
    rows: list[dict]


def _signal(row: dict) -> str | None:
    marks = [mark["mark"] for mark in row["marks"] if mark["mark"] in RANK]
    return min(marks, key=RANK.get) if marks else None


def read(engine: Engine, viewer: Viewer, request: dict, today: dt.date) -> Facts:
    if not request.get("agency_id") or not request.get("plan_date"):
        raise NotWritable("no_plan")
    result = registry.call(TOOL, {"project_id": request["project_id"], "implementing_agency": request["agency_id"],
                                  "plan_date": request["plan_date"]}, registry.Context(engine, viewer, "staff", today))
    if result["abstention"] or result["plan"] is None:
        raise NotWritable("no_plan")
    ordered = sorted(((index, row) for index, row in enumerate(result["rows"]) if _signal(row)),
                     key=lambda pair: (RANK[_signal(pair[1])], pair[0]))
    if not ordered:
        raise NotWritable("nothing_marked")
    return Facts(request, result, [row for _, row in ordered])


def question(facts: Facts) -> str:
    """The writer's task in one line, for the run log."""
    plan = facts.result["plan"]
    return (f"Write review notes on the {plan['implementing_agency']}'s Procurement Plan of "
            f"{plan['plan_date']} for {plan['project_id']}.")


def message(facts: Facts, language: str = "en") -> dict:
    plan, project = facts.result["plan"], facts.result["project"]
    return {"task": "review_notes", "language": language,
            "plan": {key: plan[key] for key in ("evidence_id", "project_id", "implementing_agency", "plan_date")},
            "project": {"project_id": project["project_id"], "project_name": project["project_name"]},
            "activities": facts.rows}


def items(facts: Facts) -> list[dict]:
    """One item per note, in order: its activity, the row a note may cite, and the row's signal."""
    return [{"key": row[KEY], "evidence_id": row["evidence_id"], "description": row["description"],
             "mark": _signal(row)} for row in facts.rows]


def subject(facts: Facts) -> dict:
    plan, project = facts.result["plan"], facts.result["project"]
    return {"project_id": project["project_id"], "project_name": project["project_name"],
            "implementing_agency": plan["implementing_agency"], "agency_id": plan["agency_id"],
            "plan_date": plan["plan_date"], "document_id": plan["document_id"], "disclosed_on": plan["disclosed_on"],
            "pdf_url": plan["pdf_url"], "as_of": facts.result["as_of"], "signal": facts.result["counts"]["signal"]}


def subject_key(facts: Facts) -> str:
    """What the draft is about, for the notice that names a draft already started on the same plan."""
    return facts.result["plan"]["document_id"]


def word(document, draft: dict, words: dict, say) -> None:
    """The Word file (the 35 brief, section 6.7), in Word's built-in styles. document is files.Word; draft
    is the draft as the page reads it; say(template, **values) fills a template from copy.json."""
    layout = words["files"]["word"]["review_notes"]
    about = draft["subject"]
    plan_date = say.date(about["plan_date"])
    document.heading(say(layout["heading"], agency=about["implementing_agency"], date=plan_date))
    document.paragraph(say(layout["line"], project_name=about["project_name"], project_id=about["project_id"],
                           date=plan_date))
    checked = draft["checked"] or {}
    document.paragraph(say(layout["origin"], created=say.date(draft["created_at"]), checker=checked.get("by") or "",
                           checked=say.date(checked["at"]) if checked.get("at") else ""))
    rows = []
    for note in draft["notes"]:
        activity = [[note["activity_reference_no"]], [note["description"] or ""]]
        cell = [run for sentence in note["sentences"]
                for run in ([sentence["text"]] + [document.footnote(say.footnote(draft, evidence))
                                                  for evidence in sentence["evidence_ids"]] + [" "])]
        rows.append([activity, [cell[:-1]] if cell else [[]]])
    document.table(layout["columns"], rows, widths=(3000, 6026))
    document.paragraph(words["notVisible"])
