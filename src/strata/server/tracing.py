"""Traces: one span for each request a viewer makes, sent to Application Insights on the App.

The server makes its spans with OpenTelemetry's API, through the tracer provider create_app is
given, or the process's global one. On the Databricks App, from_env() points the global provider
at Application Insights with Azure Monitor's OpenTelemetry distribution, which reads the
connection string the app's secret resource sets. Its own FastAPI instrumentation stays off,
because the server makes the request spans itself; its urllib instrumentation stays on, so each
call to the warehouse shows as a dependency of the request that made it. With no connection
string, the spans go nowhere.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from opentelemetry import trace

log = logging.getLogger("strata.server.tracing")
CONNECTION_STRING = "APPLICATIONINSIGHTS_CONNECTION_STRING"
# Instrumentations the distribution would turn on that the app has no use for.
SWITCHED_OFF = ("fastapi", "django", "flask", "psycopg2", "requests", "azure_sdk")


def from_env(environ: Mapping[str, str]) -> trace.TracerProvider | None:
    """The provider that sends spans to Application Insights, or None when the app has no
    connection string. Tracing that cannot start never stops the app."""
    connection_string = environ.get(CONNECTION_STRING, "").strip()
    if not connection_string:
        return None
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(connection_string=connection_string,
                                instrumentation_options={name: {"enabled": False} for name in SWITCHED_OFF})
    except Exception:  # an import or a malformed connection string: the app answers without traces
        log.exception("I could not start sending traces to Application Insights.")
        return None
    return trace.get_tracer_provider()


def trace_id(span: trace.Span) -> str | None:
    context = span.get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None
