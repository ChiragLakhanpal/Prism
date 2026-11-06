"""Ticket 154: three more deep research sources a procurement specialist reaches for, over the recordings of November
5, 2026 (data/fixture/recorded/research/, made by ops/research/record.py with Prism's named client), with the network
off: GDACS's disaster alerts for the project's country (site_conditions), the implementing agencies' own news pages
(agency_statements), and the World Bank's list of ineligible firms and individuals checked against the project's
suppliers (sanctions), read from a downloaded copy."""

import dataclasses
import datetime as dt
import re
import zipfile

import pytest
from research_world import NOV_5, RECORDED, answers

from strata.config import load_research
from strata.lakehouse.engine import DuckDBEngine
from strata.research import fetching
from strata.research.items import ITEM_KEYS
from strata.research.project import project_facts
from strata.research.sources import read
from strata.research.sources.agency_statements import written_date
from strata.research.sources.sanctions import normalised

KENYA = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?country=Kenya&fromDate=2024-11-05&toDate=2026-11-05"
NWWDA = "https://nwwda.go.ke/index.php/news-events"
ELDAS = ("https://nwwda.go.ke/index.php/news-events/115-commissioning-of-eldas-town-water-supply-project-on-2nd-june-"
         "2026")


@pytest.fixture(scope="module")
def project():
    return project_facts("P156634")


@pytest.fixture(scope="module")
def recorded():
    return fetching.offline(RECORDED)


def source(key, **settings):
    found = load_research()[key]
    return dataclasses.replace(found, settings={**found.settings, **settings}) if settings else found


def well_formed(item, project_id, key):
    assert set(item) == set(ITEM_KEYS)
    assert item["evidence_id"].startswith(f"strata.research.item:{project_id}/{key}/")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["public_from"])
    assert item["url"].startswith("https://")
    assert not re.search(r"[\w.]+@[\w-]+\.[a-z]{2,}", item["text"] + (item["author"] or ""))


# ── site_conditions ──────────────────────────────────────────────────────

def test_gdacs_gives_kenya_s_drought_alerts_with_their_dates_alert_level_and_report(project, recorded):
    result = read(source("site_conditions"), project, recorded, None, NOV_5)

    assert (result.reached, result.status) == (True, "200")
    assert [item["evidence_id"].rsplit("/", 1)[1] for item in result.items] == ["DR-1027450", "DR-1027465",
                                                                               "DR-1017863"]
    somalia = result.items[2]
    well_formed(somalia, "P156634", "site_conditions")
    assert somalia["kind"] == "site_condition" and somalia["title"] == "Drought in Kenya, Somalia"
    assert somalia["observed"] == somalia["published"] == "2025-05-21"
    assert "Alert level: Orange." in somalia["text"] and "to: 30 Mar 2026" in somalia["text"]
    assert somalia["url"] == "https://www.gdacs.org/report.aspx?eventid=1017863&episodeid=32&eventtype=DR"
    assert somalia["author"] == "GDACS" and somalia["source"]["url_of_source"] == KENYA
    assert somalia["source"]["license"].startswith("GDACS, the Global Disaster Alert and Coordination System")


def test_gdacs_gives_india_s_events_for_a_project_in_india(project, recorded):
    india = dataclasses.replace(project, country_name="India", approval_date=None)

    result = read(source("site_conditions"), india, recorded, None, NOV_5)

    assert result.reached and len(result.items) == 11
    assert all("India" in item["title"] or "India" in item["text"] for item in result.items)
    assert all(item["observed"] and "Alert level: " in item["text"] for item in result.items)


def test_gdacs_s_refusal_reaches_nothing(project):
    refusing = answers((KENYA, (403, "Forbidden")))

    result = read(source("site_conditions"), project, refusing, None, NOV_5)

    assert (result.reached, result.status, result.items) == (False, "403", [])


# ── agency_statements ────────────────────────────────────────────────────

def test_the_agencies_own_pages_give_their_entries_with_the_agency_as_author(project, recorded):
    result = read(source("agency_statements"), project, recorded, None, NOV_5)

    assert result.reached
    assert result.note.startswith("Prism read the news pages of NWWDA, CWWDA, KWAWASCO and kept ")
    eldas = next(item for item in result.items if item["url"] == ELDAS)
    well_formed(eldas, "P156634", "agency_statements")
    assert eldas["kind"] == "agency_statement"
    assert eldas["title"] == "Commissioning of Eldas Town Water Supply Project on 2nd June 2026"
    assert eldas["published"] == "2026-06-02"
    assert eldas["author"] == "Northern Water Works Development Agency"
    assert "Eldas" in eldas["text"]
    authors = {item["author"] for item in result.items}
    assert authors == {"Northern Water Works Development Agency", "Coast Water Works Development Agency",
                       "Kwale Water and Sewerage Company Ltd."}


def test_only_the_pages_of_the_agencies_the_project_names_are_read(project):
    coast_only = dataclasses.replace(project, implementing_agencies=tuple(
        agency for agency in project.implementing_agencies if "CWWDA" in agency.short_names))
    fetch = answers((NWWDA, (200, "<html></html>")))

    with pytest.raises(AssertionError, match="the test gave no answer for https://cwwda.go.ke/news"):
        read(source("agency_statements"), coast_only, fetch, None, NOV_5)
    assert fetch.calls == ["https://cwwda.go.ke/news"]


def test_a_page_that_refuses_reaches_nothing(project):
    north = dataclasses.replace(load_research()["agency_statements"],
                                pages=tuple(page for page in load_research()["agency_statements"].pages
                                            if page.agency == "NWWDA"))
    result = read(north, project, answers((NWWDA, (403, "Forbidden"))), None, NOV_5)

    assert (result.reached, result.items) == (False, [])
    assert result.note == "NWWDA's page answered 403."


@pytest.mark.parametrize("text, day", [
    ("Commissioning of Eldas Town Water Supply Project on 2nd June 2026", dt.date(2026, 6, 2)),
    ("November 4, 2026", dt.date(2026, 11, 4)),
    ("img/newsImages/WhatsApp Image 2025-05-22 at 10.30.11.jpg", dt.date(2025, 5, 22)),
    ("TENDER NOTICE", None),
])
def test_an_entry_s_date_is_the_one_it_writes(text, day):
    assert written_date(text) == day


# ── sanctions ────────────────────────────────────────────────────────────

LIST_HEADER = ["Firm Name", "Additional Firm Info", "Address", "Country", "Ineligibility Period", "", "Grounds"]
PERIOD = ["", "", "", "", "From Date", "To Date", ""]
PLANTED = [
    ["HALANE CONSTRUCTION COMPANY LTD", "", "Wajir", "Kenya", "01-MAR-2025", "28-FEB-2028", "Fraudulent Practice"],
    ["China Railway No 10 Engineering Group Co Ltd", "", "Beijing", "China", "15-JAN-2026", "Ongoing",
     "Corrupt and Fraudulent Practices"],
    ["A Firm Not On The Project Ltd", "", "", "Kenya", "01-JAN-2024", "01-JAN-2027", "Collusive Practice"],
]


def planted_xlsx(path, rows):
    """A workbook like the page's export: inline strings, the period's dates in the row under its title."""
    def cell(column, row, text):
        return f'<c r="{chr(65 + column)}{row}" t="inlineStr"><is><t>{text}</t></is></c>'

    sheet = "".join(f'<row r="{number}">' + "".join(cell(column, number, text) for column, text in enumerate(row)
                                                    if text) + "</row>"
                    for number, row in enumerate(rows, 1))
    with zipfile.ZipFile(path, "w") as book:
        book.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
                      f'2006/main"><sheetData>{sheet}</sheetData></worksheet>')


@pytest.fixture
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as opened:
        yield opened


def named_suppliers(engine):
    result = engine.run("""
        SELECT count(DISTINCT s.supplier_id) FROM strata.gold.supplier AS s
        WHERE s.name IS NOT NULL AND s.kind <> 'joint venture' AND s.supplier_id IN (
          SELECT cs.supplier_id FROM strata.gold.contract_supplier AS cs
          JOIN strata.gold.contract AS c ON c.contract_id = cs.contract_id
          WHERE c.project_id = 'P156634' AND c.public_from <= DATE '2026-11-05'
          UNION SELECT supplier_id FROM strata.gold.contract
          WHERE project_id = 'P156634' AND public_from <= DATE '2026-11-05')""", {})
    return result.rows[0][0]


def test_the_sanctions_check_finds_a_planted_exact_and_a_planted_normalised_name(project, engine, tmp_path):
    planted_xlsx(tmp_path / "2026-11-04.xlsx", [["World Bank Listing of Ineligible Firms and Individuals"],
                                                LIST_HEADER, PERIOD, *PLANTED])
    (tmp_path / "2026-11-06.csv").write_text("Firm Name\nA later copy the run cannot see yet\n")

    result = read(source("sanctions", folder=str(tmp_path)), project, None, engine, NOV_5)

    checked = named_suppliers(engine)
    assert checked > 150
    assert result.reached and result.counts == {"suppliers_checked": checked, "suppliers_sanctioned": 2}
    summary, *hits = result.items
    assert summary["evidence_id"] == "strata.research.item:P156634/sanctions/summary-2026-11-04"
    assert summary["text"].startswith(f"{checked} suppliers checked against the list of November 4, 2026; 2 on it.")
    assert summary["published"] == "2026-11-04" and summary["kind"] == "sanctions"
    by_firm = {hit["title"].split(",")[0]: hit for hit in hits}
    halane = by_firm["HALANE CONSTRUCTION COMPANY LTD"]
    assert halane["evidence_id"].endswith("/sanctions/hit-503378")
    assert "Grounds: Fraudulent Practice." in halane["text"]
    assert "From Date 01-MAR-2025, To Date 28-FEB-2028" in halane["text"] and "by its exact name" in halane["text"]
    china = by_firm["China Railway No 10 Engineering Group Co Ltd"]
    assert "China Railway No.10 Engineering Group Co., Ltd. matches it by its normalised name" in china["text"]
    for item in result.items:
        well_formed(item, "P156634", "sanctions")


def test_a_csv_copy_is_read_too(project, engine, tmp_path):
    rows = [LIST_HEADER, PERIOD, *PLANTED[:1]]
    (tmp_path / "2026-11-05.csv").write_text("\n".join(",".join(f'"{cell}"' for cell in row) for row in rows) + "\n")

    result = read(source("sanctions", folder=str(tmp_path)), project, None, engine, NOV_5)

    assert result.counts["suppliers_sanctioned"] == 1
    assert result.items[1]["evidence_id"].endswith("/sanctions/hit-503378")


def test_with_no_copy_the_sanctions_check_did_not_run(project, engine, tmp_path):
    result = read(source("sanctions", folder=str(tmp_path)), project, None, engine, NOV_5)

    assert (result.reached, result.status, result.items, result.counts) == (False, "no list", [], {})
    assert result.note == "The sanctions check did not run: the list needs a download from the page."


def test_a_normalised_name_drops_case_punctuation_and_legal_endings():
    endings = tuple(load_research()["sanctions"].settings["legal_endings"])

    assert normalised("China Railway No.10 Engineering Group Co., Ltd.", endings) == \
        "china railway no 10 engineering group"
    assert normalised("SGI STUDIO GALLI INGEGNERIA S.R.L", endings) == "sgi studio galli ingegneria"
    assert normalised("Company", endings) == "company"
