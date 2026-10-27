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


def test_each_value_has_an_id_of_its_own():
    # A test reads a value by its id, so a second entry with the same id would never be read.
    ids = [value["id"] for value in VALUES]
    assert sorted({i for i in ids if ids.count(i) > 1}) == []


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
READINGS = {"plan-541055-no-signed-contract", "plan-229129-days-late", "icr-pdf-pages", "icr-months-after-7431"}


def test_a_page_count_is_the_pages_of_its_document():
    """icr-pdf-pages reads its document's last page: the pages file holds that many pages."""
    value = BY_ID["icr-pdf-pages"]
    assert len(fmt.pages(RECORDED / f"{value['document']}.pages.txt")) == value["value"] == value["pdf_page"]


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


def spaced(text):
    """Whitespace made single, not removed, so "220,000.00 0.00" stays two numbers."""
    return re.sub(r"\s+", " ", text).strip()


def is_written_in(value, quote):
    """A number or date counts only when no digit, comma or point sits right before it and no digit right after, so
    "45,092.76" is not found inside "1,245,092.76" (ticket 05's review, P1)."""
    for form in written_forms(value):
        if isinstance(value, (int, float, datetime.date)) and not isinstance(value, bool):
            if re.search(r"(?<![\d,.])" + re.escape(form) + r"(?!\d)", spaced(quote)):
                return True
        elif spaced(form) in spaced(quote):
            return True
    return False


def test_a_number_is_never_found_as_the_tail_of_a_longer_one():
    assert is_written_in(1245092.76, "at US$1,245,092.76 on")
    assert not is_written_in(45092.76, "at US$1,245,092.76 on")
    assert not is_written_in(287515.6, "1287515.6")


@pytest.mark.parametrize("value", [v for v in VALUES if v["id"] not in READINGS], ids=lambda value: value["id"])
def test_each_value_is_written_in_its_own_quote(value):
    the_plans_date = "first_lists" in value and value["value"] == value["date"]
    assert is_written_in(value["value"], value["quote"]) or the_plans_date, (
        f"{value['id']}: {value['value']!r} is not in its quote {value['quote']!r}")


SOURCE_ABOUT = {source.file: source.about for source in fmt.load_manifest().sources}


def documents_api_date(document, project):
    """The docdt the recorded Documents API list gives for a document, by the id in its About line."""
    api_id = re.search(r"Documents API id (\d+)", SOURCE_ABOUT[document]).group(1)
    record = fmt.read(RECORDED / "api" / "documents" / f"{project}.json").body["documents"][f"D{api_id}"]
    return datetime.date.fromisoformat(record["docdt"][:10])


@pytest.mark.parametrize("value", [v for v in VALUES if "document" in v and v.get("project") and (
    RECORDED / "api" / "documents" / f"{v['project']}.json").exists()], ids=lambda value: value["id"])
def test_each_document_value_is_dated_as_the_documents_api_dates_its_document(value):
    """Ticket 05's review, P2: a project document value's date is its document's, as the Documents API dates it, so
    the first-listed values the quote check excuses by that date cannot drift with it. It reads the project's
    recorded document list, so it leaves out the PPSD templates, which belong to no project, and the French plan
    template, whose project's list the fixture does not record."""
    assert value["date"] == documents_api_date(value["document"], value["project"])


@pytest.mark.parametrize("value", [v for v in VALUES if "days_between" in v], ids=lambda value: value["id"])
def test_a_day_count_matches_the_two_dates_it_was_counted_between(value):
    start, end = (datetime.date.fromisoformat(str(BY_ID[name]["value"])) for name in value["days_between"])
    assert (end - start).days == value["value"]


@pytest.mark.parametrize("value", [v for v in VALUES if "months_between" in v], ids=lambda value: value["id"])
def test_a_month_count_matches_the_two_dates_it_was_counted_between(value):
    """A month is 365.25 / 12 = 30.4375 days, and the count is rounded to the nearest month (ticket 22)."""
    start, end = (datetime.date.fromisoformat(str(BY_ID[name]["value"])) for name in value["months_between"])
    assert round((end - start).days * 12 / 365.25) == value["value"]


AWARD_NOTICE_BIDS = TRUTH["award_notice_bids"]


@pytest.mark.parametrize("name", sorted(AWARD_NOTICE_BIDS))
def test_each_bid_of_an_award_notice_is_in_its_notice_in_the_order_the_ground_truth_gives(name):
    """Each bid's name (with its STEP supplier ID in brackets when it has one), its prices and its reason sit in
    the recorded notice's HTML after the bid before it, and each section's heading before its first bid."""
    notice = AWARD_NOTICE_BIDS[name]
    text = squash(str(resolve(notice["record"], notice["at"])))
    headings = {"awarded": "AwardedBidder(s):", "evaluated": "EvaluatedBidder(s):", "rejected": "RejectedBidder(s):"}
    at, section = 0, None
    for bid in notice["bids"]:
        if bid["section"] != section:
            section = bid["section"]
            at = text.index(headings[section], at)
        written = bid["name"] + (f" ({bid['id']})" if bid["id"] else "")
        at = text.index(squash(written), at)
        for part in (f"BidPriceatOpening<br/>{notice['currency']}{squash(bid['opening'])}<br/>",
                     f"EvaluatedBidPrice<br/>{notice['currency']}{squash(bid['evaluated'])}<"):
            at = text.index(part, at)
        if bid["reason"]:
            at = text.index(squash(f"Reason for Rejection<br/>{bid['reason']}"), at)


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
    """A package whose plan row says Canceled is listed as canceled, never as still open, so the two are counted apart."""
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


# ── Advertised again (ticket 28) ─────────────────────────────────────────

REBIDDING = TRUTH["rebidding"]


def test_the_comparables_advertised_again_are_the_three_canceled_ones():
    """Of the 52 comparables, only the canceled have a label: no award followed their notices, and their agency's
    latest plan marks them Canceled. The still-open four had bids due days before the as-of date."""
    assert REBIDDING["advertised_again"] == sorted(c["reference"] for c in CANCELED)
    assert (REBIDDING["n"], REBIDDING["m"]) == (len(CANCELED), len(COMPARABLES))
    assert REBIDDING["past_total"] == len(SIGNED) + len(STILL_OPEN) == TRUTH["past_range"]["comparables"]
    assert {c["canceled_in"] for c in CANCELED} == {REBIDDING["canceled_in"]}
    listed = resolve("api/documents/P156634.json", f"documents.D{REBIDDING['canceled_in_document_id']}")
    assert listed["docdt"][:10] == REBIDDING["canceled_plan_date"].isoformat() == REBIDDING["canceled_in"][-10:]
    assert all(c["bids_due"] > REBIDDING["as_of"] - datetime.timedelta(days=30) for c in STILL_OPEN)


def test_before_the_canceled_plan_only_the_packages_long_past_their_bids_due_date_had_no_award():
    wait = datetime.timedelta(days=548)  # config/thresholds.toml, rebidding.no_award_after_days
    for reference, due in REBIDDING["bids_due"].items():
        notice = next(n for n in recorded_notices() if n["id"] == next(c["notice"] for c in CANCELED if c["reference"] == reference))
        assert notice["submission_deadline_date"][:10] == due.isoformat()
    waited = sorted(reference for reference, due in REBIDDING["bids_due"].items() if due + wait <= REBIDDING["before_the_plan"])
    assert waited == REBIDDING["advertised_again_before_the_plan"]
    assert REBIDDING["before_the_plan"] < REBIDDING["canceled_plan_date"]


def test_no_comparable_has_two_invitations_for_bids_under_its_step_reference():
    invitations = [reference_of(n, "bid_reference_no") for n in recorded_notices() if n["notice_type"] == "Invitation for Bids"]
    twice = [c["reference"] for c in COMPARABLES if invitations.count(c["reference"]) > 1]
    assert len(twice) == REBIDDING["same_reference_notices"]


def test_the_one_reason_in_words_is_in_the_canceled_package_s_own_invitation_for_bids():
    """No award notice of a comparable says why it was advertised again; OP00083890 says its Request for Bids was
    cancelled, after "2020." with no space."""
    notice = next(n for n in recorded_notices() if n["id"] == REBIDDING["quote_notice"])
    assert notice["notice_type"] == "Invitation for Bids"
    assert reference_of(notice, "bid_reference_no") == REBIDDING["quote_reference"] in REBIDDING["advertised_again"]
    assert word_for_word(REBIDDING["quote"], notice["notice_text"])
    assert f"2020.{REBIDDING['quote']}" in notice["notice_text"]
    awards = [n for c in COMPARABLES for n in notices_for(c["reference"]) if n["notice_type"] == "Contract Award"]
    assert awards and not [n["id"] for n in awards if re.search(r"cancell?ed|re-?advertis", n["notice_text"] or "", re.I)]


def test_with_review_type_prior_no_comparable_was_advertised_again():
    narrower = [c for c in COMPARABLES if c.get("review_type") == CRITERIA["narrower_review_type"]]
    assert len([c for c in narrower if c["reference"] in REBIDDING["advertised_again"]]) == REBIDDING["narrower_advertised_again"]


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


# ── The stress shelf (ticket 18) ──────────────────────────────────────────

SHELF = TRUTH["stress_shelf"]


def shelf_quotes():
    """Every quote the stress shelf's ground truth places on a PDF page, as (id, document, page, quote)."""
    annex, plan, report, longest = (SHELF[key] for key in ("pad_risk_annex", "long_plan", "french_report",
                                                           "longest_pad"))
    found = [("annex-title", annex["document"], annex["title"]["pdf_page"], annex["title"]["quote"])]
    found += [(f"annex-{rating['risk']}", annex["document"], rating["pdf_page"], rating["quote"])
              for rating in annex["ratings"]]
    found += [("plan-table", plan["document"], plan["table_starts"]["pdf_page"], plan["table_starts"]["quote"]),
              ("report-paragraph", report["document"], report["first_paragraph"]["pdf_page"],
               report["first_paragraph"]["quote"]),
              ("longest-pad", longest["document"], longest["quote"]["pdf_page"], longest["quote"]["quote"])]
    return found


@pytest.mark.parametrize(("name", "document", "number", "quote"), shelf_quotes(), ids=lambda value: str(value))
def test_each_stress_shelf_quote_is_word_for_word_on_its_page(name, document, number, quote):
    assert word_for_word(quote, page(document, number)), f"{name}: {quote!r} is not on page {number} of {document}"


def test_the_risk_annex_text_layer_count_is_one_rated_risk_per_rating_row_and_its_pages_are_the_annex():
    annex = SHELF["pad_risk_annex"]
    assert len(annex["ratings"]) == annex["risks"]
    assert {rating["pdf_page"] for rating in annex["ratings"]} <= set(range(annex["first_pdf_page"],
                                                                             annex["last_pdf_page"] + 1))
    pages = fmt.pages(RECORDED / f"{annex['document']}.pages.txt")
    assert len(pages) == annex["pdf_pages"]
    assert [number for number, text in enumerate(pages, 1) if not text.strip()] == annex["empty_pages"]
    assert "Annex 5" in pages[annex["last_pdf_page"]]  # the next annex starts on the page after


def test_the_long_plan_lists_its_activities_and_the_documents_have_the_pages_the_ground_truth_says():
    plan = SHELF["long_plan"]
    text = fmt.read(RECORDED / f"{plan['document']}.txt").body
    references = set(re.findall(r"\b[A-Z]{2}-[A-Z]+-\d+-(?:CW|GO|CS|NC)-[A-Z]+(?:-2)?\b", text))
    assert len(references) == plan["activity_references"]
    assert sum(reference.endswith("-2") for reference in references) == plan["with_a_second_issue"]
    for key in ("long_plan", "french_report", "longest_pad"):
        assert len(fmt.pages(RECORDED / f"{SHELF[key]['document']}.pages.txt")) == SHELF[key]["pdf_pages"], key
    # The documents the run reads are projects' documents, in a folder per project. The PPSD templates and
    # guidance (documents/guidance, ticket 36) belong to no project, and the run never reads them.
    recorded = [len(fmt.pages(path)) for path in RECORDED.glob("documents/P*/*.pages.txt")]
    assert max(recorded) == SHELF["over_parser_limit"]["longest_pages"] < 500


def test_each_similar_experience_quote_is_one_paragraph_of_its_notice():
    case = SHELF["similar_experience"]
    for notice in case["notices"]:
        assert word_for_word(notice["quote"], str(resolve(case["record"], notice["at"]))), notice["notice"]


def test_each_slice_project_is_in_the_recorded_file_with_its_board_date_and_largest_sector():
    case = SHELF["slice_projects"]
    projects = resolve(case["record"], "projects")
    assert len(case["projects"]) == case["count"]
    for listed in case["projects"]:
        project = projects[listed["project"]]
        shares = {}
        for major in project.get("major_sectors") or []:
            sector = major["major_sector"]
            shares[sector["major_sector_code"]] = sum(float(s["sector_percent"]) for s in sector.get("sectors") or [])
        assert project["boardapprovaldate"][:10] == listed["board_date"].isoformat(), listed["project"]
        assert max(shares, key=shares.get) == listed["largest"], listed["project"]
        board = listed["board_date"]
        assert 2012 <= (board.year + 1 if board.month >= 7 else board.year) <= 2025


def test_the_pad_disclosure_date_is_in_its_fiscal_year():
    case = SHELF["pad_disclosed"]
    assert resolve(case["record"], case["at"]) == case["value"]
    disclosed = datetime.date.fromisoformat(case["value"][:10])
    assert (disclosed.year + 1 if disclosed.month >= 7 else disclosed.year) == case["fiscal_year"]
