"""Shared test setup: the fixture database is built once per run. The network guard is in ../conftest.py."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"


@pytest.fixture(scope="session")
def fixture_db():
    """The fixture database. The gate builds it first; a lone pytest run builds it when it is missing."""
    if not FIXTURE_DB.exists():
        subprocess.run([sys.executable, str(ROOT / "gates" / "build_fixture.py")], check=True)
    return FIXTURE_DB
