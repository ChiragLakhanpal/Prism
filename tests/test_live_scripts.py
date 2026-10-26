"""The live scripts as the first live runs met them (ticket 66): what each script installs, and the services its
readers and tools reach, proven offline with stand-ins at the network's edge.

The live agent's scripts (ops/agent/refuse_live.py, ops/agent/ask_live.py) run the app's /api/ask stream, which
detects the question's language with py3langid (src/strata/knowledge/language.py), so each script's inline
dependency list must name it at the pin pyproject.toml holds: `uv run --script` installs only what that list names.

They also load the env file once and must give it to every tool the agent calls. On October 26, 2026 every
must-refuse question whose agent called search_passages failed with KeyError: 'AZURE_OPENAI_ENDPOINT', because
the searcher read the process's environment, which the env file never reaches. Here the scripts run with the
Foundry agent replaced by one that searches before it answers, the SQL warehouse replaced by the fixture database,
and the workspace's REST API and Azure OpenAI replaced by recorders that answer from tests/fixtures/ai_search. The
process holds none of the settings, so search_passages can only get them from the env file.
"""

import asyncio
import importlib.util
import json
import re
import sys
import tomllib
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

from strata.harness.sse import events
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
ANSWER_STREAM_SCRIPTS = ("ops/agent/refuse_live.py", "ops/agent/ask_live.py")
# The env file as the wizard writes it, with made-up values. The process's environment holds none of them.
ENV = {"FOUNDRY_PROJECT_ENDPOINT": "https://wb-strata.services.ai.azure.com/api/projects/strata",
       "DATABRICKS_HOST": "https://example.cloud.databricks.com", "DATABRICKS_WAREHOUSE_ID": "0123456789abcdef",
       "DATABRICKS_TOKEN": "not-a-real-key", "AZURE_OPENAI_ENDPOINT": "https://wb-strata.openai.azure.com/openai/v1",
       "AZURE_OPENAI_API_KEY": "not-a-real-key-either"}
QUERY = "/api/2.0/vector-search/indexes/strata.gold.passage_index/query"


def inline_dependencies(path: Path) -> list[str]:
    """The dependencies a script's inline metadata block (# /// script ... # ///) names, as uv reads them."""
    block = re.search(r"^# /// script\n(.*?)^# ///$", path.read_text(), re.S | re.M).group(1)
    return tomllib.loads("".join(line.removeprefix("#").removeprefix(" ") + "\n"
                                 for line in block.splitlines()))["dependencies"]


def pinned(name: str) -> str:
    """The project's pin for a package, from pyproject.toml."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    return next(entry for entry in project["dependencies"] if entry.split("==")[0] == name)


@pytest.mark.parametrize("script", ANSWER_STREAM_SCRIPTS)
def test_a_script_that_runs_the_answer_stream_installs_the_language_detector(script):
    assert pinned("py3langid") in inline_dependencies(ROOT / script)


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def installed_by(requirements: list[str]) -> set[str]:
    """Every distribution `uv run --script` installs for these requirements: each one and what it requires in turn,
    read from the metadata of the versions this checkout's environment holds."""
    from importlib import metadata

    from packaging.requirements import Requirement

    found, waiting = set(), [Requirement(line) for line in requirements]
    while waiting:
        requirement = waiting.pop()
        if canonical(requirement.name) in found:
            continue
        found.add(canonical(requirement.name))
        try:
            needs = metadata.requires(requirement.name) or []
        except metadata.PackageNotFoundError:  # a package only the script installs, such as Application Insights'
            needs = []
        waiting += [need for need in map(Requirement, needs) if need.marker is None or need.marker.evaluate({"extra": ""})]
    return found


# Loads a script as uv runs it, then what its app loads to answer: the server, every tool's adapter and the stream's
# language detector (ticket 42), and prints every module they imported.
LOADS = """
import importlib, importlib.util, json, sys, tomllib
root, script = sys.argv[1], sys.argv[2]
sys.path[:0] = [root + "/src", root + "/ops/agent"]
before = set(sys.modules)
spec = importlib.util.spec_from_file_location("script", root + "/" + script)
spec.loader.exec_module(importlib.util.module_from_spec(spec))
import strata.server.app
from strata.config import load_thresholds
from strata.knowledge import language
for tool in tomllib.loads(open(root + "/config/tools.toml").read())["tools"].values():
    importlib.import_module(tool["adapter"].split(":")[0])
language.detect("Why were works contracts in P130164 advertised again?", load_thresholds())
print(json.dumps(sorted(set(sys.modules) - before)))
"""


@pytest.mark.parametrize("script", ANSWER_STREAM_SCRIPTS)
def test_a_script_that_runs_the_answer_stream_installs_every_package_its_app_imports(script):
    """The must-refuse check and the showcase check build the app in the uv environment their inline list makes, so
    each package the app imports to answer must be one that list installs; ticket 38's uploads brought defusedxml
    into the server's imports, which neither list named."""
    import subprocess
    from importlib import metadata

    loaded = json.loads(subprocess.run([sys.executable, "-c", LOADS, str(ROOT), script], check=True,
                                       capture_output=True, text=True).stdout)
    owners, files = metadata.packages_distributions(), {}

    def owner(module: str) -> set[str]:
        """The distribution a module comes from. Where several share its top-level name, as opentelemetry's api, sdk
        and semantic conventions do, the one whose files hold it."""
        names = owners.get(module.split(".")[0], [])
        if len(names) < 2:
            return {canonical(name) for name in names}
        path = module.replace(".", "/")
        return {canonical(name) for name in names
                if {f"{path}.py", f"{path}/__init__.py"} & files.setdefault(name, {str(f) for f in metadata.files(name)})}

    imported = set().union(*(owner(module) for module in loaded if module.split(".")[0] not in sys.stdlib_module_names))

    assert "fastapi" in imported and "py3langid" in imported  # the scan saw the server and the detector
    assert sorted(imported - installed_by(inline_dependencies(ROOT / script))) == []


# ── The env file reaches every tool ──────────────────────────────────────

class SearchesThenAnswers:
    """The Foundry agent's stand-in: it asks search_passages about the question, keeps what the tool gave back,
    then answers with the refusal the benchmark expects for the question, or with no claims."""

    name, version = "strata-orchestrator", "stand-in"

    def __init__(self, refusals: dict[str, str], seen: list):
        self.refusals, self.seen, self.question = refusals, seen, None

    def respond(self, items, previous_response_id):
        if previous_response_id is None:
            self.question = json.loads(items[0]["content"])["question"]
            return {"id": "resp_1", "output": [{"type": "function_call", "call_id": "call_1", "name": "search_passages",
                                                "arguments": json.dumps({"query": self.question})}]}
        self.seen.append(json.loads(items[0]["output"]))
        key = self.refusals.get(self.question)
        answer = {"claims": [], **({"refusal": {"key": key, "partial": False}} if key else {})}
        return {"id": "resp_2", "output": [{"type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": json.dumps(answer)}]}]}


class AsTheWarehouse:
    """The fixture database standing in for the SQL warehouse, so the tools take their workspace paths."""

    name = "databricks"

    def __init__(self, engine):
        self.engine = engine

    def run(self, sql, params=None):
        return self.engine.run(sql, params)


@pytest.fixture
def agent_script(monkeypatch):
    """Load one of ops/agent's scripts as a module, as uv runs it; sys.path and the modules it adds go back after."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    # ops/dayone has a module named live too, which a test before this one may have imported; the scripts need
    # ops/agent's, and the day-one tests get theirs back afterwards.
    monkeypatch.delitem(sys.modules, "live", raising=False)
    before = set(sys.modules)

    def load(name: str):
        spec = importlib.util.spec_from_file_location(f"strata_ops_agent_{name}", ROOT / "ops" / "agent" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    yield load
    for name in set(sys.modules) - before:
        if name in ("live", "dayone") or name.startswith("strata_ops_agent_"):
            sys.modules.pop(name)


@pytest.fixture
def the_workspace(monkeypatch, fixture_db):
    """The live services, replaced at the network's edge: the agent, the warehouse, the workspace's REST API and
    Azure OpenAI's embeddings. Returns what each was asked, so a test can say which settings reached it."""
    from strata.knowledge import embed
    from strata.lakehouse import engine as engines

    for key in ENV:
        monkeypatch.delenv(key, raising=False)
    asked = {"workspace": [], "embeddings": [], "tool_results": []}
    recorded = json.loads((ROOT / "tests" / "fixtures" / "ai_search" / "query.json").read_text())["response"]

    def http_transport(host, token, timeout=120):
        asked["workspace"].append((host, token))
        return lambda method, path, body=None: recorded if (method, path) == ("POST", QUERY) else {}

    class Embeddings:
        name, dimensions = "text-embedding-3-large", 4

        def __init__(self, endpoint, key, deployment, dimensions):
            asked["embeddings"].append((endpoint, key))

        def embed(self, texts):
            return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as opened:
            yield AsTheWarehouse(opened)

    monkeypatch.setattr(engines, "http_transport", http_transport)
    monkeypatch.setattr(embed, "AzureOpenAIEmbeddings", Embeddings)
    questions = yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]
    refusals = {question["question"]: question["expected"]["refusal"] for question in questions
                if question["kind"] == "refusals"}

    def replace(*modules):
        for module in modules:
            for name, value in (("foundry_agent", lambda env, spec: SearchesThenAnswers(refusals, asked["tool_results"])),
                                ("warehouse_engine_for", lambda env: engine_for)):
                if hasattr(module, name):
                    monkeypatch.setattr(module, name, value)
    asked["replace"] = replace
    return asked


def test_the_must_refuse_check_gives_search_passages_the_env_file_s_settings(agent_script, the_workspace, tmp_path,
                                                                           capsys):
    refuse_live = agent_script("refuse_live")
    the_workspace["replace"](sys.modules["live"], refuse_live)
    env_file = tmp_path / ".env"
    env_file.write_text("".join(f"{key}={value}\n" for key, value in ENV.items()))

    code = refuse_live.main(["--env-file", str(env_file)])

    printed = capsys.readouterr().out.splitlines()
    assert code == 0, printed
    assert len(printed) == 11 and all(line.startswith("Holds. ") for line in printed)
    # Each question's search reached AI Search on the env file's workspace, as the env file's token, and embedded
    # its query with the env file's Azure OpenAI endpoint and key; the fixture's passages came back.
    assert the_workspace["workspace"] == [(ENV["DATABRICKS_HOST"], ENV["DATABRICKS_TOKEN"])] * 11
    assert the_workspace["embeddings"] == [(ENV["AZURE_OPENAI_ENDPOINT"], ENV["AZURE_OPENAI_API_KEY"])] * 11
    assert all(result.get("rows") and "error" not in result for result in the_workspace["tool_results"])


def test_the_showcase_check_gives_search_passages_the_env_file_s_settings(agent_script, the_workspace, monkeypatch):
    ask_live = agent_script("ask_live")
    the_workspace["replace"](sys.modules["live"], ask_live)
    logged = []
    monkeypatch.setattr(ask_live, "RunLog", lambda engine: type("Kept", (), {"record": lambda self, row: logged.append(row)})())
    case = ask_live.load_cases()[ask_live.CASE]

    text = asyncio.run(ask_live.post(ask_live.app_for(ENV), ENV, case))

    kinds = [kind for kind, _ in events(text)]
    assert "error" not in kinds and kinds[-1] == "done", text
    assert the_workspace["workspace"] == [(ENV["DATABRICKS_HOST"], ENV["DATABRICKS_TOKEN"])]
    assert the_workspace["embeddings"] == [(ENV["AZURE_OPENAI_ENDPOINT"], ENV["AZURE_OPENAI_API_KEY"])]
    [result] = the_workspace["tool_results"]
    assert result["rows"][0]["evidence_id"] == "strata.gold.passage:31525018/v1/54"
    # The run was written to the run log, answered, with its one search_passages call.
    [row] = logged
    assert (row["question"], row["status"], row["error_code"]) == (case.question, "answered", None)
    assert [call["tool"] for call in json.loads(row["tool_calls"])] == ["search_passages"]


# ── The live document run fetches as the nightly job does ────────────────

class Host:
    """The World Bank's document host: each address answered with its own bytes, or refused."""

    def __init__(self, refuse=()):
        self.asked, self.refuse = [], set(refuse)

    def __call__(self, url):
        import urllib.error

        self.asked.append(url)
        if url in self.refuse:
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        return json.dumps({"documents": {}}).encode() if "/v3/wds" in url else f"the text at {url}".encode()


class Clock:
    def __init__(self):
        self.now, self.slept = 100.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(round(seconds, 3))
        self.now += seconds


@pytest.fixture
def run_live(monkeypatch):
    """ops/documents/run_live.py as a module, as uv runs it; sys.path goes back after."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    path = ROOT / "ops" / "documents" / "run_live.py"
    spec = importlib.util.spec_from_file_location("strata_ops_documents_run_live", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_live_document_run_reads_through_the_nightly_job_s_paced_and_kept_fetch(run_live, tmp_path):
    """The catch-up's document runs asked documents.worldbank.org back to back with plain urllib, were refused, and
    fetched the oversized plan texts again on every attempt. The run now builds its documents source and its layout
    parser on the nightly job's fetch (strata.lakehouse.readers.document_host): a pause between requests, each
    document kept once fetched, and a stop at the host's first refusal."""
    from strata import config
    from strata.lakehouse import readers
    from strata.reader.documents import HostRefused, LiveDocuments, PoliteFetch, list_url

    refused = "https://documents.worldbank.org/curated/en/099/refused.txt"
    host, clock = Host(refuse={refused}), Clock()
    documents, layout = run_live.document_readers(None, upload=lambda path, data: None, fetch=host,
                                                  cache=tmp_path / "fetched", sleep=clock.sleep, clock=clock)

    assert isinstance(documents, LiveDocuments) and isinstance(documents.fetch, PoliteFetch)
    assert layout.fetch is documents.fetch  # one fetcher for the texts, the PDFs and the pages the parser cuts
    assert documents.fetch.pause == config.load_sources()[readers.SOURCE].pause_seconds == 3.0
    listing = list_url(config.load_sources()[readers.SOURCE].endpoint, "P156634")
    text = "https://documents.worldbank.org/curated/en/099/plan.txt"

    documents.listing(listing)
    clock.now += 1.0  # the reader spends a second on the list
    documents.text(text)
    assert documents.text(text).body == f"the text at {text}"  # a second attempt reads the kept copy
    with pytest.raises(HostRefused):
        documents.text(refused)

    assert host.asked == [listing, text, refused]
    assert clock.slept == [2.0, 3.0]
    assert len(list((tmp_path / "fetched").iterdir())) == 1  # the text, never the list


def pdf_of(pages: list[str]) -> bytes:
    """A PDF whose text layer holds each page's lines, written by hand so the test needs no PDF writer."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", "", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in pages:
        lines = " ".join("({}) Tj T*".format(line.encode("latin-1", "replace").decode("latin-1").replace(
            "\\", "\\\\").replace("(", "\\(").replace(")", "\\)")) for line in text.split("\n"))
        stream = f"BT /F1 6 Tf 7 TL 20 780 Td {lines} ET"
        kids.append(f"{len(objects) + 1} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> "
                       f"/Contents {len(objects) + 2} 0 R >>")
        objects.append(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>"
    out, offsets = "%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out.encode("latin-1")))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out.encode("latin-1"))
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    return (out + f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode("latin-1")


def test_the_live_document_run_s_reader_reads_the_fixture_s_plans_into_the_same_pages_and_rows(run_live, tmp_path):
    """A dry run of the live document run's documents source on the fixture: P156634's recorded list, plan texts and
    PDFs (each PDF's text layer written from the recorded page texts) served by a stand-in host, through the paced,
    kept fetch, give the plan reader the same versions, the same 15 Route B pages and the same STEP rows as the
    fixture's own recorded source. The layout parser is the recorded one on both sides, since ai_parse_document needs
    the warehouse."""
    import urllib.error

    from strata.fixture import recorded as fmt
    from strata.lakehouse import catalog, plans
    from strata.reader.documents import RecordedDocuments, https
    from strata.reader.layout import RecordedLayout

    manifest = fmt.load_manifest()
    recorded = RecordedDocuments(manifest)
    by_url = {https(source.url): ("list", source.url) for source in manifest.sources if source.kind == "json"}
    by_url |= {https(source.text_url): ("text", source.text_url) for source in manifest.sources if source.kind != "json"}
    by_url |= {https(source.pdf_url): ("pdf", source.pdf_url) for source in manifest.sources if source.kind != "json"}
    asked, waits = [], []

    def host(url):
        asked.append(url)
        kind, address = by_url.get(url, (None, None))
        if kind == "list":
            return json.dumps(recorded.listing(address).body).encode()
        if kind == "text":
            return recorded.text(address).body.encode()
        if kind == "pdf":
            return pdf_of(recorded.pages(address).body)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    def read(documents):
        with DuckDBEngine.open() as engine:
            catalog.build(engine)
            report = plans.run(engine, documents, RecordedLayout(manifest), "P156634")
            return report.parsing.parsed, [sorted(engine.run(sql).as_text()) for sql in (
                "SELECT document_id, pdf_page FROM strata.bronze.layout_pages",
                "SELECT document_id, activity_reference_no, section FROM strata.silver.plan_rows",
                "SELECT document_id, pdf_pages, route_b_pages, parse_reason FROM strata.silver.plan_versions")]

    documents, _ = run_live.document_readers(None, upload=lambda path, data: None, fetch=host,
                                             cache=tmp_path / "fetched", sleep=waits.append)
    through_the_live_reader = read(documents)

    assert through_the_live_reader == read(recorded)
    assert through_the_live_reader[0] == 15 and len(through_the_live_reader[1][1]) > 0
    assert len(asked) == len(set(asked)) and waits  # each address asked once, with pauses between requests
