"""The Project Paper summary workflow: the procurement summary for the Project Paper (ticket 36).

"Draft a Project Paper summary" on the "Drafts from this check" panel at the end of Check a plan starts it, for one
implementing agency's plan version. The draft runtime (runtime.py) calls its steps and runs the writer agent and the
verifier between them, so no kind of draft can skip the checks:

1. read() runs check_plan on the plan version and agency_track_record on the same agency, through the tool registry
   as the viewer and as of today, and takes the PPSD rows the viewer's team checked for the project's packages,
   which the route reads from the drafts store (only drafts Checked by you or Exported; the 36 brief, 5.7).
2. message() is the writer's one message, data only. items() gives the summary's three parts, in order, each with
   the records its sentences may cite: the plan (check_plan's summary of counts and its rows), the agency's track
   record (agency_track_record's summary and rows) and the PPSD's risks (the records the checked rows cite). A part
   with nothing to draw on says why (reason), and the page says so and the Word file leaves it out.
3. The summary never rates the agency's procurement risk: assessing it is the specialist's call, and the writer's
   instructions (src/strata/agent/instructions/project_paper_writer.md) say so.

word() lays out the Word file: the heading, the project's line, the origin paragraph, then a Heading 2 and its
paragraph per part that has sentences, with a footnote for each citation.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from importlib import resources

from strata.dbx import Viewer
from strata.lakehouse.engine import Engine
from strata.tools import registry

TOOL = "check_plan"
TOOLS = ("check_plan", "agency_track_record")
KEY = "part"
VIEW_KEY = "summary"
PARTS = ("plan", "record", "ppsd")


class NotWritable(Exception):
    """There is nothing to write the summary from: no such plan version."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Facts:
    request: dict
    checked: dict  # check_plan's result
    track: dict  # agency_track_record's result
    ppsd: list[dict]  # the team's checked PPSD drafts on the project's packages
    agencies_with_plans: int


def agencies_with_plans(engine: Engine, project_id: str, as_of: dt.date) -> int:
    sql = (resources.files("strata.drafts") / "sql" / "agencies_with_plans.sql").read_text()
    result = engine.run(sql, {"project_id": project_id, "as_of": as_of})
    return int(result.rows[0][0]) if result.rows else 0


def read(engine: Engine, viewer: Viewer, request: dict, today: dt.date) -> Facts:
    if not request.get("agency_id") or not request.get("plan_date"):
        raise NotWritable("no_plan")
    context = registry.Context(engine, viewer, "staff", today)
    arguments = {"project_id": request["project_id"], "implementing_agency": request["agency_id"],
                 "plan_date": request["plan_date"]}
    checked = registry.call("check_plan", arguments, context)
    if checked["abstention"] or checked["plan"] is None:
        raise NotWritable("no_plan")
    track = registry.call("agency_track_record", arguments, context)
    return Facts(request, checked, track, list(request.get("ppsd") or ()),
                 agencies_with_plans(engine, request["project_id"], today))


def read_done(facts: Facts) -> dict:
    """What the read step says it read: the plan's date, the agency's past packages and the checked PPSD rows."""
    counts = facts.track["summary"]["counts"] or {}
    return {"plan_date": facts.checked["plan"]["plan_date"], "packages": counts.get("n", 0),
            "ppsd_rows": sum(len(draft["rows"]) for draft in facts.ppsd)}


def question(facts: Facts) -> str:
    plan = facts.checked["plan"]
    return (f"Write the procurement summary for the Project Paper from the {plan['implementing_agency']}'s Procurement "
            f"Plan of {plan['plan_date']} for {plan['project_id']}.")


def _ppsd_rows(facts: Facts) -> list[tuple[dict, str]]:
    """The records the checked PPSD rows cite, with the tool that returned each when the rows were written."""
    seen, found = set(), []
    for draft in facts.ppsd:
        for evidence_id, entry in draft["evidence"].items():
            if evidence_id not in seen:
                seen.add(evidence_id)
                found.append((entry["row"], entry.get("tool") or "get_lessons"))
    return found


def cited_rows(facts: Facts) -> list[tuple[dict, str]]:
    """Every record the writer may cite, with the tool that returned it."""
    return [*((row, "check_plan") for row in facts.checked["rows"]), (facts.checked["summary"], "check_plan"),
            *((row, "agency_track_record") for row in facts.track["rows"]),
            (facts.track["summary"], "agency_track_record"), *_ppsd_rows(facts)]


def message(facts: Facts, language: str = "en") -> dict:
    plan, project, track = facts.checked["plan"], facts.checked["project"], facts.track
    return {"task": "project_paper", "language": language,
            "project": {"project_id": project["project_id"], "project_name": project["project_name"]},
            "plan": {key: plan[key] for key in ("evidence_id", "implementing_agency", "plan_date")},
            "plan_check": {"summary_evidence_id": facts.checked["summary"]["evidence_id"],
                           "counts": facts.checked["counts"],
                           "activities": [{key: row[key] for key in ("evidence_id", "activity_reference_no",
                                                                     "description", "process_status", "marks")}
                                          for row in facts.checked["rows"] if row["marks"]]},
            "track_record": {"summary_evidence_id": track["summary"]["evidence_id"], "counts": track["counts"],
                             "signed_from": track["signed_from"], "differs_from_awards": track["differs_from_awards"],
                             "packages": track["rows"]},
            "ppsd": [{"draft_id": draft["draft_id"], "package_title": draft["package_title"],
                      "rows": [{"risk_label": row["risk_label"],
                                "sentences": [{"text": sentence["text"], "evidence_ids": sentence["evidence_ids"]}
                                              for sentence in row["sentences"]]} for row in draft["rows"]]}
                     for draft in facts.ppsd],
            "parts": [{"part": part, "reason": _reason(facts, part)} for part in PARTS]}


def _reason(facts: Facts, part: str) -> str | None:
    """Why a part has nothing to draw on, or None."""
    if part == "record" and not (facts.track["counts"] or {}).get("n"):
        return "no_track_record"
    if part == "ppsd" and not facts.ppsd:
        return "no_ppsd_rows"
    return None


def items(facts: Facts) -> list[dict]:
    """The summary's three parts, in order, each with the records its sentences may cite."""
    plan_ids = [facts.checked["summary"]["evidence_id"], *(row["evidence_id"] for row in facts.checked["rows"])]
    track_ids = [facts.track["summary"]["evidence_id"], *(row["evidence_id"] for row in facts.track["rows"])]
    ppsd_ids = [row["evidence_id"] for row, _ in _ppsd_rows(facts)]
    drafts = [{key: draft[key] for key in ("draft_id", "package_title", "checked_by", "checked_at")}
              for draft in facts.ppsd]
    packages = [{key: row[key] for key in ("evidence_id", "step_reference", "first_planned_on", "signed_on", "state")}
                 for row in facts.track["rows"]]
    found = []
    for part, cites in (("plan", plan_ids), ("record", track_ids), ("ppsd", ppsd_ids)):
        extra = {"reason": _reason(facts, part)}
        if part == "record":
            extra |= {"counts": facts.track["counts"], "packages": packages, "signed_from": facts.track["signed_from"]}
        if part == "ppsd":
            extra |= {"drafts": drafts}
        found.append({"key": part, "evidence_id": cites[0] if cites else facts.checked["summary"]["evidence_id"],
                      "evidence_ids": cites, "description": None, "mark": None, "extra": extra})
    return found


def subject(facts: Facts) -> dict:
    plan, project = facts.checked["plan"], facts.checked["project"]
    return {"project_id": project["project_id"], "project_name": project["project_name"],
            "implementing_agency": plan["implementing_agency"], "agency_id": plan["agency_id"],
            "plan_date": plan["plan_date"], "document_id": plan["document_id"], "disclosed_on": plan["disclosed_on"],
            "pdf_url": plan["pdf_url"], "as_of": facts.checked["as_of"], "signal": None,
            "agencies_with_plans": facts.agencies_with_plans}


def subject_key(facts: Facts) -> str:
    """What the draft is about, for the panel's notice of a summary already started on the same plan version."""
    return facts.checked["plan"]["document_id"]


def view(content: dict, fields: dict, words: dict) -> dict:
    """What the summary page adds: each part's reason and, for the PPSD part, the drafts it drew on."""
    notes = {note["key"]: note for note in content["notes"]}
    return {"agencies_with_plans": content["subject"].get("agencies_with_plans"),
            "parts": [{"part": part, "reason": (notes.get(part) or {}).get("reason"),
                       "state": (notes.get(part) or {}).get("state")} for part in PARTS]}


# ── The Word file ────────────────────────────────────────────────────────

def word(document, draft: dict, words: dict, say) -> None:
    """The Word file (the 36 brief, section 6.6), in Word's built-in styles. A part with no sentence is left out.
    Text in it speaks in the document's voice."""
    layout = words["files"]["word"]["project_paper"]
    about = draft["subject"]
    plan_date = say.date(about["plan_date"])
    document.heading(layout["heading"])
    document.paragraph(say(layout["line"], project_name=about["project_name"], project_id=about["project_id"],
                           agency=about["implementing_agency"], date=plan_date))
    checked = draft["checked"] or {}
    document.paragraph(say(layout["origin"], created=say.date(draft["created_at"]), checker=checked.get("by") or "",
                           checked=say.date(checked["at"]) if checked.get("at") else ""))
    for note in draft["notes"]:
        if not note["sentences"]:
            continue
        document.subheading(layout["parts"][note["key"]])
        runs = []
        for sentence in note["sentences"]:
            runs += [sentence["text"], *[document.footnote(_footnote(draft, evidence, say))
                                         for evidence in sentence["evidence_ids"]], " "]
        document.paragraph(*runs[:-1])
    document.paragraph(words["notVisible"])


def _footnote(draft: dict, evidence_id: str, say) -> str:
    """A footnote: the source line without "Source:", then the plan's public address for a record of the plan, as
    brief 35's footnotes do. A tool's counts and a completion report's passage get their source line only."""
    if evidence_id.startswith(("strata.silver.plan_rows:", "strata.silver.plan_versions:")):
        return say.footnote(draft, evidence_id)
    return say.source(draft, evidence_id)
