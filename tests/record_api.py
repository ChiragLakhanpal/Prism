"""Writes the Data tab's recorded API answers in tests/fixtures/api from the server itself (ticket 16).

The screen tests serve these files from their mocked API, and tests/test_data_routes.py checks that
the server still answers with them, so the screens and the server cannot drift apart. Build the
fixture database first, then run:

    uv run --frozen python tests/record_api.py

Each answer comes from GET /api/data/readiness or /api/data/sources on the fixture database, as of
October 23, 2026, the day its sources were recorded and measured, except for three states the
fixture does not hold: no measures yet (an empty catalog), one source not measured yet (the
fixture's measures without WGI's), and the error answers, which are the server's own bodies.
"""

import asyncio
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strata.config import load_thresholds  # noqa: E402
from strata.lakehouse import catalog  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Access-Token": "token-for-ana-only"}
DAY = "asof=2026-10-23"

FROM_THE_FIXTURE = {
    "data-readiness.json": f"/api/data/readiness?{DAY}",
    "data-readiness-filtered.json": f"/api/data/readiness?sources=awards,notices&from=find_comparables&{DAY}",
    "data-readiness-unknown-key.json": f"/api/data/readiness?sources=awards,not-a-source&from=find_comparables&{DAY}",
    "data-readiness-no-known-key.json": f"/api/data/readiness?sources=not-a-source&{DAY}",
    "data-readiness-before-first.json": "/api/data/readiness?asof=2026-10-01",
    "data-sources.json": "/api/data/sources",
}
# The states the fixture does not hold: the database each is read from, and the address.
EMPTY = "data-readiness-empty.json"
UNMEASURED = "data-readiness-unmeasured.json"
# The server's own bodies for the errors (src/strata/server/app.py).
ERRORS = {
    "data-readiness-no-access.json": {"code": "permission"},
    "data-readiness-error.json": {"code": "unreadable"},
    "data-readiness-timeout.json": {"code": "timeout",
                                    "timeout_seconds": load_thresholds().value("app.stamp_timeout_seconds")},
}


def answer(database: Path, path: str) -> dict:
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    async def go():
        transport = httpx.ASGITransport(app=create_app(engine_for=engine_for))
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            response = await client.get(path, headers=ANA)
            response.raise_for_status()
            return response.json()
    return asyncio.run(go())


def without_wgi(folder: Path) -> Path:
    """A catalog holding the fixture's measures for every source but WGI."""
    path = folder / "without-wgi.duckdb"
    with DuckDBEngine.open(FIXTURE_DB, read_only=True) as fixture:
        measured = fixture.run("SELECT * FROM strata.ops.data_readiness WHERE source <> :left_out", {"left_out": "wgi"})
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
        engine.insert_rows("strata.ops.data_readiness", measured.columns, list(measured.rows))
    return path


def empty(folder: Path) -> Path:
    path = folder / "empty.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


def answers() -> dict[str, dict]:
    found = {name: answer(FIXTURE_DB, path) for name, path in FROM_THE_FIXTURE.items()}
    with tempfile.TemporaryDirectory() as folder:
        found[EMPTY] = answer(empty(Path(folder)), f"/api/data/readiness?{DAY}")
        found[UNMEASURED] = answer(without_wgi(Path(folder)), f"/api/data/readiness?{DAY}")
    return found | ERRORS


def written(body: dict) -> str:
    return json.dumps(body, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    for name, body in answers().items():
        (OUT / name).write_text(written(body))
        print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
