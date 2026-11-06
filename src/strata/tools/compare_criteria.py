"""compare_criteria: your qualification criteria, item by item, against comparable notices whose criteria are
public (ticket 31; spec user story 29, and "Reading documents": "Notices' scope and qualification text is indexed
as passages too, so criteria can be compared").

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its adapter.

- The comparables are the STEP references the call names, as find_comparables returned them. A package not
  signed by the as-of date may be a tender that is still open, and Prism never comments on one (the refusal
  live_tenders), so its notice is never read: it is left out and counted (still_open).
- A comparable's criteria are public when the passages of its specific procurement notice (ticket 18's notice
  passages, strata.gold.passage of kind notice_text) set a requirement for at least one criterion item of the
  item registry (config/criteria_items.toml, read by strata.criteria.reading). The rest are counted
  (no_public_criteria).
- Each row is one comparable whose criteria are public: its notice, the requirements it sets (each the sentence
  word for word with its place in its passage, which the row carries as a citable record), and, for each of
  your items it states, how its requirement compares with yours (strata.criteria.reading.relation): less,
  same, more, or different when it set the item in other terms. For each item, a notice's requirement that
  states most of your parts is the one compared (compared_requirement), and it carries compared = true.
- items, your items as the criteria reader read them (a JSON list of {item_key, parts}), is optional: without
  it the tool counts the comparables whose criteria are public, for the section's collapsed summary.
- The summary's counts per item are tool columns (CLAUDE.md rule 1): stated, compared (put in order), less,
  same, more, different, same_or_less and not_stated, each a count of the rows.

No amount is converted: no exchange-rate source is registered, so a notice's amount in another currency sets
the item in other terms, and fx_count stays 0. Rows come newest notice first, then STEP reference.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation

from strata.config import CriteriaItems, load_criteria_items
from strata.criteria import reading
from strata.tools import common
from strata.tools.common import iso as _iso
from strata.tools.registry import Call, ToolError

TOOL = "compare_criteria"
PASSAGES = "strata.gold.passage"
REASONS = ("still_open", "no_notice", "no_public_criteria")


def _place(passage_id: str) -> tuple[int, int, str]:
    """A notice passage's order in its notice: s3 before s10, and s3/1 before s3/2."""
    found = re.search(r"/s(\d+)(?:/(\d+))?$", passage_id)
    return (int(found.group(1)), int(found.group(2) or 0), passage_id) if found else (10**6, 0, passage_id)


def your_items(text: str | None, items: CriteriaItems) -> list[dict]:
    """Your items as the call gives them, checked against the item registry: each a criterion item, once, with
    only the parts its kind measures, each a positive number (an amount with its currency)."""
    if text is None:
        return []
    try:
        given = json.loads(text)
    except json.JSONDecodeError as error:
        raise ToolError(f"{TOOL} takes items as a JSON list: {error}.") from error
    if not isinstance(given, list):
        raise ToolError(f"{TOOL} takes items as a JSON list of {{item_key, parts}}.")
    found, seen = [], set()
    for entry in given:
        key = entry.get("item_key") if isinstance(entry, dict) else None
        if not isinstance(key, str) or not items.has(key) or not items.item(key).is_criterion:
            raise ToolError(f"{TOOL} compares only the item registry's criteria, not {key!r}.")
        if key in seen:
            raise ToolError(f"{TOOL} takes each item once; {key} came twice.")
        seen.add(key)
        item, parts = items.item(key), entry.get("parts") or {}
        if not isinstance(parts, dict) or set(parts) - set(item.parts):
            raise ToolError(f"{TOOL}: {key} measures only {', '.join(item.parts) or 'nothing'}.")
        kept = {}
        for part, value in parts.items():
            if value is None:
                continue
            try:
                if part == "amount":
                    amount = Decimal(str(value["value"]))
                    currency = str(value.get("currency") or reading.USD).upper()
                    if amount <= 0:
                        raise ValueError
                    kept[part] = {"value": str(amount), "currency": currency}
                else:
                    number = int(value)
                    if number <= 0:
                        raise ValueError
                    kept[part] = number
            except (TypeError, ValueError, KeyError, InvalidOperation) as error:
                raise ToolError(f"{TOOL}: {key}'s {part} must be a positive number.") from error
        found.append({"item_key": key, "parts": kept})
    return found


def compared_requirement(requirements: list[dict], item: dict) -> dict | None:
    """The one requirement of a notice compared with your item: of its requirements for the item, the one that
    states most of the parts your item sets, and of those the first in passage order. A notice that states the
    item in a heading sentence first ("the following qualifications and experience:") and then with its numbers
    is compared on its numbers."""
    candidates = [requirement for requirement in requirements if requirement["item_key"] == item["item_key"]]
    if not candidates:
        return None
    def stated(requirement: dict) -> int:
        return sum(1 for part in item["parts"] if requirement["parts"].get(part) is not None)
    return max(candidates, key=lambda requirement: (stated(requirement), -candidates.index(requirement)))


def compare_criteria(call: Call, comparables: str, items: str | None = None) -> dict:
    refs = common.references(comparables)
    registry = load_criteria_items()
    mine = your_items(items, registry)
    packages = common.rows(call, TOOL, "packages", refs=",".join(refs)) if refs else []
    by_ref = {row["step_reference"]: row for row in packages}
    signed = common.signed(call, refs)

    left_out = {reason: [] for reason in REASONS}
    readable = []
    for ref in refs:
        package = by_ref.get(ref)
        evidence = f"strata.gold.package:{ref}"
        if package is None or not signed.get(ref):
            left_out["still_open"].append(evidence)
        elif not package["notice_id"]:
            left_out["no_notice"].append(evidence)
        else:
            readable.append(package)
    notices = ",".join(package["notice_id"] for package in readable)
    passages: dict[str, list[dict]] = {}
    for passage in (common.rows(call, TOOL, "passages", notices=notices) if readable else []):
        passages.setdefault(passage["notice_id"], []).append(passage)

    rows = []
    for package in readable:
        found = []
        for passage in sorted(passages.get(package["notice_id"], []), key=lambda row: _place(row["passage_id"])):
            for requirement in reading.requirements(passage["text"] or "", passage["section_path"], registry):
                found.append({
                    "evidence_id": f"{PASSAGES}:{passage['passage_id']}",
                    "public_from": _iso(passage["public_from"]),
                    "source": {"notice_id": package["notice_id"], "project_id": passage["project_id"]},
                    "passage_id": passage["passage_id"], "kind": "notice_text", "notice_id": package["notice_id"],
                    "project_id": passage["project_id"], "section_path": passage["section_path"],
                    "language": passage["language"], "text": passage["text"],
                    "item_key": requirement.item_key,
                    "requirement": {"text": requirement.text, "start": requirement.start, "end": requirement.end},
                    "parts": requirement.parts,
                    "compared": False,  # whether it is the requirement compared with your item
                })
        if not found:
            left_out["no_public_criteria"].append(f"strata.gold.package:{package['step_reference']}")
            continue
        relations = {}
        for item in mine:
            compared = compared_requirement(found, item)
            if compared is not None:
                compared["compared"] = True
                relations[item["item_key"]] = reading.relation(item["parts"], compared["parts"])
        rows.append({
            "evidence_id": f"strata.gold.package:{package['step_reference']}/criteria",
            "public_from": max(requirement["public_from"] for requirement in found),
            "source": {"notice_id": package["notice_id"], "project_id": package["project_id"]},
            "step_reference": package["step_reference"],
            "country_name": package["country_name"],
            "notice_id": package["notice_id"],
            "notice_date": _iso(package["notice_date"]),
            "requirements": found,
            "relations": relations,
            "rank": None,
        })
    rows.sort(key=lambda row: row["step_reference"])
    rows.sort(key=lambda row: row["notice_date"] or "", reverse=True)  # newest first; a tie keeps reference order
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank

    summary_items = []
    for item in mine:
        relations = [row["relations"][item["item_key"]] for row in rows if item["item_key"] in row["relations"]]
        less, same, more, different = (relations.count(name) for name in reading.RELATIONS)
        summary_items.append({"item_key": item["item_key"], "stated": len(relations), "compared": less + same + more,
                              "less": less, "same": same, "more": more, "different": different,
                              "same_or_less": less + same, "not_stated": len(rows) - len(relations)})
    not_used = [{"reason": reason, "count": len(ids), "evidence_ids": ids} for reason, ids in left_out.items() if ids]
    coverage = {"matched": len(refs), "used": len(rows), "not_used": not_used}
    counts = {"n": len(rows), "total": len(refs), "open": len(left_out["still_open"]),
              "missing": len(left_out["no_public_criteria"]) + len(left_out["no_notice"]), "fx_count": 0}
    found = {"rows": rows, "coverage": coverage, "items": summary_items, "counts": counts,
             "sources": common.sources(TOOL), "records_through": common.records_through(call)}
    if not refs:
        return {**found, "abstention": {"reason": "no_comparables"}}
    if not rows:
        return {**found, "abstention": {"reason": "none_public", "total": len(refs)}}
    return {**found, "abstention": None}
