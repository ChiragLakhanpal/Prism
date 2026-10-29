"""A page's reads, run together (ticket 125): the engine's run_many and the batch a page reads from.

On the workspace, each statement costs the SQL warehouse's statements API about two seconds, so a page that ran its
six statements one after another took over ten. run_many posts a page's statements at once and waits once, and
together() gives a page an engine that answers each of its reads from that one batch. The warehouse is a fake of the
Statement Execution API here, as in tests/test_engine.py; the workspace step in the ticket's report times the real one.
"""

import contextvars
import logging
import threading

import pytest

from strata.config import load_thresholds
from strata.lakehouse.engine import (DuckDBEngine, PermissionDenied, Result, Waits, WarehouseEngine,
                                     read_together, run_many)

STATEMENTS = "/api/2.0/sql/statements/"


def answered(statement_id: str, value: str) -> dict:
    return {"statement_id": statement_id, "status": {"state": "SUCCEEDED"},
            "manifest": {"schema": {"columns": [{"name": "value", "position": 0}]}},
            "result": {"data_array": [[value]]}}


class AllAtOnce:
    """A warehouse that answers a POST only once every statement of the batch has arrived: statements sent one after
    another never all arrive, so the barrier breaks and the batch fails."""

    def __init__(self, count: int):
        self.barrier = threading.Barrier(count, timeout=5)
        self.calls, self.lock = [], threading.Lock()

    def __call__(self, method, path, body):
        with self.lock:
            self.calls.append((method, path, body))
        self.barrier.wait()
        return answered(f"s-{body['statement']}", body["statement"].removeprefix("SELECT "))


def test_the_warehouse_posts_a_page_s_statements_at_once_and_answers_each_in_order():
    warehouse = AllAtOnce(3)

    results = WarehouseEngine("wh-1", warehouse).run_many([("SELECT a", None), ("SELECT b", {"x": 1}),
                                                             ("SELECT c", None)])

    assert [result.rows for result in results] == [(("a",),), (("b",),), (("c",),)]
    assert sorted(call[2]["statement"] for call in warehouse.calls) == ["SELECT a", "SELECT b", "SELECT c"]
    assert all(call[:2] == ("POST", STATEMENTS) for call in warehouse.calls)


class OneRefused:
    """A warehouse that refuses one statement for a missing grant and answers the rest."""

    def __call__(self, method, path, body):
        if body["statement"] == "SELECT b":
            return {"statement_id": "s-b", "status": {"state": "FAILED", "error": {
                "error_code": "PERMISSION_DENIED", "message": "User does not have SELECT on b."}}}
        return answered(f"s-{body['statement']}", body["statement"].removeprefix("SELECT "))


def test_a_statement_that_failed_in_the_batch_raises_its_error_only_when_the_page_runs_it():
    # A page that reads on past a failed read (the Timeline, when get_disagreements fails) still does: the batch
    # keeps the error for the statement that failed and answers the others.
    statements = [("SELECT a", None), ("SELECT b", None), ("SELECT c", None)]
    batch = read_together(WarehouseEngine("wh-1", OneRefused()), statements)

    assert batch.run("SELECT a").rows == (("a",),)
    assert batch.run("SELECT c").rows == (("c",),)
    with pytest.raises(PermissionDenied, match="does not have SELECT on b"):
        batch.run("SELECT b")
    assert batch.missed == []
    # Asked for its results alone, the batch still raises the first error.
    with pytest.raises(PermissionDenied):
        WarehouseEngine("wh-1", OneRefused()).run_many(statements)


class StillRunning:
    """A warehouse whose statement is still running when the POST comes back and for `polls` reads after it."""

    def __init__(self, polls: int):
        self.polls, self.calls = polls, []

    def __call__(self, method, path, body):
        self.calls.append((method, path, body["wait_timeout"] if body else None))
        if method == "POST" or self.polls:
            self.polls -= method == "GET"
            return {"statement_id": "s-1", "status": {"state": "RUNNING"}}
        return answered("s-1", "done")


class Counted:
    """An engine that counts its round trips: each run alone, and each batch run_many sends."""

    def __init__(self, engine):
        self.engine, self.runs, self.batches = engine, [], []

    def run(self, sql, params=None):
        self.runs.append(sql)
        return self.engine.run(sql, params)

    def run_many(self, statements, return_exceptions=False):
        self.batches.append([sql for sql, _ in statements])
        return self.engine.run_many(statements, return_exceptions=return_exceptions)


def test_a_page_reads_each_of_its_statements_from_one_batch_and_runs_alone_only_what_the_batch_missed(caplog):
    with DuckDBEngine.open() as duckdb, caplog.at_level(logging.WARNING, logger="strata.lakehouse.engine"):
        engine = Counted(duckdb)
        batch = read_together(engine, [("SELECT :n AS n", {"n": 1}), ("SELECT :n AS n", {"n": 2}),
                                       ("SELECT :n AS n", {"n": 1})])

        assert batch.run("SELECT :n AS n", {"n": 2}).rows == ((2,),)
        assert batch.run("SELECT :n AS n", {"n": 1}).rows == ((1,),)
        assert batch.run("SELECT :n AS n", {"n": 1}).rows == ((1,),)  # read twice, run once
        assert engine.batches == [["SELECT :n AS n", "SELECT :n AS n"]]  # the same statement is sent once
        assert engine.runs == []

        assert caplog.records == []
        assert batch.run("SELECT :n AS n", {"n": 3}).rows == ((3,),)
        assert engine.runs == ["SELECT :n AS n"]
        assert batch.missed == ["SELECT :n AS n"]
        # The App's log says so, since only a test reads missed: a page whose statement drifted from its reads.
        assert "took one more round trip: SELECT :n AS n" in caplog.text


def test_run_many_on_a_page_s_batch_sends_one_more_batch_of_only_what_it_does_not_hold():
    with DuckDBEngine.open() as duckdb:
        engine = Counted(duckdb)
        batch = read_together(engine, [("SELECT :n AS n", {"n": 1})])

        results = run_many(batch, [("SELECT :n AS n", {"n": 1}), ("SELECT :n + 0 AS n", {"n": 2})])

        assert [result.rows for result in results] == [((1,),), ((2,),)]
        assert engine.batches == [["SELECT :n AS n"], ["SELECT :n + 0 AS n"]]
        assert engine.runs == [] and batch.missed == []


def test_each_statement_of_a_batch_runs_in_the_request_s_context_so_its_trace_stays_under_the_request():
    # OpenTelemetry keeps the request's span in a context variable, which a thread pool does not carry by itself
    # (ticket 125's review, follow-up 1).
    request = contextvars.ContextVar("request")
    seen = []

    def warehouse(method, path, body):
        seen.append(request.get(None))
        return answered("s-1", "x")

    def page():
        request.set("GET /api/projects/P156634/summary")
        WarehouseEngine("wh-1", warehouse).run_many([("SELECT a", None), ("SELECT b", None), ("SELECT c", None)])

    contextvars.copy_context().run(page)

    assert seen == ["GET /api/projects/P156634/summary"] * 3


def test_an_engine_with_no_batch_of_its_own_runs_the_statements_one_after_another():
    class Plain:
        def __init__(self):
            self.runs = []

        def run(self, sql, params=None):
            self.runs.append((sql, params))
            return Result(("n",), ((params["n"],),))

    plain = Plain()

    assert [result.rows for result in run_many(plain, [("SELECT :n", {"n": 1}), ("SELECT :n", {"n": 2})])] == [
        ((1,),), ((2,),)]
    assert plain.runs == [("SELECT :n", {"n": 1}), ("SELECT :n", {"n": 2})]


def test_a_statement_still_running_is_asked_about_again_soon_then_less_often():
    # A short first wait, so a statement just past the warehouse's hold is not kept two seconds more; each later
    # wait doubles, up to the longest, so a slow one is not asked about many times a second.
    slept, warehouse = [], StillRunning(polls=4)
    waits = Waits(wait_seconds=10, poll_seconds=0.25, poll_max_seconds=1, statements_at_once=8)

    result = WarehouseEngine("wh-1", warehouse, sleep=slept.append, waits=waits).run("SELECT 1")

    assert result.rows == (("done",),)
    assert warehouse.calls[0] == ("POST", STATEMENTS, "10s")
    assert slept == [0.25, 0.5, 1, 1, 1]


def test_the_engine_s_waits_are_read_from_the_thresholds_file():
    thresholds = load_thresholds()
    warehouse = StillRunning(polls=0)

    engine = WarehouseEngine("wh-1", warehouse, sleep=lambda seconds: None)
    engine.run("SELECT 1")

    assert engine.waits == Waits(**{key: thresholds.value(f"warehouse.{key}") for key in (
        "wait_seconds", "poll_seconds", "poll_max_seconds", "statements_at_once")})
    assert warehouse.calls[0][2] == f"{thresholds.value('warehouse.wait_seconds')}s"
