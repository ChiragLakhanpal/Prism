"""search_passages: hybrid search over the numbered passages, as the viewer, as of a date.

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its
adapter. A searcher (src/strata/knowledge/search.py) ranks the passages within the filters: AI Search
on the workspace, the fixture search over the fixture database. The tool then reads the ranked
passages from strata.gold.passage with the viewer's engine, each only where it was public on the
as-of date and not replaced by then by a re-issue of its report (ADR 0002), so every passage it
returns is a row the app holds, with its evidence id, public date and source line.

A passage in which Prompt Shields found a prompt attack when it was read in is left out, and the
coverage line counts it with its evidence id. So is a passage with no stored result, which the
shield never screened. The rule and its reason codes are strata.knowledge.shields.held_back's, which
get_disagreements follows too. The coverage line also says how many matched passages ranked below the limit. A document type or sector the slice does not know, or a query nothing
matches, is an abstention, whose reason the registry lists. So is a workspace with no passage index yet, before
ticket 11's step 4 first syncs it: the tool logs the workspace's answer once and returns no passages, in the shape
of a search that found nothing, so the agent can answer from records or refuse, and the run goes on (ticket 67).

The call's view (staff, piu or public) is returned with the result. It does not change which passages come back:
the reports are public, and the as-of date (ticket 40) is what limits them.
"""

from __future__ import annotations

import datetime as dt
import functools
import json
import logging
from importlib import resources

from strata.config import load_slice, load_sources
from strata.knowledge import shields
from strata.knowledge.retrieval.demotion import lowered, rank
from strata.knowledge.retrieval.kinds import query_kind
from strata.knowledge.search import Filters, IndexNotFound, searcher_for
from strata.reader.passages import NOTICE_TEXT, ROUTE_B
from strata.reader.templates import template_for
from strata.tools.registry import Call

TABLE = "strata.gold.passage"
NO_INDEX = "Nothing was searched: the passage index is not available yet."
log = logging.getLogger("strata.tools.search_passages")


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "search_passages" / name).read_text()


def _iso(value) -> str | None:
    if value is None or value == "":
        return None
    return value.isoformat() if isinstance(value, dt.date) else str(value)[:10]


def _int(value) -> int | None:
    return None if value is None or value == "" else int(value)


def _boolean(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def _row(found: dict, rank: int, score: float) -> dict:
    """One ranked passage in the registry's row shape."""
    return {**passage_row(found), "rank": rank, "score": score}


def _cells(value) -> list[list[str]] | None:
    """A table row's cells, [[column head, value], ...], from the JSON silver keeps."""
    return None if value is None or value == "" else json.loads(value)


# The columns of strata.gold.passage a passage's source line is built from (passage_source).
SOURCE_COLUMNS = ("kind", "document_type", "project_id", "project_name", "document_id", "document_date", "report_number",
                  "version", "section_path", "paragraph", "paragraph_numbered", "pdf_page", "pdf_pages", "pdf_url",
                  "doc_key")


def passage_source(found: dict) -> dict:
    """A passage's source line, in the registry's source_fields for search_passages, from its row of
    strata.gold.passage (SOURCE_COLUMNS). It is defined once here, and every tool that hands over a passage, such as
    get_disagreements for a side that rests on one, gives it this way (CLAUDE.md rule 4)."""
    notice = found["kind"] == NOTICE_TEXT
    return {
        "document_type": found["document_type"],
        "project_id": found["project_id"],
        "project_name": found["project_name"],
        "document_id": str(found["document_id"]),
        "document_date": _iso(found["document_date"]),
        "report_number": found["report_number"],
        "version": _int(found["version"]),
        "section_path": found["section_path"],
        "paragraph": found["paragraph"],
        # False when the report numbers no paragraphs, as an ISR does: paragraph is then Prism's own
        # count (s4), so a citation names the section and the page instead.
        "paragraph_numbered": _boolean(found["paragraph_numbered"]),
        "pdf_page": _int(found["pdf_page"]),
        "pdf_pages": _int(found["pdf_pages"]),
        "pdf_url": found["pdf_url"],
        "doc_key": found["doc_key"],
        "notice_id": str(found["document_id"]) if notice else None,
        # A notice's own page, from the source registry's address for it (CLAUDE.md rule 9).
        "notice_url": notice_page(str(found["document_id"])) if notice else None,
    }


def passage_row(found: dict) -> dict:
    """One passage in the registry's row shape, without a search's rank. Every engine gives typed
    values (ticket 128), and each is read once here. A notice's text has its notice's id
    and its page on the World Bank's site; a table row has its table, its row and its cells."""
    kind = found["kind"]
    notice = kind == NOTICE_TEXT
    return {
        "evidence_id": f"{TABLE}:{found['passage_id']}",
        "public_from": _iso(found["public_from"]),
        "source": passage_source(found),
        "passage_id": found["passage_id"],
        "document_id": str(found["document_id"]),
        "document_type": found["document_type"],
        "project_id": found["project_id"],
        "version": _int(found["version"]),
        "section_path": found["section_path"],
        "paragraph": found["paragraph"],
        "paragraph_numbered": _boolean(found["paragraph_numbered"]),
        "part": _int(found["part"]),
        "parts": _int(found["parts"]),
        "pdf_page": _int(found["pdf_page"]),
        "last_pdf_page": _int(found["last_pdf_page"]),
        "printed_page": found["printed_page"],
        "language": found["language"],
        "parse_route": found["parse_route"],
        "kind": kind,
        "route": "layout_parser" if found["parse_route"] == ROUTE_B else "published_text",
        "scanned": _boolean(found["scanned"]),
        "table_title": found["table_title"],
        "table_row": _int(found["table_row"]),
        "cells": _cells(found["cells"]),
        "notice_id": str(found["document_id"]) if notice else None,
        "header": found["header"],
        "text": found["text"],
    }


def passages_query() -> str:
    """passages.sql, the one statement that reads passages by id, for a page that reads the passages it cites in its
    own batch (the Summary, ticket 125)."""
    return _sql("passages.sql")


def read_passage(engine, passage_id: str, as_of: dt.date) -> dict | None:
    """One passage by its id, read as the viewer, where it was public on the as-of date and not yet
    replaced by a re-issue of its report then (ADR 0002), or None. The evidence drawer opens it from a
    link, with no search behind it."""
    result = engine.run(_sql("passages.sql"), {"ids": passage_id, "as_of": as_of})
    rows = [dict(zip(result.columns, row)) for row in result.rows]
    return passage_row(rows[0]) if rows else None


def read_passages(engine, passage_ids: list[str], as_of: dt.date) -> dict[str, dict]:
    """Several passages by their ids in one statement, as read_passage reads one: those public on the as-of date
    and not yet replaced then, by id. A page that shows many passages reads them this way (ticket 32)."""
    if not passage_ids:
        return {}
    result = engine.run(_sql("passages.sql"), {"ids": ",".join(passage_ids), "as_of": as_of})
    found = (dict(zip(result.columns, row)) for row in result.rows)
    return {row["passage_id"]: passage_row(row) for row in found}


@functools.cache
def _notice_address() -> str | None:
    """Notices' record_url in config/sources.toml, read once, since every notice row of a search needs it (ticket
    18's review round 3, P9)."""
    return load_sources()["notices"].record_url


def notice_page(notice_id: str) -> str | None:
    """A notice's own page on the World Bank's site, from config/sources.toml (notices' record_url)."""
    address = _notice_address()
    return address.replace("{id}", notice_id) if address else None


def search_passages(call: Call, query: str, project_id: str | None = None, document_type: str | None = None,
                    country: str | None = None, sector: str | None = None, published_from: dt.date | None = None,
                    published_until: dt.date | None = None, limit: int | None = None) -> dict:
    """The passages that best match the query within the filters, as of call.as_of, best first."""
    value = call.thresholds.value
    most = int(value("passages.max_results"))
    limit = min(max(limit or int(value("passages.results")), 1), most)
    template = template_for(document_type) if document_type else None
    filters = Filters(call.as_of, project_id.strip().upper() if project_id else None,
                      template.document_type if template else document_type,
                      country.strip().upper() if country else None, sector.strip().lower() if sector else None,
                      published_from, published_until)
    # ranked_lower: the passages a passage reviewer ranked lower for this question's kind (ticket 32).
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "query": query,
             "filters": filters.as_dict(), "search": None,
             "ranked_lower": {"query_kind": query_kind(query), "evidence_ids": []}}
    if document_type and template is None:
        return {**empty, "abstention": {"reason": "unknown_document_type", "document_type": document_type}}
    if filters.sector and filters.sector not in load_slice().sectors:
        return {**empty, "abstention": {"reason": "unknown_sector", "sector": sector}}

    searcher = searcher_for(call)
    try:
        hits = searcher.search(query, filters, most * int(value("passages.search_depth")))
    except IndexNotFound as missing:
        # Before ticket 11's step 4 syncs it, the workspace has no passage index. The search then finds nothing and
        # says why, so the agent answers from records or refuses, and the run goes on (ticket 67).
        log.warning("search_passages found no passages, because the passage index is not available yet: %s", missing)
        return {**empty, "search": {"searcher": searcher.name, "method": NO_INDEX, "matched_is_at_least": False},
                "abstention": {"reason": "index_not_available", "query": query}}
    # matched_is_at_least: the searcher counted only the hits it gave back, so more passages may match.
    search = {"searcher": searcher.name, "method": hits.method, "matched_is_at_least": not hits.complete}
    if not hits.hits:
        return {**empty, "search": search, "abstention": {"reason": "no_match", "query": query}}

    result = call.engine.run(_sql("passages.sql"), {"ids": ",".join(hit.passage_id for hit in hits.hits),
                                                    "as_of": call.as_of})
    held = {row["passage_id"]: row for row in (dict(zip(result.columns, row)) for row in result.rows)}
    kept, left_out, missing = [], {reason: [] for reason in shields.LEFT_OUT}, 0
    for hit in hits.hits:
        found = held.get(hit.passage_id)
        if found is None:
            # The index named a passage the viewer's table does not hold as of this date, such as one a re-issue
            # replaced: it is no match, so the coverage line counts it nowhere (ticket 11's review round 2, P5).
            missing += 1
            continue
        if reason := shields.held_back(found["attack_detected"]):
            left_out[reason].append(f"{TABLE}:{hit.passage_id}")
        else:
            kept.append((found, hit.score))
    # A passage a passage reviewer ranked lower for this kind of question moves below the others, and stays:
    # it still appears, first when it is the only one (ticket 32).
    kind = query_kind(query)
    ranked_lower = lowered(call.engine, kind, call.as_of)
    kept = rank(kept, lambda pair: pair[0]["passage_id"], ranked_lower)
    rows = [_row(found, rank_, score) for rank_, (found, score) in enumerate(kept[:limit], 1)]
    not_used = shields.coverage_entries(left_out)
    matched = hits.matched - missing
    below = matched - len(rows) - sum(len(ids) for ids in left_out.values())
    if below > 0:
        not_used.append({"reason": "ranked_below_limit", "count": below, "evidence_ids": []})
    return {"rows": rows, "coverage": {"matched": matched, "used": len(rows), "not_used": not_used},
            "abstention": None if rows else {"reason": "no_match", "query": query}, "query": query,
            "filters": filters.as_dict(), "search": search,
            "ranked_lower": {"query_kind": kind, "evidence_ids": [f"{TABLE}:{found['passage_id']}" for found, _ in kept
                                                                  if found["passage_id"] in ranked_lower]}}
