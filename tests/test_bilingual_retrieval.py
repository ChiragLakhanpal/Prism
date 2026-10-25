"""Retrieval across languages, measured on a bilingual query set (ticket 42; spec seam 5).

evals/bilingual_queries.toml holds English queries whose answers are in P127203's French completion report, and
French queries whose answers are in P130164's English one. The weekly retrieval run builds them into the labeled
set as two evaluation sets, and the retrieval evaluation stores each set's recall at 20 in strata.ops. Offline,
the fixture search reads hashed words, so the stored number shows only that the harness computes and stores it;
the finding needs text-embedding-3-large on AI Search (a workspace step).
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.estimates import harness, retrieval
from strata.estimates.tracking import OfflineTracker
from strata.knowledge.retrieval import labels
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
QUERIES = tomllib.loads((ROOT / "evals" / "bilingual_queries.toml").read_text())["query"]
RAN_AT = dt.datetime(2026, 10, 25, 6, 0, tzinfo=dt.UTC)
LANGUAGE_OF_ANSWERS = {"bilingual_en_fr": "fr", "bilingual_fr_en": "en"}


@pytest.fixture
def store(tmp_path):
    with DuckDBEngine.open(tmp_path / "results.duckdb") as engine:
        catalog.build(engine)
        yield engine


def test_the_labeled_set_holds_20_or_more_english_queries_whose_answers_are_french_passages(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        built = [label for label in labels.latest(engine) if label.query_set in LANGUAGE_OF_ANSWERS]
        language = dict(engine.connection.execute("SELECT passage_id, language FROM strata.silver.passages").fetchall())

    english_over_french = {label.query_id for label in built if label.query_set == "bilingual_en_fr"}
    assert len(english_over_french) >= 20
    assert english_over_french == {query["id"] for query in QUERIES if query["set"] == "bilingual_en_fr"}
    assert {label.query_id for label in built if label.query_set == "bilingual_fr_en"}
    # Every label is a passage written in the other language from its query's.
    assert all(language[label.passage_id] == LANGUAGE_OF_ANSWERS[label.query_set] for label in built)
    labeled = sum(len(query["relevant"]) for query in QUERIES)
    assert len(built) == labeled and {label.origin for label in built} == {"bilingual_labeled"}


def test_recall_at_20_for_english_queries_over_french_passages_is_stored_in_strata_ops(fixture_db, store):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        measured = retrieval.evaluate(engine, OfflineTracker(), "run-bilingual", RAN_AT, store, today=RAN_AT.date())

    rows = {(row["segment"], row["measure"]): row["value"] for row in harness.run_rows(store, "run-bilingual")}
    english_over_french = sum(1 for query in QUERIES if query["set"] == "bilingual_en_fr")
    assert rows[("bilingual_en_fr", "queries")] == english_over_french == measured["bilingual_en_fr"].queries
    recall = rows[("bilingual_en_fr", "recall_at_20")]
    assert 0 <= recall <= 1 and recall == round(measured["bilingual_en_fr"].recall, 2)
    assert ("bilingual_fr_en", "recall_at_20") in rows
