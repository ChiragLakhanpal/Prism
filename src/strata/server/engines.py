"""Which engine runs a viewer's queries, made fresh for each request.

Prism acts as each viewer (ADR 0003): in the Databricks App, every query goes to the SQL warehouse
with the token the App forwarded for the person asking, so each viewer sees only what their own
grants allow. Nothing about a viewer is kept between requests (CLAUDE.md rule 7). The environment
decides the engine once, when the app starts:

- STRATA_DATABASE_FILE names a DuckDB file, such as the gate's fixture database
  (data/out/fixture.duckdb), opened read-only for each request. For development and tests.
- Otherwise DATABRICKS_HOST and DATABRICKS_WAREHOUSE_ID name the workspace and its SQL warehouse.
  A request with no forwarded token is refused, never run with another identity.
- With neither, there is no data service, and the routes that need one say so.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

from strata.dbx import Viewer
from strata.lakehouse.engine import (DuckDBEngine, Engine, EngineError, PermissionDenied, Transport, WarehouseEngine,
                                     http_transport)

EngineFor = Callable[[Viewer], AbstractContextManager[Engine]]
# How long a warehouse query may run when nothing sets a shorter time: WarehouseEngine's own limit.
WAREHOUSE_TIMEOUT_SECONDS = 600


def duckdb_file(path: Path | str) -> EngineFor:
    """A local DuckDB file, opened read-only for each request. A file that cannot be opened, such as
    one not built yet, is the data service failing, so the route answers with a reference."""
    @contextmanager
    def engine_for(viewer: Viewer) -> Iterator[Engine]:
        try:
            engine = DuckDBEngine.open(path, read_only=True)
        except Exception as error:
            raise EngineError(f"I could not open {path}: {error}") from error
        with engine:
            yield engine
    return engine_for


def warehouse_as_viewer(host: str, warehouse_id: str,
                        transport: Callable[[str, str], Transport] = http_transport,
                        timeout_seconds: float = WAREHOUSE_TIMEOUT_SECONDS) -> EngineFor:
    """The SQL warehouse, called with the viewer's own forwarded token. Each query gives up after
    timeout_seconds, so a read the server has stopped waiting for does not hold its thread."""
    @contextmanager
    def engine_for(viewer: Viewer) -> Iterator[Engine]:
        if not viewer.token:
            raise PermissionDenied("The Databricks App forwarded no token for this viewer, so I ran nothing.")
        yield WarehouseEngine(warehouse_id, transport(host, viewer.token), timeout_seconds=timeout_seconds)
    return engine_for


def from_environment(environ: Mapping[str, str] = os.environ,
                     timeout_seconds: float = WAREHOUSE_TIMEOUT_SECONDS) -> EngineFor | None:
    """The engine the environment names, or None when it names none. A warehouse query gives up
    after timeout_seconds, which the app sets to the stamp's timeout."""
    if path := environ.get("STRATA_DATABASE_FILE", "").strip():
        return duckdb_file(path)
    host, warehouse = environ.get("DATABRICKS_HOST", "").strip(), environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    return warehouse_as_viewer(host, warehouse, timeout_seconds=timeout_seconds) if host and warehouse else None
