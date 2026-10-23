"""Fetching (seam 1): pages come from the recorded fixture in the gate and from the live APIs on the
workspace, and bronze keeps each page once, by its content hash.

The live adapter is driven here by a fake transport that serves recorded pages, so the paging,
the watermark and the contact stripping are proved offline. The workspace step in
docs/workspace-catchup.md runs the job against the real APIs.
"""

import copy
import datetime as dt
import json
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from strata import config
from strata.lakehouse import nightly, pages
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded"
LAYERS = {
    "bronze": "SELECT count(*) FROM strata.bronze.api_pages",
    "silver": "SELECT (SELECT count(*) FROM strata.silver.awards) + (SELECT count(*) FROM strata.silver.notices) "
              "+ (SELECT count(*) FROM strata.silver.projects)",
    "gold": "SELECT (SELECT count(*) FROM strata.gold.contract) + (SELECT count(*) FROM strata.gold.notice) "
            "+ (SELECT count(*) FROM strata.gold.package) + (SELECT count(*) FROM strata.gold.supplier)",
}


def recorded(file):
    return json.loads((RECORDED / file).read_text())["response"]


def counts(engine):
    return {layer: engine.run(sql).rows[0][0] for layer, sql in LAYERS.items()}


@pytest.fixture
def fixture_copy(fixture_db, tmp_path):
    """A writable copy of the fixture database the gate built."""
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        yield engine


def restamped(source, engine):
    """The recorded pages again, fetched a day later: Finances One has stamped every row with a new as_of_date."""
    for page in pages.recorded_pages(source):
        body = copy.deepcopy(page.body)
        for row in body.get("data") or []:
            row["as_of_date"] = "24-Oct-2026"
        yield pages.Page(page.source, page.request, body, page.fetched_at + dt.timedelta(days=1))


def test_a_second_fetch_with_no_source_changes_adds_no_bronze_rows(fixture_copy):
    before = counts(fixture_copy)

    run_id = nightly.run_locally(fixture_copy, run_id="second", fetch=restamped)

    assert counts(fixture_copy) == before
    fetched = fixture_copy.run("SELECT rows_changed FROM strata.ops.pipeline_runs "
                               "WHERE run_id = :run_id AND task_key = 'fetch_by_watermark'", {"run_id": run_id}).rows
    assert fetched == ((0,),)


def test_a_page_whose_records_changed_is_kept_again_and_gold_takes_the_new_value(fixture_copy):
    def revised(source, engine):
        for page in pages.recorded_pages(source):
            body = copy.deepcopy(page.body)
            for row in body.get("data") or []:
                if row["wb_contract_number"] == "1903781":
                    row["supplier_contract_amount_usd"] = 1300000.0
            yield pages.Page(page.source, page.request, body, page.fetched_at + dt.timedelta(days=1))

    before = counts(fixture_copy)
    nightly.run_locally(fixture_copy, run_id="revised", fetch=revised)

    assert counts(fixture_copy)["bronze"] == before["bronze"] + 1  # only the awards page that changed
    amount = fixture_copy.run("SELECT contract_amount_usd FROM strata.gold.contract WHERE wb_contract_number = '1903781'")
    assert str(amount.rows[0][0]) == "1300000.00"


# ── The live adapter, with a fake transport ──────────────────────────────

class FakeAPI:
    """Serves one recorded response a page at a time, as the live API pages it."""

    def __init__(self, records_key, rows, total_key):
        self.records_key, self.rows, self.total_key, self.asked = records_key, rows, total_key, []

    def __call__(self, url):
        self.asked.append(url)
        query = parse_qs(urlparse(url).query)
        size = int((query.get("top") or query["rows"])[0])
        offset = int((query.get("skip") or query["os"])[0])
        return json.dumps({self.total_key: str(len(self.rows)), self.records_key: self.rows[offset:offset + size]})


def source(key, **changes):
    import dataclasses

    return dataclasses.replace(config.load_sources()[key], **changes)


def test_the_awards_fetch_asks_finances_one_for_kenya_page_by_page_until_the_rows_run_out():
    rows = recorded("api/awards/P156634.json")["data"]
    api = FakeAPI("data", rows, "count")

    fetched = list(pages.live_pages(source("awards", page_size=100), api))

    assert [len(page.body["data"]) for page in fetched] == [100, 100, 80]
    assert api.asked[0] == ("https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS00005"
                            "&resourceId=RS00005&type=json&filter=borrower_country_code%3D%27KE%27&top=100&skip=0")
    assert [parse_qs(urlparse(url).query)["skip"] for url in api.asked] == [["0"], ["100"], ["200"]]


def test_the_notices_fetch_stops_at_the_first_page_older_than_what_bronze_holds():
    rows = sorted(recorded("api/notices/P156634.json")["procnotices"], key=lambda row: row["submission_date"],
                  reverse=True)
    api = FakeAPI("procnotices", rows, "total")
    held = dt.date.fromisoformat(rows[150]["submission_date"][:10])  # bronze holds notices up to the 151st newest

    fetched = list(pages.live_pages(source("notices", page_size=100), api, newest_held=held))

    assert len(fetched) == 2  # the second page reaches back past it, so the 399 notices take two pages, not four
    assert "project_ctry_name=Kenya" in api.asked[0] and "srt=submission_date&order=desc" in api.asked[0]


def test_a_live_page_loses_its_contact_details_and_a_date_after_the_fetch_falls_back_to_the_fetch_day():
    rows = recorded("api/notices/P156634.json")["procnotices"]
    api = FakeAPI("procnotices", rows, "total")
    fetched_on = dt.datetime(2026, 10, 1, tzinfo=dt.UTC)  # before notice OP00474946's date, October 13, 2026
    live = list(pages.live_pages(source("notices", page_size=500), api, clock=lambda: fetched_on))

    with DuckDBEngine.open() as engine:
        from strata.lakehouse import bronze, catalog, silver

        catalog.build(engine)
        bronze.store(engine, source("notices"), live)
        silver.run(engine, source("notices"))
        body = engine.run("SELECT body FROM strata.bronze.api_pages").rows[0][0]
        notice = engine.run("SELECT notice_date, public_from FROM strata.silver.notices "
                            "WHERE notice_id = 'OP00474946'").rows

    assert "info@nwwda.go.ke" not in body and "Abdikadir Noor Osman" not in body
    assert notice == ((dt.date(2026, 10, 13), dt.date(2026, 10, 1)),)
