"""A run's trace ids, for the stream's done event and the run log.

- Application Insights: the trace id of the request's span. Ticket 06 makes one span per request with
  OpenTelemetry and sends it to Application Insights, and the live agent adapter passes the same trace
  on to Foundry in a traceparent header, so the app's span and the agent's spans share one operation
  id. Without OpenTelemetry, or outside a span, there is none.
- MLflow: no run has an MLflow trace yet. It stays empty until MLflow tracing is set up in the app.

current() is called in the request's route, while its span is open, never later in the stream.
"""

from __future__ import annotations

from strata.harness.turn import TraceIds


def _span_context():
    try:
        from opentelemetry import trace
    except ImportError:  # the app runs without traces
        return None
    context = trace.get_current_span().get_span_context()
    return context if context.is_valid else None


def current() -> TraceIds:
    context = _span_context()
    return TraceIds(application_insights=format(context.trace_id, "032x") if context else None)


def traceparent() -> str | None:
    """The W3C traceparent header for the current span, so Foundry's spans join the app's trace."""
    context = _span_context()
    if context is None:
        return None
    return f"00-{context.trace_id:032x}-{context.span_id:016x}-{int(context.trace_flags):02x}"
