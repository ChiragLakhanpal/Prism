"""Assertions, disagreements and the evidence ladder (ticket 20; docs/PLAN.md section 5).

Ratings, dates and amounts from records and documents become dated assertions in
strata.gold.assertion. Each records its subject (a project, or a package by its STEP reference), its
attribute (config/evidence_ladder.toml, [attributes]), its value, the period it describes, when it was
made, its public date, its source document and passage, and its evidence tier. They come from:

- the ISRs' ratings, which ticket 18 read from each ISR's own ratings table (strata.silver.isr_ratings).
  Each ISR rates the period since the ISR before it, so the ratings of one series never overlap and form
  a trajectory, not a disagreement.

The nightly job's detect_disagreements task runs run() for every project the run read, and the fixture
build runs it after the passage reader (gates/build_fixture.py). Every table it writes is rebuilt for
each project of the run.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import astuple, dataclass, fields
from importlib import resources

from strata.config import Ladder, load_ladder
from strata.lakehouse.engine import Engine

PASSAGES = "strata.gold.passage"  # the table a passage's evidence id names, as search_passages returns it
ISR_READER = "isr_ratings"  # ticket 18's reader of each ISR's ratings table (src/strata/lakehouse/isr_ratings.py)
# The periods an assertion can describe.
REPORT_PERIOD, WHOLE_PROJECT, CONTRACT_SIGNING = "report_period", "whole_project", "contract_signing"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _sql(name: str) -> str:
    return (resources.files("strata.knowledge") / "sql" / "assertions" / name).read_text()


def _rows(engine: Engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _date(value) -> dt.date | None:
    """A date from DuckDB (a date or a timestamp) or from the warehouse (ISO text)."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _int(value) -> int | None:
    return None if value is None or value == "" else int(value)


@dataclass(frozen=True)
class Assertion:
    """One row of strata.gold.assertion (its table definition says what each column holds)."""

    assertion_id: str
    subject_kind: str
    subject_id: str
    project_id: str
    attribute: str
    attribute_kind: str
    field_name: str
    value: str
    value_form: str
    judgment: str | None
    period_event: str
    period_start: dt.date
    period_end: dt.date
    made_at: dt.date
    replaced_on: dt.date | None
    evidence_tier: str
    form: str
    source_key: str
    document_id: str
    document_type: str | None
    report_number: str | None
    version: int | None
    sequence: int | None
    passage_id: str
    evidence_id: str
    pdf_page: int | None
    quote: str | None
    read_by: str
    public_from: dt.date


ASSERTION_COLUMNS = tuple(f.name for f in fields(Assertion))


def assertion_id(evidence_id: str, subject_id: str, attribute: str) -> str:
    """A stable id: the evidence it rests on, then its subject and attribute."""
    return f"{evidence_id}#{subject_id}/{attribute}"


# ── The ISRs' ratings ────────────────────────────────────────────────────

def isr_assertions(engine: Engine, project_id: str, ladder: Ladder) -> list[Assertion]:
    """Each ISR's rating of each attribute the ladder knows, for the period since the ISR before it. The
    first ISR's period starts on the day the Board approved the project."""
    found: dict[tuple[str, str], dict] = {}
    for row in _rows(engine, _sql("isr_ratings.sql"), project_id=project_id):
        found.setdefault((row["rating_name"], str(row["document_id"])), row)  # the first passage that prints it
    made = []
    by_name: dict[str, list[dict]] = {}
    for (name, _), row in found.items():
        by_name.setdefault(name, []).append(row)
    for name, series in by_name.items():
        attribute = ladder.attribute_named(name)
        if attribute is None:
            continue
        series.sort(key=lambda row: (_date(row["isr_date"]), str(row["document_id"])))
        previous = None
        for row in series:
            day = _date(row["isr_date"])
            approved = _date(row["approval_date"])
            start = previous + dt.timedelta(days=1) if previous else approved if approved and approved < day else day
            previous = day
            rating = ladder.rating(attribute.key, row["current_rating"])
            if rating is None or not row["passage_id"]:
                continue  # no rating ("--"), or no passage to cite for it
            evidence = f"{PASSAGES}:{row['passage_id']}"
            made.append(Assertion(
                assertion_id(evidence, project_id, attribute.key), "project", project_id, project_id, attribute.key,
                attribute.kind, name, rating, "rating", ladder.side(attribute.key, rating), REPORT_PERIOD, start, day,
                day, _date(row["replaced_on"]), ladder.tier_of(row["document_type"]) or "isr", "rating_field",
                "documents", str(row["document_id"]), row["document_type"], row["report_number"], _int(row["version"]),
                _int(row["sequence"]), row["passage_id"], evidence, _int(row["pdf_page"]), None, ISR_READER,
                _date(row["public_from"])))
    return made


# ── The run ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Report:
    assertions: int


def write(engine: Engine, projects: list[str], assertions: list[Assertion]) -> int:
    """Rebuild strata.gold.assertion for the run's projects."""
    for project_id in projects:
        engine.run("DELETE FROM strata.gold.assertion WHERE project_id = :project_id", {"project_id": project_id})
    return engine.insert_rows("strata.gold.assertion", ASSERTION_COLUMNS, [astuple(row) for row in assertions])


def run(engine: Engine, projects: list[str], *, ladder: Ladder | None = None, run_id: str = "local",
        clock: Callable[[], dt.datetime] = _now) -> Report:
    """Every assertion of the run's projects, rebuilt."""
    ladder = ladder or load_ladder()
    made = [assertion for project_id in projects for assertion in isr_assertions(engine, project_id, ladder)]
    return Report(write(engine, projects, made))


PROJECTS = "SELECT DISTINCT project_id FROM strata.silver.documents ORDER BY project_id"


def default_projects(engine: Engine) -> list[str]:
    """The projects whose documents the passage reader read."""
    return [row["project_id"] for row in _rows(engine, PROJECTS)]


def run_on_fixture(engine: Engine, run_id: str = "fixture", clock: Callable[[], dt.datetime] = _now) -> Report:
    """The run over the fixture database, as the gate builds it."""
    return run(engine, default_projects(engine), run_id=run_id, clock=clock)
