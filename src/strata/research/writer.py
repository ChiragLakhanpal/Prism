"""The deep research brief's writer (ticket 148), and the recorded writer and judge the offline tests replay.

The live writer is one chat completion on Azure OpenAI, on the deployment of the role config/models.toml names under
[research_writer], with src/strata/agent/instructions/research_brief_writer.md as its system message and the run's
message (strata.research.brief.message) as the user's. It answers with the brief as one JSON object. It has no tools:
the app hands it every item, and the verifier checks every sentence it writes.

Offline, RecordedWriter replays a recorded answer and RecordedJudge a recorded judge answer, each from a JSON file
that ops/agent/record.py --research writes (tests/fixtures/agent/research/). A recorded answer is for one project as
of one day; the judge's is for the exact sentences it was asked about, as the scripted judge's is.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from importlib import resources
from pathlib import Path
from typing import Protocol

from strata.agent.judge import JudgeError, Question, Judgement, judgements
from strata.agent.retries import Retries, Waits
from strata.knowledge.http import post_json

INSTRUCTIONS = "research_brief_writer.md"
WHO = "The research brief's writer on Azure OpenAI"


class WriterError(RuntimeError):
    """The writer gave no answer: Azure OpenAI refused or timed out, or no recording matches."""

    def __init__(self, message: str, status: int | None = None, headers: Mapping | None = None):
        super().__init__(message)
        self.status, self.headers = status, dict(headers or {})


class Writer(Protocol):
    name: str

    def write(self, message: str, project_id: str, as_of: str) -> str:
        """The brief, as the JSON text the writer answered with."""


def instructions() -> str:
    return (resources.files("strata.agent") / "instructions" / INSTRUCTIONS).read_text()


def request_body(deployment: str, message: str) -> dict:
    return {"model": deployment, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": instructions()}, {"role": "user", "content": message}]}


def answer_text(response: Mapping) -> str:
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise WriterError(f"The writer gave an answer I cannot read: {error}") from error


class AzureWriter:
    """The research_writer role's deployment on Azure OpenAI, asked once per brief."""

    def __init__(self, endpoint: str, key: str, deployment: str, post: Callable | None = None,
                 timeout: float | None = None, retries: Retries | None = None, sleep: Callable | None = None):
        from strata.config import load_thresholds

        thresholds = load_thresholds()
        seconds = timeout if timeout is not None else thresholds.value("research.writer_timeout_seconds")
        self.url, self.headers, self.name = f"{endpoint.rstrip('/')}/chat/completions", {"api-key": key}, deployment
        self.retries, self.sleep = retries or Retries.from_thresholds(thresholds), sleep
        self.post = post or (lambda url, headers, body: post_json(url, headers, body, timeout=seconds,
                                                                   error=WriterError, service="Azure OpenAI"))
        self.last_response: dict | None = None  # the recording command keeps it (ops/agent/record.py --research)

    def write(self, message: str, project_id: str, as_of: str) -> str:
        waits = Waits(WHO, self.retries, self.sleep)
        try:
            self.last_response = waits.call(lambda: self.post(self.url, self.headers, request_body(self.name, message)),
                                            WriterError)
        except (TimeoutError, OSError, ValueError) as error:
            raise WriterError(f"Azure OpenAI gave no answer I can read: {error}") from error
        return answer_text(self.last_response)


def from_environment(environ: Mapping[str, str] = os.environ) -> AzureWriter | None:
    """The live writer, or None without Azure OpenAI's keys."""
    from strata.config import load_models, load_research_writer_role

    endpoint, key = environ.get("AZURE_OPENAI_ENDPOINT", "").strip(), environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not (endpoint and key):
        return None
    return AzureWriter(endpoint, key, load_models()[load_research_writer_role()].deployment)


# ── Recorded answers, for the tests ──────────────────────────────────────

RECORDED = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "agent" / "research"


class RecordedWriter:
    """Replays the recorded writer answer for a project as of a day, and counts its calls."""

    name = "recorded research writer"

    def __init__(self, path: Path):
        self.path, self.calls = path, []

    def write(self, message: str, project_id: str, as_of: str) -> str:
        self.calls.append(message)
        recording = json.loads(self.path.read_text())
        if (recording["project_id"], recording["as_of"]) != (project_id, as_of):
            raise WriterError(f"{self.path.name} records the brief for {recording['project_id']} as of "
                              f"{recording['as_of']}, not {project_id} as of {as_of}.")
        return answer_text(recording["response"])


class RecordedJudge:
    """Answers check 4's questions from a recorded judge answer for exactly those sentences, and counts its calls."""

    name = "recorded judge"

    def __init__(self, path: Path):
        self.path, self.calls = path, []

    def judge(self, questions: list[Question]) -> list[Judgement]:
        self.calls.append(list(questions))
        recording = json.loads(self.path.read_text()) if self.path.exists() else None
        asked = [question.sentence for question in questions]
        if recording is None or recording["asked"] != asked:
            raise JudgeError(f"The judge was asked about {asked}, and {self.path.name} answers "
                             f"{None if recording is None else recording['asked']}. Record it again: "
                             "uv run --script ops/agent/record.py --research --env-file .env")
        # The recording keeps the index each asked sentence had when it was recorded, so a judgement moves to the index
        # the same sentence has now, as when a test adds a sentence before it.
        content = json.loads(answer_text(recording["response"]))
        moved = dict(zip(recording["indexes"], (question.index for question in questions), strict=True))
        placed = [{**judgement, "index": moved.get(judgement["index"], judgement["index"])}
                  for judgement in content["judgements"]]
        return judgements({"choices": [{"message": {"content": json.dumps({"judgements": placed})}}]}, questions)
