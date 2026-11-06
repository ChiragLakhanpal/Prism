"""Ticket 148: the research_evidence tool returns a deep research run's items as rows and its derived counts as the
summary record, and abstains with not_fetched when no run was made for the project.

The run is ticket 147's demo seed of the sample brief's sources (ops/research/seed.py), kept in a copy of the fixture
database through the research store (tests/research_world.py).
"""

import datetime as dt

import pytest
from research_world import seed_run, seeded_copy

from strata.lakehouse.engine import DuckDBEngine
from strata.dbx import Viewer
from strata.tools import registry

ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
AS_OF = dt.date(2026, 11, 5)


@pytest.fixture(scope="module")
def seeded(fixture_db, tmp_path_factory):
    return seeded_copy(fixture_db, tmp_path_factory.mktemp("research-evidence"))


def call(database, project_id="P156634", as_of=AS_OF):
    with DuckDBEngine.open(database, read_only=True) as engine:
        return registry.call("research_evidence", {"project_id": project_id, "as_of": as_of.isoformat()},
                             registry.Context(engine=engine, viewer=ANA))


def test_a_run_s_items_come_back_as_rows_in_the_one_item_shape(seeded, fixture_db):
    result = call(seeded)

    assert result["abstention"] is None
    assert len(result["rows"]) == len(seed_run(fixture_db)[1]) == 60
    kipevu = next(row for row in result["rows"] if row["title"].startswith("Sh280m Kipevu"))
    assert kipevu["evidence_id"].startswith("strata.research.item:P156634/outlet_feeds/")
    assert kipevu["url"].startswith("https://www.the-star.co.ke/")
    assert kipevu["published"] == "2022-05-16" and kipevu["date_known"] is True
    assert kipevu["source"]["label"] == "News outlets' feeds"
    assert kipevu["location"]["name"] == "Mombasa"
    assert "is expected to be done by October this year" in kipevu["text"]
    undated = next(row for row in result["rows"] if row["title"].startswith("Mombasa water project sparks outrage"))
    assert undated["published"] is None and undated["date_known"] is False


def test_the_summary_counts_the_items_and_the_awards_before_closing(seeded):
    summary = call(seeded)["summary"]

    assert summary["evidence_id"] == "strata.tools.research_evidence:P156634@2026-11-05"
    assert summary["items_total"] == 60
    assert summary["counts_by_kind"] == {"agency_statement": 28, "bank_report": 7, "news": 14, "procurement": 7,
                                         "satellite": 1, "site_condition": 3}
    # P156634 closes on October 31, 2026. Its contract awards from July 13 (110 days before) to closing: July 15 and
    # 20, September 4 and 25, October 12 and 13. Two were by direct selection, July 20 and September 25.
    assert summary["closing_date"] == "2026-10-31"
    assert summary["late_award_days"] == 110
    assert summary["awards_in_window"] == 6
    assert summary["direct_awards_in_window"] == 2
    assert summary["last_award_date"] == "2026-10-13"
    assert summary["days_from_last_award_to_closing"] == 18
    assert [source["key"] for source in summary["sources_not_reached"]] == ["gdelt_news", "sanctions"]
    assert summary["sources_not_reached"][0]["note"] == "GDELT limited calls from this network."
    # Each source's label and kind come from the registry (config/research.toml), so the tab says where each fed.
    assert (summary["sources_not_reached"][0]["label"], summary["sources_not_reached"][0]["kind"]) == ("GDELT", "news")
    assert {source["key"] for source in summary["sources_reached"]} == {
        "isr_narrative", "procurement_notices", "outlet_feeds", "inspection_panel", "sentinel2_mosaic", "mastodon",
        "site_conditions", "agency_statements"}
    # The seed found no copy of the sanctions list, so the check did not run and states no count (ticket 154).
    assert (summary["suppliers_checked"], summary["suppliers_sanctioned"]) == (None, None)
    assert summary["sources_not_reached"][1]["note"] == ("The sanctions check did not run: the list needs a download "
                                                         "from the page.")


def test_a_notice_s_own_dates_come_back_as_fields_of_its_row(seeded):
    """Ticket 155: the first live brief lost six developments whose award dates lived only in a notice's words."""
    rows = {row["evidence_id"].rsplit("/", 1)[1]: row for row in call(seeded)["rows"]}

    # The Sarman - Tarbaj award: published October 13, 2026; its words say "Date Notification of Award Issued
    # (YYYY/MM/DD) 2026/06/22"; strata.gold.notice holds no signing date for it.
    assert rows["OP00474946"]["notice"] == {"notice_date": "2026-10-13", "award_notification_date": "2026-06-22"}
    # The invitation for bids for the same works carries its submission date.
    assert rows["OP00474700"]["notice"] == {"notice_date": "2026-10-12", "submission_date": "2026-10-12"}
    kipevu = next(row for row in rows.values() if row["title"].startswith("Sh280m Kipevu"))
    assert kipevu["notice"] is None


def test_the_coverage_line_says_which_source_was_not_reached(seeded):
    coverage = call(seeded)["coverage"]

    assert coverage["matched"] == coverage["used"] == 60
    assert coverage["not_used"] == [{"reason": "not_reached", "count": 2, "sources": ["gdelt_news", "sanctions"]}]


def test_an_item_made_public_after_the_date_is_left_out_and_counted(seeded):
    result = call(seeded, as_of=dt.date(2026, 10, 1))

    # The run's as-of day is November 5, after October 1, so no run is public yet.
    assert result["abstention"] == {"reason": "not_fetched", "project_id": "P156634"}


def test_with_no_run_for_the_project_it_abstains_not_fetched(fixture_db):
    result = call(fixture_db)

    assert result["rows"] == []
    assert result["abstention"] == {"reason": "not_fetched", "project_id": "P156634"}
    assert result["summary"]["items_total"] is None
