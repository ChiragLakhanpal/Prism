"""Every structured source, for every country, through the lakehouse run (seam 1, ticket 17).

The gate builds data/out/fixture.duckdb with the nightly job's own tasks over the recorded pages
(gates/build_fixture.py), so most tests here read the tables that run wrote. A test that needs a
page the fixture does not hold, such as an indicator revised in place, writes that page by hand
from a recorded one and runs the same tasks on an empty database.

Expected values come from tests/ground_truth/values.toml, where each names its recorded record,
or from the recorded files read directly, never from the code under test.
"""

import copy
import dataclasses
import datetime as dt
import decimal
import json
import re
import tomllib
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from strata import config
from strata.lakehouse import bronze, catalog, gold, pages, silver, storage
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded"
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}


@pytest.fixture(scope="module")
def db(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql, **params):
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def recorded(file):
    return json.loads((RECORDED / file).read_text())["response"]


def run_one(engine, key, body, fetched_at, request="https://example.org/page?top=1000&skip=0"):
    """One page of one source through bronze and silver, as the nightly job's tasks take it."""
    source = config.load_sources()[key]
    bronze.store(engine, source, [pages.Page(key, request, body, fetched_at)])
    silver.run(engine, source)
    return source


# ── Old method names ─────────────────────────────────────────────────────

# The names used before the July 2016 Procurement Regulations, and what each is now with the
# market approach it implies in STEP's words. ICB, NCB and Direct Contracting are the spec's
# examples (user story 33); a plain Shopping names no market approach.
OLD_NAMES = {
    "International Competitive Bidding": ("Request for Bids", "Open - International"),
    "National Competitive Bidding": ("Request for Bids", "Open - National"),
    "Limited International Bidding": ("Request for Bids", "Limited - International"),
    "Shopping": ("Request for Quotations", None),
    "Direct Contracting": ("Direct Selection", "Direct"),
}
OLD_AWARDS = ("api/awards/P124109-fy2001-2016.json", "api/awards/P130164-fy2001-2016.json")


def test_old_awards_reach_gold_with_the_current_method_name_and_keep_the_dataset_s_words(db):
    written = {row["contract_number"]: row["procurement_method"]
               for file in OLD_AWARDS for row in recorded(file)["data"] if row["procurement_method"] in OLD_NAMES}
    assert {"International Competitive Bidding", "National Competitive Bidding", "Shopping",
            "Limited International Bidding"} <= set(written.values())  # the fixture holds each of these

    stored = {row["wb_contract_number"]: row for row in rows(
        db, "SELECT wb_contract_number, procurement_method, procurement_method_as_written, market_approach, source, "
            "public_from FROM strata.gold.contract WHERE source = 'awards_fy2001_2016'")}

    for number, words in written.items():
        row = stored[number]
        assert (row["procurement_method"], row["market_approach"]) == OLD_NAMES[words], number
        assert row["procurement_method_as_written"] == words
        assert row["public_from"] is not None


def test_an_old_award_written_as_direct_contracting_is_stored_as_direct_selection():
    """The FY2001 to FY2016 dataset writes no award as Direct Contracting: on October 23, 2026 a
    search for it found 0 of its 146,802 rows, which write direct awards as Direct Selection. So this
    page is a recorded P124109 row with only its method changed to the old name."""
    record = dict(recorded("api/awards/P124109-fy2001-2016.json")["data"][0], procurement_method="Direct Contracting")

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_one(engine, "awards_fy2001_2016", {"count": 1, "data": [record]}, dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        gold.build(engine)
        stored = rows(engine, "SELECT procurement_method, procurement_method_as_written, market_approach "
                              "FROM strata.gold.contract")

    assert stored == [{"procurement_method": "Direct Selection", "procurement_method_as_written": "Direct Contracting",
                       "market_approach": "Direct"}]


# A personal title followed by a name, as the FY2001 to FY2016 dataset writes a consultant hired in
# person into a contract's description: "the Consultancy Services of Dr. ..." or, in capitals,
# "CONSULTANCY SERVICES OF DR ...".
TITLED = re.compile(r"\b(?:(?:Mr|Mrs|Ms|Miss|Dr|Capt|Eng|Prof)\.?|MR|MRS|DR|CAPT|PROF)\s+[A-Z]")


def test_an_old_award_to_a_person_reaches_silver_and_gold_with_no_name_and_no_description(db):
    """The spec: individual consultants are never named (user stories 59 and 115). The FY2001 to
    FY2016 dataset names people as suppliers under Individual Consultant Selection and under
    Consultant Qualification Selection, and in contract descriptions. The names are read from the
    recorded files here, so no test file holds them."""
    people = [row for file in OLD_AWARDS for row in recorded(file)["data"]
              if row["procurement_category"] == "Consultant Services"
              and (row["procurement_method"] == "Individual Consultant Selection"
                   or TITLED.search(row["contract_description"] or ""))]
    # INDIVIDUAL CONSULTANT is the label, not a person, and other contracts' descriptions use it.
    names = {row["supplier"] for row in people if row["supplier"] and row["supplier"] != "INDIVIDUAL CONSULTANT"}
    assert len(people) >= 5 and names  # the fixture holds such rows, and they name people

    numbers = sorted({row["contract_number"] for row in people})
    in_silver = rows(db, "SELECT contract_number, supplier, contract_description, individual_consultant "
                         "FROM strata.silver.awards_fy2001_2016 WHERE list_contains(:numbers, contract_number)",
                     numbers=numbers)
    in_gold = rows(db, "SELECT wb_contract_number, supplier_id, contract_description FROM strata.gold.contract "
                       "WHERE list_contains(:numbers, wb_contract_number)", numbers=numbers)
    assert sorted({row["contract_number"] for row in in_silver}) == numbers
    assert all((row["supplier"], row["contract_description"], row["individual_consultant"]) == (None, None, True)
               for row in in_silver)
    assert sorted(row["wb_contract_number"] for row in in_gold) == numbers
    assert all((row["supplier_id"], row["contract_description"]) == (None, None) for row in in_gold)

    for table in ("strata.silver.awards_fy2001_2016", "strata.gold.contract"):
        held = db.run(f"SELECT * FROM {table}").rows
        text = [value for row in held for value in row if isinstance(value, str)]
        named = sum(any(name in value for value in text) for name in names)
        assert named == 0, f"{table} names {named} of the people the recorded rows name"  # never prints them


# A row that names a person, in each place and form the review found: a title with its period, in
# either case, a title in capitals without one, a supplier written with a title, and initials or a
# surname, such as S.A. or SA, that a firm could use as its legal form, at the start or the end of the
# name. A description that names a person comes with that person as the supplier, written without a
# title, so the row names no firm or is that person. The names are made up.
NAMED = [{"contract_description": "Hiring the Consultancy Services of Dr. Jane Doe as Social Specialist",
          "supplier": "JANE DOE"},
         {"contract_description": "INDIVIDUAL CONSULTANCY SERVICES OF MR. JOHN DOE, M&E SPECIALIST",
          "supplier": "JOHN DOE"},
         {"contract_description": "CONSULTANCY SERVICES OF DR JOHN DOE", "supplier": "JOHN DOE"},
         {"supplier": "MR. JOHN DOE"},
         {"supplier": "DR. S.A. DOE"},
         {"contract_description": "CONSULTANCY SERVICES OF DR. B.V. DOE", "supplier": "B.V. DOE"},
         {"supplier": "MRS. JANE SA"},
         {"contract_description": "CONSULTANCY SERVICES OF DR. S.A. DOE", "supplier": "DOE, S.A."}]


@pytest.mark.parametrize("named", NAMED, ids=lambda named: next(iter(named.values())))
def test_an_award_since_fy2020_that_names_a_person_keeps_no_description_and_no_name(named):
    """The awards since FY2020 write INDIVIDUAL CONSULTANT for a person, but a description or the
    supplier field could still name one. No recorded row does, so this page is a recorded P156634
    Consultant Services row with one field changed. The contract keeps its supplier ID, as an
    individual consultant does, and no table keeps the description or the name."""
    record = next(row for row in recorded("api/awards/P156634.json")["data"]
                  if row["procurement_category"] == "Consultant Services")

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_one(engine, "awards", {"count": 1, "data": [dict(record, **named)]}, dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        gold.build(engine)
        silver_row = rows(engine, "SELECT contract_description, supplier, supplier_id, individual_consultant "
                                  "FROM strata.silver.awards")
        gold_row = rows(engine, "SELECT contract_description, supplier_id FROM strata.gold.contract")
        supplier = rows(engine, "SELECT supplier_id, name, kind FROM strata.gold.supplier")

    assert silver_row == [{"contract_description": None, "supplier": None, "supplier_id": record["supplier_id"],
                           "individual_consultant": True}]
    assert gold_row == [{"contract_description": None, "supplier_id": record["supplier_id"]}]
    assert supplier == [{"supplier_id": record["supplier_id"], "name": None, "kind": "individual consultant"}]


@pytest.mark.parametrize("named", NAMED[2:], ids=lambda named: next(iter(named.values())))
def test_an_old_award_that_names_a_person_in_capitals_or_as_its_supplier_keeps_no_description_and_no_name(named):
    """The FY2001 to FY2016 dataset often writes in capitals, and a supplier field can give a title.
    The page is a recorded P124109 Consultant Services row with a firm as its supplier, with one
    field changed."""
    record = next(row for row in recorded(OLD_AWARDS[0])["data"]
                  if row["procurement_category"] == "Consultant Services" and row["supplier"]
                  and row["procurement_method"] != "Individual Consultant Selection"
                  and not TITLED.search(row["contract_description"] or ""))

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_one(engine, "awards_fy2001_2016", {"count": 1, "data": [dict(record, **named)]},
                dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        gold.build(engine)
        silver_row = rows(engine, "SELECT contract_description, supplier, individual_consultant "
                                  "FROM strata.silver.awards_fy2001_2016")
        gold_row = rows(engine, "SELECT contract_description FROM strata.gold.contract")

    assert silver_row == [{"contract_description": None, "supplier": None, "individual_consultant": True}]
    assert gold_row == [{"contract_description": None}]


# Rows that name a firm or a country, not a person, as the review found them, each with whether the
# row keeps its description. A firm's name can start with a title, DR can stand for the Democratic
# Republic of the Congo, and a firm can be hired for a person's services, with its legal form written
# out, as S.A. at the end of its name, or not at all, and with its name in the description too. The
# first two firms are public company names, and the person and the other three firms are made up.
FIRMS = [({"supplier": "DR. REDDY'S LABORATORIES LTD"}, True),
         ({"supplier": "DR. SAUER & PARTNERS"}, True),
         ({"contract_description": "Trade corridor study for Rwanda and DR Congo"}, True),
         ({"contract_description": "TRADE CORRIDOR STUDY FOR RWANDA AND DR CONGO"}, True),
         ({"contract_description": "Services of Dr. Jane Doe", "supplier": "ABC CONSULTING LTD"}, False),
         ({"contract_description": "Services of Dr. Jane Doe", "supplier": "ABC INGENIERIA S.A."}, False),
         ({"contract_description": "Services of Dr. Jane Doe", "supplier": "ABC ENTERPRISES"}, False),
         ({"contract_description": "Services of Dr. Jane Doe through ABC Consulting Ltd",
           "supplier": "ABC CONSULTING LTD"}, False)]


@pytest.mark.parametrize(("named", "keeps_description"), FIRMS, ids=lambda case: str(case))
def test_an_award_since_fy2020_that_names_a_firm_or_a_country_keeps_the_firm_s_name(named, keeps_description):
    """A personal title alone does not make a supplier a person: the firm keeps its name in silver
    and in gold.supplier, and a description loses only a person's name. The page is a recorded
    P156634 Consultant Services row with a firm as its supplier, with the fields changed."""
    record = dict(next(row for row in recorded("api/awards/P156634.json")["data"]
                       if row["procurement_category"] == "Consultant Services"
                       and row["supplier"].upper() != "INDIVIDUAL CONSULTANT"), **named)

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_one(engine, "awards", {"count": 1, "data": [record]}, dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        gold.build(engine)
        silver_row = rows(engine, "SELECT contract_description, supplier, individual_consultant FROM strata.silver.awards")
        supplier = rows(engine, "SELECT supplier_id, name, kind FROM strata.gold.supplier")

    assert silver_row == [{"contract_description": record["contract_description"] if keeps_description else None,
                           "supplier": record["supplier"], "individual_consultant": False}]
    assert supplier == [{"supplier_id": record["supplier_id"], "name": record["supplier"], "kind": "firm"}]


@pytest.mark.parametrize(("named", "keeps_description"), FIRMS, ids=lambda case: str(case))
def test_an_old_award_that_names_a_firm_or_a_country_keeps_the_firm_s_name(named, keeps_description):
    """The same rows in the FY2001 to FY2016 dataset, from a recorded P124109 Consultant Services
    row with a firm as its supplier."""
    record = dict(next(row for row in recorded(OLD_AWARDS[0])["data"]
                       if row["procurement_category"] == "Consultant Services" and row["supplier"]
                       and row["procurement_method"] != "Individual Consultant Selection"
                       and not TITLED.search(row["contract_description"] or "")), **named)

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_one(engine, "awards_fy2001_2016", {"count": 1, "data": [record]}, dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        gold.build(engine)
        silver_row = rows(engine, "SELECT contract_description, supplier, individual_consultant "
                                  "FROM strata.silver.awards_fy2001_2016")
        gold_row = rows(engine, "SELECT contract_description FROM strata.gold.contract")

    def one_line(written):  # silver keeps text on one line, as the dataset breaks long fields
        return " ".join(written.split())

    description = one_line(record["contract_description"]) if keeps_description else None
    assert silver_row == [{"contract_description": description, "supplier": one_line(record["supplier"]),
                           "individual_consultant": False}]
    assert gold_row == [{"contract_description": description}]


# ── FY2017 to FY2019, from award notices ─────────────────────────────────

GAP = TRUTH["counts"]["gap_years"]


def test_fy2017_to_fy2019_have_contracts_from_award_notices_labeled_as_local_currency(db):
    stored = rows(db, "SELECT contract_id, fiscal_year, award_notice_id, amount_basis, contract_amount_usd, "
                      "contract_currency, public_from FROM strata.gold.contract WHERE source = 'notices'")

    by_year = {f"fy{year}": sorted(row["contract_id"] for row in stored if row["fiscal_year"] == year)
               for year in (2017, 2018, 2019)}
    assert by_year == {key: sorted(GAP[key]) for key in ("fy2017", "fy2018", "fy2019")}
    assert len(stored) == sum(len(GAP[key]) for key in ("fy2017", "fy2018", "fy2019"))  # no other year
    assert {row["amount_basis"] for row in stored} == {"local currency, from award notices"}  # none in USD
    assert {row["contract_amount_usd"] for row in stored} == {None}  # never converted
    assert all(row["award_notice_id"] == row["contract_id"] and row["public_from"] for row in stored)


def test_a_contract_from_an_award_notice_keeps_the_price_in_the_currency_the_notice_names(db):
    # values.toml: award-7431-signed. OP00044090 signed IN-RRSMP-7431-CW-RFB on June 15, 2017.
    notice = [row for row in recorded("api/notices/P130164.json")["procnotices"] if row["id"] == GAP["in_inr"]][0]
    assert f"INR {GAP['in_inr_price']}" in notice["notice_text"]

    contract = rows(db, "SELECT step_reference, contract_signing_date, contract_amount, contract_currency "
                        "FROM strata.gold.contract WHERE contract_id = :notice", notice=GAP["in_inr"])
    assert contract == [{"step_reference": "IN-RRSMP-7431-CW-RFB", "contract_signing_date": dt.date(2017, 6, 15),
                         "contract_amount": decimal.Decimal(GAP["in_inr_price"].replace(",", "")),
                         "contract_currency": "INR"}]


def test_a_gap_year_notice_priced_in_us_dollars_is_labeled_so_and_one_that_repeats_an_award_is_left_out():
    """Two pages written from recorded ones. OP00044090 (values.toml, award-7431-signed) priced in US
    dollars instead of rupees is labeled US dollars from award notices. And a prior-review award
    signed on June 15, 2016 under a STEP reference, whose award notice came out on August 2, 2016
    with no signature date, falls in FY2016 by its signing and FY2017 by its notice: it is one
    contract, from the awards dataset, not two."""
    notice = next(row for row in recorded("api/notices/P130164.json")["procnotices"] if row["id"] == GAP["in_inr"])
    in_dollars = dict(notice, notice_text=notice["notice_text"].replace("INR ", "USD "))
    late = dict(notice, id="OP00000017", noticedate="02-Aug-2016", submission_date="2016-08-02T00:00:00Z",
                bid_reference_no="KE-KURA-000017-CW-RFB",
                notice_text=notice["notice_text"].replace("Contract Signature Date", "Contract Date"))
    award = dict(recorded("api/awards/P124109-fy2001-2016.json")["data"][0], contract_number="1000017",
                 borrower_contract_reference_number="KE-KURA-000017-CW-RFB", contract_signing_date="15-Jun-2016")

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_one(engine, "notices", {"total": "2", "procnotices": [in_dollars, late]},
                dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        run_one(engine, "awards_fy2001_2016", {"count": 1, "data": [award]}, dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        gold.build(engine)
        stored = rows(engine, "SELECT contract_id, source, fiscal_year, contract_currency, amount_basis "
                              "FROM strata.gold.contract ORDER BY contract_id")

    assert stored == [
        {"contract_id": "1000017", "source": "awards_fy2001_2016", "fiscal_year": 2016, "contract_currency": "USD",
         "amount_basis": "US dollars"},
        {"contract_id": GAP["in_inr"], "source": "notices", "fiscal_year": 2017, "contract_currency": "USD",
         "amount_basis": "US dollars, from award notices"},
    ]


# ── Loans and credits: the closing-date history ──────────────────────────

def test_p156634_s_closing_date_history_shows_three_moves_since_2022_as_the_loan_history_records(db):
    history = rows(db, "SELECT closing_date, previous_closing_date, reported_on, public_from "
                       "FROM strata.gold.project_closing_date WHERE project_id = 'P156634' ORDER BY reported_on")
    moves = [row for row in history if row["previous_closing_date"] is not None
             and row["reported_on"] >= dt.date(2022, 1, 1)]

    expected = [VALUES[f"closing-p156634-move-{n}"] for n in (1, 2, 3)]
    reported = [dt.datetime.strptime(value["at"].split("end_of_period=")[1].split("]")[0], "%d-%b-%Y").date()
                for value in expected]
    assert [(row["closing_date"], row["reported_on"]) for row in moves] == [
        (value["value"], day) for value, day in zip(expected, reported, strict=True)]
    assert moves[0]["previous_closing_date"] == VALUES["closing-p156634-original"]["value"]
    assert all(row["public_from"] == row["reported_on"] for row in moves)


def test_each_loan_reaches_gold_from_its_newest_snapshot_with_its_amounts(db):
    # values.toml: ibrd-loan-p164704, and the IDA credits of the two recorded projects.
    snapshot = recorded("api/loans/P164704-ibrd.json")["data"][0]
    loan = rows(db, "SELECT lender, project_id, country_code, closing_date, disbursed_usd, as_of, public_from "
                    "FROM strata.gold.loan WHERE loan_number = :loan", loan=VALUES["ibrd-loan-p164704"]["value"])

    assert loan == [{"lender": "IBRD", "project_id": "P164704", "country_code": "PK",
                     "closing_date": dt.date(2026, 6, 30), "disbursed_usd": decimal.Decimal("38860301.17"),
                     "as_of": dt.date(2026, 9, 30), "public_from": dt.date(2026, 9, 30)}]
    assert snapshot["disbursed_amount"] == 38860301.17
    credits = {row["loan_number"] for row in rows(db, "SELECT loan_number FROM strata.gold.loan WHERE lender = 'IDA'")}
    assert credits == {row["credit_number"] for row in recorded("api/credits/P156634-P130164.json")["data"]}


# ── IEG ratings and ISR ratings ──────────────────────────────────────────

def test_an_ieg_rating_reaches_gold_public_from_the_end_of_its_evaluation_year(db):
    # values.toml: ieg-outcome-p130164. IEG's ICR Review of P130164 was evaluated in FY2020.
    rating = rows(db, "SELECT outcome, evaluation_type, evaluation_fy, public_from FROM strata.gold.ieg_rating "
                      "WHERE project_id = 'P130164'")

    assert rating == [{"outcome": VALUES["ieg-outcome-p130164"]["value"], "evaluation_type": "ICRR",
                       "evaluation_fy": 2020, "public_from": dt.date(2020, 6, 30)}]


def test_the_projects_api_s_duplicate_isr_ratings_are_kept_once(db):
    listed = recorded("api/projects/P156634.json")["projects"]["P156634"]["isr_ratings"]
    distinct = {(row["code"], row["isr_date"], row["value"]) for row in listed}
    assert len(listed) == 2 * len(distinct)  # the API lists each of P156634's ratings twice

    stored = rows(db, "SELECT rating_code, isr_date, value, public_from FROM strata.gold.project_isr_rating "
                      "WHERE project_id = 'P156634'")
    assert sorted((row["rating_code"], row["isr_date"].isoformat(), row["value"]) for row in stored) == sorted(distinct)
    procurement = [row for row in stored if row["rating_code"] == "27"]
    assert [row["value"] for row in procurement] == [VALUES["isr-procurement-p156634"]["value"]]
    assert {row["public_from"] for row in stored} == {dt.date(2026, 6, 30)}


# ── Governance indicators, each published version kept ───────────────────

def revised(response, country, year, value, lastupdated):
    """The recorded Indicators API page again, as if the API had revised one value in place."""
    body = copy.deepcopy(response)
    body[0]["lastupdated"] = lastupdated
    for row in body[1]:
        if (row["country"]["id"], row["date"]) == (country, year):
            row["value"] = value
    return body


def test_an_indicator_revised_in_place_keeps_both_versions_and_a_join_between_them_takes_the_earlier():
    """The Indicators API overwrites a revised value and gives the page a new lastupdated date. This
    is the recorded WGI page for government effectiveness (lastupdated September 25, 2026), then the
    same page with Kenya's 2025 estimate, the latest year, revised on February 15, 2027, a version the API has not
    published: the fixture can record only what the API serves today."""
    from strata.lakehouse import governance

    first = recorded("api/indicators/wgi-ge-KEN-IND.json")
    earlier = [row["value"] for row in first[1] if (row["country"]["id"], row["date"]) == ("KE", "2025")][0]
    later = revised(first, "KE", "2025", -0.5, "2027-02-15")
    url = "https://api.worldbank.org/v2/country/KEN;IND/indicator/GOV_WGI_GE.EST?format=json&per_page=500&source=3"

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_one(engine, "wgi", first, dt.datetime(2026, 10, 23, tzinfo=dt.UTC), url)
        run_one(engine, "wgi", later, dt.datetime(2027, 2, 16, tzinfo=dt.UTC), url)
        gold.build(engine)
        versions = rows(engine, "SELECT value, public_from, superseded_on FROM strata.gold.governance_score "
                                "WHERE country_code = 'KE' AND indicator_id = 'GOV_WGI_GE.EST' AND year = 2025 "
                                "ORDER BY public_from")
        unchanged = rows(engine, "SELECT count(*) AS versions FROM strata.gold.governance_score "
                                 "WHERE country_code = 'IN' AND indicator_id = 'GOV_WGI_GE.EST' AND year = 2025")
        between = governance.score_as_of(engine, "KE", "GOV_WGI_GE.EST", dt.date(2026, 12, 1))
        after = governance.score_as_of(engine, "KE", "GOV_WGI_GE.EST", dt.date(2027, 3, 1))
        before = governance.score_as_of(engine, "KE", "GOV_WGI_GE.EST", dt.date(2026, 9, 1))

    assert [(row["value"], row["public_from"], row["superseded_on"]) for row in versions] == [
        (earlier, dt.date(2026, 9, 25), dt.date(2027, 2, 15)), (-0.5, dt.date(2027, 2, 15), None)]
    assert unchanged == [{"versions": 1}]
    assert (between["year"], between["value"]) == (2025, earlier)
    assert (after["year"], after["value"]) == (2025, -0.5)
    assert before is None  # nothing from this page was public before its lastupdated date


def test_cpia_and_wgi_reach_gold_for_each_country_and_year_with_a_value(db):
    """CPIA covers IDA countries only: India has values only for the years it borrowed from IDA."""
    for file, indicator in (("api/indicators/cpia-irai-KEN-IND.json", "IQ.CPA.IRAI.XQ"),
                            ("api/indicators/wgi-cc-KEN-IND.json", "GOV_WGI_CC.EST")):
        response = recorded(file)
        with_values = {(row["country"]["id"], int(row["date"])) for row in response[1] if row["value"] is not None}
        stored = rows(db, "SELECT country_code, year, public_from FROM strata.gold.governance_score "
                          "WHERE indicator_id = :indicator", indicator=indicator)
        assert {(row["country_code"], row["year"]) for row in stored} == with_values
        assert {row["public_from"] for row in stored} == {dt.date.fromisoformat(response[0]["lastupdated"])}


# ── One sector taxonomy ──────────────────────────────────────────────────

SLICE_FILE = "api/projects/kenya-fy2012-2025.json"


def test_every_slice_project_maps_to_one_sector_and_every_listed_code_is_mapped(db):
    """The projects API lists major sectors from two taxonomies: single-letter codes, many named
    FY17 - ..., some (Historic), and the newer double-letter codes such as WWX and TTX. Every Kenya
    project approved FY2012 to FY2025 that lists a major sector maps to exactly one sector."""
    sectors = config.load_sectors()
    projects = recorded(SLICE_FILE)["projects"]
    listed = {pid: project for pid, project in projects.items() if project.get("major_sectors")}
    codes = {sector["major_sector"]["major_sector_code"] for project in listed.values()
             for sector in project["major_sectors"]}
    assert any(len(code) == 3 for code in codes) and any(len(code) == 2 for code in codes)  # both taxonomies

    stored = {row["project_id"]: row for row in rows(db, "SELECT project_id, sector, sector_name, major_sector_code "
                                                         "FROM strata.gold.project WHERE country_code = 'KE'")}
    assert {pid for pid in listed} <= set(stored)
    assert all(stored[pid]["sector"] in sectors.keys for pid in listed)
    assert all(stored[pid]["sector_name"] == sectors.names[stored[pid]["sector"]] for pid in listed)
    slice_projects = [pid for pid in listed if stored[pid]["sector"] in config.load_slice().sectors]
    assert slice_projects and "P156634" in slice_projects
    assert stored["P156634"]["sector"] == "water"


def test_the_sector_file_maps_every_code_the_slice_countries_projects_list():
    """The fixture records Kenya's projects only. values.toml lists every major sector code the
    projects API gave for the four slice countries' projects, so none of their projects is left
    without a sector for want of a mapped code."""
    listed = TRUTH["sectors"]["slice_countries"]["codes"]

    assert [code for code in listed if code not in config.load_sectors().codes] == []


def test_a_passage_takes_its_project_s_one_sector_so_search_and_the_slice_agree(db):
    """The two taxonomies map to one, so the passage reader takes each project's sector from
    strata.gold.project rather than reading the sector codes again. A project's first sector code
    can belong to another sector than the one its shares give it."""
    from strata.lakehouse import passages

    projects = rows(db, "SELECT project_id, sector FROM strata.gold.project")

    assert projects
    assert [(p["project_id"], passages.project(db, p["project_id"]).slice_sector) for p in projects] == [
        (p["project_id"], p["sector"]) for p in projects]


def test_a_project_maps_to_the_major_sector_with_the_largest_share():
    """A project's sectors each carry a share. A project split 40 to public administration (BX) and
    35 plus 25 to transport (TTX, the newer taxonomy) is transport, and a project that lists no
    sector has none. The older taxonomy splits energy across several codes, so the shares add up
    by sector: a project split 35 to public administration (BX), 20 and 30 to energy (LX and PX)
    and 15 to transport (TX) is energy, from PX, its larger energy code."""
    def major(code, *percents):
        return {"major_sector": {"major_sector_code": code,
                                 "sectors": [{"sector_percent": percent} for percent in percents]}}

    split = dict(id="P000017", project_name="A split project", countrycode="KE",
                 major_sectors=[major("BX", "40.0"), major("TTX", "35.0", "25.0")])
    unlisted = dict(id="P000018", project_name="A project with no sector", countrycode="KE")
    energy = dict(id="P000019", project_name="A project split across energy codes", countrycode="PK",
                  major_sectors=[major("BX", "35.0"), major("LX", "20.0"), major("PX", "30.0"), major("TX", "15.0")])
    body = {"total": "3", "projects": {"P000017": split, "P000018": unlisted, "P000019": energy}}

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        run_one(engine, "projects", body, dt.datetime(2026, 10, 23, tzinfo=dt.UTC))
        gold.sync(engine, "project")
        stored = rows(engine, "SELECT project_id, sector, major_sector_code FROM strata.gold.project "
                              "ORDER BY project_id")

    assert stored == [{"project_id": "P000017", "sector": "transport", "major_sector_code": "TTX"},
                      {"project_id": "P000018", "sector": None, "major_sector_code": None},
                      {"project_id": "P000019", "sector": "energy", "major_sector_code": "PX"}]


# ── Data readiness for every source ──────────────────────────────────────

def reported_totals(dataset):
    """The total each recorded file of a fixture dataset says its request has, read from the file."""
    from strata.fixture import recorded as fmt

    manifest = fmt.load_manifest()
    totals = []
    for entry in manifest.sources:
        if entry.dataset == dataset and entry.kind == "json":
            response = fmt.read(manifest.recorded / entry.file).body
            about = response[0] if isinstance(response, list) else response
            totals.append(int(about.get("count", about.get("total"))))
    return totals


def measures(db, source, subject="all"):
    found = rows(db, "SELECT measure, kind, count, denominator, as_of, detail FROM strata.ops.data_readiness "
                     "WHERE run_id = 'fixture' AND source = :source AND subject = :subject",
                 source=source, subject=subject)
    return {row["measure"]: row for row in found}


PAGED = [key for key, source in config.load_sources().items() if source.paged]


@pytest.mark.parametrize("key", PAGED)
def test_each_source_s_row_count_in_ops_equals_the_total_the_api_reported(db, key):
    """Criterion 1: the rows held for each source, counted once per request, equal the totals the
    recorded responses report, which this test reads from the files themselves."""
    totals = reported_totals(config.load_sources()[key].fixture_dataset)
    coverage = measures(db, key)["coverage_rows"]

    assert totals and (coverage["count"], coverage["denominator"]) == (sum(totals), sum(totals))
    assert coverage["kind"] == "coverage"


def test_rows_held_equal_the_reported_totals_on_a_later_night():
    """Criterion 1 on a later night, for each way the job fetches. The job asks Finances One for every
    page of the awards each night: a day after the recorded fetch, the source has dropped one
    supplier row of P156634 (Kenya), and only the newest page of each request says what it holds now.
    The job asks the search API for notices newest first, and stops at the newest notice it already
    holds: the API held 13 of P130164's notices (India) on the first night and all 14 on the second,
    so the second night asks for the first page only, and the notices pushed onto later pages stay
    on the pages of the first night. P130164's project record comes back unchanged both nights, and
    gives India's code to the notices. On each source, the rows held must equal the reported totals,
    and the workspace check must pass."""
    from strata.lakehouse import ground_truth, nightly

    awards, project = "api/awards/P156634.json", "api/projects/P130164.json"
    newest_first = sorted(recorded("api/notices/P130164.json")["procnotices"],
                          key=lambda notice: notice["submission_date"], reverse=True)
    asked = {23: [], 24: []}

    def search_api(day, held):
        def get(url):  # the search API's answer to rows and os, newest first as the request asks
            query = parse_qs(urlparse(url).query)
            size, offset = int(query["rows"][0]), int(query["os"][0])
            asked[day].append(offset)
            return json.dumps({"rows": size, "os": str(offset), "total": str(len(held)),
                               "procnotices": held[offset:offset + size]}).encode()
        return get

    def fetch(day, notices):
        when = dt.datetime(2026, 10, day, tzinfo=dt.UTC)

        def pages_of(source, engine):
            if source.key == "awards":
                body = recorded(awards)
                if day == 24:
                    body = dict(body, count=body["count"] - 1, data=body["data"][1:])
                return [pages.Page(source.key, json.loads((RECORDED / awards).read_text())["source"], body, when)]
            if source.key == "projects":
                return [pages.Page(source.key, json.loads((RECORDED / project).read_text())["source"],
                                   recorded(project), when)]
            if source.key == "notices":
                # One series: the job asks for each slice country on its own, and one is enough here.
                return pages.live_pages(dataclasses.replace(source, page_size=4, countries=source.countries[:1]),
                                        search_api(day, notices),
                                        lambda country: bronze.newest_held(engine, source, country), clock=lambda: when)
            return []  # the other sources play no part here, and the job runs faster without them
        return pages_of

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        nightly.run_locally(engine, run_id="recorded", fetch=fetch(23, newest_first[1:]))
        nightly.run_locally(engine, run_id="later", fetch=fetch(24, newest_first))

        held = {}
        for source, subject, count, denominator in engine.run(
                "SELECT source, subject, count, denominator FROM strata.ops.data_readiness "
                "WHERE run_id = 'later' AND measure = 'coverage_rows'").rows:
            held.setdefault(source, {})[subject] = (count, denominator)
        check = ground_truth.read(ROOT / "tests" / "ground_truth" / "every_source_holds_the_rows_its_api_reported.sql")
        complete = dict(engine.run(check.sql, check.params).as_text())

    assert asked == {23: [0, 4, 8, 12], 24: [0]}  # every page the first night, the newest the second
    assert held == {
        "awards": {"all": (279, 279), "KE": (279, 279)},  # 280 recorded, one row gone
        "notices": {"all": (14, 14), "IN": (14, 14)},  # 13 the first night, one more the second
        "projects": {"all": (1, 1), "IN": (1, 1)},
    }
    assert complete == {"awards": "true", "notices": "true", "projects": "true"}


NEW_SOURCES = ["awards_fy2001_2016", "ieg_ratings", "ida_credits", "ibrd_loans", "ida_credit_history",
               "ibrd_loan_history", "cpia", "wgi"]


@pytest.mark.parametrize("key", NEW_SOURCES + ["awards", "notices", "projects"])
def test_each_source_has_coverage_linked_and_fresh_measures_for_the_data_readiness_page(db, key):
    found = measures(db, key)
    kinds = {row["kind"] for row in found.values()}

    assert {"coverage", "linked", "fresh"} <= kinds, key
    assert {"fresh_fetched", "fresh_newest_record"} <= set(found), key
    assert all(row["count"] is not None and row["denominator"] for row in found.values() if row["kind"] != "fresh")
    # The day the fixture was recorded. Ticket 18 recorded one project record, P127203's, a day later, and a
    # measure sees only the fetches made before it (review r2 P4).
    assert found["fresh_fetched"]["as_of"] == dt.date(2026, 10, 23)
    assert found["fresh_fetched"]["detail"] == config.load_sources()[key].cadence
    assert all(row["detail"] for row in found.values())


def test_the_projects_measure_counts_the_projects_mapped_to_a_sector(db):
    """The Kenya page lists one project with no major sector, P163538, so 92 of the 93 projects held
    for every country map to a sector: P130164, P127203 (ticket 18's report in French) and the 91 Kenya
    projects, P156634 among them."""
    linked = measures(db, "projects")["linked_sector"]
    unmapped = [pid for pid, project in recorded(SLICE_FILE)["projects"].items() if not project.get("major_sectors")]

    assert unmapped == ["P163538"]
    assert (linked["count"], linked["denominator"]) == (linked["denominator"] - 1, len(
        set(recorded(SLICE_FILE)["projects"]) | {"P130164", "P156634", "P127203"}))


# ── How much room structured data takes ──────────────────────────────────

def test_the_run_measures_and_records_each_table_s_size_and_structured_data_stays_under_half_a_gigabyte(db, fixture_db):
    """Criterion 7, on the fixture: every catalog table's size is recorded in strata.ops.table_sizes,
    the tables of documents' text, passages and vectors are not counted as structured data, and the
    structured total is under the thresholds file's limit and no more than the database file itself."""
    sizes = {row["table_name"]: row for row in rows(
        db, "SELECT table_name, structured, row_count, bytes, public_from FROM strata.ops.table_sizes "
            "WHERE run_id = 'fixture'")}
    defined = {definition.full_name for definition in catalog.table_definitions()}
    limit = config.load_thresholds().value("ingestion.structured_data_limit_bytes")
    structured = sum(row["bytes"] for row in sizes.values() if row["structured"])

    assert defined <= set(sizes)
    assert not any(sizes[name]["structured"] for name in ("strata.bronze.document_pages",
                                                            "strata.bronze.document_texts",
                                                            "strata.bronze.layout_pages",
                                                            "strata.silver.documents",
                                                            "strata.silver.document_page_routes",
                                                            "strata.silver.passages",
                                                            "strata.silver.passage_embeddings",
                                                            "strata.silver.passage_shields",
                                                            "strata.gold.passage"))
    assert all(row["bytes"] > 0 for row in sizes.values() if row["row_count"])
    assert 0 < structured <= fixture_db.stat().st_size and structured < limit == 500_000_000
    assert sizes["strata.gold.contract"]["row_count"] == rows(db, "SELECT count(*) AS n FROM strata.gold.contract")[0]["n"]


# Each paged source's full size: the total its API reported for a request for one record on
# October 23, 2026 (PLAN.md section 3 gives the awards', IEG's and the notices' too). The loan
# histories are the slice's four countries' totals added up, and CPIA and WGI are one indicator's
# total times the registry's number of codes, every country and year with or without a value.
FULL_SCALE = {
    "awards": 295_845, "awards_fy2001_2016": 146_802, "ieg_ratings": 12_629, "ida_credits": 11_486,
    "ibrd_loans": 9_538, "ida_credit_history": 36_305 + 58_526 + 30_378 + 50_349,
    "ibrd_loan_history": 11_582 + 188 + 2_637 + 22_279, "notices": 424_022, "projects": 28_208,
    "cpia": 17_556 * len(config.load_sources()["cpia"].indicators),
    "wgi": 5_832 * len(config.load_sources()["wgi"].indicators),
}


def test_every_paged_source_has_a_full_scale_count():
    assert set(FULL_SCALE) == set(PAGED)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "At full scale, structured data projects to about 1.6 GB: bronze 0.89 GB, silver 0.54 GB and gold "
    "0.15 GB. Bronze alone is over the limit, so the user decides the limit (ticket 17's parked "
    "decision 2). Remove this mark once the projection is under it."))
def test_structured_data_projected_to_every_country_from_the_fixture_stays_under_the_limit(db, tmp_path):
    """Criterion 7 at full scale, projected. Each source's bronze pages and silver rows are written
    as Parquet, the format Delta tables keep, and their bytes per record, less the file's own
    overhead, are multiplied by the source's full size. Gold grows with the records overall. A
    source with few records in the fixture is overstated, since its pages' own fields are shared by
    fewer records. The workspace measures the real size (strata.ops.table_sizes)."""
    written = iter(range(10_000))

    def quoted(path):
        return str(path).replace("'", "\\'")

    def parquet_bytes(query):
        full, empty = tmp_path / f"{next(written)}.parquet", tmp_path / f"{next(written)}.parquet"
        # The folder's path goes into the statement as text, and the gate's scratch lives under the repo
        # (ticket 73), whose path may hold a quote. Databricks SQL escapes a quote with a backslash, and
        # the transpile step writes it the way DuckDB reads it.
        db.run(f"COPY ({query}) TO '{quoted(full)}' (FORMAT parquet)")
        db.run(f"COPY ({query} LIMIT 0) TO '{quoted(empty)}' (FORMAT parquet)")
        return full.stat().st_size - empty.stat().st_size

    projected, layers, records_held = {}, {"bronze": 0.0, "silver": 0.0, "gold": 0.0}, 0
    for key, source in config.load_sources().items():
        if not source.paged:
            continue
        held = rows(db, "SELECT sum(records) AS n FROM strata.bronze.api_pages WHERE source = :source", source=key)[0]["n"]
        pages_of = f"SELECT page_hash FROM strata.bronze.api_pages WHERE source = '{key}'"
        scale = FULL_SCALE[key] / held
        in_bronze = parquet_bytes(f"SELECT * FROM strata.bronze.api_pages WHERE source = '{key}'") * scale
        in_silver = sum(parquet_bytes(f"SELECT * FROM {table} WHERE page_hash IN ({pages_of})")
                        for table in silver.transform(source).TABLES) * scale
        projected[key] = in_bronze + in_silver
        layers["bronze"] += in_bronze
        layers["silver"] += in_silver
        records_held += held
    gold_tables = [definition.full_name for definition in catalog.table_definitions()
                   if definition.full_name.startswith("strata.gold.")
                   and definition.full_name not in storage.DOCUMENT_TABLES]
    projected["gold"] = layers["gold"] = sum(
        parquet_bytes(f"SELECT * FROM {table}") for table in gold_tables) / records_held * sum(FULL_SCALE.values())
    total = sum(projected.values())
    limit = config.load_thresholds().value("ingestion.structured_data_limit_bytes")

    def listed(sizes):
        return ", ".join(f"{key} {size / 1e6:,.0f} MB" for key, size in sorted(sizes.items(), key=lambda item: -item[1]))

    assert total < limit, (f"Structured data projects to {total / 1e9:.2f} GB at full scale. By layer: "
                           f"{listed(layers)}. By source: {listed(projected)}.")


def test_the_workspace_checks_name_every_paged_source_and_the_thresholds_file_s_limit():
    """Rule 4: the registry and the thresholds file say these once, and the ground-truth SQL that the
    workspace check runs must say the same."""
    from strata.lakehouse import ground_truth

    complete = ground_truth.read(ROOT / "tests" / "ground_truth" / "every_source_holds_the_rows_its_api_reported.sql")
    limit = ground_truth.read(ROOT / "tests" / "ground_truth" / "structured_data_under_the_limit.sql")

    assert [source for source, _ in complete.expected[1:]] == sorted(PAGED)
    assert int(limit.params["limit_bytes"]) == config.load_thresholds().value("ingestion.structured_data_limit_bytes")


def test_a_gold_query_that_gives_a_key_two_rows_is_counted():
    from strata.lakehouse import gold
    from strata.lakehouse.engine import DuckDBEngine

    with DuckDBEngine.open() as engine:
        twice = gold.duplicate_keys(engine, "SELECT 1 AS k, 'a' AS v UNION ALL SELECT 1, 'b' UNION ALL SELECT 2, 'c'",
                                    ("k",))
        none = gold.duplicate_keys(engine, "SELECT 1 AS k UNION ALL SELECT 2", ("k",))

    assert (twice, none) == (1, 0)


def test_a_notice_whose_country_name_has_two_codes_gets_one_row_with_its_projects_code():
    # Serbia is RS and YF in strata.gold.country, and the notice's own project is RS (October 24, 2026).
    from strata.lakehouse import catalog, gold
    from strata.lakehouse.engine import DuckDBEngine

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        engine.run("INSERT INTO strata.silver.projects (project_id, country_code, country_name, region, page_hash, "
                   "fetched_at, public_from) VALUES "
                   "('P900001', 'RS', 'Serbia', 'Europe and Central Asia', 'h1', TIMESTAMP '2026-10-24 00:00:00', "
                   "DATE '2019-07-01'), "
                   "('P900002', 'YF', 'Serbia', 'Europe and Central Asia', 'h2', TIMESTAMP '2026-10-24 00:00:00', "
                   "DATE '2019-07-01')")
        engine.run("INSERT INTO strata.silver.notices (notice_id, project_id, project_country, contact_details_removed, "
                   "page_hash, fetched_at, public_from) VALUES ('OP00900001', 'P900001', 'Serbia', false, 'h1', "
                   "TIMESTAMP '2026-10-24 00:00:00', DATE '2026-10-24')")
        for table in ("country", "project", "project_loan", "notice"):
            gold.sync(engine, table)
        serbia = engine.run("SELECT count(*) FROM strata.gold.country WHERE country_name = 'Serbia'").rows[0][0]
        rows = engine.run("SELECT notice_id, country_code FROM strata.gold.notice").rows

    assert serbia == 2
    assert rows == (("OP00900001", "RS"),)
