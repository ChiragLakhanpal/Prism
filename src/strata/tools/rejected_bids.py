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
- groups count the packages under each item, most packages first, then the registry's order, with other
  reasons last whatever its count, as a Pareto list keeps its catch-all last. A package can sit in more than one
  group.

Rows come newest award notice first, then STEP reference, then the order the notice lists its reasons.
"""

from __future__ import annotations

import datetime as dt

from strata.config import load_criteria_items
from strata.criteria.reading import reason_item, rejection_reasons
from strata.lakehouse.passages import LANGUAGES
from strata.tools import common
from strata.tools.common import iso as _iso
from strata.tools.registry import Call

TOOL = "rejected_bids"
OTHER = "other"
# A notice's language by its name, as the notice passages read it (strata.lakehouse.passages.LANGUAGES, the one
# list): a reason in a language the list does not name, or with none, is taken as English, as notices are.
LANGUAGE_CODES = {name.lower(): code for name, code in LANGUAGES.items()}


def reason_evidence_id(notice_id: str, place: int) -> str:
    return f"strata.gold.notice:{notice_id}/reason/{place}"


def notice_reasons(text: str) -> list[tuple[str, int]]:
    """An award notice's distinct reasons, in the order it first gives each, with how many bids each rejected."""
    counted: dict[str, int] = {}
    for reason in rejection_reasons(text):
        counted[reason] = counted.get(reason, 0) + 1
    return list(counted.items())


def read_award_notice(engine, key: str, as_of: dt.date) -> dict | None:
    """One award notice as the evidence drawer shows it from a rejected-bid row (strata.gold.notice:{notice_id}/
    reason/{k}): its type, date, STEP reference and project, and the reason that row quoted, highlighted, with how
    many bids it rejected for it. Like the rows, it never names a bidder. None when no award notice has the id by
    the as-of date, or the notice gives no such reason."""
    notice_id, _, rest = key.partition("/")
    place = int(rest.split("/")[-1]) if rest.startswith("reason/") and rest.split("/")[-1].isdigit() else None
    result = engine.run(common.sql(TOOL, "award_notice"), {"notice_id": notice_id, "as_of": as_of})
    if not result.rows:
        return None
    notice = dict(zip(result.columns, result.rows[0], strict=True))
    reasons = notice_reasons(notice["notice_text"] or "")
    if place is not None and not 0 < place <= len(reasons):
        return None
    fields = [{"key": "notice_type", "value": "Contract Award", "kind": "text"},
              {"key": "published", "value": _iso(notice["notice_date"]), "kind": "date"},
              {"key": "bid_reference", "value": notice["step_reference"], "kind": "text"},
              {"key": "project_id", "value": notice["project_id"], "kind": "text"}]
    if place is not None:
        reason, bids = reasons[place - 1]
        fields += [{"key": "reason_for_rejection", "value": reason, "kind": "text", "highlight": True},
                   {"key": "bids_rejected", "value": str(bids), "kind": "text"}]
    return {"kind": "record", "row": {
        "reference": notice_id, "notice_id": notice_id, "fields": fields, "public_from": _iso(notice["public_from"]),
        "source": {"source_key": "award_notices", "document_type": "Contract Award", "project_id": notice["project_id"],
                   "document_date": _iso(notice["notice_date"])}}}


def rejected_bids(call: Call, comparables: str) -> dict:
    refs = common.references(comparables)
    items = load_criteria_items()
    notices = common.rows(call, TOOL, "award_notices", refs=",".join(refs)) if refs else []

    rows, with_notice, with_rejection = [], set(), set()
    groups: dict[str, set[str]] = {}
    for notice in notices:
        with_notice.add(notice["step_reference"])
        language = LANGUAGE_CODES.get(str(notice["notice_language"] or "").strip().lower(), "en")
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
                "reason": {"quote": reason, "lang": language},
                "bids": bids,
                "rank": None,
            })
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    order = [item.key for item in items.items]
    group_rows = sorted(({"item_key": key, "count": len(packages),
                          "rows": sum(1 for row in rows if row["item_key"] == key)} for key, packages in groups.items()),
                        key=lambda group: (group["item_key"] == OTHER, -group["count"], order.index(group["item_key"])))
    missing = [f"strata.gold.package:{ref}" for ref in refs if ref not in with_notice]
    coverage = {"matched": len(refs), "used": len(with_notice),
                "not_used": [{"reason": "no_award_notice", "count": len(missing), "evidence_ids": missing}] if missing else []}
    counts = {"total": len(refs), "m": len(with_notice), "n": len(with_rejection)}
    found = {"rows": rows, "coverage": coverage, "counts": counts, "groups": group_rows,
             "sources": common.sources(TOOL), "records_through": common.records_through(call)}
    if not refs:
        return {**found, "abstention": {"reason": "no_comparables"}}
    if not with_notice:
        return {**found, "abstention": {"reason": "no_award_notices", "total": len(refs)}}
    return {**found, "abstention": None}
