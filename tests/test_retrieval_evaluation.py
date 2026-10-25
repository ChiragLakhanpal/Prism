"""Retrieval evaluation in the replay harness (ticket 32; spec, seam 5): precision at 10, recall at 20 and nDCG
at 10 for each query set of the labeled set, stored in strata.ops.evaluation_result, using only documents public
before each query's date.

The known-answer test scores a hand-made ranking whose measures were worked out by hand below. The leakage test
dates a query between the ICR's own date and the day it became public (values.toml: icr-date, icr-disclosed),
so it proves the evaluation filters on the day a document became public, not on the date it carries.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.estimates import harness, retrieval
from strata.estimates.tracking import OfflineTracker
from strata.knowledge.retrieval.labels import Label, LiveFeedbackError
from strata.knowledge.search import Hit, Hits
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["silver_labels"]
ICR = "31525018/v1"
RAN_AT = dt.datetime(2026, 10, 24, 6, 0, tzinfo=dt.UTC)
TODAY = dt.date(2026, 10, 24)


class Ranked:
    """A searcher that gives the same ranking for every query: the passages it was given, in order."""

    name = "hand-made ranking"

    def __init__(self, rankings: dict[str, list[str]]):
        self.rankings, self.asked = rankings, []

    def search(self, query, filters, k):
        self.asked.append((query, filters.as_of, filters.project_id))
        found = self.rankings[query][:k]
        return Hits(len(found), [Hit(passage, 1.0 / (rank + 1)) for rank, passage in enumerate(found)], "by hand")


def label(query: str, passage: str, grade: int, date=dt.date(2020, 3, 27)) -> Label:
    return Label("icr_review_citations", query, query, date, "P130164", passage, grade, "icr_review_citation")


@pytest.fixture
def store(tmp_path):
    with DuckDBEngine.open(tmp_path / "results.duckdb") as engine:
        catalog.build(engine)
        yield engine


def stored(store, run_id: str) -> dict[tuple[str, str], float]:
    return {(row["segment"], row["measure"]): row["value"] for row in harness.run_rows(store, run_id)}


def test_each_measure_is_computed_from_a_ranking_whose_answers_are_known(fixture_db, store):
    """q1 labels paragraph 54 "answers it" (2) and 55 "partly" (1), and the ranking puts 54 first and 55 third:
    precision at 10 is 2/10 = 0.2, recall at 20 is 2/2 = 1, and nDCG at 10 is (3/log2(2) + 1/log2(4)) /
    (3/log2(2) + 1/log2(3)) = 3.5/3.6309 = 0.9639. q2 labels paragraph 78, which the ranking leaves out: 0, 0, 0.
    The set's measures are the means over its two queries: 0.1, 0.5 and 0.48."""
    labels = [label("q1", f"{ICR}/54", 2), label("q1", f"{ICR}/55", 1), label("q2", f"{ICR}/78", 2)]
    searcher = Ranked({"q1": [f"{ICR}/54", f"{ICR}/53", f"{ICR}/55"], "q2": [f"{ICR}/53"]})

    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        retrieval.evaluate(engine, OfflineTracker(), "run-1", RAN_AT, store, searcher=lambda _engine: searcher,
                           labels=labels, today=TODAY)

    assert stored(store, "run-1") == {
        ("icr_review_citations", "queries"): 2, ("icr_review_citations", "labels"): 3,
        ("icr_review_citations", "precision_at_10"): 0.1, ("icr_review_citations", "recall_at_20"): 0.5,
        ("icr_review_citations", "ndcg_at_10"): 0.48}
    # Each query searched only documents public before its date, and only its own project's.
    assert {(as_of, project) for _, as_of, project in searcher.asked} == {(dt.date(2020, 3, 26), "P130164")}


def test_the_labeled_set_is_scored_with_the_fixture_search_and_each_query_set_is_stored(fixture_db, store):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        retrieval.evaluate(engine, OfflineTracker(), "run-2", RAN_AT, store, today=TODAY)

    found = stored(store, "run-2")
    citations, lessons = TRUTH["icr_review_citations"], TRUTH["pad_lessons"]
    assert (found[("icr_review_citations", "queries")], found[("icr_review_citations", "labels")]) == (
        citations["queries"], citations["labels"])
    assert (found[("pad_lessons", "queries")], found[("pad_lessons", "labels")]) == (lessons["queries"], lessons["labels"])
    for query_set in ("icr_review_citations", "pad_lessons"):
        for measure in ("precision_at_10", "recall_at_20", "ndcg_at_10"):
            value = found[(query_set, measure)]
            assert 0 <= value <= 1 and round(value, 2) == value, (query_set, measure, value)
    rows = harness.run_rows(store, "run-2")
    assert {row["scorer"] for row in rows} == {"retrieval_evaluation"}
    assert {row["segment_kind"] for row in rows} == {"query_set"}


def test_no_document_public_after_a_querys_date_is_retrieved_for_it(fixture_db, store):
    """A query dated between the ICR's date (October 10, 2019) and the day it became public (November 2, 2019)
    finds none of the ICR's passages, though the ICR is dated before it. The same query dated the day after the
    ICR became public finds paragraph 54."""
    written, public = VALUES["icr-date"]["value"], VALUES["icr-disclosed"]["value"]
    between = written + dt.timedelta(days=10)
    assert written < between < public
    text = "works contract estimates were not based on market rate, which led to rebidding"
    before = Label("icr_review_citations", "before", text, between, "P130164", f"{ICR}/54", 2, "icr_review_citation")
    after = Label("icr_review_citations", "after", text, public + dt.timedelta(days=1), "P130164", f"{ICR}/54", 2,
                  "icr_review_citation")

    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        early = retrieval.ranked(engine, retrieval.evaluation_queries([before])[0])
        late = retrieval.ranked(engine, retrieval.evaluation_queries([after])[0])

    assert early and not [passage for passage, _ in early if passage.startswith("31525018/")]
    assert all(public_from < between for _, public_from in early)
    assert f"{ICR}/54" in [passage for passage, _ in late][:20]


@pytest.mark.parametrize("origin", ["feedback_reviewed", "feedback_agreement"])
def test_an_evaluation_set_built_from_a_label_that_came_from_live_feedback_fails(fixture_db, store, origin):
    labels = [label("q1", f"{ICR}/54", 2), Label("icr_review_citations", "q1", "q1", dt.date(2020, 3, 27), "P130164",
                                                 f"{ICR}/55", 0, origin)]

    with pytest.raises(LiveFeedbackError, match="never live feedback"):
        retrieval.evaluation_queries(labels)
    with DuckDBEngine.open(fixture_db, read_only=True) as engine, pytest.raises(LiveFeedbackError):
        retrieval.evaluate(engine, OfflineTracker(), "run-4", RAN_AT, store, labels=labels, today=TODAY)
    assert harness.run_rows(store, "run-4") == []


def test_a_searcher_that_returns_a_passage_public_after_the_querys_date_is_refused(fixture_db, store):
    leaky = Ranked({"q": [f"{ICR}/54"]})
    early = Label("icr_review_citations", "q", "q", dt.date(2019, 10, 20), "P130164", f"{ICR}/54", 2,
                  "icr_review_citation")

    with DuckDBEngine.open(fixture_db, read_only=True) as engine, pytest.raises(harness.LeakageError):
        retrieval.evaluate(engine, OfflineTracker(), "run-3", RAN_AT, store, searcher=lambda _engine: leaky,
                           labels=[early], today=TODAY)
