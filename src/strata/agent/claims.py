"""The agent's answer: claims as JSON, one sentence each (spec, "The agent and the answer contract").

The agent ends every run with one JSON object, {"claims": [...]}. Each claim has:

- sentence       one sentence, as the person will read it
- kind           record, quote, advice or summary
- evidence_ids   the evidence ids of the rows and passages it rests on, as the tools returned them
- numbers        each number the sentence states, as written in it
- dates          each date the sentence states, as written in it
- quote          {text, passage_id} when the sentence quotes a passage, else null

parse_claims() reads that object and refuses anything else with ClaimsError. A passage id may come
bare (31525018/v1/54) or as its evidence id (strata.gold.passage:31525018/v1/54); both mean the same
passage, and a quote's passage always counts among the claim's evidence ids.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from strata.tools.search_passages import TABLE as PASSAGES

KINDS = ("record", "quote", "advice", "summary")
FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


class ClaimsError(ValueError):
    """The agent's answer is not claims as JSON in the agreed shape."""


@dataclass(frozen=True)
class Quote:
    text: str
    evidence_id: str


@dataclass(frozen=True)
class Claim:
    sentence: str
    kind: str
    evidence_ids: tuple[str, ...]
    numbers: tuple[str, ...] = ()
    dates: tuple[str, ...] = ()
    quote: Quote | None = None


def passage_evidence_id(passage_id: str) -> str:
    """A passage's evidence id, from its bare id or from the evidence id itself."""
    passage_id = passage_id.strip()
    return passage_id if ":" in passage_id else f"{PASSAGES}:{passage_id}"


def _texts(claim: dict, key: str, where: str) -> tuple[str, ...]:
    value = claim.get(key) or []
    if not isinstance(value, list) or not all(isinstance(item, str | int | float) for item in value):
        raise ClaimsError(f"{where}'s {key} must be a list of text.")
    return tuple(str(item) for item in value)


def _claim(claim, number: int) -> Claim:
    where = f"Claim {number}"
    if not isinstance(claim, dict):
        raise ClaimsError(f"{where} is not an object.")
    sentence = claim.get("sentence")
    if not isinstance(sentence, str) or not sentence.strip():
        raise ClaimsError(f"{where} has no sentence.")
    kind = claim.get("kind")
    if kind not in KINDS:
        raise ClaimsError(f"{where}'s kind is {kind!r}, not one of {', '.join(KINDS)}.")
    evidence = list(_texts(claim, "evidence_ids", where))
    quote = claim.get("quote")
    if quote is not None:
        if not isinstance(quote, dict) or not isinstance(quote.get("text"), str) \
                or not isinstance(quote.get("passage_id"), str):
            raise ClaimsError(f"{where}'s quote must have its text and its passage_id.")
        quote = Quote(quote["text"], passage_evidence_id(quote["passage_id"]))
        if quote.evidence_id not in evidence:
            evidence.append(quote.evidence_id)
    return Claim(sentence.strip(), kind, tuple(dict.fromkeys(evidence)), _texts(claim, "numbers", where),
                 _texts(claim, "dates", where), quote)


def parse_claims(text: str) -> list[Claim]:
    """The claims in the agent's final answer, in the order it wrote them."""
    fenced = FENCE.match(text or "")
    try:
        answer = json.loads(fenced.group(1) if fenced else text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ClaimsError(f"The answer is not JSON: {error}.") from error
    if not isinstance(answer, dict) or not isinstance(answer.get("claims"), list):
        raise ClaimsError("The answer must be an object with a list of claims.")
    return claims_from(answer["claims"])


def claims_from(items) -> list[Claim]:
    """Claims from a list in the agreed shape, such as a writer's claims for one note."""
    if not isinstance(items, list):
        raise ClaimsError("The claims must be a list.")
    return [_claim(claim, number) for number, claim in enumerate(items, 1)]
