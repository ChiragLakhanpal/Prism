"""The edge table on screen: a project's Connections tab and "Why this source" in the evidence drawer (ticket 22;
the 22 brief, sections 3, 4 and 10).

neighbourhood() gives a project's one-hop neighbourhood as of the page's date: the project, the packages it plans
and the documents about it, at most connections.max_nodes nodes in all (config/thresholds.toml), chosen by a fixed
priority, the rest counted by kind. The country is left out, since it has no page; a supplier is never a node.
The appeared_together edges between a shown package's contracts and a shown document's paragraphs are the dashed
lines, ending at paragraph chips on the document's node. The tool chooses, orders and counts; the browser draws.

why() explains one passage's link in words from its score's parts: the contract it names (the route's activity
when the page gives one, otherwise the strongest link), what both concern, the project's state on the as-of date,
the months between the signing and the document's date, each part's points, the total, the threshold, where the
shared mentions sit in the paragraph, and up to connections.other_contracts_listed other contracts. It gives
nothing when no link was public on the as-of date.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from functools import cache
from pathlib import Path

from strata.config import Thresholds, load_thresholds
from strata.lakehouse.engine import Engine
from strata.server import documents
from strata.server.trail import activity_href, topics
from strata.server.viewer_sql import data_through

SQL = Path(__file__).resolve().parent / "sql" / "edges"
PARTS = ("project", "sector", "time", "text", "mentions")
# The documents the evidence ladder leans on, in the order the tab prefers them (the 22 brief, section 3.3).
LADDER = ("icr_review", "icr", "pad", "isr")
PLANS = "procurement_plan"


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


def _points(value) -> str | None:
    return None if value is None else f"{Decimal(str(value)):.2f}"


def project_state(status: str | None, closing: dt.date | None, as_of: dt.date) -> str:
    """Whether the project had closed on the as-of date: closed once its record says Closed and its closing date
    had passed, active otherwise."""
    return "closed" if status == "Closed" and (closing is None or closing <= as_of) else "active"


# ── "Why this source" ────────────────────────────────────────────────────

def _named(row: dict) -> dict:
    from_notice = row["source"] == "notices"
    return {"reference": row["step_reference"] or row["wb_contract_number"] or row["award_notice_id"] or row["contract_id"],
            "record_noun": "award notice" if from_notice else "contract", "signed_on": _iso(row["contract_signing_date"]),
            "href": activity_href(row["project_id"], row["step_reference"]), "step_reference": row["step_reference"]}


def why(engine: Engine, passage: dict, step_ref: str | None, as_of: dt.date, limits: Thresholds | None = None) -> dict | None:
    """Why a passage is a source for a contract, in words built from its link's score, or None with no link."""
    limits = limits or load_thresholds()
    links = _rows(engine, "why_links", passage=f"strata.gold.passage:{passage['passage_id']}", as_of=as_of)
    if not links:
        return None
    chosen = next((row for row in links if step_ref and row["step_reference"] == step_ref), links[0])
    mentions = json.loads(chosen["mentions"] or "[]")
    terms = json.loads(chosen["matched_terms"] or "[]")
    matched = {"project": chosen["project_id"], "sector": chosen["sector_name"], "time": chosen["months_apart"],
               "text": terms, "mentions": [mention["text"] for mention in mentions]}
    others = [_named(row) for row in links if row is not chosen]
    listed = int(limits.value("connections.other_contracts_listed"))
    return {
        **_named(chosen),
        "topics": topics(chosen["category"], chosen["sector_code"], chosen["sector_name"], mentions),
        "project_id": chosen["project_id"],
        "project_state": project_state(chosen["project_status"], _day(chosen["project_closing_date"]), as_of),
        "document": {"type": passage["document_type"],
                     "date": _iso(passage.get("document_date") or (passage.get("source") or {}).get("document_date"))},
        "months": chosen["months_apart"], "direction": chosen["time_direction"],
        "components": [{"part": part, "matched": matched[part], "points": _points(chosen[f"score_{part}"])} for part in PARTS],
        "score": _points(chosen["score"]),
        "threshold": _points(limits.value("links.threshold")),
        "mentions": mentions,
        "activity_href": _named(chosen)["href"],
        "others": others[:listed], "others_count": len(others), "others_more": max(len(others) - listed, 0),
        "connections_href": f"/projects/{chosen['project_id']}/connections",
    }


# ── The Connections tab ──────────────────────────────────────────────────

def _document_node(entry: dict, pid: str) -> dict:
    return {"document_id": entry["document_id"], "doc_key": entry["doc_key"], "type": entry["type"],
            "document_type": entry["document_type"], "document_date": entry["document_date"],
            "sequence": entry["sequence"], "agency": entry["agency"],
            "href": f"/projects/{pid}/documents/{entry['doc_key']}", "chips": [], "more_chips": 0}


def _package_node(row: dict, pid: str) -> dict:
    contracts = int(row["contracts"] or 0)
    return {"step_reference": row["step_reference"], "description": row["description"],
            "process_status": row["process_status"], "contracts": contracts,
            "first_signed_on": _iso(row["first_signed_on"]),
            "date": _iso(row["first_signed_on"]) or _iso(row["first_planned_on"]),
            "href": activity_href(pid, row["step_reference"])}


def _ladder(entries: list[dict]) -> list[str]:
    """The documents the evidence ladder leans on: the latest ICR Review, the ICR, the PAD, the latest ISR, and the
    latest Procurement Plan of each implementing agency, by document id."""
    chosen = []
    for group in LADDER:
        mine = sorted((entry for entry in entries if entry["type"] == group), key=lambda entry: entry["document_date"] or "")
        if mine:
            chosen.append(mine[-1]["document_id"])
    agencies: dict[str, dict] = {}
    for entry in entries:
        if entry["type"] == PLANS and (entry["agency"] not in agencies
                                       or (entry["document_date"] or "") > (agencies[entry["agency"]]["document_date"] or "")):
            agencies[entry["agency"]] = entry
    return chosen + [entry["document_id"] for entry in agencies.values()]


def neighbourhood(engine: Engine, project_id: str, as_of: dt.date, limits: Thresholds | None = None) -> dict | None:
    """A project's one-hop neighbourhood as of the page's date, or None for a project Strata has no record of."""
    limits = limits or load_thresholds()
    tab = documents.documents_tab(engine, project_id, as_of, 0)
    if tab is None:
        return None
    pid = project_id
    entries = [entry for group in tab["groups"] for entry in group["documents"]]
    nodes_doc = {entry["document_id"]: entry for entry in entries if entry["doc_key"]}
    packages = {row["step_reference"]: row for row in _rows(engine, "packages", project_id=pid, as_of=as_of)}
    links = [row for row in _rows(engine, "links", project_id=pid, as_of=as_of)
             if row["step_reference"] in packages and row["document_id"] in nodes_doc]
    room = int(limits.value("connections.max_nodes")) - 1

    # The slots, in the brief's order: linked packages and documents, strongest link first; the documents the
    # evidence ladder leans on; signed packages by amount, then unsigned ones by estimate; the other documents.
    order: list[tuple[str, str]] = []
    for row in links:
        for node in (("package", row["step_reference"]), ("document", row["document_id"])):
            if node not in order:
                order.append(node)
    order += [("document", document_id) for document_id in _ladder(list(nodes_doc.values()))]
    signed = sorted((row for row in packages.values() if int(row["contracts"] or 0) > 0),
                    key=lambda row: (-(Decimal(str(row["signed_usd"])) if row["signed_usd"] is not None else Decimal(0)),
                                     row["step_reference"]))
    unsigned = sorted((row for row in packages.values() if int(row["contracts"] or 0) == 0),
                      key=lambda row: (-(Decimal(str(row["estimated_amount_usd"])) if row["estimated_amount_usd"] is not None
                                         else Decimal(-1)), row["step_reference"]))
    order += [("package", row["step_reference"]) for row in signed + unsigned]
    order += [("document", entry["document_id"]) for entry in sorted(nodes_doc.values(),
                                                                     key=lambda entry: entry["document_date"] or "",
                                                                     reverse=True)]
    shown: list[tuple[str, str]] = []
    for node in order:
        if node not in shown and len(shown) < room:
            shown.append(node)
    shown_packages = [_package_node(packages[key], pid) for kind, key in shown if kind == "package"]
    shown_documents = [_document_node(nodes_doc[key], pid) for kind, key in shown if kind == "document"]
    shown_packages.sort(key=lambda node: (node["date"] or "9999", node["step_reference"]))
    shown_documents.sort(key=lambda node: (node["document_date"] or "9999", node["document_id"]))

    # The chips: each document's linked paragraphs, strongest first, at most chips_per_document of them.
    per_document = int(limits.value("connections.chips_per_document"))
    by_document = {node["document_id"]: node for node in shown_documents}
    shown_refs = {node["step_reference"] for node in shown_packages}
    edges, chips = [], {}
    for row in links:
        if row["step_reference"] not in shown_refs or row["document_id"] not in by_document:
            continue
        node = by_document[row["document_id"]]
        chip = chips.get(row["evidence_id"])
        if chip is None:
            if len(node["chips"]) >= per_document:
                continue
            chip = {"evidence_id": row["evidence_id"], "passage_id": row["passage_id"], "paragraph": row["paragraph"],
                    "paragraph_numbered": bool(row["paragraph_numbered"]), "section_path": row["section_path"],
                    "packages": []}
            chips[row["evidence_id"]] = chip
            node["chips"].append(chip)
        if row["step_reference"] not in chip["packages"]:
            chip["packages"].append(row["step_reference"])
            edges.append({"step_reference": row["step_reference"], "evidence_id": row["evidence_id"]})
    for node in shown_documents:
        node["more_chips"] = len({row["evidence_id"] for row in links if row["document_id"] == node["document_id"]
                                  and row["step_reference"] in shown_refs}) - len(node["chips"])
    for node in shown_packages:
        node["linked"] = [{"evidence_id": edge["evidence_id"]} for edge in edges if edge["step_reference"] == node["step_reference"]]

    # The rest, counted by kind, and the finding's counts with what they counted.
    hidden_packages = len(packages) - len(shown_packages)
    shown_ids = {node["document_id"] for node in shown_documents}
    hidden = [entry for entry in entries if entry["document_id"] not in shown_ids]
    more = [{"kind": "packages", "count": hidden_packages}] if hidden_packages else []
    for kind, test in (("isrs", lambda entry: entry["type"] == "isr"), ("plans", lambda entry: entry["type"] == PLANS),
                       ("documents", lambda entry: entry["type"] not in ("isr", PLANS))):
        count = sum(1 for entry in hidden if test(entry))
        if count:
            more.append({"kind": kind, "count": count})
    all_links = _rows(engine, "links", project_id=pid, as_of=as_of)
    contracts = sorted({row["step_reference"] for row in all_links})
    paragraphs = list(dict.fromkeys(row["evidence_id"] for row in all_links))
    documents_linked = list(dict.fromkeys(row["document_id"] for row in all_links))
    about = {row["evidence_id"]: row for row in all_links}
    through = data_through(engine)
    scored = max((row["scored_on"] for row in all_links if row["scored_on"]), default=None)
    total = 1 + len(packages) + len(entries)
    return {
        "as_of": as_of.isoformat(),
        "data_through": min(through, as_of).isoformat() if through else None,
        "scored_date": _iso(scored),
        "project": {"project_id": pid, "display_name": tab["project"]["display_name"]},
        "packages": shown_packages, "documents": shown_documents, "edges": edges, "more": more,
        "finding": {"contracts": len(contracts), "paragraphs": len(paragraphs), "documents": len(documents_linked),
                    "contract_items": contracts,
                    "paragraph_items": [{"document_type": about[key]["document_type"],
                                         "document_date": _iso(about[key]["document_date"]),
                                         "paragraph": about[key]["paragraph"]} for key in paragraphs],
                    "document_items": [next({"document_type": row["document_type"], "document_date": _iso(row["document_date"])}
                                            for row in all_links if row["document_id"] == key) for key in documents_linked]},
        "shown": 1 + len(shown_packages) + len(shown_documents), "total": total,
        "threshold": _points(limits.value("links.threshold")),
        "coverage": {"read": sum(1 for entry in entries if entry["read"]), "total": len(entries), "source_key": "documents"},
    }
