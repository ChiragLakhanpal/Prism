"""Microsoft Foundry evaluations of the benchmark's answers (ticket 33; docs/PLAN.md section 10; spec,
"Evaluation").

The orchestrator returns tool calls that only the app can run (ADR 0003), so a Foundry run with the agent as its
target would stop at its first tool call. Instead the full gate scores the answers it recorded through the answer
contract as a dataset, one item per answer that kept at least one sentence: the question, the kept sentences, the
passages and records they cite as context, the tool calls the agent made, and the tools it was offered. Refusals
are left out: the must-refuse check scores them, and groundedness means nothing for a refusal.

evaluate() creates one evaluation with a "custom" data source config and an item_schema (Foundry answered
"Unknown discriminator" to azure_ai_source, as fairshare's docs/limits.md records), one azure_ai_evaluator per
evaluator in config/evaluations.toml, each judged by the deployment of the judge role, then one run over the items.
It waits for the run, reads every output item and counts, per evaluator, the answers scored, the answers that met
Foundry's own threshold, and their mean score from 1 to 5.

The client reuses ticket 13's Foundry client (strata.agent.foundry.http_call). It signs in with a Microsoft Entra
token: the project key gets 403 from the evaluations API, and the tenant blocks device-code sign-in, so
ops/evals/full_gate.py opens a browser for FOUNDRY_TENANT_ID. The REST shapes follow the evaluations API as its
documentation gives them; the first live run checks them (docs/workspace-catchup.md).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from strata.config import Evaluations
from strata.evals.scoring import Asked, kept

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "response": {"type": "string"},
        "context": {"type": "string"},
        "tool_calls": {"type": "array"},
        "tool_definitions": {"type": "array"},
    },
    "required": ["query", "response"],
}
DONE = ("completed", "failed", "canceled", "cancelled")


@dataclass(frozen=True)
class EvaluatorScore:
    key: str
    label: str
    scored: int
    met: int
    mean: float | None


@dataclass
class EvaluationRun:
    eval_id: str
    run_id: str
    deployment: str
    scores: list[EvaluatorScore] = field(default_factory=list)


def unscored(evaluation: EvaluationRun | None) -> list[EvaluatorScore]:
    """The evaluators Foundry scored for no answer, as when it did not take a built-in name or data mapping. The
    full gate fails naming each one, and its rows say it ran and scored nothing."""
    return [score for score in (evaluation.scores if evaluation is not None else ()) if not score.scored]


class EvaluationError(RuntimeError):
    """Foundry did not finish the evaluation run."""


def _source_text(item: dict) -> str:
    row = item.get("row") or {}
    text = row.get("text") if isinstance(row, dict) else None
    if text:
        return " ".join(str(text).split())
    import json

    return json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)


def dataset(asked: list[Asked], tools: list[dict] | None = None) -> list[dict]:
    """One item per answer that kept a sentence, in ITEM_SCHEMA's shape."""
    if tools is None:
        from strata.tools.registry import agent_tools

        tools = agent_tools()
    definitions = [{"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}
                   for tool in tools]
    items = []
    for answer in asked:
        if answer.question["kind"] == "refusals":
            continue
        sentences = kept(answer.events)
        if not sentences:
            continue
        sources = {data["id"]: data for kind, data in answer.events if kind == "evidence"}
        cited = list(dict.fromkeys(evidence for sentence in sentences for evidence in sentence.get("evidence_ids") or ()))
        items.append({
            "query": answer.question["question"],
            "response": " ".join(sentence["text"] for sentence in sentences),
            "context": "\n".join(f"[{evidence}] {_source_text(sources[evidence])}" for evidence in cited
                                 if evidence in sources),
            "tool_calls": [{"type": "tool_call", "tool_call_id": f"call_{number}", "name": call["tool"],
                            "arguments": call["arguments"]} for number, call in enumerate(answer.calls, 1)],
            "tool_definitions": definitions,
        })
    return items


def testing_criteria(evaluations: Evaluations, deployment: str) -> list[dict]:
    return [{"type": "azure_ai_evaluator", "name": evaluator.key, "evaluator_name": evaluator.builtin,
             "data_mapping": dict(evaluator.data_mapping), "initialization_parameters": {"deployment_name": deployment}}
            for evaluator in evaluations.evaluators]


def scores(output_items: list[dict], evaluations: Evaluations) -> list[EvaluatorScore]:
    """Per evaluator: the answers with a score, those that met Foundry's threshold, and the mean score."""
    found = []
    for evaluator in evaluations.evaluators:
        results = [result for item in output_items for result in item.get("results") or ()
                   if result.get("name") == evaluator.key and isinstance(result.get("score"), int | float)]
        met = sum(1 for result in results if result.get("passed") is True or (
            result.get("passed") is None and str(result.get("label", "")).lower() == "pass"))
        mean = round(sum(result["score"] for result in results) / len(results), 2) if results else None
        found.append(EvaluatorScore(evaluator.key, evaluator.label, len(results), met, mean))
    return found


def evaluate(client, items: list[dict], evaluations: Evaluations, deployment: str, name: str,
             poll_seconds: float, wait_seconds: float, sleep: Callable[[float], None] = time.sleep,
             clock: Callable[[], float] = time.monotonic) -> EvaluationRun:
    created = client.create_eval({"name": name, "data_source_config": {
        "type": "custom", "item_schema": ITEM_SCHEMA, "include_sample_schema": False},
        "testing_criteria": testing_criteria(evaluations, deployment)})
    run = client.create_run(created["id"], {"name": name, "data_source": {
        "type": "jsonl", "source": {"type": "file_content", "content": [{"item": item} for item in items]}}})
    started = clock()
    status = run.get("status")
    while status not in DONE:
        if clock() - started > wait_seconds:
            raise EvaluationError(f"Foundry did not finish evaluation run {run['id']} within {wait_seconds:.0f} "
                                  "seconds.")
        sleep(poll_seconds)
        status = client.get_run(created["id"], run["id"]).get("status")
    if status != "completed":
        raise EvaluationError(f"Foundry's evaluation run {run['id']} ended {status}.")
    return EvaluationRun(created["id"], run["id"], deployment,
                         scores(client.output_items(created["id"], run["id"]), evaluations))


class FoundryEvaluations:
    """The Foundry project's evaluations API, with an Entra token (ticket 13's http_call)."""

    def __init__(self, endpoint: str, api_version: str, token: Callable[[], str], call=None):
        from strata.agent.foundry import http_call

        self.endpoint, self.api_version, self.token = endpoint.rstrip("/"), api_version, token
        self.call = call or http_call

    def _url(self, path: str, query: str = "") -> str:
        return f"{self.endpoint}/openai/evals{path}?api-version={self.api_version}{query}"

    def _do(self, method: str, url: str, body: dict | None = None) -> dict:
        return self.call(method, url, {"Authorization": f"Bearer {self.token()}"}, body)

    def create_eval(self, body: dict) -> dict:
        return self._do("POST", self._url(""), body)

    def create_run(self, eval_id: str, body: dict) -> dict:
        return self._do("POST", self._url(f"/{eval_id}/runs"), body)

    def get_run(self, eval_id: str, run_id: str) -> dict:
        return self._do("GET", self._url(f"/{eval_id}/runs/{run_id}"))

    def output_items(self, eval_id: str, run_id: str) -> list[dict]:
        found, after = [], ""
        while True:
            page = self._do("GET", self._url(f"/{eval_id}/runs/{run_id}/output_items", f"&limit=100{after}"))
            found += page.get("data") or []
            if not page.get("has_more") or not page.get("last_id"):
                return found
            after = f"&after={page['last_id']}"
