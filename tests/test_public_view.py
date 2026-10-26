"""The public view of a project still under way, at seam 2, the tool contract (ticket 40).

The roles file's [views] says the public view has no signals, time estimates or disagreements on active projects, so
a procurement still under way isn't prejudged (spec, user story 55). The tools apply it themselves, so a page, an
answer and a draft get the same: check_plan keeps only data notes, project_signals and estimate_time abstain with
view_public_active, and get_disagreements returns no disagreement. A closed project is the same in every view.

Whether a project is active is judged as of the page's date, never by the wall clock or by today's status in
strata.gold.project: P156634 closes on October 31, 2026 (values.toml, closing-date-p156634), eight days after this
file's date, and P130164, closed on December 31, 2018 (project-p130164-closing), was active on August 26, 2016.
Expected counts come from the staff view's answers on the same records, never from the rule's own arithmetic.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry
from strata.tools.withheld import project_status

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
TODAY = dt.date(2026, 10, 23)
ISR_7 = TRUTH["isr-7-date"]["value"]  # August 26, 2016
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", user_id="ana", token="token-for-ana-only")
NWWDA = "northern-water-works-development-agency"
PACKAGE = "KE-NWWDA-541062-CW-RFQ"  # a package in P156634's plan of October 9, 2026 (values.toml)


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as opened:
        yield opened


def run(engine, tool, arguments, view, as_of=TODAY):
    return registry.call(tool, arguments, registry.Context(engine, ANA, view, as_of))


def test_whether_a_project_is_active_is_judged_as_of_the_page_date(engine):
    assert TRUTH["closing-date-p156634"]["value"] == dt.date(2026, 10, 31)
    assert project_status(engine, "P156634", TODAY) == "active"
    assert project_status(engine, "P130164", TODAY) == "closed"
    assert project_status(engine, "P130164", ISR_7) == "active"
    assert project_status(engine, "P999999", TODAY) is None


def test_p156634_in_the_public_view_keeps_its_data_notes_and_shows_no_signal(engine):
    staff = run(engine, "check_plan", {"project_id": "P156634", "implementing_agency": NWWDA}, "staff")
    public = run(engine, "check_plan", {"project_id": "P156634", "implementing_agency": NWWDA}, "public")

    assert (staff["counts"]["needs_a_look"], staff["counts"]["watch"], staff["withheld"]) == (1, 2, None)
    assert (public["counts"]["needs_a_look"], public["counts"]["watch"], public["counts"]["signal"]) == (0, 0, 0)
    assert public["counts"]["data_note"] == staff["counts"]["data_note"] == 3
    assert public["withheld"] == "view_public_active"
    marks = {mark["mark"] for row in public["rows"] for mark in row["marks"]}
    assert marks == {"data_note"}
    # The implementing agency preview of its own agency's plan is the same as World Bank staff's.
    assert run(engine, "check_plan", {"project_id": "P156634", "implementing_agency": NWWDA}, "piu")["counts"] == \
        staff["counts"]


def test_p156634_in_the_public_view_has_no_signals_time_estimate_or_disagreement(engine):
    staff_disagreements = run(engine, "get_disagreements", {"subject_id": "P156634"}, "staff")
    public_disagreements = run(engine, "get_disagreements", {"subject_id": "P156634"}, "public")
    signals = run(engine, "project_signals", {"project_id": "P156634"}, "public")
    estimate = run(engine, "estimate_time", {"step_reference": PACKAGE}, "public")

    assert len(staff_disagreements["rows"]) > 0
    assert (public_disagreements["rows"], public_disagreements["abstention"]["reason"]) == ([], "view_public_active")
    assert (signals["rows"], signals["abstention"]["reason"]) == ([], "view_public_active")
    assert (estimate["estimate"], estimate["abstention"]["reason"]) == (None, "view_public_active")
    assert run(engine, "project_signals", {"project_id": "P156634"}, "staff")["status"] == "needs_a_look"
    assert run(engine, "estimate_time", {"step_reference": PACKAGE}, "piu")["abstention"] is None or \
        run(engine, "estimate_time", {"step_reference": PACKAGE}, "piu")["abstention"]["reason"] != "view_public_active"


def test_p130164_a_closed_project_keeps_its_disagreements_in_the_public_view_but_not_as_of_2016(engine):
    staff = run(engine, "get_disagreements", {"subject_id": "P130164"}, "staff")
    public = run(engine, "get_disagreements", {"subject_id": "P130164"}, "public")

    assert public["rows"] == staff["rows"] and len(public["rows"]) > 0
    # On August 26, 2016 the project was still under way, so the public view held back its signals then.
    assert run(engine, "project_signals", {"project_id": "P130164"}, "public", ISR_7)["abstention"]["reason"] == \
        "view_public_active"
    assert run(engine, "project_signals", {"project_id": "P130164"}, "public")["abstention"]["reason"] == "not_active"
