"""agency_track_record: how an implementing agency's past packages went against its plans (ticket 36).

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its adapter. It
chooses one of the agency's Procurement Plan versions as check_plan does (the latest public one, or the version the
call names by its date) and reads each of its activities' Signed Contract step from strata.silver.plan_step_delays,
the one definition of delay (src/strata/lakehouse/sql/plans/plan_step_delays.sql). It never measures delay itself.

A package counts (n) when its first published plan gave a date for signing and the version shows the contract
signed. Of those, it is signed by the plan's date when its delay is zero or less, and signed late when its delay is
more than [agency_track_record].late_days. A package not signed whose planned date has passed is open past its
date; one whose date has not come is not due yet. The middle delay of the counted packages is given only from
[agency_track_record].min_packages_for_middle of them (DESIGN.md section 7, rule 15); below that it is null and the
answer gives counts only.

Signed means what the plan shows: STEP's Actual date for the Signed Contract step (signed_from is "plan"). The
awards dataset can disagree: on the fixture, the October 9, 2026 plan shows KE-NWWDA-541055-CW-RFB and
KE-NWWDA-541062-CW-RFQ unsigned, and the awards dataset holds a signed contract for each. Each such package comes
back in differs_from_awards with its contract, so an answer says which source it counted and names the other.

The counts come back in the result's summary, one citable record (CLAUDE.md rule 1). Each row is one activity,
cited by its plan row's evidence id, the record check_plan cites, so the evidence drawer opens it.
"""

from __future__ import annotations

import datetime as dt
from importlib import resources

from strata.tools import check_plan
from strata.tools.registry import Call

SIGNED_FROM = "plan"


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "agency_track_record" / f"{name}.sql").read_text()


def _rows(call: Call, name: str, **params) -> list[dict]:
    result = call.engine.run(_sql(name), {"as_of": call.as_of, **params})
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def _iso(value) -> str | None:
    day = check_plan._date(value)
    return day.isoformat() if day else None


def _state(row: dict, late_days: int, as_of: dt.date) -> str:
    planned, signed = check_plan._date(row["first_planned_on"]), check_plan._date(row["actual_on"])
    if planned is None:
        return "no_planned_date"
    if signed is None:
        return "open_past_date" if planned < as_of else "not_due"
    delay = check_plan._whole(row["delay_days"])
    return "signed_by_plan" if delay <= 0 else "signed_late" if delay > late_days else "signed_within_late_days"


def _middle(delays: list[int]) -> int:
    """The middle delay: the lower of the two middle values when the count is even, so it is one package's delay."""
    ordered = sorted(delays)
    return ordered[(len(ordered) - 1) // 2]


def agency_track_record(call: Call, project_id: str, implementing_agency: str, plan_date: dt.date | None = None) -> dict:
    late_days = int(call.thresholds.value("agency_track_record.late_days"))
    minimum = int(call.thresholds.value("agency_track_record.min_packages_for_middle"))
    project, record_agencies = check_plan._project(call, project_id)
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "agency": None, "plan": None,
             "signed_from": SIGNED_FROM, "differs_from_awards": [], "from_date": None, "to_date": None,
             "counts": None}
    if project is None:
        return {**empty, "abstention": {"reason": "unknown_project", "project_id": project_id}}
    version, abstention = check_plan._choose(call, project_id, implementing_agency, plan_date, record_agencies)
    if abstention:
        return {**empty, "abstention": abstention}
    plan = check_plan._plan(version, project_id)
    agency = {"agency_id": plan["agency_id"], "agency_name": plan["implementing_agency"]}
    found = _rows(call, "packages", document_id=plan["document_id"])
    if not found:
        return {**empty, "agency": agency, "plan": plan, "abstention": {"reason": "no_activities",
                                                                        "plan_date": plan["plan_date"]}}
    refs = [row["activity_reference_no"] for row in found]
    awards: dict[str, dict] = {}
    for contract in _rows(call, "awards", refs=",".join(refs)):
        awards.setdefault(contract["step_reference"], contract)  # the earliest signing first

    rows, not_used, differs = [], {}, []
    for raw in found:
        reference = raw["activity_reference_no"]
        evidence_id = f"strata.silver.plan_rows:{plan['document_id']}/{reference}"
        state = _state(raw, late_days, call.as_of)
        award = awards.get(reference)
        row = {"evidence_id": evidence_id, "public_from": _iso(raw["public_from"]),
               "source": {"document_type": "Procurement Plan", "project_id": project_id,
                          "implementing_agency": plan["implementing_agency"], "plan_date": plan["plan_date"],
                          "document_id": plan["document_id"], "pdf_page": check_plan._whole(raw["pdf_page"])},
               "step_reference": reference, "description": raw["description"], "section": raw["section"],
               "method": raw["method"], "process_status": raw["process_status"],
               "first_planned_on": _iso(raw["first_planned_on"]),
               "first_planned_plan_date": _iso(raw["first_planned_plan_date"]),
               "first_listing_confirmed": check_plan._boolean(raw["first_listing_confirmed"]),
               "signed_on": _iso(raw["actual_on"]), "delay_days": check_plan._whole(raw["delay_days"]), "state": state,
               "awards_signed_on": _iso(award["contract_signing_date"]) if award else None,
               "awards_evidence_id": f"strata.gold.contract:{award['contract_id']}" if award else None}
        rows.append(row)
        if state in ("open_past_date", "not_due"):
            not_used.setdefault("not_signed", []).append(evidence_id)
        elif state == "no_planned_date":
            not_used.setdefault("no_planned_date", []).append(evidence_id)
        if row["signed_on"] is None and award:
            differs.append({"step_reference": reference, "process_status": raw["process_status"],
                            "awards_signed_on": row["awards_signed_on"], "evidence_id": row["awards_evidence_id"],
                            "plan_evidence_id": evidence_id})

    counted = [row for row in rows if row["state"].startswith("signed")]
    delays = [row["delay_days"] for row in counted]
    planned = [row["first_planned_plan_date"] for row in counted if row["first_planned_plan_date"]]
    counts = {"activities": len(rows), "n": len(counted),
              "signed_by_plan": sum(1 for row in counted if row["state"] == "signed_by_plan"),
              "signed_late": sum(1 for row in counted if row["state"] == "signed_late"),
              "open_past_date": sum(1 for row in rows if row["state"] == "open_past_date"),
              "not_due": sum(1 for row in rows if row["state"] == "not_due"),
              "late_days": late_days, "min_packages_for_middle": minimum,
              "middle_delay_days": _middle(delays) if len(counted) >= minimum else None,
              "differs_from_awards": len(differs)}
    return {
        "rows": rows,
        "coverage": {"matched": len(rows), "used": len(counted),
                     "not_used": [{"reason": reason, "count": len(ids), "evidence_ids": ids}
                                  for reason, ids in not_used.items()]},
        "abstention": None,
        "agency": agency,
        "plan": plan,
        "signed_from": SIGNED_FROM,
        "differs_from_awards": differs,
        "from_date": min(planned) if planned else None,
        "to_date": plan["plan_date"],
        "counts": counts,
    }
