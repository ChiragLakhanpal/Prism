"""Hybrid search over the passages, by words and by meaning, with reranking (docs/PLAN.md section 5).

A searcher takes a query and its filters and gives back the passages it ranks highest, by passage id,
with how many matched. The tool (src/strata/tools/search_passages.py) then reads those passages from
strata.gold.passage as the viewer, so the app holds every passage an answer relies on (ADR 0003).

- AiSearch, live. The Delta Sync index over strata.gold.passage on Databricks AI Search, asked a hybrid
  query (the words and the query's vector) with the reranker, run with the viewer's own token.
- FixtureSearch, offline. The same steps over the fixture database: BM25 over the words of each
  passage's header and text, the cosine of the recorded vectors, reciprocal rank fusion of the two,
  then a rerank of the best by how many of the query's words each passage holds.
- AiSearchIndex makes the index and syncs it, on the workspace (ops/documents/run_live.py).

Both searchers apply the same filters: project, document type, country, sector, the window of public
dates, and the as-of date, which keeps out a passage made public after it, or replaced by a re-issue of
its report on or before it (ADR 0002).
"""

from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from strata.knowledge.embed import Embedder, HashedWords, offline, terms

INDEX = "strata.gold.passage_index"  # the Delta Sync index over strata.gold.passage
SOURCE_TABLE = "strata.gold.passage"
FAR_FUTURE = 99991231  # gold.passage's replaced_day while a passage is current


@dataclass(frozen=True)
class Filters:
    as_of: dt.date
    project_id: str | None = None
    document_type: str | None = None
    country_code: str | None = None
    sector: str | None = None
    published_from: dt.date | None = None
    published_until: dt.date | None = None

    def as_dict(self) -> dict:
        return {"project_id": self.project_id, "document_type": self.document_type, "country": self.country_code,
                "sector": self.sector, "published_from": _iso(self.published_from),
                "published_until": _iso(self.published_until), "as_of": self.as_of.isoformat()}


@dataclass(frozen=True)
class Hit:
    passage_id: str
    score: float


@dataclass(frozen=True)
class Hits:
    matched: int  # passages within the filters that matched the query
    hits: list[Hit]  # the best of them, best first
    method: str  # how they were ranked, in a sentence


class Searcher(Protocol):
    name: str

    def search(self, query: str, filters: Filters, k: int) -> Hits:
        """The k passages that best match the query within the filters, best first."""


def _iso(day: dt.date | None) -> str | None:
    return day.isoformat() if day else None


def day_number(day: dt.date) -> int:
    """A date as the number gold.passage's public_day and replaced_day hold: 20191102."""
    return day.year * 10000 + day.month * 100 + day.day


# ── Offline: the fixture search ──────────────────────────────────────────

CANDIDATES = """
SELECT passage_id, header, text, embedding, embedding_model
FROM strata.gold.passage
WHERE public_from <= :as_of
  AND (replaced_on IS NULL OR replaced_on > :as_of)
  AND (CAST(:project_id AS STRING) IS NULL OR project_id = :project_id)
  AND (CAST(:document_type AS STRING) IS NULL OR document_type = :document_type)
  AND (CAST(:country_code AS STRING) IS NULL OR country_code = :country_code)
  AND (CAST(:sector AS STRING) IS NULL OR sector = :sector)
  AND (CAST(:published_from AS DATE) IS NULL OR public_from >= :published_from)
  AND (CAST(:published_until AS DATE) IS NULL OR public_from <= :published_until)
"""
BM25_K1, BM25_B = 1.2, 0.75
FUSION_K = 60  # reciprocal rank fusion's constant, as AI Search's hybrid query uses
RERANK_DEPTH = 20  # how many of the fused best the rerank reorders
MIN_SIMILARITY = 0.2  # the stand-in's vectors share a few hashed slots by chance, so a match needs more


def filter_params(filters: Filters) -> dict:
    return {"as_of": filters.as_of, "project_id": filters.project_id, "document_type": filters.document_type,
            "country_code": filters.country_code, "sector": filters.sector,
            "published_from": filters.published_from, "published_until": filters.published_until}


class FixtureSearch:
    """Hybrid search over the fixture database's passages and their recorded vectors."""

    name = "fixture search"

    def __init__(self, engine, embedders: dict[str, Callable[[], Embedder]] | None = None):
        self.engine = engine
        # The models that can embed a query here, with no network: only the offline stand-in.
        self.embedders = embedders if embedders is not None else {HashedWords.name: offline}

    def _query_vector(self, query: str, models: set[str]) -> list[float] | None:
        """The query's vector from the model that made the passages' vectors, when it runs here. When it
        does not, as for vectors recorded from the live model, the search ranks on the words alone."""
        if len(models) != 1 or next(iter(models)) not in self.embedders:
            return None
        return self.embedders[next(iter(models))]().embed([query])[0]

    def search(self, query: str, filters: Filters, k: int) -> Hits:
        result = self.engine.run(CANDIDATES, filter_params(filters))
        candidates = [dict(zip(result.columns, row)) for row in result.rows]
        if not candidates:
            return Hits(0, [], "No passage is within the filters.")
        wanted = list(dict.fromkeys(terms(query)))
        keyword = _bm25(wanted, [terms(f"{c['header']} {c['text']}") for c in candidates])
        vector = self._query_vector(query, {c["embedding_model"] for c in candidates})
        similarity = [_cosine(vector, c["embedding"]) if vector else 0.0 for c in candidates]
        matched = [i for i in range(len(candidates)) if keyword[i] > 0 or similarity[i] >= MIN_SIMILARITY]
        fused = _fuse(matched, keyword, similarity)
        top = sorted(matched, key=lambda i: -fused[i])[:RERANK_DEPTH]
        covered = {i: len(set(wanted) & set(terms(f"{candidates[i]['header']} {candidates[i]['text']}")))
                   for i in top}
        ranked = sorted(top, key=lambda i: (-covered[i], -fused[i], candidates[i]["passage_id"]))
        ranked += sorted((i for i in matched if i not in covered), key=lambda i: (-fused[i], candidates[i]["passage_id"]))
        method = ("BM25 on the words and the cosine of the vectors, fused by reciprocal rank, then the best "
                  f"{RERANK_DEPTH} reranked by how many of the query's words each holds"
                  if vector else "BM25 on the words, then the best reranked by how many of the query's words each holds")
        return Hits(len(matched), [Hit(candidates[i]["passage_id"], round(fused[i], 6)) for i in ranked[:k]], method)


def _bm25(wanted: list[str], documents: list[list[str]]) -> list[float]:
    count = len(documents)
    average = sum(len(d) for d in documents) / count or 1.0
    frequency = Counter(term for d in documents for term in set(d))
    scores = []
    for words in documents:
        found = Counter(words)
        score = 0.0
        for term in wanted:
            if found[term]:
                idf = math.log(1 + (count - frequency[term] + 0.5) / (frequency[term] + 0.5))
                score += idf * found[term] * (BM25_K1 + 1) / (
                    found[term] + BM25_K1 * (1 - BM25_B + BM25_B * len(words) / average))
        scores.append(score)
    return scores


def _cosine(a: list[float], b) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    size = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / size if size else 0.0


def _fuse(matched: list[int], keyword: list[float], similarity: list[float]) -> dict[int, float]:
    fused = dict.fromkeys(matched, 0.0)
    for scores in (keyword, similarity):
        ranked = sorted((i for i in matched if scores[i] > 0), key=lambda i: -scores[i])
        for rank, i in enumerate(ranked, 1):
            fused[i] += 1 / (FUSION_K + rank)
    return fused


# ── Live: AI Search ──────────────────────────────────────────────────────

Transport = Callable[[str, str, dict | None], dict]  # (method, path, body) -> the parsed JSON answer


class AiSearch:
    """The Delta Sync index on Databricks AI Search, asked as the viewer: words, the query's vector, the
    filters, and the reranker over each passage's header and text."""

    name = "AI Search"

    def __init__(self, transport: Transport, embedder: Embedder, index: str = INDEX):
        self.transport, self.embedder, self.index = transport, embedder, index

    def search(self, query: str, filters: Filters, k: int) -> Hits:
        [vector] = self.embedder.embed([query])
        answer = self.transport("POST", f"/api/2.0/vector-search/indexes/{self.index}/query", {
            "columns": ["passage_id"],
            "query_text": query,
            "query_vector": vector,
            "query_type": "HYBRID",
            "num_results": k,
            "filters_json": json.dumps(index_filters(filters)),
            "reranker": {"model": "databricks_reranker", "parameters": {"columns_to_rerank": ["header", "text"]}},
        })
        columns = [column["name"] for column in (answer.get("manifest") or {}).get("columns", [])]
        rows = (answer.get("result") or {}).get("data_array") or []
        at, score = columns.index("passage_id"), columns.index("score") if "score" in columns else len(columns) - 1
        hits = [Hit(str(row[at]), float(row[score])) for row in rows]
        return Hits(len(hits), hits, "AI Search's hybrid query, words and vector, with its reranker over the "
                                     "header and the text")


def index_filters(filters: Filters) -> dict:
    """The filters as AI Search's filters_json takes them: equal values, and day numbers compared."""
    found: dict = {"public_day <=": day_number(filters.as_of), "replaced_day >": day_number(filters.as_of)}
    for column, wanted in (("project_id", filters.project_id), ("document_type", filters.document_type),
                           ("country_code", filters.country_code), ("sector", filters.sector)):
        if wanted:
            found[column] = wanted
    if filters.published_from:
        found["public_day >="] = day_number(filters.published_from)
    if filters.published_until:
        found["public_day <="] = min(day_number(filters.published_until), found["public_day <="])
    return found


@dataclass(frozen=True)
class IndexState:
    ready: bool
    rows: int
    message: str


class AiSearchIndex:
    """The Delta Sync index over strata.gold.passage on the AI Search endpoint, made when missing and
    synced after each run. Delta Sync reads the table's change feed, so the table needs it turned on."""

    columns = ["passage_id", "project_id", "document_type", "country_code", "sector", "header", "text",
               "public_day", "replaced_day", "embedding"]

    def __init__(self, transport: Transport, endpoint: str, dimensions: int, index: str = INDEX,
                 table: str = SOURCE_TABLE):
        self.transport, self.endpoint, self.dimensions, self.index, self.table = (
            transport, endpoint, dimensions, index, table)

    def ensure(self, run_sql: Callable[[str], object]) -> bool:
        """Make the index if it is missing. Returns whether it made it."""
        run_sql(f"ALTER TABLE {self.table} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")  # sql-lint: names only
        try:
            self.transport("GET", f"/api/2.0/vector-search/indexes/{self.index}", None)
            return False
        except LookupError:
            pass
        self.transport("POST", "/api/2.0/vector-search/indexes", {
            "name": self.index,
            "endpoint_name": self.endpoint,
            "primary_key": "passage_id",
            "index_type": "DELTA_SYNC",
            "delta_sync_index_spec": {
                "source_table": self.table,
                "pipeline_type": "TRIGGERED",
                "columns_to_sync": self.columns,
                "embedding_vector_columns": [{"name": "embedding", "embedding_dimension": self.dimensions}],
            },
        })
        return True

    def sync(self) -> None:
        self.transport("POST", f"/api/2.0/vector-search/indexes/{self.index}/sync", {})

    def state(self) -> IndexState:
        answer = self.transport("GET", f"/api/2.0/vector-search/indexes/{self.index}", None)
        status = answer.get("status") or {}
        return IndexState(bool(status.get("ready")), int(status.get("indexed_row_count") or 0),
                          str(status.get("message") or ""))


# ── Which searcher a call uses ───────────────────────────────────────────

def searcher_for(call, environ: dict | None = None) -> Searcher:
    """The fixture search on DuckDB; on the workspace, AI Search with the viewer's own token and the
    query embedded by the deployment config/models.toml names."""
    if getattr(call.engine, "name", "") == "duckdb":
        return FixtureSearch(call.engine)
    import os

    from strata.config import load_models
    from strata.knowledge.embed import AzureOpenAIEmbeddings
    from strata.lakehouse.engine import http_transport

    env = os.environ if environ is None else environ
    model = load_models()["embed"]
    embedder = AzureOpenAIEmbeddings(env["AZURE_OPENAI_ENDPOINT"], env["AZURE_OPENAI_API_KEY"], model.deployment,
                                     model.dimensions)
    return AiSearch(not_found_as_lookup(http_transport(env["DATABRICKS_HOST"], call.viewer.token)), embedder)


def not_found_as_lookup(transport: Transport) -> Transport:
    """The workspace's transport, with a 404 raised as LookupError, so a missing index reads as missing."""
    from strata.lakehouse.engine import EngineError

    def call(method: str, path: str, body: dict | None = None) -> dict:
        try:
            return transport(method, path, body)
        except EngineError as error:
            if " 404 " in str(error) or "RESOURCE_DOES_NOT_EXIST" in str(error):
                raise LookupError(str(error)) from error
            raise

    return call
