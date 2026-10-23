"""Usage events and traces at seam 3: each request a viewer makes writes one usage event to
strata.ops.usage_events (viewer, route, view and time, for the adoption measures) and sends one
trace, whose id the event keeps. The viewer is kept by the user id the App forwards, never by
email, because every account user can read strata.ops.

The events go to a DuckDB catalog in the test's own folder, through the same table definition the
deploy creates on the warehouse. The traces go to OpenTelemetry's in-memory exporter; on the
Databricks App the same spans go to Application Insights (a workspace step).
"""

import asyncio
import datetime as dt
import time

import duckdb
import httpx
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app
from strata.server.engines import duckdb_file
from strata.server.usage import UsageLog

ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}
BEN = {
    "X-Forwarded-Email": "ben.example@worldbank.org",
    "X-Forwarded-User": "4022@1984",
    "X-Forwarded-Access-Token": "token-for-ben-only",
}


def serve(app, requests, before_stopping=lambda: None):
    """Start the app as a server does, make the requests in turn, and stop it."""
    async def go():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                responses = [await client.get(path, headers=headers) for path, headers in requests]
            before_stopping()
            return responses
    return asyncio.run(go())


@pytest.fixture
def ops(tmp_path):
    path = tmp_path / "strata.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


def events(path):
    with DuckDBEngine.open(path, read_only=True) as engine:
        return engine.run("SELECT viewer_id, route, view, requested_at, trace_id, public_from "
                          "FROM strata.ops.usage_events ORDER BY requested_at").rows


def test_each_request_writes_one_usage_event_with_its_viewer_route_view_and_time(ops):
    usage = UsageLog(lambda: DuckDBEngine.open(ops), flush_seconds=None)
    before = dt.datetime.now(dt.UTC)

    serve(create_app(usage=usage), [
        ("/api/me", ANA),
        ("/api/freshness?view=public&asof=2016-08-26", BEN),
        ("/api/me", {}),
        ("/api/health", {}),  # the platform's check, not a viewer's request
    ])

    after = dt.datetime.now(dt.UTC)
    rows = events(ops)
    assert [row[:3] for row in rows] == [
        ("4021@1984", "/api/me", "staff"),
        # Until ticket 40, every request sees the World Bank staff view, whatever the link asks for.
        ("4022@1984", "/api/freshness", "staff"),
        (None, "/api/me", "staff"),
    ]
    assert all(before <= row[3] <= after for row in rows)
    assert all(row[5] == row[3].date() for row in rows)


def test_a_usage_event_keeps_no_email(ops):
    usage = UsageLog(lambda: DuckDBEngine.open(ops), flush_seconds=None)

    serve(create_app(usage=usage), [("/api/me", ANA)])

    with DuckDBEngine.open(ops, read_only=True) as engine:
        everything = engine.run("SELECT * FROM strata.ops.usage_events").rows
        columns = engine.run("SELECT column_name FROM information_schema.columns "
                             "WHERE table_schema = 'ops' AND table_name = 'usage_events'").rows
    assert len(everything) == 1
    assert "ana.example@worldbank.org" not in str(everything)
    assert not [name for (name,) in columns if "email" in name]


def test_the_events_wait_for_one_insert_and_the_server_writes_them_when_it_stops(ops):
    inserts = []

    class Counting(DuckDBEngine):
        def insert_rows(self, table, columns, rows, chunk=500):
            inserts.append(len(rows))
            return super().insert_rows(table, columns, rows, chunk)

    usage = UsageLog(lambda: Counting(DuckDBEngine.open(ops).connection), flush_seconds=None)
    waiting = []

    serve(create_app(usage=usage), [("/api/me", ANA)] * 3, before_stopping=lambda: waiting.extend(inserts))

    assert waiting == []
    assert inserts == [3]
    assert len(events(ops)) == 3


def test_the_server_writes_waiting_events_every_few_seconds(ops):
    usage = UsageLog(lambda: DuckDBEngine.open(ops), flush_seconds=0.05)
    written = []

    def wait_for_the_writer():
        for _ in range(100):
            try:
                found = events(ops)
            except duckdb.Error:  # the writer holds the file at this moment; look again
                found = []
            if found:
                written.extend(found)
                break
            time.sleep(0.02)

    serve(create_app(usage=usage), [("/api/me", ANA)], before_stopping=wait_for_the_writer)

    assert len(written) == 1


def test_each_request_sends_one_trace_and_its_usage_event_keeps_the_trace_id(ops):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    usage = UsageLog(lambda: DuckDBEngine.open(ops), flush_seconds=None)

    serve(create_app(usage=usage, tracer_provider=provider), [("/api/me", ANA), ("/api/health", {})])

    [span] = exporter.get_finished_spans()
    assert span.name == "GET /api/me"
    assert span.attributes["url.path"] == "/api/me"
    assert span.attributes["http.response.status_code"] == 200
    assert span.attributes["strata.view"] == "staff"
    assert "token-for-ana-only" not in str(dict(span.attributes))
    [row] = events(ops)
    assert row[4] == format(span.context.trace_id, "032x")


def traced():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider


def test_an_api_span_is_named_by_its_route_so_each_project_shares_one_operation():
    exporter, provider = traced()
    app = create_app(tracer_provider=provider, engine_for=duckdb_file("/nowhere/strata.duckdb"))

    serve(app, [("/api/projects/P130164/procurement/AGENCY-1", ANA), ("/api/projects/P156634/procurement/AGENCY-2", ANA)])

    assert [span.name for span in exporter.get_finished_spans()] == [
        "GET /api/projects/{project_id}/procurement/{agency_id}"] * 2


def test_a_failed_request_s_reference_is_its_trace_in_application_insights():
    exporter, provider = traced()
    app = create_app(tracer_provider=provider, engine_for=duckdb_file("/nowhere/strata.duckdb"))

    [response] = serve(app, [("/api/projects/P130164/procurement/AGENCY-1", ANA)])

    [span] = exporter.get_finished_spans()
    assert response.status_code == 503
    assert response.json() == {"code": "data_service", "trace_id": format(span.context.trace_id, "032x")}


def test_a_usage_log_that_cannot_write_never_breaks_a_request():
    def broken():
        raise OSError("the warehouse is not answering")

    [response] = serve(create_app(usage=UsageLog(broken, flush_seconds=None)), [("/api/me", ANA)])

    assert response.status_code == 200
