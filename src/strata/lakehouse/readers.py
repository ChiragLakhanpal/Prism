"""The document readers in the nightly job: the parse_and_embed and sync_index tasks (ticket 43).

parse_and_embed runs the plan reader (strata.lakehouse.plans) for each project whose Procurement Plans it reads,
then re-syncs strata.gold.package, which reads the plan rows, and then the passage reader
(strata.lakehouse.passages) for the slice's projects. Both readers fetch only documents bronze does not hold, send
only pages they have not parsed to the layout parser, and embed and screen only passage texts the model and the
shield have not seen, so a night with no new document parses and embeds nothing. The plan reader reads only each
project's newest Procurement Plan and lists each older one once as superseded in strata.ops.skipped_documents, unless
config/thresholds.toml's ingestion.plan_versions says "all" (ticket 108). sync_index syncs strata.gold.passage and, on
the workspace, asks the AI Search index to sync from it.

Readers holds what the readers need, which is the one thing that differs between the workspace and this computer:

- recorded(): the fixture's recorded lists, texts, pages and layouts, the offline embedder and shield, the
  projects whose plans the fixture records, and no index.
- live(): the World Bank's hosts through PoliteFetch (a pause between requests, each answer kept in the bronze
  files volume, and a stop at the first refusal), ai_parse_document with the night's reading time checked before
  each page (live_parser), Prompt Shields and the embedding deployment with the keys the job reads from the secret
  scope, and the AI Search index.

When the document host refuses a request (HostRefused), or the night's reading time is spent (BudgetSpent), the
task stops reading, writes a data readiness note and finishes, so the job goes on and the next night starts where
this one stopped. The time is checked before each request and before each page the layout parser reads: the page
being read finishes, its layout stays in strata.bronze.layout_pages, and the document is listed as unfinished in
strata.ops.skipped_documents, with each document and project's document list the stop left as not read (ticket 86).
A document, or a project's document list, that the source cannot give (NotFetched)
does not stop the reading: it is skipped with its reason in strata.ops.skipped_documents, and a later run tries it
again. The passage reader writes each document's passages as soon as it has read it, so a stop keeps them
(ticket 72).
"""

from __future__ import annotations

import datetime as dt
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from strata.config import load_slice, load_sources
from strata.lakehouse import gold, passages, plans
from strata.lakehouse.engine import Engine
from strata.reader.documents import BudgetSpent, Documents, HostRefused, NotFetched, PoliteFetch, StopReading

log = logging.getLogger("strata.lakehouse.readers")

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
    # The night's reading time (PoliteFetch, through document_host): the passage reader checks it before each
    # document, which a document bronze already holds reads without a request (ticket 86). None reads without a limit,
    # as the recorded fixture does.
    budget: PoliteFetch | None = None


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


CACHE = "/Volumes/strata/bronze/files/fetched"  # the bundle's bronze files volume, a folder on serverless compute


def document_host(fetch, cache, sleep=None, clock=None):
    """fetch(url) for the World Bank's document host as the job asks it: the documents source's pause between
    requests (config/sources.toml), each document kept in cache once fetched, each project's document list, the
    documents API's endpoint, asked for again every night, so a document disclosed since is found, and no request
    after the night's reading time (config/thresholds.toml, ingestion.document_host_minutes), so the tasks after
    parse_and_embed still run inside the job's window."""
    from strata.config import load_thresholds
    from strata.reader.documents import PoliteFetch
    from strata.reader.layout import https

    source = load_sources()[SOURCE]
    lists = https(source.endpoint)
    minutes = float(load_thresholds().value("ingestion.document_host_minutes"))
    return PoliteFetch(fetch, source.pause_seconds or 0.0, cache, sleep=sleep, clock=clock,
                       keep=lambda url: not https(url).startswith(lists), budget=minutes * 60)


class OnBudget:
    """A layout parser that checks the night's reading time before each page it reads, as the fetch checks it before
    each request. ai_parse_document fetches a PDF once and reads its pages one by one: on October 26, 2026 it read 97
    pages of one plan in 99 minutes with no request between them, the time was never checked, and the job's
    150-minute stop ended parse_and_embed with the seven tasks after it never run (ticket 72). Once the time is
    spent, the page being read finishes and the next raises BudgetSpent."""

    def __init__(self, parser, fetch):
        self.parser, self.fetch, self.name = parser, fetch, parser.name

    def parse(self, page):
        self.fetch.within_budget(page.pdf_url, page.pdf_page)
        return self.parser.parse(page)


def live_parser(engine: Engine, fetch, upload):
    """The layout parser config/models.toml names ([layout] parser), on the job's fetch (document_host), with the
    night's reading time checked before each page. The nightly job and ops/documents/run_live.py build it here.
    upload(path, data) writes a page's PDF to the volume the parser reads."""
    from strata.config import load_layout_parser
    from strata.reader.layout import PARSERS

    return OnBudget(PARSERS[load_layout_parser()](engine, upload=upload, fetch=fetch), fetch)


def live(engine: Engine, environ: Mapping[str, str] | None = None, search_endpoint: str | None = None) -> Readers:
    """The readers on the workspace, as the job runs them on serverless compute. Without Azure OpenAI's keys the
    plan reader still runs, and the passage reader waits for a night that has them. search_endpoint is the AI
    Search endpoint the bundle names (variable ai_search_endpoint); without it sync_index syncs only gold."""
    from strata.config import load_models
    from strata.fixture.record import fetch_url
    from strata.knowledge.embed import AzureOpenAIEmbeddings
    from strata.knowledge.shields import PromptShields, content_safety_endpoint
    from strata.reader.documents import LiveDocuments

    env = os.environ if environ is None else environ
    fetch = document_host(fetch_url, CACHE if os.path.isdir(os.path.dirname(CACHE)) else None)
    layout = live_parser(engine, fetch, _write_to_volume)
    endpoint, key = env.get("AZURE_OPENAI_ENDPOINT", "").strip(), env.get("AZURE_OPENAI_API_KEY", "").strip()
    shield = embedder = None
    if endpoint and key:
        model = load_models()["embed"]
        shield = PromptShields(content_safety_endpoint(endpoint), key)
        embedder = AzureOpenAIEmbeddings(endpoint, key, model.deployment, model.dimensions)
    search = (search_endpoint or "").strip()
    return Readers(LiveDocuments(fetch), layout, shield, embedder,
                   plan_projects=passages.default_projects, report_projects=passages.default_projects,
                   index=_index(search) if search else None, budget=fetch)


def _write_to_volume(path: str, data: bytes) -> None:
    """Serverless compute reads and writes a Unity Catalog volume as a folder."""
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(data)


def _workspace_transport():
    """The workspace's REST API as the job's own sign-in on serverless compute, with a missing index raised as
    LookupError."""
    from databricks.sdk import WorkspaceClient

    client = WorkspaceClient()

    def transport(method: str, path: str, body: dict | None = None) -> dict:
        try:
            return client.api_client.do(method, path, body=body) or {}
        except Exception as error:  # the SDK's NotFound, read as a missing index
            if "does not exist" in str(error).lower() or "not found" in str(error).lower():
                raise LookupError(str(error)) from error
            raise

    return transport


def _index(endpoint: str, transport=None) -> Callable[[Engine], None]:
    """sync_index's call to the AI Search index. A missing index is made, and a new TRIGGERED Delta Sync index
    runs its first sync as it is made, so only an index that was already there is asked to sync: the workspace
    refuses a sync request while an index is still being made (ops/documents/run_live.py does the same)."""
    def sync(engine: Engine) -> None:
        from strata.config import load_models
        from strata.knowledge.search import AiSearchIndex

        index = AiSearchIndex(transport or _workspace_transport(), endpoint, load_models()["embed"].dimensions)
        if not index.ensure(lambda sql: engine.run(sql)):
            index.sync()

    return sync


def _count(engine: Engine, table: str) -> int:
    return int(engine.run(f"SELECT count(*) AS n FROM {table}").rows[0][0])  # sql-lint: names only, from ADDED_TO


@dataclass(frozen=True)
class Reading:
    """What both readers did in one run: the rows they added or changed, the passage reader's report when it
    finished, its counts so far (which hold what it wrote even when it stopped), and the stop that ended the
    reading, if one did. What each reader skipped or left unfinished is in strata.ops.skipped_documents."""

    changed: int
    report: passages.Report | None
    tally: passages.Tally
    stopped: StopReading | None = None


def read(engine: Engine, readers: Readers, run_id: str, clock: Callable[[], dt.datetime]) -> int:
    """The parse_and_embed task: both readers, over only what changed. Returns the rows they added or changed."""
    return reading(engine, readers, run_id, clock).changed


def reading(engine: Engine, readers: Readers, run_id: str, clock: Callable[[], dt.datetime],
            tally: passages.Tally | None = None, passages_first: bool = False) -> Reading:
    """Both readers, over only what changed, as the nightly job's parse_and_embed and ops/documents/run_live.py
    run them. A project whose plans the source cannot give (NotFetched, as when search.worldbank.org answered 503
    for P089634's document list on October 26, 2026) is skipped with its reason and the plan reader goes on; the
    passage reader writes each document as soon as it has read it and skips the same way (ticket 72). A stop ends
    the reading for the run and writes a data readiness note. tally, when given, counts the passage reader's
    documents as it goes, so a caller still has the counts when something else ends the run.

    The nightly job reads the plans first and the passages after them. The plan reader stops once only the passage
    reader's minutes of the night are left (config/thresholds.toml, ingestion.passage_reader_minutes), so the passage
    reader always has time: on October 27, 2026 the plan reader spent the whole night fetching P156634's Procurement
    Plans, and strata.gold.passage held no row after the run (ticket 86). That stop is not the night's: the plan it was
    parsing is listed as unfinished, each plan and project's document list it did not reach as not read, and the
    passage reader reads on until the night's time is spent. passages_first turns the order round, as
    ops/documents/run_live.py does, and the plans get the time that is left."""
    before = {table: _count(engine, table) for table in ADDED_TO}
    tally = tally if tally is not None else passages.Tally()
    report: passages.Report | None = None
    synced = 0

    def read_plans() -> StopReading | None:
        nonlocal synced
        stop = None
        projects = readers.plan_projects(engine)
        at = 0
        try:
            with _leaving_for_passages(readers, after=not passages_first):
                for at, project_id in enumerate(projects):
                    try:
                        plans.run(engine, readers.documents, readers.layout, project_id, clock=clock, run_id=run_id)
                    except NotFetched as error:  # its document list, or a PDF the layout parser needed
                        plans.skip(engine, run_id, "plans",
                                   plans.Skipped(project_id, None, error.url or _list(project_id), str(error)), clock())
        except StopReading as stopped:
            stop = stopped
            # plans.run listed what the stop left of its project; each later project's document list waits too.
            plans.not_read(engine, run_id, "plans", [plans.unreached(later, None, _list(later), stopped)
                                                     for later in projects[at + 1:]], clock())
        synced += gold.sync(engine, "package")  # its query reads the plan rows read tonight, before any stop
        if isinstance(stop, BudgetSpent) and stop.left_for is not None:  # its share of the night, not the night's end
            log.warning("The plan reader stopped, and the passage reader reads next: %s", stop)
            return None
        return stop

    def read_passages() -> StopReading | None:
        nonlocal report, synced
        if readers.shield is None or readers.embedder is None:
            return None
        try:
            report = passages.run(engine, readers.documents, readers.report_projects(engine), shield=readers.shield,
                                  embedder=readers.embedder, layout=readers.layout, clock=clock, run_id=run_id,
                                  tally=tally, budget=readers.budget.within_budget if readers.budget else None)
        except StopReading as stopped:
            synced += tally.synced  # the documents written before the stop stay in strata.gold.passage
            return stopped
        synced += report.synced
        return None

    stop: StopReading | None = None
    for read_one in (read_passages, read_plans) if passages_first else (read_plans, read_passages):
        stop = read_one()
        if stop is not None:  # the reader after it waits for the next run
            note_stop(engine, run_id, clock(), stop, tally)
            if tally.parsed or tally.skipped:  # the task's log names what the passage reader wrote (ticket 86)
                log.warning("I wrote the passages of %s before the stop%s", _documents(len(tally.written_ids)),
                            f": {_joined(tally.written_ids)}." if tally.written_ids else ".")
            break
    changed = synced + sum(_count(engine, table) - count for table, count in before.items())
    return Reading(changed, report, tally, stop)


PASSAGE_READER = "the passage reader"


def _leaving_for_passages(readers: Readers, after: bool):
    """While the plan reader reads, the night's time ends the passage reader's minutes early
    (ingestion.passage_reader_minutes), when the passage reader reads after it and can run: it has a shield and an
    embedder, and the night has a reading time."""
    from contextlib import nullcontext

    from strata.config import load_thresholds

    if not after or readers.budget is None or readers.shield is None or readers.embedder is None:
        return nullcontext()
    minutes = float(load_thresholds().value("ingestion.passage_reader_minutes"))
    return readers.budget.leaving(minutes * 60, PASSAGE_READER)


def _list(project_id: str) -> str:
    """The documents API address of the project's document list, which a skipped plan reading names."""
    from strata.reader.documents import list_url

    return list_url(load_sources()[SOURCE].endpoint, project_id)


def _documents(count: int) -> str:
    return f"{plans.count_words(count)} document{'' if count == 1 else 's'}"


def _joined(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _passage_reading(tally: passages.Tally) -> str:
    """What the passage reader wrote and left before a stop, as a sentence for the stop's note (ticket 86)."""
    left = plans.left_words(*tally.left())
    said = f"I wrote the passages of {_documents(tally.written)} before the stop"
    if tally.unchanged:
        said += f", found {_documents(tally.unchanged)} already written and unchanged"
    return f"{said}, and left {left} for the next night." if left else f"{said}."


def note_stop(engine: Engine, run_id: str, when: dt.datetime, stopped: StopReading,
              tally: passages.Tally | None = None) -> None:
    """A data readiness note that the readers stopped for the night: the document host refused a request, or the
    night's reading time was spent. When the passage reader had started, the note also counts the documents it wrote
    before the stop and those it left, which strata.ops.skipped_documents lists one by one (ticket 86)."""
    day = f"{when:%B} {when.day}, {when.year}"
    if isinstance(stopped, HostRefused):
        why = (f"The document host answered HTTP {stopped.status} on {day}, so I stopped reading documents "
               "for the night.")
    else:
        minutes = getattr(stopped, "minutes", None)
        why = (f"I stopped reading documents on {day}, after the night's {minutes} minutes for the document host, "
               "so the job's later tasks had time to run.")
    reading = f" {_passage_reading(tally)}" if tally is not None and (tally.parsed or tally.skipped) else ""
    engine.insert_rows("strata.ops.data_readiness", NOTE_COLUMNS, [(
        run_id, SOURCE, "all", stopped.measure, "fresh", None, None, when.date(),
        f"{why}{reading} The documents and pages read before it are kept, and the next night goes on from there.",
        when, when.date())])


def sync_index(engine: Engine, readers: Readers | None) -> int:
    """The sync_index task: strata.gold.passage made equal to the passages, then, on the workspace, the AI Search
    index asked to sync from it. Returns the gold rows it added, changed or removed."""
    changed = gold.sync(engine, "passage")
    if readers is not None and readers.index is not None:
        readers.index(engine)
    return changed
