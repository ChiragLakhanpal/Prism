"""Prompt Shields: each passage is scanned for a prompt attack when it is ingested, and the result is
kept (docs/PLAN.md section 6, "Guardrails"). A passage is data the agent reads, so a document that
carries instructions for a model must be caught before any answer cites it.

- PromptShields, live. Azure AI Content Safety's shieldPrompt operation on the Foundry resource,
  which judges each passage as a document. Its answer says whether it found an attack.
- PatternShield, offline. A stand-in that looks for the commonest attack phrasings, so the gate can
  prove that every passage gets a stored result and that a hit is counted. It is not Prompt Shields,
  and its name, kept with each result, says so.

A hit is never dropped: the passage stays, its result says an attack was found, the data readiness
measures count it, and search_passages leaves it out and says why.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from strata.knowledge.http import post_json


@dataclass(frozen=True)
class Scan:
    attack_detected: bool
    detail: str | None = None


class Shield(Protocol):
    name: str

    def scan(self, texts: list[str]) -> list[Scan]:
        """One result per text, in the same order."""


class ShieldError(RuntimeError):
    """The shield could not scan, so the run stops rather than keep passages with no result."""


# ── Offline ──────────────────────────────────────────────────────────────

ATTACKS = re.compile(
    r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|earlier)\s+"
    r"(?:instructions|prompts?|rules)\b"
    r"|\byou\s+are\s+now\s+(?:a|an|in)\b|\bsystem\s+prompt\b|\bjailbreak\b|\bdeveloper\s+mode\b", re.I)


class PatternShield:
    """The offline stand-in for Prompt Shields."""

    name = "offline stand-in (attack phrasings)"

    def scan(self, texts: list[str]) -> list[Scan]:
        results = []
        for text in texts:
            found = ATTACKS.search(text)
            results.append(Scan(bool(found), f"It found the phrase {found.group(0)!r}." if found else None))
        return results


# ── Live ─────────────────────────────────────────────────────────────────

Transport = Callable[[str, dict, dict], dict]  # (url, headers, body) -> the parsed JSON answer
API_VERSION = "2024-09-01"


def http_post(url: str, headers: dict, body: dict) -> dict:
    return post_json(url, headers, body, timeout=60, error=ShieldError, service="Prompt Shields")


def content_safety_endpoint(openai_endpoint: str) -> str:
    """The Content Safety endpoint of the Foundry resource whose Azure OpenAI endpoint is given:
    https://wb-strata.openai.azure.com/openai/v1 becomes https://wb-strata.cognitiveservices.azure.com."""
    found = re.match(r"https://([^./]+)\.(?:openai|services\.ai|cognitiveservices)\.azure\.com", openai_endpoint)
    if not found:
        raise ShieldError(f"I cannot tell the Foundry resource from {openai_endpoint!r}.")
    return f"https://{found.group(1)}.cognitiveservices.azure.com"


class PromptShields:
    """Azure AI Content Safety's Prompt Shields, one passage per document, a few documents a call."""

    name = "Prompt Shields"
    per_call = 3  # documents in one call: three passages of at most 500 tokens stay under 10,000 characters

    def __init__(self, endpoint: str, key: str, post: Transport = http_post):
        self.url = f"{endpoint.rstrip('/')}/contentsafety/text:shieldPrompt?api-version={API_VERSION}"
        self.headers = {"Ocp-Apim-Subscription-Key": key}
        self.post = post

    def scan(self, texts: list[str]) -> list[Scan]:
        results = []
        for start in range(0, len(texts), self.per_call):
            batch = texts[start:start + self.per_call]
            answer = self.post(self.url, self.headers, {"userPrompt": "", "documents": batch})
            analyses = answer.get("documentsAnalysis") or []
            if len(analyses) != len(batch):
                raise ShieldError(f"Prompt Shields judged {len(analyses)} of {len(batch)} passages.")
            results += [Scan(bool(analysis.get("attackDetected")),
                             "Prompt Shields found a document attack." if analysis.get("attackDetected") else None)
                        for analysis in analyses]
        return results
