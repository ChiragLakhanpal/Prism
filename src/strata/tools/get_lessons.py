"""get_lessons: the library's current lessons at their versions, as the viewer, as of a date (ticket 29).

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its
adapter. A lesson enters the library only when two people decided it (strata.knowledge.lessons.review),
so the tool reads the decided versions in strata.ops.lesson_versions and the evidence they rest on.

- As of a date, each lesson is at the newest version decided on or before it, and its evidence is only
  what was public by then (ADR 0002). A lesson whose current version retired it is left out and counted.
- The hindsight test's replays (ticket 34) set call.decided_by, the replay's own date. The library is then
  the one decided by that date, and each lesson version counts from the day every quote it rests on was
  public, not from its decision: Strata did not exist on a 2014 approval date, but the reports its lessons
  come from did. A version whose quotes were not all public by the as-of date is not in that library yet.
- Each lesson carries its evidence ids (the passages its quotes are in), the edition of the procurement
  rules its project followed (config/editions.toml, from the project's PAD), and ieg_status, one field for
  the four evidence badges (strata.knowledge.lessons.review.ieg_status).
- Lessons are ranked by fit and evidence, never by use (spec story 98): first by fit, the share of the
  query's words the lesson's statement, quotes and tags hold (a tool column, so the agent states no number
  of its own); then by the strength of IEG's part in the evidence (IEG's own lesson, then a lesson IEG
  restated, then one that rests on the ICR alone); then by how many quotes it rests on. strata.ops.
  lesson_uses, which counts how often each lesson was cited, is never read here.

The call's view (staff, piu or public) is returned with the result. It does not change the result: lessons in
the library are for every view (the roles file's [views], ticket 40).
"""

from __future__ import annotations

import datetime as dt
import json
from importlib import resources

from strata.config import load_editions, load_lesson_lists
from strata.knowledge.embed import terms
from strata.knowledge.lessons.propose import IEG_TYPES, PASSED
from strata.knowledge.lessons.review import IEG_STATUSES, ieg_status
from strata.reader.templates import ICR, template_for
from strata.tools.registry import Call

TABLE = "strata.ops.lesson_versions"
PASSAGES = "strata.gold.passage"


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "get_lessons" / name).read_text()


def _rows(call: Call, name: str, **params) -> list[dict]:
    result = call.engine.run(_sql(name), params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


# Values arrive typed from DuckDB and as text from the SQL warehouse, so each is read once here.

def _iso(value) -> str | None:
    if value is None or value == "":
        return None
    return value.isoformat()[:10] if isinstance(value, dt.date) else str(value)[:10]


def _int(value) -> int | None:
    return None if value is None or value == "" else int(value)


def _bool(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def ieg_quote(lesson: dict) -> dict | None:
    """IEG's words that restate a lesson this tool returned, for the drawer's IEG line, when IEG's review restated
    it. Section 3's risks and section 5's lessons both read it here, beside the rows it reads (ticket 31's review
    round 3, F6)."""
    if lesson["ieg_status"] != "restated":
        return None
    said = next((row for row in lesson["evidence"] if row["role"] == "restatement" and row["restated_by_ieg"]), None)
    return None if said is None else {"text": said["quote"], "lang": None, "doc_short": said["doc_short"],
                                      "evidence_id": said["evidence_id"]}


def evidence_row(row: dict) -> dict:
    """One quote a lesson rests on, with the passage it is in and the fields of its source line."""
    template = template_for(row["document_type"] or "")
    short = template.short_name if template else row["document_type"]
    return {"evidence_id": f"{PASSAGES}:{row['passage_id']}", "passage_id": row["passage_id"], "role": row["role"],
            "document_type": row["document_type"], "doc_short": short, "document_id": str(row["document_id"]),
            "project_id": row["project_id"], "report_number": row["report_number"],
            "document_date": _iso(row["document_date"]), "paragraph": row["paragraph"],
            "locator": "section" if short == "ICR Review" else "paragraph", "page": _int(row["cited_page"]),
            "quote": row["quote"], "restated_by_ieg": _bool(row["restated_by_ieg"]), "public_from": _iso(row["public_from"])}


def fit(query: str | None, words: str) -> float | None:
    """The share of the query's distinct words the lesson's words hold, to two places, or None with no query."""
    wanted = set(terms(query or ""))
    if not wanted:
        return None
    return round(len(wanted & set(terms(words))) / len(wanted), 2)


def _report(row: dict) -> dict:
    """One completion report as a count lists it: its project and its document."""
    template = template_for(row["document_type"] or "")
    return {"project_id": row["project_id"], "project_name": row["project_name"],
            "document_id": str(row["document_id"]), "version": _int(row["version"]),
            "document_type": row["document_type"], "doc_short": template.short_name if template else row["document_type"],
            "doc_key": row["doc_key"], "date": _iso(row["document_date"]), "public_from": _iso(row["public_from"])}


def reports(call: Call, packages: str, lists) -> dict:
    """The completion reports of the comparable packages' projects, and the risk factors they raised (ticket 30).

    projects is how many projects the packages belong to, read how many of them have an ICR Strata read by the
    as-of date, and missing why the rest do not: no_report (no ICR public by then) or not_read (an ICR with no
    passage Strata read). Each risk factor any counted report raised comes with k, how many of the counted
    reports raised it, and each of those reports with the passage that raised it. Every count is a value here,
    so a sentence that states one cites this summary (CLAUDE.md rule 1)."""
    wanted = ",".join(dict.fromkeys(ref.strip() for ref in packages.split(",") if ref.strip()))
    found = _rows(call, "reports.sql", packages=wanted, as_of=call.as_of, icr=ICR.document_type)
    counted = [row for row in found if row["document_id"] and (_int(row["passages"]) or 0) > 0]
    missing = []
    for code, rows in (("no_report", [row for row in found if not row["document_id"]]),
                       ("not_read", [row for row in found if row["document_id"] and not _int(row["passages"])])):
        if rows:
            missing.append({"reason_code": code, "count": len(rows), "project_ids": [row["project_id"] for row in rows]})
    by_document = {str(row["document_id"]): row for row in counted}
    raised: dict[str, dict[str, dict]] = {}
    if by_document:
        for row in _rows(call, "raised.sql", documents=",".join(by_document), decided_by=decided_by(call),
                         passed=PASSED):
            report = by_document[str(row["document_id"])]
            for key in json.loads(row["risk_factors"] or "[]"):
                if lists.risk_factor(key) is None:
                    continue
                raised.setdefault(key, {}).setdefault(str(row["document_id"]), {
                    **_report(report), "evidence_id": f"{PASSAGES}:{row['passage_id']}", "passage_id": row["passage_id"],
                    "paragraph": row["paragraph"], "page": _int(row["cited_page"])})
    factors = [{"key": item.key, "label": item.label, "k": len(raised[item.key]),
                "reports": sorted(raised[item.key].values(), key=lambda report: (report["date"] or "", report["project_id"]),
                                  reverse=True)}
               for item in lists.risk_factors if item.key in raised]
    return {"projects": len(found), "read": len(counted), "missing": missing,
            "counted": sorted((_report(row) for row in counted), key=lambda report: (report["date"] or "", report["project_id"]),
                              reverse=True),
            "risk_factors": factors}


def decided_by(call: Call) -> dt.date:
    """The date the library's decisions are read as of: the as-of date, or a hindsight replay's own date."""
    return call.decided_by or call.as_of


def _dated_by_evidence(versions: list[dict], evidence: list[dict], as_of: dt.date) -> dict[str, dict]:
    """Each lesson at its newest version whose quotes were all public by the as-of date, for a hindsight replay
    (ticket 34). A version rests on the quotes of every proposal added to the lesson at it or before it; it
    counts from the day the last of them was public, which becomes its public_from. A lesson with no such
    version was not in the library yet."""
    sources: dict[str, list[tuple[int, str]]] = {}
    for row in evidence:
        if row["role"] == "source":
            sources.setdefault(row["lesson_id"], []).append((_int(row["added_at_version"]), _iso(row["public_from"])))
    current: dict[str, dict] = {}
    for row in versions:  # oldest first, so a later version that counts replaces an earlier one
        quotes = [public for added, public in sources.get(row["lesson_id"], []) if added <= _int(row["version"])]
        if quotes and max(quotes) <= as_of.isoformat():
            current[row["lesson_id"]] = {**row, "public_from": max(quotes)}
    return current


def get_lessons(call: Call, query: str | None = None, risk_factor: str | None = None, stage: str | None = None,
                limit: int | None = None, packages: str | None = None, lesson_id: str | None = None) -> dict:
    """The current lessons that fit the query and the filters, as of call.as_of, best first; with packages, the
    completion reports of their projects and the risk factors those reports raised; with lesson_id, only that lesson,
    as a draft row that cites it is rewritten from its current version (ticket 39)."""
    lists, editions = load_lesson_lists(), load_editions()
    most = int(call.thresholds.value("lesson_review.get_lessons_max_results"))
    limit = min(max(limit or most, 1), most)
    wanted = lesson_id  # the loop below names each lesson lesson_id
    filters = {"risk_factor": risk_factor, "stage": stage, **({"lesson_id": wanted} if wanted else {})}
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "query": query, "filters": filters,
             "ranking": "fit, then evidence", "reports": reports(call, packages, lists) if packages else None}
    if risk_factor and lists.risk_factor(risk_factor) is None:
        return {**empty, "abstention": {"reason": "unknown_risk_factor", "risk_factor": risk_factor}}
    if stage and lists.stage(stage) is None:
        return {**empty, "abstention": {"reason": "unknown_stage", "stage": stage}}

    versions = _rows(call, "versions.sql", decided_by=decided_by(call))
    evidence_rows = _rows(call, "evidence.sql", decided_by=decided_by(call),
                          evidence_through=decided_by(call) if call.decided_by else call.as_of)
    current: dict[str, dict] = {}
    if call.decided_by is None:
        for row in versions:
            current[row["lesson_id"]] = row  # oldest first, so the last is current on the as-of date
    else:
        current = _dated_by_evidence(versions, evidence_rows, call.as_of)
        evidence_rows = [row for row in evidence_rows if _iso(row["public_from"]) <= call.as_of.isoformat()]
    evidence: dict[str, list[dict]] = {}
    for row in evidence_rows:
        held = current.get(row["lesson_id"])
        if held is not None and _int(row["added_at_version"]) <= _int(held["version"]):
            found = evidence.setdefault(row["lesson_id"], [])
            if row["passage_id"] not in {seen["passage_id"] for seen in found}:  # merged proposals share restatements
                found.append(row)
    projects = {row["project_id"]: row for row in _rows(call, "projects.sql", as_of=call.as_of, types=",".join(IEG_TYPES))}

    retired, filtered, candidates = [], 0, []
    for lesson_id, version in current.items():
        if version["state"] != "current":
            retired.append(f"{TABLE}:{lesson_id}/v{_int(version['version'])}")
            continue
        factors = json.loads(version["risk_factors"] or "[]")
        if ((risk_factor and risk_factor not in factors) or (stage and version["stage"] != stage)
                or (wanted and wanted != lesson_id)):
            filtered += 1
            continue
        rows = sorted(evidence.get(lesson_id, []), key=lambda row: (_int(row["added_at_version"]), row["role"] != "source",
                                                                    _iso(row["document_date"]) or ""))
        project = projects.get(version["project_id"]) or {}
        ieg = ieg_status(rows, project.get("ieg_reviewed_on"))
        tags = {"risk_factors": [{"key": key, "label": item.label} for key in factors if (item := lists.risk_factor(key))],
                "stage": _item(lists.stage(version["stage"])), "kind": _item(lists.kind(version["kind"]))}
        words = " ".join([version["statement"], *(row["quote"] for row in rows),
                          *(item["label"] for item in tags["risk_factors"]), (tags["stage"] or {}).get("label", "")])
        edition = editions.get(version["edition_key"])
        candidates.append({
            "evidence_id": f"{TABLE}:{lesson_id}/v{_int(version['version'])}", "public_from": _iso(version["public_from"]),
            "source": {"table": TABLE, "lesson_id": lesson_id, "version": _int(version["version"]),
                       "decided_on": _iso(version["decided_on"]), "project_id": version["project_id"],
                       "project_name": project.get("project_name")},
            "lesson_id": lesson_id, "version": _int(version["version"]), "statement": version["statement"], **tags,
            "edition": {"key": edition.key, "name": edition.name, "short": edition.short} if edition else None, **ieg,
            "evidence": [evidence_row(row) for row in rows],
            "project": {"project_id": version["project_id"], "project_name": project.get("project_name"),
                        "country": project.get("country_name"), "region": project.get("region"),
                        "sector": project.get("sector_name")},
            "decided_on": _iso(version["decided_on"]), "fit": fit(query, words), "rank": None})

    # Fit first, then the evidence: IEG's part in it, then how many quotes it rests on. Never use.
    candidates.sort(key=lambda row: (-(row["fit"] or 0), IEG_STATUSES.index(row["ieg_status"]), -len(row["evidence"]),
                                     row["lesson_id"]))
    rows = [{**row, "rank": rank} for rank, row in enumerate(candidates[:limit], 1)]
    not_used = []
    if retired:
        not_used.append({"reason": "retired", "count": len(retired), "evidence_ids": retired})
    if filtered:
        not_used.append({"reason": "filtered_out", "count": filtered, "evidence_ids": []})
    if len(candidates) > limit:
        not_used.append({"reason": "ranked_below_limit", "count": len(candidates) - limit, "evidence_ids": []})
    return {**empty, "rows": rows, "coverage": {"matched": len(current), "used": len(rows), "not_used": not_used},
            "abstention": None if rows else {"reason": "no_lessons"}}


def _item(found) -> dict | None:
    return {"key": found.key, "label": found.label} if found else None
