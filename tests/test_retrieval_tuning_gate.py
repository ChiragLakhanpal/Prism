"""The tuning gate (ticket 32; spec story 102; spec, seam 5): a search setup ships only when it loses nothing on
the held-out set or the hindsight set. Over the fixture's labeled set and its recorded embeddings, the current
setup (config/models.toml, [search.setup]) passes against itself, and a deliberately worse one is blocked:
turning the reranker off, or giving keyword search no weight. The hindsight set is ticket 34's, so the gate says
it was not compared, never that it passed.
"""

import datetime as dt
import json

import pytest

from strata.config import SearchSetup, load_search
from strata.estimates import harness, retrieval
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine

RAN_AT = dt.datetime(2026, 10, 24, 6, 0, tzinfo=dt.UTC)


@pytest.fixture
def store(tmp_path):
    with DuckDBEngine.open(tmp_path / "results.duckdb") as engine:
        catalog.build(engine)
        yield engine


def run_gate(fixture_db, store, candidate, run_id):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        return retrieval.gate(engine, candidate, OfflineTracker(), run_id, RAN_AT, store)


def test_the_current_setup_passes_the_gate_and_the_hindsight_set_is_not_compared(fixture_db, store):
    verdict = run_gate(fixture_db, store, load_search().setup, "gate-current")

    assert (verdict.ships, verdict.held_out, verdict.hindsight, verdict.losses) == (True, "passed", "not_compared", [])
    assert {comparison.query_set for comparison in verdict.comparisons} == {"icr_review_citations", "pad_lessons"}
    rows = {(row["segment"], row["measure"]): (row["value"], row["value_text"])
            for row in harness.run_rows(store, "gate-current") if row["scorer"] == "retrieval_tuning_gate"}
    assert rows[("held_out", "passed")] == (1, None)
    assert rows[("hindsight", "passed")] == (None, "not compared")
    ships, setups = rows[("verdict", "ships")]
    assert ships == 1 and json.loads(setups)["candidate"]["rerank"] is True


@pytest.mark.parametrize("worse", [SearchSetup(rerank=False), SearchSetup(keyword_weight=0.0)],
                         ids=["reranker-off", "no-keyword-weight"])
def test_a_deliberately_worse_setup_is_blocked(fixture_db, store, worse):
    verdict = run_gate(fixture_db, store, worse, "gate-worse")

    assert (verdict.ships, verdict.held_out, verdict.hindsight) == (False, "lost", "not_compared")
    assert verdict.losses and all(loss.candidate < loss.current for loss in verdict.losses)
    rows = {(row["segment"], row["measure"]): row["value"] for row in harness.run_rows(store, "gate-worse")
            if row["scorer"] == "retrieval_tuning_gate"}
    assert (rows[("held_out", "passed")], rows[("verdict", "ships")]) == (0, 0)
