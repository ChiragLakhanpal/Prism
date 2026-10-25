"""project_signals: Strata's fixed signals for one project, a reason to look and never a finding (ticket 37).

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its
adapter. It runs seven fixed checks on the project's public records, each only on what was public on
or before the as-of date (ADR 0002), with every threshold from config/thresholds.toml (CLAUDE.md
rule 9): [signals], and [plan_check] for the two checks the plan check already makes.

The checks, in the order the screens list them (CHECKS):

- completion_passed: an activity in an implementing agency's latest Procurement Plan passed its
  planned completion with no signed contract: check_plan's completion_passed_no_contract reason.
- above_estimate: a contract was signed far above its estimate: check_plan's signed_over_estimate or
  signed_late_over_estimate reason, at [plan_check].actual_to_estimate_ratio.
- late_direct: a direct-selection activity of late_direct_min_usd or more first appears in a plan
  published late_direct_months or fewer months before the closing date, and the same agency's previous
  plan was read and does not list it.
- closing_moves: the loan history shows the closing date moved closing_moves_min times or more,
  counted per project (gold.project_closing_date), so two credits that move together count once.
- restructured: the latest ISR's restructuring history lists a restructuring of a level in
  restructured_levels dated in the last restructured_months months.
- isr_lowered: the latest ISR rated progress towards the development objective, or overall
  implementation progress, lower than the ISR before it, on isr_rating_scale.
- disbursement: less than disbursement_max_share of the money committed and not canceled was paid out
  (disbursed divided by disbursed plus undisbursed), with disbursement_months or fewer months left.

The plan checks read each agency's latest plan only when it is dated within plan_months of the as-of
date. One signal is one check that fired, with a count of what it fired on; it is strong when its key is
in strong, or its count reaches its strong_from. The status: needs_a_look with look_min signals or one
strong one, watch with fewer and none strong, no_signals when the checks that ran found nothing, and
not_checked when no check could run (an abstention, no_records). A closed, pipeline or dropped project
is not checked (not_active), since the checks look for reasons to look during implementation.

Each row is one signal: the check, whether it is strong, its count, the values its line states and the
records it rests on (items), each record cited by its own evidence id and public date, so a citation
marker opens the record and an answer can cite it. Every number a line states is a value here, at its
rounding: a ratio as the whole number "about" rounds it to, an amount in US$ millions to one decimal.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources

from strata.config import load_project_page
from strata.tools import check_plan as plan_check
from strata.tools.registry import Call

CHECKS = ("completion_passed", "above_estimate", "late_direct", "closing_moves", "restructured", "isr_lowered",
          "disbursement")
PLAN_CHECKS = ("completion_passed", "above_estimate", "late_direct")
# What each check reads, for the reason it gives when it cannot run (the registry's reasons).
NEEDS = {"completion_passed": "plans", "above_estimate": "plans", "late_direct": "plans",
         "closing_moves": "loan_history", "restructured": "isr", "isr_lowered": "isr", "disbursement": "loans"}
COMPLETION = ("completion_passed_no_contract",)
ABOVE = ("signed_over_estimate", "signed_late_over_estimate")
ACTIVE, CLOSED = "active", "closed"
STATUS_KIND = {"Active": ACTIVE, "Closed": CLOSED, "Pipeline": "pipeline", "Dropped": "dropped"}
RESTRUCTURING = re.compile(r"Restructuring Level (\d+) Approved on (\d{2})-([A-Za-z]{3})-(\d{4})")
MONTHS = {name: number for number, name in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
MILLION, TENTH, CENT = Decimal(1_000_000), Decimal("0.1"), Decimal("0.01")
SOURCES = {"plans": "Procurement Plan", "loan_history": "loan_history", "isr": "isr", "loans": "loans"}


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "project_signals" / name).read_text()


def _rows(call: Call, name: str, **params) -> list[dict]:
    result = call.engine.run(_sql(name), {**params, "as_of": call.as_of})
    return [dict(zip(result.columns, row)) for row in result.rows]


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _iso(value) -> str | None:
    day = _date(value)
    return day.isoformat() if day else None


def _money(value) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value))


def months_before(day: dt.date, months: int) -> dt.date:
    """The same day of the month, this many months earlier, or the month's last day when it has none."""
    month = day.month - 1 - months
    year, month = day.year + month // 12, month % 12 + 1
    for last in (31, 30, 29, 28):
        try:
            return dt.date(year, month, min(day.day, last))
        except ValueError:
            continue
    raise ValueError(day)


def months_after(day: dt.date, months: int) -> dt.date:
    return months_before(day, -months)


def whole_months(start: dt.date, end: dt.date) -> int:
    """The whole months from start to end: 9 from January 22 to October 31."""
    months = (end.year - start.year) * 12 + end.month - start.month
    return months - 1 if end.day < start.day else months


def millions(usd: Decimal) -> str:
    """US dollars in millions to one decimal, as a sentence writes them: 2600000.00 is 2.6."""
    return f"{(usd / MILLION).quantize(TENTH, ROUND_HALF_UP):,}"


@dataclass(frozen=True)
class Limits:
    look_min: int
    strong: tuple[str, ...]
    strong_from: dict[str, int]
    plan_months: int
    late_direct_methods: tuple[str, ...]
    late_direct_min_usd: Decimal
    late_direct_months: int
    closing_moves_min: int
    restructured_levels: tuple[int, ...]
    restructured_months: int
    rating_scale: tuple[str, ...]
    disbursement_max_share: Decimal
    disbursement_months: int

    @classmethod
    def read(cls, call: Call) -> Limits:
        value = call.thresholds.value
        return cls(int(value("signals.look_min")), tuple(value("signals.strong")),
                   {key: int(value(f"signals.{key}_strong_from")) for key in PLAN_CHECKS},
                   int(value("signals.plan_months")), tuple(value("signals.late_direct_methods")),
                   Decimal(str(value("signals.late_direct_min_usd"))), int(value("signals.late_direct_months")),
                   int(value("signals.closing_moves_min")), tuple(int(level) for level in value("signals.restructured_levels")),
                   int(value("signals.restructured_months")), tuple(value("signals.isr_rating_scale")),
                   Decimal(str(value("signals.disbursement_max_share"))), int(value("signals.disbursement_months")))

    def as_values(self, call: Call) -> dict:
        """The values the checks used, for the copy that defines each status and check."""
        plan = plan_check.Thresholds.read(call).as_values()
        return {"look_min": self.look_min, "strong": list(self.strong), "strong_from": dict(self.strong_from),
                "plan_months": self.plan_months,
                "completion_passed_min_estimated_usd": plan["completion_passed_min_estimated_usd"],
                "completion_passed_min_millions": millions(Decimal(plan["completion_passed_min_estimated_usd"])),
                "actual_to_estimate_ratio": plan["actual_to_estimate_ratio"],
                "late_direct_min_usd": str(self.late_direct_min_usd.quantize(CENT)),
                "late_direct_min_millions": millions(self.late_direct_min_usd),
                "late_direct_months": self.late_direct_months, "closing_moves_min": self.closing_moves_min,
                "restructured_levels": list(self.restructured_levels), "restructured_months": self.restructured_months,
                "disbursement_max_percent": int((self.disbursement_max_share * 100).quantize(Decimal(1), ROUND_HALF_UP)),
                "disbursement_months": self.disbursement_months}


def thresholds_used(thresholds) -> dict:
    """The values the checks use, read from the thresholds file without running them, for a page with no
    project to check (Following when you follow none)."""
    call = Call(None, None, "staff", dt.date.min, thresholds)
    return Limits.read(call).as_values(call)


# ── The project ──────────────────────────────────────────────────────────

def _project(call: Call, project_id: str, history: list[dict]) -> dict | None:
    """The project as of the date: its status and closing date from the projects API's record once that record
    was public, and before then its closing date from the loan history, the project counting as active while
    that date was still ahead."""
    found = _rows(call, "project.sql", project_id=project_id)
    if not found:
        return None
    row = found[0]
    current = plan_check.record_is_current(row, call.as_of)
    if current:
        status, closing = STATUS_KIND.get(row["status"] or "", None), _date(row["closing_date"])
        record_on = plan_check.record_date(row)
    else:
        closing = _date(history[-1]["closing_date"]) if history else None
        status = None if closing is None else ACTIVE if closing >= call.as_of else CLOSED
        record_on = _date(row["public_from"])
    if status == ACTIVE and closing is not None:
        closing_kind = "closes" if closing >= call.as_of else "past_closing"
    else:
        closing_kind = status
    return {"evidence_id": f"strata.gold.project:{row['project_id']}", "public_from": _iso(record_on),
            "project_id": row["project_id"], "project_name": row["project_name"], "country": row["country"],
            "status": status, "status_as_written": row["status"] if current else None,
            "closing_date": _iso(closing), "closing_kind": closing_kind,
            "days_to_close": (closing - call.as_of).days if closing else None}


# ── The plan checks ──────────────────────────────────────────────────────

def _plan_checks(call: Call, project: dict, limits: Limits) -> tuple[dict[str, list[dict]] | None, str | None, list[dict]]:
    """What the three plan checks found on each agency's latest plan dated within plan_months, the reason none
    could run (no_plans, no_recent_plans), and the plans read."""
    latest = _rows(call, "latest_plans.sql", project_id=project["project_id"])
    if not latest:
        return None, "no_plans", []
    since = months_before(call.as_of, limits.plan_months)
    recent = [row for row in latest if _date(row["plan_date"]) >= since]
    plans = [{"implementing_agency": row["implementing_agency"], "agency_id": plan_check.agency_id(row["implementing_agency"]),
              "document_id": row["document_id"], "plan_date": _iso(row["plan_date"]),
              "in_scope": _date(row["plan_date"]) >= since} for row in latest]
    if not recent:
        return None, "no_recent_plans", plans
    firsts = {row["activity_reference_no"]: row for row in _rows(call, "first_listings.sql", project_id=project["project_id"])}
    closing = _date(project["closing_date"])
    found: dict[str, list[dict]] = {key: [] for key in PLAN_CHECKS}
    for plan in recent:
        result = plan_check.check_plan(call, project["project_id"], plan["implementing_agency"])
        for row in result["rows"]:
            reasons = {reason["code"]: reason for mark in row["marks"] for reason in mark["reasons"]}
            if any(code in reasons for code in COMPLETION):
                found["completion_passed"].append(row)
            above = next((reasons[code] for code in ABOVE if code in reasons), None)
            if above is not None:
                found["above_estimate"].append({**row, "ratio": above["ratio"], "ratio_exact": above["ratio_exact"]})
            late = _late_direct(row, firsts.get(row["activity_reference_no"]), closing, limits)
            if late is not None:
                found["late_direct"].append(late)
    return found, None, plans


def _late_direct(row: dict, first: dict | None, closing: dt.date | None, limits: Limits) -> dict | None:
    """The activity as the late direct selection check reports it, or None when it is not one."""
    estimated = _money(row["estimated_amount_usd"])
    if (row["method"] not in limits.late_direct_methods or estimated is None or estimated < limits.late_direct_min_usd
            or first is None or not first["previous_document_id"] or closing is None):
        return None
    first_on = _date(first["plan_date"])
    if first_on < months_before(closing, limits.late_direct_months):
        return None
    return {**row, "amount_millions": millions(estimated), "first_plan_date": _iso(first_on),
            "first_document_id": first["document_id"]}


# ── The checks on the loan history, the ISRs and the loans ───────────────

def _history_item(project_id: str, row: dict) -> dict:
    reported = _iso(row["reported_on"])
    return {"evidence_id": f"strata.gold.project_closing_date:{project_id}/{reported}", "public_from": _iso(row["public_from"]),
            "closing_date": _iso(row["closing_date"]), "previous_closing_date": _iso(row["previous_closing_date"]),
            "reported_on": reported}


def _closing_moves(project_id: str, history: list[dict]) -> list[dict]:
    return [_history_item(project_id, row) for row in history[1:]]


def _latest_isr(ratings: list[dict]) -> list[dict]:
    return [row for row in ratings if row["document_id"] == ratings[0]["document_id"]] if ratings else []


def _rating_item(project_id: str, row: dict, key: str) -> dict:
    return {"evidence_id": f"strata.silver.isr_ratings:{project_id}/{row['document_id']}/{key}",
            "public_from": _iso(row["public_from"]), "document_id": row["document_id"], "rating_key": key,
            "rating_name": row["rating_name"], "current_rating": row["current_rating"],
            "previous_rating": row["previous_rating"], "isr_date": _iso(row["isr_date"]),
            "sequence": None if row["sequence"] is None else int(row["sequence"])}


def _lowered(project_id: str, latest: list[dict], limits: Limits) -> list[dict]:
    """The ratings the latest ISR lowered from the ISR before it, on the rating scale."""
    rated = load_project_page().isr_ratings
    scale = {name: place for place, name in enumerate(limits.rating_scale)}
    lowered = []
    for row in latest:
        key = rated.get(row["rating_name"])
        now, before = scale.get(row["current_rating"] or ""), scale.get(row["previous_rating"] or "")
        if key and now is not None and before is not None and now > before:
            lowered.append(_rating_item(project_id, row, key))
    return lowered


def _restructurings(call: Call, latest: list[dict], limits: Limits) -> list[dict] | None:
    """The restructurings of the counted levels the latest ISR lists in the window, or None when that ISR was
    never read into passages."""
    document_id = latest[0]["document_id"]
    found = _rows(call, "restructurings.sql", document_id=document_id)
    if not found:
        [read] = _rows(call, "passages_read.sql", document_id=document_id)
        return [] if read["passages"] else None
    since = months_before(call.as_of, limits.restructured_months)
    items, seen = [], set()
    for row in found:
        for level, day, month, year in RESTRUCTURING.findall(row["text"]):
            dated = dt.date(int(year), MONTHS[month.lower()], int(day))
            if int(level) in limits.restructured_levels and since <= dated <= call.as_of and dated not in seen:
                seen.add(dated)
                items.append({"evidence_id": f"strata.gold.passage:{row['passage_id']}", "public_from": _iso(row["public_from"]),
                              "level": int(level), "restructured_on": dated.isoformat(), "document_id": document_id,
                              "isr_date": _iso(latest[0]["isr_date"])})
    return sorted(items, key=lambda item: item["restructured_on"])


def _loan_item(project_id: str, row: dict) -> dict:
    return {"evidence_id": f"strata.gold.loan:{project_id}/{row['loan_number']}", "public_from": _iso(row["public_from"]),
            "loan_number": row["loan_number"],
            **{key: None if row[key] is None else str(_money(row[key]).quantize(CENT))
               for key in ("original_principal_usd", "disbursed_usd", "undisbursed_usd", "cancelled_usd")},
            "as_of": _iso(row["as_of"])}


def disbursed_share(loans: list[dict]) -> tuple[Decimal, Decimal, Decimal]:
    """Disbursed, disbursed plus undisbursed, and the first divided by the second, over the loans. The second is
    what the loans had committed and not canceled, measured in the same currency as what they disbursed, so a
    credit committed in another currency and reported in US dollars at a later rate is measured against itself."""
    disbursed = sum((_money(row["disbursed_usd"]) or Decimal(0) for row in loans), Decimal(0))
    available = disbursed + sum((_money(row["undisbursed_usd"]) or Decimal(0) for row in loans), Decimal(0))
    return disbursed, available, (disbursed / available if available else Decimal(0))


# ── The tool ─────────────────────────────────────────────────────────────

def _signal(project: dict, key: str, items: list[dict], values: dict, limits: Limits, as_of: dt.date,
            source: dict) -> dict:
    count = values.pop("count", len(items))
    strong = key in limits.strong or (key in limits.strong_from and count >= limits.strong_from[key])
    public = max((_date(item["public_from"]) for item in items), default=as_of)
    return {"evidence_id": f"strata.tools.project_signals:{project['project_id']}/{key}@{as_of.isoformat()}",
            "public_from": _iso(min(public, as_of)), "source": source, "check": key, "strong": strong,
            "count": count, "values": values, "items": items}


def _plan_source(project_id: str, items: list[dict]) -> dict:
    first = items[0]["source"]
    return {"source_key": "plans", "project_id": project_id, "document_id": first["document_id"], "date": first["plan_date"]}


def _status(signals: list[dict], ran: int, limits: Limits) -> str:
    if not ran:
        return "not_checked"
    if not signals:
        return "no_signals"
    if len(signals) >= limits.look_min or any(signal["strong"] for signal in signals):
        return "needs_a_look"
    return "watch"


def project_signals(call: Call, project_id: str) -> dict:
    """Run the seven checks on one project, as of call.as_of."""
    limits = Limits.read(call)
    thresholds = limits.as_values(call)
    history = _rows(call, "history.sql", project_id=project_id)
    project = _project(call, project_id, history)
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "project": project, "checks": [],
             "counts": {"signals": 0, "strong": 0, "ran": 0, "checks": len(CHECKS)}, "thresholds": thresholds,
             "plans": []}
    if project is None:
        return {**empty, "status": None, "abstention": {"reason": "unknown_project", "project_id": project_id}}
    if project["status"] != ACTIVE:
        return {**empty, "status": project["status"] or "not_checked",
                "abstention": {"reason": "not_active" if project["status"] else "no_records", "project_id": project_id}}

    found: dict[str, list[dict]] = {}
    values: dict[str, dict] = {key: {} for key in CHECKS}
    missing: dict[str, str] = {}
    sources: dict[str, dict] = {}

    plan_found, plan_missing, plans = _plan_checks(call, project, limits)
    for key in PLAN_CHECKS:
        if plan_found is None:
            missing[key] = plan_missing
        else:
            found[key] = plan_found[key]
            if found[key]:
                sources[key] = _plan_source(project_id, found[key])
    if found.get("above_estimate"):
        ratios = [item["ratio"] for item in found["above_estimate"]]
        values["above_estimate"] = {"ratio_min": min(ratios), "ratio_max": max(ratios)}
    if found.get("late_direct"):
        total = sum((_money(item["estimated_amount_usd"]) for item in found["late_direct"]), Decimal(0))
        values["late_direct"] = {"total_millions": millions(total)}

    if not history:
        missing["closing_moves"] = "no_loan_history"
    else:
        moves = _closing_moves(project_id, history)
        found["closing_moves"] = moves if len(moves) >= limits.closing_moves_min else []
        if found["closing_moves"]:
            values["closing_moves"] = {"since_year": _date(moves[0]["reported_on"]).year}
            sources["closing_moves"] = {"source_key": "loan_history", "project_id": project_id, "document_id": None,
                                        "date": moves[-1]["reported_on"]}

    latest = _latest_isr(_rows(call, "isr_ratings.sql", project_id=project_id))
    if not latest:
        missing["isr_lowered"] = missing["restructured"] = "no_isr"
    else:
        isr_source = {"source_key": "isr", "project_id": project_id, "document_id": latest[0]["document_id"],
                      "date": _iso(latest[0]["isr_date"])}
        found["isr_lowered"] = _lowered(project_id, latest, limits)
        if found["isr_lowered"]:
            values["isr_lowered"] = {"isr_date": _iso(latest[0]["isr_date"])}
            sources["isr_lowered"] = isr_source
        restructurings = _restructurings(call, latest, limits)
        if restructurings is None:
            missing["restructured"] = "no_isr"
        else:
            found["restructured"] = restructurings
            if restructurings:
                values["restructured"] = {"latest_on": restructurings[-1]["restructured_on"],
                                          "since_year": _date(restructurings[0]["restructured_on"]).year}
                sources["restructured"] = isr_source

    loans = _rows(call, "loans.sql", project_id=project_id)
    if not loans:
        missing["disbursement"] = "no_loans"
    else:
        disbursed, available, share = disbursed_share(loans)
        closing = _date(project["closing_date"])
        left = whole_months(call.as_of, closing) if closing else None
        slow = share < limits.disbursement_max_share and left is not None and 0 <= left <= limits.disbursement_months
        found["disbursement"] = [_loan_item(project_id, row) for row in loans] if slow else []
        if slow:
            snapshot = max(_date(row["as_of"]) for row in loans)
            values["disbursement"] = {
                "count": 1, "percent": int((share * 100).quantize(Decimal(1), ROUND_HALF_UP)),
                "percent_exact": str((share * 100).quantize(TENTH, ROUND_HALF_UP)),
                "disbursed_usd": str(disbursed.quantize(CENT)), "disbursed_millions": millions(disbursed),
                "available_usd": str(available.quantize(CENT)), "available_millions": millions(available),
                "months_left": left, "as_of_date": _iso(snapshot)}
            sources["disbursement"] = {"source_key": "loans", "project_id": project_id, "document_id": None,
                                       "date": _iso(snapshot)}

    rows = [_signal(project, key, found[key], dict(values[key]), limits, call.as_of, sources[key])
            for key in CHECKS if found.get(key)]
    # Strong signals first, then the others in the order of CHECKS (the 37 brief, section 4.3).
    rows.sort(key=lambda row: (not row["strong"], CHECKS.index(row["check"])))
    by_key = {row["check"]: row for row in rows}
    checks = [{"key": key, "ran": key not in missing, "missing": missing.get(key), "fired": key in by_key,
               "strong": by_key[key]["strong"] if key in by_key else False} for key in CHECKS]
    ran = sum(1 for check in checks if check["ran"])
    not_used: dict[str, list[str]] = {}
    for key, reason in missing.items():
        not_used.setdefault(reason, []).append(key)
    status = _status(rows, ran, limits)
    return {
        "rows": rows,
        "coverage": {"matched": len(CHECKS), "used": ran,
                     "not_used": [{"reason": reason, "count": len(keys), "checks": keys} for reason, keys in not_used.items()]},
        "abstention": {"reason": "no_records", "project_id": project_id} if status == "not_checked" else None,
        "project": project,
        "status": status,
        "checks": checks,
        "counts": {"signals": len(rows), "strong": sum(1 for row in rows if row["strong"]), "ran": ran,
                   "checks": len(CHECKS)},
        "thresholds": thresholds,
        "plans": plans,
    }
