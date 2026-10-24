"""People acting on the fixture's lesson review queue, for the tests and the recorded API answers that need
decided lessons (ticket 29). Each act goes through the same LessonReview the HTTP routes use, as a viewer
from tests/fixtures/roles.toml, on a writable copy of the fixture database.

The fixture's queue holds three proposed lessons from P130164, by the passage each cites: ICR paragraph 54
(the rebidding lesson), ICR paragraph 55 (permits before award) and the ICR Review's section 12 (IEG's lesson).
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

from strata.config import load_roles
from strata.dbx import Viewer
from strata.knowledge.lessons.review import LessonReview
from strata.lakehouse.engine import DuckDBEngine, PermissionDenied

ROOT = Path(__file__).resolve().parents[1]
ROLES = load_roles(ROOT / "tests" / "fixtures" / "roles.toml")
REBIDDING, PERMITS, IEG_LESSON = "31525018/v1/54", "31525018/v1/55", "34056616/v2/12"


def person(email: str) -> Viewer:
    return Viewer(email=email, name=email, user_id=f"id-{email}", token="not-a-real-token")


ANA = person("ana.example@worldbank.org")
ASHA = person("asha.raman@worldbank.example")
LEELA = person("leela.iyer@worldbank.example")
OMAR = person("omar.haddad@worldbank.example")
PRIYA = person("priya.nair@worldbank.example")
WANJIRU = person("wanjiru.kamau@worldbank.example")


WRITES = re.compile(r"\s*(INSERT|MERGE|UPDATE|DELETE|CREATE|DROP|ALTER)\b", re.IGNORECASE)


class ReadsOnly:
    """The viewer's engine in these tests: it reads, and refuses every write as the warehouse would refuse a
    viewer with no MODIFY grant, so a test proves the app's own engine writes the review record."""

    def __init__(self, engine):
        self.engine = engine

    def run(self, sql, params=None):
        if WRITES.match(sql):
            raise PermissionDenied("The viewer may not write the review record.")
        return self.engine.run(sql, params)

    def insert_rows(self, table, columns, rows):
        raise PermissionDenied(f"The viewer may not write {table}.")


class Unclosed:
    """The app's own engine in these tests: the request's open connection, which the route's close leaves open."""

    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def close(self):
        pass


class OneConnection:
    """A writable copy of the fixture database, opened once for each request. DuckDB attaches a file only once
    in a process, so the viewer's engine (ReadsOnly) and the app's own engine (Unclosed) share the request's
    connection, as both reach the same tables on the warehouse."""

    def __init__(self, path: Path):
        self.path, self.open = path, None

    @contextmanager
    def engine_for(self, _viewer):
        with DuckDBEngine.open(self.path) as engine:
            self.open = engine
            try:
                yield ReadsOnly(engine)
            finally:
                self.open = None

    def the_app(self):
        assert self.open is not None, "The app writes only during a request."
        return Unclosed(self.open)


def copy_of(fixture_db: Path, folder: Path) -> Path:
    target = folder / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    return target


def review_on(day: dt.date, hour: int = 14) -> LessonReview:
    return LessonReview(ROLES, today=lambda: day, now=lambda: dt.datetime.combine(day, dt.time(hour), tzinfo=dt.UTC))


def item_of(engine, passage_id: str, kind: str = "new") -> str:
    """The queue item of the proposal that cites a passage."""
    result = engine.run("SELECT i.item_id FROM strata.ops.lesson_review_items AS i "
                        "JOIN strata.silver.lesson_proposals AS p ON p.proposal_id = i.proposal_id "
                        "WHERE p.passage_id = :passage_id AND i.kind = :kind ORDER BY i.created_at",
                        {"passage_id": passage_id, "kind": kind})
    return result.rows[0][0]


def decide(database: Path, passage_id: str, day: dt.date, outcome: str = "add", recommender: Viewer = ASHA,
           decider: Viewer = OMAR, **decision) -> dict:
    """Recommend, then decide, the new lesson from a passage, a day apart in the morning and the afternoon."""
    with DuckDBEngine.open(database) as engine:
        item = item_of(engine, passage_id)
        # The scenario's own connection writes the record here, as the app's own engine does in a request.
        review_on(day, 9).act(engine, recommender, item, "recommend",
                              {"expected_stage": "recommendation", "outcome": outcome if outcome != "repeat" else "add",
                               "reason": "The quote supports it, word for word."}, writer=engine)
        return review_on(day, 15).act(engine, decider, item, "decide",
                                      {"expected_stage": "decision", "outcome": outcome,
                                       "reason": "Two people read the evidence and agree.", **decision}, writer=engine)
