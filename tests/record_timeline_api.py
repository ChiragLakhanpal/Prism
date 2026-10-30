"""Writes a project timeline's recorded answers in tests/fixtures/api from the server itself (ticket 23).

The screen tests, the design gallery and the capture command serve these files, and tests/test_timeline.py checks
that the server still answers with them, so the Timeline tab and the server cannot drift apart. Build the fixture
database first, then run:

    uv run --frozen python tests/record_timeline_api.py

Each answer comes from the fixture database as of October 23, 2026, the day its sources were recorded, or as of the
date its address names:

- timeline-p130164.json: the showcase's timeline as the plain page asks for it, with no ?asof=, with both disagreements, the three rating bands and the contract
  signed only in its award notice; timeline-p130164-2016-08-26.json, the same as of the day ISR 7 was disclosed; and
  timeline-p130164-2024-01-01.json, as of a date after the ICR Review's re-issue, whose second dashed line ends near
  the chart's right edge, where the as-of date is.
- timeline-p156634.json: a project with a crowded What lane, whose contracts group by year; and
  timeline-p156634-public.json, its public view, which shows no disagreement on a project still under way.
- timeline-p130164-failed.json: the showcase's timeline when get_disagreements does not answer (FAILED): the marks,
  with no rating bands and no dashed lines, and the newest ISR as the How lane's one ISR mark.
- timeline-p130164-grouped.json: the showcase's timeline on the planted copy of tests/planted_groups.py (GROUPED),
  as the workspace's assertions pass read it: 16 pairs about three facts, drawn as three dashed lines (ticket 136).
- evidence-*.json: what each kind of mark opens in the evidence drawer, from a link: a report's document view (ISR 7,
  the ICR, the replaced ICR Review and the PAD), a band's ratings, a disagreement's two sides with each side's
  passage, an event's passage, the contract's signing and a year of contracts.
"""

import asyncio
import datetime as dt
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
DAY = "asof=2026-10-23"
TODAY = dt.date(2026, 10, 23)
PDO = "437378890475ef48"  # ISR 7 and ICR paragraph 78 on progress towards the PDO at the mid-term review
EFFICIENCY = "51ea6e6516c0ea63"  # ICR paragraph 44 and the re-issued ICR Review on efficiency

TIMELINE = {
    "timeline-p130164.json": "/api/projects/P130164/timeline",
    "timeline-p130164-2016-08-26.json": "/api/projects/P130164/timeline?asof=2016-08-26",
    "timeline-p130164-2024-01-01.json": "/api/projects/P130164/timeline?asof=2024-01-01",
    "timeline-p156634.json": "/api/projects/P156634/timeline",
    "timeline-p156634-public.json": "/api/projects/P156634/timeline?view=public",
    "evidence-doc-p130164-isr-7.json": f"/api/evidence?id=doc:26733307&{DAY}",
    "evidence-doc-p130164-isr-12.json": f"/api/evidence?id=doc:29794672&{DAY}",
    "evidence-doc-p130164-icr.json": f"/api/evidence?id=doc:31525018&{DAY}",
    "evidence-doc-p130164-pad.json": f"/api/evidence?id=doc:18381488&{DAY}",
    "evidence-doc-p130164-icr-review-2020.json": f"/api/evidence?id=doc:31906731&{DAY}",
    "evidence-doc-p130164-icr-review-2023.json": f"/api/evidence?id=doc:34056616&{DAY}",
    "evidence-ratings-p130164-1-9.json": f"/api/evidence?id=ratings:P130164:pdo_progress:1-9&{DAY}",
    "evidence-ratings-p130164-1-9-2024-01-01.json": "/api/evidence?id=ratings:P130164:pdo_progress:1-9&asof=2024-01-01",
    "evidence-ratings-p130164-10-11.json": f"/api/evidence?id=ratings:P130164:pdo_progress:10-11&{DAY}",
    "evidence-ratings-p130164-12-13.json": f"/api/evidence?id=ratings:P130164:pdo_progress:12-13&{DAY}",
    "evidence-disagreement-p130164-pdo.json": f"/api/evidence?id=disagreement:{PDO}&{DAY}",
    "evidence-disagreement-p130164-efficiency.json": f"/api/evidence?id=disagreement:{EFFICIENCY}&{DAY}",
    "evidence-isr-p130164-7-s4.json": f"/api/evidence?id=strata.gold.passage:26733307/v1/s4&{DAY}",
    "evidence-icr-p130164-78.json": f"/api/evidence?id=strata.gold.passage:31525018/v1/78&{DAY}",
    "evidence-icr-p130164-44.json": f"/api/evidence?id=strata.gold.passage:31525018/v1/44&{DAY}",
    "evidence-icr-review-p130164-2023-5.json": f"/api/evidence?id=strata.gold.passage:34056616/v2/5&{DAY}",
    "evidence-isr-p130164-7-key-dates.json": f"/api/evidence?id=strata.gold.passage:26733307/v1/s1&{DAY}",
    "evidence-icr-p130164-11.json": f"/api/evidence?id=strata.gold.passage:31525018/v1/11&{DAY}",
    "evidence-package-in-rrsmp-7431.json": f"/api/evidence?id=strata.gold.package:IN-RRSMP-7431-CW-RFB&{DAY}",
    "evidence-contracts-p156634-2019.json": f"/api/evidence?id=contracts:P156634:2019&{DAY}",
}

# The answers recorded while get_disagreements fails, as failing_get_disagreements makes it.
FAILED = {
    "timeline-p130164-failed.json": "/api/projects/P130164/timeline",
}


# The answers recorded on the planted copy (tests/planted_groups.py), whose pairs share a report (ticket 136).
GROUPED = {
    "timeline-p130164-grouped.json": "/api/projects/P130164/timeline",
}


def planted(folder: Path) -> Path:
    """The planted copy of the fixture database, in folder."""
    sys.path.insert(0, str(ROOT / "tests"))
    from planted_groups import plant

    return plant(FIXTURE_DB, folder / "planted.duckdb")


def failing_get_disagreements(call):
    """The tool registry's call, except that get_disagreements raises, as when its tables cannot be read."""
    def failing(name, arguments, context):
        if name == "get_disagreements":
            raise RuntimeError("get_disagreements did not answer")
        return call(name, arguments, context)
    return failing


def app_on(database: Path):
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine
    # A page with no ?asof= reads as of today: the day the fixture was recorded.
    return create_app(engine_for=engine_for, today=lambda: TODAY)


def answer(database: Path, path: str) -> dict:
    async def go():
        transport = httpx.ASGITransport(app=app_on(database))
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            response = await client.get(path, headers=ANA)
            response.raise_for_status()
            return response.json()
    return asyncio.run(go())


def write(name: str, path: str, database: Path = FIXTURE_DB) -> None:
    (OUT / name).write_text(json.dumps(answer(database, path), indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote tests/fixtures/api/{name}.")


def main() -> None:
    for name, path in TIMELINE.items():
        write(name, path)
    from strata.server import timeline

    call = timeline.registry.call
    timeline.registry.call = failing_get_disagreements(call)
    try:
        for name, path in FAILED.items():
            write(name, path)
    finally:
        timeline.registry.call = call
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        database = planted(Path(folder))
        for name, path in GROUPED.items():
            write(name, path, database)


if __name__ == "__main__":
    main()
