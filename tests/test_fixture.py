"""Building the fixture database: each CSV file in the placeholder folder becomes a table,
and a file whose name is not a table name stops the build before it writes anything."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def builder():
    spec = importlib.util.spec_from_file_location("build_fixture", ROOT / "gates" / "build_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_fixture_file_whose_name_starts_with_an_underscore_stops_the_build(tmp_path):
    source = tmp_path / "placeholder"
    source.mkdir()
    (source / "_plan_rows.csv").write_text("plan_id\nP1\n")
    out = tmp_path / "fixture.duckdb"

    with pytest.raises(SystemExit, match="start with a letter"):
        builder().build(out=out, source=source)

    assert not out.exists()
