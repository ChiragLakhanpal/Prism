"""check_plan: Strata's fixed checks on every activity in one implementing agency's Procurement Plan.

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is
its adapter. It reads the plan's own record, as the plan reader wrote it (silver.plan_versions,
plan_rows, plan_step_delays, plan_listings and plan_data_notes), and the project's closing date
(gold.project), each only where it was public on or before the as-of date (ADR 0002). Its SQL is
in src/strata/tools/sql/check_plan/.

The checks, with their thresholds in config/thresholds.toml's [plan_check] (CLAUDE.md rule 9):

- Needs a look: no signed contract, and the planned completion passed before the as-of date, for
  an activity estimated at completion_passed_min_estimated_usd or more, or with no estimate, so a
  missing amount never hides it. The planned completion is the first published planned date of the
  Contract Completion step, or this version's own planned date when the first listing gives none or
  is not yet public (activities.sql). The reason gives the days left before closing.
- Watch: no signed contract and still pending days_before_closing days or fewer before the
  project's closing date, or after it. Not added when the planned completion already passed,
  because that reason gives the closing date and the days left.
- Watch: a signed amount at least actual_to_estimate_ratio times its estimate. The reason also
  gives how many days after its first published planned date the contract was signed.
- Data note: each note the plan reader wrote, and a check the tool could not run because the plan
  gives no planned completion date or no estimate (the activity then counts as not fully checked).
- Moved on since the plan (ticket 132): the plan still says the contract is not signed (a Process Status
  before signing and no Signed Contract date), and a contract record or an award notice says it was signed
  before a later plan of the agency replaced this version (at any time, for the agency's latest plan). That is a disagreement between the two records, defined once
  by the nightly job's detect_disagreements task (strata.knowledge.assertions), and the tool reads it
  (moved_on.sql) rather than working it out again. The row then gets none of the pending checks above, whose
  "no signed contract" the record contradicts; its reason gives the record's signing date and which record it
  is, and cites the plan row, the disagreement and the record. It is not a signal, and the counts give it
  apart (moved_on), so it is never counted as still pending.

A reason that measures from a first published planned date cites the plan row that gave it, beside
the row checked, so a later plan that moves the date never leaves the delay without its source.

The counts give every number the Check a plan screen states about the whole plan: the activities,
how many were checked fully and how many not, how many carry each mark (moved_on among them), how many carry a signal
(needs a look or watch, the rows a draft of review notes covers), and how many carry any mark or
none, so the screen never counts rows itself.

Every number a reason states is a value here, at its rounding: days are whole numbers, amounts
are text with two decimals, and the ratio is given exactly to two decimals and as the whole
number "about" rounds it to. Each row also gives its estimate in US$ millions to two decimals
(estimated_millions), which Home's briefing line writes (ticket 41). The screen and the agent never compute them. Each reason's code and
each abstention's reason is listed in the registry's [tools.check_plan.result], and the registry
refuses one it does not list.

The baseline (ticket 21): when a World Bank staff member saved one of this agency's versions as the
plan agreed at negotiations (strata.ops.plan_baselines), and saved it by the as-of date, the result
names it, and each reason that states a delay also gives the delay from the baseline's planned date
(the reason's baseline values): a signing before, on or after the baseline's date, a planned completion
that has or has not passed in the baseline, an activity the baseline did not list, or a step it gave no
date. A baseline adds a measure and never changes the marks, which come from the first published
planned date.

The call's view (staff, piu or public) is returned with the result and applied by the roles file's [views]
(ticket 40): the implementing agency view gets the baseline without who saved it, and the public view gets no
baseline and, on a project not yet closed on the as-of date, the data notes without any signal.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from importlib import resources

from strata.config import load_views
from strata.reader.repair import AS_READ as REFERENCE_AS_READ
from strata.tools.registry import Call

CONTRACT_STATUSES = ("Signed", "Completed")  # STEP's Process Status once a contract is signed
PENDING_STATUSES = ("Pending Implementation", "Under Implementation", "Under Review", "Draft")
CHECKS = ("own_dates", "estimate", "closing_date")  # what the screen's method sentence names
SIGNALS = ("needs_a_look", "watch")  # the marks that are signals; a data note describes the record
MOVED_ON = "moved_on"  # the mark of an activity the records have moved past (ticket 132); not a signal
# The record that says a moved-on activity's contract was signed, in the step tracker's words for the same records
# (src/strata/server/tracker.py, actual_source), by the form of its assertion.
RECORD_WORDS = {"contract_record": "contract_awards", "award_notice": "award_notice"}
SIGNING, COMPLETION = "Signed Contract", "Contract Completion"  # STEP's steps the delay reasons measure
CENTS, WHOLE = Decimal("0.01"), Decimal("1")


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "check_plan" / name).read_text()


def agency_id(name: str) -> str:
    """An implementing agency's id in links: its name in lower case, with hyphens between words."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def implementing_agencies(text: str | None) -> list[str]:
    """The agencies a projects API record names. The API joins them with a bare comma, and a comma
    followed by a space sits inside a name ("Ministry of Water, Sanitation and Irrigation")."""
    return [name.strip() for name in re.split(r",(?! )", text or "") if name.strip()]


# Every engine gives typed values (ticket 128); each is read once here, and a value written as text reads the same.

def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _money(value) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value)).quantize(CENTS)


def _whole(value) -> int | None:
    return None if value is None or value == "" else int(value)


def _boolean(value) -> bool | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, bool) else str(value).lower() == "true"


def _iso(value: dt.date | None) -> str | None:
    return value.isoformat() if value else None


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


MILLION = Decimal(1_000_000)


def millions(value: Decimal | None) -> str | None:
    """An amount in US$ millions to two decimals, with trailing zeros dropped, as Home's sentence writes it (ticket
    41): 1230000.00 is "1.23", 2000000.00 is "2" and 300000.00 is "0.3"."""
    if value is None:
        return None
    rounded = (value / MILLION).quantize(CENTS, ROUND_HALF_UP)
    text = format(rounded.normalize(), "f")
    return text if text != "-0" else "0"


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

def record_date(row: dict) -> dt.date:
    """The day a projects API record's values became public. The API changes a status, a closing
    date or the agencies in place, and gold keeps only the newest record, so its values count as
    public from the day that record was last updated, or the project's own public date when the
    record has no update date (ADR 0002). project.sql gives both columns."""
    return _date(row["record_updated_on"]) or _date(row["public_from"])


def record_is_current(row: dict, as_of: dt.date) -> bool:
    """Whether the record's values were public by the as-of date."""
    return record_date(row) <= as_of


def _project(call: Call, project_id: str) -> tuple[dict | None, list[str]]:
    """The project as the result gives it, and the implementing agencies its record names."""
    found = _rows(call, "project.sql", project_id=project_id, as_of=call.as_of)
    if not found:
        return None, []
    row = found[0]
    record_on = record_date(row)
    current = record_is_current(row, call.as_of)
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
    }, implementing_agencies(row["implementing_agency"]) if current else []


def _version(row: dict) -> dict:
    return {"document_id": row["document_id"], "implementing_agency": row["implementing_agency"],
            "plan_date": _date(row["plan_date"]), "disclosed_on": _date(row["disclosed_on"]),
            "public_from": _date(row["public_from"]), "text_url": row["text_url"], "pdf_url": row["pdf_url"]}


def _choose(call: Call, project_id: str, asked: str, plan_date: dt.date | None,
            record_agencies: list[str]) -> tuple[dict | None, dict | None]:
    """The plan version to check, or the abstention that says why there is none. record_agencies
    is the agencies the project record names, so an agency with no plan can still be named in full."""
    versions = [_version(row) for row in _rows(call, "versions.sql", project_id=project_id)
                if row["implementing_agency"]]
    # By date, so the latest is last even when an agency's name is spelled two ways.
    versions.sort(key=lambda version: (version["plan_date"], version["public_from"], version["document_id"]))
    public = [version for version in versions if version["public_from"] <= call.as_of]
    wanted = asked.strip().lower()
    mine = [v for v in versions if v["implementing_agency"].lower() == wanted or agency_id(v["implementing_agency"]) == wanted]
    if not mine:
        # The latest public version of each agency, by its id, so an agency whose name is spelled two ways is listed
        # once, as its latest plan spells it.
        agencies = {agency_id(version["implementing_agency"]): version for version in public}
        record = [name for name in record_agencies if name.lower() == wanted or agency_id(name) == wanted]
        return None, {"reason": "no_plan_from_agency", "implementing_agency": asked,
                      "agency_name": record[0] if record else None,
                      "agencies": [{"implementing_agency": version["implementing_agency"], "agency_id": key,
                                    "latest_plan_date": _iso(version["plan_date"])}
                                   for key, version in sorted(agencies.items())]}
    mine_public = [version for version in mine if version["public_from"] <= call.as_of]
    latest = mine_public[-1] if mine_public else None
    name = (latest or mine[-1])["implementing_agency"]  # as its latest plan spells it
    agency = {"implementing_agency": name, "agency_id": agency_id(name),
              "latest_plan_date": _iso(latest["plan_date"]) if latest else None}
    if plan_date is None:
        if latest is None:
            return None, {"reason": "no_plan_as_of", **agency}
        return {**latest, "is_latest": True}, None
    named = [version for version in mine if version["plan_date"] == plan_date]
    if not named:
        return None, {"reason": "version_not_found", "plan_date": _iso(plan_date), **agency}
    # Two documents can share a plan date, such as a plan and its re-issue; the one disclosed latest by the as-of
    # date is the version, so a later disclosure never hides one that was public then.
    named_public = [version for version in named if version["public_from"] <= call.as_of]
    if not named_public:
        return None, {"reason": "version_not_public", "plan_date": _iso(plan_date),
                      "public_from": _iso(named[0]["public_from"]), **agency}
    return {**named_public[-1], "is_latest": named_public[-1] is latest}, None


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


# ── The baseline ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Baseline:
    record: dict  # what the result's baseline field gives
    dates: dict[str, dict[str, dt.date | None]]  # each listed activity's planned dates, by step


@cache
def _views():
    return load_views()


def baseline_reads(project_id: str, agency: str, as_of: dt.date, view: str) -> list[tuple[str, dict]]:
    """The statement read_baseline runs, none when the view has no baseline, for a page that sends it in one batch
    with others (ticket 125)."""
    if not _views().allows(view, "baseline"):
        return []
    return [(_sql("baseline.sql"), {"project_id": project_id, "agency_id": agency, "as_of": as_of})]


def read_baseline(engine, project_id: str, agency: str, as_of: dt.date, view: str) -> Baseline | None:
    """The baseline saved for this agency's plans by the as-of date, as the view may see it (the roles file's [views]:
    baseline, and baseline_saver for who saved it), or None."""
    if not _views().allows(view, "baseline"):
        return None
    result = engine.run(_sql("baseline.sql"), {"project_id": project_id, "agency_id": agency, "as_of": as_of})
    rows = [dict(zip(result.columns, row)) for row in result.rows]
    if not rows:
        return None
    first = rows[0]
    dates: dict[str, dict[str, dt.date | None]] = {}
    for row in rows:
        if row["activity_reference_no"]:
            dates.setdefault(row["activity_reference_no"], {})[row["step"]] = _date(row["planned_on"])
    saved_on = _iso(_date(first["public_from"]))
    return Baseline({"plan_date": _iso(_date(first["plan_date"])), "document_id": first["document_id"],
                     "saved_by": first["saved_by_name"] if _views().allows(view, "baseline_saver") else None,
                     "saved_on": saved_on,
                     "evidence_id": f"strata.ops.plan_baselines:{project_id}/{agency}", "public_from": saved_on},
                    dates)


def _against(baseline: Baseline, reference: str, step: str) -> tuple[str | None, dt.date | None]:
    """Whether the baseline listed the activity, and its planned date for the step."""
    listed = baseline.dates.get(reference)
    if listed is None:
        return "not_in_baseline", None
    planned = listed.get(step)
    return (None, planned) if planned else ("no_date", None)


def _baseline_values(reason: dict, row: dict, baseline: Baseline, as_of: dt.date) -> dict | None:
    """The delay from the baseline for a reason that states a delay, or None for one that states none."""
    if reason["code"] == "signed_late_over_estimate":
        state, planned = _against(baseline, row["activity_reference_no"], SIGNING)
        days = (row["signed_on"] - planned).days if planned else None
        if planned:
            state = "late" if days > 0 else "early" if days < 0 else "on_date"
    elif reason["code"] == "completion_passed_no_contract":
        state, planned = _against(baseline, row["activity_reference_no"], COMPLETION)
        days = (as_of - planned).days if planned and planned < as_of else None
        if planned:
            state = "past" if planned < as_of else "ahead"
    else:
        return None
    return {"state": state, "planned_on": _iso(planned), "days": abs(days) if days else days,
            "plan_date": baseline.record["plan_date"]}


def _with_baseline(signals: list[dict], row: dict, baseline: Baseline | None, as_of: dt.date) -> list[dict]:
    if baseline is None:
        return signals
    for reason in signals:
        values = _baseline_values(reason, row, baseline, as_of)
        if values is not None:
            reason["baseline"] = values
            reason["evidence_ids"] = [*reason["evidence_ids"], baseline.record["evidence_id"]]
    return signals


# ── The checks ───────────────────────────────────────────────────────────

def _reason(code: str, mark: str, evidence_ids: list[str], **values) -> dict:
    return {"code": code, "mark": mark, **values, "evidence_ids": evidence_ids}


def _ratio(actual: Decimal, estimated: Decimal) -> tuple[Decimal, int]:
    exact = actual / estimated
    return exact.quantize(CENTS, ROUND_HALF_UP), int(exact.quantize(WHOLE, ROUND_HALF_UP))


DATES = ("signed_on", "planned_signing_on", "planned_signing_plan_date", "planned_completion_on",
         "planned_completion_plan_date", "public_from")


def _typed(raw: dict) -> dict:
    """One activity's values from either engine, typed once: dates, amounts, whole numbers and a true-or-false
    value."""
    return {**raw, **{key: _date(raw[key]) for key in DATES},
            "estimated_amount_usd": _money(raw["estimated_amount_usd"]),
            "actual_amount_usd": _money(raw["actual_amount_usd"]),
            "days_late": _whole(raw["days_late"]), "pdf_page": _whole(raw["pdf_page"]),
            "first_listing_confirmed": _boolean(raw["first_listing_confirmed"])}


def _first_listed(row: dict, document: str, cite: list[str]) -> list[str]:
    """The row cited, then the plan row that gave a delay's first published planned date when another plan gave it
    (ticket 09's verification round 2, V2). An upload's rows name no such document."""
    reference, first = row.get("activity_reference_no"), row.get(document)
    found = f"strata.silver.plan_rows:{first}/{reference}" if first and reference else None
    return cite + [found] if found and found not in cite else cite


def _signals(row: dict, cite: list[str], project: dict, limits: Thresholds,
             as_of: dt.date) -> tuple[list[dict], list[dict]]:
    """The signal reasons and the could-not-check notes for one typed activity."""
    signals, notes = [], []
    estimated, actual = row["estimated_amount_usd"], row["actual_amount_usd"]
    status = row["process_status"]
    contract = row["signed_on"] is not None or status in CONTRACT_STATUSES
    pending = not contract and (status is None or status in PENDING_STATUSES)
    closing, days_to_close = project["closing_date"], project["days_to_close"]
    completion_cite = _first_listed(row, "planned_completion_document", cite)
    near = cite + [project["evidence_id"]]

    completion_passed = False
    if pending and (estimated is None or estimated >= limits.completion_passed_min_estimated_usd):
        if row["planned_completion_on"] is None:
            notes.append(_reason("no_planned_date", "data_note", cite, step="Contract Completion"))
        elif row["planned_completion_on"] < as_of:
            completion_passed = True
            signals.append(_reason("completion_passed_no_contract", "needs_a_look",
                                   completion_cite + [project["evidence_id"]] if closing else completion_cite,
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
                    "signed_late_over_estimate" if late else "signed_over_estimate", "watch",
                    _first_listed(row, "planned_signing_document", cite) if late else cite,
                    signed_on=_iso(row["signed_on"]), actual_amount_usd=_text(actual),
                    estimated_amount_usd=_text(estimated), ratio=about, ratio_exact=str(exact),
                    days_late=row["days_late"] if late else None,
                    planned_signing_on=_iso(row["planned_signing_on"]) if late else None,
                    planned_signing_plan_date=_iso(row["planned_signing_plan_date"]) if late else None))
    return signals, notes


def moved_on_reads(document_id: str, as_of: dt.date) -> tuple[str, dict]:
    """The statement that reads the disagreements of one version's rows that say the records moved past them."""
    from strata.knowledge.assertions import PLAN_ROW, STATUS

    return _sql("moved_on.sql"), {"document_id": document_id, "as_of": as_of, "plan_row": PLAN_ROW, "status": STATUS,
                                  "package": "package"}


def _moved_on(call: Call, document_id: str) -> dict[str, dict]:
    """Each activity of the version the records moved past, by its reference: the disagreement to cite, a contract
    record's before an award notice's, then the earliest signing."""
    sql, params = moved_on_reads(document_id, call.as_of)
    result = call.engine.run(sql, params)
    found: dict[str, dict] = {}
    for row in sorted((dict(zip(result.columns, values)) for values in result.rows),
                      key=lambda row: (row["record_form"] != "contract_record", str(row["signed_on"]),
                                       row["disagreement_id"])):
        if row["record_form"] in RECORD_WORDS:
            found.setdefault(row["activity_reference_no"], row)
    return found


def _moved_on_reason(found: dict, activity: dict, cite: list[str]) -> dict:
    """The reason of an activity the records moved past: the record's signing date, which record it is, and the
    plan's own Process Status, citing the plan row, the disagreement and the record."""
    from strata.tools.get_disagreements import TABLE

    return _reason("moved_on_since_plan", MOVED_ON,
                   [*cite, f"{TABLE}:{found['disagreement_id']}", found["record_evidence_id"]],
                   process_status=activity["process_status"], signed_on=_iso(_date(found["signed_on"])),
                   record=RECORD_WORDS[found["record_form"]], disagreement_id=found["disagreement_id"])


def _note(note: dict, cite: list[str]) -> dict:
    """A data note the plan reader wrote (silver.plan_data_notes), with the values its sentence needs."""
    if note["note"] == "method_differs_from_reference":
        return _reason(note["note"], "data_note", cite, reference_method_code=note["reference_method_code"],
                       reference_method=note["reference_method"], method=note["method"])
    if note["note"] == "method_unknown":  # the plan's own words, which no method name in the registry matches
        return _reason(note["note"], "data_note", cite, method=note["method"])
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
        # A reference that breaks STEP's grammar and stays as the plan gives it (strata.reader.repair; ticket 131).
        "reference_as_read": activity.get("reference_repair") == REFERENCE_AS_READ,
        "estimated_amount_usd": _text(estimated),
        "estimated_millions": millions(estimated),
        "actual_amount_usd": _text(actual),
        "process_status": activity["process_status"],
        **{key: _iso(activity[key]) for key in ("signed_on", "planned_signing_on", "planned_signing_plan_date")},
        "days_late": activity["days_late"],
        **{key: _iso(activity[key]) for key in ("planned_completion_on", "planned_completion_plan_date")},
        "first_listing_confirmed": activity["first_listing_confirmed"],
        "actual_to_estimate": str(_ratio(actual, estimated)[0]) if actual and estimated else None,
        "marks": marks,
    }


# ── An implementing agency's upload (ticket 38) ──────────────────────────
#
# An upload is checked with the same checks, against the project's closing date. Its delay is measured from each
# step's first published planned date when a published plan of the project lists the activity, and from the
# upload's own planned date when none does. The upload's own values are its rows: the officer's Method, amounts
# and status, and each step's Actual date. Every row is cited as upload-row:{upload_id}:{position}, public on the
# day the upload was kept, and the reading's data notes become data notes on their rows.

UPLOAD_NOTES = ("unread_date", "unread_amount", "no_method", "duplicate_ref")


def upload_row_id(upload_id: str, position: int) -> str:
    """The evidence id of one activity of an upload."""
    return f"upload-row:{upload_id}:{position}"


def _upload_activity(row: Mapping, first: dict[tuple[str, str], dict], uploaded_on: dt.date) -> dict:
    """One upload row as the checks read a plan row: its STEP values, its own Signed Contract date, and the planned
    signing and completion dates its delay is measured from."""
    fields, steps = row.get("fields") or {}, row.get("steps") or {}
    reference = row.get("reference")

    def own(step: str, head: str) -> dt.date | None:
        return _date((steps.get(step) or {}).get(head))

    def measured_from(step: str) -> tuple[dt.date | None, dt.date | None]:
        published = first.get((reference, step)) if reference else None
        if published and published["first_planned_on"]:
            return _date(published["first_planned_on"]), _date(published["first_planned_plan_date"])
        planned = own(step, "planned")
        return planned, uploaded_on if planned else None

    signed_on = own(SIGNING, "actual")
    signing_on, signing_plan = measured_from(SIGNING)
    completion_on, completion_plan = measured_from(COMPLETION)
    listed = bool(reference) and any(key[0] == reference for key in first)
    return {"activity_reference_no": reference, "section": row.get("section"), "description": row.get("description"),
            "review_type": fields.get("review_type"), "method": fields.get("method"),
            "market_approach": fields.get("market_approach"),
            "estimated_amount_usd": _money(fields.get("estimated_amount_usd")),
            "actual_amount_usd": _money(fields.get("actual_amount_usd")), "process_status": fields.get("process_status"),
            "pdf_page": None, "signed_on": signed_on, "planned_signing_on": signing_on,
            "planned_signing_plan_date": signing_plan,
            "days_late": (signed_on - signing_on).days if signed_on and signing_on else None,
            "planned_completion_on": completion_on, "planned_completion_plan_date": completion_plan,
            "first_listing_confirmed": (any(first[key]["first_listing_confirmed"] for key in first if key[0] == reference)
                                        if listed else None),
            "public_from": uploaded_on, "position": int(row["position"]), "listed": listed}


@cache
def reference_methods() -> dict[str, str]:
    """The reference codes whose method the plan reader's method_differs_from_reference note knows, read from that
    note's one definition (src/strata/lakehouse/sql/plans/plan_data_notes.sql), so an upload gets the same note."""
    text = (resources.files("strata.lakehouse") / "sql" / "plans" / "plan_data_notes.sql").read_text()
    return dict(re.findall(r"\('([A-Z]+)', '([^']+)'\)", text))


def _upload_notes(row: Mapping, activity: dict, cite: list[str]) -> list[dict]:
    """The reading's data notes on one row, then the plan reader's two notes as it writes them on a published plan
    (plan_data_notes.sql): a reference that ends in another method's code, and a signed or completed contract whose
    actual amount reads 0.00."""
    notes = []
    for note in row.get("notes") or []:
        values = {key: value for key, value in note.items() if key != "code"}
        notes.append(_reason(note["code"], "data_note", cite, **values))
    reference, method = activity["activity_reference_no"], activity["method"]
    code = re.search(r"-([A-Z]+)$", reference).group(1) if reference and re.search(r"-([A-Z]+)$", reference) else None
    if method and code in reference_methods() and reference_methods()[code] != method:
        notes.append(_reason("method_differs_from_reference", "data_note", cite, reference_method_code=code,
                             reference_method=reference_methods()[code], method=method))
    if activity["process_status"] in CONTRACT_STATUSES and activity["actual_amount_usd"] == Decimal("0.00"):
        notes.append(_reason("actual_amount_zero", "data_note", cite, process_status=activity["process_status"],
                             actual_amount_usd=_text(activity["actual_amount_usd"])))
    return notes


def check_upload(call: Call, upload: Mapping, project: dict, limits: Thresholds) -> dict:
    """Check every activity of an upload, in the order of the officer's file."""
    uploaded_on = _date(upload["uploaded_on"])
    agency = upload["implementing_agency"]
    first = {(row["activity_reference_no"], row["step"]): row
             for row in _rows(call, "upload_first_dates.sql", project_id=upload["project_id"], as_of=call.as_of)}
    plan = {"evidence_id": f"strata.ops.uploads:{upload['upload_id']}", "public_from": _iso(uploaded_on),
            "document_id": upload["upload_id"], "project_id": upload["project_id"], "implementing_agency": agency,
            "agency_id": agency_id(agency), "plan_date": _iso(uploaded_on), "disclosed_on": None, "is_latest": None,
            "pdf_url": None, "text_url": None, "upload_id": upload["upload_id"]}
    activities, not_used = [], {}
    for row in upload["rows"]:
        evidence_id = upload_row_id(upload["upload_id"], int(row["position"]))
        activity = _upload_activity(row, first, uploaded_on)
        signals, unchecked = _signals(activity, [evidence_id], project, limits, call.as_of)
        written = _upload_notes(row, activity, [evidence_id])
        marks = []
        if signals:
            strongest = "needs_a_look" if any(s["mark"] == "needs_a_look" for s in signals) else "watch"
            marks.append({"mark": strongest, "reasons": signals})
        if written or unchecked:
            marks.append({"mark": "data_note", "reasons": written + unchecked})
        for note in unchecked:
            not_used.setdefault(note["code"], []).append(evidence_id)
        shown = _row(activity, evidence_id, plan, marks)
        shown["source"] = {**shown["source"], "document_type": "Upload"}
        activities.append({**shown, "position": activity["position"], "listed": activity["listed"]})
    return _result(activities, not_used, plan, project, limits, None)


def _result(activities: list[dict], not_used: dict, plan: dict, project: dict, limits: Thresholds,
            baseline: dict | None, withheld: str | None = None) -> dict:
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
        "baseline": baseline,
        "withheld": withheld,
        "counts": {"activities": len(activities), "checked": len(activities) - len(partly),
                   "not_fully_checked": len(partly),
                   "needs_a_look": count("needs_a_look"), "watch": count("watch"), "moved_on": count(MOVED_ON),
                   "data_note": count("data_note"),
                   "signal": sum(1 for row in activities if any(m["mark"] in SIGNALS for m in row["marks"])),
                   "marked": sum(1 for row in activities if row["marks"]),
                   "unmarked": sum(1 for row in activities if not row["marks"])},
    }


def check_plan(call: Call, project_id: str, implementing_agency: str, plan_date: dt.date | None = None,
               upload_id: str | None = None) -> dict:
    """Check every activity in the chosen plan version, or in the viewer's team's upload, as of call.as_of."""
    limits = Thresholds.read(call)
    project, record_agencies = _project(call, project_id)
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "plan": None, "project": project,
             "checks_run": [], "thresholds": limits.as_values(), "counts": None, "baseline": None, "withheld": None}
    if upload_id is not None:
        # The same answer for an upload that does not exist, belongs to another team, or is of another project or
        # agency, so a call reveals nothing about another team's uploads.
        upload = call.uploads(upload_id) if call.uploads is not None else None
        wanted = implementing_agency.strip().lower()
        if (upload is None or project is None or upload["project_id"] != project_id
                or wanted not in (upload["implementing_agency"].lower(), agency_id(upload["implementing_agency"]))):
            return {**empty, "project": None, "abstention": {"reason": "unknown_upload"}}
        return check_upload(call, upload, project, limits)
    if project is None:
        return {**empty, "abstention": {"reason": "unknown_project", "project_id": project_id}}
    version, abstention = _choose(call, project_id, implementing_agency, plan_date, record_agencies)
    if abstention:
        return {**empty, "abstention": abstention}
    plan = _plan(version, project_id)
    baseline = read_baseline(call.engine, project_id, plan["agency_id"], call.as_of, call.view)
    empty["baseline"] = baseline.record if baseline else None

    params = {"document_id": version["document_id"], "as_of": call.as_of}
    found = [_typed(raw) for raw in _rows(call, "activities.sql", **params)]
    if not found:
        return {**empty, "plan": plan, "abstention": {"reason": "no_activities", "plan_date": plan["plan_date"]}}
    notes = {}
    for note in _rows(call, "data_notes.sql", **params):
        notes.setdefault(note["activity_reference_no"], []).append(note)

    # The public view shows no signal on a project still under way, and keeps the data notes, which describe the
    # published record, not the progress of a live process (the roles file's [views], ticket 40; the 10 brief, 6).
    from strata.tools.withheld import WITHHELD, withheld
    hidden = withheld(call, "signals_on_active_projects", project_id)
    # An activity the records moved past is a disagreement between two records, which the same view holds back on a
    # project still under way; its pending checks stay off, since the records say its contract was signed.
    moved = _moved_on(call, version["document_id"])
    disagreements_hidden = bool(moved) and withheld(call, "disagreements_on_active_projects", project_id)
    activities, not_used = [], {}
    for activity in found:
        evidence_id = f"strata.silver.plan_rows:{plan['document_id']}/{activity['activity_reference_no']}"
        passed = moved.get(activity["activity_reference_no"])
        if passed is None:
            signals, unchecked = _signals(activity, [evidence_id], project, limits, call.as_of)
            signals = [] if hidden else _with_baseline(signals, activity, baseline, call.as_of)
        else:
            signals, unchecked = [], []
        written = [_note(note, [evidence_id]) for note in notes.get(activity["activity_reference_no"], [])]
        marks = []
        if signals:
            strongest = "needs_a_look" if any(s["mark"] == "needs_a_look" for s in signals) else "watch"
            marks.append({"mark": strongest, "reasons": signals})
        if passed is not None and not disagreements_hidden:
            marks.append({"mark": MOVED_ON, "reasons": [_moved_on_reason(passed, activity, [evidence_id])]})
        if written or unchecked:
            marks.append({"mark": "data_note", "reasons": written + unchecked})
        for note in unchecked:
            not_used.setdefault(note["code"], []).append(evidence_id)
        # position and listed describe an upload's rows; a published plan's rows have neither.
        activities.append({**_row(activity, evidence_id, plan, marks), "position": None, "listed": None})
    return _result(activities, not_used, plan, project, limits, empty["baseline"], WITHHELD if hidden else None)
