"""The data readiness measures each run writes to strata.ops.data_readiness (spec, "Data readiness
and the dashboard"): coverage (rows and years), linked (to STEP references, notices and projects),
fresh (as of, with the cadence) and the contact details removed, per source and country. Each is a
count with its denominator, or a date. There is no composite score.

Each source's measures are defined once, in <source>.sql in this folder: a query that returns
source, country_code, measure, numerator, denominator, as_of and detail. measure() runs each one
for the sources in the registry and adds its rows under the run's id. A source with no file here
has no measures yet.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from importlib import resources

from strata.config import load_sources
from strata.lakehouse.engine import Engine

COLUMNS = "run_id, source, country_code, measure, numerator, denominator, as_of, detail, measured_at, public_from"


def _query(source: str) -> str | None:
    # importlib.resources rather than __file__, which serverless Python tasks do not set.
    path = resources.files("strata.lakehouse.readiness") / f"{source}.sql"
    if not path.is_file():
        return None
    return "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("--"))


def measure(engine: Engine, run_id: str, clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)) -> int:
    """Write this run's measures for every source that has them. Returns how many rows it wrote."""
    measured_at = clock()
    written = 0
    for source in load_sources().values():
        query = _query(source.key)
        if query is None:
            continue
        written += len(engine.run(f"SELECT 1 AS one FROM ({query}) AS m", {"cadence": source.cadence}).rows)  # sql-lint: names only
        engine.run(  # sql-lint: names only
            f"INSERT INTO strata.ops.data_readiness ({COLUMNS}) "
            f"SELECT :run_id, m.source, m.country_code, m.measure, m.numerator, m.denominator, m.as_of, m.detail, "
            f":measured_at, :public_from FROM ({query}) AS m",
            {"run_id": run_id, "cadence": source.cadence, "measured_at": measured_at,
             "public_from": measured_at.astimezone(dt.UTC).date()})
    return written
