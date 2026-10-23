"""The lakehouse run over the fixture (seam 1): recorded pages go in, and bronze, silver, gold and
the data readiness measures in strata.ops come out.

The gate builds data/out/fixture.duckdb with the same run the nightly job makes on the workspace
(gates/build_fixture.py), so these tests read the tables the run wrote. Expected values come from
tests/ground_truth/values.toml, where each one names its recorded record, or from the recorded
files themselves, never from the code under test.
"""

import datetime as dt
import decimal
import json
import re
import tomllib
from pathlib import Path

import pytest

from strata.lakehouse import clean, contacts
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}
KENYA = TRUTH["counts"]["kenya"]  # Kenya's rows, counted from the recorded files apart from Strata's code
RECORDED = ROOT / "data" / "fixture" / "recorded"

# The recorded files of the three sources this run ingests, for Kenya.
KENYA_RECORDS = ("api/awards/P156634.json", "api/awards/P176758-P170941.json", "api/notices/P156634.json",
                 "api/notices/kenya-works-open-on-2026-10-09.json", "api/notices/kenya-icb-2015.json",
                 "api/projects/P156634.json")


@pytest.fixture(scope="module")
def gold(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def one(engine, sql, **params):
    result = engine.run(sql, params)
    assert len(result.rows) == 1, f"expected one row, got {len(result.rows)}: {sql}"
    return dict(zip(result.columns, result.rows[0], strict=True))


def record(file):
    return json.loads((RECORDED / file).read_text())["response"]


# The gold tables the ticket names: country, project, package (keyed by STEP reference), notice,
# contract, contract supplier (one row per joint-venture member) and supplier.
GOLD_TABLES = ["country", "project", "package", "notice", "contract", "contract_supplier", "supplier"]


@pytest.mark.parametrize("table", GOLD_TABLES)
def test_the_run_builds_each_gold_table_with_a_public_from_date_on_every_row(gold, table):
    counts = one(gold, f"SELECT count(*) AS n_rows, count(public_from) AS n_dated FROM strata.gold.{table}")

    assert counts["n_rows"] > 0
    assert counts["n_dated"] == counts["n_rows"]


def test_a_kenya_award_reaches_gold_with_its_public_from_date(gold):
    # values.toml: award-541055-signed and award-541055-amount, contract 1903781.
    contract = one(gold, "SELECT * FROM strata.gold.contract WHERE wb_contract_number = :number", number="1903781")

    assert contract["step_reference"] == "KE-NWWDA-541055-CW-RFB"
    assert contract["contract_signing_date"] == dt.date(2026, 6, 22)
    assert contract["contract_amount_usd"] == decimal.Decimal("1287515.60")
    assert contract["public_from"] == dt.date(2026, 6, 22)


# ── Every Kenya award, notice and project value in values.toml ────────────

def contract_signed(gold, value):
    number = value["at"].split("wb_contract_number=")[1].split("]")[0]
    row = one(gold, "SELECT contract_signing_date, public_from FROM strata.gold.contract "
                    "WHERE wb_contract_number = :number", number=number)
    assert (row["contract_signing_date"], row["public_from"]) == (value["value"], value["value"])


def supplier_share(gold, value):
    number = value["at"].split("wb_contract_number=")[1].split("]")[0]
    row = one(gold, "SELECT supplier_contract_amount_usd, public_from FROM strata.gold.contract_supplier "
                    "WHERE wb_contract_number = :number", number=number)
    assert row["supplier_contract_amount_usd"] == decimal.Decimal(str(value["value"])).quantize(decimal.Decimal("0.01"))
    assert row["public_from"] is not None


def notice_date(gold, value):
    notice = value["at"].split("id=")[1].split("]")[0]
    row = one(gold, "SELECT notice_date, public_from FROM strata.gold.notice WHERE notice_id = :notice", notice=notice)
    assert (row["notice_date"], row["public_from"]) == (value["value"], value["value"])


def notice_loan(gold, value):
    """A loan form in a notice's text: the notice carries the one normalized loan number."""
    notice = value["at"].split("id=")[1].split("]")[0]
    row = one(gold, "SELECT loan_number, project_id, public_from FROM strata.gold.notice WHERE notice_id = :notice",
              notice=notice)
    assert (row["loan_number"], row["project_id"]) == ("IDA60300", "P156634")
    assert row["public_from"] is not None


def project_closing(gold, value):
    project = record(value["record"])["projects"]["P156634"]
    row = one(gold, "SELECT closing_date, public_from FROM strata.gold.project WHERE project_id = 'P156634'")
    assert row["closing_date"] == value["value"]
    assert row["public_from"] == dt.date.fromisoformat(project["public_disclosure_date"])


def individual_consultant(gold, value):
    """The supplier the dataset calls INDIVIDUAL CONSULTANT keeps its own ID, but has no name in gold."""
    rows = gold.run("SELECT s.name, s.kind, s.public_from FROM strata.gold.contract_supplier AS cs "
                    "JOIN strata.gold.supplier AS s ON s.supplier_id = cs.supplier_id "
                    "WHERE cs.wb_contract_number = '1668349'").rows
    assert [(name, kind) for name, kind, _ in rows] == [(None, "individual consultant")]
    assert rows[0][2] is not None


def notice_method_as_written(gold, value):
    """An old method name is stored as the current one, and the notice's own words stay in their columns."""
    notice = value["at"].split("id=")[1].split("]")[0]
    column = {"procurement_method_code": "procurement_method_code",
              "procurement_method_name": "procurement_method_as_written"}[value["at"].rsplit(".", 1)[1]]
    row = one(gold, f"SELECT {column} AS as_written, procurement_method, market_approach, public_from "
                    "FROM strata.gold.notice WHERE notice_id = :notice", notice=notice)
    assert row["as_written"] == value["value"]
    assert (row["procurement_method"], row["market_approach"]) == ("Request for Bids", "Open - International")
    assert row["public_from"] == dt.date(2015, 9, 14)  # its noticedate, 14-Sep-2015


def isr_rating(gold, value):
    """The projects API lists the rating twice; gold keeps it once, public from its ISR's date."""
    row = one(gold, "SELECT value, public_from FROM strata.gold.project_isr_rating "
                    "WHERE project_id = 'P156634' AND rating_name = 'Procurement'")
    assert (row["value"], row["public_from"]) == (value["value"], dt.date(2026, 6, 30))


CHECKS = {
    "notice-icb-code": notice_method_as_written,
    "notice-icb-name": notice_method_as_written,
    "award-541055-signed": contract_signed,
    "award-541062-signed": contract_signed,
    "award-229129-signed": contract_signed,
    "award-541055-amount": supplier_share,
    "award-notice-541055": notice_date,
    "loan-form-hyphen": notice_loan,
    "loan-form-bare": notice_loan,
    "loan-form-older": notice_loan,
    "loan-form-older-with-lender": notice_loan,
    "closing-date-p156634": project_closing,
    "individual-consultant": individual_consultant,
    "isr-procurement-p156634": isr_rating,
}


def test_every_kenya_award_notice_and_project_value_has_a_check():
    kenya = {key for key, value in VALUES.items() if value.get("record") in KENYA_RECORDS}

    assert kenya == set(CHECKS)


@pytest.mark.parametrize("value_id", sorted(CHECKS))
def test_each_kenya_value_appears_in_gold_with_its_public_from_date(gold, value_id):
    CHECKS[value_id](gold, VALUES[value_id])


# ── Contact details ──────────────────────────────────────────────────────

# This test's own idea of an email address and a phone number, written apart from the stripping
# code: an international number (+254 20 1234567, (+254) 20 123 4567), a Kenyan or Indian number
# with its trunk zero (046-1234567, 0141-1234567) and a Kenyan mobile (0722123456), also with a
# space after its zero (0 722-123456). Any letter, digit or removed contact right before an "@"
# counts as an email address, however untidy the rest of it is.
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+")
AT_SIGN = re.compile(r"[A-Za-z0-9\]]@")
PHONE = re.compile(r"\(?\+\d{1,3}\)?[ -]{0,3}\(?\d{2,4}\)?[ -]{0,3}\d{3,4}[ -]?\d{3,4}"
                   r"|(?<![\d.,/-])0\d{2,3}[ -]\d{6,7}(?![\d.])|(?<![\d.,/-])07\d{8}(?![\d.])"
                   r"|(?<![\d.,/-])0 7\d{2}[ -]?\d{6}(?![\d.])")
# Two more patterns of this test's own. One is a number of seven digits or more written after a
# phone label, whatever its shape (Tel 254 20 1234567, Tel.254412345678, Telephone Number: 254...,
# Mob. No. 98123 45678). The other is any digit written after a removed number and a slash. That
# digit may start a second mobile, or be the last digit of a second line (0722 123 456/7).
LABELLED_PHONE = re.compile(r"\b(?:tel\w*|\w*phone|mobile|mob|cell\w*|fax)\b[^0-9\n]{0,15}?\+?\(?\d[\d ().-]{6,}\d", re.I)
AFTER_REMOVED = re.compile(r"\[contact removed\]\s*/\s*\d")
# An email with spaces around its "@" (JDOE @ EXAMPLE.COM) or spelled out (jdoe [at] example [dot] com).
# Its domain has a letter, so a rate a report's table writes after a year ("INR - 2013 @7.4%") is not one.
SPACED_EMAIL = re.compile(r"\w\s*(?:@|[\[(]\s*at\s*[\])])\s*(?=[\w.]*[A-Za-z])\w+"
                          r"(?:(?:\.|\s*[\[(]\s*dot\s*[\])]\s*)\w+)+", re.I)


def text_values(engine):
    """Every non-empty text value in bronze, silver and gold, with where it is."""
    columns = engine.run("SELECT table_schema, table_name, column_name FROM system.information_schema.columns "
                         "WHERE table_catalog = 'strata' AND table_schema IN ('bronze', 'silver', 'gold') "
                         "AND data_type = 'VARCHAR'").rows
    for schema, table, column in columns:
        for (value,) in engine.connection.execute(
                f'SELECT "{column}" FROM strata.{schema}.{table} WHERE "{column}" IS NOT NULL').fetchall():
            yield f"{schema}.{table}.{column}", value


# Contact names that are job titles, not people. A P130164 notice gives "Chief Engineer" as its
# contact's name, and the project's reports use the title as an ordinary word ("headed by the Chief
# Engineer"), so it is no contact detail in a report's text. Every other table is still checked for it.
JOB_TITLES = {"Chief Engineer"}
REPORT_TEXT = ("bronze.document_texts.", "bronze.document_pages.", "silver.passages.", "gold.passage.")


def recorded_contacts():
    """Every contact name, email and phone number the recorded notices carry, read from the files."""
    found = set()
    for file in ("P156634", "P130164", "kenya-works-open-on-2026-10-09"):
        for notice in record(f"api/notices/{file}.json")["procnotices"]:
            found |= {notice[key].strip() for key in ("contact_name", "contact_email", "contact_phone_no")
                      if notice.get(key) and len(notice[key].strip()) > 5}
            found |= set(EMAIL.findall(notice.get("notice_text") or ""))
    return found


def awkward_contact_notice():
    """values.toml, awkward.contact_details: the notice that carries a contact name, email and phone.
    The test reads them from the recorded file, so this file never writes them out."""
    awkward = TRUTH["awkward"]["contact_details"]
    return next(notice for notice in record(awkward["record"])["procnotices"] if notice["id"] == awkward["notice"])


def test_no_email_address_or_phone_number_is_left_in_bronze_silver_or_gold(gold):
    found = recorded_contacts()
    notice = awkward_contact_notice()
    # Plain booleans and places, so a failure never prints the contact details themselves.
    assert all(notice[field] in found for field in ("contact_name", "contact_email", "contact_phone_no"))

    leaks = []
    for where, value in text_values(gold):
        leaks += [(where, "an email or phone number")
                  for _ in EMAIL.findall(value) + AT_SIGN.findall(value) + PHONE.findall(value)
                  + LABELLED_PHONE.findall(value) + AFTER_REMOVED.findall(value) + SPACED_EMAIL.findall(value)]
        leaks += [(where, "a recorded contact detail") for contact in found if contact in value
                  and not (contact in JOB_TITLES and where.startswith(REPORT_TEXT))]
    assert leaks == []


def outside_contacts(value):
    """A page without its contact fields and its free text: what stripping must leave as received."""
    if isinstance(value, dict):
        return {key: outside_contacts(item) for key, item in value.items()
                if key not in contacts.CONTACT_FIELDS + contacts.FREE_TEXT}
    if isinstance(value, list):
        return [outside_contacts(item) for item in value]
    return value


NOTICE_FILES = sorted(path.relative_to(RECORDED).as_posix() for path in (RECORDED / "api" / "notices").glob("*.json"))


@pytest.mark.parametrize("file", NOTICE_FILES)
def test_stripping_leaves_every_field_but_the_contact_fields_and_the_free_text_as_received(file):
    page = record(file)

    stripped, _ = contacts.strip(page)

    assert outside_contacts(stripped) == outside_contacts(page)


def test_stripping_keeps_reference_numbers_fiscal_years_and_postal_codes(gold):
    """A notice's reference ends in its fiscal years (NWWDA-WSDP-03-2019-2020), and a P.O. Box ends
    in its postal code (05586-00100). Neither is a phone number."""
    stripped, _ = contacts.strip(record("api/notices/P156634.json"))
    text = {notice["id"]: notice.get("notice_text") or "" for notice in stripped["procnotices"]}

    assert "NWWDA-WSDP-03-2019-2020" in text["OP00152444"]
    assert "MOWS-WSDP-01-2017-2018" in text["OP00121580"]
    assert "P.O BOX 05586-00100" in text["OP00246451"]
    notice = one(gold, "SELECT bid_reference_no FROM strata.gold.notice WHERE notice_id = 'OP00152444'")
    assert notice["bid_reference_no"] == "NWWDA-WSDP-03-2019-2020"
    assert one(gold, "SELECT count(*) AS n FROM strata.gold.notice WHERE bid_reference_no LIKE '%contact removed%'"
               ) == {"n": 0}


def test_stripping_removes_an_email_or_a_mobile_number_written_untidily():
    """Bidders' details in award notices are often typed by hand: a space after the "@" or inside the
    domain, a comma for a dot, a space after a mobile number's zero. These values are made up."""
    page = {"procnotices": [{"id": "OP-made-up", "notice_text": (
        "Email jdoe@g mail.com, jdoe@ example.org or j.doe@mail,com. Tel 0 722-123456. "
        "Ref NWWDA-WSDP-03-2019-2020, P.O BOX 05586-00100.")}]}

    stripped, removed = contacts.strip(page)

    assert stripped["procnotices"][0]["notice_text"] == (
        "Email [contact removed], [contact removed] or [contact removed]. Tel [contact removed]. "
        "Ref NWWDA-WSDP-03-2019-2020, P.O BOX 05586-00100.")
    assert removed == 4


def test_stripping_removes_every_number_written_after_a_phone_label():
    """Award notices write bidders' numbers with a country code and no plus, and a contact's second
    mobile after a slash. An extension and a phrase such as "Mobile 4x4 units" stay. Made-up values."""
    page = {"procnotices": [{"id": "OP-made-up", "contact_phone_no": "0722 123456", "notice_text": (
        "Tel 254 20 1234567, 254722123456. Tel.254412345678. PHONE: 256 41 1234567. TEL/FAX 258 21 123456. "
        "Tel: 0722 123 456/733123456. Ext. 42301. Mobile 4x4 units.")}]}

    stripped, removed = contacts.strip(page)

    assert stripped["procnotices"][0]["notice_text"] == (
        "Tel [contact removed]. Tel.[contact removed]. PHONE: [contact removed]. TEL/FAX [contact removed]. "
        "Tel: [contact removed]. Ext. 42301. Mobile 4x4 units.")
    assert removed == 1 + 6  # the contact_phone_no field, and six replacements in the text


def test_stripping_knows_every_common_phone_label_and_an_email_written_to_dodge_a_scan():
    """Notices label a number in many ways. A number with a country code and no plus goes after each
    label, an Indian mobile with no trunk zero goes after Mob, Ph, M or Contact, and an email goes
    when its "@" has spaces around it or is written [at] or (at). A phrase that only uses a label's
    word stays, and so does an extension. These values are made up."""
    page = {"procnotices": [{"id": "OP-made-up", "notice_text": (
        "Telephone Number: 254 20 1234567. Phone Number: 254722123456. Mobile Number: 254 722 123456. "
        "Tel #: 254 20 1234567. Telefax: 254 20 1234567. Cellphone: 254722123456. "
        "Mobile/WhatsApp: 254722123456. Mob: 9812345678. Mob. No. 98123 45678. Ph: 9812345678. "
        "M: 9812345678. Contact: 9812345678. "
        "Email JDOE @ EXAMPLE.COM, jdoe [at] example [dot] com or jdoe(at)example.com. "
        "Mobile 4x4 units, 3 Mobile cranes, Fax machine 2 units. Tel: 0722 123456 Ext. 42335.")}]}

    stripped, removed = contacts.strip(page)

    assert stripped["procnotices"][0]["notice_text"] == (
        "Telephone Number: [contact removed]. Phone Number: [contact removed]. Mobile Number: [contact removed]. "
        "Tel #: [contact removed]. Telefax: [contact removed]. Cellphone: [contact removed]. "
        "Mobile/WhatsApp: [contact removed]. Mob: [contact removed]. Mob. No. [contact removed]. "
        "Ph: [contact removed]. M: [contact removed]. Contact: [contact removed]. "
        "Email [contact removed], [contact removed] or [contact removed]. "
        "Mobile 4x4 units, 3 Mobile cranes, Fax machine 2 units. Tel: [contact removed] Ext. 42335.")
    assert removed == 7 + 5 + 3 + 1


def test_stripping_removes_emails_and_numbers_run_together_with_no_spaces():
    """Scraped award notices sometimes run a mobile, two emails and two numbers together, or write a
    second line as one more digit. Nothing of them may be left: no "@" and a domain, no first digits
    of a number, no last digit of a line. These values are made up."""
    page = {"procnotices": [{"id": "OP-made-up", "notice_text": (
        "MOMBASA, KENYA0712345678jdoe@example.com.info@example.org<br/>"
        "Nairobi, Kenya+254 712 345 678+254 20 123 4567sales@example.co<br/>"
        "Nairobi<br/>0722 123 456/7<br/>Dated 12/03/2019")}]}

    stripped, removed = contacts.strip(page)

    assert stripped["procnotices"][0]["notice_text"] == (
        "MOMBASA, [contact removed]<br/>"
        "Nairobi, Kenya[contact removed][contact removed] [contact removed]<br/>"
        "Nairobi<br/>[contact removed]<br/>Dated 12/03/2019")
    assert removed == 5


def test_the_fetch_counts_the_contact_details_it_removes(gold):
    removed = one(gold, "SELECT sum(contact_details_removed) AS n FROM strata.bronze.api_pages WHERE source = 'notices'")

    assert removed["n"] >= len(recorded_contacts())


# ── Data readiness ───────────────────────────────────────────────────────

def measures(gold, country="KE"):
    rows = gold.run("SELECT source, measure, count, denominator, as_of, detail FROM strata.ops.data_readiness "
                    "WHERE run_id = 'fixture' AND subject = :country", {"country": country}).rows
    return {(source, measure): (count, denominator, as_of, detail)
            for source, measure, count, denominator, as_of, detail in rows}


def test_the_run_writes_kenya_s_coverage_linked_and_fresh_measures_each_count_with_its_denominator(gold):
    kenya = measures(gold)
    counts = {key: value for key, value in kenya.items() if not key[1].startswith("fresh")}

    assert {("awards", "coverage_rows"), ("awards", "coverage_years"), ("awards", "linked_step_reference"),
            ("awards", "linked_notice"), ("notices", "coverage_rows"), ("notices", "coverage_years"),
            ("projects", "coverage_rows"), ("projects", "coverage_years")} <= set(counts)
    assert all(count is not None and denominator for count, denominator, _, _ in counts.values())
    # The awards files report all their rows in their count fields, and the run holds them all.
    assert kenya["awards", "coverage_rows"][:2] == (KENYA["award_rows"], KENYA["award_rows"])
    assert kenya["awards", "linked_step_reference"][:2] == (KENYA["with_step_reference"], KENYA["contracts"])
    assert kenya["awards", "linked_notice"][:2] == (KENYA["with_notice"], KENYA["contracts"])
    assert kenya["notices", "coverage_rows"][:2] == (KENYA["notices"], KENYA["notices"])


def test_each_measure_has_the_kind_the_spec_names(gold):
    """The spec's kinds: coverage (rows and years), linked, fresh, and the contact details removed,
    which the dashboard's Governance page shows as personal data stripped."""
    kinds = dict(gold.run("SELECT DISTINCT measure, kind FROM strata.ops.data_readiness "
                          "WHERE run_id = 'fixture' AND subject = 'KE'").rows)

    assert kinds == {"coverage_rows": "coverage", "coverage_years": "coverage", "linked_step_reference": "linked",
                     "linked_notice": "linked", "linked_project": "linked", "linked_sector": "linked",
                     "contact_details_removed": "stripped", "fresh_fetched": "fresh", "fresh_newest_record": "fresh"}


def test_the_ground_truth_sql_expects_the_counts_values_toml_holds():
    """Rule 4: the counts are written once. The SQL check's expect lines must say the same."""
    from strata.lakehouse import ground_truth

    case = ground_truth.read(ROOT / "tests" / "ground_truth" / "kenya_contracts_with_a_step_reference.sql")

    counts = (str(KENYA["with_step_reference"]), str(KENYA["contracts"]))
    assert case.expected[1:] == [("gold", *counts), ("ops", *counts)]


def test_the_comparables_sql_expects_the_counts_values_toml_holds():
    """Rule 4: values.toml's [comparables] writes the counts once. The SQL check's expect lines must
    say the same: 45 signed (two of them only in their award notice), 3 canceled and 4 still open."""
    from strata.lakehouse import ground_truth

    criteria = TRUTH["comparables"]
    case = ground_truth.read(ROOT / "tests" / "ground_truth" / "kenya_comparables_signed.sql")

    in_award_notice = criteria["signed_only_in_award_notice"]
    assert case.expected[1:] == [("award notice", str(in_award_notice)), ("canceled", str(criteria["canceled"])),
                                 ("contract awards", str(criteria["signed"] - in_award_notice)),
                                 ("still open", str(criteria["still_open"]))]


def test_each_source_is_fresh_as_of_its_fetch_with_its_cadence(gold):
    kenya = measures(gold)

    for source in ("awards", "notices", "projects"):
        assert kenya[source, "fresh_fetched"][2:] == (dt.date(2026, 10, 23), "daily")  # the fixture's recorded day
        assert kenya[source, "fresh_newest_record"][2] <= dt.date(2026, 10, 23)


def kenya_notices_with_a_contact_field():
    """Kenya's notices that fill any contact field, counted from the recorded files."""
    return {notice["id"] for file in KENYA_RECORDS if file.startswith("api/notices/")
            for notice in record(file)["procnotices"]
            if notice.get("project_ctry_name") == "Kenya"
            and any(str(notice.get(field) or "").strip() for field in contacts.CONTACT_FIELDS)}


def test_the_contact_details_removed_are_recorded_as_a_data_readiness_measure(gold):
    """The measure counts notices, as its denominator does: a notice counts when the fetch removed
    any contact detail from it, from a contact field or from its text."""
    removed, notices, _, detail = measures(gold)["notices", "contact_details_removed"]

    assert notices == KENYA["notices"]
    assert len(kenya_notices_with_a_contact_field()) <= removed <= notices
    assert detail == ("This counts the notices that had contact names, addresses, emails, phone numbers or web "
                      "addresses removed before they were kept, out of the notices held.")


# ── Fiscal years and currencies ──────────────────────────────────────────

def test_fiscal_years_run_july_to_june_as_the_awards_dataset_counts_them(gold):
    """Silver works the fiscal year out from the signing date; the dataset's own fiscal_year field,
    which silver does not read, is the independent answer."""
    recorded_years = {row["wb_contract_number"]: row["fiscal_year"] for file in KENYA_RECORDS
                      if file.startswith("api/awards/") for row in record(file)["data"]}
    gold_years = dict(gold.run("SELECT wb_contract_number, fiscal_year FROM strata.gold.contract "
                               "WHERE country_code = 'KE' AND source = 'awards'").rows)

    assert gold_years == recorded_years


def test_a_notice_carries_the_fiscal_year_its_date_falls_in(gold):
    """The recorded notices' dates: OP00191645 on August 17, 2022, which opens FY2023, and OP00175878
    on April 21, 2022, which closes FY2022."""
    years = dict(gold.run("SELECT notice_id, fiscal_year FROM strata.silver.notices "
                          "WHERE notice_id IN ('OP00191645', 'OP00175878')").rows)

    assert years == {"OP00191645": 2023, "OP00175878": 2022}


def test_an_award_notice_keeps_its_signed_price_in_the_currency_it_names(gold):
    # values.toml, awkward.joint_venture: award notice OP00125855 for KE-KIMAWASCO-158691-CW-RFB. Its
    # text gives "Signed Contract price KES 151,320,438.30"; the awards dataset gives US dollars.
    notice = [row for row in record("api/notices/P156634.json")["procnotices"] if row["id"] == "OP00125855"][0]
    assert "Signed Contract price<br/>KES 151,320,438.30" in notice["notice_text"]

    row = one(gold, "SELECT signed_contract_price, signed_contract_currency FROM strata.gold.notice "
                    "WHERE notice_id = 'OP00125855'")
    assert (row["signed_contract_price"], row["signed_contract_currency"]) == (decimal.Decimal("151320438.30"), "KES")


# ── Loan numbers and old method names ────────────────────────────────────

def project_credits(project):
    """The loans and credits a recorded project record lists, as the projects API writes them (IDA-60300)."""
    loans = record(f"api/projects/{project}.json")["projects"][project].get("loan_transactions") or []
    return {loan["financier_loan"] for loan in loans if loan.get("financier_loan")}


def test_a_loan_number_in_each_of_its_forms_normalizes_to_one_value_and_joins_to_its_project(gold):
    """values.toml: credit 60300 as the credits dataset (IDA60300), notices and the projects API
    (IDA-60300), a notice's free text (60300) and Procurement Plans (IDA / 60300) write it, and
    the older four-digit form with a country code that notices also use (6030-KE, IDA- 6030-KE).
    clean.loan_number is the one normalization every source uses; a number written with no lender
    keeps its digits, and gold matches them to the loans of the notice's own project."""
    with_lender = ("loan-form-compact", "loan-form-hyphen", "loan-form-slash", "loan-form-older-with-lender")
    assert {clean.loan_number(VALUES[key]["value"]).normalized for key in with_lender} == {"IDA60300"}
    for key in ("loan-form-bare", "loan-form-older"):
        written = clean.loan_number(VALUES[key]["value"])
        assert (written.normalized, written.digits) == (None, "60300")
    india = clean.loan_number(VALUES["loan-form-older-india"]["value"])
    assert {f"IDA-{india.digits}"} == project_credits("P130164")

    loan = one(gold, "SELECT project_id, public_from FROM strata.gold.project_loan WHERE loan_number = 'IDA60300'")
    assert loan["project_id"] == "P156634"
    for key in ("loan-form-bare", "loan-form-older", "loan-form-older-with-lender"):
        notice_loan(gold, VALUES[key])


@pytest.mark.parametrize("project", ["P156634", "P130164"])
def test_every_notice_that_writes_one_of_its_projects_credits_carries_it_in_gold(gold, project):
    """However a notice writes a credit its project record lists (IDA-60300, 60300 KE, 6030-KE,
    IDA- 6030-KE, 6030), gold gives the notice that credit, and never a lender with four digits."""
    rows = gold.run("SELECT s.notice_id, s.loan_number_as_written, n.loan_number FROM strata.silver.notices AS s "
                    "JOIN strata.gold.notice AS n ON n.notice_id = s.notice_id "
                    "WHERE s.project_id = :project AND s.loan_number_as_written IS NOT NULL", {"project": project}).rows
    credits = {credit.split("-")[1]: credit.replace("-", "") for credit in project_credits(project)}
    wrong, checked = [], 0
    for notice, written, loan in rows:
        digits = re.sub(r"\D", "", written)
        for number, credit in credits.items():
            if digits in (number, number[:-1]):  # 60300, or the older four-digit 6030
                checked += 1
                if loan != credit:
                    wrong.append((notice, written, loan))
    assert checked and wrong == []
    assert not [loan for _, _, loan in rows if loan and re.fullmatch(r"[A-Z]+\d{4}", loan)]


def test_a_notice_that_says_ncb_is_stored_as_request_for_bids_open_national(gold):
    raw = [notice for notice in record("api/notices/P130164.json")["procnotices"] if notice["id"] == "OP00019969"][0]
    assert raw["procurement_method_code"] == "NCB"

    notice = one(gold, "SELECT procurement_method, market_approach, procurement_method_as_written "
                       "FROM strata.gold.notice WHERE notice_id = 'OP00019969'")
    assert notice == {"procurement_method": "Request for Bids", "market_approach": "Open - National",
                      "procurement_method_as_written": raw["procurement_method_name"]}


# ── Packages and their Process Status ────────────────────────────────────

def test_a_package_takes_its_process_status_from_the_newest_plan_that_lists_it(gold):
    """values.toml, [[comparable]]: the KIMAWASCO plan of March 19, 2025 marks three works packages
    Canceled. A package no plan read so far lists, such as one still open on P176758 or P170941,
    has no Process Status."""
    package = ("SELECT p.process_status, v.plan_date, p.process_status_public_from FROM strata.gold.package AS p "
               "LEFT JOIN strata.silver.plan_versions AS v ON v.document_id = p.process_status_document_id "
               "WHERE p.step_reference = :reference")
    canceled = [c for c in TRUTH["comparable"] if "canceled_in" in c]
    still_open = [c for c in TRUTH["comparable"] if "signed" not in c and "canceled_in" not in c]

    for comparable in canceled:
        plan_date = dt.date.fromisoformat(comparable["canceled_in"].rsplit("procurement-plan-", 1)[1])
        status, listed_on, public_from = one(gold, package, reference=comparable["reference"]).values()
        assert (status, listed_on) == ("Canceled", plan_date), comparable["reference"]
        assert public_from is not None
    assert len(canceled) == 3
    assert one(gold, package, reference=still_open[0]["reference"])["process_status"] is None


# ── Joint ventures and individual consultants ────────────────────────────

def test_the_joint_venture_award_becomes_one_joint_venture_supplier_linked_to_its_members(gold):
    venture = TRUTH["awkward"]["joint_venture"]  # contract 1624689, members 503708 and 503711
    share = decimal.Decimal(str(venture["amount_per_member_usd"])).quantize(decimal.Decimal("0.01"))
    # The KIMAWASCO plan of March 19, 2025 gives KE-KIMAWASCO-158691-CW-RFB an Actual Amount of
    # 1,395,944.66 on PDF page 3: the contract's amount, which the two members' shares make once.
    plan = (RECORDED / "documents/P156634/procurement-plan-2025-03-19.pages.txt").read_text().split("\f")[2]
    assert "1,800,000.00 1,395,944.66 Terminated" in plan

    contract = one(gold, "SELECT * FROM strata.gold.contract WHERE wb_contract_number = :number",
                   number=venture["contract"])
    assert contract["contract_amount_usd"] == decimal.Decimal("1395944.66")
    assert (contract["joint_venture"], contract["supplier_count"]) == (True, 2)
    supplier = one(gold, "SELECT * FROM strata.gold.supplier WHERE supplier_id = :supplier_id",
                   supplier_id=contract["supplier_id"])
    assert (supplier["kind"], supplier["member_count"]) == ("joint venture", 2)
    members = gold.run("SELECT supplier_id, joint_venture_id, supplier_contract_amount_usd "
                       "FROM strata.gold.contract_supplier WHERE wb_contract_number = :number ORDER BY supplier_id",
                       {"number": venture["contract"]}).rows
    assert members == tuple((member, contract["supplier_id"], share) for member in venture["supplier_ids"])
    firms = gold.run("SELECT kind FROM strata.gold.supplier WHERE supplier_id IN (:first, :second)",
                     {"first": venture["supplier_ids"][0], "second": venture["supplier_ids"][1]}).rows
    assert firms == (("firm",), ("firm",))
    package = one(gold, "SELECT sum(contract_amount_usd) AS total FROM strata.gold.contract "
                        "WHERE step_reference = 'KE-KIMAWASCO-158691-CW-RFB'")
    assert package["total"] == decimal.Decimal("1395944.66")


def test_individual_consultant_rows_never_yield_a_supplier_name(gold):
    """values.toml, individual-consultant: the awards dataset names some suppliers only as
    INDIVIDUAL CONSULTANT, each with its own hashed supplier ID."""
    rows = [row for file in KENYA_RECORDS if file.startswith("api/awards/") for row in record(file)["data"]
            if row["supplier"] == "INDIVIDUAL CONSULTANT"]
    ids = sorted({row["supplier_id"] for row in rows})
    assert len(ids) > 1

    suppliers = gold.run("SELECT supplier_id, name, kind FROM strata.gold.supplier ORDER BY supplier_id").rows
    individuals = [(supplier_id, name, kind) for supplier_id, name, kind in suppliers if supplier_id in ids]
    assert individuals == [(supplier_id, None, "individual consultant") for supplier_id in ids]
    assert [name for _, name, _ in suppliers if name and "INDIVIDUAL CONSULTANT" in name.upper()] == []


@pytest.mark.parametrize("label", ["INDIVIDUAL CONSULTANT", "Individual Consultant", " individual  consultant "])
def test_an_individual_consultant_label_in_any_capitals_never_becomes_a_supplier_name(label):
    from strata.lakehouse.silver import awards

    page = {"data": [{"wb_contract_number": "1668349", "supplier_id": "1", "supplier": label}]}
    rows = awards.parse(page, "a page", dt.datetime(2026, 10, 23, tzinfo=dt.UTC))["strata.silver.awards"]

    row = dict(zip(awards.TABLES["strata.silver.awards"], rows[0], strict=True))
    assert (row["supplier"], row["individual_consultant"]) == (None, True)


COMPARABLES = TRUTH["comparable"]


@pytest.mark.parametrize("comparable", COMPARABLES, ids=[c["reference"] for c in COMPARABLES])
def test_each_comparable_package_is_in_gold_with_its_notice_and_signing(gold, comparable):
    package = one(gold, "SELECT * FROM strata.gold.package WHERE step_reference = :reference",
                  reference=comparable["reference"])

    assert (package["first_notice_id"], package["first_notice_date"]) == (comparable["notice"], comparable["notice_date"])
    assert package["procurement_category"] == "Works"
    assert package["procurement_method"] == "Request for Bids"
    assert package["country_code"] == "KE"
    assert package["public_from"] <= comparable["notice_date"]
    if "contract" in comparable:  # signed, with a row in the awards dataset
        assert (package["contract_signed_on"], package["signed_in"]) == (comparable["signed"], "contract awards")
        assert package["review_type"] == comparable["review_type"]
        contract = one(gold, "SELECT step_reference FROM strata.gold.contract WHERE wb_contract_number = :number",
                       number=comparable["contract"])
        assert contract["step_reference"] == comparable["reference"]
    elif "award_notice" in comparable:  # signed, only in its Contract Award notice
        assert (package["contract_signed_on"], package["signed_in"]) == (comparable["signed"], "award notice")
        assert package["award_notice_id"] == comparable["award_notice"]
    else:  # canceled in its plan, or still open on the plan's date
        assert (package["contract_signed_on"], package["signed_in"]) == (None, None)
    if "bids_due" in comparable:
        assert (package["bids_due"], package["project_id"]) == (comparable["bids_due"], comparable["project"])
