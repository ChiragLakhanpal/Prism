"""Where drafts are kept: strata.ops, written as the app's own service principal (ticket 35).

Adapted from fairshare's server/drafts.py, which kept drafts in memory for two hours with two states,
"draft" and fairshare's second state, which Strata leaves behind. Strata keeps them in four tables
(src/strata/lakehouse/tables/ops/): the draft with its author's team, every state it has been in, each
export with the evidence pack's snapshot, and the files each export made. Nothing is updated or deleted: a change of state is a new row, merged on
the draft and its step, so it is written only while the state the person saw is still the latest, and
two acts at the same moment cannot both write the next step (CLAUDE.md rule 5).

Ticket 36 adds two more: each value a person set on a field only people fill (a suggested PPSD row's risk owner and
ratings, and the form the draft uses), and each report a draft's author kept on a disagreement card. Each save is a
new row; views in src/strata/lakehouse/views/ops/ give the latest value of each, so nothing is overwritten.

Ticket 39 adds the choices an author makes for rows that cite a changed lesson (strata.ops.draft_lesson_choices).
A Saved draft's content is the draft as those choices leave it (strata.drafts.lesson_choices.apply), so its page,
its counts, its holds and its files all read the same rows.

The store holds no access rule. The draft routes (src/strata/server/drafts.py) ask the one access rule
(src/strata/server/access.py) before they show or change anything. Values arrive typed from DuckDB and
as text from the SQL warehouse, so each is read once here.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

from strata.drafts.lesson_choices import COLUMNS as CHOICE_COLUMNS
from strata.drafts.lesson_choices import LessonChoice, apply, from_row
from strata.lakehouse.engine import Engine, EngineError

STATES = ("draft", "checked", "exported", "discarded")
DRAFT_COLUMNS = ("draft_id", "kind", "team_key", "author_id", "author_name", "idempotency_key", "project_id",
                 "subject", "content", "created_at", "public_from")
STATE_COLUMNS = ("draft_id", "step", "state", "from_state", "actor_id", "actor_name", "changed_at", "public_from")
EXPORT_COLUMNS = ("draft_id", "export_id", "exported_at", "actor_id", "actor_name", "footnotes", "sources", "opened",
                  "snapshot", "public_from")
FILE_COLUMNS = ("draft_id", "export_id", "name", "media_type", "size_bytes", "content", "public_from")
FIELD_COLUMNS = ("draft_id", "save_no", "row_key", "field", "value", "set_by_id", "set_by_name", "set_at", "public_from")


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.drafts") / "sql" / f"{name}.sql").read_text()


def moment(value) -> dt.datetime | None:
    """A timestamp from either engine, in UTC: DuckDB gives a naive UTC datetime, the warehouse text."""
    if value is None or value == "":
        return None
    if not isinstance(value, dt.datetime):
        value = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00").replace(" ", "T"))
    return value if value.tzinfo else value.replace(tzinfo=dt.UTC)


def iso(value: dt.datetime | None) -> str | None:
    return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z") if value else None


@dataclass(frozen=True)
class State:
    step: int
    state: str
    from_state: str | None
    actor_id: str
    actor_name: str | None
    changed_at: dt.datetime


@dataclass(frozen=True)
class Export:
    export_id: str
    exported_at: dt.datetime
    actor_id: str
    actor_name: str | None
    footnotes: int
    sources: int
    opened: int
    snapshot: dict
    files: tuple[dict, ...] = ()


@dataclass(frozen=True)
class FieldValue:
    """The latest value a person set on one field of a draft (ticket 36); None when they removed it."""

    value: str | None
    set_by_id: str
    set_by_name: str | None
    set_at: dt.datetime


@dataclass(frozen=True)
class Choice:
    """The report a draft's author kept on one disagreement card (ticket 36): lean or other, with the reason keeping
    the other needs. Ticket 23's card records it in strata.ops.disagreement_choices with the draft's id."""

    kept: str
    reason: str | None
    set_by_name: str | None
    set_at: dt.datetime


@dataclass(frozen=True)
class Saved:
    """A draft as it is kept: its row, its history, newest last, its latest export, the latest value of each field
    a person set (by row key and field; the form is ("", "form")) and the latest choice on each disagreement."""

    draft_id: str
    kind: str
    team_key: str
    author_id: str
    author_name: str | None
    project_id: str | None
    subject: str | None
    content: dict
    created_at: dt.datetime
    states: tuple[State, ...] = ()
    export: Export | None = None
    fields: dict = field(default_factory=dict)
    choices: dict = field(default_factory=dict)
    # Ticket 39: the choices its author made for rows that cite a changed lesson, oldest first. content already shows
    # the draft as they leave it.
    lesson_choices: tuple[LessonChoice, ...] = ()

    @property
    def state(self) -> State:
        return self.states[-1]

    def last(self, state: str) -> State | None:
        """The latest act that put the draft in this state, if it has been in it. A restore returns a draft
        to the state it was discarded from, so it is not the act: after a restore, "Checked by" keeps the
        time of the check."""
        return next((step for step in reversed(self.states) if step.state == state and step.from_state != "discarded"),
                    None)


@dataclass
class NewDraft:
    draft_id: str
    kind: str
    team_key: str
    author_id: str
    author_name: str | None
    idempotency_key: str | None
    project_id: str | None
    subject: str | None
    content: dict
    created_at: dt.datetime


@dataclass
class NewExport:
    export_id: str
    exported_at: dt.datetime
    actor_id: str
    actor_name: str | None
    footnotes: int
    sources: int
    opened: int
    snapshot: dict
    files: list[tuple[str, str, bytes]] = field(default_factory=list)  # (name, media type, bytes)


class Stale(Exception):
    """The draft's state is no longer the one the person saw. It carries the state it is in now."""

    def __init__(self, state: str):
        super().__init__(state)
        self.state = state


class DraftStore:
    """The drafts in strata.ops. engine() opens the engine that reads and writes them: the app's own."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    @contextmanager
    def _open(self) -> Iterator[Engine]:
        engine = self.engine()
        try:
            yield engine
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                close()

    @staticmethod
    def _rows(engine: Engine, query: str, **params) -> list[dict]:
        result = engine.run(_sql(query), params)
        return [dict(zip(result.columns, row)) for row in result.rows]

    def create(self, draft: NewDraft) -> None:
        """Save a new draft in the Draft state."""
        with self._open() as engine:
            engine.insert_rows("strata.ops.drafts", DRAFT_COLUMNS, [(
                draft.draft_id, draft.kind, draft.team_key, draft.author_id, draft.author_name, draft.idempotency_key,
                draft.project_id, draft.subject, json.dumps(draft.content, ensure_ascii=False), draft.created_at,
                draft.created_at.date())])
            engine.insert_rows("strata.ops.draft_states", STATE_COLUMNS, [(
                draft.draft_id, 1, "draft", None, draft.author_id, draft.author_name, draft.created_at,
                draft.created_at.date())])

    def by_key(self, author_id: str, idempotency_key: str) -> str | None:
        with self._open() as engine:
            found = self._rows(engine, "by_key", author_id=author_id, idempotency_key=idempotency_key)
        return found[0]["draft_id"] if found else None

    def _saved(self, engine: Engine, rows: list[dict]) -> list[Saved]:
        if not rows:
            return []
        ids = ",".join(row["draft_id"] for row in rows)
        states: dict[str, list[State]] = {}
        for row in self._rows(engine, "states", ids=ids):
            states.setdefault(row["draft_id"], []).append(State(
                int(row["step"]), row["state"], row["from_state"], row["actor_id"], row["actor_name"],
                moment(row["changed_at"])))
        exports: dict[str, Export] = {}
        for row in self._rows(engine, "exports", ids=ids):
            if row["draft_id"] in exports:
                continue  # newest first, so the first is the latest
            files = tuple({"name": item["name"], "media_type": item["media_type"], "size": int(item["size_bytes"])}
                          for item in self._rows(engine, "files", draft_id=row["draft_id"], export_id=row["export_id"]))
            exports[row["draft_id"]] = Export(
                row["export_id"], moment(row["exported_at"]), row["actor_id"], row["actor_name"], int(row["footnotes"]),
                int(row["sources"]), int(row["opened"]), json.loads(row["snapshot"]), files)
        fields: dict[str, dict] = {}
        for row in self._rows(engine, "fields", ids=ids):
            fields.setdefault(row["draft_id"], {})[(row["row_key"], row["field"])] = FieldValue(
                row["value"], row["set_by_id"], row["set_by_name"], moment(row["set_at"]))
        authors = {row["draft_id"]: (row["author_id"], row["author_name"]) for row in rows}
        choices: dict[str, dict] = {}
        for row in self._rows(engine, "choices", ids=ids):
            author_id, author_name = authors.get(row["draft_id"], (None, None))
            if row["viewer"] != author_id:
                continue  # only the draft's author chooses for it
            kept = "lean" if row["kept_assertion_id"] == row["leaned_assertion_id"] else "other"
            choices.setdefault(row["draft_id"], {})[row["disagreement_id"]] = Choice(
                kept, row["reason"] or None, author_name, moment(row["made_at"]))
        lessons: dict[str, list[LessonChoice]] = {}
        for row in self._rows(engine, "lesson_choices", ids=ids):
            lessons.setdefault(row["draft_id"], []).append(from_row(row, moment))
        return [Saved(row["draft_id"], row["kind"], row["team_key"], row["author_id"], row["author_name"],
                      row["project_id"], row["subject"],
                      apply(json.loads(row["content"]), lessons.get(row["draft_id"], [])), moment(row["created_at"]),
                      tuple(sorted(states.get(row["draft_id"], []), key=lambda step: step.step)),
                      exports.get(row["draft_id"]), fields.get(row["draft_id"], {}), choices.get(row["draft_id"], {}),
                      tuple(lessons.get(row["draft_id"], [])))
                for row in rows if states.get(row["draft_id"])]

    def get(self, draft_id: str) -> Saved | None:
        if "," in draft_id:
            return None
        with self._open() as engine:
            found = self._saved(engine, self._rows(engine, "draft", draft_id=draft_id))
        return found[0] if found else None

    def for_team(self, team_key: str, author_id: str) -> list[Saved]:
        """The drafts saved under a team, and every draft of this author whatever team it was saved under."""
        with self._open() as engine:
            return self._saved(engine, self._rows(engine, "team_drafts", team_key=team_key, author_id=author_id))

    def change(self, draft_id: str, expected: str, state: str, actor_id: str, actor_name: str | None,
               at: dt.datetime) -> None:
        """Move a draft from the state its author saw to the next one, or raise Stale with its state now."""
        with self._open() as engine:
            before = self._rows(engine, "states", ids=draft_id)
            if before[-1]["state"] != expected:
                raise Stale(before[-1]["state"])
            try:
                engine.run(_sql("change_state"), {"draft_id": draft_id, "expected": expected, "state": state,
                                                  "actor_id": actor_id, "actor_name": actor_name, "changed_at": at})
            except EngineError:
                # Delta refuses the second of two writers of the same step: if another act moved the
                # draft meanwhile, say so; any other failure is the data service's.
                now = self._rows(engine, "states", ids=draft_id)
                if len(now) != len(before):
                    raise Stale(now[-1]["state"]) from None
                raise
            after = self._rows(engine, "states", ids=draft_id)
        if len(after) != len(before) + 1 or after[-1]["state"] != state:
            raise Stale(after[-1]["state"])

    def save_export(self, draft_id: str, export: NewExport) -> None:
        """Keep an export's record and its files. Saved before the draft moves to Exported."""
        with self._open() as engine:
            engine.insert_rows("strata.ops.draft_exports", EXPORT_COLUMNS, [(
                draft_id, export.export_id, export.exported_at, export.actor_id, export.actor_name, export.footnotes,
                export.sources, export.opened, json.dumps(export.snapshot, ensure_ascii=False),
                export.exported_at.date())])
            engine.insert_rows("strata.ops.draft_files", FILE_COLUMNS, [(
                draft_id, export.export_id, name, media_type, len(content), base64.b64encode(content).decode("ascii"),
                export.exported_at.date()) for name, media_type, content in export.files])

    def set_field(self, draft_id: str, row_key: str, name: str, value: str | None, actor_id: str,
                  actor_name: str | None, at: dt.datetime) -> None:
        """Keep one value a person set on a draft's field, or its removal (value None), as a new row (ticket 36).
        Nothing is updated or deleted; the latest row is the field's value now."""
        with self._open() as engine:
            saves = int(self._rows(engine, "field_saves", draft_id=draft_id)[0]["saves"])
            engine.insert_rows("strata.ops.draft_fields", FIELD_COLUMNS, [(
                draft_id, saves + 1, row_key, name, value, actor_id, actor_name, at, at.date())])

    def choose(self, draft_id: str, row_key: str, lesson_id: str, action: str, cited_version: int,
               current_version: int, reason: str | None, rewrite: dict | None, draft_state: str, actor_id: str,
               actor_name: str | None, at: dt.datetime) -> None:
        """Keep one choice an author made for a row that cites a changed lesson, as a new row (ticket 39). Nothing is
        updated or deleted; the draft reads its choices in order."""
        with self._open() as engine:
            made = int(self._rows(engine, "lesson_choice_count", draft_id=draft_id)[0]["choices"])
            engine.insert_rows("strata.ops.draft_lesson_choices", CHOICE_COLUMNS, [(
                draft_id, made + 1, row_key, lesson_id, action, cited_version, current_version, reason,
                json.dumps(rewrite, ensure_ascii=False) if rewrite is not None else None, draft_state, actor_id,
                actor_name, at, at.date())])

    def field_history(self, draft_id: str) -> list[dict]:
        """Every save of a draft's fields, oldest first, for the evidence pack's "Fields you set" table."""
        with self._open() as engine:
            return [{**row, "set_at": moment(row["set_at"])} for row in self._rows(engine, "field_history",
                                                                                    draft_id=draft_id)]

    def file(self, draft_id: str, export_id: str, name: str) -> tuple[str, bytes] | None:
        with self._open() as engine:
            found = self._rows(engine, "file", draft_id=draft_id, export_id=export_id, name=name)
        return (found[0]["media_type"], base64.b64decode(found[0]["content"])) if found else None

    def opened_since(self, viewer_id: str, evidence_ids: list[str], since: dt.datetime) -> dict[str, dt.datetime]:
        """The sources among these that the viewer opened since a moment, with when they last did."""
        asked = [evidence for evidence in dict.fromkeys(evidence_ids) if evidence and "," not in evidence]
        if not asked or not viewer_id:
            return {}
        with self._open() as engine:
            found = self._rows(engine, "opened_since", viewer_id=viewer_id, ids=",".join(asked), since=since)
        return {row["evidence_id"]: moment(row["last_opened_at"]) for row in found}
