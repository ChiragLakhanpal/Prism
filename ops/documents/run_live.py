# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "pypdf==6.21.2", "py3langid==0.3.0"]
# ///
"""Read the document slice into numbered passages on the shared workspace, with Route B, and sync
their AI Search index: tickets 11 and 18's live run.

Run it from the main checkout, after the deploy (ops/bundle/deploy.py) has made the strata catalog
and its tables, and after the nightly job has filled strata.gold.project:

    uv run --script ops/documents/run_live.py --env-file .env

It runs the same readers as the gate with the live adapters. First the passage reader
(src/strata/lakehouse/passages.py) counts the projects the slice criteria select from
strata.gold.project (config/slice.toml) and fetches their documents, with the showcase's, the demo
plan's and the stress shelf's, from the World Bank's hosts on this computer. Then the plan reader
(src/strata/lakehouse/plans.py) reads each slice project's Procurement Plans. Both readers fetch through the
nightly job's fetch (strata.lakehouse.readers.document_host): the documents source's pause between requests, each
document kept in .cache/documents once fetched, so a later run never asks for it again, and a stop at the host's
first refusal or once the reading time in config/thresholds.toml is spent. Route A reads the published
text; every page the page router sends to Route B goes, one page at a time, to the layout parser that
config/models.toml names ([layout] parser: ai_parse_document until day-one test 3 chooses), under the
daily page cap both readers share (config/thresholds.toml, ingestion.daily_page_cap). Each passage is
scanned with Prompt Shields on the Foundry resource; only a passage whose header or text changed is
embedded again, with the deployment config/models.toml names for the embed role. The run writes bronze,
silver, strata.gold.passage and strata.ops on the warehouse, with the stress shelf's outcomes in
strata.ops.stress_shelf. Then it makes the Delta Sync index that config/models.toml's [search] table
names on the AI Search endpoint the env file names (AI_SEARCH_ENDPOINT), when it is missing, syncs it,
and waits until it holds every passage. A second run the same day parses no page it read.

The run reads through the nightly job's own path (strata.lakehouse.readers.reading), so the job and this
script share one writer of passages. It reads the slice's reports into passages first, then the Procurement
Plans with the time that is left, so a run whose plan pages outlast the reading time still writes passages; the
nightly job reads the plans first. It writes each document's passages to strata.gold.passage as soon as it has
read that document (ticket 72). A document, or a project's document list, that a host does not give, as
when search.worldbank.org answered 503 for P089634's list on October 26, 2026, is skipped: the run prints it
with its reason as it goes, records it in strata.ops.skipped_documents, and goes on with the next. At the end
it prints how many documents it parsed, skipped and wrote.

A run that stops before it finished, as when a World Bank host refuses a request or the reading time in
config/thresholds.toml (ingestion.document_host_minutes) is spent, keeps every document it wrote before the stop,
lists the document it was reading as unfinished in strata.ops.skipped_documents, and syncs the index; the next run
goes on from there. The time is checked before each page the layout parser reads as well as before each request.

It exits 0 when it wrote at least one document's passages and the index holds every passage, 1 when the index
did not catch up in time, and 2 when it wrote no document's passages or could not run.

It needs DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, a token or a service principal, AI_SEARCH_ENDPOINT,
AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY. Then check the ground-truth queries on both engines, as
for every file marked for databricks, among them the slice's project count:

    uv run --script ops/bundle/check.py same-rows --env-file .env
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import sys
import time
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.config import load_layout_parser, load_models  # noqa: E402
from strata.lakehouse import passages, plans, readers  # noqa: E402
from strata.lakehouse.engine import EngineError  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

NEEDS = ("AI_SEARCH_ENDPOINT", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
WAIT_MINUTES = 30
# Where this computer keeps each document it fetched, so a run that stopped never asks for it again; the nightly
# job keeps them in the bronze files volume instead. .cache is gitignored.
CACHE = REPO / ".cache" / "documents"


def document_readers(engine, upload, fetch=None, cache=CACHE, sleep=None, clock=None):
    """The documents source and the layout parser the run reads with, on the one fetch the nightly job uses
    (strata.lakehouse.readers.document_host, ticket 66): the documents source's pause between requests
    (config/sources.toml), each document kept in cache once fetched, every project's document list asked for again,
    a HostRefused stop at the host's first 403 or 429, and the night's reading time (config/thresholds.toml,
    ingestion.document_host_minutes), checked before each request and before each page the parser reads, after
    which the run stops and the next goes on from the kept copies (ticket 72). fetch is the host (plain urllib unless
    a test gives one); upload writes a page's PDF to the volume for the parser."""
    from strata.fixture.record import fetch_url
    from strata.lakehouse.readers import document_host, live_parser
    from strata.reader.documents import LiveDocuments

    paced = document_host(fetch or fetch_url, cache, sleep=sleep, clock=clock)
    return LiveDocuments(paced), live_parser(engine, paced, upload)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


RUN_RECORD = """
SELECT reader, project_id, document_id, url, outcome, reason FROM strata.ops.skipped_documents
WHERE run_id = :run_id ORDER BY skipped_at, project_id, document_id
"""


def read_documents(engine, found: readers.Readers, run_id: str, clock: Callable[[], dt.datetime] = _now) -> int:
    """Both readers over the slice, through the nightly job's own path (strata.lakehouse.readers.reading), so the
    job and this script share one writer of passages: the passage reader first, then the plan reader with the time
    that is left (passages_first), so the plans' scanned pages cannot spend the reading time before a passage is
    written, as they did on October 26, 2026. Each document a reader skips or leaves unfinished is printed
    with its reason as the run goes (a warning from strata.lakehouse.plans) and again at the end from the run's
    record in strata.ops.skipped_documents, with how many documents the run parsed, skipped and wrote. Returns 0 when
    the run wrote at least one document's passages to strata.gold.passage, and 2 when it wrote none or could not
    run."""
    from strata.knowledge.embed import EmbedError
    from strata.knowledge.shields import ShieldError

    tally = passages.Tally()
    done = None
    try:
        done = readers.reading(engine, found, run_id, clock, tally=tally, passages_first=True)
    # The warehouse, Prompt Shields or the embedding deployment failed, or a request did: urllib's errors and the
    # Databricks SDK's are OSErrors. What the run wrote before stays.
    except (EngineError, ShieldError, EmbedError, OSError) as error:
        print(f"The run stopped: {str(error).rstrip('.')}. The documents it wrote before that stay in "
              "strata.gold.passage, and the next run goes on from there.")
    try:
        record = engine.run(RUN_RECORD, {"run_id": run_id}).rows
    except EngineError:
        record = []  # the warehouse is what failed; the skips were printed as the run went
    skipped = [row for row in record if row[4] == "skipped"]
    unfinished = [row for row in record if row[4] != "skipped"]
    print(f"Run {run_id} parsed {tally.parsed} document{'' if tally.parsed == 1 else 's'}, skipped {len(skipped)} and "
          f"wrote the passages of {tally.written} to strata.gold.passage"
          + (f", and left {len(unfinished)} unfinished." if unfinished else "."))
    for reader, project_id, document_id, url, outcome, reason in record:
        what = plans.named(reader, document_id)
        print(f"  {what} of {project_id}, {'skipped' if outcome == 'skipped' else 'left unfinished'} by the "
              f"{'plan' if reader == 'plans' else 'passage'} reader ({url}): {reason}")
    if done is not None and done.stopped is not None:
        print(f"It stopped before it finished: {str(done.stopped).rstrip('.')}. The documents it wrote before that "
              "stay, and the next run goes on from there.")
    report = done.report if done is not None else None
    if report is not None:
        print(f"It counted {report.slice_projects} projects in the slice and read {report.documents} documents into "
              f"{report.passages} passages, with {report.scans} scans read by {found.layout.name}, and "
              f"{report.notice_passages} passages of notices' text. {found.shield.name} scanned {report.scanned} "
              f"new passage texts and {found.embedder.name} embedded {report.embedded}.")
        passages.print_measures(engine, report.run_id)
        for outcome in report.shelf:
            shown = f"{outcome.count} of {outcome.denominator}" if outcome.count is not None else outcome.state
            print(f"  stress shelf {outcome.shelf_key}: {outcome.document_id or 'no document'}, {shown}")
    return 0 if done is not None and tally.written else 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/documents/run_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse, sign-in and keys")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    missing = [key for key in NEEDS if not env.get(key)]
    if missing:
        print(f"The env file has no value for {', '.join(missing)}. Run the setup wizard first "
              "(ops/wizard/strata-setup.sh).")
        return 2

    from bundle_live import LiveWorkspace  # the Databricks SDK, which only the live run needs
    from databricks.sdk.errors import NotFound

    from strata.knowledge.embed import AzureOpenAIEmbeddings
    from strata.knowledge.search import AiSearchIndex
    from strata.knowledge.shields import PromptShields, content_safety_endpoint
    from strata.reader.layout import PARSERS

    name = load_layout_parser()
    if name not in PARSERS:
        print(f"config/models.toml names the layout parser {name}, and Strata has no adapter for it. "
              f"Name one of these: {', '.join(sorted(PARSERS))}.")
        return 2
    workspace = LiveWorkspace(env)
    engine = workspace.engine()
    documents, layout = document_readers(
        engine, upload=lambda path, data: workspace.w.files.upload(path, io.BytesIO(data), overwrite=True))

    def rest(method: str, path: str, body: dict | None = None) -> dict:
        try:
            return workspace.w.api_client.do(method, path, body=body) or {}
        except NotFound as error:
            raise LookupError(str(error)) from error

    model = load_models()["embed"]
    shield = PromptShields(content_safety_endpoint(env["AZURE_OPENAI_ENDPOINT"]), env["AZURE_OPENAI_API_KEY"])
    embedder = AzureOpenAIEmbeddings(env["AZURE_OPENAI_ENDPOINT"], env["AZURE_OPENAI_API_KEY"], model.deployment,
                                     model.dimensions)
    found = readers.Readers(documents, layout, shield, embedder, plan_projects=passages.default_projects,
                            report_projects=passages.default_projects)
    code = read_documents(engine, found, f"documents-{_now():%Y%m%dT%H%M%S%f}")
    if code:
        return code

    held = int(engine.run("SELECT count(*) AS n FROM strata.gold.passage").rows[0][0])
    index = AiSearchIndex(rest, env["AI_SEARCH_ENDPOINT"], model.dimensions)
    made = index.ensure(lambda sql: engine.run(sql))
    if not made:
        index.sync()
    deadline = time.monotonic() + WAIT_MINUTES * 60
    state = index.state()
    while not (state.ready and state.rows >= held) and time.monotonic() < deadline:
        time.sleep(30)
        state = index.state()
    print(f"The index {index.index} on {index.endpoint} holds {state.rows} of the {held} passages in "
          f"{index.table}{' and is ready' if state.ready else ''}. {state.message}".strip())
    return 0 if state.ready and state.rows >= held else 1


if __name__ == "__main__":
    sys.exit(main())
