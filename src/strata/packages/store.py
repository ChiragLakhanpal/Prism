"""Where planned packages and opened plan checks are kept: the app state store, Lakebase on the App (ADR 0005;
src/strata/appstate), written as the app's own service principal (ticket 15).

A package is one row in strata.app.planned_packages and one row in strata.app.planned_package_saves for each
save; its latest save is the package now. Nothing is updated or deleted (CLAUDE.md rule 5). The store holds no
access rule: the package routes show a package only to the person who made it. The first use makes the
tables, unless they exist, so the app needs only its database. Values arrive typed from DuckDB and Postgres,
and as text from an engine that answers in text, so each is read once here.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from importlib import resources
from threading import Lock

from strata import appstate
from strata.drafts.store import moment
from strata.lakehouse.engine import Engine

PACKAGE_COLUMNS = ("package_id", "author_id", "author_name", "sentence", "run_id", "created_at", "public_from")
SAVE_COLUMNS = ("package_id", "save_id", "criteria", "plan_months", "plan_before_range", "saved_at", "public_from")
PLAN_CHECK_COLUMNS = ("viewer_id", "project_id", "agency_id", "implementing_agency", "plan_date", "latest",
                      "activities", "opened_at", "public_from")


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.packages") / "sql" / f"{name}.sql").read_text()


def _flag(value) -> bool | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, bool) else str(value).lower() == "true"


def _float(value) -> float | None:
    return None if value is None or value == "" else float(value)


def _day(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


@dataclass(frozen=True)
class Saved:
    """A package as it is kept: its row and its latest save."""

    package_id: str
    author_id: str
    author_name: str | None
    sentence: str
    run_id: str | None
    created_at: dt.datetime
    save_id: str
    criteria: dict
    plan_months: float | None
    plan_before_range: bool | None
    saved_at: dt.datetime


@dataclass(frozen=True)
class PlanCheck:
    project_id: str
    agency_id: str
    implementing_agency: str | None
    plan_date: dt.date
    latest: bool
    activities: int | None
    opened_at: dt.datetime


class PackageStore:
    """The planned packages in the app state store. engine() opens the engine that reads and writes them: the
    app's own."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine
        self._built = False
        self._building = Lock()

    @contextmanager
    def _open(self) -> Iterator[Engine]:
        engine = self.engine()
        try:
            if not self._built:
                with self._building:
                    if not self._built:
                        appstate.build(engine)
                        self._built = True
            yield engine
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                close()

    @staticmethod
    def _rows(engine: Engine, query: str, **params) -> list[dict]:
        result = engine.run(_sql(query), params)
        return [dict(zip(result.columns, row)) for row in result.rows]

    @staticmethod
    def _saved(row: dict) -> Saved:
        return Saved(row["package_id"], row["author_id"], row["author_name"], row["sentence"], row["run_id"] or None,
                     moment(row["created_at"]), row["save_id"], json.loads(row["criteria"]),
                     _float(row["plan_months"]), _flag(row["plan_before_range"]), moment(row["saved_at"]))

    def create(self, package_id: str, author_id: str, author_name: str | None, sentence: str, run_id: str | None,
               save_id: str, criteria: dict, at: dt.datetime) -> None:
        """Save a new package with its first criteria."""
        with self._open() as engine:
            engine.insert_rows("strata.app.planned_packages", PACKAGE_COLUMNS, [(
                package_id, author_id, author_name, sentence, run_id, at, at.date())])
            engine.insert_rows("strata.app.planned_package_saves", SAVE_COLUMNS, [(
                package_id, save_id, json.dumps(criteria, ensure_ascii=False), None, None, at, at.date())])

    def save(self, package_id: str, save_id: str, criteria: dict, plan_months: float | None,
             plan_before_range: bool | None, at: dt.datetime) -> None:
        """Keep the package's criteria after a change, as a new save."""
        with self._open() as engine:
            engine.insert_rows("strata.app.planned_package_saves", SAVE_COLUMNS, [(
                package_id, save_id, json.dumps(criteria, ensure_ascii=False), plan_months, plan_before_range, at,
                at.date())])

    def get(self, package_id: str) -> Saved | None:
        with self._open() as engine:
            found = self._rows(engine, "package", package_id=package_id)
        return self._saved(found[0]) if found else None

    def mine(self, author_id: str) -> list[Saved]:
        with self._open() as engine:
            return [self._saved(row) for row in self._rows(engine, "packages", author_id=author_id)]

    def record_plan_check(self, viewer_id: str, project_id: str, agency_id: str, implementing_agency: str | None,
                          plan_date: dt.date, latest: bool, activities: int | None, at: dt.datetime) -> None:
        with self._open() as engine:
            engine.insert_rows("strata.app.plan_checks_opened", PLAN_CHECK_COLUMNS, [(
                viewer_id, project_id, agency_id, implementing_agency, plan_date, latest, activities, at, at.date())])

    def plan_checks(self, viewer_id: str) -> list[PlanCheck]:
        with self._open() as engine:
            rows = self._rows(engine, "plan_checks", viewer_id=viewer_id)
        return [PlanCheck(row["project_id"], row["agency_id"], row["implementing_agency"], _day(row["plan_date"]),
                          bool(_flag(row["latest"])), None if row["activities"] is None else int(row["activities"]),
                          moment(row["opened_at"])) for row in rows]
