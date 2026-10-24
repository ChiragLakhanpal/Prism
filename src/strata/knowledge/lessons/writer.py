"""The review-proposed-lessons workflow: the lesson review writer's summary of each new item's evidence and
the current lessons it may repeat, checked by the verifier before anyone reads it (ticket 29; spec,
"Workflows and drafts"; the 29 design brief, sections 4.6, 5.7 and 5.8).

For each open item (a new lesson, a re-check or a cross-check) waiting in the queue, the workflow:

1. reads the item's evidence (the quotes and the whole passages they are in) and the library's current
   lessons, the only lessons a lead may merge it into;
2. sends the writer agent (config/agents.toml, lesson_review_writer) one message that carries data only;
3. runs the verifier's checks 1 to 3 on every sentence it wrote (strata.agent.verifier), with the item's
   passages and the current lessons as the only evidence it may cite, so a sentence that states a number
   no passage quotes, cites something else or misquotes a page is removed and shown with its reason;
4. keeps at most lesson_review.likely_repeats_max likely repeats, each a current lesson with at least one
   kept sentence, and stores the result in strata.ops.lesson_review_notes.

It writes again for an item when a decision has changed the library since its last note, or when the
writer gave no answer last time, so the likely repeats name only current lessons. The nightly job's
propose_lessons task runs it after it queues new items; the review page's "Try again" runs it for one item.
The writer is the Foundry agent on the workspace; offline, the scripted agent replays its recorded answers
(tests/fixtures/agent/lesson_review.toml). This workflow is plain Python, as the draft runtime is: the
Microsoft Agent Framework package is not added (a parked decision).
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from collections.abc import Callable
from functools import cache
from importlib import resources
from pathlib import Path

from strata.agent.claims import ClaimsError, claims_from
from strata.agent.loop import AgentError, output_text
from strata.agent.verifier import Verdict, answer_events, check
from strata.harness.facts import Facts
from strata.knowledge.lessons.review import Store, _int, _iso, _json
from strata.lakehouse.engine import Engine

log = logging.getLogger("strata.lessons")
TOOL = "lesson_review"  # what the check line names as the source of the evidence
LESSONS = "strata.ops.lesson_versions"
PASSAGES = "strata.gold.passage"
NOTE_COLUMNS = ("item_id", "written_at", "status", "content", "library_versions", "agent", "agent_version", "error",
                "public_from")
ROOT = Path(__file__).resolve().parents[4]
RECORDED_CASES = ROOT / "tests" / "fixtures" / "agent" / "lesson_review.toml"


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.knowledge.lessons") / "sql" / f"{name}.sql").read_text()


def latest_notes(engine: Engine) -> dict[str, dict]:
    """The newest note on each item."""
    result = engine.run(_sql("review_notes"), {})
    notes: dict[str, dict] = {}
    for row in (dict(zip(result.columns, row, strict=True)) for row in result.rows):
        notes[row["item_id"]] = row  # oldest first, so the last one stays
    return notes


def library_versions(store: Store) -> int:
    return sum(len(versions) for versions in store.versions.values())


def lesson_evidence_id(lesson_id: str, version) -> str:
    return f"{LESSONS}:{lesson_id}/v{_int(version)}"


def facts_for(store: Store, item: dict, subject: dict) -> tuple[Facts, list[dict], list[dict]]:
    """What the writer may cite: the item's passages, and the current lessons it could repeat."""
    facts = Facts()

    def passages_of(rows: list[dict]) -> list[dict]:
        found = []
        for row in rows:
            # The passage in search_passages' row shape, so the evidence drawer opens it from the note with no request.
            project = store.projects.get(row["project_id"]) or {}
            passage = {"passage_id": row["passage_id"], "text": row.get("passage_text") or "", "kind": "paragraph",
                       "language": row.get("language"), "document_type": row["document_type"],
                       "project_id": row["project_id"], "paragraph": row["paragraph"], "pdf_page": _int(row["cited_page"]),
                       "source": {"document_type": row["document_type"], "project_id": row["project_id"],
                                  "project_name": project.get("project_name"),
                                  "document_date": row["document_date"].isoformat()
                                  if hasattr(row["document_date"], "isoformat") else row["document_date"],
                                  "report_number": row["report_number"], "paragraph": row["paragraph"],
                                  "pdf_page": _int(row["cited_page"])}}
            evidence_id = f"{PASSAGES}:{row['passage_id']}"
            facts.record(evidence_id, passage, tool=TOOL)
            found.append({"evidence_id": evidence_id, "role": row["role"], "document_type": row["document_type"],
                          "paragraph": row["paragraph"], "page": _int(row["cited_page"]), "quote": row["quote"],
                          "text": passage["text"]})
        return found

    passages, library = passages_of(subject["evidence"]), []
    own = store.lesson_of(item)
    for lesson_id, versions in sorted(store.versions.items()):
        latest = versions[-1]
        if latest["state"] != "current" or lesson_id == own:
            continue
        evidence_id = lesson_evidence_id(lesson_id, latest["version"])
        # The lesson in get_lessons' row shape, so the evidence drawer names it by its statement, version and date.
        lesson = {"lesson_id": lesson_id, "version": _int(latest["version"]), "statement": latest["statement"],
                  "decided_on": _iso(latest["decided_on"])}
        facts.record(evidence_id, lesson, tool="get_lessons")
        # A library lesson's own passages, so a sentence about what the two lessons share can quote and cite them.
        rows = [row for proposal in store.lesson_proposals(lesson_id) for row in store.evidence.get(proposal, [])]
        library.append({"evidence_id": evidence_id, **lesson, "evidence": passages_of(rows)})
    return facts, passages, library


def message(subject: dict, passages: list[dict], library: list[dict], most: int) -> dict:
    row = subject["row"] or {}
    return {"task": "lesson_review", "lesson": {"statement": subject["statement"], "kind": row.get("kind"),
                                                 "stage": row.get("stage"),
                                                 "risk_factors": _json(row.get("risk_factors"), [])},
            "evidence": passages, "library": library, "max_repeats": most}


def parse(text: str) -> tuple[list, list[tuple[str, list]]]:
    """The writer's summary claims, and each likely repeat's lesson id with its claims."""
    try:
        answer = json.loads(text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ClaimsError(f"The writer's answer is not JSON: {error}.") from error
    if not isinstance(answer, dict) or not isinstance(answer.get("summary", []), list) \
            or not isinstance(answer.get("repeats", []), list):
        raise ClaimsError("The writer's answer must be an object with a summary and a list of repeats.")
    repeats = []
    for number, repeat in enumerate(answer.get("repeats") or [], 1):
        if not isinstance(repeat, dict) or not isinstance(repeat.get("lesson_id"), str):
            raise ClaimsError(f"Repeat {number} does not name its lesson_id.")
        repeats.append((repeat["lesson_id"], claims_from(repeat.get("claims") or [])))
    return claims_from(answer.get("summary") or []), repeats


def compose(facts: Facts, library: list[dict], summary: list, repeats: list[tuple[str, list]], most: int) -> dict:
    """The note: the kept summary sentences, the likely repeats that kept a sentence, the evidence cited, the
    verifier's counts and the removed sentences, each with its reasons."""
    current = {lesson["lesson_id"]: lesson for lesson in library}
    # Only a current lesson can be a likely repeat: the writer's words about any other lesson are not checked or
    # shown, as a lead can merge into no other lesson (the 29 brief, section 4.2).
    repeats = [(lesson_id, claims) for lesson_id, claims in repeats if lesson_id in current]
    checked, owners = [], []
    for claim in summary:
        checked.append(check(len(checked), claim, facts))
        owners.append(None)
    for lesson_id, claims in repeats:
        for claim in claims:
            checked.append(check(len(checked), claim, facts))
            owners.append(lesson_id)
    verdict = Verdict(tuple(checked))
    kept: dict[str | None, list[dict]] = {}
    evidence, counts, removed = {}, None, []
    for event in answer_events(verdict, facts, [TOOL]):
        data = dict(event.data)
        if event.type == "sentence":
            kept.setdefault(owners[data["index"]], []).append(data)
        elif event.type == "evidence":
            evidence[data["id"]] = data
        elif event.type == "checks":
            counts = data
        elif event.type == "removed":
            removed.append({**data, "repeat_of": owners[data["index"]]})
    found = [{"lesson_id": lesson_id, "version": current[lesson_id]["version"], "sentences": kept[lesson_id]}
             for lesson_id, _ in repeats if kept.get(lesson_id)][:most]
    status = ("nothing_to_add" if not summary and not repeats
              else "nothing_survived" if not verdict.kept else "ready")
    return {"status": status, "sentences": kept.get(None, []), "repeats": found, "evidence": evidence,
            "checks": counts, "removed": removed}


def write_one(engine: Engine, store: Store, item: dict, subject: dict, agent, now: dt.datetime, most: int) -> dict:
    """The writer's note on one item, stored as a new row. A writer that gives no answer leaves a failed row."""
    facts, passages, library = facts_for(store, item, subject)
    row = {"item_id": item["item_id"], "written_at": now, "library_versions": library_versions(store),
           "agent": getattr(agent, "name", None), "agent_version": None, "error": None, "public_from": now.date()}
    try:
        response = agent.respond([{"role": "user", "content": json.dumps(message(subject, passages, library, most),
                                                                          ensure_ascii=False, default=str)}], None)
        row["agent_version"] = getattr(agent, "version", None)
        summary, repeats = parse(output_text(response))
    except (AgentError, ClaimsError) as error:
        log.warning("The lesson review writer gave no answer for %s: %s", item["item_id"], error)
        row |= {"status": "failed", "content": None, "error": getattr(error, "code", None) or str(error)[:300]}
    else:
        note = compose(facts, library, summary, repeats, most)
        row |= {"status": note["status"], "content": json.dumps(note, ensure_ascii=False, default=str)}
    engine.insert_rows("strata.ops.lesson_review_notes", NOTE_COLUMNS, [tuple(row[column] for column in NOTE_COLUMNS)])
    return row


def needs_a_note(store: Store, item: dict, note: dict | None) -> bool:
    """An open item of any kind: a re-check's or cross-check's page summarizes the lesson's current evidence."""
    if store.stage(item) == "decided":
        return False
    return note is None or note["status"] == "failed" or _int(note["library_versions"]) != library_versions(store)


def run(engine: Engine, agent_for: Callable[[dict, dict], object | None], clock: Callable[[], dt.datetime],
        most: int, review=None) -> int:
    """A note for each open item (a new lesson, a re-check or a cross-check) that needs one. Returns the notes
    written. agent_for gives the writer for an
    item and its subject, or None when there is none, and the item keeps waiting for its note."""
    from strata.knowledge.lessons.review import LessonReview

    store = Store(engine)
    review = review or LessonReview(roles=None)  # subject() reads the store only; no one acts here
    notes = latest_notes(engine)
    written = 0
    for item in sorted(store.items.values(), key=lambda found: found["item_id"]):
        if not needs_a_note(store, item, notes.get(item["item_id"])):
            continue
        subject = review.subject(store, item)
        agent = agent_for(item, subject)
        if agent is None:
            continue
        write_one(engine, store, item, subject, agent, clock(), most)
        written += 1
    return written


# ── Offline: the scripted writer ─────────────────────────────────────────

def recorded_agent_for(path: Path = RECORDED_CASES) -> Callable[[dict, dict], object | None]:
    """The scripted writer for each item whose cited passage has a recorded answer, else None."""
    from strata.agent.scripted import ScriptedAgent, load_cases

    cases = load_cases(path)

    def agent_for(item: dict, subject: dict):
        first = next((row for row in subject["evidence"] if row["role"] == "source"), None)
        case = cases.get(f"lesson-review-{first['passage_id'].replace('/', '-')}") if first else None
        return ScriptedAgent(case) if case else None
    return agent_for
