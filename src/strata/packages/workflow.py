"""The plan-a-package workflow (ticket 15): a sentence in, a saved package and its comparables out.

plan() runs four steps, each announced as a step event: read the sentence with the package reader (one
structured call to the drafting model), compute review type and market approach from the thresholds file,
save the package in the app state store (Lakebase on the App, ADR 0005) for the person, then run
find_comparables as the viewer on the criteria that pick the comparables. Nothing is saved until the reader has read the sentence, so a failed model call, or a
sentence with no package in it, leaves nothing in the Packages tab. A person who sets the criteria themselves
skips the reading: the package is saved with their sentence and no criteria.

The spec names Microsoft Agent Framework for workflows in code; like the draft runtime (src/strata/drafts),
this one is plain Python steps, because the framework's package is not in the lockfile and the steps need no
more than this.

package_view() is a saved package as its workspace shows it, and list_rows() the Packages tab's rows.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from strata.agent.claims import ClaimsError
from strata.agent.loop import AgentError, output_text
from strata.config import Thresholds
from strata.dbx import Viewer
from strata.harness.turn import Event
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.packages import criteria as criteria_of, reader
from strata.packages.form import Form
from strata.packages.store import PackageStore, PlanCheck, Saved
from strata.drafts.store import iso

log = logging.getLogger("strata.packages")
# Why a package could not be planned, as the reading page's error event says it. web/src/copy.ts has one
# sentence for each under packageWorkspace.readErrors. no_package is a sentence that describes nothing to
# buy; package_store is the app's own account unable to save, which the viewer cannot fix.
PLAN_ERRORS = ("no_reader", "agent_unavailable", "content_filter", "agent_output", "no_package", "package_store",
               "internal")


class PlanError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def step(name: str, status: str, **details) -> Event:
    return Event("step", {"id": name, "kind": name, "status": status, **details})


@dataclass
class Planning:
    """One package being planned: the sentence, who asked, and what happened, for the run log."""

    sentence: str
    viewer: Viewer
    run_id: str
    read: bool = True
    agent: str | None = None
    agent_version: str | None = None
    package_id: str | None = None


def package_view(saved: Saved, form: Form, thresholds: Thresholds) -> dict:
    """A saved package as its workspace shows it: the sentence, every field with its value and where the value
    came from, the rules behind the computed values, and the find_comparables arguments its criteria give."""
    shown = criteria_of.view(form, criteria_of.Criteria.from_json(saved.criteria), thresholds)
    return {"package_id": saved.package_id, "sentence": saved.sentence, "step_reference": None,
            "created_at": iso(saved.created_at), "saved_at": iso(saved.saved_at),
            "plan_before_range": saved.plan_before_range, **shown}


def list_rows(packages: list[Saved], checks: list[PlanCheck], form: Form, thresholds: Thresholds,
              country_names: dict[str, str], project_countries: dict[str, str | None] | None = None) -> dict:
    """The Packages tab's rows, newest first: the person's packages, by when each was last saved, and the plans
    they checked, by when they last opened each, with their projects' countries by code."""
    project_countries = project_countries or {}
    rows = []
    for saved in packages:
        shown = criteria_of.view(form, criteria_of.Criteria.from_json(saved.criteria), thresholds)
        values = {entry["key"]: entry["value"] for entry in shown["fields"]}
        rows.append({"type": "package", "package_id": saved.package_id, "description": values.get("description"),
                     "country": values.get("country"), "country_name": country_names.get(values.get("country") or ""),
                     "step_reference": None, "project_id": None, "guesses": shown["guesses"],
                     "last_worked_on": iso(saved.saved_at)})
    for check in checks:
        rows.append({"type": "plan_check", "project_id": check.project_id, "agency_id": check.agency_id,
                     "implementing_agency": check.implementing_agency, "plan_date": check.plan_date.isoformat(),
                     "latest": check.latest, "activities": check.activities,
                     "country_name": country_names.get(project_countries.get(check.project_id) or ""),
                     "last_worked_on": iso(check.opened_at)})
    rows.sort(key=lambda row: row["last_worked_on"], reverse=True)
    return {"rows": rows, "counts": {"packages": len(packages), "plan_checks": len(checks), "total": len(rows)}}


async def plan(planning: Planning, reader_for: Callable[[], object | None], form: Form, thresholds: Thresholds,
               countries: Callable[[], dict[str, str]], store: PackageStore, comparables: Callable[[dict], dict],
               now: Callable[[], dt.datetime], new_package_id: Callable[[], str], new_save_id: Callable[[], str],
               max_months: float) -> AsyncIterator[Event]:
    """The planning of one package, as events: the steps, the saved package, then its comparables. A step that
    cannot run raises PlanError with its code. countries gives the World Bank's country list by code."""
    codes = countries()
    if planning.read:
        yield step("read", "running")
        agent = reader_for()
        if agent is None:
            raise PlanError("no_reader")
        planning.agent = getattr(agent, "name", None)
        message = [{"role": "user", "content": json.dumps(reader.message(planning.sentence, form), ensure_ascii=False)}]
        try:
            response = await asyncio.to_thread(agent.respond, message, None)
            planning.agent_version = getattr(agent, "version", None)
            reading = reader.read(output_text(response), form, codes, max_months, thresholds)
        except AgentError as error:
            raise PlanError(error.code if error.code in PLAN_ERRORS else "agent_unavailable") from error
        except ClaimsError as error:
            log.warning("The package reader of run %s answered in a shape I can't read: %s", planning.run_id, error)
            raise PlanError("agent_output") from error
        if not reading.package:
            raise PlanError("no_package")
        guesses = sum(1 for key, entry in reading.values.items()
                      if not entry["stated"] and form.field(key).source == "guessed")
        yield step("read", "done", count=len(reading.values), guesses=guesses)

        yield step("compute", "running")
        criteria = criteria_of.from_reading(form, reading.values, reading.dividing, thresholds, reading.unlisted)
        yield step("compute", "done")
    else:
        criteria = criteria_of.empty(form)

    yield step("save", "running")
    package_id, at = new_package_id(), now()
    try:
        await asyncio.to_thread(store.create, package_id, planning.viewer.user_id, planning.viewer.name,
                                planning.sentence, planning.run_id if planning.read else None, new_save_id(),
                                criteria.as_json(), at)
    except EngineError as error:  # the app's own account saves packages, a PermissionDenied included
        raise PlanError("package_store") from error
    planning.package_id = package_id
    saved = Saved(package_id, planning.viewer.user_id, planning.viewer.name, planning.sentence,
                  planning.run_id if planning.read else None, at, "", criteria.as_json(), None, None, at)
    view = package_view(saved, form, thresholds)
    yield step("save", "done")
    yield Event("package", {"package": view})

    if view["comparables_query"] is None:
        return
    yield step("compare", "running")
    try:
        result = await asyncio.to_thread(comparables, view["comparables_query"])
    except (PermissionDenied, EngineError):
        log.exception("find_comparables failed for the new package %s; its page will try again.", package_id)
        yield step("compare", "failed")
        return
    yield step("compare", "done", count=len(result.get("rows") or []))
    yield Event("comparables", {"result": result})
