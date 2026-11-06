"""Ticket 147: the two deep research readers that read the lakehouse, isr_narrative and procurement_notices, on the
fixture database for P156634, as of November 5, 2026, the day the sample brief's items were read."""

import re

import pytest
from research_world import NOV_5

from strata.config import load_research
from strata.lakehouse.engine import DuckDBEngine
from strata.research.items import ITEM_KEYS
from strata.research.project import project_facts
from strata.research.sources import read

ISR_19, ISR_18 = "40114539", "40091292"


@pytest.fixture(scope="module")
def project():
    return project_facts("P156634")


@pytest.fixture
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as opened:
        yield opened


def test_the_isr_reader_keeps_the_two_newest_isrs_status_passages_and_comments_on_targets(project, engine):
    result = read(load_research()["isr_narrative"], project, None, engine, NOV_5)

    assert result.reached and result.status == "read"
    by_id = {item["evidence_id"]: item for item in result.items}
    solar = by_id[f"strata.research.item:P156634/isr_narrative/{ISR_19}-p2-s4"]
    assert "Solarization of" in solar["text"] and "complete" in solar["text"]
    assert solar["public_from"] == solar["published"] == "2026-06-30"
    assert solar["url"].endswith("P156634-a6497888-50b9-45b4-88d2-1303b0327745.pdf#page=2")
    works = by_id[f"strata.research.item:P156634/isr_narrative/{ISR_18}-p2-s4"]
    assert "Overall physical progress of works contracts is at 85 percent" in works["text"]
    assert works["public_from"] == "2026-03-12"
    kwale = [item for item in result.items if "once Kwale contracts are complete" in item["text"]]
    assert any(item["evidence_id"].split("/")[-1].startswith(ISR_18) for item in kwale)
    assert {item["evidence_id"].split("/")[-1].split("-")[0] for item in result.items} == {ISR_19, ISR_18}
    assert all(item["kind"] == "bank_report" and set(item) == set(ITEM_KEYS) for item in result.items)
    sections = {item["evidence_id"].rsplit("-", 1)[-1] for item in result.items}
    assert sections == {"s4", "s6", "s7"}  # status (4.1) and the results indicators (6.1, 6.2), never the ratings


def test_the_isr_reader_reads_as_of_its_day(project, engine):
    import datetime as dt

    result = read(load_research()["isr_narrative"], project, None, engine, dt.datetime(2026, 5, 1, tzinfo=dt.UTC))

    assert {item["evidence_id"].split("/")[-1].split("-")[0] for item in result.items} == {ISR_18, "40038432"}


def test_the_notice_reader_gives_the_awards_and_the_invitation_of_the_last_180_days(project, engine):
    result = read(load_research()["procurement_notices"], project, None, engine, NOV_5)

    ids = [item["evidence_id"].rsplit("/", 1)[-1] for item in result.items]
    assert ids == ["OP00474946", "OP00474700", "OP00474696", "OP00471125", "OP00466974", "OP00457686",
                   "OP00456907"]
    award = result.items[0]
    assert award["title"] == ("Contract Award OP00474946, KE-NWWDA-541055-CW-RFB (Request for Bids): Equipping of "
                              "Exploratory Boreholes Project-Lot 1- Sarman - Tarbaj Water Supply")
    assert award["public_from"] == award["published"] == "2026-10-13"
    assert award["url"] == "https://projects.worldbank.org/en/projects-operations/procurement-detail/OP00474946"
    assert result.items[1]["title"].startswith("Invitation for Bids OP00474700")
    direct = [item for item in result.items if "(Direct Selection)" in item["title"]]
    assert [item["published"] for item in direct] == ["2026-09-25", "2026-07-20"]


def test_no_notice_text_keeps_a_contact_detail(project, engine):
    result = read(load_research()["procurement_notices"], project, None, engine, NOV_5)

    for item in result.items:
        assert not re.search(r"[\w.]+@[\w-]+\.\w+", item["text"]), item["evidence_id"]
        assert not re.search(r"(?:\+254|\b07\d{2})[\s-]?\d{3}[\s-]?\d{3}", item["text"]), item["evidence_id"]


def test_a_reader_with_no_lakehouse_reaches_nothing(project):
    result = read(load_research()["procurement_notices"], project, None, None, NOV_5)

    assert (result.reached, result.items, result.status) == (False, [], "no database")
