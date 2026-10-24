"""The engine adapter: the same SQL text and parameters reach the warehouse, Spark and DuckDB.

The warehouse is reached through a recorded-shape fake of the Statement Execution API, because
the offline tests never leave this computer. The workspace step `ops/bundle/check.py same-rows`
runs the real thing.
"""

import datetime as dt
import io
import urllib.error
import urllib.request

import pytest

from strata.lakehouse.engine import (DuckDBEngine, EngineError, PermissionDenied, SparkEngine, WarehouseEngine,
                                     http_transport)

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


@pytest.mark.parametrize("error", [
    {"error_code": "BAD_REQUEST", "message": "[INSUFFICIENT_PERMISSIONS] Insufficient privileges:\n"
                                             "User does not have USE CATALOG on Catalog 'strata'. SQLSTATE: 42501"},
    {"error_code": "PERMISSION_DENIED", "message": "User does not have SELECT on Table 'strata.gold.project'."},
], ids=["missing-grant", "permission-denied"])
def test_a_statement_refused_for_a_missing_grant_raises_permission_denied(error):
    warehouse = FakeWarehouse([{"statement_id": "s-1", "status": {"state": "FAILED", "error": error}}])

    with pytest.raises(PermissionDenied):
        WarehouseEngine("wh-1", warehouse).run(SQL)


@pytest.mark.parametrize("code, refused", [(401, PermissionDenied), (403, PermissionDenied), (500, EngineError)])
def test_a_token_the_workspace_refuses_raises_permission_denied(monkeypatch, code, refused):
    def urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, code, "Refused", {}, io.BytesIO(b'{"message": "Refused."}'))

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(refused) as raised:
        http_transport("strata.test", "not-a-real-key")("POST", "/api/2.0/sql/statements/", {})
    assert isinstance(raised.value, PermissionDenied) == (refused is PermissionDenied)


def test_spark_gets_the_same_text_and_named_parameters():
    class FakeSpark:
        def sql(self, text, args=None):
            self.seen = (text, args)
            return type("Frame", (), {"columns": ["n"], "collect": lambda frame: [(1,)]})()

    spark = FakeSpark()
    result = SparkEngine(spark).run(SQL, {"as_of": "2018-12-31"})

    assert spark.seen == (SQL, {"as_of": "2018-12-31"})
    assert result.as_text() == [("1",)]


def test_duckdb_writes_a_timestamp_and_a_date_the_way_the_warehouse_does():
    """The Statement Execution API writes a TIMESTAMP in UTC with milliseconds and a Z."""
    with DuckDBEngine.open() as engine:
        result = engine.run("SELECT TIMESTAMP '2026-10-23 23:30:00.123456' AS at, DATE '2026-10-23' AS day")

    assert result.as_text() == [("2026-10-23T23:30:00.123Z", "2026-10-23")]


def test_duckdb_takes_one_statement_per_call():
    with DuckDBEngine.open() as engine, pytest.raises(EngineError, match="one statement"):
        engine.run("SELECT 1; SELECT 2")


def test_the_transpile_step_refuses_what_duckdb_cannot_express_instead_of_dropping_it():
    with DuckDBEngine.open() as engine, pytest.raises(EngineError, match="transpile"):
        engine.run("CREATE TABLE strata.main.t (id STRING COMMENT 'the id', public_from DATE)")


# ── Rows that Python built ───────────────────────────────────────────────

ROWS = [("1624689", "503708", "NICHOLAS O'DWYER LIMITED"), ("1624689", "503711", None)]
COLUMNS = ("wb_contract_number", "supplier_id", "supplier")


def test_duckdb_adds_rows_with_every_value_bound_so_a_quote_in_a_name_stays_as_it_is():
    with DuckDBEngine.open() as engine:
        engine.run("CREATE SCHEMA strata.silver")
        engine.run("CREATE TABLE strata.silver.awards (wb_contract_number STRING, supplier_id STRING, supplier STRING)")

        added = engine.insert_rows("strata.silver.awards", COLUMNS, ROWS)

        assert added == 2
        assert engine.run("SELECT * FROM strata.silver.awards ORDER BY supplier_id").rows == tuple(ROWS)


def test_the_warehouse_splits_an_insert_whose_values_would_pass_the_apis_size_limit():
    # The Statement Execution API refuses parameters over 1,048,576 characters in all. Three pages of
    # layout elements at 400 characters each, with a budget of 1,000, go as two INSERTs: two rows, then one.
    pages = [("1", "1", "x" * 400), ("1", "2", "y" * 400), ("1", "3", "z" * 400)]
    warehouse = FakeWarehouse([succeeded([]), succeeded([])])

    added = WarehouseEngine("wh-1", warehouse).insert_rows("strata.bronze.layout_pages", COLUMNS, pages,
                                                           chunk_characters=1_000)

    assert added == 3
    statements = [call[2]["statement"] for call in warehouse.calls]
    assert statements[0].endswith("VALUES (:v0_0, :v0_1, :v0_2), (:v1_0, :v1_1, :v1_2)")
    assert statements[1].endswith("VALUES (:v0_0, :v0_1, :v0_2)")
    assert {"name": "v0_2", "value": "z" * 400, "type": "STRING"} in warehouse.calls[1][2]["parameters"]


def test_a_row_too_large_for_the_apis_parameters_is_refused_before_anything_is_sent():
    from strata.lakehouse.engine import RowTooLarge

    warehouse = FakeWarehouse([succeeded([])])
    text = ("1", "33218784", "x" * 1_001)

    with pytest.raises(RowTooLarge, match="1,010 characters of values.*at most 1,000"):
        WarehouseEngine("wh-1", warehouse).insert_rows("strata.bronze.document_texts", COLUMNS, [text],
                                                       chunk_characters=1_000)

    assert warehouse.calls == []


def test_the_warehouse_adds_rows_in_one_insert_whose_every_value_is_a_parameter():
    warehouse = FakeWarehouse([succeeded([])])

    WarehouseEngine("wh-1", warehouse).insert_rows("strata.silver.awards", COLUMNS, ROWS)

    body = warehouse.calls[0][2]
    assert body["statement"] == ("INSERT INTO strata.silver.awards (wb_contract_number, supplier_id, supplier) "
                                 "VALUES (:v0_0, :v0_1, :v0_2), (:v1_0, :v1_1, :v1_2)")
    assert {"name": "v0_2", "value": "NICHOLAS O'DWYER LIMITED", "type": "STRING"} in body["parameters"]
    assert {"name": "v1_2"} in body["parameters"]


def test_spark_adds_rows_as_a_frame_typed_by_the_table_and_appended_by_name():
    class FakeSpark:
        def __init__(self):
            self.calls = []

        def table(self, name):
            self.calls.append(("table", name))
            return type("Table", (), {"select": lambda table, *columns: type("Picked", (), {"schema": columns})()})()

        def createDataFrame(self, rows, schema):  # noqa: N802, the PySpark name
            self.calls.append(("frame", rows, schema))
            spark = self

            class Writer:
                def mode(self, mode):
                    spark.calls.append(("mode", mode))
                    return self

                def saveAsTable(self, name):  # noqa: N802, the PySpark name
                    spark.calls.append(("save", name))

            return type("Frame", (), {"write": Writer()})()

    spark = FakeSpark()
    SparkEngine(spark).insert_rows("strata.silver.awards", COLUMNS, ROWS)

    assert spark.calls == [("table", "strata.silver.awards"), ("frame", ROWS, COLUMNS), ("mode", "append"),
                           ("save", "strata.silver.awards")]


def test_adding_rows_takes_only_a_three_part_table_name():
    with DuckDBEngine.open() as engine, pytest.raises(EngineError, match="three-part table name"):
        engine.insert_rows("awards; SELECT 1", COLUMNS, ROWS)
