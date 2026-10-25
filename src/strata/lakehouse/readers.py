"""The document readers in the nightly job: the parse_and_embed and sync_index tasks (ticket 43).

parse_and_embed runs the plan reader (strata.lakehouse.plans) for each project whose Procurement Plans it reads,
then re-syncs strata.gold.package, which reads the plan rows, and then the passage reader
(strata.lakehouse.passages) for the slice's projects. Both readers fetch only documents bronze does not hold, send
only pages they have not parsed to the layout parser, and embed and screen only passage texts the model and the
shield have not seen, so a night with no new document parses and embeds nothing. sync_index syncs
strata.gold.passage and, on the workspace, asks the AI Search index to sync from it.

Readers holds what the readers need, which is the one thing that differs between the workspace and this computer:

- recorded(): the fixture's recorded lists, texts, pages and layouts, the offline embedder and shield, the
  projects whose plans the fixture records, and no index.
- live(): the World Bank's hosts through PoliteFetch (a pause between requests, each answer kept in the bronze
  files volume, and a stop at the first refusal), ai_parse_document, Prompt Shields and the embedding
  deployment with the keys the job reads from the secret scope, and the AI Search index.

When the document host refuses a request (HostRefused), the task stops reading, writes a data readiness note and
finishes, so the job goes on and the next night starts where this one stopped.
"""

from __future__ import annotations

import datetime as dt
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from strata.config import load_slice, load_sources
from strata.lakehouse import gold, passages, plans
from strata.lakehouse.engine import Engine
from strata.reader.documents import Documents, HostRefused

SOURCE = "documents"
NOTE_COLUMNS = ("run_id", "source", "subject", "measure", "kind", "count", "denominator", "as_of", "detail",
                "measured_at", "public_from")
# Counted before and after the readers run: what they added is what the task changed, with the gold syncs.
ADDED_TO = ("strata.bronze.document_lists", "strata.bronze.document_texts", "strata.bronze.layout_pages",
            "strata.silver.passage_shields", "strata.silver.passage_embeddings")


@dataclass(frozen=True)
class Readers:
    documents: Documents
    layout: object | None  # a LayoutParser; None leaves Route B's pages for a run that has one
    shield: object | None  # a Shield; with no shield or no embedder, the passage reader waits for a run that has both
    embedder: object | None
    plan_projects: Callable[[Engine], list[str]]
    report_projects: Callable[[Engine], list[str]]
    index: Callable[[Engine], None] | None = None  # asks the search index to sync from strata.gold.passage


def fixture_plan_projects() -> tuple[str, ...]:
    """The projects whose Procurement Plans the fixture records: the demo plan's, then the stress shelf's plan's
    (config/slice.toml). The fixture build reads the same ones."""
    chosen = load_slice()
    return tuple(dict.fromkeys([chosen.demo_plan.project_id, *(item.project_id for item in chosen.stress_shelf
                                                             if item.kind == "large_plan" and item.project_id)]))


def recorded(manifest=None, documents: Documents | None = None) -> Readers:
    """The readers over the recorded fixture. documents may wrap the recorded source, as a test that holds some
    documents back for a later night does."""
    from strata.fixture import recorded as fmt
    from strata.knowledge.embed import offline
    from strata.knowledge.shields import PatternShield
    from strata.reader.documents import RecordedDocuments
    from strata.reader.layout import RecordedLayout

    manifest = manifest or fmt.load_manifest()
    documents = documents or RecordedDocuments(manifest)
    return Readers(documents, RecordedLayout(manifest), PatternShield(), offline(),
                   plan_projects=lambda engine: list(fixture_plan_projects()),
                   report_projects=lambda engine: passages.listed_projects(documents,
                                                                           passages.default_projects(engine)))


SCOPE_KEYS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AI_SEARCH_ENDPOINT")
CACHE = "/Volumes/strata/bronze/files/fetched"  # the bundle's bronze files volume, a folder on serverless compute


def live(engine: Engine, environ: Mapping[str, str] | None = None) -> Readers:
    """The readers on the workspace, as the job runs them on serverless compute. Without Azure OpenAI's keys the
    plan reader still runs, and the passage reader waits for a night that has them."""
    from strata.config import load_layout_parser, load_models
    from strata.fixture.record import fetch_url
    from strata.knowledge.embed import AzureOpenAIEmbeddings
    from strata.knowledge.shields import PromptShields, content_safety_endpoint
    from strata.reader.documents import LiveDocuments, PoliteFetch
    from strata.reader.layout import PARSERS

    env = os.environ if environ is None else environ
    fetch = PoliteFetch(fetch_url, load_sources()[SOURCE].pause_seconds or 0.0,
                        CACHE if os.path.isdir(os.path.dirname(CACHE)) else None)
    layout = PARSERS[load_layout_parser()](engine, upload=_write_to_volume, fetch=fetch)
    endpoint, key = env.get("AZURE_OPENAI_ENDPOINT", "").strip(), env.get("AZURE_OPENAI_API_KEY", "").strip()
    shield = embedder = None
    if endpoint and key:
        model = load_models()["embed"]
        shield = PromptShields(content_safety_endpoint(endpoint), key)
        embedder = AzureOpenAIEmbeddings(endpoint, key, model.deployment, model.dimensions)
    search = env.get("AI_SEARCH_ENDPOINT", "").strip()
    return Readers(LiveDocuments(fetch), layout, shield, embedder,
                   plan_projects=passages.default_projects, report_projects=passages.default_projects,
                   index=_index(search) if search else None)


def _write_to_volume(path: str, data: bytes) -> None:
    """Serverless compute reads and writes a Unity Catalog volume as a folder."""
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(data)


def _index(endpoint: str) -> Callable[[Engine], None]:
    def sync(engine: Engine) -> None:
        from databricks.sdk import WorkspaceClient  # on the workspace's serverless compute, signed in as the job

        from strata.config import load_models
        from strata.knowledge.search import AiSearchIndex

        client = WorkspaceClient()

        def transport(method: str, path: str, body: dict | None = None) -> dict:
            try:
                return client.api_client.do(method, path, body=body) or {}
            except Exception as error:  # the SDK's NotFound, read as a missing index
                if "does not exist" in str(error).lower() or "not found" in str(error).lower():
                    raise LookupError(str(error)) from error
                raise

        index = AiSearchIndex(transport, endpoint, load_models()["embed"].dimensions)
        index.ensure(lambda sql: engine.run(sql))
        index.sync()

    return sync


def _count(engine: Engine, table: str) -> int:
    return int(engine.run(f"SELECT count(*) AS n FROM {table}").rows[0][0])  # sql-lint: names only, from ADDED_TO


def read(engine: Engine, readers: Readers, run_id: str, clock: Callable[[], dt.datetime]) -> int:
    """The parse_and_embed task: both readers, over only what changed. Returns the rows they added or changed."""
    before = {table: _count(engine, table) for table in ADDED_TO}
    synced = 0
    try:
        for project_id in readers.plan_projects(engine):
            plans.run(engine, readers.documents, readers.layout, project_id, clock=clock, run_id=run_id)
        synced += gold.sync(engine, "package")  # its query reads the plan rows the plan reader just wrote
        if readers.shield is not None and readers.embedder is not None:
            report = passages.run(engine, readers.documents, readers.report_projects(engine), shield=readers.shield,
                                  embedder=readers.embedder, layout=readers.layout, clock=clock, run_id=run_id)
            synced += report.synced
    except HostRefused as refused:
        note_refusal(engine, run_id, clock(), refused)
    return synced + sum(_count(engine, table) - count for table, count in before.items())


def note_refusal(engine: Engine, run_id: str, when: dt.datetime, refused: HostRefused) -> None:
    """A data readiness note that the document host refused a request, so the readers stopped for the night."""
    engine.insert_rows("strata.ops.data_readiness", NOTE_COLUMNS, [(
        run_id, SOURCE, "all", "document_host_refused", "fresh", None, None, when.date(),
        f"The document host answered HTTP {refused.status} on {when:%B} {when.day}, {when.year}, so the readers "
        "stopped for the night. The documents and pages read before it are kept, and the next night goes on "
        "from there.", when, when.date())])


def sync_index(engine: Engine, readers: Readers | None) -> int:
    """The sync_index task: strata.gold.passage made equal to the passages, then, on the workspace, the AI Search
    index asked to sync from it. Returns the gold rows it added, changed or removed."""
    changed = gold.sync(engine, "passage")
    if readers is not None and readers.index is not None:
        readers.index(engine)
    return changed
