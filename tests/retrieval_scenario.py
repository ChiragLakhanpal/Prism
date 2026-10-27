"""People using the retrieval loop on a writable copy of the fixture database (ticket 32), for the tests and the
recorded API answers: asking the showcase question, reporting a passage from the evidence drawer, deciding on the
reports, and grading the notice queries, each through the HTTP routes as a viewer from tests/fixtures/roles.toml.

One connection to the copy serves every request: the viewer's engine reads through it and refuses writes, as the
warehouse refuses a viewer with no MODIFY grant, and the app's own engine writes through it, so a test proves the
app's own identity writes every row. The viewer's engine is also the fixture's stand-in for the readers group: it
reads every masked column (strata.lakehouse.masks) as NULL, as the warehouse's column masks give it to anyone but
the app and the catalog's owner, so a test proves no page needs to know who sent a report or asked a question
when it reads as the viewer (ticket 64). It also reads no row of a filtered table unless the viewer is in the reviewer
group the filter names, as the warehouse's row filters give it (ticket 63). The scripted agent answers the showcase question (tests/fixtures/agent), and
the answer cites ICR P130164 paragraph 54, which search_passages found.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import shutil
from contextlib import contextmanager
from pathlib import Path

import httpx

from strata.agent.loop import answer_runner
from strata.agent.scripted import ScriptedAgent, ScriptedJudge, load_cases
from strata.config import load_roles, load_thresholds
from strata.knowledge.lessons.review import LessonReview
from strata.knowledge.retrieval.judging import Judging
from strata.knowledge.retrieval.reports import CitationLog, PassageReports
from strata.lakehouse import masks
from strata.lakehouse.engine import DuckDBEngine, PermissionDenied
from strata.server.app import create_app
from strata.server.evidence import OpenedLog

ROOT = Path(__file__).resolve().parents[1]
ROLES = load_roles(ROOT / "tests" / "fixtures" / "roles.toml")
CASE = "p130164-rebidding"
PARAGRAPH_54 = "strata.gold.passage:31525018/v1/54"
PARAGRAPH_55 = "strata.gold.passage:31525018/v1/55"
TODAY = dt.date(2026, 10, 23)


def headers(email: str, user_id: str | None = None) -> dict:
    return {"X-Forwarded-Email": email, "X-Forwarded-Preferred-Username": email,
            "X-Forwarded-User": user_id or f"id-{email}", "X-Forwarded-Access-Token": "not-a-real-token"}


ANA = headers("ana.example@worldbank.org")
LEELA = headers("leela.iyer@worldbank.example")
PRIYA = headers("priya.nair@worldbank.example")
DANIEL = headers("daniel.okafor@worldbank.example")
MEI = headers("mei.tanaka@worldbank.example")
TOMAS = headers("tomas.rivera@worldbank.example")
OMAR = headers("omar.haddad@worldbank.example")
# More people who use Strata, for the rules for scale: none of them is in the roles file.
KOFI = headers("kofi.example@worldbank.org")
SARA = headers("sara.example@worldbank.org")
NOOR = headers("noor.example@worldbank.org")


class ReadsOnly:
    """A viewer's engine: a reader, who may not write, reads each masked column as NULL, and reads a filtered table's
    rows only when in one of the reviewer groups (the roles file's keys) the filter names."""

    def __init__(self, engine, groups: frozenset[str] = frozenset()):
        self.engine = engine
        self.groups = groups

    def run(self, sql, params=None):
        if sql.lstrip().upper().startswith(("INSERT", "MERGE", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")):
            raise PermissionDenied("The viewer may not write the retrieval loop's tables.")
        return self.engine.run(masks.as_a_reader(sql, self.groups), params)

    def insert_rows(self, table, columns, rows):
        raise PermissionDenied(f"The viewer may not write {table}.")

    def __getattr__(self, name):
        return getattr(self.engine, name)


class Loop:
    """A writable copy of the fixture database and an app over it, with a clock the test moves."""

    def __init__(self, fixture_db: Path, folder: Path, mode: str = "pilot", case: str = CASE):
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / "retrieval.duckdb"
        shutil.copy(fixture_db, self.path)
        self.database = DuckDBEngine.open(self.path)
        # The fixture's day, so a decision made in a test is public on the day the answers are read as of.
        self.at = dt.datetime(2026, 10, 23, 9, 0, tzinfo=dt.UTC)
        self.runs = 0
        thresholds = load_thresholds()
        if mode != "pilot":
            values = {**thresholds.values, "retrieval": {**thresholds.values["retrieval"], "mode": mode}}
            thresholds = type(thresholds)(thresholds.path, values)
        self.thresholds = thresholds
        # Ids counted in order, so the recorded answers are the same on every run.
        self.ids: dict[str, int] = {}
        self.reports = PassageReports(ROLES, now=self.now, thresholds=thresholds, new_id=self.new_id)
        self.judging = Judging(ROLES, now=self.now, thresholds=thresholds, new_id=self.new_id)
        self.case = case
        case = load_cases()[case]

        @contextmanager
        def engine_for(viewer):
            yield self.reader(getattr(viewer, "email", None))

        def new_run_id():
            self.runs += 1
            return f"run-{self.runs:04d}"

        self.app = create_app(runner=answer_runner(lambda turn: ScriptedAgent(case), engine_for, today=lambda: TODAY),
                              engine_for=engine_for, judge=ScriptedJudge(case), new_run_id=new_run_id,
                              lessons=LessonReview(ROLES, now=self.now),
                              passage_reports=self.reports, judging=self.judging, feedback_record=self.the_app,
                              citations=CitationLog(self.the_app), opened=OpenedLog(self.the_app, now=self.now),
                              today=lambda: TODAY, now=self.now)

    def new_id(self, prefix: str) -> str:
        self.ids[prefix] = self.ids.get(prefix, 0) + 1
        return f"{prefix}-{self.ids[prefix]:04d}"

    def now(self) -> dt.datetime:
        self.at += dt.timedelta(seconds=1)
        return self.at

    def the_app(self):
        return self.database.cursor()

    def reader(self, email: str | None = None):
        """The engine a viewer reads through: the stand-in for the readers group, with the reviewer groups the roles
        file puts the viewer with this email in."""
        person = ROLES.person(email)
        return ReadsOnly(self.database.cursor(), frozenset(person.groups) if person else frozenset())

    def later(self, **delta):
        self.at += dt.timedelta(**delta)

    def close(self):
        self.database.close()

    def request(self, method: str, path: str, who: dict, body=None, params=None) -> httpx.Response:
        async def go():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                return await client.request(method, path, headers=who, json=body, params=params)
        return asyncio.run(go())

    def ask(self, who: dict, view: str = "staff") -> str:
        """Ask the case's question (the showcase's unless the loop was given another), as the box would, and return
        the answer's run id."""
        case = load_cases()[self.case]
        response = self.request("POST", "/api/ask", who, {"question": case.question, "scope": case.scope,
                                                          "asof": case.as_of.isoformat(), "view": view})
        assert response.status_code == 200, response.text
        return f"run-{self.runs:04d}"

    def report(self, who: dict, run_id: str, kind: str = "wrong_passage", reason: str | None = None,
               evidence_id: str = PARAGRAPH_54, view: str = "staff") -> httpx.Response:
        return self.request("POST", "/api/feedback", who, {"evidence_id": evidence_id, "run_id": run_id, "sentence_id": None,
                                                           "kind": kind, "reason": reason, "view": view})

    def decide(self, who: dict, group_id: str, outcome: str = "rank_lower", reason: str | None = "Read it; it fits.",
               state: str | None = None) -> httpx.Response:
        if state is None:
            state = self.request("GET", f"/api/passage-reports/{group_id}", who).json()["state"]
        return self.request("POST", f"/api/passage-reports/{group_id}/decide", who,
                            {"expected_state": state, "outcome": outcome, "reason": reason})

    def opened(self, who: dict, evidence_id: str, run_id: str | None = None) -> httpx.Response:
        return self.request("POST", "/api/evidence/opened", who, {"evidence_id": evidence_id, "run_id": run_id})

    def rows(self, sql: str) -> list[dict]:
        result = self.database.cursor().run(sql, {})
        return [dict(zip(result.columns, row)) for row in result.rows]

    def weekly(self) -> dict:
        from strata.knowledge.retrieval import weekly

        return weekly.run(self.database.cursor(), now=self.now, thresholds=self.thresholds, roles=ROLES,
                          new_id=self.new_id)
