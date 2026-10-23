"""The ground-truth file, tests/ground_truth/values.toml, lists every value the spec's Testing
Decisions name, with where each one came from. These tests prove that each value is really
in the recorded fixture, read straight from the recorded files and never through Strata's
own code:

- a quote is word for word on the stated PDF page of a recorded document, or in the stated
  field of a recorded API record, ignoring only whitespace and line-end hyphenation, and each
  value is written in its own quote;
- the October 9, 2026 plan's rows hold the values the blueprint's Check a plan wireframe shows;
- the comparable works packages join notice to signed contract on the STEP reference, and a
  package with no signed contract is either canceled, as its plan row says, or still open;
- the awkward cases the lakehouse must handle on purpose are present.
"""

import datetime
import functools
import re
import tomllib
from pathlib import Path

import pytest

from strata.fixture import recorded as fmt

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "tests" / "ground_truth" / "values.toml"
RECORDED = ROOT / "data" / "fixture" / "recorded"
TRUTH = tomllib.loads(GROUND_TRUTH.read_text())
VALUES = TRUTH["value"]
BY_ID = {value["id"]: value for value in VALUES}
DOCUMENT_FIELDS = {"document", "document_type", "project", "date", "pdf_page"}
RECORD_FIELDS = {"record", "at"}

# Every value the spec's Testing Decisions name, by its id in values.toml.
SPEC_VALUES = [
    "plan-541055-estimated", "plan-541055-status", "plan-541055-planned-completion", "plan-541055-no-signed-contract",
    "plan-229129-estimated", "plan-229129-signed", "plan-229129-first-planned-signing", "plan-229129-days-late",
    "plan-229129-actual", "plan-199461-reference-method", "plan-199461-method-column", "plan-503455-actual-zero",
    "plan-541061-actual-zero",
    "icr-para-54", "icr-para-55", "icr-para-78", "icr-date",
    "isr-7-date", "isr-7-rating", "mid-term-review", "restructuring", "isr-12-date", "isr-12-rating",
    "award-7431-signed", "icr-review-date", "icr-review-reissue-date", "icr-review-number-2020",
    "icr-review-number-2023",
]


def squash(text):
    return re.sub(r"\s+", "", text)


def word_for_word(quote, text):
    """True when the quote is in the text, ignoring whitespace and words split by a hyphen at a line end."""
    joined = re.sub(r"-[ \t]*\r?\n\s*", "", text)
    return squash(quote) in squash(text) or squash(quote) in squash(joined)


def page(document, number):
    return fmt.pages(RECORDED / f"{document}.pages.txt")[number - 1]


def resolve(record, path):
    """Follow a path such as procnotices[id=OP00044090].notice_text through a recorded response.

    A [key=value&key=value] step picks the one list item whose fields match; a number picks an item."""
    current = fmt.read(RECORDED / record).body
    for step in path.split("."):
        name, _, condition = step.partition("[")
        if name:
            current = current[int(name)] if isinstance(current, list) else current[name]
        if condition:
            wanted = dict(pair.split("=", 1) for pair in condition.rstrip("]").split("&"))
            matches = [item for item in current if all(str(item.get(k)) == v for k, v in wanted.items())]
            assert len(matches) == 1, f"{record}: {step} matched {len(matches)} records, not one"
            current = matches[0]
    return current


def located_text(value):
    if "document" in value:
        return page(value["document"], value["pdf_page"])
    return str(resolve(value["record"], value["at"]))


def test_the_ground_truth_lists_every_value_the_spec_names():
    missing = [name for name in SPEC_VALUES if name not in BY_ID]
    assert not missing, f"values.toml has no entry for {missing}"


@pytest.mark.parametrize("value", VALUES, ids=lambda value: value["id"])
def test_each_value_names_its_source(value):
    assert value.get("says") and "value" in value and value.get("quote")
    fields = DOCUMENT_FIELDS if "document" in value else RECORD_FIELDS
    assert fields <= set(value), f"{value['id']} needs {sorted(fields - set(value))}"


@pytest.mark.parametrize("value", VALUES, ids=lambda value: value["id"])
def test_each_quote_is_word_for_word_where_the_ground_truth_says(value):
    assert word_for_word(value["quote"], located_text(value)), (
        f"{value['id']}: {value['quote']!r} is not in {value.get('document') or value['record']}"
        f" {'page ' + str(value['pdf_page']) if 'pdf_page' in value else value.get('at')}")


# Values that read their quote rather than copy it. Each has its own check: the plan row
# test shows KE-NWWDA-541055-CW-RFB's Actual Amount 0.00 and status Pending Implementation,
# and the day-count test counts the days between two dates. A first-listed value is its
# plan's date, which the first-listed test checks.
READINGS = {"plan-541055-no-signed-contract", "plan-229129-days-late"}


def written_forms(value):
    """The ways a value is written in the sources: a date in ISO, dd-Mon-yyyy, yyyy/mm/dd or
    "Month d, yyyy" form, an amount with thousands commas or as JSON writes it, anything else as it is."""
    if isinstance(value, datetime.date):
        return {value.isoformat(), value.strftime("%d-%b-%Y"), value.strftime("%Y/%m/%d"),
                f"{value:%B} {value.day}, {value.year}"}
    if isinstance(value, float):
        return {f"{value:,.2f}", str(value)}
    return {str(value)}


def test_each_reading_is_a_value_in_the_ground_truth():
    assert READINGS <= set(BY_ID)


@pytest.mark.parametrize("value", [v for v in VALUES if v["id"] not in READINGS], ids=lambda value: value["id"])
def test_each_value_is_written_in_its_own_quote(value):
    in_quote = any(squash(form) in squash(value["quote"]) for form in written_forms(value["value"]))
    the_plans_date = "first_lists" in value and value["value"] == value["date"]
    assert in_quote or the_plans_date, f"{value['id']}: {value['value']!r} is not in its quote {value['quote']!r}"


@pytest.mark.parametrize("value", [v for v in VALUES if "days_between" in v], ids=lambda value: value["id"])
def test_a_day_count_matches_the_two_dates_it_was_counted_between(value):
    start, end = (datetime.date.fromisoformat(str(BY_ID[name]["value"])) for name in value["days_between"])
    assert (end - start).days == value["value"]


FIRST_LISTED = [value for value in VALUES if "first_lists" in value]


def test_every_plan_said_to_be_the_first_to_list_an_activity_has_a_check():
    assert {value["first_lists"] for value in FIRST_LISTED} == {
        "KE-NWWDA-229129-CW-RFB", "KE-NWWDA-541055-CW-RFB", "KE-CWSB-567630-CW-DIR", "NWWDA-WSDP-03-2019-2020"}


@pytest.mark.parametrize("value", FIRST_LISTED, ids=lambda value: value["id"])
def test_a_plan_said_to_be_the_first_to_list_an_activity_lists_it_and_the_version_before_does_not(value):
    """not_in is the same agency's previous version, found by reading the Executing Agency of every plan between."""
    earlier = value["not_in"]
    earlier_texts = [*fmt.pages(RECORDED / f"{earlier}.pages.txt"), fmt.read(RECORDED / f"{earlier}.txt").body]

    assert word_for_word(value["first_lists"], page(value["document"], value["pdf_page"]))
    assert re.search(r"\d{4}-\d{2}-\d{2}$", earlier).group() < str(value["date"])
    assert not any(word_for_word(value["first_lists"], text) for text in earlier_texts), (
        f"{earlier} already lists {value['first_lists']}")


# The eight activities in the blueprint's Check a plan wireframe (docs/blueprint/strata-blueprint.html).
WIREFRAME_ACTIVITIES = {
    "KE-NWWDA-541055-CW-RFB", "KE-NWWDA-229129-CW-RFB", "KE-NWWDA-541062-CW-RFQ", "KE-NWWDA-199461-GO-RFB",
    "KE-NWWDA-503455-CW-RFQ", "KE-NWWDA-541061-CW-RFQ", "KE-NWWDA-199471-GO-RFQ", "NWWDA-WSDP-03-2019-2020",
}
ROW_FIELDS = ("reference", "description", "review_type", "method", "market_approach", "estimated_amount_usd",
              "actual_amount_usd", "process_status")


def plan_rows():
    """Each activity's stretch of the plan page, from its reference to the next activity's, with no whitespace."""
    plan = TRUTH["plan"]
    text = squash(page(plan["document"], plan["pdf_page"]))
    references = [row["reference"] for row in TRUTH["plan_row"]] + plan["also_lists"]
    starts = sorted((text.index(squash(reference)), reference) for reference in references)
    ends = [start for start, _ in starts[1:]] + [len(text)]
    return {reference: text[start:end] for (start, reference), end in zip(starts, ends)}


def test_the_ground_truth_holds_the_eight_activities_the_wireframe_shows():
    assert {row["reference"] for row in TRUTH["plan_row"]} == WIREFRAME_ACTIVITIES


@pytest.mark.parametrize("row", TRUTH["plan_row"], ids=lambda row: row["reference"])
def test_each_plan_row_holds_its_values_in_its_own_row_of_the_october_9_plan(row):
    text = plan_rows()[row["reference"]]
    for field in ROW_FIELDS:
        assert squash(row[field]) in text, f"{row['reference']}: {field} {row[field]!r} is not in its row"
    for quote in row["quotes"]:
        assert squash(quote) in text, f"{row['reference']}: {quote!r} is not in its row"
    # A quote must show each field in place. The Actual Amount is checked right after the
    # Estimated Amount, its column's neighbour, because "0.00" alone is inside "1,230,000.00".
    shown = {field: row[field] for field in ("review_type", "method", "market_approach", "estimated_amount_usd",
                                             "process_status")}
    shown["actual_amount_usd"] = f"{row['estimated_amount_usd']} {row['actual_amount_usd']}"
    for field, text in shown.items():
        assert any(squash(text) in squash(quote) for quote in row["quotes"]), (
            f"{row['reference']}: no quote shows {field} {text!r} in place")


CRITERIA = TRUTH["comparables"]
COMPARABLES = TRUTH["comparable"]
SIGNED = [c for c in COMPARABLES if "signed" in c]
CANCELED = [c for c in COMPARABLES if "canceled_in" in c]
STILL_OPEN = [c for c in COMPARABLES if "signed" not in c and "canceled_in" not in c]


def notice_date(notice):
    return datetime.datetime.strptime(notice["noticedate"], "%d-%b-%Y").date()


def reference_of(row, field):
    return (row.get(field) or "").strip()


@functools.cache
def recorded_notices():
    return [notice for name in CRITERIA["notices"] for notice in fmt.read(RECORDED / name).body["procnotices"]]


@functools.cache
def awards_by_reference():
    awards = {}
    for name in CRITERIA["awards"]:
        for row in fmt.read(RECORDED / name).body["data"]:
            awards.setdefault(reference_of(row, "borrower_contract_reference_number"), []).append(row)
    return awards


def notices_for(reference):
    return [n for n in recorded_notices() if reference_of(n, "bid_reference_no") == reference]


def plan_row(document, pdf_page, reference):
    """An activity's stretch of a plan page, from its reference to the next activity's, with no whitespace."""
    text = squash(page(document, pdf_page))
    start = text.index(squash(reference))
    later = re.search(r"KE-[A-Z]+-\d+-", text[start + len(squash(reference)):])
    return text[start:start + len(squash(reference)) + later.start()] if later else text[start:]


@pytest.mark.parametrize("comparable", COMPARABLES, ids=lambda comparable: comparable["reference"])
def test_each_comparable_joins_its_notice_to_its_signed_contract_on_the_step_reference(comparable):
    notice = next(n for n in recorded_notices() if n["id"] == comparable["notice"])
    awards = awards_by_reference().get(comparable["reference"], [])
    award_notices = [n["id"] for n in notices_for(comparable["reference"]) if n["notice_type"] == "Contract Award"]

    assert notice["notice_type"] == "Invitation for Bids"
    assert reference_of(notice, "bid_reference_no") == comparable["reference"]
    assert notice_date(notice) == comparable["notice_date"]
    assert notice["project_id"] == comparable.get("project", "P156634")
    if "award_notice" in comparable:
        award = next(n for n in recorded_notices() if n["id"] == comparable["award_notice"])
        signature = "Contract Signature Date</b><br/>(YYYY/MM/DD)<br/>" + comparable["signed"].strftime("%Y/%m/%d")
        assert award["notice_type"] == "Contract Award"
        assert reference_of(award, "bid_reference_no") == comparable["reference"]
        assert signature in award["notice_text"]
        assert awards == [], f"{comparable['reference']} now has an award row: give it contract and review_type"
    elif "signed" in comparable:
        assert {row["wb_contract_number"] for row in awards} == {comparable["contract"]}
        assert {row["contract_signing_date"] for row in awards} == {comparable["signed"].strftime("%d-%b-%Y")}
        assert {row["review_type"] for row in awards} == {comparable["review_type"]}
    elif "canceled_in" in comparable:
        row = plan_row(comparable["canceled_in"], comparable["pdf_page"], comparable["reference"])
        assert "Canceled" in comparable["quote"] and squash(comparable["quote"]) in row, (
            f"{comparable['reference']}: {comparable['quote']!r} is not in its row of {comparable['canceled_in']}")
        if "notice_says" in comparable:
            assert word_for_word(comparable["notice_says"], notice["notice_text"])
        assert awards == [] and award_notices == [], f"{comparable['reference']} is listed as canceled but was signed"
    else:
        canceled = [n["id"] for n in notices_for(comparable["reference"])
                    if re.search(r"cancel", n.get("notice_text") or "", re.IGNORECASE)]
        assert awards == [], f"{comparable['reference']} is listed as still open but has an award row"
        assert award_notices == [], (
            f"{comparable['reference']} is listed as still open but has award notices {award_notices}")
        assert canceled == [], f"{comparable['reference']} is listed as still open but {canceled} says it was canceled"
        # Bids were due after the plan's date, so no contract could have been signed by then.
        assert notice["submission_deadline_date"][:10] == comparable["bids_due"].isoformat()
        assert comparable["bids_due"] > CRITERIA["first_notice_to"]


def test_at_least_25_comparables_are_signed_and_at_least_3_are_still_open():
    assert len(SIGNED) == CRITERIA["signed"] >= 25
    assert len(STILL_OPEN) == CRITERIA["still_open"] >= 3
    assert len(CANCELED) == CRITERIA["canceled"]
    assert len([c for c in SIGNED if "award_notice" in c]) == CRITERIA["signed_only_in_award_notice"]


def test_every_canceled_plan_row_of_a_comparable_is_marked_canceled_in_the_ground_truth():
    """A package whose plan row says Canceled can never be signed, so it is not censored as still open."""
    for comparable in COMPARABLES:
        for document, pdf_page in {(c["canceled_in"], c["pdf_page"]) for c in CANCELED}:
            text = squash(page(document, pdf_page))
            if squash(comparable["reference"]) in text:
                row = plan_row(document, pdf_page, comparable["reference"])
                assert ("Canceled" in row) == ("canceled_in" in comparable), comparable["reference"]


def test_the_list_holds_every_recorded_package_that_meets_the_default_criteria():
    first = {}
    for notice in recorded_notices():
        if (notice["notice_type"] == "Invitation for Bids"
                and notice.get("procurement_group") == CRITERIA["procurement_group"]
                and notice.get("procurement_method_code") == CRITERIA["procurement_method_code"]
                and notice["project_ctry_name"] == CRITERIA["country"]):
            reference = reference_of(notice, "bid_reference_no")
            if reference not in first or notice_date(notice) < notice_date(first[reference]):
                first[reference] = notice
    meets = {reference: notice["id"] for reference, notice in first.items()
             if CRITERIA["first_notice_from"] <= notice_date(notice) <= CRITERIA["first_notice_to"]}
    assert meets == {c["reference"]: c["notice"] for c in COMPARABLES}


def test_the_narrower_criteria_leave_fewer_than_20_comparables():
    narrower = [c for c in COMPARABLES if c.get("review_type") == CRITERIA["narrower_review_type"]]
    assert len(narrower) == CRITERIA["narrower_count"] < 20


AWKWARD = TRUTH["awkward"]


def test_the_ground_truth_names_every_awkward_case_the_ticket_lists():
    assert {"contact_details", "joint_venture", "dated_in_the_future"} <= set(AWKWARD)
    assert {"loan-form-compact", "loan-form-hyphen", "loan-form-bare", "loan-form-slash", "individual-consultant",
            "plan-503455-actual-zero", "plan-199461-reference-method", "plan-199461-method-column"} <= set(BY_ID)


def test_a_recorded_notice_carries_a_contact_name_email_and_phone_number():
    case = AWKWARD["contact_details"]
    notice = resolve(case["record"], f"procnotices[id={case['notice']}]")
    # Plain booleans, so a failure never prints the contact details themselves.
    has_name = bool(notice["contact_name"].strip())
    has_email = bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", notice["contact_email"].strip()))
    has_phone = len(re.sub(r"\D", "", notice["contact_phone_no"])) >= 7
    assert has_name and has_email and has_phone


def test_the_loan_number_forms_are_four_spellings_of_one_credit():
    forms = [BY_ID[name]["value"] for name in ("loan-form-compact", "loan-form-hyphen", "loan-form-bare",
                                               "loan-form-slash")]
    assert len(set(forms)) == 4
    assert {re.sub(r"\D", "", form) for form in forms} == {"60300"}


def test_a_joint_venture_award_has_one_row_per_member_with_the_amount_split_equally():
    case = AWKWARD["joint_venture"]
    rows = [row for row in fmt.read(RECORDED / case["awards"]).body["data"]
            if row["wb_contract_number"] == case["contract"]]
    notice = resolve(case["notices"], f"procnotices[id={case['notice']}]")
    assert sorted(row["supplier_id"] for row in rows) == case["supplier_ids"]
    assert {row["supplier_contract_amount_usd"] for row in rows} == {case["amount_per_member_usd"]}
    assert notice["notice_type"] == "Contract Award"
    assert all(f"({supplier})" in notice["notice_text"] for supplier in case["supplier_ids"])


def test_a_recorded_document_is_dated_after_its_disclosure_and_after_it_was_recorded():
    case = AWKWARD["dated_in_the_future"]
    recording = fmt.read(RECORDED / case["record"])
    document = recording.body["documents"][case["document"]]
    assert document["docdt"][:10] == case["docdt"].isoformat()
    assert document["disclosure_date"][:10] == case["disclosed"].isoformat()
    assert case["docdt"] > datetime.date.fromisoformat(recording.recorded) > case["disclosed"]


def test_a_contract_signed_in_the_fy2017_2019_gap_is_in_no_award_dataset():
    case = AWKWARD["fy2017_2019_gap"]
    rows = fmt.read(RECORDED / case["awards"]).body["data"]
    assert rows, "the FY2001 to FY2016 awards file is empty"
    assert all(row["borrower_contract_reference_number"] != case["reference"] for row in rows)
    assert datetime.date(2016, 7, 1) <= BY_ID["award-7431-signed"]["value"] <= datetime.date(2019, 6, 30)
