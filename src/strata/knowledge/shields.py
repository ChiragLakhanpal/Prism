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

held_back() is the one rule for a tool that would hand a passage's words to the agent: a passage with a
stored attack, or with no stored result at all, is kept from the agent, under the reason code its coverage
line counts it by (LEFT_OUT; config/tools.toml lists the codes under each tool's reasons). search_passages
leaves such a passage out; get_disagreements gives a side that rests on one without its words (ticket 64).
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


# ── What a stored result means to a tool ─────────────────────────────────

ATTACK_FOUND, NOT_SCREENED = "prompt_shields_hit", "not_screened"
LEFT_OUT = (ATTACK_FOUND, NOT_SCREENED)  # in the order a coverage line lists them


def held_back(attack_detected) -> str | None:
    """Why a passage's words are kept from the agent, as a coverage line's reason code, or None when Prompt Shields
    screened it and found no attack. The stored result arrives typed, or as text."""
    if attack_detected is None or attack_detected == "":
        return NOT_SCREENED
    found = attack_detected if isinstance(attack_detected, bool) else str(attack_detected).lower() == "true"
    return ATTACK_FOUND if found else None


def coverage_entries(left_out: dict[str, list[str]]) -> list[dict]:
    """The coverage line's entries for the passages a tool kept from the agent, by reason code, each with its count
    and its passages' evidence ids, in LEFT_OUT's order; a reason with no passage gives no entry."""
    return [{"reason": reason, "count": len(left_out[reason]), "evidence_ids": left_out[reason]}
            for reason in LEFT_OUT if left_out.get(reason)]


# ── Offline ──────────────────────────────────────────────────────────────

ATTACKS = re.compile(
    r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|earlier)\s+"
    r"(?:instructions|prompts?|rules)\b"
    r"|\byou\s+are\s+now\s+(?:a|an|in)\b|\bsystem\s+prompt\b|\bjailbreak\b|\bdeveloper\s+mode\b", re.I)


class PatternShield:
    """The offline stand-in for Prompt Shields."""

    name = "the offline stand-in for Prompt Shields"  # the measures' sentences name it this way

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
