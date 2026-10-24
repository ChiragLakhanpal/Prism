"""Writes the Data tab's recorded API answers, and the evidence drawer's answers for each kind of passage,
in tests/fixtures/api from the server itself (tickets 16 and 18).

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
    "data-readiness-plan-check.json": f"/api/data/readiness?sources=documents,projects&from=check_plan&{DAY}",
    "data-readiness-unknown-key.json": f"/api/data/readiness?sources=awards,not-a-source&from=find_comparables&{DAY}",
    "data-readiness-no-known-key.json": f"/api/data/readiness?sources=not-a-source&{DAY}",
    "data-readiness-before-first.json": "/api/data/readiness?asof=2026-10-01",
    "data-sources.json": "/api/data/sources",
    # The evidence drawer's answers, one for each kind of passage (tickets 14 and 18): a paragraph of
    # published text, an ISR's section, a paragraph the layout parser read from a scan, a row of the PAD's
    # risk table and the table's summary, a section of a notice's text with contact details removed, and a
    # paragraph of the completion report in French.
    "evidence-icr-p130164-54.json": "/api/evidence?id=strata.gold.passage:31525018/v1/54",
    "evidence-isr-p130164-s4.json": "/api/evidence?id=strata.gold.passage:19095337/v1/s4",
    "evidence-pad-p130164-scanned.json": "/api/evidence?id=strata.gold.passage:18381488/v1/23",
    "evidence-pad-p130164-risk-row.json": "/api/evidence?id=strata.gold.passage:18381488/v1/table65.2",
    "evidence-pad-p130164-risk-summary.json": "/api/evidence?id=strata.gold.passage:18381488/v1/table65",
    "evidence-notice-op00118817.json": "/api/evidence?id=strata.gold.passage:OP00118817/v1/s8",
    "evidence-icr-p127203-fr.json": "/api/evidence?id=strata.gold.passage:33407968/v1/1",
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


# The hardest documents' states the fixture does not reach (ticket 18), each the fixture's measures with
# its shelf outcomes changed, so the server builds the page from them: a Gap (nothing recovered from the
# risk annex, recorded as unreadable) and a Partial; each abstention (no hand count, stopped at the
# daily page cap, not read yet, no document fits); and a shelf never read.
SHELF_STATES = {
    "data-readiness-shelf-gap.json": [
        ("UPDATE strata.ops.stress_shelf SET count = 0, unreadable = true WHERE shelf_key = :key", {"key": "p130164_pad"}),
        ("UPDATE strata.ops.stress_shelf SET count = 80 WHERE shelf_key = :key", {"key": "longest_pad"}),
    ],
    "data-readiness-shelf-abstentions.json": [
        ("UPDATE strata.ops.stress_shelf SET denominator = NULL, denominator_from = NULL, counted_on = NULL "
         "WHERE shelf_key = :key", {"key": "p130164_pad"}),
        ("UPDATE strata.ops.stress_shelf SET state = 'no_document', document_id = NULL, project_id = NULL "
         "WHERE shelf_key = :key", {"key": "longest_pad"}),
        ("UPDATE strata.ops.stress_shelf SET state = 'stopped_at_cap', read_pages = 6, daily_page_cap = 30 "
         "WHERE shelf_key = :key", {"key": "long_plan"}),
        ("DELETE FROM strata.ops.stress_shelf WHERE shelf_key = :key", {"key": "french_report"}),
    ],
    "data-readiness-shelf-two-gaps.json": [
        ("UPDATE strata.ops.stress_shelf SET count = 0, unreadable = true WHERE shelf_key = :key", {"key": "p130164_pad"}),
        ("UPDATE strata.ops.stress_shelf SET count = 0 WHERE shelf_key = :key", {"key": "longest_pad"}),
    ],
    "data-readiness-shelf-empty.json": [("DELETE FROM strata.ops.stress_shelf WHERE run_id = :run", {"run": "fixture"})],
}


def with_shelf(folder: Path, name: str, database: Path = FIXTURE_DB) -> Path:
    """A copy of the fixture database with its shelf outcomes changed for one state."""
    import shutil

    path = folder / name.replace(".json", ".duckdb")
    shutil.copy(database, path)
    with DuckDBEngine.open(path) as engine:
        for sql, params in SHELF_STATES[name]:
            engine.run(sql, params)
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
        for name in SHELF_STATES:
            found[name] = answer(with_shelf(Path(folder), name), f"/api/data/readiness?{DAY}")
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
