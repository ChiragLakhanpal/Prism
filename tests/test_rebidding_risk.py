"""rebidding_risk at seam 2: how many comparable packages were advertised again, and why, called by name
through the tool registry on the fixture database.

The expected counts come from tests/ground_truth/values.toml's [rebidding] entry, counted by hand from the
recorded notices, awards and plans (tests/test_ground_truth_values.py checks each against the recorded
files), never the way the tool counts. On the fixture only the three canceled comparables were advertised
again, no award notice gives a reason, and the one reason in words is in an Invitation for Bids.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.dbx import Viewer
from strata.lakehouse import ground_truth
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
REBIDDING = TRUTH["rebidding"]
REF = REBIDDING["step_reference"]
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rebidding(engine, **arguments):
    arguments.setdefault("as_of", REBIDDING["as_of"].isoformat())
    return registry.call("rebidding_risk", arguments, registry.Context(engine=engine, viewer=ANA))


def test_on_the_fixture_three_of_the_52_comparables_were_advertised_again_as_the_direct_count_says(engine):
    result = rebidding(engine, step_reference=REF)

    assert (result["n"], result["m"]) == (REBIDDING["n"], REBIDDING["m"])
    assert sorted(row["step_reference"] for row in result["rows"]) == REBIDDING["advertised_again"]
    assert result["summary"]["n"] == REBIDDING["n"] and result["summary"]["m"] == REBIDDING["m"]


def test_the_nightly_run_records_how_many_packages_each_label_source_names_in_strata_ops(engine):
    """The fixture's nightly run counted them on October 23, 2026: the same counts as the ground-truth SQL, which
    counts straight from the notices, contracts and plan rows."""
    case = ground_truth.read(ROOT / "tests" / "ground_truth" / "rebidding_label_counts.sql")
    direct = engine.run(case.sql, case.params)
    held = engine.run("SELECT source, count, denominator, as_of FROM strata.ops.rebidding_labels "
                      "WHERE run_id = :run_id ORDER BY source", {"run_id": "fixture"})

    assert [row[:3] for row in held.rows] == [tuple(row) for row in direct.rows]
    assert {row[0] for row in held.rows} == {"no_award", "same_reference", "canceled_row", "any"}
    assert {row[3] for row in held.rows} == {dt.date.fromisoformat(case.params["as_of"])}


def test_each_reason_code_the_tool_may_group_under_has_its_heading_in_the_copy_file():
    """A reason code is renamed in the registry, the tool and the copy together (config/tools.toml)."""
    from strata import config
    from strata.tools import find_comparables

    codes = set(config.load_tools()["rebidding_risk"].result.reasons) - set(find_comparables.REASONS)
    copy = (ROOT / "web" / "src" / "copy.ts").read_text()
    rebid = copy[copy.index("\n  rebid: {"):]
    headings = rebid[rebid.index("reasons: {"):rebid.index("} as Record<string, string>", rebid.index("reasons: {"))]
    assert {reason.code for reason in config.load_rebidding_reasons()} <= codes
    assert [code for code in sorted(codes) if f"{code}:" not in headings] == []


def test_the_mocked_answers_say_they_are_mocks_and_use_none_of_the_ticket_s_or_the_blueprint_s_figures():
    """The model shown and the model that did no better are not in the fixture, so the screens' mocks for them are
    labeled, made up, and never the illustrative "6 of 37" or "about 2 in 10" (spec, "Wireframe numbers")."""
    import json

    mocks = sorted((ROOT / "tests" / "fixtures" / "api").glob("*mock*.json"))
    assert {path.name for path in mocks} >= {"rebidding-mock-model-shown.json", "rebidding-mock-not-better.json"}
    for path in mocks:
        body = json.loads(path.read_text())
        assert "made up" in body["mock"], path.name
        if body.get("tool") == "rebidding_risk":
            assert (body["n"], body["m"]) != (6, 37) and body["m"] not in (37, 118), path.name
            assert body["model"]["in10"] != 2, path.name


def test_the_one_reason_in_words_is_quoted_word_for_word_with_its_notice(engine):
    """No award notice gives a reason on the fixture: the reason is the canceled package's own Invitation for
    Bids, so here a notice, not an award notice, gives the quote."""
    rows = {row["step_reference"]: row for row in rebidding(engine, step_reference=REF)["rows"]}

    quoted = rows[REBIDDING["quote_reference"]]
    assert quoted["row_kind"] == "quote" and quoted["reason_code"] == "process_canceled"
    assert quoted["quote"] == {"text": REBIDDING["quote"], "lang": "en", "notice_id": REBIDDING["quote_notice"]}
    assert [(item["record_kind"], item["reference"]) for item in quoted["evidence"]] == [("notice", REBIDDING["quote_notice"])]
    assert quoted["evidence_id"] == quoted["evidence"][0]["evidence_id"]


AWARD_NOTICE = "OP90000377"  # made up: a Contract Award notice no recorded file holds


@pytest.fixture
def with_an_award_notice(fixture_db, tmp_path):
    """A copy of the fixture with one more notice for KE-KIMAWASCO-377450-CW-RFB, one of the three advertised again:
    a Contract Award notice of June 3, 2024 whose text says all bids were rejected (ticket 28's review, follow-up
    4)."""
    import shutil

    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    day = dt.date(2024, 6, 3)
    with DuckDBEngine.open(target) as copy:
        copy.insert_rows("strata.gold.notice", ("notice_id", "notice_type", "notice_date", "step_reference", "project_id",
                                                "public_from"),
                         [(AWARD_NOTICE, "Contract Award", day, "KE-KIMAWASCO-377450-CW-RFB", "P156634", day)])
        copy.insert_rows("strata.silver.notices", ("notice_id", "notice_type", "notice_text", "notice_language",
                                                   "contact_details_removed", "page_hash", "fetched_at", "public_from"),
                         [(AWARD_NOTICE, "Contract Award", "Bids were opened on 3 March 2024. All bids were rejected.",
                           "English", False, "not-a-real-hash", dt.datetime(2024, 6, 3, tzinfo=dt.UTC), day)])
    with DuckDBEngine.open(target, read_only=True) as engine:
        yield engine


def test_an_award_notice_that_says_why_is_quoted_and_cited_as_section_5_cites_it(with_an_award_notice):
    """Ticket 28's review, follow-ups 4 and 6: the award notice's sentence is quoted word for word, and the row cites
    the notice as strata.gold.notice:{id}, the id section 5's rejected bids cite it by, so one record keeps one
    marker. The drawer opens it with that sentence highlighted."""
    from strata.server import evidence

    rows = {row["step_reference"]: row for row in rebidding(with_an_award_notice, step_reference=REF)["rows"]}
    quoted = rows["KE-KIMAWASCO-377450-CW-RFB"]
    opened = evidence.read(with_an_award_notice, quoted["evidence_id"], REBIDDING["as_of"])

    assert (quoted["row_kind"], quoted["reason_code"]) == ("quote", "all_bids_rejected")
    assert quoted["quote"] == {"text": "All bids were rejected.", "lang": "en", "notice_id": AWARD_NOTICE}
    assert [(item["record_kind"], item["evidence_id"]) for item in quoted["evidence"]] == [
        ("award_notice", f"strata.gold.notice:{AWARD_NOTICE}")]
    assert quoted["evidence_id"] == f"strata.gold.notice:{AWARD_NOTICE}"
    assert [field["value"] for field in opened["row"]["fields"] if field.get("highlight")] == ["All bids were rejected."]


@pytest.mark.parametrize("text, found", [
    ("Bids were opened on 3 March 2024. All bids were rejected.", ("all_bids_rejected", "All bids were rejected.")),
    ("Reason for Rejection: Non Responsive", None),  # one bidder's reason in an award notice, not why it went again
    ("Late bids will be rejected.", None),  # an Invitation for Bids' own rule
], ids=["all-rejected", "a-bidder-s-reason", "a-rule-for-late-bids"])
def test_a_notice_gives_a_reason_for_advertising_again_only_when_a_sentence_says_one(text, found):
    from strata.estimates import rebidding as labels

    assert labels.reason_in(text) == found


def test_the_drawer_opens_a_reason_s_notice_with_its_page_and_a_plan_row_with_its_plan(engine):
    """Ticket 28's design review, F1: a notice opened from a reason links to its page on the World Bank's site, as a
    comparable package's notice does, and a plan row to Check a plan on its plan version, as the trail's does."""
    from strata.config import load_sources
    from strata.server import evidence

    notice = evidence.read(engine, f"strata.silver.notices:{REBIDDING['quote_notice']}", REBIDDING["as_of"])
    plan = evidence.read(engine, f"strata.silver.plan_rows:{REBIDDING['canceled_in_document_id']}/KE-KIMAWASCO-157517-CW-RFB",
                         REBIDDING["as_of"])

    assert notice["row"]["url"] == load_sources()["notices"].record_url.replace("{id}", REBIDDING["quote_notice"])
    assert plan["row"]["plan_href"] == (f"/projects/{plan['row']['source']['project_id']}/procurement/"
                                        f"kilifi-mariakani-water-and-sewerage-company-ltd/"
                                        f"{REBIDDING['canceled_plan_date'].isoformat()}#KE-KIMAWASCO-157517-CW-RFB")


def test_the_other_two_cite_their_canceled_plan_row_with_its_process_status_word_for_word(engine):
    rows = {row["step_reference"]: row for row in rebidding(engine, step_reference=REF)["rows"]}

    for reference in set(REBIDDING["advertised_again"]) - {REBIDDING["quote_reference"]}:
        row = rows[reference]
        assert (row["row_kind"], row["reason_code"], row["process_status"]) == ("canceled_row", "canceled_row", "Canceled")
        [plan_row] = row["evidence"]
        assert plan_row["record_kind"] == "plan_row" and plan_row["date"] == REBIDDING["canceled_plan_date"].isoformat()
        assert row["source"]["plan_document_id"] == REBIDDING["canceled_in_document_id"]
        assert set(row["label_sources"]) == {"no_award", "canceled_row"}


def test_the_groups_put_the_most_packages_first_and_rows_follow_them(engine):
    result = rebidding(engine, step_reference=REF)

    assert [(group["reason_code"], group["count"]) for group in result["groups"]] == [("canceled_row", 2), ("process_canceled", 1)]
    assert [row["step_reference"] for row in result["rows"]] == [ref for group in result["groups"] for ref in group["step_references"]]
    assert [row["rank"] for row in result["rows"]] == [1, 2, 3]


def test_it_counts_the_canceled_comparables_the_past_range_leaves_out_and_says_so(engine):
    result = rebidding(engine, step_reference=REF)

    assert result["past_range_total"] == REBIDDING["past_total"]
    assert result["denominator_reason"] == "canceled_included"
    assert result["coverage"]["used"] == REBIDDING["m"]
    assert "canceled" not in {entry["reason"] for entry in result["coverage"]["not_used"]}


def test_with_review_type_prior_none_was_advertised_again_and_there_are_too_few_for_a_model(engine):
    result = rebidding(engine, step_reference=REF, review_type=TRUTH["comparables"]["narrower_review_type"])

    assert (result["n"], result["m"]) == (REBIDDING["narrower_advertised_again"], TRUTH["comparables"]["narrower_count"])
    assert result["rows"] == [] and result["groups"] == [] and result["abstention"] is None
    assert result["model"]["shown"] is False and result["model"]["not_shown_reason"] == "too_few"
    assert result["model"]["in10"] is None


def test_a_plan_row_marked_canceled_after_the_as_of_date_does_not_count(engine):
    """As of December 31, 2024 the March 19, 2025 plan was not public: two packages had waited long enough with no
    award, and the third had not. KE-NWWDA-541055-CW-RFB was in no plan yet, so the call gives the comparables'
    default criteria itself, as for a package planned from a sentence."""
    criteria = TRUTH["comparables"]
    result = rebidding(engine, method="Request for Bids", category="Works", country="KE",
                       notice_from=criteria["first_notice_from"].isoformat(), as_of=REBIDDING["before_the_plan"].isoformat())

    assert sorted(row["step_reference"] for row in result["rows"]) == REBIDDING["advertised_again_before_the_plan"]
    assert all(row["process_status"] is None and "canceled_row" not in row["label_sources"] for row in result["rows"])
    assert {row["reason_code"] for row in result["rows"]} <= {"no_award", "process_canceled"}
