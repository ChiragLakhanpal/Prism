"""compare_cost_estimates: comparable packages' signed amounts against their own cost estimates (ticket 31).

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its adapter. It
answers the spec's user story 31, "catch a cost estimate set below market rates before it forces rebidding", by
placing each comparable package by how far its signed amount was from its own cost estimate, in percent. It does
not draw the package's own cost estimate among their signed amounts: find_comparables may choose comparables by a
size band around it, so it would sit in the middle by construction (the 31 brief, section 3.1).

- The comparables are the STEP references the call names, as find_comparables returned them, so the reference
  class is defined once.
- A package's cost estimate is chosen by one rule, in sql/compare_cost_estimates/estimates.sql: the Estimated
  Amount (US$) of the first plan version, public on the as-of date, that lists it with one.
- Its signed amount adds its contracts in the contract awards data, in US dollars (gold.contract, which keeps a
  joint venture's contract once). A package signed only in a Contract Award notice has its price in the notice's
  currency, and no exchange-rate source is registered, so it is left out and counted (no_usd_amount).
- Each comparable is used, or left out for the first of these reasons: still_open (no signed contract by the
  as-of date), no_estimate (no plan version public by then gives one), no_usd_amount.
- diff_pct is a tool column (CLAUDE.md rule 1): 100 x (signed - estimate) / estimate, rounded half up to one
  decimal, or to a whole number when it is 100 or more either way (DESIGN.md section 6, Numbers). Its sign says
  above (positive) or below (negative); 0 is at the cost estimate.
- Below past_range.min_comparables packages with both amounts there are no quartiles, and the tool abstains with
  every package (too_few_comparables). From there it gives the quartiles of diff_pct (linear between the two
  nearest packages), and above past_range.quantile_dots_above, quantile dots each standing for an equal share.

The rows come in the chart's left-to-right order: lowest difference first, then STEP reference.
"""

from __future__ import annotations

import datetime as dt
import statistics
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources

from strata.config import load_sources, load_tools
from strata.tools.registry import Call

TOOL = "compare_cost_estimates"
CENTS = Decimal("0.01")
REASONS = ("still_open", "no_estimate", "no_usd_amount")


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / TOOL / f"{name}.sql").read_text()


def _rows(call: Call, name: str, **params) -> list[dict]:
    result = call.engine.run(_sql(name), {"as_of": call.as_of, **params})
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _iso(value) -> str | None:
    day = _date(value)
    return day.isoformat() if day else None


def _money(value) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value)).quantize(CENTS)


def _flag(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def references(text: str) -> list[str]:
    """The STEP references a call names, in order, each once."""
    return list(dict.fromkeys(part.strip() for part in text.split(",") if part.strip()))


def percent(value: Decimal) -> float | int:
    """A percentage at DESIGN.md section 6's rounding: one decimal up to 100, none from 100, half up. It is
    read again after rounding, so 99.96 becomes 100, not 100.0."""
    tenth = value.quantize(Decimal("0.1"), ROUND_HALF_UP)
    if abs(tenth) >= 100:
        return int(value.quantize(Decimal(1), ROUND_HALF_UP))
    return float(tenth)


def diff_pct(signed: Decimal, estimate: Decimal) -> float | int:
    return percent((signed - estimate) * 100 / estimate)


def _quartiles(values: list[float]) -> dict:
    cuts = statistics.quantiles(sorted(values), n=4, method="inclusive")
    return {name: percent(Decimal(str(cut))) for name, cut in zip(("q25", "q50", "q75"), cuts, strict=True)}


def _quantile_dots(rows: list[dict], count: int) -> list[dict]:
    """count dots, each standing for an equal share of the packages in the chart's order (as nearly equal as
    the number allows), placed at the middle of its share."""
    dots, start = [], 0
    for k in range(count):
        size = len(rows) // count + (1 if k < len(rows) % count else 0)
        share = rows[start:start + size]
        start += size
        if not share:
            continue
        middle = statistics.median(Decimal(str(row["diff_pct"])) for row in share)
        dots.append({"k": k + 1, "diff_pct": percent(Decimal(middle)), "count": len(share),
                     "step_references": [row["step_reference"] for row in share]})
    return dots


def _sources() -> list[dict]:
    registry = load_sources()
    return [{"key": key, "dataset_name": registry[key].dataset_name} for key in load_tools()[TOOL].sources]


def _own_estimate(call: Call, step_reference: str | None, estimate_usd: float | None) -> dict:
    """The package's own cost estimate: its plan row's Estimated Amount (US$), as the page's header gives it, or
    the amount the call gives for a package that has no plan row."""
    if step_reference:
        from strata.tools.find_comparables import read_package

        package = read_package(call.engine, step_reference, call.as_of)
        amount = package["estimated_amount_usd"] if package else None
        return {"step_reference": step_reference, "estimated_amount_usd": amount,
                "evidence_id": package["evidence_id"] if package else None, "given": False}
    amount = _money(estimate_usd) if estimate_usd is not None else None
    return {"step_reference": None, "estimated_amount_usd": str(amount) if amount is not None else None,
            "evidence_id": None, "given": amount is not None}


def compare_cost_estimates(call: Call, comparables: str, step_reference: str | None = None,
                           estimate_usd: float | None = None) -> dict:
    refs = references(comparables)
    limit = int(call.thresholds.value("past_range.min_comparables"))
    joined = ",".join(refs)
    packages = {row["step_reference"]: row for row in _rows(call, "packages", refs=joined)} if refs else {}
    estimates = {row["step_reference"]: row for row in _rows(call, "estimates", refs=joined)} if refs else {}
    contracts: dict[str, list[dict]] = {}
    for row in (_rows(call, "contracts", refs=joined) if refs else []):
        contracts.setdefault(row["step_reference"], []).append(row)

    rows, left_out = [], {reason: [] for reason in REASONS}
    for ref in refs:
        package = packages.get(ref)
        evidence = f"strata.gold.package:{ref}"
        signed = package is not None and (_flag(package["signed_in_awards"]) or _flag(package["signed_in_award_notice"]))
        estimate = estimates.get(ref)
        mine = contracts.get(ref, [])
        if not signed:
            left_out["still_open"].append(evidence)
        elif estimate is None:
            left_out["no_estimate"].append(evidence)
        elif not mine:
            left_out["no_usd_amount"].append(evidence)
        else:
            estimated = _money(estimate["estimated_amount_usd"])
            total = sum((_money(row["contract_amount_usd"]) for row in mine), Decimal(0))
            if estimated is None or estimated <= 0:
                left_out["no_estimate"].append(evidence)
                continue
            public = max([_date(estimate["public_from"])] + [_date(row["public_from"]) for row in mine])
            rows.append({
                "evidence_id": f"{evidence}/cost",
                "public_from": public.isoformat(),
                "source": {"plan": {"document_id": str(estimate["document_id"]), "plan_date": _iso(estimate["plan_date"]),
                                    "pdf_page": int(estimate["pdf_page"]),
                                    "implementing_agency": estimate["implementing_agency"]},
                           "contract_ids": [str(row["contract_id"]) for row in mine]},
                "step_reference": ref,
                "project_id": package["project_id"],
                "country_code": package["country_code"],
                "country_name": package["country_name"],
                "description": package["description"],
                "estimated_amount_usd": str(estimated),
                "signed_amount_usd": str(total.quantize(CENTS)),
                "diff_pct": diff_pct(total, estimated),
                "contracts": [{"contract_id": str(row["contract_id"]), "amount_usd": str(_money(row["contract_amount_usd"])),
                               "signed_on": _iso(row["contract_signing_date"])} for row in mine],
                "rank": None,
            })
    rows.sort(key=lambda row: (row["diff_pct"], row["step_reference"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank

    not_used = [{"reason": reason, "count": len(ids), "evidence_ids": ids} for reason, ids in left_out.items() if ids]
    coverage = {"matched": len(refs), "used": len(rows), "not_used": not_used}
    counts = {"total": len(refs), "m": len(rows), "open": len(left_out["still_open"]),
              "no_estimate": len(left_out["no_estimate"]), "no_usd": len(left_out["no_usd_amount"]),
              "above": sum(1 for row in rows if row["diff_pct"] > 0),
              "below": sum(1 for row in rows if row["diff_pct"] < 0),
              "at": sum(1 for row in rows if row["diff_pct"] == 0)}
    amounts = [Decimal(row["estimated_amount_usd"]) for row in rows]
    band = {"low_usd": str(min(amounts)), "high_usd": str(max(amounts))} if amounts else None
    through = call.engine.run(_sql_records_through(), {"as_of": call.as_of}).rows
    found = {"rows": rows, "coverage": coverage, "package": _own_estimate(call, step_reference, estimate_usd),
             "counts": counts, "band": band, "quartiles": None, "quantile_dots": None, "min_comparables": limit,
             "sources": _sources(), "records_through": _iso(through[0][0]) if through else None}
    if not refs:
        return {**found, "abstention": {"reason": "no_comparables"}}
    if not rows:
        return {**found, "abstention": {"reason": "none_with_both_amounts", "total": len(refs)}}
    if len(rows) < limit:
        return {**found, "abstention": {"reason": "too_few_comparables", "count": len(rows), "min_comparables": limit}}
    dots_above = int(call.thresholds.value("past_range.quantile_dots_above"))
    dots = _quantile_dots(rows, int(call.thresholds.value("past_range.quantile_dots"))) if len(rows) > dots_above else None
    return {**found, "quartiles": _quartiles([row["diff_pct"] for row in rows]), "quantile_dots": dots,
            "abstention": None}


def _sql_records_through() -> str:
    # The same day the comparables' source lines give ("Records run through ..."), from find_comparables' query.
    return (resources.files("strata.tools") / "sql" / "find_comparables" / "records_through.sql").read_text()
