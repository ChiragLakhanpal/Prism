"""Planned dates for every STEP step of an implementing agency's plan, and the STEP rows CSV (ticket 38).

An implementing agency officer drafts planned dates for every activity of their team's upload, or of their own
agency's latest published plan. No model writes this draft: estimate_time dates each step from the delay model
(src/strata/estimates/step_dates.py), and the verifier checks every date and count before anything is saved. The
draft runtime (runtime.py, write_computed) runs this module's steps:

1. read() reads the activities as the viewer: an upload's rows, which the draft route has already read through the
   one access rule and hands over in the request, or check_plan's rows for a published plan. For each activity it
   calls estimate_time through the tool registry, as of today, with the upload's row (upload_row, so the steps are
   dated from the officer's own dates) or the plan row's STEP reference (dated from each step's first published
   date).
2. compose() lays out the draft from those answers, one entry per activity in the order of the officer's file,
   then runs the verifier's checks 1 and 2 on it: every date and count on the page must match a value estimate_time
   returned this turn for that step's list of comparable packages, and every list must have come back this turn. A
   value that fails is removed from its cell, with the reason, and the draft's check line counts the rest.
3. nothing_dated() says when no step at all could be dated, so nothing is saved.

Each dated step rests on its list of comparable packages, cited as steps:{activity}:{step_key}, where the activity
is the upload's row (upload:{upload_id}:{position}) or the STEP reference; the draft lists those lists as its
sources, so the bar counts the lists the viewer opened and the evidence pack records them. The draft keeps each
list as estimate_time returned it this turn, in the evidence drawer's shape for a step's list (web/src/lib/steps.ts,
StepListRow), so a count or a date on the page opens its comparable packages with no request.

step_rows_csv() writes the STEP rows file: STEP's columns from the STEP column registry (config/uploads.toml), one
row per activity in the file's order, the checked choice's planned dates filled in, the officer's other values
copied unchanged, and the columns the registry leaves to people and STEP empty: UTF-8 with a byte order mark, commas,
CRLF line ends and RFC 4180 quoting, and no line outside STEP's columns.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from dataclasses import dataclass

from strata.agent.claims import Claim
from strata.agent.verifier import Verdict, check
from strata.config import load_thresholds
from strata.dbx import Viewer
from strata.estimates.step_dates import CHOICES, Settings, families
from strata.harness.facts import Facts as Seen
from strata.lakehouse.engine import Engine
from strata.reader.step_columns import DESCRIPTION, REFERENCE, registry as step_columns
from strata.tools import registry

TOOL = "estimate_time"
TOOLS = (TOOL,)
KEY = "position"
VIEW_KEY = "dates"
DEFAULT_CHOICE = "cautious"
CHOICE = ("", "choice")  # the draft field that holds the one choice for the whole draft
DRAFT_ONLY_FIELDS = ("choice",)  # switched only in Draft; once checked, the export uses the checked choice
STEP_FIELDS = ("step_key", "comparables_n", "abstain_reason", "plan_first_date", "middle", "cautious")


class NotWritable(Exception):
    """There is nothing to date: no such upload or plan, or one with no activity."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Facts:
    """What the draft is dated from: each activity with estimate_time's answer for it, and the plan's subject."""

    request: dict
    subject: dict
    activities: list[dict]  # each: position, reference, description, section, fields, raw, answer
    as_of: dt.date


def _labels() -> dict[str, dict]:
    """Each step's label and STEP name, by its key, from the step-label registry."""
    return {entry["key"]: entry for family in families().values() for entry in family["steps"]}


def read(engine: Engine, viewer: Viewer, request: dict, today: dt.date) -> Facts:
    if request.get("upload"):
        return _read_upload(engine, viewer, request, today)
    if request.get("agency_id") and request.get("plan_date"):
        return _read_plan(engine, viewer, request, today)
    raise NotWritable("no_plan")


def _read_upload(engine: Engine, viewer: Viewer, request: dict, today: dt.date) -> Facts:
    upload = request["upload"]

    def only(upload_id: str):  # the route read this upload through the access rule; the tools get nothing else
        return upload if upload_id == upload["upload_id"] else None

    context = registry.Context(engine, viewer, "staff", today, uploads=only)
    checked = registry.call("check_plan", {"project_id": upload["project_id"],
                                           "implementing_agency": upload["implementing_agency"],
                                           "upload_id": upload["upload_id"]}, context)
    if checked["abstention"] or not upload["rows"]:
        raise NotWritable("no_plan")
    activities = []
    for row in upload["rows"]:
        answer = registry.call(TOOL, {"upload_row": f"{upload['upload_id']}:{row['position']}"}, context)
        activities.append({"position": int(row["position"]), "reference": row.get("reference"),
                           "description": row.get("description"), "section": row.get("section"),
                           "fields": row.get("fields") or {}, "raw": row.get("raw") or {},
                           "list_key": f"upload:{upload['upload_id']}:{row['position']}", "answer": answer})
    project = checked["project"]
    subject = {"source": "upload", "upload_id": upload["upload_id"], "file_name": upload["file_name"],
               "project_id": upload["project_id"], "project_name": project["project_name"],
               "implementing_agency": upload["implementing_agency"], "agency_id": checked["plan"]["agency_id"],
               "plan_date": upload["uploaded_on"], "official_use_only": True}
    return Facts(request, subject, activities, today)


def _read_plan(engine: Engine, viewer: Viewer, request: dict, today: dt.date) -> Facts:
    context = registry.Context(engine, viewer, "staff", today)
    checked = registry.call("check_plan", {"project_id": request["project_id"], "implementing_agency": request["agency_id"],
                                           "plan_date": request["plan_date"]}, context)
    if checked["abstention"] or not checked["rows"]:
        raise NotWritable("no_plan")
    activities = []
    for position, row in enumerate(checked["rows"], 1):
        answer = registry.call(TOOL, {"step_reference": row["activity_reference_no"]}, context)
        fields = {key: row[key] for key in ("review_type", "method", "market_approach", "estimated_amount_usd",
                                            "actual_amount_usd", "process_status")}
        activities.append({"position": position, "reference": row["activity_reference_no"],
                           "description": row["description"], "section": row["section"], "fields": fields,
                           "raw": {key: value for key, value in fields.items() if value is not None},
                           "list_key": row["activity_reference_no"], "answer": answer})
    plan, project = checked["plan"], checked["project"]
    subject = {"source": "plan", "upload_id": None, "file_name": None, "project_id": project["project_id"],
               "project_name": project["project_name"], "implementing_agency": plan["implementing_agency"],
               "agency_id": plan["agency_id"], "plan_date": plan["plan_date"], "document_id": plan["document_id"],
               "official_use_only": True}
    return Facts(request, subject, activities, today)


def question(facts: Facts) -> str:
    about = facts.subject
    return f"Date every STEP step of {about['implementing_agency']}'s plan of {about['plan_date']} for {about['project_id']}."


def read_done(facts: Facts) -> dict:
    return {"activities": len(facts.activities)}


def subject_key(facts: Facts) -> str:
    return facts.subject["upload_id"] or facts.subject["document_id"]


def list_id(activity: dict, step_key: str) -> str:
    return f"steps:{activity['list_key']}:{step_key}"


def _choice(value: dict | None) -> dict | None:
    return None if value is None else {key: value.get(key) for key in ("planned_date", "days", "days_relation",
                                                                      "longer", "in10")}


def _activity(found: dict, labels: dict) -> dict:
    """One activity's entry: its STEP values, and each step's two dates and count as estimate_time gave them."""
    answer = found["answer"]
    dated = answer["step_dates"] or {}
    steps = []
    for step in dated.get("steps") or []:
        label = labels.get(step["step_key"], {})
        steps.append({"step_key": step["step_key"], "label": label.get("label"), "step_name": label.get("step_name"),
                      "is_anchor": step.get("is_anchor"), "comparables_n": step.get("comparables_n"),
                      "abstain_reason": step.get("abstain_reason"), "plan_first_date": step.get("plan_first_date"),
                      "middle": _choice(step.get("middle")), "cautious": _choice(step.get("cautious")),
                      "list_id": list_id(found, step["step_key"]), "removed": None})
    return {"key": f"activity-{found['position']}", "position": found["position"], "reference": found["reference"],
            "description": found["description"], "section": found["section"], "fields": found["fields"],
            "raw": found["raw"], "family": dated.get("family"), "family_reason": dated.get("family_reason"),
            "basis": dated.get("basis"), "needs_start_date": dated.get("needs_start_date"),
            "abstain_all": dated.get("abstain_all"), "actual_steps_count": dated.get("actual_steps_count"),
            "estimate_abstention": (answer["abstention"] or {}).get("reason"), "steps": steps}


def _claims(activities: list[dict]) -> tuple[list[Claim], list[tuple[str, str]]]:
    """One claim for each step that states a date or a count, citing its list, as the page states them, and which
    activity and step each is about."""
    claims, owners = [], []
    for activity in activities:
        for step in activity["steps"]:
            dates = [step[choice]["planned_date"] for choice in CHOICES if step[choice] and step[choice]["planned_date"]]
            if not dates and step["comparables_n"] is None:
                continue
            parts = [f"{choice} date {step[choice]['planned_date']}" for choice in CHOICES
                     if step[choice] and step[choice]["planned_date"]]
            if step["comparables_n"] is not None:
                parts.append(f"{step['comparables_n']} comparable packages")
            claims.append(Claim(f"{step['label']}: {'; '.join(parts)}.", "record", (step["list_id"],)))
            owners.append((activity["key"], step["step_key"]))
    return claims, owners


def _seen(facts: Facts) -> Seen:
    """Every list estimate_time returned this turn, by its id, with the step's values as the tool gave them."""
    seen = Seen()
    for found in facts.activities:
        for step in (found["answer"]["step_dates"] or {}).get("steps") or []:
            evidence_id = list_id(found, step["step_key"])
            seen.record(evidence_id, {"evidence_id": evidence_id, "public_from": facts.as_of.isoformat(),
                                      "source": {"tool": TOOL, "sources": [s["key"] for s in found["answer"]["sources"]]},
                                      **{key: step.get(key) for key in STEP_FIELDS}}, tool=TOOL)
    return seen


def _lists(facts: Facts, seen: Seen) -> dict[str, dict]:
    """Each step's list of comparable packages, by its id, as the evidence drawer shows a step's list: the step as
    estimate_time returned it this turn, with its comparable packages, and what the list's words need. The row keeps
    what the verifier saw, so the evidence pack names its source as it does any tool's."""
    found = {}
    for activity in facts.activities:
        answer = activity["answer"]
        dated = answer["step_dates"] or {}
        steps = dated.get("steps") or []
        for index, step in enumerate(steps):
            evidence_id = list_id(activity, step["step_key"])
            found[evidence_id] = {**(seen.get(evidence_id) or {}), "family": dated.get("family"), "step": step,
                                  "previous_key": steps[index - 1]["step_key"] if index else None,
                                  "basis": dated.get("basis"), "records_through": answer.get("records_through"),
                                  "sources": [source["dataset_name"] for source in answer.get("sources") or ()],
                                  "abstain_all": dated.get("abstain_all") is not None,
                                  "min_comparables": dated.get("min_comparables")}
    return found


def compose(facts: Facts) -> tuple[dict, Verdict]:
    """The draft, checked: every date and count matches what estimate_time returned for its list this turn."""
    labels = _labels()
    activities = [_activity(found, labels) for found in facts.activities]
    claims, owners = _claims(activities)
    seen = _seen(facts)
    checked = [check(index, claim, seen) for index, claim in enumerate(claims)]
    verdict = Verdict(tuple(checked), checks_run=(1, 2))
    removed = []
    by_key = {activity["key"]: activity for activity in activities}
    for sentence in verdict.removed:
        key, step_key = owners[sentence.index]
        step = next(step for step in by_key[key]["steps"] if step["step_key"] == step_key)
        step["middle"] = step["cautious"] = None
        step["removed"] = [reason.code for reason in sentence.reasons]
        removed.append({"key": key, "step_key": step_key, "reasons": [{"check": r.check, "code": r.code, "text": r.text}
                                                                      for r in sentence.reasons]})
    lists = [{"evidence_id": step["list_id"], "activity": activity["key"], "step_key": step["step_key"],
              "comparables_n": step["comparables_n"]}
             for activity in activities for step in activity["steps"]
             if any(step[choice] and step[choice]["planned_date"] for choice in CHOICES)]
    # Every count on the page opens its list, a step that is not dated too; only the lists a date rests on are the
    # draft's sources, which the bar counts and the evidence pack records.
    held = _lists(facts, seen)
    evidence = {step["list_id"]: {"id": step["list_id"], "kind": "steps", "tool": TOOL, "stratum": "How",
                                  "short_name": None, "row": held[step["list_id"]], "highlights": []}
                for activity in activities for step in activity["steps"]
                if step["list_id"] in held and (step["comparables_n"] or any(entry["evidence_id"] == step["list_id"]
                                                                              for entry in lists))}
    for activity in activities:  # each activity's "Steps dated", counted here after the verifier, never in the browser
        own = [step for step in activity["steps"] if not step["is_anchor"]]
        activity["counts"] = {"steps": len(own), "dated": {choice: sum(1 for step in own if step[choice] and
                                                                       step[choice]["planned_date"]) for choice in CHOICES}}
    dateable = [step for activity in activities for step in activity["steps"] if not step["is_anchor"]]
    counts = {"activities": len(activities), "steps": len(dateable),
              "dated": {choice: sum(1 for step in dateable if step[choice] and step[choice]["planned_date"])
                        for choice in CHOICES},
              "lists": len(lists), "no_family": sum(1 for activity in activities if not activity["family"])}
    content = {"subject": {**facts.subject, "as_of": facts.as_of.isoformat(), "activities": len(activities)},
               "notes": [], "activities": activities, "lists": lists, "evidence": evidence,
               "checks": {**verdict.counts(), "tools": list(TOOLS), "computed": True}, "removed": removed, "disagreements": [],
               "counts": counts,
               "min_comparables": int(load_thresholds().value("time_estimate.min_comparables"))}
    return content, verdict


def nothing_dated(content: dict) -> bool:
    return not any(content["counts"]["dated"].values())


# ── What the page and the files read ─────────────────────────────────────

def chosen(fields: dict) -> str:
    """The draft's one choice of dates: the author's, or cautious by default."""
    value = fields.get(CHOICE)
    return value if value in CHOICES else DEFAULT_CHOICE


def check_value(content: dict, row_key: str, name: str, value: str | None) -> str | None:
    """Why a value cannot be set, or None: only the choice, middle or cautious, for the whole draft."""
    if row_key != "" or name != "choice":
        return "unknown_field"
    return None if value in CHOICES else "unknown_value"


def view(content: dict, fields: dict, words: dict) -> dict:
    """What the page shows beside the draft's common parts: the choice, the activities, the counts and STEP's
    columns the file fills, copies and leaves empty."""
    columns = step_columns()
    return {"choice": chosen(fields), "activities": content["activities"], "counts": content["counts"],
            "min_comparables": content.get("min_comparables"), "left_to_people": columns.left_to_people(),
            "cautious_in10": Settings.read(load_thresholds()).in10("cautious"),
            "csv_columns": [column.name for column in columns.csv_columns()]}


def rows(draft: dict) -> tuple[list[str], list[list[str]]]:
    """The STEP rows: the header, then one row per activity in the file's order."""
    columns = step_columns().csv_columns()
    choice = draft[VIEW_KEY]["choice"]
    lines = []
    for activity in draft[VIEW_KEY]["activities"]:
        by_name = {step["step_name"]: step for step in activity["steps"]}
        line = []
        for column in columns:
            if column.fill == "left":
                line.append("")
            elif column.fill == "planned":
                step = by_name.get(column.step)
                value = step.get(choice) if step else None
                line.append(value["planned_date"] if value and value.get("planned_date") else "")
            elif column.field == DESCRIPTION:
                line.append(activity["description"] or "")
            elif column.field == REFERENCE:
                line.append("")
            else:
                line.append(activity["raw"].get(column.field) or "")
        lines.append(line)
    return [column.name for column in columns], lines


def step_rows_csv(draft: dict) -> bytes:
    header, lines = rows(draft)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    writer.writerows(lines)
    return ("﻿" + out.getvalue()).encode("utf-8")
