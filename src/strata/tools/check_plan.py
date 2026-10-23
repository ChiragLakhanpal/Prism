"""check_plan: Strata's fixed checks on every activity in one implementing agency's Procurement Plan.

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is
its adapter. It reads the plan's own record, as the plan reader wrote it (silver.plan_versions,
plan_rows, plan_step_delays, plan_listings and plan_data_notes), and the project's closing date
(gold.project), each only where it was public on or before the as-of date (ADR 0002). Its SQL is
in src/strata/tools/sql/check_plan/.

The checks, with their thresholds in config/thresholds.toml's [plan_check] (CLAUDE.md rule 9):

- Needs a look: no signed contract, and the planned completion (the first published planned date
  of the Contract Completion step) passed before the as-of date, for an activity estimated at
  completion_passed_min_estimated_usd or more, or with no estimate, so a missing amount never
  hides it. The reason gives the days left before closing.
- Watch: no signed contract and still pending days_before_closing days or fewer before the
  project's closing date, or after it. Not added when the planned completion already passed,
  because that reason gives the closing date and the days left.
- Watch: a signed amount at least actual_to_estimate_ratio times its estimate. The reason also
  gives how many days after its first published planned date the contract was signed.
- Data note: each note the plan reader wrote, and a check the tool could not run because the plan
  gives no planned completion date or no estimate (the activity then counts as not fully checked).

Every number a reason states is a value here, at its rounding: days are whole numbers, amounts
are text with two decimals, and the ratio is given exactly to two decimals and as the whole
number "about" rounds it to. The screen and the agent never compute them.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources

from strata.tools.registry import Call

CONTRACT_STATUSES = ("Signed", "Completed")  # STEP's Process Status once a contract is signed
PENDING_STATUSES = ("Pending Implementation", "Under Implementation", "Under Review", "Draft")
CHECKS = ("own_dates", "estimate", "closing_date")  # what the screen's method sentence names
CENTS, WHOLE = Decimal("0.01"), Decimal("1")


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "check_plan" / name).read_text()


def agency_id(name: str) -> str:
    """An implementing agency's id in links: its name in lower case, with hyphens between words."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# Values arrive typed from DuckDB and as text from the SQL warehouse, so each is read once here.

def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _money(value) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value)).quantize(CENTS)


def _whole(value) -> int | None:
    return None if value is None or value == "" else int(value)


def _flag(value) -> bool | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, bool) else str(value).lower() == "true"


def _iso(value: dt.date | None) -> str | None:
    return value.isoformat() if value else None


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _rows(call: Call, name: str, **params) -> list[dict]:
    result = call.engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


@dataclass(frozen=True)
class Thresholds:
    completion_passed_min_estimated_usd: Decimal
    days_before_closing: int
    actual_to_estimate_ratio: Decimal

    @classmethod
    def read(cls, call: Call) -> Thresholds:
        value = call.thresholds.value
        return cls(Decimal(str(value("plan_check.completion_passed_min_estimated_usd"))),
                   int(value("plan_check.days_before_closing")),
                   Decimal(str(value("plan_check.actual_to_estimate_ratio"))))

    def as_values(self) -> dict:
        return {"completion_passed_min_estimated_usd": str(self.completion_passed_min_estimated_usd.quantize(CENTS)),
                "days_before_closing": self.days_before_closing,
                "actual_to_estimate_ratio": str(self.actual_to_estimate_ratio)}


# ── The project and the plan ─────────────────────────────────────────────

def _project(call: Call, project_id: str) -> dict | None:
    found = _rows(call, "project.sql", project_id=project_id, as_of=call.as_of)
    if not found:
        return None
    row = found[0]
    record_on = _date(row["record_updated_on"]) or _date(row["public_from"])
    current = record_on <= call.as_of  # the record's values were public by the as-of date
    return {
        "evidence_id": f"strata.gold.project:{row['project_id']}",
        "public_from": _iso(record_on if current else _date(row["public_from"])),
        "project_id": row["project_id"],
        "project_name": row["project_name"],
        "status": row["status"] if current else None,
        "closing_date": _iso(_date(row["closing_date"])) if current else None,
        "record_date": _iso(record_on) if current else None,
        "days_to_close": ((_date(row["closing_date"]) - call.as_of).days
                          if current and row["closing_date"] else None),
    }


def _version(row: dict) -> dict:
    return {"document_id": row["document_id"], "implementing_agency": row["implementing_agency"],
            "plan_date": _date(row["plan_date"]), "disclosed_on": _date(row["disclosed_on"]),
            "public_from": _date(row["public_from"]), "text_url": row["text_url"], "pdf_url": row["pdf_url"]}


def _choose(call: Call, project_id: str, asked: str, plan_date: dt.date | None) -> tuple[dict | None, dict | None]:
    """The plan version to check, or the abstention that says why there is none."""
    versions = [_version(row) for row in _rows(call, "versions.sql", project_id=project_id)
                if row["implementing_agency"]]
    public = [version for version in versions if version["public_from"] <= call.as_of]
    wanted = asked.strip().lower()
    mine = [v for v in versions if v["implementing_agency"].lower() == wanted or agency_id(v["implementing_agency"]) == wanted]
    if not mine:
        agencies = {}
        for version in public:  # the latest public version of each agency, by name
            agencies[version["implementing_agency"]] = version["plan_date"]
        return None, {"reason": "no_plan_from_agency", "implementing_agency": asked,
                      "agencies": [{"implementing_agency": name, "agency_id": agency_id(name),
                                    "latest_plan_date": _iso(date)} for name, date in sorted(agencies.items())]}
    name = mine[0]["implementing_agency"]
    mine_public = [version for version in mine if version["public_from"] <= call.as_of]
    latest = mine_public[-1] if mine_public else None
    agency = {"implementing_agency": name, "agency_id": agency_id(name),
              "latest_plan_date": _iso(latest["plan_date"]) if latest else None}
    if plan_date is None:
        if latest is None:
            return None, {"reason": "no_plan_as_of", **agency}
        return {**latest, "is_latest": True}, None
    named = [version for version in mine if version["plan_date"] == plan_date]
    if not named:
        return None, {"reason": "version_not_found", "plan_date": _iso(plan_date), **agency}
    if named[-1]["public_from"] > call.as_of:
        return None, {"reason": "version_not_public", "plan_date": _iso(plan_date),
                      "public_from": _iso(named[-1]["public_from"]), **agency}
    return {**named[-1], "is_latest": named[-1] is latest}, None


def _plan(version: dict, project_id: str) -> dict:
    return {
        "evidence_id": f"strata.silver.plan_versions:{version['document_id']}",
        "public_from": _iso(version["public_from"]),
        "document_id": version["document_id"],
        "project_id": project_id,
        "implementing_agency": version["implementing_agency"],
        "agency_id": agency_id(version["implementing_agency"]),
        "plan_date": _iso(version["plan_date"]),
        "disclosed_on": _iso(version["disclosed_on"]),
        "is_latest": version["is_latest"],
        "pdf_url": version["pdf_url"],
        "text_url": version["text_url"],
    }


# ── The checks ───────────────────────────────────────────────────────────

def _reason(code: str, mark: str, evidence_ids: list[str], **values) -> dict:
    return {"code": code, "mark": mark, **values, "evidence_ids": evidence_ids}


def _ratio(actual: Decimal, estimated: Decimal) -> tuple[Decimal, int]:
    exact = actual / estimated
    return exact.quantize(CENTS, ROUND_HALF_UP), int(exact.quantize(WHOLE, ROUND_HALF_UP))


DATES = ("signed_on", "planned_signing_on", "planned_signing_plan_date", "planned_completion_on",
         "planned_completion_plan_date", "public_from")


def _typed(raw: dict) -> dict:
    """One activity's values from either engine, typed once: dates, amounts, whole numbers and a flag."""
    return {**raw, **{key: _date(raw[key]) for key in DATES},
            "estimated_amount_usd": _money(raw["estimated_amount_usd"]),
            "actual_amount_usd": _money(raw["actual_amount_usd"]),
            "days_late": _whole(raw["days_late"]), "pdf_page": _whole(raw["pdf_page"]),
            "first_listing_confirmed": _flag(raw["first_listing_confirmed"])}


def _signals(row: dict, cite: list[str], project: dict, limits: Thresholds,
             as_of: dt.date) -> tuple[list[dict], list[dict]]:
    """The signal reasons and the could-not-check notes for one typed activity."""
    signals, notes = [], []
    estimated, actual = row["estimated_amount_usd"], row["actual_amount_usd"]
    status = row["process_status"]
    contract = row["signed_on"] is not None or status in CONTRACT_STATUSES
    pending = not contract and (status is None or status in PENDING_STATUSES)
    closing, days_to_close = project["closing_date"], project["days_to_close"]
    near = cite + [project["evidence_id"]]

    completion_passed = False
    if pending and (estimated is None or estimated >= limits.completion_passed_min_estimated_usd):
        if row["planned_completion_on"] is None:
            notes.append(_reason("no_planned_date", "data_note", cite, step="Contract Completion"))
        elif row["planned_completion_on"] < as_of:
            completion_passed = True
            signals.append(_reason("completion_passed_no_contract", "needs_a_look", near if closing else cite,
                                   planned_completion_on=_iso(row["planned_completion_on"]),
                                   planned_completion_plan_date=_iso(row["planned_completion_plan_date"]),
                                   closing_date=closing, days_to_close=days_to_close))
    if pending and not completion_passed and closing and days_to_close <= limits.days_before_closing:
        code = ("pending_near_closing" if days_to_close > 0 else
                "pending_on_closing_day" if days_to_close == 0 else "pending_after_closing")
        signals.append(_reason(code, "watch", near, closing_date=closing, days_to_close=days_to_close))

    if contract and actual is not None and actual > 0:
        if not estimated:
            notes.append(_reason("no_estimate", "data_note", cite))
        else:
            exact, about = _ratio(actual, estimated)
            if actual / estimated >= limits.actual_to_estimate_ratio:
                late = row["days_late"] is not None and row["days_late"] > 0
                signals.append(_reason(
                    "signed_late_over_estimate" if late else "signed_over_estimate", "watch", cite,
                    signed_on=_iso(row["signed_on"]), actual_amount_usd=_text(actual),
                    estimated_amount_usd=_text(estimated), ratio=about, ratio_exact=str(exact),
                    days_late=row["days_late"] if late else None,
                    planned_signing_on=_iso(row["planned_signing_on"]) if late else None,
                    planned_signing_plan_date=_iso(row["planned_signing_plan_date"]) if late else None))
    return signals, notes


def _note(note: dict, cite: list[str]) -> dict:
    """A data note the plan reader wrote (silver.plan_data_notes), with the values its sentence needs."""
    if note["note"] == "method_differs_from_reference":
        return _reason(note["note"], "data_note", cite, reference_method_code=note["reference_method_code"],
                       reference_method=note["reference_method"], method=note["method"])
    return _reason(note["note"], "data_note", cite, process_status=note["process_status"],
                   actual_amount_usd=_text(_money(note["actual_amount_usd"])))


def _row(activity: dict, evidence_id: str, plan: dict, marks: list[dict]) -> dict:
    """One activity as the tool returns it: STEP's fields, the values behind its checks, and its marks."""
    estimated, actual = activity["estimated_amount_usd"], activity["actual_amount_usd"]
    return {
        "evidence_id": evidence_id,
        "public_from": _iso(activity["public_from"]),
        "source": {"document_type": "Procurement Plan", "project_id": plan["project_id"],
                   "implementing_agency": plan["implementing_agency"], "plan_date": plan["plan_date"],
                   "document_id": plan["document_id"], "pdf_page": activity["pdf_page"]},
        **{key: activity[key] for key in ("activity_reference_no", "section", "description", "review_type",
                                          "method", "market_approach")},
        "estimated_amount_usd": _text(estimated),
        "actual_amount_usd": _text(actual),
        "process_status": activity["process_status"],
        **{key: _iso(activity[key]) for key in ("signed_on", "planned_signing_on", "planned_signing_plan_date")},
        "days_late": activity["days_late"],
        **{key: _iso(activity[key]) for key in ("planned_completion_on", "planned_completion_plan_date")},
        "first_listing_confirmed": activity["first_listing_confirmed"],
        "actual_to_estimate": str(_ratio(actual, estimated)[0]) if actual and estimated else None,
        "marks": marks,
    }


def check_plan(call: Call, project_id: str, implementing_agency: str, plan_date: dt.date | None = None) -> dict:
    """Check every activity in the chosen plan version, as of call.as_of."""
    limits = Thresholds.read(call)
    project = _project(call, project_id)
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "plan": None, "project": project,
             "checks_run": [], "thresholds": limits.as_values(), "counts": None}
    if project is None:
        return {**empty, "abstention": {"reason": "unknown_project", "project_id": project_id}}
    version, abstention = _choose(call, project_id, implementing_agency, plan_date)
    if abstention:
        return {**empty, "abstention": abstention}
    plan = _plan(version, project_id)

    params = {"document_id": version["document_id"], "as_of": call.as_of}
    found = [_typed(raw) for raw in _rows(call, "activities.sql", **params)]
    if not found:
        return {**empty, "plan": plan, "abstention": {"reason": "no_activities", "plan_date": plan["plan_date"]}}
    notes = {}
    for note in _rows(call, "data_notes.sql", **params):
        notes.setdefault(note["activity_reference_no"], []).append(note)

    activities, not_used = [], {}
    for activity in found:
        evidence_id = f"strata.silver.plan_rows:{plan['document_id']}/{activity['activity_reference_no']}"
        signals, unchecked = _signals(activity, [evidence_id], project, limits, call.as_of)
        written = [_note(note, [evidence_id]) for note in notes.get(activity["activity_reference_no"], [])]
        marks = []
        if signals:
            strongest = "needs_a_look" if any(s["mark"] == "needs_a_look" for s in signals) else "watch"
            marks.append({"mark": strongest, "reasons": signals})
        if written or unchecked:
            marks.append({"mark": "data_note", "reasons": written + unchecked})
        for note in unchecked:
            not_used.setdefault(note["code"], []).append(evidence_id)
        activities.append(_row(activity, evidence_id, plan, marks))

    def count(mark: str) -> int:
        return sum(1 for row in activities if any(m["mark"] == mark for m in row["marks"]))

    partly = {evidence for ids in not_used.values() for evidence in ids}
    return {
        "rows": activities,
        "coverage": {"matched": len(activities), "used": len(activities) - len(partly),
                     "not_used": [{"reason": code, "count": len(ids), "evidence_ids": ids}
                                  for code, ids in not_used.items()]},
        "abstention": None,
        "plan": plan,
        "project": project,
        "checks_run": [check for check in CHECKS if check != "closing_date" or project["closing_date"]],
        "thresholds": limits.as_values(),
        "counts": {"activities": len(activities), "checked": len(activities) - len(partly),
                   "needs_a_look": count("needs_a_look"), "watch": count("watch"), "data_note": count("data_note"),
                   "unmarked": sum(1 for row in activities if not row["marks"])},
    }
