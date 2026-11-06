"""Shared setup for the deep research tests (tickets 147 and 148): the recorded answers, the fixture's project, a fake
clock, an app state database that holds only the research tables, in memory, and the demo seed's run
(ops/research/seed.py, seed:P156634:2026-11-05) written into a copy of the fixture, or given as each source's result."""

from __future__ import annotations

import copy
import datetime as dt
import shutil
import sys
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded" / "research"
TABLES = ROOT / "src" / "strata" / "lakehouse" / "tables" / "ops"
# The day the sample brief's items were read (.notes/prism-sample, build5.py).
NOV_5 = dt.datetime(2026, 11, 5, 18, 0, tzinfo=dt.UTC)
sys.path.insert(0, str(ROOT / "ops" / "research"))
import seed as research_seed  # noqa: E402

PROJECT = "P156634"
SEED_RUN_ID = f"seed:{PROJECT}:2026-11-05"


class Clock:
    """A clock that moves only when a test sleeps, so no test waits."""

    def __init__(self, start: float = 1000.0):
        self.now, self.slept = start, []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(round(seconds, 6))
        self.now += seconds


def research_tables(path: Path | None = None) -> DuckDBEngine:
    """A DuckDB database with the schema strata.ops and the three research tables, from their definitions."""
    engine = DuckDBEngine.open(path)
    engine.run("CREATE SCHEMA IF NOT EXISTS strata.ops")
    for name in ("research_runs", "research_items", "research_cache"):
        engine.run((TABLES / f"{name}.sql").read_text())
    return engine


def answers(*pairs) -> callable:
    """A fetch that answers each address it knows with its (status, body) and fails the test on any other, counting
    its calls."""
    known = dict(pairs)
    calls: list[str] = []

    def fetch(url: str, *, headers=None):
        calls.append(url)
        assert url in known, f"the test gave no answer for {url}"
        status, body = known[url]
        return status, {"content-type": "text/html"}, body if isinstance(body, bytes) else body.encode()

    fetch.calls = calls
    return fetch


@cache
def _seed_run(fixture_db: str):
    with DuckDBEngine.open(Path(fixture_db), read_only=True) as fixture:
        return research_seed.sample_run(PROJECT, fixture)


def seed_run(fixture_db: Path):
    """The seed's run and its items, read once per test process from the recordings and the fixture database."""
    run, items = _seed_run(str(fixture_db))
    return run, copy.deepcopy(items)


def seeded_copy(fixture_db: Path, folder: Path) -> Path:
    """A copy of the fixture database with the seed's run kept in it, through the research store."""
    from strata.research.store import ResearchStore

    target = folder / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    run, items = seed_run(fixture_db)
    with DuckDBEngine.open(target) as engine:
        assert ResearchStore(lambda: engine.cursor()).save(run, items)
    return target


def seed_kit(fixture_db: Path, fail: str | None = None):
    """A run's kit whose readers give each source's result from the seed's run, as ticket 147's read() gives a
    SourceResult; the source that fail names raises instead."""
    from strata.config import load_research
    from strata.research import run as research_run
    from strata.research.sources import SourceResult

    run, items = seed_run(fixture_db)
    sources = [source for source in load_research().values() if source.enabled]

    def read(source, project, fetch, engine, now):
        if source.key == fail:
            raise RuntimeError("The answer could not be read.")
        note = run.source_notes[source.key]
        return SourceResult(source.key, [item for item in copy.deepcopy(items) if item["source"]["key"] == source.key],
                            source.key in run.reached, note["status"], note["note"])

    return research_run.Kit(facts=lambda engine, project_id, as_of: {"project_id": project_id},
                            sources=lambda: sources, read=read, fetch=None)
