"""The suggested PPSD rows and Project Paper summary story (ticket 36), through the HTTP routes, shared by
tests/test_ppsd_rows.py, tests/test_project_paper.py and tests/record_ppsd_api.py.

On a copy of the fixture database whose three proposed lessons two reviewers added to the library on October 27,
2026 (tests/lesson_scenario.py), as of October 28: Ana, World Bank staff on the Kenya water team, sets section 1's
country to India for KE-NWWDA-541055-CW-RFB, so its comparables reach P130164's ICR, selects both risks in section 3
and suggests PPSD rows from them. The scripted writer replays tests/fixtures/agent/writers.toml and the scripted judge
its recorded answers. Ana sets one owner, marks the rows as checked, is refused the export while an owner is left,
sets the second owner and exports. Then she drafts the Project Paper summary for the agency's plan of October 9, 2026,
which draws on the rows she checked, checks it and exports it.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
from contextlib import contextmanager
from pathlib import Path

import httpx

import lesson_scenario as scenario
from strata import appstate
from strata.agent.scripted import WRITER_CASES, ScriptedAgent, ScriptedJudge, load_cases
from strata.config import load_roles
from strata.drafts.store import DraftStore
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.packages.store import PackageStore
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.server.evidence import OpenedLog

DECIDED, TODAY = dt.date(2026, 10, 27), dt.date(2026, 10, 28)
PACKAGE = "KE-NWWDA-541055-CW-RFB"
INDIA = {"country": "IN", "notice_from": "2013-01-01"}
RISKS = ["cost_estimates", "permits_before_award"]
PLAN = {"project_id": "P156634", "agency_id": "northern-water-works-development-agency", "plan_date": "2026-10-09"}


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"40{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN, CY = viewer(21, "Ana"), viewer(22, "Ben"), viewer(23, "Cy")
GROUPS = {"4021@1984": ["users", "strata-team-kenya-water"], "4022@1984": ["users", "strata-team-kenya-water"],
          "4023@1984": []}


def library(fixture_db: Path, folder: Path) -> Path:
    """A copy of the fixture database with the three proposed lessons in the library."""
    database = scenario.copy_of(fixture_db, folder)
    for passage in (scenario.REBIDDING, scenario.PERMITS, scenario.IEG_LESSON):
        scenario.decide(database, passage, DECIDED)
    return database


class Story:
    """The app on a library, with app state in a DuckDB file, the scripted writer and judge of the case now
    writing, a clock that moves a minute at a time and fixed ids."""

    def __init__(self, database: Path, folder: Path, kinds=None):
        self.state_db = folder / "state.duckdb"
        with DuckDBEngine.open(self.state_db) as engine:
            catalog.build(engine)
            appstate.build(engine)
        self.cases = load_cases(WRITER_CASES)
        self.case = "ppsd-rows-ke-nwwda-541055"
        self.at = dt.datetime(2026, 10, 28, 9, 0, tzinfo=dt.UTC)
        ids = iter(f"draft-{number:04d}" for number in range(1, 100))
        runs = iter(f"run-{number:04d}" for number in range(1, 100))

        @contextmanager
        def reading(_viewer):
            with DuckDBEngine.open(database, read_only=True) as engine:
                yield engine

        story = self

        class Judge:
            name = "scripted judge"

            def judge(self, questions):
                return ScriptedJudge(story.cases[story.case]).judge(questions)

        def state():
            return DuckDBEngine.open(self.state_db)

        self.app = create_app(engine_for=reading, drafts=DraftStore(state), opened=OpenedLog(state, now=self.clock),
                              packages=PackageStore(state), writers=lambda kind: ScriptedAgent(self.cases[self.case]),
                              judge=Judge(), access=Access(load_roles(), StaticGroups(GROUPS)), today=lambda: TODAY,
                              now=self.clock, new_draft_id=lambda: next(ids), new_run_id=lambda: next(runs), kinds=kinds)

    def clock(self) -> dt.datetime:
        self.at += dt.timedelta(minutes=1)
        return self.at

    def call(self, method: str, path: str, headers=ANA, **options) -> httpx.Response:
        async def go():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://strata.test") as client:
                return await client.request(method, path, headers=headers, **options)
        return asyncio.run(go())

    def select(self, risks=tuple(RISKS), headers=ANA) -> httpx.Response:
        return self.call("PUT", f"/api/packages/{PACKAGE}/risk-selection", headers,
                         json={"changes": {risk: True for risk in risks}})

    def write(self, case: str, body: dict, headers=ANA) -> tuple[list, str | None]:
        self.case = case
        text = self.call("POST", "/api/drafts", headers, json=body).text
        sent = events(text)
        made = [data["draft_id"] for kind, data in sent if kind == "draft"]
        return sent, made[0] if made else None

    def suggest(self, case: str = "ppsd-rows-ke-nwwda-541055", key: str = "ppsd-1", headers=ANA, **extra):
        return self.write(case, {"kind": "ppsd_rows", "package": PACKAGE, "criteria": INDIA, "idempotency_key": key,
                                 **extra}, headers)

    def summarize(self, case: str = "project-paper-p156634", key: str = "pp-1", headers=ANA):
        return self.write(case, {"kind": "project_paper", **PLAN, "idempotency_key": key}, headers)

    def get(self, path: str, headers=ANA, **params) -> httpx.Response:
        return self.call("GET", path, headers, params=params)

    def act(self, draft_id: str, action: str, expected: str, headers=ANA) -> httpx.Response:
        return self.call("POST", f"/api/drafts/{draft_id}/{action}", headers, json={"expected_state": expected})

    def set_field(self, draft_id: str, row_key: str, field: str, value, headers=ANA, view="staff") -> httpx.Response:
        return self.call("PUT", f"/api/drafts/{draft_id}/fields", headers,
                         json={"row_key": row_key, "field": field, "value": value, "view": view})

    def download(self, draft_id: str, suffix: str) -> tuple[str, bytes]:
        draft = self.get(f"/api/drafts/{draft_id}").json()
        name = next(item["name"] for item in draft["export"]["files"] if item["name"].endswith(suffix))
        return name, self.get(f"/api/drafts/{draft_id}/files/{name}").content


def events(text: str) -> list[tuple[str, dict]]:
    """A server-sent event stream's events, as (type, data), without its keep-alive comments."""
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if lines:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found
