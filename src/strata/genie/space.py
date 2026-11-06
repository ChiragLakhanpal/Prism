"""The Genie space, built from code (ticket 33; docs/PLAN.md section 12, "genie.py (the Genie space from code)").

config/genie.toml defines the space once: its title, description, one text instruction, the metric views and gold
tables it reads, sample questions and trusted SQL (src/strata/genie/trusted/). Its benchmark questions are the
questions in evals/benchmark.yaml that ask_genie answers, each answered by its ground-truth SQL.

serialized() writes the space in Genie's serialized form. Written from ticket 33's description of fairshare's
genie.py, because fairshare could not be read on the build machine, with two changes the notes ask for:

- Every id comes from uuid5 and a stable key, such as the trusted question's words, never uuid4, so a deploy that
  changes nothing changes no id.
- Every list is sorted by its id or identifier, and there is exactly one text instruction.

deploy() makes the workspace's space match: it finds Prism's space by the id it was given or by its title,
compares what Genie holds (get_space with include_serialized_space) with what the repo says, and creates,
updates or leaves it. It never changes a space whose title is not Prism's, because the workspace is shared with
fairshare, and the throwaway space the setup wizard made for day-one test 5 is one of those. The field names of
the serialized form follow Genie's API as its documentation gives them; they have not been sent from this repo
yet, which the workspace step in docs/workspace-catchup.md does.
"""

from __future__ import annotations

import dataclasses
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from strata.config import GenieConfig, load_genie
from strata.lakehouse import ground_truth
from strata.lakehouse.engine import EngineError, Transport

ROOT = Path(__file__).resolve().parents[3]
TRUSTED = Path(__file__).resolve().parent / "trusted"
# The namespace of every id in Prism's space: uuid5 of this and an item's key gives the same id each time.
NAMESPACE = uuid.UUID("5d1f3c1e-2b7a-4c8e-9a64-7f0e5b3d2c10")
GENIE = "/api/2.0/genie/spaces"
PARAMETER = re.compile(r"(?<![:\w]):([a-z_][a-z0-9_]*)")


@dataclass(frozen=True)
class Trusted:
    question: str
    sql: str


@dataclass(frozen=True)
class Benchmark:
    """One of the space's benchmark questions: its id in evals/benchmark.yaml, the words Genie is asked and the
    ground-truth SQL that answers it."""

    id: str
    question: str
    case: ground_truth.Case


@dataclass(frozen=True)
class Space:
    title: str
    description: str
    instruction: str
    metric_views: tuple[str, ...]
    tables: tuple[str, ...]
    sample_questions: tuple[str, ...]
    trusted: tuple[Trusted, ...]
    benchmarks: tuple[Benchmark, ...]


def replace(space: Space, **changes) -> Space:
    return dataclasses.replace(space, **changes)


def benchmarks(questions: list[dict] | None = None, root: Path = ROOT) -> tuple[Benchmark, ...]:
    """The benchmark file's questions that ask_genie answers, with their ground-truth SQL."""
    if questions is None:
        from strata.evals import benchmark

        questions = benchmark.load()
    return tuple(Benchmark(question["id"], question["arguments"]["question"],
                           ground_truth.read(root / question["ground_truth"]))
                 for question in questions if question.get("tool") == "ask_genie")


def load(config: GenieConfig | None = None, questions: list[dict] | None = None, root: Path = ROOT) -> Space:
    config = config or load_genie()
    trusted = tuple(Trusted(entry.question, sql_only((TRUSTED / entry.sql).read_text())) for entry in config.trusted)
    return Space(config.title, config.description, config.instruction, config.metric_views, config.tables,
                 config.sample_questions, trusted, benchmarks(questions, root))


def sql_only(text: str) -> str:
    """A SQL file without its comment lines."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--")).strip()


def written_in(case: ground_truth.Case) -> str:
    """A ground-truth query with each bound parameter written in as a quoted literal, for Genie's benchmark,
    which takes SQL with no parameters. The values are the file's own, never a viewer's."""
    def literal(match: re.Match) -> str:
        name = match.group(1)
        return "'" + case.params[name].replace("'", "''") + "'" if name in case.params else match.group(0)

    return PARAMETER.sub(literal, sql_only(case.sql))


def item_id(kind: str, key: str) -> str:
    """The id of one item of the space: the same kind and key give the same id every time."""
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}").hex


def reads(space: Space) -> tuple[str, ...]:
    return tuple(sorted({*space.metric_views, *space.tables}))


def serialized(space: Space) -> dict:
    """The space in Genie's serialized form, every list sorted by id or identifier."""
    def by_id(items: list[dict]) -> list[dict]:
        return sorted(items, key=lambda item: item["id"])

    return {
        "version": 1,
        "config": {"sample_questions": by_id([{"id": item_id("sample_question", question), "question": [question]}
                                              for question in space.sample_questions])},
        "data_sources": {"tables": [{"identifier": name} for name in reads(space)]},
        "instructions": {
            "text_instructions": [{"id": item_id("text_instruction", "space"), "content": [space.instruction]}],
            "example_question_sqls": by_id([{"id": item_id("trusted", trusted.question),
                                             "question": [trusted.question], "sql": [trusted.sql]}
                                            for trusted in space.trusted]),
        },
        "benchmarks": {"questions": by_id([{"id": item_id("benchmark", item.id), "question": [item.question],
                                            "answer": [{"format": "SQL", "content": [written_in(item.case)]}]}
                                           for item in space.benchmarks])},
    }


def request(space: Space, warehouse_id: str) -> dict:
    """The body that creates or updates the space."""
    return {"title": space.title, "description": space.description, "warehouse_id": warehouse_id,
            "serialized_space": json.dumps(serialized(space), sort_keys=True)}


# ── Comparing with what Genie holds ──────────────────────────────────────

PARTS = {("title",): "the title", ("description",): "the description", ("warehouse_id",): "the warehouse",
         ("config",): "the sample questions", ("data_sources",): "the metric views and tables",
         ("instructions", "text_instructions"): "the text instruction",
         ("instructions", "example_question_sqls"): "the trusted SQL", ("benchmarks",): "the benchmark questions",
         ("version",): "the serialized form's version"}


def _holds(theirs: Any, ours: Any) -> bool:
    """Whether what Genie holds has everything the repo sends, ignoring fields Genie adds."""
    if isinstance(ours, dict):
        return isinstance(theirs, dict) and all(key in theirs and _holds(theirs[key], value)
                                                for key, value in ours.items())
    if isinstance(ours, list):
        return isinstance(theirs, list) and len(theirs) == len(ours) and all(
            _holds(found, value) for found, value in zip(theirs, ours, strict=True))
    return theirs == ours


def changes(body: dict, found: dict) -> list[str]:
    """What differs between the body the repo sends and the space Genie holds, in words."""
    ours = {**body, **json.loads(body["serialized_space"])}
    try:
        held = json.loads(found.get("serialized_space") or "{}")
    except ValueError:
        held = {}
    theirs = {**found, **held}
    differ = []
    for path, words in PARTS.items():
        mine, other = ours, theirs
        for key in path:
            mine = mine.get(key) if isinstance(mine, dict) else None
            other = other.get(key) if isinstance(other, dict) else None
        if not _holds(other, mine):
            differ.append(words)
    return differ


# ── The deploy ───────────────────────────────────────────────────────────

class Spaces(Protocol):
    def list_spaces(self) -> list[dict]: ...
    def get_space(self, space_id: str) -> dict: ...
    def create_space(self, body: dict) -> dict: ...
    def update_space(self, space_id: str, body: dict) -> dict: ...


class RestSpaces:
    """Genie's space API on the workspace, through a transport with one person's token."""

    def __init__(self, transport: Transport):
        self.transport = transport

    def list_spaces(self) -> list[dict]:
        found, token = [], None
        while True:
            page = self.transport("GET", GENIE + (f"?page_token={token}" if token else ""), None)
            found += page.get("spaces") or []
            token = page.get("next_page_token")
            if not token:
                return found

    def get_space(self, space_id: str) -> dict:
        """The space with its serialized form. LookupError when Genie holds no such space, such as one deleted
        since the env file named it."""
        try:
            return self.transport("GET", f"{GENIE}/{space_id}?include_serialized_space=true", None)
        except EngineError as error:
            if " 404 " in str(error):
                raise LookupError(space_id) from error
            raise

    def create_space(self, body: dict) -> dict:
        return self.transport("POST", GENIE, body)

    def update_space(self, space_id: str, body: dict) -> dict:
        return self.transport("PATCH", f"{GENIE}/{space_id}", body)


@dataclass
class Deployed:
    space_id: str
    action: str  # created, updated or unchanged
    changes: list[str] = dataclasses.field(default_factory=list)
    notes: list[str] = dataclasses.field(default_factory=list)


def _found(api: Spaces, space_id: str) -> dict | None:
    try:
        return api.get_space(space_id)
    except LookupError:
        return None


def deploy(api: Spaces, space: Space, warehouse_id: str, known_id: str | None) -> Deployed:
    """Make the workspace's Prism space match the repo. known_id is the env file's GENIE_SPACE_ID, if any."""
    body, notes, current = request(space, warehouse_id), [], None
    if known_id:
        found = _found(api, known_id)
        if found is not None and found.get("title") == space.title:
            current = found
        elif found is not None:
            notes.append(f"The space {known_id} is titled {found.get('title')}, which is not Prism's, so I left it "
                         "as it was.")
    if current is None:
        named = [item for item in api.list_spaces() if item.get("title") == space.title]
        if len(named) > 1:
            raise ValueError(f"{len(named)} spaces are titled {space.title}: "
                             f"{', '.join(item['space_id'] for item in named)}. Keep one, then deploy again.")
        if named:
            current = _found(api, named[0]["space_id"])
    if current is None:
        created = api.create_space(body)
        return Deployed(created["space_id"], "created", [], notes)
    differ = changes(body, current)
    if not differ:
        return Deployed(current["space_id"], "unchanged", [], notes)
    api.update_space(current["space_id"], body)
    return Deployed(current["space_id"], "updated", differ, notes)


def append_env(path: Path, key: str, value: str) -> None:
    """Add KEY='value' as the env file's last line, leaving every other line as it was. The live commands read a
    later line over an earlier one, so the new value wins (ops/dayone/dayone.py, load_env)."""
    text = Path(path).read_text() if Path(path).exists() else ""
    escaped = value.replace("'", "'\\''")
    with open(path, "a") as handle:
        handle.write(("" if not text or text.endswith("\n") else "\n") + f"{key}='{escaped}'\n")
