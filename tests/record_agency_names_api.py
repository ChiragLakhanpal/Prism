"""Writes the Procurement tab's answers for P130164 with a plan whose agency its record writes another way (ticket 133),
in tests/fixtures/api, from the server itself on a copy of the fixture (tests/india_agency.py).

The screen test in web/tests/projects.spec.ts serves them, and tests/test_agency_names.py checks that the server still
answers with them. Build the fixture database first, then run:

    uv run --frozen python tests/record_agency_names_api.py
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from india_agency import RECORDED, app_on, give_p130164_a_plan  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Access-Token": "token-for-ana-only",
       "X-Forwarded-Preferred-Username": "Ana Example", "X-Forwarded-User": "4021@1984"}


async def record(app) -> dict[str, str]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
        found = {}
        for name, path in RECORDED.items():
            response = await client.get(path, headers=ANA)
            response.raise_for_status()
            found[name] = json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"
        return found


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        found = asyncio.run(record(app_on(give_p130164_a_plan(FIXTURE_DB, Path(folder)))))
    for name, text in found.items():
        (OUT / name).write_text(text)
        print(f"Wrote tests/fixtures/api/{name}.")


if __name__ == "__main__":
    main()
