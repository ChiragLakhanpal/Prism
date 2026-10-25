"""The draft runtime: writing a draft, moving it between states, and what its page and the Drafts tab show
(ticket 35; adapted from fairshare's server/drafts.py and harness/agents.py).

Writing (write) runs one draft kind's workflow (config/drafts.toml) in four steps, each announced as a
step event: read the facts as the viewer, have the writer agent write, run the verifier's six checks on every
sentence (CLAUDE.md rule 1; src/strata/agent/answer_check.py, shared with the answer stream), and save. Nothing is saved until the writer and the verifier finish, and nothing is
saved when no sentence passed the checks, so a failed model call leaves nothing in Drafts.

A draft moves from draft to checked to exported, and to discarded and back, only when its author acts
(ACTIONS). fairshare's second state is gone, and no code that reaches the screen uses its word.

draft_view and list_row build what the draft page and the Drafts tab read. Every count the screens state
comes from here: the sources a draft cites, how many of them the viewer opened since it was saved, how
many citations become footnotes, and the holds that keep it from export.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import importlib
import json
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from functools import cache

from strata.agent.answer_check import Asker, SixChecks
from strata.agent.claims import ClaimsError, claims_from
from strata.agent.loop import AgentError, output_text
from strata.agent.verifier import AnswerCheck, Verdict, answer_events, check
from strata.config import DraftKind, DraftKinds
from strata.dbx import Viewer
from strata.drafts.holds import Draft as HoldDraft
from strata.drafts.store import DraftStore, NewDraft, Saved, iso
from strata.harness.facts import Facts
from strata.harness.turn import Event
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.server.access import is_author
from strata.server.engines import EngineFor

log = logging.getLogger("strata.drafts")
STAFF = "staff"
# Why a draft could not be written, as the writing page's error event says it. web/src/copy.ts has one
# sentence for each kind under draft.kinds.<kind>.writeErrors.
# permission is the viewer's own read of the facts refused; draft_store is the app's own account unable to
# save the draft, which the viewer cannot fix.
WRITE_ERRORS = ("no_agent", "agent_unavailable", "content_filter", "agent_output", "data_service", "no_plan",
                "nothing_marked", "permission", "draft_store", "internal",
                # A mission brief (ticket 37): no such project, or one no longer active.
                "no_project", "not_active",
                # Suggested PPSD rows (ticket 36): no such package, or no selected risk still in its table.
                "no_package", "no_selected_risks")
OPEN_STATES = ("draft", "checked")


@dataclass(frozen=True)
class Action:
    """One act of a draft's author: the states it starts from, the state it moves to (None: back to the
    state a discarded draft was discarded from) and the capability a refusal names (the 40 brief)."""

    starts: tuple[str, ...]
    to: str | None
    capability: str


ACTIONS = {
    "check": Action(("draft",), "checked", "check"),
    "export": Action(("checked",), "exported", "export"),
    "discard": Action(("draft", "checked"), "discarded", "check"),
    "restore": Action(("discarded",), None, "check"),
}


@cache
def writer_module(kind: DraftKind):
    return importlib.import_module(kind.writer)


@cache
def function(path: str) -> Callable:
    module, name = path.split(":")
    return getattr(importlib.import_module(module), name)


def step(name: str, status: str, **details) -> Event:
    return Event("step", {"id": name, "kind": name, "status": status, **details})


# ── Writing ──────────────────────────────────────────────────────────────

class WriteError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def parse_notes(text: str, key: str) -> dict[str, dict]:
    """The writer's notes by the key that names each, such as an activity's STEP reference: its claims,
    or the code it refused with."""
    try:
        answer = json.loads(text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ClaimsError(f"The writer's answer is not JSON: {error}.") from error
    if not isinstance(answer, dict) or not isinstance(answer.get("notes"), list):
        raise ClaimsError("The writer's answer must be an object with a list of notes.")
    notes = {}
    for number, note in enumerate(answer["notes"], 1):
        if not isinstance(note, dict) or not isinstance(note.get(key), str):
            raise ClaimsError(f"Note {number} does not name its {key}.")
        refusal = note.get("refusal")
        notes[note[key]] = {"refusal": str(refusal)} if refusal else {"claims": claims_from(note.get("claims") or [])}
    return notes


def note_check(module, facts, written: dict[str, dict], six_checks: SixChecks,
               language: str = "en") -> tuple[AnswerCheck, Facts, list[str]]:
    """Checks 1 to 3 on what the writer wrote, each note against its own item's row, then check 5, ready for
    checks 6 and 4 (SixChecks.finish); with every row the check returned, and the item each sentence belongs to.

    Each note cites only its own item's row, so the verifier checks each note's sentences against that row
    alone: a sentence that cites another item's row is removed as a source the check did not return for this
    note (id_not_returned), even though the tool returned that row for another note."""
    seen = Facts()
    # A kind whose items cite several tools' rows, such as the mission brief's (ticket 37), names each row's tool.
    cited = module.cited_rows(facts) if hasattr(module, "cited_rows") else [(row, module.TOOL) for row in facts.rows]
    for row, tool in cited:
        seen.record(row["evidence_id"], row, tool=tool)
    checked, owners = [], []
    for item in module.items(facts):
        own = Facts()
        for evidence_id in item.get("evidence_ids") or [item["evidence_id"]]:
            own.record(evidence_id, seen.get(evidence_id), tool=seen.tool(evidence_id))
        for claim in (written.get(item["key"]) or {}).get("claims") or []:
            checked.append(check(len(checked), claim, own, language))
            owners.append(item["key"])
    return six_checks.checked(checked, seen), seen, owners


def compose(module, facts, written: dict[str, dict], verdict: Verdict, seen: Facts, owners: list[str]) -> dict:
    """The draft from what the writer wrote and what the six checks kept: one note per item, in order, each
    with its kept sentences, the evidence they cite, the verifier's counts, the removed sentences, and any
    disagreement check 6 shows under a note's sentence."""
    items = module.items(facts)
    events = answer_events(verdict, seen, list(getattr(module, "TOOLS", (module.TOOL,))))
    kept: dict[str, list[dict]] = {}
    evidence, checks, removed, disagreements = {}, None, [], []
    for event in events:
        data = dict(event.data)
        if event.type == "sentence":
            kept.setdefault(owners[data["index"]], []).append(data)
        elif event.type == "evidence":
            evidence[data["id"]] = data
        elif event.type == "checks":
            checks = data
        elif event.type == "removed":
            removed.append({**data, "key": owners[data["index"]]})
        elif event.type == "disagreement":
            disagreements.append({**data, "key": owners[data["after"]]})
    notes = []
    for item in items:
        wrote = written.get(item["key"]) or {}
        state = "refused" if wrote.get("refusal") else "written" if kept.get(item["key"]) else "abstained"
        notes.append({"key": item["key"], module.KEY: item["key"], "evidence_id": item["evidence_id"],
                      "description": item["description"],
                      "mark": item["mark"], "state": state, "refusal": wrote.get("refusal"),
                      "sentences": kept.get(item["key"], []), **item.get("extra", {})})
    return {"subject": module.subject(facts), "notes": notes, "evidence": evidence, "checks": checks,
            "removed": removed, "disagreements": disagreements}


@dataclass
class Writing:
    """One draft being written: what it is, who asked, and where it goes."""

    kind: DraftKind
    request: dict
    viewer: Viewer
    team_key: str
    idempotency_key: str | None
    run_id: str
    language: str = "en"
    # Filled as it runs, for the run log.
    question: str | None = None
    agent: str | None = None
    agent_version: str | None = None
    verdict: Verdict | None = None
    draft_id: str | None = None


async def write(writing: Writing, engine_for: EngineFor, agent_for: Callable[[str], object | None],
                store: DraftStore, today: dt.date, now: Callable[[], dt.datetime],
                new_draft_id: Callable[[], str], six_checks: SixChecks) -> AsyncIterator[Event]:
    """The writing of one draft, as events: the four steps, then the saved draft's id, or the removed
    sentences when none passed. A step that cannot run raises WriteError with its code. The check step runs all
    six checks (src/strata/agent/answer_check.py), as the viewer and as of today: its own steps inside it are not
    sent, since the writing page lists four."""
    module = writer_module(writing.kind)

    def read():
        with engine_for(writing.viewer) as engine:
            return module.read(engine, writing.viewer, writing.request, today)

    yield step("read", "running")
    try:
        facts = await asyncio.to_thread(read)
    except module.NotWritable as error:
        raise WriteError(error.code) from error
    except PermissionDenied as error:
        raise WriteError("permission") from error
    except EngineError as error:
        raise WriteError("data_service") from error
    writing.question = module.question(facts)
    # What the read step says it read: a plan's date for review notes, or the kind's own counts (ticket 37).
    read_done = module.read_done(facts) if hasattr(module, "read_done") else {"plan_date": facts.result["plan"]["plan_date"]}
    yield step("read", "done", **read_done)

    items = module.items(facts)
    yield step("write", "running", count=len(items))
    agent = agent_for(writing.kind.key)
    if agent is None:
        raise WriteError("no_agent")
    writing.agent = getattr(agent, "name", None)
    message = [{"role": "user", "content": json.dumps(module.message(facts, writing.language), ensure_ascii=False,
                                                      default=str)}]
    try:
        response = await asyncio.to_thread(agent.respond, message, None)
        writing.agent_version = getattr(agent, "version", None)
        written = parse_notes(output_text(response), module.KEY)
    except AgentError as error:
        raise WriteError(error.code) from error
    except ClaimsError as error:
        log.warning("The writer of run %s answered in a shape I can't read: %s", writing.run_id, error)
        raise WriteError("agent_output") from error
    claimed = [key for key, note in written.items() if note.get("claims")]
    wrote = {"notes": len(claimed), "sentences": sum(len(written[key]["claims"]) for key in claimed)}
    if hasattr(module, "written_rows"):  # suggested PPSD rows count rows, two cells each (ticket 36)
        wrote["rows"] = module.written_rows(claimed)
    yield step("write", "done", **wrote)

    yield step("check", "running")
    check_notes, seen, owners = note_check(module, facts, written, six_checks, writing.language)
    verdict = None
    async for item in six_checks.finish(check_notes, seen, Asker(writing.viewer, STAFF, today, writing.run_id)):
        if isinstance(item, Verdict):
            verdict = item
    content = compose(module, facts, written, verdict, seen, owners)
    if hasattr(module, "finish"):  # a kind that groups its notes, such as suggested PPSD rows' cells into rows
        content = module.finish(content, facts)
    writing.verdict = verdict
    counts = content["checks"]
    yield step("check", "done", checks_run=counts["checks_run"], checks=len(counts["checks_run"]),
               written=counts["sentences"]["written"], removed=counts["sentences"]["removed"])
    if not verdict.kept:
        yield Event("nothing_survived", {"removed": content["removed"], "checks": counts})
        return

    yield step("save", "running")
    draft_id = new_draft_id()
    # What the writer wrote, for the steps the draft page lists ("I wrote six sentences in three notes.").
    content |= {"kind": writing.kind.key, "written": wrote,
                "writer": {"agent": writing.agent, "version": writing.agent_version, "run_id": writing.run_id}}
    record = NewDraft(draft_id, writing.kind.key, writing.team_key, writing.viewer.user_id, writing.viewer.name,
                      writing.idempotency_key, content["subject"].get("project_id"), module.subject_key(facts),
                      content, now())
    try:
        await asyncio.to_thread(store.create, record)
    except EngineError as error:  # the app's own account saves drafts, a PermissionDenied included
        raise WriteError("draft_store") from error
    writing.draft_id = draft_id
    yield step("save", "done")
    yield Event("draft", {"draft_id": draft_id})


# ── What the screens read ────────────────────────────────────────────────

def written_notes(saved: Saved) -> int:
    return sum(1 for note in saved.content["notes"] if note["state"] == "written")


def sources(content: dict) -> list[dict]:
    """The distinct sources the kept sentences cite, numbered in order of first appearance, as the
    citation markers are, with the notes that cite each."""
    found: dict[str, dict] = {}
    for note in content["notes"]:
        for sentence in note["sentences"]:
            for evidence in sentence["evidence_ids"]:
                entry = found.setdefault(evidence, {"evidence_id": evidence, "number": len(found) + 1, "cited_in": []})
                key = note["key"]
                if key not in entry["cited_in"]:
                    entry["cited_in"].append(key)
    return list(found.values())


def citations(content: dict) -> int:
    """How many citations the kept sentences carry: each one becomes a footnote in the Word file."""
    return sum(len(sentence["evidence_ids"]) for note in content["notes"] for sentence in note["sentences"])


def writer_module_for(kind: str):
    """The writer module of a kind by its key, or None for a kind the registry no longer lists."""
    from strata.config import load_draft_kinds

    found = load_draft_kinds().kinds.get(kind)
    return writer_module(found) if found else None


def kind_view(saved: Saved) -> dict:
    """What a kind adds to its page, such as suggested PPSD rows' form, fields and footnotes (ticket 36): one marker
    per sentence, which may carry several sources and becomes one footnote. Each footnote's text is built here, once,
    and the page shows the same string as its "In Word:" line."""
    module = writer_module_for(saved.kind)
    if module is None or not hasattr(module, "view"):
        return {}
    from strata.drafts.files import words

    fields = {key: value.value for key, value in saved.fields.items()}
    shown = {module.VIEW_KEY: module.view(saved.content, fields, words())}
    if hasattr(module, "footnotes"):
        shown["footnotes"] = module.footnotes(saved.content, words())
    return shown


def hold_input(saved: Saved, kinds: DraftKinds, view: str) -> HoldDraft:
    """The draft as the holds read it: its state now, the view, what it holds, its fields and its choices."""
    return HoldDraft(saved.state.state, view, saved.kind, saved.content,
                     {key: value.value for key, value in saved.fields.items()},
                     {key: choice.kept for key, choice in saved.choices.items()}, kinds.cards_on_drafts)


def holds(saved: Saved, kinds: DraftKinds, view: str) -> list[dict]:
    """The holds that keep the draft from export now, in the order its kind names them, each with how many items
    it has left and the anchor of the first, for the bar's link to it (the 36 brief, section 4.5)."""
    kind = kinds.kinds[saved.kind]
    draft = hold_input(saved, kinds, view)
    found = []
    for key in kind.holds:
        held = function(kinds.holds[key].test)(draft)
        if held is not None and held.left > 0:
            found.append({"key": key, "copy": kinds.holds[key].copy, "left": held.left,
                          "first_anchor": held.first_anchor})
    return found


def _who(step, viewer: Viewer) -> dict | None:
    if step is None:
        return None
    return {"at": iso(step.changed_at), "by": step.actor_name, "you": bool(viewer.user_id) and step.actor_id == viewer.user_id}


def draft_view(saved: Saved, viewer: Viewer, view: str, kinds: DraftKinds, opened: dict[str, dt.datetime]) -> dict:
    """A draft as its page shows it to this viewer, in this view."""
    kind = kinds.kinds[saved.kind]
    listed = [{**entry, "opened": entry["evidence_id"] in opened,
               "last_opened_at": iso(opened.get(entry["evidence_id"]))} for entry in sources(saved.content)]
    state = saved.state
    export = saved.export
    extra = kind_view(saved)
    return {
        "draft_id": saved.draft_id,
        "kind": saved.kind,
        "state": state.state,
        "discarded_from": state.from_state if state.state == "discarded" else None,
        "author": {"name": saved.author_name, "you": is_author(viewer, saved.author_id)},
        "created_at": iso(saved.created_at),
        "checked": _who(saved.last("checked"), viewer),
        "discarded": _who(state, viewer) if state.state == "discarded" else None,
        "subject": saved.content["subject"],
        "counts": {"signal": saved.content["subject"].get("signal"), "written": written_notes(saved)},
        "written": saved.content.get("written"),
        "notes": saved.content["notes"],
        "evidence": saved.content["evidence"],
        "checks": saved.content["checks"],
        "checks_count": len(saved.content["checks"]["checks_run"]),
        "removed": saved.content["removed"],
        "sources": listed,
        # One footnote per marker where a kind numbers its footnotes (ticket 36); else one per citation.
        "citations": len(extra["footnotes"]) if "footnotes" in extra else citations(saved.content),
        "opened": {"count": sum(1 for entry in listed if entry["opened"]), "of": len(listed)},
        "layout": {"columns": list(kind.columns), "export": kind.export, "sources_list": kind.sources_list,
                   "removed_box": kind.removed_box, "not_checked": list(kind.not_checked)},
        "holds": holds(saved, kinds, view),
        "may_act": is_author(viewer, saved.author_id) and view == STAFF and state.state != "exported",
        "export": None if export is None else {
            "export_id": export.export_id, "exported_at": iso(export.exported_at), "by": export.actor_name,
            "you": bool(viewer.user_id) and export.actor_id == viewer.user_id, "footnotes": export.footnotes,
            "sources": export.sources, "opened": export.opened,
            "disagreements": sum(1 for row in export.snapshot.get("sources", []) if row.get("kept_another")),
            "files": list(export.files),
            "files_available": bool(export.files)},
        "writer": saved.content.get("writer"),
        # The disagreements check 6 attached, and the report kept on each (ticket 36).
        "disagreements": saved.content.get("disagreements") or [],
        "choices": [{"disagreement_id": key, "kept": choice.kept, "reason": choice.reason, "at": iso(choice.set_at),
                     "by": choice.set_by_name} for key, choice in saved.choices.items()],
        **extra,
    }


def list_row(saved: Saved, viewer: Viewer, opened: dict[str, dt.datetime] | None) -> dict:
    """A draft as the Drafts tab lists it. opened is given only for the viewer's own drafts to check. Suggested PPSD
    rows add their progress: how many owners are set and, in the Long Form, how many rows are rated (ticket 36)."""
    listed = sources(saved.content)
    shown = kind_view(saved)
    progress = shown["ppsd"] if "ppsd" in shown else None
    return {
        "draft_id": saved.draft_id,
        "kind": saved.kind,
        "state": saved.state.state,
        "subject": saved.content["subject"],
        "notes": written_notes(saved),
        "author": {"name": saved.author_name, "you": is_author(viewer, saved.author_id)},
        "created_at": iso(saved.created_at),
        "changed": _who(saved.state, viewer),
        "checked": _who(saved.last("checked"), viewer),
        "exported": _who(saved.last("exported"), viewer),
        "opened": None if opened is None else {
            "count": sum(1 for entry in listed if entry["evidence_id"] in opened), "of": len(listed)},
        **({"progress": {**progress["counts"], "form": progress["form"], "rows": len(progress["rows"])}}
           if progress else {}),
    }
