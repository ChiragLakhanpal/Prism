"""What a draft's author chose for rows that cite a changed lesson, and the draft as those choices leave it (ticket 39;
the 39 brief, sections 4.4 to 4.6).

A draft is saved once and never rewritten (strata.ops.drafts). Each choice its author makes on a version notice is a
new row in strata.ops.draft_lesson_choices, and apply() lays them over the saved draft, in order, so every screen and
file reads the draft as the author left it:

- update   the row's notes become the ones the kind's writer rewrote from the lesson's current version, which the
           verifier checked; the row now cites that version, and its earlier text stays on record for "Show the
           earlier text" and "Go back to version {a}".
- revert   undoes the latest update of that row, with no model call.
- keep     the row keeps citing its version; the reason is kept, and the notice comes back only for a later change.
- remove   the row leaves the draft's notes, its counts, its sources and its Word file; it stays on record, so
- restore  brings it back as it was.

Nothing here decides a tier; strata.knowledge.lessons.notices does, from the draft apply() returns.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
from dataclasses import dataclass

ACTIONS = ("update", "keep", "remove", "restore", "revert")
COLUMNS = ("draft_id", "choice_no", "row_key", "lesson_id", "action", "cited_version", "current_version", "reason",
           "rewrite", "draft_state", "actor_id", "actor_name", "chosen_at", "public_from")
VERSIONS = "strata.ops.lesson_versions"


@dataclass(frozen=True)
class LessonChoice:
    choice_no: int
    row_key: str
    lesson_id: str
    action: str
    cited_version: int
    current_version: int
    reason: str | None
    rewrite: dict | None
    draft_state: str
    actor_name: str | None
    chosen_at: dt.datetime

    def as_dict(self) -> dict:
        return {"row_key": self.row_key, "lesson_id": self.lesson_id, "action": self.action,
                "cited_version": self.cited_version, "current_version": self.current_version, "reason": self.reason,
                "at": self.chosen_at.astimezone(dt.UTC).isoformat().replace("+00:00", "Z"), "by": self.actor_name}


def cites(version_id: str, lesson_id: str, version: int) -> bool:
    return version_id == f"{VERSIONS}:{lesson_id}/v{version}"


def _row_keys(content: dict, row_key: str) -> set[str]:
    """The keys of the notes that make up a row: a suggested PPSD row's cells, or the note itself."""
    for row in (content.get("ppsd") or {}).get("rows") or []:
        if row["row_key"] == row_key:
            return set((row.get("cells") or {}).values())
    return {row_key}


def apply(content: dict, choices: list[LessonChoice]) -> dict:
    """The draft as its author's choices leave it. The saved content is not changed; a copy is."""
    if not choices:
        return content
    shown = copy.deepcopy(content)
    original = {note["key"]: note for note in content.get("notes") or []}
    rows = {row["row_key"]: row for row in (shown.get("ppsd") or {}).get("rows") or []}
    updates: dict[tuple[str, str], list[LessonChoice]] = {}
    kept: dict[tuple[str, str], LessonChoice] = {}
    removed: dict[str, LessonChoice | None] = {}
    for choice in sorted(choices, key=lambda one: one.choice_no):
        key = (choice.row_key, choice.lesson_id)
        if choice.action == "update":
            updates.setdefault(key, []).append(choice)
            kept.pop(key, None)
        elif choice.action == "revert" and updates.get(key):
            updates[key].pop()
        elif choice.action == "keep":
            kept[key] = choice
        elif choice.action == "remove":
            removed[choice.row_key] = choice
        elif choice.action == "restore":
            removed.pop(choice.row_key, None)

    notes = {note["key"]: note for note in shown.get("notes") or []}
    for (row_key, lesson_id), done in updates.items():
        if not done:
            continue
        latest = done[-1]
        for note in latest.rewrite.get("notes") or []:
            if note["key"] in notes:
                notes[note["key"]] = {**notes[note["key"]], **note}
        shown["evidence"] = {**(shown.get("evidence") or {}), **(latest.rewrite.get("evidence") or {})}
        row = rows.get(row_key)
        if row is not None and (row.get("lesson") or {}).get("id") == lesson_id:
            row["lesson"] = {**row["lesson"], "version": latest.current_version,
                             "evidence_id": f"{VERSIONS}:{lesson_id}/v{latest.current_version}"}
            if latest.rewrite.get("sources") is not None:
                row["sources"] = latest.rewrite["sources"]
        earlier = [original[key] for key in sorted(_row_keys(content, row_key)) if key in original]
        shown.setdefault("lesson_updated", []).append({**latest.as_dict(), "earlier": earlier})
    shown["notes"] = [notes[note["key"]] for note in shown.get("notes") or []]
    shown["lesson_kept"] = [choice.as_dict() for choice in kept.values()]
    gone = {key for row_key in removed for key in _row_keys(content, row_key)}
    shown["notes"] = [note for note in shown["notes"] if note["key"] not in gone]
    for row_key, choice in removed.items():
        if row_key in rows:
            rows[row_key]["removed"] = True
            rows[row_key]["removed_at"] = choice.as_dict()["at"]
    shown["lesson_removed"] = [choice.as_dict() for choice in removed.values()]
    return shown


def from_row(row: dict, moment) -> LessonChoice:
    """One stored choice, from either engine (DuckDB gives typed values, the SQL warehouse text)."""
    rewrite = row["rewrite"]
    return LessonChoice(int(row["choice_no"]), row["row_key"], row["lesson_id"], row["action"], int(row["cited_version"]),
                        int(row["current_version"]), row["reason"] or None,
                        json.loads(rewrite) if rewrite else None, row["draft_state"], row["actor_name"],
                        moment(row["chosen_at"]))
