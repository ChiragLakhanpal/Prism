"""Writes the Data tab's recorded API answers, the evidence drawer's answers for each kind of passage, and
the project pages' answers (All projects, a project's Summary, Procurement tab, Packages, Documents and source
view, a plan's changes and its baseline), in tests/fixtures/api from the server itself (tickets 16, 18 and 21).

The screen tests serve these files from their mocked API, and tests/test_data_routes.py checks that
the server still answers with them, so the screens and the server cannot drift apart. Build the
fixture database first, then run:

    uv run --frozen python tests/record_api.py

Each answer comes from GET /api/data/readiness or /api/data/sources on the fixture database, as of
October 23, 2026, the day its sources were recorded and measured, except for three states the
fixture does not hold: no measures yet (an empty catalog), one source not measured yet (the
fixture's measures without WGI's), and the error answers, which are the server's own bodies.

The project pages' answers come from the fixture database too (HUB), and the baseline's from a copy of
it in which Ana saved the agency's plan of July 21, 2025 as the baseline on October 23, 2026
(BASELINE). model-routes.json lists the routes the server tags as calling a model, which the
Summary's screen test checks it never asks for. tests/test_project_hub.py checks each against the server.
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
from strata.server.app import create_app, model_routes  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Access-Token": "token-for-ana-only",
       "X-Forwarded-Preferred-Username": "Ana Example", "X-Forwarded-User": "4021@1984"}
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
    # The same notice's qualification text, the kind of section the drawer is for (critique r2).
    "evidence-notice-op00118817-qualifications.json": "/api/evidence?id=strata.gold.passage:OP00118817/v1/s5",
    "evidence-icr-p127203-fr.json": "/api/evidence?id=strata.gold.passage:33407968/v1/1",
}
# The project pages (ticket 21): All projects, a project's header and Procurement tab, its Summary, Packages
# and Documents, the source view in each of its states, and what changed in a plan.
SOURCE = "/api/projects/P130164/documents"
NWWDA = "/api/projects/P156634/procurement/northern-water-works-development-agency"
MINISTRY = "/api/projects/P156634/procurement/ministry-of-water-and-irrigation"
HUB = {
    "projects.json": f"/api/projects?{DAY}",
    "projects-page-2.json": f"/api/projects?{DAY}&page=2",
    "projects-india.json": f"/api/projects?{DAY}&q=india",
    "projects-no-match.json": f"/api/projects?{DAY}&q=atlantis",
    "project-p130164.json": "/api/projects/P130164?asof=2026-10-22",
    "project-p156634.json": "/api/projects/P156634?asof=2026-10-22",
    "summary-p130164.json": f"/api/projects/P130164/summary?{DAY}",
    "summary-p156634.json": f"/api/projects/P156634/summary?{DAY}",
    "packages-p156634.json": f"/api/projects/P156634/packages?{DAY}",
    "packages-p156634-page-2.json": f"/api/projects/P156634/packages?{DAY}&page=2",
    "packages-p156634-boreholes.json": f"/api/projects/P156634/packages?{DAY}&q=boreholes",
    "packages-p156634-no-match.json": f"/api/projects/P156634/packages?{DAY}&q=atlantis",
    "documents-p130164.json": f"/api/projects/P130164/documents?{DAY}",
    # A project the slice selects whose documents the fixture holds no list of, and one outside the slice.
    "project-p117635.json": "/api/projects/P117635?asof=2026-10-22",
    "documents-p117635-none-yet.json": f"/api/projects/P117635/documents?{DAY}",
    "project-p120014.json": "/api/projects/P120014?asof=2026-10-22",
    "documents-p120014-outside.json": f"/api/projects/P120014/documents?{DAY}",
    "source-icr-p130164-23-54.json": f"{SOURCE}/icr-2019-10-10?page=23&para=54&{DAY}",
    "source-icr-p130164-23.json": f"{SOURCE}/icr-2019-10-10?page=23&{DAY}",
    "source-icr-p130164-moved.json": f"{SOURCE}/icr-2019-10-10?page=22&para=54&{DAY}",
    "source-icr-p130164-no-para.json": f"{SOURCE}/icr-2019-10-10?page=23&para=999&{DAY}",
    "source-icr-p130164-page-range.json": f"{SOURCE}/icr-2019-10-10?page=80&{DAY}",
    "source-icr-p130164-page-unread.json": f"{SOURCE}/icr-2019-10-10?page=5&{DAY}",
    "source-icr-p130164-page-empty.json": f"{SOURCE}/icr-2019-10-10?page=49&{DAY}",
    "source-icr-p130164-front-matter.json": f"{SOURCE}/icr-2019-10-10?page=2&{DAY}",
    "source-icr-p130164-short.json": f"{SOURCE}/icr?page=23&para=54&{DAY}",
    "source-p130164-ambiguous.json": f"{SOURCE}/isr?{DAY}",
    "source-p130164-not-found.json": f"{SOURCE}/not-a-document?{DAY}",
    "source-p130164-doc-unread.json": f"{SOURCE}/30152361?{DAY}",
    "source-icr-p130164-not-public.json": f"{SOURCE}/icr-2019-10-10?page=23&asof=2019-10-01",
    "source-icr-review-p130164-reissue.json": f"{SOURCE}/icr-review-2023-05-04?page=1&{DAY}",
    # A page with a table the reader read into rows (the PAD's risk table), and a Procurement Plan's page of
    # STEP rows, each wider than a phone's column (the 21 design review, round 3, B1).
    "source-pad-p130164-65.json": f"{SOURCE}/pad-2013-10-01?page=65&{DAY}",
    "source-plan-p161305-3.json": f"/api/projects/P161305/documents/procurement-plan-kenya-national-highways-authority-2026-09-24?page=3&{DAY}",
    "changes-nwwda-2026-10-09.json": f"{NWWDA}/2026-10-09/changes?{DAY}",
    "changes-nwwda-2020-12-07.json": f"{NWWDA}/2020-12-07/changes?{DAY}",
    # The Ministry's plan of April 30, 2020 added one activity and re-dated another since November 8, 2019.
    "changes-ministry-2020-04-30.json": f"{MINISTRY}/2020-04-30/changes?{DAY}",
    "check-plan-p156634-ministry-2020-04-30.json": f"{MINISTRY}/2020-04-30?{DAY}",
    # Check a plan (ticket 10), which ticket 21's baseline adds a field to.
    "check-plan-p156634-nwwda-2026-10-09.json": f"{NWWDA}/2026-10-09?asof=2026-10-22",
    # The plan of July 21, 2025 before anyone saved a baseline, which the baseline's screen test saves.
    "check-plan-p156634-nwwda-2025-07-21.json": f"{NWWDA}/2025-07-21?{DAY}",
    "check-plan-p156634-nwwda-2026-10-10-not-found.json": f"{NWWDA}/2026-10-10?asof=2026-10-22",
    "check-plan-p156634-wajir-no-plan.json": "/api/projects/P156634/procurement/wajir-water-and-sewerage-company?asof=2026-10-22",
}
# The baseline's answers, from a copy of the fixture in which Ana saved the plan of July 21, 2025 as the
# baseline on October 23, 2026.
SAVED_AT = "2026-10-23T15:30:00+00:00"
BASELINE = {
    "check-plan-p156634-nwwda-2026-10-09-baseline.json": f"{NWWDA}/2026-10-09?{DAY}",
    "check-plan-p156634-nwwda-2025-07-21-baseline.json": f"{NWWDA}/2025-07-21?{DAY}",
    "project-p156634-baseline.json": f"/api/projects/P156634?{DAY}",
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


def app_on(database: Path, read_only: bool = True):
    import datetime as dt

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(database, read_only=read_only) as engine:
            yield engine
    return create_app(engine_for=engine_for, now=lambda: dt.datetime.fromisoformat(SAVED_AT))


def answer(database: Path, path: str, method: str = "GET", body: dict | None = None, read_only: bool = True) -> dict:
    async def go():
        transport = httpx.ASGITransport(app=app_on(database, read_only))
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            response = await client.request(method, path, headers=ANA, json=body)
            response.raise_for_status()
            return response.json()
    return asyncio.run(go())


def with_baseline(folder: Path, database: Path = FIXTURE_DB) -> tuple[Path, dict]:
    """A copy of the fixture database in which Ana saved the plan of July 21, 2025 as the baseline, and the
    answer the save gave."""
    import shutil

    path = folder / "baseline.duckdb"
    shutil.copy(database, path)
    saved = answer(path, f"{NWWDA}/baseline", "PUT", {"plan_date": "2025-07-21"}, read_only=False)
    return path, saved


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
# risk annex, recorded as unreadable, against a hand count, as the slice file holds one once a person
# counts the annex) and a Partial; each abstention (no hand count, stopped at the daily page cap, not
# read yet, no document fits); and a shelf never read. The fixture itself has no hand count (review r2
# B1), so the default page shows the risks recovered with nothing to check them against.
HAND_COUNT = ("UPDATE strata.ops.stress_shelf SET denominator = 8, denominator_from = 'hand_count', "
              "counted_on = DATE '2026-10-20' WHERE shelf_key = :key", {"key": "p130164_pad"})
SHELF_STATES = {
    "data-readiness-shelf-gap.json": [
        HAND_COUNT,
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
        HAND_COUNT,
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
    found = {name: answer(FIXTURE_DB, path) for name, path in {**FROM_THE_FIXTURE, **HUB}.items()}
    with tempfile.TemporaryDirectory() as folder:
        found[EMPTY] = answer(empty(Path(folder)), f"/api/data/readiness?{DAY}")
        found[UNMEASURED] = answer(without_wgi(Path(folder)), f"/api/data/readiness?{DAY}")
        for name in SHELF_STATES:
            found[name] = answer(with_shelf(Path(folder), name), f"/api/data/readiness?{DAY}")
        database, found["baseline-saved.json"] = with_baseline(Path(folder))
        for name, path in BASELINE.items():
            found[name] = answer(database, path)
    found["model-routes.json"] = {"routes": model_routes(create_app(engine_for=None))}
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
