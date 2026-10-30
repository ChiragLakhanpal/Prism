"""find_comparables' period of notices at seam 2, the tool contract (ticket 137): it never ends before it starts.

The period starts with the awards data Strata holds, July 1, 2019 (config/thresholds.toml, past_range.period_from),
and by default ends on the plan's date. A plan older than the awards data would end it before it starts, as the
walkthrough's capture of IN-RRSMP-7516-CW-RFB (P130164, plan of June 20, 2018) showed on October 29, 2026: "They had
to be in India and have notices from July 1, 2019 to June 20, 2018". Such a plan's period runs to the as-of date
instead, and criteria.period says so, which section 1's note (web/src/lib/period.ts) writes as its own sentence. When
even that ends before it starts, no package can match, and the period says why instead of naming a range.

The fixture reads no plan of P130164, though its documents list names them all, so P130164's package is tested on a
copy of the fixture database that holds the newest plan's row for it (tests/record_comparables_api.py,
india_database). The answers the screen tests serve are recorded by the same module and checked here.
"""

import datetime as dt
import json
import tomllib
from pathlib import Path

import pytest

from record_comparables_api import AS_OF, INDIA_PACKAGE, answers, india_database, plan_dates
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry
from strata.tools.find_comparables import EMPTY, FORWARD

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "tests" / "fixtures" / "api"
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
DATA_STARTS = "2019-07-01"  # the first day of the contract awards data since FY2020 (docs/PLAN.md section 3)
TRUTH = {value["id"]: value for value in
         tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
INDIA_PLAN_DATE = TRUTH["plan-p130164-newest-date"]["value"].isoformat()


@pytest.fixture(scope="module")
def india(fixture_db, tmp_path_factory):
    with DuckDBEngine.open(india_database(tmp_path_factory.mktemp("india-plan")), read_only=True) as engine:
        yield engine


def find(engine, as_of=AS_OF, **criteria):
    return registry.call("find_comparables", {"step_reference": INDIA_PACKAGE, "as_of": as_of, **criteria},
                         registry.Context(engine=engine, viewer=ANA))


def test_a_plan_older_than_the_awards_data_compares_packages_from_the_data_s_start_to_the_as_of_date(india):
    result = find(india)

    assert result["package"]["plan"]["plan_date"] == INDIA_PLAN_DATE
    criteria = result["criteria"]
    assert (criteria["notice_from"], criteria["notice_to"], criteria["period"]) == (
        DATA_STARTS, "2026-10-30", "plan_before_data")
    # The period no longer ends on the plan's date, so the package did not give it.
    assert "notice_to" not in criteria["from_package"]


def test_an_as_of_date_before_the_awards_data_matches_no_package_and_says_why_instead_of_a_range(india):
    # The plan of June 20, 2018 is public by December 1, 2018, but the awards data Strata holds starts in 2019.
    result = find(india, as_of=dt.date(2018, 12, 1))

    assert result["criteria"]["period"] == "before_data"
    assert result["abstention"] == {"reason": "no_comparables", "matched": 0}
    assert result["rows"] == [] and result["coverage"] == {"matched": 0, "used": 0, "not_used": []}


def test_a_period_the_call_gives_that_ends_before_it_starts_matches_no_package(india):
    result = find(india, notice_from="2024-01-01", notice_to="2023-01-01")

    assert result["criteria"]["period"] == "ends_before_start"
    assert result["abstention"] == {"reason": "no_comparables", "matched": 0}


def test_for_every_plan_date_in_the_fixture_the_period_never_ends_before_it_starts(fixture_db):
    """Every plan date the fixture holds, as of the plan's own date and as of October 30, 2026, from the recording the
    screen tests build section 1's note from (web/tests/package-period.spec.ts)."""
    recorded = json.loads((RECORDED / "notice-periods.json").read_text())
    entries = recorded["periods"]

    assert recorded["period_from"] == DATA_STARTS
    assert {entry["plan_date"] for entry in entries} == {day.isoformat() for day in plan_dates(fixture_db)}
    for entry in entries:
        assert entry["period"] in FORWARD + EMPTY, entry
        if entry["period"] in FORWARD:
            assert entry["notice_from"] <= entry["notice_to"], entry
        older = entry["plan_date"] < DATA_STARTS
        if entry["as_of"] < DATA_STARTS:
            assert entry["period"] == "before_data", entry
        else:
            assert (entry["period"], entry["notice_to"]) == (
                ("plan_before_data", entry["as_of"]) if older else ("plan_date", entry["plan_date"])), entry
    # P130164's newest plan, the walkthrough's: the period the ticket's sentence names.
    assert {"plan_date": INDIA_PLAN_DATE, "as_of": "2026-10-30", "notice_from": DATA_STARTS, "notice_to": "2026-10-30",
            "period": "plan_before_data"} in entries
    # The fixture holds plans from both sides of the awards data's start, and as-of dates before it.
    assert {entry["period"] for entry in entries} == {"plan_date", "plan_before_data", "before_data"}


def test_the_recorded_answers_are_what_the_tool_and_the_routes_give(fixture_db, tmp_path):
    for name, text in answers(tmp_path).items():
        assert text == (RECORDED / name).read_text(), f"{name} is out of date: run tests/record_comparables_api.py"
