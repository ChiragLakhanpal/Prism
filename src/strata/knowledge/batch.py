"""The batch model: bulk extraction on Azure OpenAI's Global Batch (docs/PLAN.md section 2).

config/models.toml's batch role names the deployment (gpt-5.4-nano). A batch is a list of requests, each
a chat completion with the rules in its instructions and the data in its message (so Prompt Shields does
not read the rules as an attack; spec, "Security and privacy"), asked for one JSON object, and keyed by
a custom_id. Assertions (strata.knowledge.assertions) use it now; proposed lessons (ticket 29) reuse it.

- AzureOpenAIBatch, live. It writes the requests as one JSONL file, uploads it through the v1 API's files
  operation (purpose batch), creates a batch on the chat completions endpoint with a 24-hour window, waits
  for it within a time limit, and reads its output file. A batch that has not finished in time raises
  BatchPending with the batch's id. The run keeps that id with the requests in bronze and, on a later run,
  waits for the same batch instead of asking, and paying, again (resume); a batch that failed, expired or
  was cancelled is asked again.
- HeldAnswers asks nothing. A run with no live model, such as the nightly job before ticket 43 gives it
  the Azure OpenAI keys, uses it to replay the answers bronze holds from the batch role's deployment, so
  what the live model read is kept.
- RecordedBatch, offline. It answers each request with the line a recording holds for its custom_id
  (tests/fixtures/azure/batch_assertions.json), in the Batch API's output-line shape, so the gate runs the
  same reading code as the live run. A request the recording does not hold gets no answer.
  ops/assertions/batch_live.py --record writes the recording from a live batch with recording(), which
  keeps the assertion planted by hand, so the gate still proves the quote check rejects it.

from_environment() gives the live model when AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are set, and
None otherwise.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

RECORDING = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "azure" / "batch_assertions.json"
ENDPOINT = "/chat/completions"
WINDOW = "24h"
FINISHED = ("completed", "failed", "expired", "cancelled")
ENDED_WITHOUT_ANSWERS = ("failed", "expired", "cancelled")  # a held batch in one of these is asked again


@dataclass(frozen=True)
class Request:
    """One request of a batch: its key, the rules, and the data as one JSON message."""

    custom_id: str
    instructions: str
    data: dict

    def body(self, deployment: str) -> dict:
        return {"model": deployment, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": self.instructions},
                             {"role": "user", "content": json.dumps(self.data, ensure_ascii=False, sort_keys=True)}]}

    def digest(self, deployment: str) -> str:
        """SHA-256 of what the model is asked, so an unchanged request is not asked again."""
        return hashlib.sha256(json.dumps(self.body(deployment), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Answer:
    """The model's answer to one request: its message's content (JSON text), or why there is none."""

    custom_id: str
    content: str | None
    error: str | None = None


class BatchModel(Protocol):
    name: str  # what reads, kept with each answer and each assertion
    deployment: str  # the deployment the requests name

    def answer(self, requests: list[Request], resume: str | None = None) -> list[Answer]:
        """The answers it has, one per request it answered, in any order. resume names a batch an earlier run
        sent these requests in, which is still running: the model waits for it instead of asking again."""


class BatchError(RuntimeError):
    """The Batch API refused, or answered in a shape it was not asked for."""


class BatchPending(BatchError):
    """The batch did not finish within the time the run gives it. A later run waits for it by its id."""

    def __init__(self, message: str, batch_id: str | None = None):
        super().__init__(message)
        self.batch_id = batch_id


def request_line(request: Request, deployment: str) -> dict:
    """One line of a batch's input file."""
    return {"custom_id": request.custom_id, "method": "POST", "url": ENDPOINT, "body": request.body(deployment)}


def read_lines(lines: list[dict]) -> list[Answer]:
    """The answers in a batch's output lines: each line's custom_id and its chat completion's content."""
    answers = []
    for line in lines:
        custom_id = line.get("custom_id")
        if not custom_id:
            raise BatchError("A line of the batch's output has no custom_id.")
        response = line.get("response") or {}
        if line.get("error") or response.get("status_code") != 200:
            error = line.get("error")
            message = (error.get("message") if isinstance(error, dict) else error) or \
                f"status {response.get('status_code')}"
            answers.append(Answer(custom_id, None, str(message)))
            continue
        try:
            content = response["body"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise BatchError(f"The answer to {custom_id} is not a chat completion: {error}") from error
        answers.append(Answer(custom_id, content))
    return answers


# ── Offline ──────────────────────────────────────────────────────────────

class RecordedBatch:
    """The offline stand-in: the answers a recording holds, for the requests it holds them for."""

    def __init__(self, path: Path = RECORDING, deployment: str | None = None):
        from strata.config import load_models

        held = json.loads(path.read_text())
        self.recorded = bool(held.get("recorded"))
        self.deployment = deployment or load_models()["batch"].deployment
        self.name = f"{self.deployment} ({'recorded' if self.recorded else 'written by hand in its shape'})"
        self.lines = {line["custom_id"]: line for line in held["lines"]}

    def answer(self, requests: list[Request], resume: str | None = None) -> list[Answer]:
        return read_lines([self.lines[request.custom_id] for request in requests if request.custom_id in self.lines])


class HeldAnswers:
    """Asks nothing: a run with it uses only the answers bronze already holds from the batch role's deployment.
    Its name is the deployment's, as the live model's is, so those answers are found by what read them."""

    def __init__(self, deployment: str | None = None):
        from strata.config import load_models

        self.deployment = self.name = deployment or load_models()["batch"].deployment

    def answer(self, requests: list[Request], resume: str | None = None) -> list[Answer]:
        return []


RECORDED_ABOUT = ("The batch role's answers (config/models.toml, on Global Batch) to the assertion requests for "
                  "P130164's PAD, its ICR and its two ICR Reviews, as lines of the Batch API's output file, keyed by "
                  "custom_id, recorded by ops/assertions/batch_live.py --record. One assertion, marked planted, was "
                  "written by hand with a quote that is not on its page, so the gate proves the check rejects it; "
                  "each new recording keeps it.")


def _planted(line: dict) -> list[dict]:
    """The assertions planted by hand in one line of a recording."""
    try:
        content = line["response"]["body"]["choices"][0]["message"]["content"]
        return [item for item in json.loads(content or "{}").get("assertions", []) if "planted" in item]
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return []


def recording(lines: list[dict], held: dict, recorded_on: str) -> dict:
    """A new recording of a batch's output lines, with each assertion planted in the recording held kept in
    the answer to the same request, after the model's own."""
    planted = {line["custom_id"]: _planted(line) for line in held.get("lines", [])}
    answered = {line.get("custom_id") for line in lines}
    missing = [custom_id for custom_id, items in planted.items() if items and custom_id not in answered]
    if missing:
        raise BatchError(f"The batch gave no answer to {', '.join(missing)}, which holds the planted assertion. "
                         f"Nothing was written.")
    written = []
    for line in lines:
        keep = planted.get(line.get("custom_id")) or []
        if keep:
            line = json.loads(json.dumps(line))  # a copy, so the batch's own line is left as it came
            message = line["response"]["body"]["choices"][0]["message"]
            content = json.loads(message["content"] or "{}")
            content["assertions"] = list(content.get("assertions") or []) + keep
            message["content"] = json.dumps(content, ensure_ascii=False)
        written.append(line)
    return {"about": RECORDED_ABOUT, "recorded": recorded_on, "lines": written}


# ── Live ─────────────────────────────────────────────────────────────────

# (method, url, headers, body, content type) -> the answer's bytes
Transport = Callable[[str, str, dict, bytes | None, str | None], bytes]


def http_request(method: str, url: str, headers: dict, body: bytes | None, content_type: str | None) -> bytes:
    request = urllib.request.Request(url, method=method, data=body,
                                     headers={**headers, **({"Content-Type": content_type} if content_type else {})})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as refused:
        raise BatchError(f"Azure OpenAI answered {refused.code}: "
                         f"{refused.read().decode(errors='replace')[:300]}") from refused
    except urllib.error.URLError as unreachable:
        raise BatchError(f"I could not reach Azure OpenAI: {unreachable.reason}") from unreachable


def multipart(fields: dict[str, str], file_name: str, file_bytes: bytes) -> tuple[bytes, str]:
    """A multipart/form-data body with plain fields and one file, as the files operation takes it."""
    boundary = f"strata-{uuid.uuid4().hex}"
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
             for name, value in fields.items()]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
                 f"Content-Type: application/jsonl\r\n\r\n".encode() + file_bytes + b"\r\n")
    return b"".join(parts) + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


class AzureOpenAIBatch:
    """The batch role's deployment on Azure OpenAI's Global Batch, through the v1 API."""

    def __init__(self, endpoint: str, key: str, deployment: str, transport: Transport = http_request,
                 sleep: Callable[[float], None] = time.sleep, wait_seconds: float = 3600, poll_seconds: float = 60):
        self.base = endpoint.rstrip("/")
        self.headers = {"api-key": key}
        self.deployment = self.name = deployment
        self.transport, self.sleep = transport, sleep
        self.wait_seconds, self.poll_seconds = wait_seconds, poll_seconds

    def _json(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        answer = self.transport(method, f"{self.base}{path}", self.headers, data, None if body is None else
                                "application/json")
        try:
            return json.loads(answer)
        except ValueError as error:
            raise BatchError(f"Azure OpenAI's answer to {method} {path} is not JSON.") from error

    def answer(self, requests: list[Request], resume: str | None = None) -> list[Answer]:
        return read_lines(self.output_lines(requests, resume))

    def _submit(self, requests: list[Request]) -> dict:
        """Upload the requests as one JSONL file and create a batch of them."""
        lines = "\n".join(json.dumps(request_line(request, self.deployment), ensure_ascii=False)
                          for request in requests) + "\n"
        body, content_type = multipart({"purpose": "batch"}, "requests.jsonl", lines.encode())
        uploaded = json.loads(self.transport("POST", f"{self.base}/files", self.headers, body, content_type))
        return self._json("POST", "/batches", {"input_file_id": uploaded["id"], "endpoint": ENDPOINT,
                                               "completion_window": WINDOW})

    def output_lines(self, requests: list[Request], resume: str | None = None) -> list[dict]:
        """The batch's output file, one line per request it answered, as the Batch API wrote it. With resume,
        the batch an earlier run sent these requests in is waited for, unless it ended with no answers."""
        if not requests:
            return []
        batch = self._json("GET", f"/batches/{resume}") if resume else None
        if batch is None or batch.get("status") in ENDED_WITHOUT_ANSWERS:
            batch = self._submit(requests)
        waited = 0.0
        while batch.get("status") not in FINISHED:
            if waited >= self.wait_seconds:
                raise BatchPending(f"Batch {batch.get('id')} was still {batch.get('status')} after {waited:.0f} "
                                   f"seconds.", batch_id=batch.get("id"))
            self.sleep(self.poll_seconds)
            waited += self.poll_seconds
            batch = self._json("GET", f"/batches/{batch['id']}")
        if batch["status"] != "completed" or not batch.get("output_file_id"):
            raise BatchError(f"Batch {batch.get('id')} ended {batch['status']} with no output file.")
        output = self.transport("GET", f"{self.base}/files/{batch['output_file_id']}/content", self.headers, None,
                                None).decode()
        return [json.loads(line) for line in output.splitlines() if line.strip()]


def from_environment(environ: Mapping[str, str] = os.environ) -> AzureOpenAIBatch | None:
    """The live batch model, with the deployment of the model file's batch role, or None without its keys."""
    from strata.config import load_models

    endpoint, key = environ.get("AZURE_OPENAI_ENDPOINT", "").strip(), environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not (endpoint and key):
        return None
    return AzureOpenAIBatch(endpoint, key, load_models()["batch"].deployment)
