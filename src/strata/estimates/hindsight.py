"""The hindsight test (ticket 34; docs/PLAN.md section 10): Strata replayed as of each closed pilot project's
approval date, counting which risks its completion report later blamed Strata would have shown.

It is a scorer for the replay harness (strata.estimates.harness, the spec's seam 5). Each gate-set project is
one window: the cutoff is its approval date, and the outcomes are read as of the run. For each project the scorer

1. reads the main packages of its first Procurement Plan: the hindsight.main_packages largest by Estimated
   Amount (US$), as of the run, since the packages are the question;
2. runs the risk-table builder (strata.packages.risks, ticket 30) for each one, frozen at the approval date,
   with the package's category, Method and country, and keeps the risks each table shows (at most
   package_risks.max_rows; a row the verifier removed is not shown). Every row and passage a table rests on
   goes through the harness's frozen reader, which stops the run if one was public after the approval date;
3. asks get_lessons, frozen the same way, whether a lesson in the library already covered each blamed risk.

The library in a replay is the one decided by the run's date, with each lesson counted from the day the quotes
it rests on became public (get_lessons, call.decided_by). Strata did not exist on a 2014 approval date, so
counting lessons from their 2026 decisions would leave the library empty at every approval date.

A project's blamed risks are the reconciled set the coding tool stored (strata.estimates.hindsight_coding):
two coders' readings of the ICR, with the ICR Review settling where they differ. A blamed risk is caught when
any main package's table showed it.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import resources

from strata.config import Thresholds
from strata.estimates.harness import HARNESS, Replay, Score, Scored
from strata.estimates.past_range import as_date
from strata.tools import registry

SCORER = "hindsight_test"
MODEL = "strata.packages.risks"


def _sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "hindsight" / f"{name}.sql").read_text()


@dataclass(frozen=True)
class Settings:
    """The test's settings, from config/thresholds.toml's [hindsight] and the builder's max_rows."""

    main_packages: int
    checklist_size: int
    interval_level: float
    min_blamed_for_share: int
    expected_projects: int
    mcnemar_alpha: float
    notices_from: dt.date
    max_rows: int

    @classmethod
    def from_thresholds(cls, thresholds: Thresholds) -> Settings:
        value = thresholds.value
        return cls(int(value("hindsight.main_packages")), int(value("hindsight.checklist_size")),
                   float(value("hindsight.interval_level")), int(value("hindsight.min_blamed_for_share")),
                   int(value("hindsight.expected_projects")), float(value("hindsight.mcnemar_alpha")),
                   as_date(value("hindsight.notices_from")), int(value("package_risks.max_rows")))


@dataclass(frozen=True)
class Case:
    """One gate-set project: when it was approved, its sector, the risks its completion report blamed (risk keys
    from config/lessons.toml) and the checklist the baseline shows for it."""

    project_id: str
    approval_date: dt.date
    sector: str | None
    blamed: tuple[str, ...]
    checklist: tuple[str, ...]


def _criteria(package: Mapping, notices_from: dt.date) -> dict:
    """find_comparables' arguments for a first-plan package, as a planned package with no STEP row gives them."""
    from strata.tools.find_comparables import CATEGORIES

    return {"category": CATEGORIES.get(str(package["section"] or "").upper()), "method": package["method"],
            "country": package["country_code"], "notice_from": notices_from}


def _risks_build(*args, **options):
    from strata.packages import risks

    return risks.build(*args, **options)


def _detail(package: Mapping, table) -> dict:
    """What one frozen risk table showed, with the date each source it cites became public, for the stored record."""
    payload = table.payload
    return {"step_reference": package["activity_reference_no"],
            "estimated_amount_usd": None if package["estimated_amount_usd"] is None
            else f"{float(package['estimated_amount_usd']):.2f}",
            "empty_reason": payload.get("empty_reason"),
            "rows": [{"risk_key": row["risk_key"], "lesson_evidence_id": row["lesson"]["evidence_id"],
                      "sources": [{"evidence_id": source["evidence_id"], "public_from": source["public_from"]}
                                  for source in row["sources"]]}
                     for row in payload.get("rows", [])],
            "removed": [row["risk_key"] for row in ((payload.get("verifier") or {}).get("removed") or [])]}


class HindsightScorer:
    """The replay harness's scorer for the hindsight test: one window per gate-set project."""

    name = SCORER

    def __init__(self, cases: Mapping[str, Case], builder: Callable = _risks_build, model: str = MODEL):
        self.cases, self.builder, self.model = dict(cases), builder, model

    def score(self, replay: Replay) -> Scored:
        case = self.cases[replay.window.segment]
        settings = Settings.from_thresholds(replay.thresholds)
        cutoff, decided_by = replay.window.cutoff, replay.window.outcomes_through
        engine = replay.inputs.engine
        packages = replay.outcomes.rows(_sql("first_plan"), project_id=case.project_id)[:settings.main_packages]
        shown: list[str] = []
        details, read = [], [cutoff]
        for package in packages:
            table = self.builder(engine, HARNESS, as_of=cutoff, criteria=_criteria(package, settings.notices_from),
                                 words=package["description"], thresholds=replay.thresholds, decided_by=decided_by)
            rows = replay.inputs.checked([row for _, row in table.facts.items()])
            read += [as_date(row["public_from"]) for row in rows if row.get("public_from")]
            details.append(_detail(package, table))
            shown += [row["risk_key"] for row in table.payload.get("rows", []) if row["risk_key"] not in shown]

        context = registry.Context(engine, HARNESS, "staff", cutoff, replay.thresholds, decided_by)
        covered = []
        for key in case.blamed:
            found = registry.call("get_lessons", {"risk_factor": key, "limit": 1}, context)
            read += [as_date(row["public_from"]) for row in replay.inputs.checked(found["rows"])]
            if found["rows"]:
                covered.append(key)
        caught = [key for key in case.blamed if key in shown]
        checklist_caught = [key for key in case.blamed if key in case.checklist]
        scores = [Score("blamed", len(case.blamed)), Score("covered", len(covered)), Score("shown", len(caught)),
                  Score("checklist_caught", len(checklist_caught)), Score("packages", len(packages)),
                  Score("blamed_keys", text=json.dumps(list(case.blamed))),
                  Score("covered_keys", text=json.dumps(covered)), Score("shown_keys", text=json.dumps(caught)),
                  Score("every_shown_key", text=json.dumps(shown)),
                  Score("checklist_keys", text=json.dumps(list(case.checklist))),
                  Score("package_tables", text=json.dumps(details)),
                  Score("inputs_through", text=max(read).isoformat())]
        return Scored(scores, params={"project_id": case.project_id, "approval_date": cutoff.isoformat(),
                                      "main_packages": settings.main_packages, "max_rows": settings.max_rows})
