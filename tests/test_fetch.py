"""Fetching (seam 1): pages come from the recorded fixture in the gate and from the live APIs on the
workspace, and bronze keeps each page once, by its content hash.

The live adapter is driven here by a fake transport that serves recorded pages, so the paging,
the watermark and the contact stripping are proved offline. The workspace step in
docs/workspace-catchup.md runs the job against the real APIs.
"""

import copy
import datetime as dt
import decimal
import json
import shutil
import tomllib
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from strata import config
from strata.lakehouse import nightly, pages
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded"
AWKWARD = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["awkward"]
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
        for row in pages.records(source, body):
            if "as_of_date" in row:
                row["as_of_date"] = "24-Oct-2026"
        yield pages.Page(page.source, page.request, body, page.fetched_at + dt.timedelta(days=1))


def test_a_second_fetch_with_no_source_changes_adds_no_bronze_rows(fixture_copy):
    before = counts(fixture_copy)

    run_id = nightly.run_locally(fixture_copy, run_id="second", fetch=restamped)

    assert counts(fixture_copy) == before
    fetched = fixture_copy.run("SELECT rows_changed FROM strata.ops.pipeline_runs "
                               "WHERE run_id = :run_id AND task_key = 'fetch_by_watermark'", {"run_id": run_id}).rows
    assert fetched == ((0,),)


def test_the_same_records_in_another_order_add_no_bronze_rows():
    """Finances One cannot sort, so a later fetch may return a page's records in another order. The
    source has not changed, so bronze keeps each page once."""
    from strata.lakehouse import bronze, catalog

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        for key, file in (("awards", "api/awards/P156634.json"),
                          ("notices", "api/notices/kenya-works-open-on-2026-10-09.json")):
            source = config.load_sources()[key]
            body = recorded(file)
            reordered = dict(body, **{source.records: list(reversed(body[source.records]))})
            url = f"https://example.org/{key}?page=1"

            first = bronze.store(engine, source, [pages.Page(key, url, body, dt.datetime(2026, 10, 23, tzinfo=dt.UTC))])
            later = bronze.store(engine, source, [pages.Page(key, url, reordered, dt.datetime(2026, 10, 24, tzinfo=dt.UTC))])

            assert (key, first, later) == (key, 1, 0)


def test_a_fetch_that_fails_partway_keeps_every_page_it_fetched_before_the_failure():
    """A fetch for every country asks for hundreds of pages, and the API may stop answering partway.
    Bronze keeps each page as it comes, so the pages already fetched are not lost and are not asked
    for again."""
    from strata.lakehouse import bronze, catalog

    rows = recorded("api/awards/P156634.json")["data"]
    source = config.load_sources()["awards"]

    def fetch():
        for number in range(3):
            yield pages.Page("awards", f"https://example.org/awards?top=100&skip={number * 100}",
                             {"count": 280, "data": rows[number * 100:(number + 1) * 100]},
                             dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        raise OSError("The API stopped answering.")

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        with pytest.raises(OSError):
            bronze.store(engine, source, fetch())
        kept = engine.run("SELECT count(*) FROM strata.bronze.api_pages").rows[0][0]

    assert kept == 3


def test_a_page_whose_records_changed_is_kept_again_and_gold_takes_the_new_value(fixture_copy):
    def revised(source, engine):
        for page in pages.recorded_pages(source):
            body = copy.deepcopy(page.body)
            for row in body["data"] if source.key == "awards" else []:
                if row["wb_contract_number"] == "1903781":
                    row["supplier_contract_amount_usd"] = 1300000.0
            yield pages.Page(page.source, page.request, body, page.fetched_at + dt.timedelta(days=1))

    before = counts(fixture_copy)
    nightly.run_locally(fixture_copy, run_id="revised", fetch=revised)

    assert counts(fixture_copy)["bronze"] == before["bronze"] + 1  # only the awards page that changed
    amount = fixture_copy.run("SELECT contract_amount_usd FROM strata.gold.contract WHERE wb_contract_number = '1903781'")
    assert str(amount.rows[0][0]) == "1300000.00"


def test_a_supplier_row_a_later_fetch_drops_leaves_gold(fixture_copy):
    """values.toml, awkward.joint_venture: contract 1624689 went to members 503708 and 503711. When
    a later fetch holds the contract with one member only, gold counts that member alone."""
    def revised(source, engine):
        for page in pages.recorded_pages(source):
            body = copy.deepcopy(page.body)
            if source.key == "awards":
                body["data"] = [row for row in body["data"]
                                if (row["wb_contract_number"], row["supplier_id"]) != ("1624689", "503711")]
            yield pages.Page(page.source, page.request, body, page.fetched_at + dt.timedelta(days=1))

    nightly.run_locally(fixture_copy, run_id="revised", fetch=revised)

    contract = fixture_copy.run("SELECT contract_amount_usd, supplier_id, supplier_count, joint_venture "
                                "FROM strata.gold.contract WHERE wb_contract_number = '1624689'").as_text()
    assert contract == [("697972.33", "503708", "1", "false")]
    members = fixture_copy.run("SELECT supplier_id, joint_venture_id FROM strata.gold.contract_supplier "
                               "WHERE wb_contract_number = '1624689'").rows
    assert members == (("503708", None),)
    ventures = fixture_copy.run("SELECT count(*) FROM strata.gold.supplier WHERE supplier_id = 'JV-503708-503711'")
    assert ventures.rows == ((0,),)


def test_a_joint_venture_whose_members_sit_on_two_pages_keeps_both_when_only_one_page_changes():
    """values.toml, awkward.joint_venture: contract 1624689 went to members 503708 and 503711. When a
    country's awards fill two pages, a later fetch may change the first page only. Bronze keeps the
    second page from its first fetch, as its content did not change, and that page still counts."""
    venture = AWKWARD["joint_venture"]
    rows = recorded(venture["awards"])["data"]
    second = [row for row in rows if (row["wb_contract_number"], row["supplier_id"]) == (venture["contract"], "503711")]
    first = [row for row in rows if row not in second]

    def two_pages(changed_amounts, day):
        def fetch(source, engine):
            if source.key != "awards":
                yield from pages.recorded_pages(source)
                return
            fetched_at = dt.datetime(2026, 10, day, tzinfo=dt.UTC)
            revised = [dict(row, **changed_amounts.get(row["wb_contract_number"], {})) for row in first]
            yield pages.Page("awards", "https://example.org/awards?top=1000&skip=0", {"data": revised}, fetched_at)
            yield pages.Page("awards", "https://example.org/awards?top=1000&skip=1000", {"data": second}, fetched_at)
        return fetch

    with DuckDBEngine.open() as engine:
        from strata.lakehouse import catalog

        catalog.build(engine)
        nightly.run_locally(engine, run_id="first", fetch=two_pages({}, 23))
        nightly.run_locally(engine, run_id="later", fetch=two_pages(
            {"1903781": {"supplier_contract_amount_usd": 1300000.0}}, 24))

        kept = engine.run("SELECT count(*) FROM strata.bronze.api_pages WHERE source = 'awards'").rows
        contract = engine.run("SELECT contract_amount_usd, supplier_count, joint_venture FROM strata.gold.contract "
                              "WHERE wb_contract_number = :number", {"number": venture["contract"]}).rows
        members = engine.run("SELECT supplier_id FROM strata.gold.contract_supplier WHERE wb_contract_number = :number "
                             "ORDER BY supplier_id", {"number": venture["contract"]}).rows

    assert kept == ((3,),)  # the first page twice, the second once
    share = decimal.Decimal(str(venture["amount_per_member_usd"]))
    assert contract == ((share * 2, 2, True),)  # US$1,395,944.66, counted once
    assert [supplier for (supplier,) in members] == venture["supplier_ids"]


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


def test_the_awards_fetch_asks_finances_one_for_every_country_page_by_page_until_the_rows_run_out():
    rows = recorded("api/awards/P156634.json")["data"]
    api = FakeAPI("data", rows, "count")

    fetched = list(pages.live_pages(source("awards", page_size=100), api))

    assert [len(page.body["data"]) for page in fetched] == [100, 100, 80]
    assert api.asked[0] == ("https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS00005"
                            "&resourceId=RS00005&type=json&top=100&skip=0")
    assert [parse_qs(urlparse(url).query)["skip"] for url in api.asked] == [["0"], ["100"], ["200"]]
    assert {page.country_code for page in fetched} == {None}  # no country filter, so no one country


def test_the_notices_fetch_stops_at_the_first_page_older_than_what_bronze_holds():
    rows = sorted(recorded("api/notices/P156634.json")["procnotices"], key=lambda row: row["submission_date"],
                  reverse=True)
    api = FakeAPI("procnotices", rows, "total")
    held = dt.date.fromisoformat(rows[150]["submission_date"][:10])  # bronze holds notices up to the 151st newest

    fetched = list(pages.live_pages(source("notices", page_size=100), api, newest_held=lambda country: held))

    assert len(fetched) == 2  # the second page reaches back past it, so the 399 notices take two pages, not four
    assert "project_ctry_name" not in api.asked[0] and "srt=submission_date&order=desc" in api.asked[0]


class FakeIndicators:
    """Serves a recorded Indicators API response a page at a time, as [about the page, records]."""

    def __init__(self, response):
        self.meta, self.rows, self.asked = response[0], response[1], []

    def __call__(self, url):
        self.asked.append(url)
        query = parse_qs(urlparse(url).query)
        size, number = int(query["per_page"][0]), int(query["page"][0])
        pages_in_all = -(-len(self.rows) // size)
        meta = dict(self.meta, page=number, pages=pages_in_all, per_page=size, total=len(self.rows))
        return json.dumps([meta, self.rows[(number - 1) * size:number * size] or None])


def test_an_indicators_source_asks_for_each_indicator_page_by_page():
    api = FakeIndicators(recorded("api/indicators/wgi-ge-KEN-IND.json"))  # 54 rows
    wgi = source("wgi", page_size=20, indicators=("GOV_WGI_GE.EST", "GOV_WGI_CC.EST"))

    fetched = list(pages.live_pages(wgi, api))

    assert [len(pages.records(wgi, page.body)) for page in fetched] == [20, 20, 14, 20, 20, 14]
    assert api.asked[0] == ("https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_GE.EST?format=json&source=3"
                            "&page=1&per_page=20")
    assert "indicator/GOV_WGI_CC.EST?" in api.asked[3]
    assert {pages.reported_total(wgi, page.body) for page in fetched} == {54}
    assert {pages.newest_record(wgi, page.body) for page in fetched} == {dt.date(2026, 9, 25)}  # its lastupdated


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

    contact = next(row for row in rows if row["id"] == AWKWARD["contact_details"]["notice"])
    kept = [field for field in ("contact_email", "contact_name") if contact[field] and contact[field] in body]
    assert contact["contact_email"] and contact["contact_name"] and kept == []  # never prints the details
    assert notice == ((dt.date(2026, 10, 13), dt.date(2026, 10, 1)),)


class FakeCountries:
    """Serves each country's notices a page at a time, newest first, as the search API pages them."""

    def __init__(self, by_country):
        self.by_country, self.asked = by_country, []

    def __call__(self, url):
        self.asked.append(url)
        query = parse_qs(urlparse(url).query)
        rows = self.by_country[query["project_ctry_name"][0]]
        size, offset = int(query["rows"][0]), int(query["os"][0])
        return json.dumps({"total": str(len(rows)), "procnotices": rows[offset:offset + size]}).encode()


def notices_only(notices, stop_after=None):
    """The nightly job's live fetch for the notices source alone, as the given source entry; every
    other source returns nothing. With stop_after, the API stops answering after that many pages."""
    def fetch(source, engine):
        if source.key != "notices":
            return iter(())
        fetched = nightly.fetch_live(notices, engine)
        if stop_after is None:
            return fetched
        return (page if number < stop_after else _stop() for number, page in enumerate(fetched))
    return fetch


def _stop():
    raise OSError("The API stopped answering.")


def test_a_country_added_to_the_slice_is_fetched_in_full_though_bronze_holds_newer_records_of_another(
        monkeypatch):
    """A source fetched for the slice countries keeps a watermark per country. Bronze holds Kenya's
    newest notices, and every notice of the added country is older than those, so a source-wide
    watermark would stop its first fetch after one page. The search API stands in for any source
    fetched country by country."""
    rows = sorted(recorded("api/notices/P156634.json")["procnotices"], key=lambda row: row["submission_date"],
                  reverse=True)
    kenya, added = config.Country("Kenya", "KE", "KEN"), config.Country("Uganda", "UG", "UGA")
    by_country = {"scope": "slice countries", "country_filter": "project_ctry_name={name}"}
    api = FakeCountries({"Kenya": rows[:200], "Uganda": rows[200:]})
    monkeypatch.setattr("strata.fixture.record.fetch_url", api)

    with DuckDBEngine.open() as engine:
        from strata.lakehouse import catalog

        catalog.build(engine)
        nightly.run_task(engine, "fetch_by_watermark", "first",
                         notices_only(source("notices", countries=(kenya,), **by_country)))
        api.asked.clear()
        fetched = list(nightly.fetch_live(source("notices", page_size=50, countries=(kenya, added), **by_country),
                                          engine))

    uganda = [page for page in fetched if "project_ctry_name=Uganda" in page.request]
    assert [len(page.body["procnotices"]) for page in uganda] == [50, 50, 50, 49]
    assert {page.country_code for page in uganda} == {"UG"}


def test_a_source_fetched_for_every_country_keeps_one_watermark(monkeypatch):
    """With no country filter, the newest notice bronze holds from the last fetch is the watermark,
    so a second fetch stops at the first page older than it."""
    rows = sorted(recorded("api/notices/P156634.json")["procnotices"], key=lambda row: row["submission_date"],
                  reverse=True)
    api = FakeAPI("procnotices", rows, "total")
    monkeypatch.setattr("strata.fixture.record.fetch_url", lambda url: api(url).encode())

    with DuckDBEngine.open() as engine:
        from strata.lakehouse import catalog

        catalog.build(engine)
        nightly.run_task(engine, "fetch_by_watermark", "first", notices_only(source("notices", page_size=100)))
        api.asked.clear()
        again = list(nightly.fetch_live(source("notices", page_size=100), engine))

    assert len(again) == 1  # the newest page already reaches back to the newest notice held


def test_a_fetch_that_failed_partway_sets_no_watermark_so_the_next_run_fetches_what_it_missed(monkeypatch):
    """Bronze keeps the newest pages of a fetch that failed partway. Their records are newer than the
    ones the fetch never reached, so a watermark taken from them would stop the next fetch before it
    reached those. The watermark counts only the pages of fetches that finished."""
    rows = sorted(recorded("api/notices/P156634.json")["procnotices"], key=lambda row: row["submission_date"],
                  reverse=True)
    api = FakeAPI("procnotices", rows, "total")
    monkeypatch.setattr("strata.fixture.record.fetch_url", lambda url: api(url).encode())
    notices = source("notices", page_size=100)

    with DuckDBEngine.open() as engine:
        from strata.lakehouse import catalog

        catalog.build(engine)
        with pytest.raises(OSError):
            nightly.run_task(engine, "fetch_by_watermark", "cut short", notices_only(notices, stop_after=2))
        held = engine.run("SELECT count(*) FROM strata.bronze.api_pages").rows[0][0]
        again = list(nightly.fetch_live(notices, engine))

    assert held == 2
    assert [len(page.body["procnotices"]) for page in again] == [100, 100, 100, 99]  # all 399, from the top


def test_the_nightly_job_fetches_a_frozen_source_only_while_bronze_holds_none_of_its_pages():
    """The FY2001 to FY2016 awards have not changed since March 2022 (cadence frozen), so once bronze
    holds them the job does not ask Finances One for its 147 pages again."""
    from strata.lakehouse import catalog

    asked = []

    def fetch(source, engine):
        asked.append(source.key)
        return pages.recorded_pages(source) if source.cadence == "frozen" else iter(())

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        nightly.run_task(engine, "fetch_by_watermark", "first", fetch)
        first, asked[:] = list(asked), []
        nightly.run_task(engine, "fetch_by_watermark", "second", fetch)

    assert "awards_fy2001_2016" in first
    assert "awards_fy2001_2016" not in asked and "awards" in asked
