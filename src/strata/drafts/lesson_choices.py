"""What a draft's author chose for rows that cite a changed lesson, and the draft as those choices leave it (ticket 39;
the 39 brief, sections 4.4 to 4.6).

A draft is saved once and never rewritten (strata.ops.drafts). Each choice its author makes on a version notice is a
new row in strata.ops.draft_lesson_choices, and apply() lays them over the saved draft, in order, so every screen and
file reads the draft as the author left it:

- update   the row's notes become the ones the kind's writer rewrote from the lesson's current version, which the
           verifier checked; the row now cites that version, and its earlier text stays on record for "Show the
           earlier text" and "Go back to version {a}". The sentences the verifier removed from the rewrite take the
           place of the earlier text's in the removed box (CLAUDE.md rule 2), and the counts the screens show (the
           steps' sentences and the check line's) are the draft's as it now stands.
- revert   undoes the latest update of that row, with no model call.
- keep     the row keeps citing its version; the reason is kept, and the notice comes back only for a later change.
- remove   the row leaves the draft's notes, its counts, its sources, its check line and its Word file; it stays on
           record, so the sentences the verifier removed from it stay in the removed box, and
- restore  brings it back as it was.

Nothing here decides a tier; strata.knowledge.lessons.notices does, from the draft apply() returns.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
from collections.abc import Mapping
from dataclasses import dataclass

from strata.agent.verifier import kept_counts

ACTIONS = ("update", "keep", "remove", "restore", "revert")
COLUMNS = ("draft_id", "choice_no", "row_key", "lesson_id", "action", "cited_version", "current_version", "reason",
           "rewrite", "draft_state", "actor_id", "actor_name", "chosen_at", "public_from")
VERSIONS = "strata.ops.lesson_versions"
# The draft's counts the screens show: the steps' sentences, and the check line's counts over the sentences on screen.
SHOWN_COUNTS = ("sentences", "shown")
# The tools behind the check line's "Not checked" clauses, which a rewrite's tools join.
TOOL_LISTS = ("tools", "cited_tools", "cited_only")


class CannotRewrite(Exception):
    """A kind's rewrite_row cannot rewrite the row: the row is gone, or the lesson has no version a row can be
    rewritten from. The update route answers 409 stale, so the page reloads the draft."""


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


def next_index(content: dict, choices: list[LessonChoice] | tuple[LessonChoice, ...] = ()) -> int:
    """The number a new sentence takes: one after every sentence the draft has had, on the page or in the removed box,
    in its saved notes and in every rewrite, so a citation marker names one sentence even after a removed row comes
    back (the draft page opens a source by its sentence's number)."""
    parts = [content, *(choice.rewrite for choice in choices if choice.rewrite)]
    numbers = [sentence["index"] for part in parts for note in part.get("notes") or ()
               for sentence in note.get("sentences") or ()]
    numbers += [item["index"] for part in parts for item in part.get("removed") or () if "index" in item]
    return 1 + max(numbers, default=-1)


def apply(content: dict, choices: list[LessonChoice]) -> dict:
    """The draft as its author's choices leave it. The saved content is not changed; a copy is. It carries next_index,
    counted before any removed row's notes leave it."""
    if not choices:
        return content
    shown = copy.deepcopy(content)
    shown["next_index"] = next_index(content, choices)
    original = {note["key"]: note for note in content.get("notes") or []}
    rows = {row["row_key"]: row for row in (shown.get("ppsd") or {}).get("rows") or []}
    updates: dict[tuple[str, str], list[LessonChoice]] = {}
    kept: dict[tuple[str, str], LessonChoice] = {}
    removed: dict[str, LessonChoice | None] = {}
    for choice in sorted(choices, key=lambda one: (one.choice_no, one.chosen_at)):
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
    checks, removed_box = shown.get("checks"), list(shown.get("removed") or [])
    language = content.get("lang") or "en"
    for (row_key, lesson_id), done in updates.items():
        if not done:
            continue
        latest = done[-1]
        replaced = [note["key"] for note in latest.rewrite.get("notes") or [] if note["key"] in notes]
        for key in replaced:  # the earlier text's counts and removed sentences give way to the rewrite's
            gone_too = sum(1 for item in removed_box if item.get("key") == key)
            checks = _counted(checks, kept_counts(original[key].get("sentences") or (), gone_too,
                                                  (checks or {}).get("checks_run") or (), content.get("evidence"),
                                                  language), -1)
        removed_box = [item for item in removed_box if item.get("key") not in replaced] + list(
            latest.rewrite.get("removed") or [])
        checks = _counted(checks, latest.rewrite.get("checks"), 1)
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
    for key in sorted(gone & set(notes)):  # a removed row's sentences leave the counts; its removed ones stay shown
        checks = _counted(checks, kept_counts(notes[key].get("sentences") or (), 0,
                                              (checks or {}).get("checks_run") or (), shown.get("evidence"), language), -1)
    shown["notes"] = [note for note in shown["notes"] if note["key"] not in gone]
    shown["checks"], shown["removed"] = checks, removed_box
    for row_key, choice in removed.items():
        if row_key in rows:
            rows[row_key]["removed"] = True
            rows[row_key]["removed_at"] = choice.as_dict()["at"]
    shown["lesson_removed"] = [choice.as_dict() for choice in removed.values()]
    return shown


def _added(total: Mapping, part: Mapping, sign: int) -> dict:
    out = dict(total)
    for key, value in part.items():
        if isinstance(value, Mapping):
            out[key] = _added(total.get(key) or {}, value, sign)
        elif isinstance(value, int) and not isinstance(value, bool):
            out[key] = (total.get(key) or 0) + sign * value
    return out


def _counted(checks: dict | None, part: Mapping | None, sign: int) -> dict | None:
    """The draft's counts with a part of its sentences' counts added (sign 1) or taken away (-1): only the counts the
    screens show, and only those the draft has (a draft saved before ticket 24 has no shown counts). A rewrite's tools
    join the ones behind the "Not checked" clauses."""
    if not checks or not part:
        return checks
    out = dict(checks)
    for key in SHOWN_COUNTS:
        if key in checks and key in part:
            out[key] = _added(checks[key], part[key], sign)
    if "shown" in out and not out["shown"].get("cross_language"):  # sent only when some are (ticket 42)
        out["shown"] = {key: value for key, value in out["shown"].items() if key != "cross_language"}
    if sign > 0:
        for key in TOOL_LISTS:
            if key in checks and part.get(key):
                out[key] = sorted(set(checks[key]) | set(part[key]))
    return out


def from_row(row: dict, moment) -> LessonChoice:
    """One stored choice, from either engine, which both give typed values (ticket 128)."""
    rewrite = row["rewrite"]
    return LessonChoice(row["choice_no"], row["row_key"], row["lesson_id"], row["action"], row["cited_version"],
                        row["current_version"], row["reason"] or None,
                        json.loads(rewrite) if rewrite else None, row["draft_state"], row["actor_name"],
                        moment(row["chosen_at"]))
