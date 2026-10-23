"""Ground-truth SQL (seam 2): each file in tests/ground_truth runs on the fixture database
and must return the rows its `-- expect:` lines list, header first.

The SQL is written once, in Databricks SQL, and reaches DuckDB through the engine adapter's
transpile step, the same way every Strata query does. `-- param: name = value` lines bind
parameters. The expected rows come from an independent source named in each file, never from
the code.
"""

from pathlib import Path

import pytest

from strata.lakehouse import ground_truth
from strata.lakehouse.engine import DuckDBEngine

GROUND_TRUTH = Path(__file__).parent / "ground_truth"


@pytest.mark.parametrize("path", sorted(GROUND_TRUTH.glob("*.sql")), ids=lambda p: p.stem)
def test_ground_truth(path, fixture_db):
    case = ground_truth.read(path)
    assert case.expected, f"{path.name} has no -- expect: lines"

    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run(case.sql, case.params)

    assert [result.columns, *result.as_text()] == case.expected


def test_the_sample_query_is_marked_to_run_on_the_warehouse_too():
    case = ground_truth.read(GROUND_TRUTH / "showcase_fiscal_years.sql")

    assert case.engines == ("duckdb", "databricks")
    assert case.params == {"as_of": "2018-12-31"}
