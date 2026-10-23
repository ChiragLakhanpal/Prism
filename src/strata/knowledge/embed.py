"""Embeddings: each passage, with its short header in front, becomes a vector for hybrid search
(docs/PLAN.md section 5). config/models.toml's embed role names the deployment and the vector size.

- AzureOpenAIEmbeddings, live. text-embedding-3-large on Azure OpenAI at 1,024 dimensions, through the
  v1 API's embeddings operation, many passages a call.
- HashedWords, offline. A stand-in that hashes each word and each pair of words into a vector of the
  same size, so the same words give nearby vectors. The gate's fixture search runs on it. It is not
  a language model, and its name, kept with each vector, says so.

EMBEDDERS names each adapter. A vector is kept with the model that made it, and the run embeds only
the passage texts that model has not embedded yet.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Protocol


class Embedder(Protocol):
    name: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """One vector per text, in the same order."""


class EmbedError(RuntimeError):
    """The embedding model could not embed, so the run stops rather than keep passages with no vector."""


# ── Offline ──────────────────────────────────────────────────────────────

WORD = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """A word without its plural or its -ing, so rates and rate, or rebidding and rebid, meet."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ing") and len(word) > 5:
        word = word[:-3]
        return word[:-1] if len(word) > 2 and word[-1] == word[-2] and word[-1] not in "ls" else word
    if word.endswith("s") and not word.endswith(("ss", "us", "is")) and len(word) > 3:
        return word[:-1]
    return word


def terms(text: str) -> list[str]:
    """A text's words in lower case, each stemmed: the words both the stand-in and keyword search match on."""
    return [stem(word) for word in WORD.findall(text.lower())]


class HashedWords:
    """The offline stand-in for the embedding model."""

    name = "offline stand-in (hashed words)"

    def __init__(self, dimensions: int = 1024):
        self.dimensions = dimensions

    def _slot(self, feature: str) -> tuple[int, float]:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        number = int.from_bytes(digest, "big")
        return number % self.dimensions, 1.0 if number >> 63 else -1.0

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            words = terms(text)
            for feature in words + [f"{a} {b}" for a, b in zip(words, words[1:])]:
                slot, sign = self._slot(feature)
                vector[slot] += sign
            size = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / size for value in vector])
        return vectors


# ── Live ─────────────────────────────────────────────────────────────────

Transport = Callable[[str, dict, dict], dict]  # (url, headers, body) -> the parsed JSON answer


def http_post(url: str, headers: dict, body: dict, timeout: int = 120) -> dict:
    request = urllib.request.Request(url, method="POST", data=json.dumps(body).encode("utf-8"),
                                     headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        raise EmbedError(f"Azure OpenAI answered {error.code}: {error.read().decode(errors='replace')[:300]}") from error
    except urllib.error.URLError as error:
        raise EmbedError(f"I could not reach Azure OpenAI: {error.reason}") from error


class AzureOpenAIEmbeddings:
    """text-embedding-3-large (or whichever deployment config/models.toml names) on Azure OpenAI."""

    per_call = 64  # passages in one call, each at most 500 tokens, well under the model's limits

    def __init__(self, endpoint: str, key: str, deployment: str, dimensions: int, post: Transport = http_post):
        self.url = f"{endpoint.rstrip('/')}/embeddings"
        self.headers = {"api-key": key}
        self.name, self.dimensions, self.post = deployment, dimensions, post

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), self.per_call):
            batch = texts[start:start + self.per_call]
            answer = self.post(self.url, self.headers, {"model": self.name, "input": batch,
                                                        "dimensions": self.dimensions})
            data = sorted(answer.get("data") or [], key=lambda item: item["index"])
            if len(data) != len(batch) or any(len(item["embedding"]) != self.dimensions for item in data):
                raise EmbedError(f"Azure OpenAI gave {len(data)} vectors for {len(batch)} passages, or vectors "
                                 f"that are not {self.dimensions} long.")
            vectors += [item["embedding"] for item in data]
        return vectors


EMBEDDERS = {HashedWords.name: HashedWords, "azure-openai": AzureOpenAIEmbeddings}


def offline() -> HashedWords:
    """The stand-in, at the vector size config/models.toml names."""
    from strata.config import load_models

    return HashedWords(load_models()["embed"].dimensions)
