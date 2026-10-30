"""Writes the recorded answers for find_comparables' period of notices in tests/fixtures/api (ticket 137).

The period starts with the awards data Strata holds, July 1, 2019 (config/thresholds.toml, past_range.period_from),
and by default ends on the plan's date, or on the as-of date for a plan older than its start. The screen tests build
section 1's note from these answers, and tests/test_comparables_period.py checks that the tool still gives them, so the
note and the tool cannot drift apart. Build the fixture database first, then run:

    uv run --frozen python tests/record_comparables_api.py

- notice-periods.json (not named comparables-*, which tests/test_package_routes.py reads as find_comparables
  answers): for every plan date the fixture holds (the plan versions its reader read, and every
  Procurement Plan its documents lists name), the period find_comparables compares packages from, as of the plan's
  own date and as of October 30, 2026: its start, its end and its case (criteria.period).
- package-in-rrsmp-7516.json and comparables-in-rrsmp-7516.json: P130164's package IN-RRSMP-7516-CW-RFB as of October
  30, 2026, the day the walkthrough's capture was taken again after the fix; comparables-in-rrsmp-7516-2018-12-01.json
  is the same as of December 1, 2018, before the awards data starts. The fixture reads no plan of P130164, so these
  come from a copy of the fixture database that holds the newest plan's row for the package (india_database).
"""

import asyncio
import datetime as dt
import json
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strata.config import load_thresholds  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.app import create_app  # noqa: E402
from strata.tools.find_comparables import period  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
DOCUMENTS = ROOT / "data" / "fixture" / "recorded" / "api" / "documents"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
INDIA_PACKAGE = "IN-RRSMP-7516-CW-RFB"
INDIA_PLAN = "30152361"  # P130164's Procurement Plan of June 20, 2018, the newest its documents list names
# The day the App showed the package's page after the redeploy, as the ticket's sentence names it.
AS_OF = dt.date(2026, 10, 30)
# A day after the plan of June 20, 2018 became public and before the awards data starts.
BEFORE_THE_DATA = dt.date(2018, 12, 1)


def listed_plans() -> list[tuple[str, dict]]:
    """Every Procurement Plan the fixture's documents lists name, as (project, its record in the list)."""
    found = []
    for path in sorted(DOCUMENTS.glob("*.json")):
        documents = json.loads(path.read_text()).get("response", {}).get("documents", {})
        found += [(path.stem, record) for record in documents.values()
                  if isinstance(record, dict) and record.get("docty") == "Procurement Plan"]
    return found


def plan_dates(database: Path = FIXTURE_DB) -> list[dt.date]:
    """Every plan date the fixture holds: the plan versions its reader read and every plan its documents lists name."""
    with DuckDBEngine.open(database, read_only=True) as engine:
        read = {row[0] for row in engine.run("SELECT DISTINCT plan_date FROM strata.silver.plan_versions", {}).rows}
    named = {dt.date.fromisoformat(record["docdt"][:10]) for _, record in listed_plans()}
    return sorted(read | named)


def india_database(folder: Path) -> Path:
    """A copy of the fixture database in which P130164's plan of June 20, 2018 lists IN-RRSMP-7516-CW-RFB: the
    document, its date and its links from P130164's documents list, the STEP reference from the walkthrough's capture,
    and its Method and plan table from the reference (RFB, CW). Its other fields stay empty."""
    path = folder / "india.duckdb"
    shutil.copy(FIXTURE_DB, path)
    [record] = [record for project, record in listed_plans() if project == "P130164" and record["id"] == INDIA_PLAN]
    day = dt.date.fromisoformat(record["docdt"][:10])
    with DuckDBEngine.open(path) as engine:
        engine.run(
            "INSERT INTO strata.silver.plan_versions (document_id, project_id, implementing_agency, plan_date, "
            "disclosed_on, series_order, previous_document_id, is_latest, pdf_pages, route_b_pages, parse_reason, "
            "text_url, pdf_url, public_from) VALUES (:document_id, 'P130164', NULL, :day, :day, 1, NULL, TRUE, 1, 0, "
            "NULL, :text_url, :pdf_url, :day)",
            {"document_id": INDIA_PLAN, "day": day, "text_url": record["txturl"], "pdf_url": record["pdfurl"]})
        engine.run(
            "INSERT INTO strata.silver.plan_rows (document_id, project_id, section, activity_reference_no, method, "
            "pdf_page, parser, public_from) VALUES (:document_id, 'P130164', 'WORKS', :reference, 'Request for Bids', "
            "1, 'stand-in', :day)",
            {"document_id": INDIA_PLAN, "reference": INDIA_PACKAGE, "day": day})
    return path


def periods(dates: list[dt.date]) -> dict:
    """find_comparables' period for each plan date, as of the plan's own date and as of AS_OF."""
    period_from = dt.date.fromisoformat(str(load_thresholds().value("past_range.period_from")))
    found = []
    for plan_date in dates:
        for as_of in sorted({plan_date, AS_OF}):
            start, end, case = period(plan_date, as_of, period_from)
            found.append({"plan_date": plan_date.isoformat(), "as_of": as_of.isoformat(),
                          "notice_from": start.isoformat(), "notice_to": end.isoformat(), "period": case})
    return {"period_from": period_from.isoformat(), "periods": found}


def pretty(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    india = india_database(folder)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(india, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=reading, today=lambda: AS_OF)

    async def story() -> dict[str, str]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            async def get(path: str, as_of: dt.date) -> str:
                return pretty((await client.get(path, headers=ANA, params={"asof": as_of.isoformat()})).json())

            return {
                "package-in-rrsmp-7516.json": await get(f"/api/packages/{INDIA_PACKAGE}", AS_OF),
                "comparables-in-rrsmp-7516.json": await get(f"/api/packages/{INDIA_PACKAGE}/comparables", AS_OF),
                "comparables-in-rrsmp-7516-2018-12-01.json":
                    await get(f"/api/packages/{INDIA_PACKAGE}/comparables", BEFORE_THE_DATA),
            }

    return {"notice-periods.json": pretty(periods(plan_dates())), **asyncio.run(story())}


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        for name, text in answers(Path(folder)).items():
            (OUT / name).write_text(text)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
