"""From an answer's run ID to its tool calls and the tables they read (ticket 45, the third criterion), at seam 3.

A question goes in over HTTP to the scripted agent, whose tools run on the fixture database through the tool
registry. The registry notes every table each call's queries read (Context.reads), and the run log writes the run,
its calls and those tables to strata.ops beside each other. The Governance page's lineage tiles then read them by
the run's ID, or the latest run when Run ID is empty. The Delta version a call read exists only on the workspace, so
offline it is empty (docs/workspace-catchup.md checks it there).
"""

import asyncio
import datetime as dt
from contextlib import contextmanager

import httpx
import pytest

from dashboard_seed import rows
from strata.agent.loop import answer_runner
from strata.agent.runs import RunLog
from strata.agent.scripted import ScriptedAgent, ScriptedJudge, load_cases
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

TODAY = dt.date(2026, 10, 23)
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}


@pytest.fixture(scope="module")
def logged(fixture_db, tmp_path_factory):
    """The showcase question asked once, with the scripted answer that adds a number no record holds, and its run
    logged in a database of its own."""
    ops = tmp_path_factory.mktemp("lineage") / "ops.duckdb"
    with DuckDBEngine.open(ops) as engine:
        catalog.build(engine)
    case = load_cases()["p130164-number-with-no-record"]

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = create_app(runner=answer_runner(lambda turn: ScriptedAgent(case), engine_for, today=lambda: TODAY),
                     engine_for=engine_for, judge=ScriptedJudge(case), new_run_id=lambda: "run-0001",
                     runs=RunLog(lambda: DuckDBEngine.open(ops)))

    async def ask():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            return await client.post("/api/ask", headers=ANA, json={
                "question": case.question, "scope": case.scope, "asof": case.as_of.isoformat()})

    assert asyncio.run(ask()).status_code == 200
    with DuckDBEngine.open(ops, read_only=True) as engine:
        yield engine


def test_from_an_answer_s_run_id_the_lineage_reaches_its_tool_calls_and_the_tables_they_read(logged):
    [run] = rows(logged, "lineage_run", run_id="run-0001")
    calls = rows(logged, "lineage_calls", run_id="run-0001")
    reads = rows(logged, "lineage_reads", run_id="run-0001")

    assert (run["run_id"], run["view"], run["tool_calls"]) == ("run-0001", "World Bank staff", 1)
    assert run["question"] == "Why were works contracts in P130164 advertised again?"
    [call] = calls
    assert (call["call_order"], call["tool"]) == (1, "search_passages")
    assert call["rows_returned"] > 0 and call["took_ms"] is not None
    assert "strata.gold.passage:31525018/v1/54" in call["evidence_ids"]  # ICR paragraph 54, which the answer cites
    tables = [row["table_name"] for row in reads]
    assert "strata.gold.passage" in tables  # the passages a search returns are the knowledge model's
    assert all(row["call"] == "1. search_passages" for row in reads)
    assert all(row["version_read"] is None for row in reads)  # DuckDB keeps no versions
    assert all(row["sources"] for row in reads)


def test_an_empty_run_id_shows_the_latest_answer_run(logged):
    assert [row["run_id"] for row in rows(logged, "lineage_run")] == ["run-0001"]
    assert rows(logged, "lineage_calls") == rows(logged, "lineage_calls", run_id="run-0001")


def test_the_run_log_keeps_each_removed_sentence_s_reason_without_its_words(logged):
    """The scripted answer adds "Bids were usually opened within 45 days.", which no record backs (ticket 13's case),
    and the AI quality page counts it by its reason."""
    [run] = rows(logged, "lineage_run", run_id="run-0001")
    found = logged.run("SELECT * FROM strata.ops.answer_removals WHERE run_id = 'run-0001'")

    assert run["sentences_removed"] == 1
    assert [row[:3] for row in found.rows] == [("run-0001", 1, "number_not_in_records")]
    assert found.columns == ("run_id", "position", "reason", "removed_at", "public_from")
    today = dt.datetime.now(dt.UTC).date()  # the run log dates a run by the clock it ended on
    assert [(row["reason"], row["sentences"]) for row in rows(logged, "removed_reasons", date_to=today)] == [
        ("No record supports a number or date", 1)]
