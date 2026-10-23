"""The engine adapter: the same SQL text and parameters reach the warehouse, Spark and DuckDB.

The warehouse is reached through a recorded-shape fake of the Statement Execution API, because
the offline tests never leave this computer. The workspace step `ops/bundle/check.py same-rows`
runs the real thing.
"""

import datetime as dt

import pytest

from strata.lakehouse.engine import DuckDBEngine, EngineError, SparkEngine, WarehouseEngine

SQL = "SELECT event, happened_on FROM strata.ops.events WHERE happened_on <= CAST(:as_of AS DATE)"


class FakeWarehouse:
    """Answers like the Statement Execution API: maybe still running, then rows in chunks."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, method, path, body):
        self.calls.append((method, path, body))
        return self.replies.pop(0)


def succeeded(rows, link=None):
    return {"statement_id": "s-1", "status": {"state": "SUCCEEDED"},
            "manifest": {"schema": {"columns": [{"name": "happened_on", "position": 1},
                                                {"name": "event", "position": 0}]}},
            "result": {"data_array": rows, "next_chunk_internal_link": link}}


def test_the_warehouse_gets_one_statement_with_typed_named_parameters():
    warehouse = FakeWarehouse([succeeded([["ISR 7", "2016-08-26"]])])

    result = WarehouseEngine("wh-1", warehouse).run(SQL, {"as_of": dt.date(2018, 12, 31), "limit": 5,
                                                          "who": "ISR", "late": True, "none": None})

    method, path, body = warehouse.calls[0]
    assert (method, path) == ("POST", "/api/2.0/sql/statements/")
    assert body["statement"] == SQL
    assert body["warehouse_id"] == "wh-1"
    assert body["parameters"] == [
        {"name": "as_of", "value": "2018-12-31", "type": "DATE"},
        {"name": "limit", "value": "5", "type": "BIGINT"},
        {"name": "who", "value": "ISR", "type": "STRING"},
        {"name": "late", "value": "true", "type": "BOOLEAN"},
        {"name": "none"},
    ]
    assert result.columns == ("event", "happened_on")
    assert result.as_text() == [("ISR 7", "2016-08-26")]


def test_the_warehouse_engine_waits_for_a_running_statement_and_reads_every_chunk():
    warehouse = FakeWarehouse([
        {"statement_id": "s-1", "status": {"state": "RUNNING"}},
        succeeded([["ISR 7", "2016-08-26"]], link="/api/2.0/sql/statements/s-1/result/chunks/1"),
        {"data_array": [["ISR 12", "2018-04-10"]]},
    ])

    result = WarehouseEngine("wh-1", warehouse, sleep=lambda seconds: None).run(SQL, {"as_of": "2018-12-31"})

    assert [call[:2] for call in warehouse.calls[1:]] == [
        ("GET", "/api/2.0/sql/statements/s-1"), ("GET", "/api/2.0/sql/statements/s-1/result/chunks/1")]
    assert result.as_text() == [("ISR 7", "2016-08-26"), ("ISR 12", "2018-04-10")]


def test_a_statement_the_warehouse_refuses_raises_its_reason():
    warehouse = FakeWarehouse([{"statement_id": "s-1", "status": {
        "state": "FAILED", "error": {"message": "[TABLE_OR_VIEW_NOT_FOUND] strata.ops.events"}}}])

    with pytest.raises(EngineError, match="TABLE_OR_VIEW_NOT_FOUND"):
        WarehouseEngine("wh-1", warehouse).run(SQL)


def test_spark_gets_the_same_text_and_named_parameters():
    class FakeSpark:
        def sql(self, text, args=None):
            self.seen = (text, args)
            return type("Frame", (), {"columns": ["n"], "collect": lambda frame: [(1,)]})()

    spark = FakeSpark()
    result = SparkEngine(spark).run(SQL, {"as_of": "2018-12-31"})

    assert spark.seen == (SQL, {"as_of": "2018-12-31"})
    assert result.as_text() == [("1",)]


def test_duckdb_takes_one_statement_per_call():
    with DuckDBEngine.open() as engine, pytest.raises(EngineError, match="one statement"):
        engine.run("SELECT 1; SELECT 2")


def test_the_transpile_step_refuses_what_duckdb_cannot_express_instead_of_dropping_it():
    with DuckDBEngine.open() as engine, pytest.raises(EngineError, match="transpile"):
        engine.run("CREATE TABLE strata.main.t (id STRING COMMENT 'the id', public_from DATE)")
