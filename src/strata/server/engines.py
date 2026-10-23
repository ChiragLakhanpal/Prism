"""Which engine runs a viewer's queries, made fresh for each request.

Strata acts as each viewer (ADR 0003): in the Databricks App, every query goes to the SQL warehouse
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
                        transport: Callable[[str, str], Transport] = http_transport) -> EngineFor:
    """The SQL warehouse, called with the viewer's own forwarded token."""
    @contextmanager
    def engine_for(viewer: Viewer) -> Iterator[Engine]:
        if not viewer.token:
            raise PermissionDenied("The Databricks App forwarded no token for this viewer, so I ran nothing.")
        yield WarehouseEngine(warehouse_id, transport(host, viewer.token))
    return engine_for


def from_environment(environ: Mapping[str, str] = os.environ) -> EngineFor | None:
    """The engine the environment names, or None when it names none."""
    if path := environ.get("STRATA_DATABASE_FILE", "").strip():
        return duckdb_file(path)
    host, warehouse = environ.get("DATABRICKS_HOST", "").strip(), environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    return warehouse_as_viewer(host, warehouse) if host and warehouse else None
