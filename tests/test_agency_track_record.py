"""agency_track_record (ticket 36), at seam 2: how an implementing agency's past packages went against its plans.

It counts the activities of one of the agency's Procurement Plan versions by their Signed Contract step in
strata.silver.plan_step_delays, the one definition of delay, never computing delay itself. Expected values come
from tests/ground_truth/agency_track_record_nwwda_2026_10_09.sql and tests/ground_truth/values.toml.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.config import load_thresholds, load_tools
from strata.dbx import Viewer
from strata.lakehouse import ground_truth
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
TRUTH = ground_truth.read(ROOT / "tests" / "ground_truth" / "agency_track_record_nwwda_2026_10_09.sql")
VIEWER = Viewer(email="ana.example@worldbank.org", name="Ana Example", user_id="4021@1984", token="not-a-real-token")
NWWDA = "Northern Water Works Development Agency"


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as opened:
        yield opened


def track(engine, as_of=dt.date(2026, 10, 22), **arguments):
    arguments = {"project_id": "P156634", "implementing_agency": NWWDA, "plan_date": "2026-10-09", **arguments}
    return registry.call("agency_track_record", arguments, registry.Context(engine, VIEWER, "staff", as_of))


def test_the_counts_are_the_ground_truth_s_and_come_back_in_a_citable_summary(engine):
    result = track(engine)
    [header, values] = TRUTH.expected

    counts = result["summary"]["counts"]
    assert {name: str(counts[name]) for name in header} == dict(zip(header, values, strict=True))
    assert result["summary"]["evidence_id"].startswith("strata.tools.agency_track_record:P156634/")
    assert counts["late_days"] == int(TRUTH.params["late_days"]) == load_thresholds().value("agency_track_record.late_days")
    assert result["agency"] == {"agency_id": "northern-water-works-development-agency", "agency_name": NWWDA}
    assert result["plan"]["plan_date"] == "2026-10-09"


def test_below_twenty_packages_there_is_no_middle_delay(engine):
    """Rule 15: no middle, range or "in 10" from fewer than 20 cases; the five NWWDA versions give seven."""
    counts = track(engine)["summary"]["counts"]

    assert counts["n"] < load_thresholds().value("agency_track_record.min_packages_for_middle") == 20
    assert counts["middle_delay_days"] is None


def test_it_reads_delay_from_plan_step_delays_and_never_recomputes_it(engine):
    result = track(engine)
    row = next(row for row in result["rows"] if row["step_reference"] == "KE-NWWDA-229129-CW-RFB")

    assert row["delay_days"] == VALUES["plan-229129-days-late"]["value"]
    assert (row["first_planned_on"], row["signed_on"]) == (
        VALUES["plan-229129-first-planned-signing"]["value"].isoformat(), VALUES["plan-229129-signed"]["value"].isoformat())
    assert row["state"] == "signed_late"
    assert row["evidence_id"] == "strata.silver.plan_rows:40132287/KE-NWWDA-229129-CW-RFB"


def test_it_counts_the_plan_s_signed_dates_and_names_the_two_packages_the_awards_dataset_shows_signed(engine):
    """The trap: the October 9, 2026 plan shows no signed contract for KE-NWWDA-541055-CW-RFB and shows
    KE-NWWDA-541062-CW-RFQ Pending Implementation, while the awards dataset shows both signed."""
    result = track(engine)
    by_reference = {row["step_reference"]: row for row in result["rows"]}

    assert result["signed_from"] == "plan"
    for reference, award in (("KE-NWWDA-541055-CW-RFB", "award-541055-signed"), ("KE-NWWDA-541062-CW-RFQ", "award-541062-signed")):
        row = by_reference[reference]
        assert (row["state"], row["signed_on"]) == ("open_past_date", None)
        assert row["awards_signed_on"] == VALUES[award]["value"].isoformat()
    assert [entry["step_reference"] for entry in result["differs_from_awards"]] == [
        "KE-NWWDA-541055-CW-RFB", "KE-NWWDA-541062-CW-RFQ"]
    assert result["summary"]["counts"]["differs_from_awards"] == 2
    assert result["coverage"]["not_used"] == [{"reason": "not_signed", "count": 2, "evidence_ids": [
        "strata.silver.plan_rows:40132287/KE-NWWDA-541055-CW-RFB", "strata.silver.plan_rows:40132287/KE-NWWDA-541062-CW-RFQ"]}]


def test_as_of_a_date_before_a_contract_was_public_its_award_does_not_count(engine):
    """ADR 0002: as of June 1, 2026 the KE-NWWDA-541055-CW-RFB contract of June 22 was not public yet, and the
    October 9 plan was not public either, so the tool checks the agency's latest version public then."""
    result = track(engine, as_of=dt.date(2026, 6, 1), plan_date=None)

    assert result["plan"]["plan_date"] == "2026-03-05"
    assert all(entry["step_reference"] != "KE-NWWDA-541055-CW-RFB" for entry in result["differs_from_awards"])
    for row in result["rows"]:
        assert row["public_from"] <= "2026-06-01"


def test_an_agency_with_no_plan_gets_an_abstention(engine):
    result = track(engine, implementing_agency="Wajir Water and Sewerage Company", plan_date=None)

    assert result["rows"] == [] and result["abstention"]["reason"] == "no_plan_from_agency"


def test_it_is_in_the_registry_with_a_benchmark_question():
    tool = load_tools()["agency_track_record"]

    assert tool.benchmark == "agency-track-record-nwwda-2026-10-09"
    assert tool.result.summary_fields == ("counts",)
