"""The model that decides the uncertain middle of name matching for suppliers (docs/PLAN.md section 5).

A pair whose match probability falls between config/thresholds.toml's model_min_probability and
auto_merge_min_probability goes to a judge, which says merge, no merge or unsure, how sure it is, and
why. A decision stands only when the judge is at least model_confidence_min sure; any other pair goes
to a person. The judge sees the two sides' names, countries, projects and contracts, and nothing that
scores or ranks a supplier.

- AzureOpenAIJudge, live: the deployment of the role config/models.toml's [supplier_matching] names
  (judge_role, the draft role), on Azure OpenAI's chat completions, asked for one JSON answer per pair.
  The rules are in the instructions and the pair is data in the message, so Prompt Shields does not
  read the rules as an attack (spec, "Security and privacy").
- SameNameStandIn, offline: merges a pair whose names are the same once normalized and leaves every
  other pair to a person. It is not a model, and its name, kept with each decision in
  strata.ops.supplier_pairs, says so.

from_environment() gives the live judge when AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are set,
and None otherwise; with no judge, the pairs in the middle wait for a person (review_reason no_model).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from strata.knowledge.http import post_json
from strata.knowledge.suppliers.names import normalize

DECISIONS = ("merge", "no_merge", "unsure")


@dataclass(frozen=True)
class Side:
    name: str
    country: str | None
    projects: tuple[str, ...]
    contracts: tuple[str, ...]


@dataclass(frozen=True)
class Question:
    pair_id: str
    left: Side
    right: Side


@dataclass(frozen=True)
class Judgement:
    decision: str  # merge, no_merge or unsure
    confidence: float  # from 0 to 1
    reason: str


class Judge(Protocol):
    name: str

    def decide(self, questions: list[Question]) -> list[Judgement]:
        """One judgement per question, in the same order."""


class JudgeError(RuntimeError):
    """The judge could not answer, or answered in a shape it was not asked for."""


# ── Offline ──────────────────────────────────────────────────────────────

class SameNameStandIn:
    """The offline stand-in for the judge."""

    name = "offline stand-in (same name once normalized)"

    def decide(self, questions: list[Question]) -> list[Judgement]:
        judged = []
        for question in questions:
            if normalize(question.left.name) == normalize(question.right.name):
                judged.append(Judgement("merge", 0.95, "The names are the same once legal forms, accents and "
                                                       "punctuation are taken off."))
            else:
                judged.append(Judgement("unsure", 0.5, "The names differ, and the stand-in leaves every such "
                                                       "pair to a person."))
        return judged


# ── Live ─────────────────────────────────────────────────────────────────

Transport = Callable[[str, dict, dict], dict]  # (url, headers, body) -> the parsed JSON answer

INSTRUCTIONS = """You decide whether two rows of World Bank procurement records name the same supplier.
Each row gives a supplier's name as a contract award or an award notice writes it, its country, its
projects and its contracts. Names may differ in legal form (LTD, LIMITED, PVT, S.A.), punctuation,
accents, word order, and may be cut off at 40 characters in records from FY2001 to FY2016.
Two firms with similar names in one country are often different firms: a shared project or contract
is evidence, a shared first word is not. Never judge a supplier's quality, size or record.
Answer with one JSON object and nothing else: {"decision": "merge" | "no_merge" | "unsure",
"confidence": a number from 0 to 1, "reason": one sentence}. Say unsure when the rows do not settle it."""


def http_post(url: str, headers: dict, body: dict) -> dict:
    return post_json(url, headers, body, timeout=60, error=JudgeError, service="Azure OpenAI")


def _side(side: Side) -> dict:
    return {"name": side.name, "country": side.country, "projects": list(side.projects),
            "contracts": list(side.contracts)}


def _judgement(answer: dict) -> Judgement:
    try:
        content = json.loads(answer["choices"][0]["message"]["content"])
        decision, confidence, reason = content["decision"], float(content["confidence"]), str(content["reason"])
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise JudgeError(f"Azure OpenAI gave an answer I cannot read as a judgement: {error}") from error
    if decision not in DECISIONS or not 0 <= confidence <= 1:
        raise JudgeError(f"Azure OpenAI gave the decision {decision!r} with confidence {confidence}; I asked for "
                         f"one of {', '.join(DECISIONS)} with a confidence from 0 to 1.")
    return Judgement(decision, confidence, reason)


class AzureOpenAIJudge:
    """The judge role's deployment on Azure OpenAI."""

    def __init__(self, endpoint: str, key: str, deployment: str, post: Transport = http_post):
        self.url = f"{endpoint.rstrip('/')}/chat/completions"
        self.headers = {"api-key": key}
        self.name, self.post = deployment, post

    def decide(self, questions: list[Question]) -> list[Judgement]:
        judged = []
        for question in questions:
            pair = {"first": _side(question.left), "second": _side(question.right)}
            answer = self.post(self.url, self.headers, {
                "model": self.name, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": INSTRUCTIONS},
                             {"role": "user", "content": json.dumps(pair, ensure_ascii=False)}]})
            judged.append(_judgement(answer))
        return judged


def from_environment(environ: Mapping[str, str] = os.environ) -> AzureOpenAIJudge | None:
    """The live judge, with the deployment of the role the model file names, or None without its keys."""
    from strata.config import load_models, load_supplier_matching

    endpoint, key = environ.get("AZURE_OPENAI_ENDPOINT", "").strip(), environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not (endpoint and key):
        return None
    return AzureOpenAIJudge(endpoint, key, load_models()[load_supplier_matching().judge_role].deployment)
