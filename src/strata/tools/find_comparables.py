"""find_comparables: the comparable packages for one package, and their past range.

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its
adapter. It reads the package's row in its newest public Procurement Plan (silver.plan_rows and
plan_steps), then every package from every project that matches the criteria (gold.package, with its
notices and contracts), each only where it was public on or before the as-of date (ADR 0002). Its SQL
is in src/strata/tools/sql/find_comparables/.

How it works, with its thresholds in config/thresholds.toml's [past_range] (CLAUDE.md rule 9):

- The criteria are the glossary's seven: method, category, market approach, review type, size band,
  region (the country) and period. A criterion the call leaves out defaults from the package's plan
  row: its Method, its category (the plan table it sits in) and its project's country, with notices
  from period_from to the plan's date. Market approach, review type and size band stay open unless
  given, because a package still open has no review type or signed amount in any record. "any"
  leaves a criterion open. A criterion matches whatever its case, since the agent writes it.
- A package with a Method in no_notice_methods, or a Market Approach that starts with a word in
  no_notice_market_approaches, has no specific procurement notice, so the tool abstains
  (no_public_notice).
- Procurement cycle time runs from a comparable's specific procurement notice to its signed
  contract. A package with no signed contract by the as-of date is still open: its days so far count
  as not signed yet (censored). A canceled package is left out and named in the coverage line,
  unless canceled_as_still_open says to keep it as still open. A matching package Strata cannot
  measure (no STEP reference to join notice to contract, no notice, signed before its notice, or no
  value for a criterion the call set) is counted in the coverage line with its reason.
- The past range is Kaplan-Meier (src/strata/estimates/past_range.py): the months by which a
  quarter, half, three quarters and 8 in 10 were signed. Below min_comparables the tool returns no
  range and no share, abstains (too_few_comparables) and still returns every comparable. Above
  quantile_dots_above it also returns quantile_dots dots.
- The plan's months run from the plan row's planned notice date to its planned signing date. The
  result gives how many comparables were signed within them, and, from min_comparables up, about how
  many in 10, so the screen states counts and never works one out.
- From min_comparables up, frequencies holds the two numbers each frequency phrase states, so the agent
  can cite them like any value: [8, 10] for "8 in 10 were signed within", and for the plan's share
  [about N, 10], with N at least 1 and at most 9, because the screen writes "fewer than 1 in 10" and
  "more than 9 in 10" at the ends. With none or all signed within the plan, it names no share.

Every number is at its rounding here: days are whole, and months have one decimal. The rows come
shortest first, by months and then STEP reference, which is the order the chart's dots and its table
use. The call's view is returned with the result but not applied until ticket 40.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources

from strata.config import load_sources, load_tools
from strata.estimates.past_range import QUARTERS, Observation, months, quantile_dots, quartiles
from strata.tools.check_plan import agency_id
from strata.tools.registry import Call

TOOL = "find_comparables"
ANY = "any"
# The plan table a STEP row sits in, and the procurement category the notices and awards give it.
CATEGORIES = {"WORKS": "Works", "GOODS": "Goods", "NON CONSULTING SERVICES": "Non-consulting Services",
              "CONSULTING FIRMS": "Consultant Services", "INDIVIDUAL CONSULTANTS": "Consultant Services"}
# The order the coverage line lists what it left out.
REASONS = ("no_step_reference", "no_notice", "canceled", "signed_before_notice", "no_review_type",
           "no_market_approach", "no_amount")
CENTS = Decimal("0.01")


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "find_comparables" / name).read_text()


def _rows(engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


# Values arrive typed from DuckDB and as text from the SQL warehouse, so each is read once here.

def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _money(value) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value)).quantize(CENTS)


def _iso(value: dt.date | None) -> str | None:
    return value.isoformat() if value else None


def _as_float(value: Decimal) -> float:
    return float(value)


@dataclass(frozen=True)
class Limits:
    min_comparables: int
    quantile_dots_above: int
    quantile_dots: int
    period_from: dt.date
    max_plan_months: int
    canceled_as_still_open: bool
    no_notice_methods: tuple[str, ...]
    no_notice_market_approaches: tuple[str, ...]

    @classmethod
    def read(cls, call: Call) -> Limits:
        value = call.thresholds.value
        return cls(int(value("past_range.min_comparables")), int(value("past_range.quantile_dots_above")),
                   int(value("past_range.quantile_dots")), _date(value("past_range.period_from")),
                   int(value("past_range.max_plan_months")), bool(value("past_range.canceled_as_still_open")),
                   tuple(value("past_range.no_notice_methods")),
                   tuple(value("past_range.no_notice_market_approaches")))

    def as_values(self) -> dict:
        return {"min_comparables": self.min_comparables, "quantile_dots_above": self.quantile_dots_above,
                "quantile_dots": self.quantile_dots, "max_plan_months": self.max_plan_months,
                "canceled_as_still_open": self.canceled_as_still_open}


# ── The package ──────────────────────────────────────────────────────────

def read_package(engine, step_reference: str, as_of: dt.date) -> dict | None:
    """The package as its newest plan version public on the as-of date gives it, or None when no
    such version lists it. The package page's header shows the same facts."""
    found = _rows(engine, "package.sql", step_reference=step_reference.strip(), as_of=as_of)
    if not found:
        return None
    row = found[0]
    estimated = _money(row["estimated_amount_usd"])
    return {
        "evidence_id": f"strata.silver.plan_rows:{row['document_id']}/{row['activity_reference_no']}",
        "public_from": _iso(_date(row["public_from"])),
        "step_reference": row["activity_reference_no"],
        "description": row["description"],
        "project_id": row["project_id"],
        "project_name": row["project_name"],
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "section": row["section"],
        "category": CATEGORIES.get(row["section"]),
        "method": row["method"],
        "market_approach": row["market_approach"],
        "review_type": row["review_type"],
        "estimated_amount_usd": str(estimated) if estimated is not None else None,
        "process_status": row["process_status"],
        "planned_notice_on": _iso(_date(row["planned_notice_on"])),
        "planned_signing_on": _iso(_date(row["planned_signing_on"])),
        "plan": {"document_id": row["document_id"], "implementing_agency": row["implementing_agency"],
                 "agency_id": agency_id(row["implementing_agency"] or ""), "plan_date": _iso(_date(row["plan_date"])),
                 "disclosed_on": _iso(_date(row["disclosed_on"])), "pdf_page": int(row["pdf_page"])},
    }


def _open(value: str | None) -> str | None:
    """A criterion's value, or None when the call leaves it open with "any"."""
    return None if value is None or value.strip().lower() == ANY else value.strip()


def _criteria(package: dict, limits: Limits, asked: dict) -> dict:
    defaults = {"method": package["method"], "category": package["category"], "country": package["country_code"],
                "notice_from": limits.period_from, "notice_to": _date(package["plan"]["plan_date"])}
    criteria, from_package = {}, []
    for name in ("method", "category", "market_approach", "review_type", "country"):
        given = asked.get(name)
        if given is None and name in defaults:
            criteria[name] = defaults[name]
            # A default the package does not give, such as a plan table with no category, leaves the
            # criterion open, and the package is not named as where it came from.
            if defaults[name] is not None:
                from_package.append(name)
        else:
            criteria[name] = _open(given)
    for name in ("notice_from", "notice_to"):
        criteria[name] = asked.get(name) or defaults[name]
        if asked.get(name) is None and name == "notice_to":
            from_package.append(name)
    criteria["size_from_usd"] = asked.get("size_from_usd")
    criteria["size_to_usd"] = asked.get("size_to_usd")
    criteria["from_package"] = from_package
    return criteria


def _no_notice(package: dict, limits: Limits) -> dict | None:
    """The abstention for a package whose Method or Market Approach has no specific procurement notice."""
    if package["method"] in limits.no_notice_methods:
        return {"reason": "no_public_notice", "field": "Method", "value": package["method"]}
    approach = package["market_approach"] or ""
    if any(approach.startswith(word) for word in limits.no_notice_market_approaches):
        return {"reason": "no_public_notice", "field": "Market Approach", "value": approach}
    return None


# ── The comparables ──────────────────────────────────────────────────────

def _same(value: str, wanted: str) -> bool:
    """Whether a record's value is the criterion, whatever the case, since the agent writes the criteria
    itself: "post" is STEP's Post."""
    return value.strip().casefold() == wanted.strip().casefold()


def _meets_each(candidate: dict, criteria: dict) -> dict[str, bool | None]:
    """For each criterion the SQL could not apply and the call set, whether the candidate meets it:
    True or False when its records give a value, None when they give none. Each is keyed by the reason
    the coverage line gives when the value is missing."""
    found = {}
    if criteria["review_type"] is not None:
        # The contract's review type first, because it is what happened; then the plan row's.
        review_type = candidate.get("review_type") or candidate.get("plan_review_type")
        found["no_review_type"] = None if review_type is None else _same(review_type, criteria["review_type"])
    if criteria["market_approach"] is not None:
        approach = (candidate.get("plan_market_approach") or candidate.get("contract_market_approach")
                    or candidate.get("notice_market_approach") or candidate.get("market_approach"))
        found["no_market_approach"] = None if approach is None else _same(approach, criteria["market_approach"])
    if criteria["size_from_usd"] is not None or criteria["size_to_usd"] is not None:
        amount = _money(candidate["amount_usd"])
        low, high = criteria["size_from_usd"], criteria["size_to_usd"]
        found["no_amount"] = None if amount is None else (
            (low is None or amount >= Decimal(str(low))) and (high is None or amount <= Decimal(str(high))))
    return found


def _matches(candidate: dict, criteria: dict) -> tuple[bool, str | None]:
    """Whether a candidate meets the criteria the SQL could not apply, and the reason it cannot be used
    when it has no value for one of them. It is checked against every criterion first: a known value
    that differs leaves it out of the match, even when another criterion has no value. Of the criteria
    with no value, the reason given is the first in the coverage line's order."""
    found = _meets_each(candidate, criteria)
    if any(meets is False for meets in found.values()):
        return False, None
    return True, next((reason for reason in REASONS if reason in found and found[reason] is None), None)


def _comparable(candidate: dict, as_of: dt.date) -> dict:
    """One comparable as the tool returns it: signed on its first contract, or on its award notice's
    signature date, or still open with its days so far."""
    notice_date = _date(candidate["notice_date"])
    contract_on, award_on = _date(candidate["signed_on"]), _date(candidate["award_signed_on"])
    signed_on = contract_on or award_on
    signed_public = contract_on or (_date(candidate["award_notice_on"]) if award_on else None)
    signed_in = "contract awards" if contract_on else "award notice" if award_on else None
    days = ((signed_on or as_of) - notice_date).days
    return {
        "evidence_id": f"strata.gold.package:{candidate['step_reference']}",
        "public_from": _iso(max(day for day in (notice_date, signed_public) if day)),
        "source": {"project_id": candidate["project_id"], "notice_id": candidate["notice_id"],
                   "contract_id": candidate["contract_id"] if contract_on else None,
                   "award_notice_id": candidate["award_notice_id"] if not contract_on and award_on else None,
                   "signed_in": signed_in},
        "step_reference": candidate["step_reference"],
        "project_id": candidate["project_id"],
        "country_code": candidate["country_code"],
        "country_name": candidate["country_name"],
        "notice_id": candidate["notice_id"],
        "notice_date": _iso(notice_date),
        "signed_on": _iso(signed_on),
        "still_open": signed_on is None,
        "days": days,
        "months": _as_float(months(days)),
        "rank": None,
    }


def _select(candidates: list[dict], unlinked: list[dict], criteria: dict, limits: Limits,
            as_of: dt.date) -> tuple[list[dict], dict[str, list[str]], int]:
    """The comparables, what was left out by reason, and how many canceled packages matched."""
    rows, left_out, canceled = [], {reason: [] for reason in REASONS}, 0
    for contract in unlinked:
        matched, _ = _matches(contract, criteria)
        if matched:
            left_out["no_step_reference"].append(f"strata.gold.contract:{contract['contract_id']}")
    for candidate in candidates:
        matched, unknown = _matches(candidate, criteria)
        if not matched:
            continue
        evidence_id = f"strata.gold.package:{candidate['step_reference']}"
        signed = candidate["signed_on"] is not None or candidate["award_signed_on"] is not None
        is_canceled = not signed and candidate["process_status"] == "Canceled"
        # The reasons in the coverage line's order: a canceled package was never signed, so it has no
        # signed amount either, and canceled is the reason that says why.
        row = None
        if candidate["notice_date"] is None:
            reason = "no_notice"
        elif is_canceled and not limits.canceled_as_still_open:
            reason = "canceled"
        else:
            row = _comparable(candidate, as_of)
            reason = "signed_before_notice" if row["days"] < 0 else unknown
        if reason:
            left_out[reason].append(evidence_id)
        else:
            rows.append(row)
        canceled += is_canceled and (reason == "canceled" or not reason)
    rows.sort(key=lambda row: (row["months"], row["step_reference"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows, left_out, canceled


def _coverage(rows: list[dict], left_out: dict[str, list[str]]) -> dict:
    not_used = [{"reason": reason, "count": len(ids), "evidence_ids": ids} for reason, ids in left_out.items() if ids]
    return {"matched": len(rows) + sum(entry["count"] for entry in not_used), "used": len(rows), "not_used": not_used}


def _plan(package: dict, rows: list[dict], ranged: bool) -> dict | None:
    """The plan's months, from its planned notice date to its planned signing date, and how many
    comparables were signed within them: a count of rows at their one-decimal months."""
    notice_on, signing_on = _date(package["planned_notice_on"]), _date(package["planned_signing_on"])
    if notice_on is None or signing_on is None or signing_on < notice_on:
        return None
    days = (signing_on - notice_on).days
    planned = months(days)
    within = sum(1 for row in rows if not row["still_open"] and Decimal(str(row["months"])) <= planned)
    in10 = (Decimal(within * 10) / len(rows)).quantize(Decimal(1), ROUND_HALF_UP) if ranged and rows else None
    return {"days": days, "months": _as_float(planned), "planned_notice_on": _iso(notice_on),
            "planned_signing_on": _iso(signing_on), "plan_date": package["plan"]["plan_date"],
            "within": within, "in10": int(in10) if in10 is not None else None}


def _frequencies(plan: dict | None, total: int) -> dict:
    """The numbers each frequency phrase states: "8 in 10 were signed within", and the plan's "about N in
    10", "fewer than 1 in 10" or "more than 9 in 10"."""
    share = None
    if plan is not None and plan["in10"] is not None and 0 < plan["within"] < total:
        share = [min(max(plan["in10"], 1), 9), 10]
    return {"q80": [int(QUARTERS["q80"] * 10), 10], "plan": share}


def _past_range(rows: list[dict]) -> dict:
    observations = [Observation(row["days"], not row["still_open"]) for row in rows]
    days = quartiles(observations)
    return {**{name: _as_float(months(value)) if value is not None else None for name, value in days.items()},
            "days": days}


def _quantile_dots(rows: list[dict], count: int) -> list[dict]:
    observations = [Observation(row["days"], not row["still_open"]) for row in rows]
    last = max(row["days"] for row in rows)  # a dot the curve never reaches sits at the last follow-up
    return [{"k": k, "days": day if day is not None else last, "months": _as_float(months(day if day is not None else last)),
             "reached": day is not None} for k, day in quantile_dots(observations, count)]


def _sources() -> list[dict]:
    registry = load_sources()
    return [{"key": key, "dataset_name": registry[key].dataset_name} for key in load_tools()[TOOL].sources]


def find_comparables(call: Call, step_reference: str, method: str | None = None, category: str | None = None,
                     market_approach: str | None = None, review_type: str | None = None,
                     size_from_usd: float | None = None, size_to_usd: float | None = None,
                     country: str | None = None, notice_from: dt.date | None = None,
                     notice_to: dt.date | None = None) -> dict:
    """The comparables for one package and their past range, as of call.as_of."""
    limits = Limits.read(call)
    package = read_package(call.engine, step_reference, call.as_of)
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "package": package,
             "criteria": None, "counts": None, "past_range": None, "plan": None, "frequencies": None,
             "quantile_dots": None,
             "thresholds": limits.as_values(), "sources": _sources(), "records_through": None}
    if package is None:
        return {**empty, "abstention": {"reason": "unknown_package", "step_reference": step_reference.strip()}}
    asked = {"method": method, "category": category, "market_approach": market_approach, "review_type": review_type,
             "country": country, "notice_from": notice_from, "notice_to": notice_to,
             "size_from_usd": size_from_usd, "size_to_usd": size_to_usd}
    criteria = _criteria(package, limits, asked)
    through = _rows(call.engine, "records_through.sql", as_of=call.as_of)
    records_through = _iso(_date(through[0]["records_through"])) if through else None
    country_name = None
    if criteria["country"] is not None:
        named = _rows(call.engine, "country.sql", country=criteria["country"])
        country_name = named[0]["country_name"] if named else criteria["country"]
    found = {**empty, "criteria": {**{key: _iso(value) if isinstance(value, dt.date) else value
                                      for key, value in criteria.items()}, "country_name": country_name},
             "records_through": records_through}
    no_notice = _no_notice(package, limits)
    if no_notice:
        return {**found, "abstention": no_notice}

    params = {"as_of": call.as_of, "step_reference": package["step_reference"], "country": criteria["country"],
              "method": criteria["method"], "category": criteria["category"],
              "notice_from": criteria["notice_from"], "notice_to": criteria["notice_to"]}
    candidates = _rows(call.engine, "candidates.sql", **params)
    unlinked = _rows(call.engine, "unlinked.sql", **{k: v for k, v in params.items() if k != "step_reference"})
    rows, left_out, canceled = _select(candidates, unlinked, criteria, limits, call.as_of)
    coverage = _coverage(rows, left_out)
    still_open = sum(1 for row in rows if row["still_open"])
    counts = {"comparables": len(rows), "signed": len(rows) - still_open, "still_open": still_open,
              "canceled": canceled, "canceled_as_still_open": limits.canceled_as_still_open}
    found = {**found, "coverage": coverage, "counts": counts}
    if not rows:
        reason = "none_measurable" if coverage["matched"] else "no_comparables"
        return {**found, "abstention": {"reason": reason, "matched": coverage["matched"]}}
    if len(rows) < limits.min_comparables:
        return {**found, "rows": rows, "plan": _plan(package, rows, ranged=False),
                "abstention": {"reason": "too_few_comparables", "count": len(rows),
                               "min_comparables": limits.min_comparables}}
    dots = _quantile_dots(rows, limits.quantile_dots) if len(rows) > limits.quantile_dots_above else None
    plan = _plan(package, rows, ranged=True)
    return {**found, "rows": rows, "plan": plan, "frequencies": _frequencies(plan, len(rows)),
            "past_range": _past_range(rows), "quantile_dots": dots, "abstention": None}
