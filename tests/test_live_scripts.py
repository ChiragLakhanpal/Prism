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
