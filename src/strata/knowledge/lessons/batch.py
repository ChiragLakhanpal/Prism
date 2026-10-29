"""The batch model the lesson extractor sends documents to (docs/PLAN.md section 2: the batch role's deployment on Global
Batch for bulk extraction; config/models.toml's batch role names the deployment).

A batch takes requests in the Batch API's line shape ({custom_id, method, url, body}) and answers each,
up to a day later, with its custom_id and either the model's text or an error. Two adapters:

- AzureGlobalBatch, live: uploads the requests as a JSON Lines file, creates a batch with a 24-hour
  completion window, and later reads its output and error files. It is a workspace step
  (docs/workspace-catchup.md), since the gate's machine has no key.
- RecordedBatch, offline: answers from tests/fixtures/azure/lesson_batch.json, written by hand in the
  shape the Batch API's output file documents. A request it holds no answer for fails with
  not_recorded, so the fixture never makes up what a model said about a document.
"""

from __future__ import annotations

import io
import json
import os
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[4]
RECORDED = ROOT / "tests" / "fixtures" / "azure" / "lesson_batch.json"
NOT_RECORDED = "not_recorded"


class BatchError(RuntimeError):
    """The batch service refused or could not be reached, so the run stops and says which."""


@dataclass(frozen=True)
class Answer:
    """One request's answer: the model's text, or why there is none."""

    custom_id: str
    text: str | None = None
    error: str | None = None


class Batch(Protocol):
    model: str

    def submit(self, requests: list[dict]) -> str:
        """Send the requests as one batch, and return the batch's id."""

    def results(self, batch_id: str, custom_ids: list[str]) -> list[Answer] | None:
        """Each request's answer, or None while the batch is still running."""


def text_of(response: Mapping) -> str | None:
    """The model's text in one line of an output file, from its chat completion."""
    body = (response.get("response") or {}).get("body") or {}
    choices = body.get("choices") or []
    return (choices[0].get("message") or {}).get("content") if choices else None


class RecordedBatch:
    """The batch model's recorded answers, for the gate and the fixture."""

    def __init__(self, path: Path = RECORDED):
        recorded = json.loads(Path(path).read_text())
        self.model = recorded["model"]
        self.lines = {line["custom_id"]: line for line in recorded["outputs"]}

    def submit(self, requests: list[dict]) -> str:
        return f"recorded-{uuid.uuid5(uuid.NAMESPACE_URL, ','.join(r['custom_id'] for r in requests)).hex[:12]}"

    def results(self, batch_id: str, custom_ids: list[str]) -> list[Answer]:
        answers = []
        for custom_id in custom_ids:
            line = self.lines.get(custom_id)
            if line is None:
                answers.append(Answer(custom_id, error=NOT_RECORDED))
            elif (line.get("response") or {}).get("status_code") != 200:
                answers.append(Answer(custom_id, error=json.dumps(line.get("error") or line.get("response"))))
            else:
                answers.append(Answer(custom_id, text=text_of(line)))
        return answers


class AzureGlobalBatch:
    """Azure OpenAI's Batch API on a Global Batch deployment (the v1 API's files and batches)."""

    window = "24h"

    def __init__(self, endpoint: str, key: str, model: str, timeout: int = 120):
        self.base = endpoint.rstrip("/")
        self.headers = {"api-key": key}
        self.model, self.timeout = model, timeout

    def _call(self, method: str, path: str, body: bytes | None = None, content_type: str | None = None) -> bytes:
        headers = {**self.headers, **({"Content-Type": content_type} if content_type else {})}
        request = urllib.request.Request(f"{self.base}{path}", data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as refused:
            raise BatchError(f"Azure OpenAI's Batch API answered {refused.code}: "
                             f"{refused.read().decode(errors='replace')[:300]}") from refused
        except urllib.error.URLError as unreachable:
            raise BatchError(f"I could not reach Azure OpenAI's Batch API: {unreachable.reason}") from unreachable

    def submit(self, requests: list[dict]) -> str:
        lines = "".join(json.dumps(request, ensure_ascii=False) + "\n" for request in requests).encode()
        boundary = uuid.uuid4().hex
        form = io.BytesIO()
        form.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\nbatch\r\n".encode())
        form.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"lessons.jsonl\"\r\n"
                   "Content-Type: application/jsonl\r\n\r\n".encode() + lines + b"\r\n")
        form.write(f"--{boundary}--\r\n".encode())
        uploaded = json.loads(self._call("POST", "/files", form.getvalue(), f"multipart/form-data; boundary={boundary}"))
        created = json.loads(self._call("POST", "/batches", json.dumps({
            "input_file_id": uploaded["id"], "endpoint": "/chat/completions",
            "completion_window": self.window}).encode(), "application/json"))
        return created["id"]

    def results(self, batch_id: str, custom_ids: list[str]) -> list[Answer] | None:
        batch = json.loads(self._call("GET", f"/batches/{batch_id}"))
        if batch.get("status") not in ("completed", "failed", "expired", "cancelled"):
            return None
        found: dict[str, Answer] = {}
        for file_key in ("output_file_id", "error_file_id"):
            if batch.get(file_key):
                for raw in self._call("GET", f"/files/{batch[file_key]}/content").decode().splitlines():
                    if raw.strip():
                        line = json.loads(raw)
                        ok = (line.get("response") or {}).get("status_code") == 200
                        found[line["custom_id"]] = (Answer(line["custom_id"], text=text_of(line)) if ok else
                                                    Answer(line["custom_id"], error=json.dumps(line.get("error"))))
        return [found.get(custom_id, Answer(custom_id, error=f"batch {batch.get('status')}")) for custom_id in custom_ids]


def from_environment(environ: Mapping[str, str] = os.environ) -> AzureGlobalBatch | None:
    """The live batch model when AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are set, else None."""
    from strata.config import load_models

    endpoint, key = environ.get("AZURE_OPENAI_ENDPOINT", "").strip(), environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not (endpoint and key):
        return None
    # The v1 endpoint, as the embeddings and the supplier judge use it: files and batches sit beside chat/completions.
    return AzureGlobalBatch(endpoint, key, load_models()["batch"].deployment)
