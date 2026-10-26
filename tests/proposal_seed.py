"""A snapshot for the proposal's tests (ticket 46): the fixture database's measures, with the dashboard's made-up month
for what the fixture never holds (tests/dashboard_seed.py: benchmark runs, Foundry evaluations, retrieval runs, the
hindsight test, answers and the cost pull), and a made-up rolling backtest, since the fixture's test years have no
package with a known outcome.

Every made-up value is in tests/dashboard_seed.py or below, so a test can name the number it expects. None of it is a
finding: the proposal's real snapshot is pulled from the workspace by ops/proposal/pull_live.py, run as the README's
section "The proposal" says.
"""

from __future__ import annotations

import datetime as dt

from dashboard_seed import TODAY, at, insert, seeded
from strata.dashboard import findings
from strata.lakehouse.engine import DuckDBEngine
from strata.proposal import snapshot

# Test year: (packages with a known outcome, those signed within their 8-in-10 point). 2023 has fewer than 20.
BACKTEST = {"2021": (40, 31), "2022": (52, 43), "2023": (12, 9), "2024": (60, 47), "2025": (25, 21)}


def backtest(engine) -> None:
    ran = at(dt.date(2026, 10, 19), 3)
    rows = []
    for year, (n, m) in BACKTEST.items():
        for measure, value in (("n", n), ("m", m), ("coverage_percent", round(100 * m / n))):
            rows.append({"run_id": "backtest-1", "scorer": "time_estimate_backtest", "model": None,
                         "segment_kind": "test_year", "segment": year, "measure": measure, "value": value,
                         "value_text": None, "cutoff": None, "outcomes_through": None, "mlflow_run_id": None,
                         "ran_at": ran, "public_from": ran.date()})
    insert(engine, "strata.ops.evaluation_result", rows)


def seeded_engine() -> DuckDBEngine:
    engine = seeded()
    backtest(engine)
    findings.write(engine, "findings-1", lambda: at(TODAY, 6))
    return engine


def merged(fixture_db) -> dict:
    """The fixture's snapshot, with each result the fixture has not measured taken from the made-up month."""
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        fixture = snapshot.pull(engine, TODAY, source="fixture")
    made_up = snapshot.pull(seeded_engine(), TODAY, source="made-up month")
    results = {key: found if found["measured"] else made_up["results"][key]
               for key, found in fixture["results"].items()}
    return {**fixture, "source": "fixture and made-up month", "results": results}
