"""Data readiness at seams 1 and 2: the measures the fixture's runs write, and data_readiness_for, the
tool the Data readiness page and the agent call (ticket 16; the 16 design brief).

Expected values come from the measures themselves, read with a direct query on strata.ops, from
tests/ground_truth/values.toml, or from hand-made catalogs whose rows each test writes, never from
the way the tool computes them.
"""

import datetime as dt
import json
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "tests" / "fixtures" / "api"
# The day the fixture's sources were recorded, which the data-freshness stamp shows.
RECORDED_ON = dt.date.fromisoformat(json.loads((RECORDED / "freshness.json").read_text())["data_through"])


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def query(engine, sql, **params):
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


# ── Seam 1: the measures the fixture's runs write ─────────────────────────

def test_the_fixture_takes_every_measure_on_the_day_its_sources_were_recorded(engine):
    """So a page or a tool call pinned to that day reads the same measures whatever day the gate runs."""
    days = query(engine, "SELECT DISTINCT CAST(measured_at AS DATE) AS day, public_from FROM strata.ops.data_readiness")

    assert days == [{"day": RECORDED_ON, "public_from": RECORDED_ON}]
