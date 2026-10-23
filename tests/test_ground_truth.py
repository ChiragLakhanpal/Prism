"""Ground-truth SQL (seam 2): each file in tests/ground_truth runs on the fixture database
and must return the rows its `-- expect:` lines list, header first.

The expected rows come from an independent source named in each file, never from the code.
"""

import csv
from pathlib import Path

import duckdb
import pytest

GROUND_TRUTH = Path(__file__).parent / "ground_truth"


def expected_rows(sql):
    lines = [line.split("-- expect:", 1)[1].strip() for line in sql.splitlines() if line.startswith("-- expect:")]
    return [tuple(row) for row in csv.reader(lines)]


@pytest.mark.parametrize("path", sorted(GROUND_TRUTH.glob("*.sql")), ids=lambda p: p.stem)
def test_ground_truth(path, fixture_db):
    sql = path.read_text()
    expected = expected_rows(sql)
    assert expected, f"{path.name} has no -- expect: lines"

    with duckdb.connect() as con:
        con.execute("ATTACH ? AS strata (READ_ONLY)", [str(fixture_db)])
        result = con.execute(sql)
        header = tuple(column[0] for column in result.description)
        rows = [tuple("" if value is None else str(value) for value in row) for row in result.fetchall()]

    assert [header, *rows] == expected
