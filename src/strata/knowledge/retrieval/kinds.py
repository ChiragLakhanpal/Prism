"""The kind of question a question is (config/retrieval.toml): the kind whose words the question holds most
often, the first in the file on a tie, and the fallback when it holds none. A passage report and a
ranking-lower decision are about one kind, so a reviewer's decision moves a passage only for questions like
the ones in its reports."""

from __future__ import annotations

from collections import Counter

from strata.config import RetrievalLists, load_retrieval
from strata.knowledge.embed import terms


def query_kind(question: str, lists: RetrievalLists | None = None) -> str:
    lists = lists or load_retrieval()
    held = Counter(terms(question))
    best, most = lists.fallback, 0
    for kind in lists.query_kinds:
        found = sum(held[word] for word in kind.words)
        if found > most:
            best, most = kind.key, found
    return best


def kinds(lists: RetrievalLists | None = None) -> tuple[str, ...]:
    return tuple(kind.key for kind in (lists or load_retrieval()).query_kinds)
