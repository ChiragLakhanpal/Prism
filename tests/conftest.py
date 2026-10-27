"""Shared test setup: the fixture database is built once per run. The network guard is in ../conftest.py."""

import fcntl
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"


@contextmanager
def one_at_a_time(lock):
    """Hold a lock on a file, so processes that share the file take turns. Closing it lets go."""
    with open(lock, "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory):
    """The fixture database, which the tests open read-only. The gate builds it first.

    A lone pytest run builds it when it is missing. pytest-xdist workers that need it at the same
    time take turns on a lock in the run's shared temporary folder, so only the first one builds it.
    """
    if not FIXTURE_DB.exists():
        with one_at_a_time(tmp_path_factory.getbasetemp().parent / "fixture-build.lock"):
            if not FIXTURE_DB.exists():
                subprocess.run([sys.executable, str(ROOT / "gates" / "build_fixture.py")], check=True)
    return FIXTURE_DB


@pytest.fixture
def shield_finding_an_attack_in():
    """A shield stand-in that finds a prompt attack in each passage holding the given words, and in no
    other. The passage tests and the search tests use it to prove a hit is kept, counted and left out."""
    from strata.knowledge.shields import Scan

    class FindsAnAttack:
        name = "test shield"

        def __init__(self, words: str):
            self.words = words

        def scan(self, texts):
            return [Scan(self.words in text, "found by the test") for text in texts]

    return FindsAnAttack


@pytest.fixture
def every_plan_version(monkeypatch):
    """The plan reader reads every plan a project's document list names, newest first, as it did before ticket 108
    (config/thresholds.toml's ingestion.plan_versions = "all"), for a test of how it reads many plan versions. The
    nightly job reads only each project's newest plan."""
    from strata.config import load_thresholds
    from strata.lakehouse import plans

    every = plans.with_plan_versions(load_thresholds(), plans.EVERY_VERSION)
    monkeypatch.setattr(plans, "load_thresholds", lambda: every)
    return every
