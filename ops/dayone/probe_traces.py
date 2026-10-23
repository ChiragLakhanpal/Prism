# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0"]
# ///
"""Day-one test 10: traces reach Application Insights from the app.

Run it from the main checkout after the wizard:

    uv run --script ops/dayone/probe_traces.py --env-file .env

It deploys the probe app if it is not running yet, asks it to send one span with a new marker,
and then asks Application Insights for that marker for up to ten minutes, because traces take
a few minutes to arrive. The query uses the Azure command line the wizard signed in. It writes
test 10 in docs/day-one-results.md.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dayone  # noqa: E402
from dayone import Outcome, ProbeError, SetupError  # noqa: E402

NEEDS = ["DATABRICKS_HOST", "APPLICATIONINSIGHTS_CONNECTION_STRING"]


def check(traces, env: dict, config: dict) -> Outcome:
    marker = f"strata-dayone-{uuid.uuid4().hex[:12]}"
    evidence = [f"Marker: {marker}."]
    try:
        sent = traces.send(marker)
    except SetupError as error:
        return dayone.not_run(error, evidence)
    except ProbeError as error:
        evidence.append(str(error))
        return Outcome("failed", "The app could not send a trace.", evidence)
    if sent.get("app"):
        evidence.append(f"App: {sent['app']}.")
    if sent.get("error"):
        evidence.append(sent["error"])
        return Outcome("failed", "The app could not send a trace.", evidence)
    evidence.append(f"The app sent trace {sent.get('trace_id')}.")
    try:
        rows = traces.find(marker)
    except SetupError as error:
        return dayone.not_run(error, evidence)
    except ProbeError as error:
        evidence.append(str(error))
        return Outcome("failed", "I could not ask Application Insights for the trace.", evidence)
    if not rows:
        return Outcome("failed", "The app sent a trace, and it did not reach Application Insights within ten "
                                 "minutes.", evidence)
    evidence.append(f"Application Insights holds it: {', '.join(str(part) for part in rows[0])}.")
    return Outcome("passed", "A trace the app sent reached Application Insights.", evidence)


class CannedTraces:
    """An app whose trace arrives, for --dry-run."""

    def __init__(self, env: dict, config: dict):
        self.app = f"https://{config['names']['app']}-dry-run.databricksapps.com"

    def send(self, marker):
        return {"trace_id": "0" * 32, "flushed": True, "app": self.app}

    def find(self, marker):
        return [["dry-run", "dependency", "0" * 32]]


def live(env: dict, config: dict):
    from live import LiveTraces
    return LiveTraces(env, config)


def main(argv: list[str] | None = None, service=None) -> int:
    return dayone.run_probe(10, argv, __doc__, NEEDS, live, CannedTraces, check, service)


if __name__ == "__main__":
    sys.exit(main())
