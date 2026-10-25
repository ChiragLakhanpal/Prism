"""rejected_bids: how many comparable packages had bids rejected, and why, from their award notices (ticket 31).

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its adapter. An
award notice lists its rejected bidders, each with a Reason for Rejection. The tool reads only that field, word
for word (strata.criteria.reading.rejection_reasons), and never a bidder: a list of reasons across packages with
names beside them would be a supplier profile, which Strata refuses (the 31 brief, section 6.7). The award
notice itself, opened in the evidence drawer, shows the record as published.

- m is the comparables with an award notice published by the as-of date: award notices are where rejected bids
  are listed. n is those with at least one rejected bid that gives a reason.
- Each row is one reason in one award notice: its text and language, how many bids that notice rejected for
  it (bids), and the item it concerned (config/criteria_items.toml; a reason no item names falls under other).
  Its evidence id names the notice and the reason's place among the notice's reasons:
  strata.gold.notice:OP00125282/reason/1.
- groups count the packages under each item, most packages first, then the registry's order. A package can sit
  in more than one group.

Rows come newest award notice first, then STEP reference, then the order the notice lists its reasons.
"""

from __future__ import annotations

import datetime as dt
from importlib import resources

from strata.config import load_criteria_items, load_sources, load_tools
from strata.criteria.reading import reason_item, rejection_reasons
from strata.tools.registry import Call

TOOL = "rejected_bids"
LANGUAGES = {"english": "en", "french": "fr", "spanish": "es", "portuguese": "pt"}


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / TOOL / f"{name}.sql").read_text()


def _iso(value) -> str | None:
    if value is None or value == "":
        return None
    return value.isoformat()[:10] if isinstance(value, dt.date) else str(value)[:10]


def _references(text: str) -> list[str]:
    return list(dict.fromkeys(part.strip() for part in text.split(",") if part.strip()))


def _sources() -> list[dict]:
    registry = load_sources()
    return [{"key": key, "dataset_name": registry[key].dataset_name} for key in load_tools()[TOOL].sources]


def reason_evidence_id(notice_id: str, place: int) -> str:
    return f"strata.gold.notice:{notice_id}/reason/{place}"


def notice_reasons(text: str) -> list[tuple[str, int]]:
    """An award notice's distinct reasons, in the order it first gives each, with how many bids each rejected."""
    counted: dict[str, int] = {}
    for reason in rejection_reasons(text):
        counted[reason] = counted.get(reason, 0) + 1
    return list(counted.items())


def rejected_bids(call: Call, comparables: str) -> dict:
    refs = _references(comparables)
    items = load_criteria_items()
    result = call.engine.run(_sql("award_notices"), {"refs": ",".join(refs), "as_of": call.as_of}) if refs else None
    notices = [dict(zip(result.columns, row, strict=True)) for row in result.rows] if result else []

    rows, with_notice, with_rejection = [], set(), set()
    groups: dict[str, set[str]] = {}
    for notice in notices:
        with_notice.add(notice["step_reference"])
        language = LANGUAGES.get(str(notice["notice_language"] or "").strip().lower(), "en")
        for place, (reason, bids) in enumerate(notice_reasons(notice["notice_text"] or ""), 1):
            key = reason_item(reason, items)
            with_rejection.add(notice["step_reference"])
            groups.setdefault(key, set()).add(notice["step_reference"])
            rows.append({
                "evidence_id": reason_evidence_id(notice["notice_id"], place),
                "public_from": _iso(notice["public_from"]),
                "source": {"notice_id": notice["notice_id"], "notice_type": "Contract Award",
                           "project_id": notice["project_id"]},
                "step_reference": notice["step_reference"],
                "country_name": notice["country_name"],
                "notice_id": notice["notice_id"],
                "notice_date": _iso(notice["notice_date"]),
                "item_key": key,
                "reason": {"text": reason, "lang": language},
                "bids": bids,
                "rank": None,
            })
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    order = [item.key for item in items.items]
    group_rows = sorted(({"item_key": key, "count": len(packages),
                          "rows": sum(1 for row in rows if row["item_key"] == key)} for key, packages in groups.items()),
                        key=lambda group: (-group["count"], order.index(group["item_key"])))
    missing = [f"strata.gold.package:{ref}" for ref in refs if ref not in with_notice]
    coverage = {"matched": len(refs), "used": len(with_notice),
                "not_used": [{"reason": "no_award_notice", "count": len(missing), "evidence_ids": missing}] if missing else []}
    counts = {"total": len(refs), "m": len(with_notice), "n": len(with_rejection)}
    found = {"rows": rows, "coverage": coverage, "counts": counts, "groups": group_rows, "sources": _sources(),
             "records_through": max((_iso(notice["notice_date"]) for notice in notices), default=None)}
    if not refs:
        return {**found, "abstention": {"reason": "no_comparables"}}
    if not with_notice:
        return {**found, "abstention": {"reason": "no_award_notices", "total": len(refs)}}
    return {**found, "abstention": None}
