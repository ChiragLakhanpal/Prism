"""Retrieval evaluation in the replay harness, and the tuning gate (ticket 32; spec, seam 5; spec story 102).

RetrievalEvaluation is a replay harness scorer (strata.estimates.harness). For each evaluation set of the
labeled set (strata.knowledge.retrieval.labels: the ICR Reviews' citations, the PADs' lessons sections and the
judged notice queries) it searches each query with only documents public before the query's date, within the
query's project, and reports the set's size and the means over its queries of precision at 10, recall at 20
and nDCG at 10 (the k of each is in config/thresholds.toml), each at two decimals, a tool column. The harness
writes them to strata.ops.evaluation_result, one segment per query set, and logs them to MLflow. A searcher
that returns a passage made public after its query's date stops the run with LeakageError, so a number can
never rest on a document the query could not have seen.

The tuning gate (gate()) compares a candidate search setup with production's (config/models.toml,
[search.setup]) on the held-out queries, one in held_out_every of each evaluation set by a stable hash of the
query's id. A candidate that scores lower on any measure of any held-out set, by more than tuning_tolerance,
is blocked. The hindsight set belongs to ticket 34: until it exists, the gate reports it as not compared,
never as passed, and decides on the held-out set alone.

Live feedback never reaches an evaluation set: evaluation_queries() refuses a label from it.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from functools import cache
from importlib import resources
from types import SimpleNamespace

from strata.config import SearchSetup, Thresholds, load_search, load_thresholds
from strata.estimates import harness
from strata.estimates.harness import HARNESS, LeakageError, Reader, Score, Scored, Window
from strata.knowledge.retrieval import labels as label_set
from strata.knowledge.retrieval.labels import EVALUATION_SETS, Label, Query
from strata.knowledge.search import Filters, Searcher, searcher_for
from strata.lakehouse.engine import Engine

SCORER = "retrieval_evaluation"
GATE = "retrieval_tuning_gate"
DAY = dt.timedelta(days=1)

SearcherFor = Callable[[Engine], Searcher]


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "retrieval" / f"{name}.sql").read_text()


def evaluation_queries(labels: Iterable[Label]) -> list[Query]:
    """The queries of an evaluation set, from its labels. A label from live feedback is refused."""
    return label_set.evaluation_set(labels)


def held_out(query_id: str, every: int) -> bool:
    """Whether a query is held out of tuning: one in every, by a stable hash of its id."""
    return int(hashlib.sha256(query_id.encode("utf-8")).hexdigest()[:8], 16) % every == 0


def default_searcher(setup: SearchSetup | None = None) -> SearcherFor:
    """Production's searcher, run as the harness: the fixture search on DuckDB, AI Search on the workspace."""
    return lambda engine: searcher_for(SimpleNamespace(engine=engine, viewer=HARNESS), setup=setup)


def ranked(engine: Engine, query: Query, searcher: Searcher | None = None, k: int | None = None,
           reader: Reader | None = None) -> list[tuple[str, dt.date]]:
    """The passages a search ranks for a query, best first, each with the day it became public. The search sees
    only documents public before the query's date; a passage public after it is refused with LeakageError."""
    as_of = query.date - DAY
    searcher = searcher or default_searcher()(engine)
    k = k or int(load_thresholds().value("retrieval.recall_k"))
    hits = searcher.search(query.text, Filters(as_of, project_id=query.project_id), k)
    ids = [hit.passage_id for hit in hits.hits]
    if not ids:
        return []
    params = {"ids": ",".join(ids)}
    if reader is not None:
        found = reader.rows(_sql("passages_public"), **params)
    else:
        result = engine.run(_sql("passages_public"), params)
        found = [dict(zip(result.columns, row)) for row in result.rows]
    public = {row["passage_id"]: label_set.as_date(row["public_from"]) for row in found}
    for passage in ids:
        if passage in public and public[passage] > as_of:
            raise LeakageError(f"The search for query {query.query_id}, dated {query.date}, returned {passage}, which "
                               f"became public on {public[passage]}.")
    return [(passage, public[passage]) for passage in ids if passage in public]


@dataclass(frozen=True)
class Measured:
    """An evaluation set's size and its measures: the means over its queries, unrounded."""

    queries: int
    labels: int
    precision: float
    recall: float
    ndcg: float

    def values(self) -> tuple[float, float, float]:
        return self.precision, self.recall, self.ndcg


def measures(ranking: Sequence[str], relevant: dict[str, int], thresholds: Thresholds) -> tuple[float, float, float]:
    """Precision at precision_k, recall at recall_k and nDCG at ndcg_k for one query, whose labeled passages
    have grades 1 (partly) or 2 (answers it). nDCG's gain is 2^grade - 1, discounted by log2 of rank + 1."""
    value = thresholds.value
    p_k, r_k, n_k = (int(value(f"retrieval.{name}")) for name in ("precision_k", "recall_k", "ndcg_k"))
    precision = sum(1 for passage in ranking[:p_k] if relevant.get(passage, 0) > 0) / p_k
    recall = sum(1 for passage in ranking[:r_k] if relevant.get(passage, 0) > 0) / len(relevant)
    dcg = sum((2 ** relevant.get(passage, 0) - 1) / math.log2(rank + 2) for rank, passage in enumerate(ranking[:n_k]))
    ideal = sum((2 ** grade - 1) / math.log2(rank + 2)
                for rank, grade in enumerate(sorted(relevant.values(), reverse=True)[:n_k]))
    return precision, recall, (dcg / ideal if ideal else 0.0)


def measure(engine: Engine, queries: list[Query], searcher: Searcher, thresholds: Thresholds,
            reader: Reader | None = None) -> Measured:
    scored = [measures([passage for passage, _ in ranked(engine, query, searcher, None, reader)], query.relevant,
                       thresholds) for query in queries if query.relevant]
    count = len(scored) or 1
    return Measured(len(scored), sum(len(query.relevant) for query in queries if query.relevant),
                    *(sum(values[i] for values in scored) / count for i in range(3)))


def measure_names(thresholds: Thresholds) -> tuple[str, str, str]:
    value = thresholds.value
    return (f"precision_at_{value('retrieval.precision_k')}", f"recall_at_{value('retrieval.recall_k')}",
            f"ndcg_at_{value('retrieval.ndcg_k')}")


@dataclass
class RetrievalEvaluation:
    """A replay harness scorer: one evaluation set, searched by one setup."""

    query_set: str
    labels: list[Label]
    searcher: SearcherFor
    setup: SearchSetup
    split: str = "all"  # all, or held_out: only the queries held out of tuning
    name: str = SCORER
    model: str = "search_passages"
    measured: Measured | None = field(default=None, init=False)

    def queries(self, thresholds: Thresholds) -> list[Query]:
        found = evaluation_queries(label for label in self.labels if label.query_set == self.query_set)
        if self.split == "held_out":
            every = int(thresholds.value("retrieval.held_out_every"))
            found = [query for query in found if held_out(query.query_id, every)]
        return found

    def score(self, replay: harness.Replay) -> Scored:
        reader = replay.inputs
        self.measured = measure(reader.engine, self.queries(replay.thresholds), self.searcher(reader.engine),
                                replay.thresholds, reader)
        names = measure_names(replay.thresholds)
        return Scored([Score("queries", self.measured.queries), Score("labels", self.measured.labels),
                       *(Score(name, round(value, 2)) for name, value in zip(names, self.measured.values()))],
                      params={"setup": json.dumps(asdict(self.setup), sort_keys=True), "split": self.split})


def read_labels(engine: Engine, as_of: dt.date, thresholds: Thresholds) -> list[Label]:
    """The labeled set's latest build, as the harness may read it on a date."""
    return [Label(row["query_set"], row["query_id"], row["query_text"], label_set.as_date(row["query_date"]),
                  row["project_id"], row["passage_id"], row["grade"], row["origin"], row["weight"])
            for row in Reader(engine, as_of, thresholds).rows(_sql("labels_as_of"))]


def evaluate(engine: Engine, tracker, run_id: str, ran_at: dt.datetime, store: Engine | None = None,
             searcher: SearcherFor | None = None, labels: list[Label] | None = None, today: dt.date | None = None,
             setup: SearchSetup | None = None, split: str = "all",
             thresholds: Thresholds | None = None) -> dict[str, Measured]:
    """Score each evaluation set that has queries, with one setup, through the replay harness: one segment per
    set in strata.ops.evaluation_result under run_id. Returns each set's unrounded measures."""
    thresholds = thresholds or load_thresholds()
    setup = setup or load_search().setup
    today = today or ran_at.astimezone(dt.UTC).date()
    labels = labels if labels is not None else read_labels(engine, today, thresholds)
    searcher = searcher or default_searcher(setup)
    found = {}
    for query_set in EVALUATION_SETS:
        scorer = RetrievalEvaluation(query_set, labels, searcher, setup, split)
        if not scorer.queries(thresholds):
            continue
        window = Window(today, today, "query_set" if split == "all" else split, query_set)
        harness.replay(engine, scorer, window, tracker, run_id, ran_at, store=store, thresholds=thresholds)
        found[query_set] = scorer.measured
    return found


# ── The tuning gate ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Comparison:
    """One measure of one held-out query set, for the current setup and the candidate."""

    query_set: str
    measure: str
    current: float
    candidate: float

    def lost(self, tolerance: float) -> bool:
        return self.candidate < self.current - tolerance


@dataclass(frozen=True)
class Verdict:
    """What the tuning gate found: whether the candidate ships, and on which sets it lost."""

    ships: bool
    held_out: str  # passed, lost or not_compared (no query set had a held-out query)
    hindsight: str  # passed, lost or not_compared (until ticket 34 makes the hindsight set)
    comparisons: list[Comparison]
    losses: list[Comparison]


# The hindsight comparison, once ticket 34 makes one: given the engine and the two setups, whether the candidate
# lost (True), held (False), or None when there is nothing to compare.
Hindsight = Callable[[Engine, SearchSetup, SearchSetup], bool | None]


def gate(engine: Engine, candidate: SearchSetup, tracker, run_id: str, ran_at: dt.datetime, store: Engine | None = None,
         current: SearchSetup | None = None, hindsight: Hindsight | None = None, labels: list[Label] | None = None,
         today: dt.date | None = None, thresholds: Thresholds | None = None) -> Verdict:
    """Compare a candidate search setup with production's on the held-out queries, and on the hindsight set when
    there is one. The two setups' scores go to strata.ops.evaluation_result under run_id/current and
    run_id/candidate, and the verdict under run_id, as the retrieval_tuning_gate scorer."""
    thresholds = thresholds or load_thresholds()
    current = current or load_search().setup
    today = today or ran_at.astimezone(dt.UTC).date()
    labels = labels if labels is not None else read_labels(engine, today, thresholds)
    tolerance = float(thresholds.value("retrieval.tuning_tolerance"))
    scores = {name: evaluate(engine, tracker, f"{run_id}/{name}", ran_at, store, setup=setup, labels=labels,
                             today=today, split="held_out", thresholds=thresholds)
              for name, setup in (("current", current), ("candidate", candidate))}
    names = measure_names(thresholds)
    comparisons = [Comparison(query_set, name, now, then)
                   for query_set, measured in scores["current"].items()
                   for name, now, then in zip(names, measured.values(), scores["candidate"][query_set].values())]
    losses = [comparison for comparison in comparisons if comparison.lost(tolerance)]
    lost_hindsight = hindsight(engine, current, candidate) if hindsight else None
    # Nothing to compare is never a pass: with no held-out query the candidate does not ship.
    held = "not_compared" if not comparisons else ("lost" if losses else "passed")
    behind = "not_compared" if lost_hindsight is None else ("lost" if lost_hindsight else "passed")
    verdict = Verdict(held == "passed" and behind != "lost", held, behind, comparisons, losses)
    _record(store or engine, run_id, ran_at, today, candidate, current, verdict)
    return verdict


def _record(store: Engine, run_id: str, ran_at: dt.datetime, today: dt.date, candidate: SearchSetup,
            current: SearchSetup, verdict: Verdict) -> None:
    """The verdict's rows in strata.ops.evaluation_result: whether each set passed, with "not compared" as text
    for a set the gate could not compare, never a pass; the losses; and whether the candidate ships."""
    scorer = SimpleNamespace(name=GATE, model="search_passages")
    setups = json.dumps({"current": asdict(current), "candidate": asdict(candidate)}, sort_keys=True)
    losses = json.dumps([asdict(loss) for loss in verdict.losses], sort_keys=True)
    rows = [
        ("held_out", Score("passed", None, "not compared") if verdict.held_out == "not_compared"
         else Score("passed", 1 if verdict.held_out == "passed" else 0)),
        ("held_out", Score("losses", len(verdict.losses), losses)),
        ("hindsight", Score("passed", None, "not compared") if verdict.hindsight == "not_compared"
         else Score("passed", 1 if verdict.hindsight == "passed" else 0)),
        ("verdict", Score("ships", 1 if verdict.ships else 0, setups)),
    ]
    harness.write(store, [harness.row(run_id, scorer, Window(today, today, "check", segment), score, None, ran_at)
                          for segment, score in rows])
