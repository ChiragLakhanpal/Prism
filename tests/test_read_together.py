"""A page's reads, run together (ticket 125): the engine's run_many and the batch a page reads from.

On the workspace, each statement costs the SQL warehouse's statements API about two seconds, so a page that ran its
six statements one after another took over ten. run_many posts a page's statements at once and waits once, and
together() gives a page an engine that answers each of its reads from that one batch. The warehouse is a fake of the
Statement Execution API here, as in tests/test_engine.py; the workspace step in the ticket's report times the real one.
"""

import threading

import pytest

from strata.config import load_thresholds
from strata.lakehouse.engine import DuckDBEngine, Result, Waits, WarehouseEngine, read_together, run_many

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

    def run_many(self, statements):
        self.batches.append([sql for sql, _ in statements])
        return self.engine.run_many(statements)


def test_a_page_reads_each_of_its_statements_from_one_batch_and_runs_alone_only_what_the_batch_missed():
    with DuckDBEngine.open() as duckdb:
        engine = Counted(duckdb)
        batch = read_together(engine, [("SELECT :n AS n", {"n": 1}), ("SELECT :n AS n", {"n": 2}),
                                       ("SELECT :n AS n", {"n": 1})])

        assert batch.run("SELECT :n AS n", {"n": 2}).rows == ((2,),)
        assert batch.run("SELECT :n AS n", {"n": 1}).rows == ((1,),)
        assert batch.run("SELECT :n AS n", {"n": 1}).rows == ((1,),)  # read twice, run once
        assert engine.batches == [["SELECT :n AS n", "SELECT :n AS n"]]  # the same statement is sent once
        assert engine.runs == []

        assert batch.run("SELECT :n AS n", {"n": 3}).rows == ((3,),)
        assert engine.runs == ["SELECT :n AS n"]
        assert batch.missed == ["SELECT :n AS n"]


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
