"""Writes the "Advertised again" block's recorded answers in tests/fixtures/api from the server itself (ticket 28).

The screen tests and the design gallery serve these files, and tests/test_package_routes.py checks that the
server still answers with them, so section 1's block and the server cannot drift apart. Build the fixture
database first, then run:

    uv run --frozen python tests/record_rebidding_api.py

Each answer comes from the fixture database as of October 22, 2026, the date section 1's recorded answers use:

- rebidding-ke-nwwda-541055.json: the demo package with section 1's default criteria: three of the 52
  comparables were advertised again, the canceled ones put back, and the fixture holds no rebidding backtest,
  so the model is not shown (no_results).
- rebidding-ke-nwwda-541055-prior.json: with review type Prior, none of 7, too few for a model.
- rebidding-planned-works-rfb-ke.json: the rural roads package from a sentence, whose criteria are works under
  Request for Bids in Kenya, as /api/comparables takes them.
- evidence-notice-op00083890.json and evidence-plan-row-ke-kimawasco-157517.json: a notice whose words a row
  quotes, and a canceled plan row, as the evidence drawer opens them.
- evidence-plan-row-ke-nwwda-541055.json: the demo package's own plan row, which the marker of the package page's
  facts, "From the plan row", and its "Show the plan row" open in the evidence drawer (ticket 101).

The block's other states (the model shown, a group of more than five, a second notice under the same STEP
reference, a reason in French, the error) are not in the fixture. They are mocks in tests/fixtures/api whose names
start with rebidding-mock-, written by hand from the same shape, with numbers of their own.
"""

import asyncio
import json
import sys
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Access-Token": "token-for-ana-only",
       "X-Forwarded-Preferred-Username": "Ana Example", "X-Forwarded-User": "4021@1984"}
DEMO = "/api/packages/KE-NWWDA-541055-CW-RFB"
ANSWERS = {
    "rebidding-ke-nwwda-541055.json": f"{DEMO}/rebidding",
    "rebidding-ke-nwwda-541055-prior.json": f"{DEMO}/rebidding?review_type=Prior",
    "rebidding-planned-works-rfb-ke.json": "/api/rebidding?category=Works&country=KE&method=Request%20for%20Bids",
    "evidence-notice-op00083890.json": "/api/evidence?id=strata.silver.notices:OP00083890",
    "evidence-plan-row-ke-kimawasco-157517.json": "/api/evidence?id=strata.silver.plan_rows:40001676/KE-KIMAWASCO-157517-CW-RFB",
    "evidence-plan-row-ke-nwwda-541055.json": "/api/evidence?id=strata.silver.plan_rows:40132287/KE-NWWDA-541055-CW-RFB",
}


def answers() -> dict[str, str]:
    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(FIXTURE_DB, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=reading)

    async def story() -> dict[str, str]:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            found = {}
            for name, path in ANSWERS.items():
                response = await client.get(f"{path}{'&' if '?' in path else '?'}asof=2026-10-22", headers=ANA)
                found[name] = json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"
            return found

    return asyncio.run(story())


def main() -> int:
    for name, text in answers().items():
        (OUT / name).write_text(text)
        print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
