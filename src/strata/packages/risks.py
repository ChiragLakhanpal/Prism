"""The risk-table builder (ticket 30): section 3 of the package workspace, "Procurement risks and what helped".

It is a workflow step, so the package routes run it for a viewer and the hindsight test (ticket 34) runs it
headless over many packages with an as-of date. Every input arrives as an argument: the engine that runs as the
viewer, the viewer, the as-of date and the view (CLAUDE.md rule 7), never a module global. It runs the tools
through the tool registry and keeps every row they return in its own Facts, as an answer's turn does:

1. find_comparables, with the package's criteria, for its comparable packages: every package the criteria
   match, the ones section 1 times and the ones it can only count (no notice, canceled).
2. get_lessons with those packages, for the completion reports (ICRs) of their projects that Strata read and
   how many of them raised each risk factor, in its summary record. Every count the section states is a value
   there (CLAUDE.md rule 1).
3. get_lessons again for each risk factor the reports raised, for the current lesson that fits the package
   best on what helped with it. A risk with no current lesson is not a row: every row has a lesson (the 30
   brief, section 5.1).

The rows are ranked by fit and evidence and never by use (spec story 98; web/src/copy.ts packageRisks.note
says so, and must change with rank below): first by how closely the row's lesson fits the package's words
(get_lessons' fit), then by how many completion reports raised the risk, then by IEG's part in the lesson's
evidence, then by how many quotes the lesson rests on. At most package_risks.max_rows rows are kept
(config/thresholds.toml).

Each row is two claims, and all six checks run on them as on any answer, through SixChecks as a draft's notes do
(ticket 61): the count ('"Cost estimates below market rates" came up in 1 of 1 completion reports ...'), citing
get_lessons' summary, and what helped ('What helped with "Cost estimates below market rates" was "Base works
estimates on market rates to avoid rebidding".'), citing the lesson and the passages it rests on. Both restate their
records' own words, the risk's name and the lesson's, so checks 1 to 3 prove them and check 4 needs no model; the
screen's check line calls those words names and lessons that match their records, not quotes from a page. Check 6
asks get_disagreements about the projects the sources belong to, and a disagreement a row rests on comes with the
row, both sides. Before any check, each row's count is compared with the summary's own count for its risk, and a
row that differs is removed, as check 1 would remove it: the summary holds other numbers, such as a report's page,
that could otherwise back a wrong count (ticket 30's verify O1). A row with a claim that fails a check is removed
whole, since a risk without its count, or a count without its lesson, would mislead.

The search for passages is not called: get_lessons returns the passages each count and each lesson rest on,
with their evidence ids, so every source the section shows came back from a tool this turn.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from strata.agent.answer_check import Asker, SixChecks
from strata.agent.claims import Claim
from strata.agent.loop import keep_result
from strata.agent.verifier import NUMBER, Verdict, disagreement_event, verify
from strata.config import Thresholds, load_lesson_lists, load_sources, load_thresholds, load_tools
from strata.dbx import Viewer
from strata.harness.facts import Facts
from strata.knowledge.lessons.review import IEG_STATUSES
from strata.lakehouse.engine import Engine
from strata.tools import registry

TOOLS = ("find_comparables", "get_lessons")
PACKAGE = "strata.gold.package:"
# Why the section has no rows, as the page's empty states say it (web/src/copy.ts packageRisks.empty).
EMPTY_REASONS = ("missing_criteria", "no_comparables", "no_reports", "no_lessons", "all_removed")


@dataclass(frozen=True)
class RiskTable:
    """What the builder made: the section's payload, every row the tools returned, and the verifier's verdict on
    the rows' claims (None when no row was written)."""

    payload: dict
    facts: Facts
    verdict: Verdict | None


def rank(candidate: tuple[dict, dict]) -> tuple:
    """A row's place: by its lesson's fit to the package, then the reports that raised the risk, then IEG's part
    in the lesson's evidence, then the quotes it rests on. Never by use. web/src/copy.ts packageRisks.note says
    this in words, so the two change together (CLAUDE.md rule 4)."""
    factor, lesson = candidate
    return (-(lesson["fit"] or 0), -factor["k"], IEG_STATUSES.index(lesson["ieg_status"]), -len(lesson["evidence"]),
            factor["key"])


def _source(evidence: Mapping, project_name: str | None) -> dict:
    """One source pill of a row: a passage the lesson rests on, in the tool's order (the completion report first,
    then IEG's documents)."""
    return {"evidence_id": evidence["evidence_id"], "passage_id": evidence["passage_id"], "role": evidence["role"],
            "doc_type": evidence["document_type"], "doc_short": evidence["doc_short"], "pcode": evidence["project_id"],
            "project_name": project_name, "date": evidence["document_date"], "para": evidence["paragraph"],
            "locator": {"kind": evidence["locator"], "text": evidence["paragraph"]}, "page": evidence["page"],
            "quote": evidence["quote"], "public_from": evidence["public_from"]}


def ieg_quote(lesson: Mapping) -> dict | None:
    """IEG's words that restate the lesson, for the drawer's IEG line, when IEG's review restated it."""
    if lesson["ieg_status"] != "restated":
        return None
    said = next((row for row in lesson["evidence"] if row["role"] == "restatement" and row["restated_by_ieg"]), None)
    return None if said is None else {"text": said["quote"], "lang": None, "doc_short": said["doc_short"],
                                      "evidence_id": said["evidence_id"]}


def _row(factor: dict, lesson: dict) -> dict:
    name = (lesson.get("project") or {}).get("project_name")
    return {"risk_key": factor["key"], "risk_label": factor["label"], "k": factor["k"],
            "lesson": {"id": lesson["lesson_id"], "evidence_id": lesson["evidence_id"], "version": lesson["version"],
                       "decided_on": lesson["decided_on"], "text": lesson["statement"], "fit": lesson["fit"],
                       "ieg_status": lesson["ieg_status"], "review_date": lesson["review_date"],
                       "ieg_quote": ieg_quote(lesson)},
            "sources": [_source(evidence, name if evidence["project_id"] == lesson["project"]["project_id"] else None)
                        for evidence in lesson["evidence"]],
            "reports": factor["reports"],
            # Ticket 22's edges and ticket 23's disagreements have not landed, so no row has either yet.
            "related_notices": None, "disagreement": None}


def _claims(row: dict, m: int, counts_id: str) -> tuple[Claim, Claim]:
    """A row's two claims: its count, citing get_lessons' summary, and what helped, citing the lesson and its
    passages. Each restates its records' words in quote marks, the risk's name and the lesson's statement, so checks 1
    to 3 can prove it. The sentences are the verifier's input; the page writes the row from its own copy."""
    label, k = row["risk_label"], row["k"]
    text = row["lesson"]["text"].rstrip(". ")
    count = Claim(f'"{label}" came up in {k} of {m} completion reports for projects with comparable packages.',
                  "record", (counts_id,), (str(k), str(m)))
    helped = Claim(f'What helped with "{label}" was "{text}".', "quote",
                   (row["lesson"]["evidence_id"], *(source["evidence_id"] for source in row["sources"])))
    return count, helped


def _removed(row: dict, checked) -> dict:
    """A row the checks removed, as the removed box says it: which claim failed, and its first reason."""
    failed = next(sentence for sentence in checked if not sentence.kept)
    reason = failed.reasons[0]
    return {"risk_key": row["risk_key"], "risk_label": row["risk_label"],
            "claim_kind": "count" if failed is checked[0] else "helped", "k": row["k"],
            "lesson_text": row["lesson"]["text"], "check": reason.check, "reason_code": reason.code}


def _count_differs(row: dict, m: int, reports: Mapping) -> dict | None:
    """A row whose count is not the summary's own count for its risk, or whose table's m is not the summary's count
    of reports read, as the removed box says it: check 1's reason, before the verifier runs (ticket 30's verify O1)."""
    counted = {factor["key"]: factor["k"] for factor in reports["risk_factors"]}
    if row["k"] == counted.get(row["risk_key"]) and m == reports["read"]:
        return None
    return {"risk_key": row["risk_key"], "risk_label": row["risk_label"], "claim_kind": "count", "k": row["k"],
            "lesson_text": row["lesson"]["text"], "check": 1, "reason_code": NUMBER}


def build(engine: Engine, viewer: Viewer, *, as_of, criteria: Mapping | None, words: str | None = None,
          view: str = "staff", selected: Iterable[str] = (), missing: Iterable[str] = (),
          thresholds: Thresholds | None = None, decided_by=None, six_checks: SixChecks | None = None) -> RiskTable:
    """The section for one package, as of a date, as the viewer: its rows, counts, checks and empty reason.

    criteria are find_comparables' arguments for the package (its step_reference, or a planned package's
    comparables_query), or None while the package lacks a criterion, which missing names. words are the
    package's own, such as its description, which a lesson's fit is measured against; without them, a package
    from a STEP row is measured against its plan row's Description. selected are the risk keys the viewer stored
    for the package, shown and not. decided_by is for the hindsight test's replays only (ticket 34): the library as
    decided by that date, each lesson counted from the day its quotes became public (registry.Context.decided_by).
    six_checks are the app's six checks, with its judge (the package routes pass them); check 6 asks on this engine,
    as the viewer. Without them, the checks run with no judge, which a row needs only when checks 1 to 3 cannot
    prove it, and then removes it (judge_unavailable): the hindsight test's replays and a draft's read step."""
    limits = thresholds or load_thresholds()
    held = load_tools()
    lists = load_lesson_lists()
    max_rows = int(limits.value("package_risks.max_rows"))
    facts = Facts()
    context = registry.Context(engine, viewer, view, as_of, limits, decided_by)
    stored = list(dict.fromkeys(selected))
    registry_sources = list(dict.fromkeys(key for name in TOOLS for key in held[name].sources))
    names = load_sources()
    payload = {"rows": [], "p": None, "m": None, "most_common": None, "max_rows": max_rows,
               "coverage": {"missing": [], "sources": registry_sources}, "counted": [],
               "verifier": None, "empty_reason": None, "missing": list(missing), "written": None,
               "selected_keys": [], "selected_not_shown": [], "counts_evidence_id": None,
               "source_names": list(dict.fromkeys(names[key].dataset_name for key in registry_sources)),
               "data_through": None, "as_of": as_of.isoformat() if as_of else None}

    def finish(verdict: Verdict | None = None, **changes) -> RiskTable:
        payload.update(changes)
        shown = {row["risk_key"] for row in payload["rows"]}
        payload["selected_keys"] = [row["risk_key"] for row in payload["rows"] if row["risk_key"] in stored]
        payload["selected_not_shown"] = [
            {"risk_key": key, "risk_label": (lists.risk_factor(key).label if lists.risk_factor(key) else key)}
            for key in stored if key not in shown]
        return RiskTable(payload, facts, verdict)

    def run(name: str, arguments: Mapping) -> dict:
        result = registry.call(name, {key: value for key, value in arguments.items() if value is not None}, context,
                               held)
        keep_result(facts, name, result, held)
        return result

    if criteria is None:
        return finish(empty_reason="missing_criteria")
    comparables = run("find_comparables", criteria)
    payload["as_of"], payload["data_through"] = comparables["as_of"], comparables["records_through"]
    # A package from a STEP row is described by its plan row, which find_comparables read.
    words = words or (comparables.get("package") or {}).get("description")
    packages = [row["step_reference"] for row in comparables["rows"]] + [
        evidence[len(PACKAGE):] for entry in comparables["coverage"]["not_used"] for evidence in entry["evidence_ids"]
        if evidence.startswith(PACKAGE)]
    if not packages:
        return finish(empty_reason="no_comparables")

    counted = run("get_lessons", {"query": words, "packages": ",".join(dict.fromkeys(packages))})
    reports = counted["summary"]["reports"]
    p, m = reports["projects"], reports["read"]
    payload.update(p=p, m=m, counted=reports["counted"], counts_evidence_id=counted["summary"]["evidence_id"],
                   coverage={"missing": [{"reason_code": gap["reason_code"], "count": gap["count"]}
                                         for gap in reports["missing"]], "sources": registry_sources})
    if m == 0:
        return finish(empty_reason="no_reports")

    candidates = []
    for factor in reports["risk_factors"]:
        found = run("get_lessons", {"query": words, "risk_factor": factor["key"], "limit": 1})
        if found["rows"]:
            candidates.append((factor, found["rows"][0]))
    if not candidates:
        return finish(empty_reason="no_lessons")

    written = [_row(factor, lesson) for factor, lesson in sorted(candidates, key=rank)[:max_rows]]
    removed = [found for found in (_count_differs(row, m, reports) for row in written) if found]
    claimed = [row for row in written if not _count_differs(row, m, reports)]
    claims = [claim for row in claimed for claim in _claims(row, m, payload["counts_evidence_id"])]
    six = (six_checks or SixChecks(None, None, held, limits)).on(engine)
    check = six.checked(verify(claims, facts).sentences, facts)
    verdict = six.verdict_now(check, facts, Asker(viewer, view, as_of or registry.today(), "package-risks"))
    # A disagreement check 6 attached to a row's sentence comes with the row, both sides (DESIGN.md section 5).
    cards = {}
    for found in verdict.attached:
        cards.setdefault(found.after // 2, disagreement_event(found).data)
    kept = []
    for index, row in enumerate(claimed):
        checked = verdict.sentences[2 * index:2 * index + 2]
        if all(sentence.kept for sentence in checked):
            kept.append({**row, "disagreement": cards.get(index)})
        else:
            removed.append(_removed(row, checked))
    counts = verdict.counts()
    checks = {"counts": counts, "tools": list(TOOLS),
              "judge_failed": counts["judge"]["called"] and counts["judge"]["responded"] is False,
              "unjudged": counts["judge"]["unjudged"], "removed": removed}
    if not kept:
        return finish(verdict, verifier=checks, empty_reason="all_removed", written=len(written))
    k_max = max(row["k"] for row in kept)
    return finish(verdict, rows=kept, verifier=checks,
                  most_common={"risk_keys": [row["risk_key"] for row in kept if row["k"] == k_max], "k_max": k_max})
