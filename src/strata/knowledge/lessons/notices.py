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


def tier(since: Iterable[dict]) -> str | None:
    """The strongest tier among the versions decided after the cited one, or None when there are none."""
    found = [t for t in (version_tier(v) for v in since) if t is not None]
    return max(found, key=TIERS.index) if found else None


def citations(content: dict) -> Iterator[tuple[str, str, int]]:
    """Each (row key, lesson id, version) a draft's rows cite, once each, in the draft's order."""
    seen = set()

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
            key = (str(note.get("key")), found["lesson_id"], int(found["version"])) if found else None
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
