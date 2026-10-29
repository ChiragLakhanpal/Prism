"""Version notices: which drafts cite a lesson at a version a lead has since changed or retired (ticket 43; the
39 brief, sections 4.1 and 9).

A draft cites a lesson at a version, as the evidence id strata.ops.lesson_versions:lesson-3f2a9c1d0b/v1, so
nothing in a draft changes without its author (GLOSSARY.md, "Lesson version"). Every version a lead decides
after the cited one has a tier, from the decision that made it, and the strongest tier wins:

- strengthened      a quote was added as evidence; the statement and tags are unchanged (change_kind merged).
                    It goes to the digest only and never marks a draft.
- narrowed          the wording or the tags changed (wording, tags). The screen says "Changed".
- retired_outdated  retired because it no longer applies.
- retired_wrong     retired because it was wrong. It also holds the draft's export until its author chooses.

tier() is the one place that decides it, for the nightly job here and for the Lessons page's server (ticket 39).
mark() is the nightly job's refresh_drafts task: it reads every draft that is not discarded, finds each row that
cites a lesson at an older version, and adds a row to strata.ops.lesson_version_notices for each change it has
not marked yet. It never writes to a draft or its states.

Ticket 39 adds what the screens read, from the same tier and the same citations: row_notices() gives each open
notice on a draft as its author's choices leave it (strata.drafts.lesson_choices), with was and now (describe()),
and strengthened() the lessons a draft cites that only gained a quote, for the digest's quiet line. The draft page,
the Lessons tab and ticket 41's Home all read these, never a second computation.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable, Iterable, Iterator
from functools import cache
from importlib import resources

from strata.lakehouse.engine import Engine

VERSIONS = "strata.ops.lesson_versions"  # the table a lesson citation names, as get_lessons writes it
CITATION = re.compile(r"^strata\.ops\.lesson_versions:(?P<lesson_id>[^/\s]+)/v(?P<version>\d+)$")
TIERS = ("strengthened", "narrowed", "retired_outdated", "retired_wrong")  # weakest first
MARKS_A_DRAFT = frozenset({"narrowed", "retired_outdated", "retired_wrong"})
HOLDS_EXPORT = frozenset({"retired_wrong"})
NOTICE_COLUMNS = ("draft_id", "row_key", "lesson_id", "cited_version", "current_version", "tier", "holds_export",
                  "decided_on", "run_id", "noticed_at", "public_from")


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.knowledge.lessons") / "sql" / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def _date(value) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def version_tier(version: dict) -> str | None:
    """The tier of one lesson version, from the lead's decision that made it; None for version 1."""
    if version["state"] in ("retired_wrong", "retired_outdated"):
        return version["state"]
    return {"merged": "strengthened", "wording": "narrowed", "tags": "narrowed"}.get(version["change_kind"])


def retired(versions: dict[str, list[dict]], lesson_id: str, version: int) -> bool:
    """Whether a lesson's version retired it, as wrong or as out of date: an author who keeps a row against it keeps
    the row, since the lesson has no version left to keep."""
    return any(_version(row) == version and row["state"] in ("retired_wrong", "retired_outdated")
               for row in versions.get(lesson_id, []))


def tier(since: Iterable[dict]) -> str | None:
    """The strongest tier among the versions decided after the cited one, or None when there are none."""
    found = [t for t in (version_tier(v) for v in since) if t is not None]
    return max(found, key=TIERS.index) if found else None


def citations(content: dict) -> Iterator[tuple[str, str, int]]:
    """Each (row key, lesson id, version) a draft's rows cite, once each, in the draft's order. A row is a note,
    except in a draft of suggested PPSD rows (ticket 36), whose notes are the cells of a PPSD row: a cell's
    citation belongs to its row, where the draft page shows the notice (the 39 brief, section 2.4)."""
    seen = set()
    row_of = {note_key: row["row_key"] for row in (content.get("ppsd") or {}).get("rows") or []
              for note_key in (row.get("cells") or {}).values()}

    def walk(value) -> Iterator[str]:
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from walk(item)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)

    for note in content.get("notes") or []:
        for text in walk(note):
            found = CITATION.match(text)
            row_key = row_of.get(note.get("key"), str(note.get("key")))
            key = (row_key, found["lesson_id"], int(found["version"])) if found else None
            if key and key not in seen:
                seen.add(key)
                yield key


def mark(engine: Engine, run_id: str, clock: Callable[[], dt.datetime]) -> int:
    """Add a version notice for each open draft row that cites a lesson at a version since changed or retired,
    unless that change is already marked. Returns how many it added."""
    versions: dict[str, list[dict]] = {}
    for row in _rows(engine, "notice_versions"):
        versions.setdefault(row["lesson_id"], []).append(row)
    held = {(r["draft_id"], r["row_key"], r["lesson_id"], int(r["cited_version"]), int(r["current_version"]))
            for r in _rows(engine, "notices_held")}
    when = clock()
    new = []
    for draft in _rows(engine, "notice_drafts", citation=f"%{VERSIONS}:%"):
        for row_key, lesson_id, cited in citations(json.loads(draft["content"])):
            history = sorted(versions.get(lesson_id, []), key=lambda v: int(v["version"]))
            later = [v for v in history if int(v["version"]) > cited]
            found = tier(later)
            if found not in MARKS_A_DRAFT:
                continue
            current = later[-1]
            key = (draft["draft_id"], row_key, lesson_id, cited, int(current["version"]))
            if key in held:
                continue
            held.add(key)
            new.append((*key, found, found in HOLDS_EXPORT, _date(current["decided_on"]), run_id, when, when.date()))
    return engine.insert_rows("strata.ops.lesson_version_notices", NOTICE_COLUMNS, new) if new else 0


# ── What the screens read (ticket 39) ────────────────────────────────────

FIELDS = ("statement", "risk_factors", "stage", "kind", "categories", "methods")  # what a version may change
WORD = re.compile(r"\S+")


def history(engine: Engine) -> dict[str, list[dict]]:
    """Every version of every lesson, oldest first, with the categories and methods each names, by lesson id. It
    reads strata.knowledge.lessons.review's own query, so the review pages and the notices see the same rows."""
    from strata.knowledge.lessons import review

    found: dict[str, list[dict]] = {}
    for row in review._rows(engine, "lesson_versions"):
        found.setdefault(row["lesson_id"], []).append(row)
    return found


def _version(row: dict) -> int:
    return row["version"]


def changed_ranges(was: str, now: str) -> tuple[list[list[int]], list[list[int]]]:
    """The character ranges of the words that changed, in was (removed words) and in now (added words). Neighbouring
    changed words make one run, so the page marks each run once."""
    import difflib

    def words(text: str) -> list[re.Match]:
        return list(WORD.finditer(text or ""))

    before, after = words(was), words(now)
    matcher = difflib.SequenceMatcher(a=[m.group() for m in before], b=[m.group() for m in after], autojunk=False)
    was_ranges, now_ranges = [], []
    for op, a1, a2, b1, b2 in matcher.get_opcodes():
        if op in ("replace", "delete") and a2 > a1:
            was_ranges.append([before[a1].start(), before[a2 - 1].end()])
        if op in ("replace", "insert") and b2 > b1:
            now_ranges.append([after[b1].start(), after[b2 - 1].end()])
    return was_ranges, now_ranges


def labels(field: str, row: dict) -> str:
    """A version's value for one field, as the screen names it: the statement, or the labels of its tags joined by
    commas, from the closed lists (config/lessons.toml; config/package_form.toml for categories and methods)."""
    from strata.config import load_lesson_lists
    from strata.knowledge.lessons import tags

    value = row.get(field)
    if field == "statement":
        return value or ""
    lists = load_lesson_lists()
    if field == "stage":
        found = lists.stage(value)
        return found.label if found else ""
    if field == "kind":
        found = lists.kind(value)
        return found.label if found else ""
    keys = json.loads(value) if isinstance(value, str) and value else (value or [])
    if field == "risk_factors":
        return ", ".join(item.label for key in keys if (item := lists.risk_factor(key)))
    return ", ".join(tags.label(field, key) for key in keys)


def describe(versions: list[dict], a: int, b: int) -> dict:
    """Version a of a lesson against version b: each field that changed, with its was and now and the changed
    words in each; the decision that made b, with the lead's reason; and the versions that came between."""
    by_number = {_version(row): row for row in versions}
    first, last = by_number[a], by_number[b]
    retired = last["state"] in ("retired_wrong", "retired_outdated")
    changes = []
    if not retired:
        for field in FIELDS:
            was, now = labels(field, first), labels(field, last)
            if was != now:
                was_ranges, now_ranges = changed_ranges(was, now)
                changes.append({"field": field, "was": was, "now": now, "was_ranges": was_ranges,
                                "now_ranges": now_ranges})
    return {"a": a, "b": b, "statement_a": first["statement"], "statement_b": last["statement"],
            "changes": changes, "decided_on": _date(last["decided_on"]).isoformat(),
            "retired_on": _date(last["decided_on"]).isoformat() if retired else None,
            "retired_as": last["state"] if retired else None, "reason": last["reason"],
            "between": [{"version": _version(row), "decided_on": _date(row["decided_on"]).isoformat()}
                        for row in versions if a < _version(row) < b],
            # An example version the seed command set up for one viewer (ticket 41): no lead decided it.
            **({"example": True} if last.get("example") else {})}


def row_notices(content: dict, versions: dict[str, list[dict]]) -> list[dict]:
    """Each open notice on a draft, in the draft's order: a row that cites a lesson at a version a lead has since
    changed or retired, and that its author has not chosen for. A row the author kept at its version shows a notice
    again only for a change after the one they kept it against; a removed row and an updated row show none (the 39
    brief, sections 4.4 to 4.6). Each comes with was and now, its tier and whether it holds export."""
    kept = {(entry["row_key"], entry["lesson_id"], entry["cited_version"]): entry
            for entry in content.get("lesson_kept") or []}
    found = []
    for row_key, lesson_id, cited in citations(content):
        rows = sorted(versions.get(lesson_id, []), key=_version)
        if not rows:
            continue
        keep = kept.get((row_key, lesson_id, cited))
        since = keep["current_version"] if keep else cited
        level = tier([row for row in rows if _version(row) > since])
        if level not in MARKS_A_DRAFT:
            continue
        latest = _version(rows[-1])
        found.append({"row_key": row_key, "lesson_id": lesson_id, "tier": level, "holds_export": level in HOLDS_EXPORT,
                      "anchor": f"notice-{row_key}", "kept": keep, **describe(rows, cited, latest)})
    return found


def strengthened(content: dict, versions: dict[str, list[dict]], since: Callable[[dict], bool]) -> list[dict]:
    """The lessons a draft's rows cite that only gained a quote since the version they cite, where since(version)
    says a gain counts (the digest's window): each with the cited and current versions and what the lesson rests on
    at each, as the merge's was and now record it ({quotes, reports})."""
    found = []
    for row_key, lesson_id, cited in citations(content):
        rows = sorted(versions.get(lesson_id, []), key=_version)
        later = [row for row in rows if _version(row) > cited]
        if not later or tier(later) != "strengthened" or not any(since(row) for row in later):
            continue
        merges = [row for row in later if row["change_kind"] == "merged"]
        was = json.loads(merges[0]["was"] or "{}") if merges else {}
        now = json.loads(merges[-1]["now"] or "{}") if merges else {}
        found.append({"row_key": row_key, "lesson_id": lesson_id, "a": cited, "b": _version(rows[-1]),
                      "statement": rows[-1]["statement"], "decided_on": _date(rows[-1]["decided_on"]).isoformat(),
                      "was": was, "now": now})
    return found
