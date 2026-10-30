"""A project's Documents tab and the source view (ticket 21; the 21 brief, sections 6 and 7).

- documents_tab lists every document the documents API lists for the project, grouped by type in the
  order a project produces them (the appraisal document, Project Papers, ISRs, Procurement Plans, the
  completion report, its reviews, performance assessments, then the rest), newest first in each group,
  with the date on the document, the day the World Bank made it public (its public_from, ADR 0002) and
  how many of its pages Strata read. A report re-issued under the same report number replaces its
  earlier version in one row. The route counts each group and says which documents show before "Show
  all" (app.documents_shown), so the screen counts nothing. It also says whether the project is in the
  set whose documents Strata fetches (config/slice.toml: the projects its criteria select and the ones it
  names), so a project outside that set is not told its documents are still to come.
- source_page gives one PDF page of a document as the reader read it: its paragraphs as the document
  numbers them and its tables' rows, never a table's summary, which is Strata's own words, with a
  paragraph that runs onto the page from the one before. A page with none says why: it has no text
  (empty), it is the report's front matter, which the reader leaves out (front_matter), or the reader
  could not read it (unread). A
  Procurement Plan's page gives its STEP rows, or its published text where it has no table. It corrects
  a wrong address and says how: a paragraph on another page (moved), a paragraph the document does not
  have (no_para), or a page past the last (page_range). A document is named by its key in the project
  (silver.documents' doc_key, such as icr-2019-10-10, or procurement-plan-{agency}-{date} for a plan),
  by its type alone when the project has one current document of that type (icr), or by its documents
  API id; the answer then gives the key to show instead (canonical).

Each read uses only what was public on or before the as-of date. Dates arrive as UTC timestamps, and
the date part is taken here, never in the browser.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from functools import cache
from pathlib import Path

from strata.config import load_project_page, load_slice
from strata.lakehouse.clean import public_from
from strata.lakehouse.engine import Engine
from strata.lakehouse.passages import select
from strata.reader.layout import https
from strata.server.projects import display_name
from strata.lakehouse.clean import agency_id

SQL = Path(__file__).resolve().parent / "sql" / "documents"
# The documents API's type for each group, in the order a project produces its documents.
# The documents API's type for each group, in project-cycle order, and the groups re-issued under one
# report number, the later replacing the earlier: config/project_page.toml (CLAUDE.md rule 9).
PAGE = load_project_page()
TYPES = PAGE.document_groups
ORDER = [*TYPES.values(), "other"]
# A group's documents as an address names them by type alone: /documents/icr.
SLUGS = {group.replace("_", "-"): group for group in TYPES.values()}
REISSUED = PAGE.reissued
LANGUAGES = {"English": "en", "French": "fr", "Spanish": "es", "Portuguese": "pt"}


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


def plan_key(agency: str, plan_date) -> str:
    """A Procurement Plan's key in its project: procurement-plan-{agency}-{date}."""
    return f"procurement-plan-{agency_id(agency)}-{_iso(plan_date)}"


def _listed(engine: Engine, project_id: str) -> dict[str, dict]:
    """Every document the project's newest lists name, by its documents API id."""
    latest: dict[str, tuple[str, dt.date]] = {}
    for row in _rows(engine, "lists", project_id=project_id):
        latest[row["url"]] = (row["response"], _day(row["fetched_at"]))
    found: dict[str, dict] = {}
    for response, fetched in latest.values():
        for key, document in json.loads(response).get("documents", {}).items():
            if key == "facets" or not isinstance(document, dict) or not document.get("id") or not document.get("docdt"):
                continue
            disclosed = _day(document.get("disclosure_date"))
            found[str(document["id"])] = {
                "document_id": str(document["id"]), "document_type": document.get("docty") or "",
                "report_number": document.get("repnb") or None, "document_date": _day(document["docdt"]),
                "disclosed_on": disclosed, "public_from": public_from(disclosed, fetched),
                # The list gives pdfurl over http; the readers store it over https, and so does this page (ticket 63).
                "pdf_url": https(document["pdfurl"]) if document.get("pdfurl") else None,
                "language": LANGUAGES.get(document.get("lang") or "")}
    return found


class _Documents:
    """The project's documents as the reader holds them: listed, read, and its plans' versions."""

    def __init__(self, engine: Engine, project_id: str):
        self.listed = _listed(engine, project_id)
        self.read = {row["document_id"]: row for row in _rows(engine, "read", project_id=project_id)}
        self.plans = {row["document_id"]: row for row in _rows(engine, "plans", project_id=project_id)}

    def key(self, document_id: str) -> str | None:
        if document_id in self.read:
            return self.read[document_id]["doc_key"]
        plan = self.plans.get(document_id)
        return plan_key(plan["implementing_agency"], plan["plan_date"]) if plan and plan["implementing_agency"] else None

    def entry(self, document_id: str) -> dict:
        """One document as the Documents tab and the source view give it."""
        listed = self.listed.get(document_id, {})
        read, plan = self.read.get(document_id), self.plans.get(document_id)
        kind = listed.get("document_type") or (read["document_type"] if read else "Procurement Plan" if plan else "")
        pages = int(read["pdf_pages"]) if read else int(plan["pdf_pages"]) if plan else None
        pages_read = int(read["pages_read"]) if read else pages if plan and plan["parse_reason"] else None
        disclosed = listed.get("disclosed_on") or _day((read or plan or {}).get("disclosed_on"))
        public = listed.get("public_from") or _day((read or plan or {}).get("public_from"))
        return {
            "document_id": document_id, "type": TYPES.get(kind, "other"), "document_type": kind,
            "document_date": _iso(listed.get("document_date") or (read["document_date"] if read else
                                                                  plan["plan_date"] if plan else None)),
            "disclosed_on": _iso(disclosed), "public_from": _iso(public),
            "read": pages_read is not None, "doc_key": self.key(document_id),
            "pages_read": pages_read, "pdf_pages": pages,
            "partial": pages_read is not None and pages is not None and pages_read < pages,
            "pdf_url": listed.get("pdf_url") or (read or plan or {}).get("pdf_url"),
            "sequence": int(read["sequence"]) if read and read["sequence"] is not None else None,
            "agency": plan["implementing_agency"] if plan else None,
            "language": (read["language"] if read else None) or listed.get("language"),
            "report_number": listed.get("report_number") or (read["report_number"] if read else None),
        }

    def all_ids(self) -> list[str]:
        return list(dict.fromkeys([*self.listed, *self.read, *self.plans]))


def _newest_first(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda entry: (entry["document_date"] or "", entry["document_id"]), reverse=True)


def plans_unread_reads(project_id: str) -> list[tuple[str, dict]]:
    """The statements plans_unread() runs, for the Procurement tab's first batch (ticket 125)."""
    return [(_query(name), {"project_id": project_id}) for name in ("lists", "read", "plans")]


def plans_unread(engine: Engine, project_id: str, as_of: dt.date) -> int:
    """How many Procurement Plans the project's documents list, public by the date, that I haven't read: the ones this
    tab marks Not read. The Procurement tab says the plan it shows is the only one I have read, and links here when
    there are others (ticket 134: P156634 lists 240 plans)."""
    held = _Documents(engine, project_id)
    day = as_of.isoformat()
    entries = [held.entry(document_id) for document_id in held.all_ids()]
    return sum(1 for entry in entries if entry["type"] == "procurement_plan" and not entry["read"]
               and entry["public_from"] and entry["public_from"] <= day)


def documents_tab(engine: Engine, project_id: str, as_of: dt.date, shown: int = 5) -> dict | None:
    """Every document listed for the project and public by the date, by type, or None for no such project."""
    found = _rows(engine, "project", project_id=project_id, as_of=as_of)
    if not found:
        return None
    held = _Documents(engine, project_id)
    entries = [held.entry(document_id) for document_id in held.all_ids()]
    entries = [entry for entry in entries if entry["public_from"] and entry["public_from"] <= as_of.isoformat()]
    groups = []
    for group in ORDER:
        mine = _newest_first([entry for entry in entries if entry["type"] == group])
        if group in REISSUED:
            mine = _fold_reissues(mine)
        else:
            for entry in mine:
                entry["reissue"] = None
        if not mine:
            continue
        for index, entry in enumerate(mine):
            entry["shown"] = index < shown
        groups.append({"type": group, "count": len(mine), "shown_count": min(len(mine), shown), "documents": mine})
    return {"as_of": as_of.isoformat(),
            "project": {"project_id": project_id, "display_name": display_name(found[0]["project_name"])},
            "in_document_set": project_id in select(engine, load_slice()).projects,
            "groups": groups, "total": sum(group["count"] for group in groups),
            "shown_total": sum(group["shown_count"] for group in groups),
            "documents_through": _through(engine, project_id, as_of)}


def _fold_reissues(entries: list[dict]) -> list[dict]:
    """A report re-issued under the same number shows once, as its newest version, with the one it replaced."""
    kept, by_number = [], {}
    for entry in entries:  # newest first
        number = entry["report_number"]
        if number and number in by_number:
            newer = by_number[number]
            if newer["reissue"] is None:
                newer["reissue"] = {key: entry[key] for key in ("document_id", "document_date", "disclosed_on",
                                                                "doc_key", "pdf_url")}
            continue
        entry["reissue"] = None
        if number:
            by_number[number] = entry
        kept.append(entry)
    return kept


def _through(engine: Engine, project_id: str, as_of: dt.date) -> str | None:
    fetched = [_day(row["fetched_at"]) for row in _rows(engine, "lists", project_id=project_id)]
    return min(max(fetched), as_of).isoformat() if fetched else None


# ── The source view ──────────────────────────────────────────────────────

def _resolve(held: _Documents, doc: str, as_of: dt.date) -> tuple[str, dict]:
    """The document an address names: ("found", entry), ("ambiguous", {type, count}), ("not_found", {})."""
    ids = held.all_ids()
    by_key = {held.key(document_id): document_id for document_id in ids if held.key(document_id)}
    if doc in by_key:
        return "found", held.entry(by_key[doc])
    if doc.isdigit() and doc in ids:
        return "found", held.entry(doc)
    group = SLUGS.get(doc)
    if group:
        current = [held.entry(document_id) for document_id in ids]
        current = [entry for entry in current if entry["type"] == group and entry["read"]
                   and entry["public_from"] and entry["public_from"] <= as_of.isoformat()]
        current = _fold_reissues(_newest_first(current)) if group in REISSUED else current
        if len(current) == 1:
            return "found", current[0]
        if len(current) > 1:
            return "ambiguous", {"type": group, "count": len(current)}
    return "not_found", {}


def _replacements(held: _Documents, entry: dict, as_of: dt.date) -> dict:
    """The version this re-issue replaced, or the re-issue that replaced this version, public by the date."""
    if entry["type"] not in REISSUED or not entry["report_number"]:
        return {"replaces": None, "replaced_by": None}
    same = [held.entry(document_id) for document_id in held.all_ids()]
    same = _newest_first([other for other in same if other["report_number"] == entry["report_number"]
                          and other["document_id"] != entry["document_id"] and other["type"] == entry["type"]
                          and other["public_from"] and other["public_from"] <= as_of.isoformat()])
    older = [other for other in same if (other["document_date"] or "") < (entry["document_date"] or "")]
    newer = [other for other in same if (other["document_date"] or "") > (entry["document_date"] or "")]
    pick = lambda found: {"doc_key": found[0]["doc_key"], "document_date": found[0]["document_date"]} if found else None
    return {"replaces": pick(older), "replaced_by": pick(newer[::-1])}


def _reading_order(row: dict) -> tuple:
    """A passage's place on its page: paragraphs before table rows, by the page each starts on, then by the
    key after the version in its id, read as numbers where it holds them (54 before 100, s2 before s10)."""
    key = str(row["passage_id"]).split("/", 2)[-1]
    chunks = tuple((0, int(chunk), "") if chunk.isdigit() else (1, 0, chunk) for chunk in re.findall(r"\d+|\D+", key))
    return row["kind"] == "table_row", row["pdf_page"], chunks


def _passages(engine: Engine, document_id: str, version: int, page: int) -> tuple[list[dict], list[dict]]:
    paragraphs, tables = [], {}
    found = sorted(_rows(engine, "page", document_id=document_id, version=version, page=page), key=_reading_order)
    for row in found:
        if row["kind"] == "table_row":
            table = tables.setdefault(row["table_title"] or "", {"title": row["table_title"], "rows": []})
            table["rows"].append({"passage_id": row["passage_id"], "row": row["table_row"],
                                  "cells": json.loads(row["cells"]) if row["cells"] else []})
        else:
            paragraphs.append({"passage_id": row["passage_id"], "section_path": row["section_path"],
                               "paragraph": row["paragraph"], "numbered": bool(row["paragraph_numbered"]),
                               "part": row["part"], "language": row["language"], "text": row["text"],
                               "from_page_before": row["pdf_page"] < page})
    return paragraphs, list(tables.values())


def source_page(engine: Engine, project_id: str, doc: str, page: int | None, para: str | None,
                passage: str | None, as_of: dt.date) -> dict | None:
    """One page of a document as the reader read it, or None when there is no such project then."""
    found = _rows(engine, "project", project_id=project_id, as_of=as_of)
    if not found:
        return None
    answer = {"as_of": as_of.isoformat(),
              "project": {"project_id": project_id, "display_name": display_name(found[0]["project_name"])},
              "asked": {"page": page, "para": para, "passage": passage}}
    held = _Documents(engine, project_id)
    state, entry = _resolve(held, doc, as_of)
    if state == "ambiguous":
        return {**answer, "state": "ambiguous", "ambiguous": entry}
    if state == "not_found":
        return {**answer, "state": "not_found"}
    canonical = entry["doc_key"] if entry["doc_key"] and entry["doc_key"] != doc else None
    document = {key: entry[key] for key in ("document_id", "doc_key", "type", "document_type", "document_date",
                                           "disclosed_on", "pdf_pages", "pdf_url", "language", "sequence", "agency")}
    answer |= {"document": document, "canonical": canonical}
    if not entry["public_from"] or entry["public_from"] > as_of.isoformat():
        return {**answer, "state": "not_public", "disclosed_on": entry["disclosed_on"] or entry["public_from"]}
    if not entry["read"] and entry["type"] != "procurement_plan" or entry["pdf_pages"] is None:
        return {**answer, "state": "doc_unread"}
    answer["document"] |= _replacements(held, entry, as_of)

    pages = entry["pdf_pages"]
    read = held.read.get(entry["document_id"])
    version = int(read["version"]) if read else 1
    correction, highlight = None, None
    if (para or passage) and read:
        named = _rows(engine, "paragraph", document_id=entry["document_id"], version=version, para=para or "",
                      passage_id=passage or "")
        if named:
            first = named[0]
            if page is not None and first["pdf_page"] != page and para:
                correction = {"kind": "moved", "para": para, "page": first["pdf_page"]}
            page = first["pdf_page"]
            highlight = {"passage_id": first["passage_id"], "para": first["paragraph"] if first["paragraph_numbered"] else None}
        elif para:
            correction = {"kind": "no_para", "para": para, "page": page or 1}
    page = max(page or 1, 1)
    if page > pages:
        correction, page, highlight = {"kind": "page_range", "para": None, "page": pages}, pages, None

    paragraphs, tables, plan_rows, page_text = [], [], [], None
    if read:
        paragraphs, tables = _passages(engine, entry["document_id"], version, page)
    elif entry["type"] == "procurement_plan":
        plan_rows = _rows(engine, "plan_page", document_id=entry["document_id"], page=page)
        for row in plan_rows:
            for key in ("estimated_amount_usd", "actual_amount_usd"):
                row[key] = None if row[key] is None else f"{row[key]:.2f}" if not isinstance(row[key], str) else row[key]
        if not plan_rows:
            text = _rows(engine, "plan_text", document_id=entry["document_id"], page=page)
            lines = [line.strip() for line in (text[0]["text"] if text else "").splitlines() if line.strip()]
            page_text = lines or None
    if paragraphs or tables or plan_rows or page_text:
        page_state = "read"
    else:
        route = _rows(engine, "page_route", document_id=entry["document_id"], page=page) if read else []
        reason = route[0]["reason"] if route else None
        page_state = {"no_text": "empty", "front_matter": "front_matter"}.get(reason, "unread")
    return {**answer, "state": "page", "page": page, "correction": correction, "highlight": highlight,
            "page_state": page_state, "passages": paragraphs, "tables": tables, "plan_rows": plan_rows,
            "page_text": page_text}
