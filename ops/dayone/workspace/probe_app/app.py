"""Prism's day-one probe app, for tests 1 and 10.

probe_hosts.py and probe_traces.py deploy it under the app name in ops/dayone/dayone.toml. The
app shell ticket later deploys Prism itself under that name. Routes:

  /dayone          the app's version and whether tracing is on
  /dayone/reach    asks each World Bank host once and returns each HTTP status (test 1)
  /dayone/trace    sends one span to Application Insights with ?marker=... (test 10)

It uses the standard library's HTTP server, so it needs only the tracing package.
"""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SETTINGS = json.loads(os.environ.get("STRATA_DAYONE_SETTINGS") or "{}")
TRACING = ""
if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor()  # reads APPLICATIONINSIGHTS_CONNECTION_STRING
        TRACING = "on"
    except Exception as error:  # the app still answers test 1 without tracing
        TRACING = f"off: {type(error).__name__}: {error}"
else:
    TRACING = "off: the app has no Application Insights connection string"


def fetch_status(url, timeout=20):
    request = urllib.request.Request(url, headers={"User-Agent": "strata-dayone-probe"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception as error:  # DNS, a refused connection or a timeout: the host did not answer
        return f"no answer ({type(error).__name__}: {str(error)[:120]})"


def send_trace(marker):
    from opentelemetry import trace

    tracer = trace.get_tracer("strata.dayone")
    with tracer.start_as_current_span("strata-dayone-trace") as span:
        span.set_attribute("strata.dayone.marker", marker)
        trace_id = format(span.get_span_context().trace_id, "032x")
    flushed = trace.get_tracer_provider().force_flush(30000)
    return {"trace_id": trace_id, "flushed": bool(flushed)}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/dayone/reach":
            body = {host: fetch_status(address) for host, address in SETTINGS.get("hosts", {}).items()}
        elif url.path == "/dayone/trace":
            marker = parse_qs(url.query).get("marker", [""])[0]
            body = send_trace(marker) if TRACING == "on" else {"error": f"Tracing is {TRACING}."}
        else:
            body = {"app": "strata-dayone", "version": SETTINGS.get("version"), "tracing": TRACING}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("DATABRICKS_APP_PORT", "8000"))), Handler).serve_forever()
