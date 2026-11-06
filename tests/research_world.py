"""Shared setup for the deep research tests (ticket 147): the recorded answers, the fixture's project, a fake clock,
and an app state database that holds only the research tables, in memory."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded" / "research"
TABLES = ROOT / "src" / "strata" / "lakehouse" / "tables" / "ops"
# The day the sample brief's items were read (.notes/prism-sample, build5.py).
NOV_5 = dt.datetime(2026, 11, 5, 18, 0, tzinfo=dt.UTC)


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
