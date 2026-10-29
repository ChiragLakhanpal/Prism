"""The contract trail: one activity from its plan row to its notice, bids, contract and the report paragraphs that
appeared together with the contract (ticket 22; the 22 brief, sections 2 and 10).

activity_trail() reads it all in one call, as the viewer and as of the page's date, from stored records and the
edge table, with no model. It gives the activity's header, the lead's parts, and five stages in procurement order:
in the Procurement Plan, the notices, the bids the award notices list, the contracts, and the paragraphs. A stage
with a record gives each record with its evidence id, its public date and its source line's fields; a stage with
none gives a reason code instead, which the copy file turns into one first-person sentence:

- plan: not_read (no plan Strata read lists it), after_asof (a plan listing it was public only later);
- notice: method_no_notice and approach_no_notice (its Method or Market Approach uses none), none_found,
  after_asof;
- bids: individual_consultant (the name is withheld here, never by the browser), direct_selection, none_found,
  after_asof;
- contract: none_found, after_asof;
- paragraphs: no_contract, no_links (with the threshold and the documents read), after_asof.

Each join says how it was made (joined_on): key for records that share the STEP reference, together for the
scored link to a paragraph. Bids keep the award notice's own order, prices as it writes them, and the Reason for
Rejection word for word. Nothing scores, ranks or profiles a supplier: no supplier ID leaves this module, and an
individual consultant is never named. The page counts nothing: the lead's counts and its parts are here.

read_notice and read_contract open a notice and a contract in the evidence drawer by their evidence ids; a plan row
opens through the rebidding block's reader with activity_links added (strata.server.evidence).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from decimal import Decimal
from functools import cache
from pathlib import Path

from strata.config import load_sources, load_thresholds
from strata.lakehouse.engine import Engine
from strata.reader.templates import template_for
from strata.server import documents
from strata.server.projects import display_name
from strata.server.viewer_sql import data_through
from strata.tools.find_comparables import read_package

SQL = Path(__file__).resolve().parent / "sql" / "trail"
AWARD = "Contract Award"
CONSULTANTS = "Consultant Services"
INDIVIDUAL = "Individual Consultant Selection"
OUTCOMES = {"awarded": "awarded", "evaluated": "not_awarded", "rejected": "rejected"}
# Where each kind of record comes from in the source registry, for its source line's dataset (config/sources.toml).
DATASETS = {"notices": "notices", "award_notices": "notices", "awards": "awards",
            "awards_fy2001_2016": "awards_fy2001_2016"}
LATEST = dt.date(9999, 12, 31)


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_query(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _day(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _iso(value) -> str | None:
    day = _day(value)
    return day.isoformat() if day else None


def _money(value) -> str | None:
    """An amount as its record writes it, with its cents: 1245092.76."""
    if value is None or value == "":
        return None
    return f"{Decimal(str(value)):.2f}"


def _true(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def dataset(key: str) -> dict:
    """How the World Bank credits a source, for a record's source line (the source registry's attribution)."""
    source = load_sources()[DATASETS.get(key, key)]
    return {"source_key": key, "dataset_name": source.dataset_name, "license": source.license,
            "data_source": source.attribution.data_source if source.attribution else None,
            "record_url": source.record_url}


def notice_url(notice_id: str) -> str | None:
    """A notice's own page on the World Bank's site (search_passages.notice_page, the one definition)."""
    from strata.tools.search_passages import notice_page

    return notice_page(notice_id)


def activity_href(project_id: str | None, reference: str | None) -> str | None:
    """The activity page of a STEP reference, under its project (docs/PLAN.md section 8)."""
    return f"/projects/{project_id}/packages/{reference}" if project_id and reference else None


def activity_links(project_id: str | None, reference: str | None) -> dict:
    """What a record opened in the drawer needs for its "Open the activity" link."""
    return {"record_kind": "activity", "step_reference": reference, "project_id": project_id,
            "activity_href": activity_href(project_id, reference)}


def paragraph_key(passage_id: str) -> str:
    """The paragraph a passage belongs to: a long paragraph is read as parts that share its number, such as
    27348420/v1/annex3.62/1 and /2, so its key leaves the part off (27348420/v1/annex3.62)."""
    return "/".join(passage_id.split("/")[:3])


def _field(key: str, value, kind: str = "text") -> dict | None:
    return None if value is None or value == "" else {"key": key, "value": value, "kind": kind}


def _fields(*fields) -> list[dict]:
    return [field for field in fields if field is not None]


# ── The stages ───────────────────────────────────────────────────────────

def _plan_stage(engine: Engine, reference: str, as_of: dt.date) -> tuple[dict, dict | None]:
    package = read_package(engine, reference, as_of)
    if package is None:
        later = read_package(engine, reference, LATEST) is not None
        return {"stage": "plan", "found": False, "joined_on": "key", "reason": "after_asof" if later else "not_read", "records": []}, None
    plan = package["plan"]
    steps = [{"step": row["step"], "first_planned_on": _iso(row["first_planned_on"]), "actual_on": _iso(row["actual_on"])}
             for row in _rows(engine, "plan_steps", document_id=plan["document_id"], reference=reference)]
    first = next((_iso(row["first_planned_plan_date"]) for row in _rows(
        engine, "plan_steps", document_id=plan["document_id"], reference=reference) if row["first_planned_plan_date"]), None)
    record = {
        "evidence_id": package["evidence_id"], "public_from": package["public_from"],
        "description": package["description"], "method": package["method"],
        "market_approach": package["market_approach"], "review_type": package["review_type"],
        "estimated_amount_usd": package["estimated_amount_usd"], "process_status": package["process_status"],
        "fields": _fields(_field("method", package["method"]), _field("market_approach", package["market_approach"]),
                          _field("review_type", package["review_type"]),
                          _field("estimated_amount_usd", package["estimated_amount_usd"], "usd"),
                          _field("process_status", package["process_status"])),
        "steps": steps, "first_plan_date": first, "plan_date": plan["plan_date"], "agency_id": plan["agency_id"],
        "implementing_agency": plan["implementing_agency"],
        "source": {"document_type": "Procurement Plan", "project_id": package["project_id"],
                   "implementing_agency": plan["implementing_agency"], "plan_date": plan["plan_date"],
                   "disclosed_on": plan["disclosed_on"], "document_id": plan["document_id"],
                   "pdf_page": plan["pdf_page"]},
    }
    return {"stage": "plan", "found": True, "reason": None, "joined_on": "key", "records": [record]}, package


def _notice_record(row: dict, again: bool) -> dict:
    return {
        "evidence_id": f"strata.gold.notice:{row['notice_id']}", "public_from": _iso(row["public_from"]),
        "notice_id": row["notice_id"], "notice_type": row["notice_type"], "notice_date": _iso(row["notice_date"]),
        "readvertised": again, "url": notice_url(row["notice_id"]),
        "fields": _fields(_field("notice_type", row["notice_type"]), _field("published", _iso(row["notice_date"]), "date"),
                          _field("procurement_method", row["procurement_method_as_written"]),
                          _field("submission_deadline", _iso(row["submission_deadline"]), "date"),
                          _field("bid_description", row["bid_description"])),
        "source": {**dataset("notices"), "document_type": row["notice_type"], "project_id": row["project_id"],
                   "document_date": _iso(row["notice_date"])},
    }


def _notice_stage(notices: list[dict], method: str | None, approach: str | None) -> dict:
    shown = [row for row in notices if row["notice_type"] != AWARD and _true(row["public_then"])]
    if shown:
        seen: dict[str, int] = {}
        records = []
        for row in shown:
            seen[row["notice_type"]] = seen.get(row["notice_type"], 0) + 1
            records.append(_notice_record(row, seen[row["notice_type"]] > 1))
        return {"stage": "notice", "found": True, "reason": None, "joined_on": "key", "records": records}
    # A Method or a Market Approach that invites firms directly has no public notice, so none is missing (the 22
    # brief, 2.7). The thresholds file's one list says which, for the past range too.
    limits = load_thresholds()
    if any(row["notice_type"] != AWARD for row in notices):
        reason = "after_asof"
    elif method in limits.value("past_range.no_notice_methods"):
        reason = "method_no_notice"
    elif approach and any(approach.startswith(word) for word in limits.value("past_range.no_notice_market_approaches")):
        reason = "approach_no_notice"
    else:
        reason = "none_found"
    return {"stage": "notice", "found": False, "joined_on": "key", "reason": reason, "records": [], "method": method,
            "market_approach": approach}


def _bids_stage(engine: Engine, notices: list[dict], method: str | None, consultants: bool, reference: str) -> dict:
    awards = [row for row in notices if row["notice_type"] == AWARD]
    shown = [row for row in awards if _true(row["public_then"])]
    individual = method == INDIVIDUAL or reference.upper().endswith("-INDV") or "-CS-INDV" in reference.upper()
    if individual:
        return {"stage": "bids", "found": False, "joined_on": "key", "reason": "individual_consultant", "records": []}
    if not shown:
        reason = "after_asof" if awards else "direct_selection" if method == "Direct Selection" else "none_found"
        return {"stage": "bids", "found": False, "joined_on": "key", "reason": reason, "records": []}
    bids_by_notice: dict[str, list[dict]] = {}
    for row in _rows(engine, "bids", notices=",".join(row["notice_id"] for row in shown)):
        bids_by_notice.setdefault(row["notice_id"], []).append(row)
    records = []
    for notice in shown:
        listed = bids_by_notice.get(notice["notice_id"], [])
        grouped: dict[int, list[dict]] = {}
        for row in listed:
            grouped.setdefault(int(row["bid"]), []).append(row)
        bids = []
        for number, members in grouped.items():
            first = members[0]
            named = [member["name"] for member in members if member["name"]]
            bids.append({
                "bid": number, "outcome": OUTCOMES.get(first["section"], "none"),
                "name": named[0] if len(members) == 1 and named else None,
                "is_individual_consultant": any(_true(member["individual_consultant"]) for member in members),
                "is_joint_venture": len(members) > 1, "members": named if len(members) > 1 else [],
                "country": first["country"], "price_at_opening": first["price_at_opening"],
                "evaluated_price": first["evaluated_price"], "reason": first["reason"],
            })
        first = listed[0] if listed else {}
        records.append({
            "evidence_id": f"strata.gold.notice:{notice['notice_id']}", "public_from": _iso(notice["public_from"]),
            "notice_id": notice["notice_id"], "notice_date": _iso(notice["notice_date"]),
            "currency": first.get("currency") or notice["signed_contract_currency"],
            "labels": {"price_at_opening": first.get("price_at_opening_label"),
                       "evaluated_price": first.get("evaluated_price_label")},
            "lists_scores": any(_true(row["notice_lists_scores"]) for row in listed),
            "proposals": consultants, "bids": bids, "bid_count": len(bids), "url": notice_url(notice["notice_id"]),
            "source": {**dataset("award_notices"), "document_type": AWARD, "project_id": notice["project_id"],
                       "document_date": _iso(notice["notice_date"])},
        })
    return {"stage": "bids", "found": True, "reason": None, "joined_on": "key", "records": records}


def _supplier(row: dict) -> dict:
    """A contract's supplier as plain text: never named for an individual consultant, and a joint venture with its
    members in the order its name gives them ("A / B"), as the bids table lists a joint venture's members."""
    individual = row["supplier_kind"] == "individual consultant"
    venture = row["supplier_kind"] == "joint venture"
    name = None if individual else row["supplier_name"]
    members = [member.strip() for member in name.split(" / ") if member.strip()] if venture and name else []
    return {"name": name, "country": row["supplier_country"], "is_individual_consultant": individual,
            "is_joint_venture": venture, "members": members}


def _contract_record(row: dict) -> dict:
    from_notice = row["source"] == "notices"
    amount, currency = ((_money(row["contract_amount"]), row["contract_currency"]) if from_notice
                        else (_money(row["contract_amount_usd"]), "USD"))
    reference = row["wb_contract_number"] or row["award_notice_id"] or row["contract_id"]
    return {
        "evidence_id": f"strata.gold.contract:{row['contract_id']}", "public_from": _iso(row["public_from"]),
        "contract_id": row["contract_id"], "contract_reference": reference, "step_reference": row["step_reference"],
        "signed_on": _iso(row["contract_signing_date"]), "amount": amount, "currency": currency,
        "from_notice": from_notice, "record_noun": "award notice" if from_notice else "contract",
        "award_notice_id": row["award_notice_id"], "description": row["contract_description"],
        "supplier": _supplier(row),
        "source": {**dataset(row["source"]), "document_type": AWARD if from_notice else "Contract award",
                   "project_id": row["project_id"], "document_date": _iso(row["contract_signing_date"])},
    }


def _contract_stage(contracts: list[dict]) -> dict:
    shown = [row for row in contracts if _true(row["public_then"])]
    if shown:
        return {"stage": "contract", "found": True, "reason": None, "joined_on": "key",
                "records": [_contract_record(row) for row in shown]}
    return {"stage": "contract", "found": False, "joined_on": "key", "reason": "after_asof" if contracts else "none_found", "records": []}


def topics(category: str | None, sector_code: str | None, sector_name: str | None, mentions: list[dict]) -> list[dict]:
    """What a link's paragraph and contract both concern, in the order "Why this source" names them: the
    procurement category when the paragraph mentions it, the project's sector, then the places and the
    contract's name as the paragraph writes them (the 22 brief, section 4.2). The screen maps the codes."""
    found = []
    if any(mention["kind"] == "category" for mention in mentions) and category:
        found.append({"kind": "category", "code": category})
    if sector_code:
        found.append({"kind": "sector", "code": sector_code, **({"name": sector_name} if sector_name else {})})
    found += [{"kind": mention["kind"], "text": mention["text"]} for mention in mentions
              if mention["kind"] in ("place", "name")]
    return found


def _coverage(engine: Engine, project_id: str, as_of: dt.date) -> dict | None:
    """How many of the project's listed documents I read, for the coverage line (DESIGN.md section 5)."""
    tab = documents.documents_tab(engine, project_id, as_of, 0)
    if tab is None:
        return None
    entries = [entry for group in tab["groups"] for entry in group["documents"]]
    return {"read": sum(1 for entry in entries if entry["read"]), "total": len(entries), "source_key": "documents"}


def document_labels(document_type: str | None) -> dict:
    """A document's stratum and short name, from the reader's templates: Why and ICR for a completion report."""
    template = template_for(document_type or "")
    return {"stratum": template.stratum if template else "Why",
            "short_name": template.short_name if template else (document_type or None)}


def passage_card(row: dict) -> dict:
    mentions = json.loads(row["mentions"] or "[]")
    return {
        **document_labels(row["document_type"]),
        "evidence_id": row["evidence_id"], "public_from": _iso(row["public_from"]), "passage_id": row["passage_id"],
        "contract_evidence_id": row["contract_evidence_id"], "document_id": row["document_id"],
        "document_type": row["document_type"], "title_section": None, "title_page": None,
        "document_date": _iso(row["document_date"]), "paragraph": row["paragraph"],
        "paragraph_numbered": _true(row["paragraph_numbered"]), "section_path": row["section_path"],
        "pdf_page": row["pdf_page"], "printed_page": row["printed_page"], "doc_key": row["doc_key"],
        "language": row["language"], "text": row["text"],
        "highlights": [[mention["start"], mention["end"]] for mention in mentions],
        "topics": topics(row["category"], row["sector_code"], row["sector_name"], mentions),
        "source": {"document_type": row["document_type"], "project_id": row["project_id"],
                   "document_date": _iso(row["document_date"]), "pdf_page": row["pdf_page"]},
    }


def _in_document_order(card: dict) -> tuple:
    """A card's place in its report: its page, then its paragraph id read with its numbers as numbers."""
    parts = re.split(r"(\d+)", card["passage_id"])
    return (card["pdf_page"] or 0, [int(part) if part.isdigit() else part for part in parts])


def _tell_titles_apart(cards: list[dict]) -> None:
    """Cards of one report that would share a title say what tells them apart: a paragraph number used again in an
    annex names its section ("Annex 2.A, paragraph 27"), and a section name used twice names its page."""
    titles: dict[tuple, list[dict]] = {}
    for card in cards:
        titles.setdefault((card["paragraph_numbered"], card["paragraph"] if card["paragraph_numbered"]
                           else card["section_path"]), []).append(card)
    for alike in (group for group in titles.values() if len(group) > 1):
        sections = {card["section_path"] for card in alike}
        for card in alike:
            if card["paragraph_numbered"] and len(sections) == len(alike):
                card["title_section"] = card["section_path"]
            else:
                card["title_page"] = card["pdf_page"]


def _paragraph_stage(engine: Engine, contract_stage: dict, contracts: list[dict], project_id: str,
                     as_of: dt.date) -> dict:
    limits = load_thresholds()
    threshold = f"{Decimal(str(limits.value('links.threshold'))):.2f}"
    if not contract_stage["found"]:
        return {"stage": "paragraphs", "found": False, "joined_on": "together", "records": [], "groups": [],
                "threshold": threshold, "reason": "after_asof" if contracts else "no_contract"}
    ids = [record["evidence_id"] for record in contract_stage["records"]]
    references = {record["evidence_id"]: record["contract_reference"] for record in contract_stage["records"]}
    # One card a paragraph: a paragraph read as parts shows its strongest part, as the edge to it scored.
    cards: dict[str, dict] = {}
    for row in _rows(engine, "paragraphs", contracts=",".join(ids), as_of=as_of):
        key = paragraph_key(row["passage_id"])
        card = cards.get(key)
        if card is None or Decimal(str(row["score"])) > Decimal(card["score"]):
            cards[key] = {**passage_card(row), "score": str(row["score"]),
                          "contract_reference": references.get(row["contract_evidence_id"])}
    if not cards:
        return {"stage": "paragraphs", "found": False, "joined_on": "together", "records": [], "groups": [],
                "threshold": threshold, "reason": "no_links", "coverage": _coverage(engine, project_id, as_of)}
    # Grouped by report, oldest first, each in document order: the order says what was known when and ranks nothing.
    by_report: dict[str, list[dict]] = {}
    for card in sorted(cards.values(), key=lambda card: (card["document_date"] or "", card["document_id"])):
        card.pop("score")
        by_report.setdefault(card["document_id"], []).append(card)
    shown = int(limits.value("contract_trail.paragraphs_per_report"))
    records, groups = [], []
    for document_id, mine in by_report.items():
        mine.sort(key=_in_document_order)
        _tell_titles_apart(mine)
        records += mine
        first = mine[0]
        groups.append({"document_id": document_id, "document_type": first["document_type"],
                       "short_name": first["short_name"], "stratum": first["stratum"],
                       "document_date": first["document_date"], "count": len(mine), "shown": min(len(mine), shown)})
    return {"stage": "paragraphs", "found": True, "reason": None, "joined_on": "together", "records": records,
            "groups": groups, "threshold": threshold}


def _lead(stages: dict[str, dict]) -> dict:
    plan, notice, bids, contract = (stages[name] for name in ("plan", "notice", "bids", "contract"))
    parts = []
    record = plan["records"][0] if plan["found"] else None
    if record and record["estimated_amount_usd"]:
        parts.append({"kind": "estimated", "amount": record["estimated_amount_usd"], "currency": "USD",
                      "evidence_id": record["evidence_id"]})
    if notice["found"]:
        first = notice["records"][0]
        parts.append({"kind": "advertised", "date": first["notice_date"], "evidence_id": first["evidence_id"],
                      "reference": first["notice_id"]})
    signed = [record for record in contract["records"] if record["signed_on"]]
    if len(signed) == 1:
        parts.append({"kind": "signed", "date": signed[0]["signed_on"], "amount": signed[0]["amount"],
                      "currency": signed[0]["currency"], "evidence_id": signed[0]["evidence_id"],
                      "reference": signed[0]["contract_reference"], "record_noun": signed[0]["record_noun"]})
    elif len(signed) > 1:
        parts.append({"kind": "signed_many", "count": len(signed), "first_date": signed[0]["signed_on"],
                      "last_date": signed[-1]["signed_on"], "evidence_id": signed[0]["evidence_id"]})
    no_notice = not notice["found"] and notice["reason"] in ("none_found", "after_asof")
    missing = ("notice_and_contract" if no_notice and not contract["found"] else "notice" if no_notice
               else "contract" if not contract["found"] else None)
    # Each award notice's bids, in date order, so the lead counts every notice's, not only the first's.
    listed = [{"count": award["bid_count"], "notice_id": award["notice_id"], "evidence_id": award["evidence_id"],
               "proposals": award["proposals"]} for award in bids["records"] if award["bids"]]
    return {"parts": parts, "no_estimate": bool(record) and not record["estimated_amount_usd"], "missing": missing,
            "bids": listed, "many_contracts": len(contract["records"]) > 1,
            "paragraphs": len(stages["paragraphs"]["records"]) if contract["found"] else None}


def _first(rows: list[dict], column: str):
    """The first value a column holds in these rows, or None."""
    return next((row[column] for row in rows if row[column]), None)


def activity_trail(engine: Engine, project_id: str, reference: str, as_of: dt.date) -> dict | None:
    """The contract trail of one activity, as of the page's date, or None when no record carries the reference.
    The activity's own project is named, so a page opened under another project can show its own address."""
    reference = reference.strip()
    held = _rows(engine, "activity", reference=reference)
    if not held:
        return None
    owner = held[0]["project_id"]
    plan, package = _plan_stage(engine, reference, as_of)
    notices = _rows(engine, "notices", reference=reference, as_of=as_of)
    contracts = _rows(engine, "contracts", reference=reference, as_of=as_of)
    # The header and the reasons read only the records public on the as-of date (ADR 0002).
    public_contracts = [row for row in contracts if _true(row["public_then"])]
    public_notices = [row for row in notices if _true(row["public_then"])]
    method = (package or {}).get("method") or _first(public_contracts, "procurement_method") \
        or _first(public_notices, "procurement_method")
    approach = (package or {}).get("market_approach") or _first(public_notices, "market_approach")
    category = (package or {}).get("category") or _first(public_contracts, "procurement_category") \
        or _first(public_notices, "procurement_category")
    consultants = category == CONSULTANTS or "-CS-" in reference.upper()
    contract_stage = _contract_stage(contracts)
    stages = {"plan": plan, "notice": _notice_stage(notices, method, approach),
              "bids": _bids_stage(engine, notices, method, consultants, reference), "contract": contract_stage}
    stages["paragraphs"] = _paragraph_stage(engine, contract_stage, contracts, owner, as_of)
    # The activity is named as STEP typed it in its notice when one was public, since the plan reader can split a
    # word inside a plan's cell ("Explor atory"); then as its plan or its contract names it.
    description = _first([row for row in public_notices if row["notice_type"] != AWARD], "bid_description") \
        or _first(public_notices, "bid_description") or (package or {}).get("description") \
        or _first(public_contracts, "contract_description")
    through = data_through(engine)
    return {
        "as_of": as_of.isoformat(),
        "data_through": min(through, as_of).isoformat() if through else None,
        "activity": {"step_reference": reference, "project_id": owner, "project_name": held[0]["project_name"],
                     "display_name": display_name(held[0]["project_name"]) if held[0]["project_name"] else None,
                     "description": description, "method": method, "consultants": consultants,
                     "implementing_agency": (package or {}).get("plan", {}).get("implementing_agency"),
                     "href": activity_href(owner, reference)},
        "moved": owner != project_id,
        "lead": _lead(stages),
        "stages": [stages[name] for name in ("plan", "notice", "bids", "contract", "paragraphs")],
    }


# ── The drawer's records ─────────────────────────────────────────────────

def read_notice(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    """A procurement notice of any type, opened from the trail or from a package advertised again: its own fields,
    never a contact, and, when its text says why the package went out again, that sentence word for word,
    highlighted, as the rebidding block quoted it (ticket 28's review, follow-up 6)."""
    from strata.estimates.rebidding import reason_in

    found = _rows(engine, "notice", notice_id=key, as_of=as_of)
    if not found:
        return None
    row = found[0]
    award = row["notice_type"] == AWARD
    price = (f"{row['signed_contract_currency']} {_money(row['signed_contract_price'])}"
             if award and row["signed_contract_price"] is not None and row["signed_contract_currency"] else None)
    given = reason_in(row["notice_text"] or "")
    fields = _fields(_field("notice_type", row["notice_type"]), _field("published", _iso(row["notice_date"]), "date"),
                     _field("bid_reference", row["bid_reference_no"]),
                     _field("procurement_method", row["procurement_method_as_written"]),
                     _field("submission_deadline", _iso(row["submission_deadline"]), "date") if not award else None,
                     _field("contract_signature_date", _iso(row["contract_signature_date"]), "date") if award else None,
                     _field("signed_contract_price", price), _field("bid_description", row["bid_description"]),
                     {"key": "notice_says", "value": given[1], "kind": "text", "highlight": True} if given else None)
    return {"kind": "record", "row": {
        "reference": row["notice_id"], "notice_id": row["notice_id"], "record_kind": "award_notice" if award else "notice",
        "fields": fields, "public_from": _iso(row["public_from"]), "step_reference": row["step_reference"],
        "project_id": row["project_id"], "activity_href": activity_href(row["project_id"], row["step_reference"]),
        "url": notice_url(row["notice_id"]),
        "source": {"source_key": "award_notices" if award else "notices", "document_type": row["notice_type"],
                   "project_id": row["project_id"], "document_date": _iso(row["notice_date"])}}}


def read_contract(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    """A contract, opened from the trail: its awards dataset's own fields, or its award notice's, and its supplier
    as plain text, never named for an individual consultant."""
    found = _rows(engine, "contract", contract_id=key, as_of=as_of)
    if not found:
        return None
    record = _contract_record({**found[0], "public_then": True})
    supplier = record["supplier"]
    fields = _fields(_field("contract_reference", record["contract_reference"]),
                     _field("signed", record["signed_on"], "date"),
                     _field("supplier", "individual_consultant" if supplier["is_individual_consultant"]
                            else supplier["name"], "supplier"),
                     _field("supplier_country", supplier["country"]),
                     _field("signed_amount", record["amount"], "amount"),
                     _field("contract_description", record["description"]))
    # A contract from an award notice cites the notice, published on its public date; one from an awards dataset
    # cites the dataset on its signing date.
    source_key, dated = (("award_notices", record["public_from"]) if record["from_notice"]
                         else (found[0]["source"], record["signed_on"]))
    return {"kind": "record", "row": {
        "reference": record["contract_reference"], "record_kind": "contract", "fields": fields,
        "currency": record["currency"], "public_from": record["public_from"], "step_reference": record["step_reference"],
        "project_id": found[0]["project_id"], "activity_href": activity_href(found[0]["project_id"], record["step_reference"]),
        "source": {"source_key": source_key, "document_type": record["source"]["document_type"],
                   "project_id": found[0]["project_id"], "document_date": dated}}}
