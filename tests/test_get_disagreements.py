"""get_disagreements at seam 2, the tool contract (ticket 20).

The tool is called by name through the registry (config/tools.toml), as a viewer, with an optional
as-of date. For a subject it returns each disagreement with both sides in the order written, the side
Strata leans on, the ladder's rule, and what changes if you keep the other, plus the trajectories and
the count of assertions the run rejected. Expected values come from tests/ground_truth/values.toml,
never from the code.
"""

import datetime as dt
import re
import shutil
import tomllib
from pathlib import Path

import pytest

from strata import config
from strata.dbx import Viewer
from strata.knowledge import assertions
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
ISR_7 = "strata.gold.passage:26733307/v1/s4#P130164/pdo_progress"
PARAGRAPH_78 = "strata.gold.passage:31525018/v1/78#P130164/pdo_progress"


def value(key: str):
    return TRUTH[key]["value"]


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def get_disagreements(engine, **arguments):
    return registry.call("get_disagreements", arguments, registry.Context(engine=engine, viewer=ANA))


def about(result, attribute: str) -> list[dict]:
    return [row for row in result["rows"] if row["attribute"] == attribute]


# ── The showcase disagreement ────────────────────────────────────────────

def test_isr_7_and_the_icrs_paragraph_78_come_back_as_one_disagreement_leaning_on_the_icr(engine):
    """Criterion 1: both sides in the order written, Strata leaning on the ICR under the outcome-judgment rule,
    and what changes if you keep ISR 7."""
    result = get_disagreements(engine, subject_id="P130164")

    [row] = about(result, "pdo_progress")
    isr_7, paragraph = row["sides"]
    assert [isr_7["assertion_id"], paragraph["assertion_id"]] == [ISR_7, PARAGRAPH_78]
    assert (row["lean_assertion_id"], row["other_assertion_id"], row["rule_id"]) == (PARAGRAPH_78, ISR_7, "outcome")
    assert row["evidence_id"] == f"strata.gold.disagreement:{row['disagreement_id']}"
    assert row["period"] == {"event": "mid_term_review", "start": value("mid-term-review").isoformat(),
                             "end": value("mid-term-review").isoformat()}
    # ISR 7 keeps the report's own field name and its rating, word for word.
    assert (isr_7["field_name"], isr_7["value"]) == ("Progress towards achievement of PDO", value("isr-7-rating"))
    assert (isr_7["made_at"], isr_7["evidence_tier"], isr_7["sequence"]) == (value("isr-7-date").isoformat(), "isr", 7)
    assert isr_7["evidence_id"] == "strata.gold.passage:26733307/v1/s4"
    assert isr_7["months_after_event"] == 3  # rated three months after the mid-term review (blueprint)
    assert (paragraph["quote"], paragraph["pdf_page"]) == (value("icr-para-78"), TRUTH["icr-para-78"]["pdf_page"])
    assert (paragraph["made_at"], paragraph["public_from"]) == (value("icr-date").isoformat(),
                                                                value("icr-disclosed").isoformat())
    assert (paragraph["evidence_tier"], paragraph["judgment"]) == ("icr", "unsatisfactory")
    # What the card names each side by and links it to: the paragraph as the report numbers it, and the
    # document's key in the source view's address (ticket 21). An ISR numbers no paragraphs.
    para = TRUTH["icr-para-78"]
    assert (paragraph["paragraph"], paragraph["paragraph_numbered"]) == (str(para["paragraph"]), True)
    assert paragraph["doc_key"] == para["document"].rsplit("/", 1)[1]
    assert (isr_7["paragraph_numbered"], isr_7["doc_key"]) == (False, f"isr-{value('isr-7-date').isoformat()}")
    assert row["if_you_keep"] == {"assertion_id": ISR_7, "attribute": "pdo_progress", "value": value("isr-7-rating"),
                                  "value_form": "rating", "judgment": "satisfactory",
                                  "field_name": "Progress towards achievement of PDO", "period_event": "mid_term_review"}


def test_isrs_1_to_13_come_back_as_a_trajectory_not_a_disagreement(engine):
    """Criterion 2: ISRs 1 to 9 Satisfactory, 10 and 11 Moderately Satisfactory, 12 and 13 Moderately
    Unsatisfactory."""
    result = get_disagreements(engine, subject_id="P130164")

    [trajectory] = [item for item in result["trajectories"] if item["attribute"] == "pdo_progress"]
    assert trajectory["field_name"] == "Progress towards achievement of PDO"
    assert [point["value"] for point in trajectory["points"]] == [value(f"isr-{n}-rating") for n in range(1, 14)]
    assert [(run["value"], run["first_sequence"], run["last_sequence"]) for run in trajectory["runs"]] == [
        (value("isr-1-rating"), 1, 9), (value("isr-10-rating"), 10, 11), (value("isr-12-rating"), 12, 13)]
    assert not any(side["evidence_tier"] == "isr" for row in result["rows"] for side in row["sides"]
                   if all(other["evidence_tier"] == "isr" for other in row["sides"]))


@pytest.mark.parametrize("as_of", ["2019-10-01", "2019-11-01"], ids=["before-the-icr-was-dated", "before-it-was-public"])
def test_before_the_icr_was_public_no_disagreement_comes_back_for_the_project(engine, as_of):
    """Criterion 3: the ICR is dated October 10, 2019 but became public on November 2, 2019, so as of
    either date before that, nothing disagrees with ISR 7. The ISRs' trajectory is still there."""
    result = get_disagreements(engine, subject_id="P130164", as_of=as_of)

    assert result["rows"] == []
    assert result["abstention"] is None
    assert [item["attribute"] for item in result["trajectories"] if item["attribute"] == "pdo_progress"]
    assert result["rejected"]["count"] == 0


def test_the_2023_reissue_of_the_icr_review_replaces_the_2020_version_for_current_answers(engine):
    """Criterion 6: today the efficiency disagreement rests on the re-issue (May 4, 2023), and no answer cites
    the March 27, 2020 version. As of a date between the two, the 2020 version was current, and it gave no
    efficiency rating, so nothing disagreed about efficiency."""
    today = get_disagreements(engine, subject_id="P130164")
    between = get_disagreements(engine, subject_id="P130164", as_of="2022-01-01")

    [efficiency] = about(today, "efficiency")
    assert [side["document_id"] for side in efficiency["sides"]] == ["31525018", "34056616"]
    assert efficiency["sides"][1]["made_at"] == value("icr-review-reissue-date").isoformat()
    assert efficiency["lean_assertion_id"] == efficiency["sides"][1]["assertion_id"]
    assert "31906731" not in {side["document_id"] for row in today["rows"] for side in row["sides"]}
    assert about(between, "efficiency") == []
    assert [row["attribute"] for row in between["rows"]] == ["pdo_progress"]


def test_a_disagreement_with_the_replaced_2020_icr_review_is_left_out_of_current_answers_and_counted(
        fixture_db, tmp_path):
    """Criterion 6 with the rule doing the work: the March 27, 2020 ICR Review agrees with every other source,
    so on a copy of the fixture its outcome rating is made to differ. As of a date between the two versions it
    disagrees with the ICR and with IEG's dataset row; from May 4, 2023, when the re-issue under the same report
    number became public, those disagreements are left out and the coverage line counts them."""
    copy = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, copy)
    outcome_2020 = "strata.gold.passage:31906731/v1/6.a#P130164/outcome"

    with DuckDBEngine.open(copy) as engine:
        engine.run("UPDATE strata.gold.assertion SET value = :rating, judgment = :judgment "
                   "WHERE assertion_id = :assertion_id",
                   {"rating": "Moderately Satisfactory", "judgment": "satisfactory", "assertion_id": outcome_2020})
        assertions.redetect(engine, ["P130164"], config.load_ladder())
        between = get_disagreements(engine, subject_id="P130164", attribute="outcome", as_of="2022-01-01")
        today = get_disagreements(engine, subject_id="P130164", attribute="outcome", as_of="2026-10-23")

    assert len(between["rows"]) == 2
    assert all(outcome_2020 in {side["assertion_id"] for side in row["sides"]} for row in between["rows"])
    assert between["coverage"]["not_used"] == []
    assert today["rows"] == []
    [not_used] = today["coverage"]["not_used"]
    assert (not_used["reason"], not_used["count"]) == ("replaced_by_later_version", 2)
    assert sorted(not_used["evidence_ids"]) == sorted(row["evidence_id"] for row in between["rows"])


@pytest.mark.parametrize("old, new, rule", [
    ('tiers = ["ieg", "icr", "isr", "pad"]', 'tiers = ["ieg", "isr", "icr", "pad"]', "outcome"),
    ('class = "judgment"', 'class = "moment"', "moment"),
], ids=["isrs-above-the-icr", "progress-as-a-moment"])
def test_reordering_the_ladder_in_its_config_flips_the_side_strata_leans_on(fixture_db, tmp_path, old, new, rule):
    """Criterion 4: an edited copy of config/evidence_ladder.toml, and no code change. Ranking ISRs above the
    ICR, or classing progress towards the PDO as a fact about a moment (which ISR 7 recorded at that moment),
    makes Strata lean on ISR 7 instead. The disagreements are decided again from the assertions held."""
    ladder = tmp_path / "evidence_ladder.toml"
    text = (ROOT / "config" / "evidence_ladder.toml").read_text()
    assert old in text
    ladder.write_text(text.replace(old, new, 1))
    copy = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, copy)

    with DuckDBEngine.open(copy) as engine:
        assertions.redetect(engine, ["P130164"], config.load_ladder(ladder))
        [row] = about(get_disagreements(engine, subject_id="P130164"), "pdo_progress")

    assert (row["lean_assertion_id"], row["other_assertion_id"], row["rule_id"]) == (ISR_7, PARAGRAPH_78, rule)
    assert row["if_you_keep"]["assertion_id"] == PARAGRAPH_78


def test_each_side_is_a_citable_record_and_a_side_read_from_a_passage_carries_its_words(engine, tmp_path):
    """The answer loop keeps each side under its own evidence id (config/tools.toml, nested_rows), so each
    side is cited and dated like a row, and a side that rests on a passage carries the passage's text, which
    holds its quote word for word. A record backs its own values and has no text. The trajectories and the
    rejected count come back as the summary record the agent cites them by."""
    result = get_disagreements(engine, subject_id="P130164", as_of="2026-10-23")
    tool = config.load_tools()["get_disagreements"]

    [row] = about(result, "pdo_progress")
    isr_7, paragraph = row["sides"]
    assert TRUTH["icr-para-78"]["quote"] in " ".join(paragraph["text"].split())
    assert "Progress towards achievement of PDO" in isr_7["text"]
    assert all(side["public_from"] <= result["as_of"] for row in result["rows"] for side in row["sides"])
    package = get_disagreements(engine, subject_id="KE-MOWASCO-307378-GO-RFB", as_of="2026-10-23")
    assert [side["text"] for side in package["rows"][0]["sides"]] == [None, None]
    assert result["summary"]["evidence_id"] == "strata.tools.get_disagreements:P130164@2026-10-23"
    assert (result["summary"]["trajectories"], result["summary"]["rejected"]) == (result["trajectories"],
                                                                                result["rejected"])
    unsourced = {**row, "sides": [{**isr_7, "evidence_id": None}, paragraph]}
    with pytest.raises(registry.ToolContractError, match="has no evidence id"):
        registry.check_contract(tool, {**result, "rows": [unsourced]})

    path = tmp_path / "tools.toml"
    path.write_text((ROOT / "config" / "tools.toml").read_text().replace('nested_rows = ["sides"]',
                                                                         'nested_rows = ["both_sides"]'))
    with pytest.raises(config.ConfigError, match="both_sides, which row_fields does not list"):
        config.load_tools(path)


# ── Ties between records ─────────────────────────────────────────────────

def sides_of(row) -> list[tuple[str, str]]:
    return [(side["form"], side["value"]) for side in row["sides"]]


def test_a_tie_between_records_goes_to_the_more_specific_source(engine):
    """Criterion 5, first tie: the October 9, 2026 plan dates KE-NWWDA-199461-GO-RFB's signing July 19, 2021,
    and the awards dataset and the award notice July 9. Every record was made at its moment, so the moment rule
    ranks them the same; a record of the signed contract is more specific than the package's plan row."""
    result = get_disagreements(engine, subject_id="KE-NWWDA-199461-GO-RFB", attribute="signed_on")

    found = {tuple(sorted(sides_of(row))): row for row in result["rows"]}
    plan = ("plan_row", value("plan-199461-signed").isoformat())
    contract = ("contract_record", value("award-199461-signed").isoformat())
    notice = ("award_notice", value("notice-199461-signed").isoformat())
    assert set(found) == {tuple(sorted((contract, plan))), tuple(sorted((notice, plan)))}
    for row in found.values():
        leaned = next(side for side in row["sides"] if side["assertion_id"] == row["lean_assertion_id"])
        assert (leaned["form"], row["rule_id"]) in {("contract_record", "tieSpecific"), ("award_notice", "tieSpecific")}
        assert row["period"]["event"] == "contract_signing"
        assert row["subject_kind"] == "package"
    plan_side = next(side for side in next(iter(found.values()))["sides"] if side["form"] == "plan_row")
    assert plan_side["evidence_id"].startswith("strata.silver.plan_rows:") and plan_side["made_at"] == "2026-10-09"
    # The earlier plan versions dated the signing the same way, and a later version replaced each of them.
    [not_used] = result["coverage"]["not_used"]
    assert (not_used["reason"], not_used["count"]) == ("replaced_by_later_version", 4)


def test_a_tie_between_equally_specific_records_goes_to_the_more_recent_one(engine):
    """Criterion 5, second tie: the awards dataset dates KE-MOWASCO-307378-GO-RFB's signing December 1, 2022
    and its award notice, published March 3, 2023, November 22, 2022. Both are records of the signed contract,
    equally specific, so the notice, made later, wins."""
    result = get_disagreements(engine, subject_id="KE-MOWASCO-307378-GO-RFB")

    [row] = result["rows"]
    assert sides_of(row) == [("contract_record", value("award-307378-signed").isoformat()),
                             ("award_notice", value("notice-307378-signed").isoformat())]
    notice = row["sides"][1]
    assert notice["made_at"] == value("notice-307378-date").isoformat()
    assert (row["lean_assertion_id"], row["rule_id"]) == (notice["assertion_id"], "tieRecent")
    assert notice["evidence_id"] == "strata.gold.notice:OP00216847"
    assert row["sides"][0]["evidence_id"] == "strata.gold.contract:1729599"
    assert (notice["paragraph"], notice["doc_key"]) == (None, None)  # a record has no paragraph


# ── The words the screens write from the result ─────────────────────────

def copy_keys(group: str) -> set[str]:
    """The keys of one group under copy.disagreement in the screens' copy file (web/src/copy.ts)."""
    text = (ROOT / "web" / "src" / "copy.ts").read_text()
    words = text[text.index("\n  disagreement: {"):]
    words = words[words.index(f"\n    {group}: {{"):]
    words = words[:words.index("\n    },")]
    return set(re.findall(r"^ {6}(\w+):", words, flags=re.MULTILINE))


def test_every_rule_tier_and_reason_the_tool_can_return_has_its_words_in_the_copy_file():
    """The tool returns the ladder's rule id, each side's evidence tier and its coverage line's reason codes,
    never a sentence (as check_plan returns reason codes); the copy file says them (brief 23, section 7.5;
    ticket 09's one copy sentence per reason code). Reordering the ladder changes which id comes back and
    needs no copy change; a new rule, tier or reason needs its words."""
    ladder = config.load_ladder()

    assert {rule.id for rule in ladder.rules} | set(ladder.ties) <= copy_keys("rule")
    assert set(ladder.tiers) <= copy_keys("written")
    assert set(config.load_tools()["get_disagreements"].result.reasons) <= copy_keys("reasons")


def test_the_rejected_assertion_is_counted_for_the_project(engine):
    """Criterion 7 at seam 2: the timeline states how many assertions the run left out (brief 23)."""
    result = get_disagreements(engine, subject_id="P130164")

    assert result["rejected"] == {"count": 1, "reasons": [{"reason": "quote_not_on_page", "count": 1}]}


def test_a_subject_strata_does_not_hold_is_an_abstention(engine):
    result = get_disagreements(engine, subject_id="P999999")

    assert result["rows"] == [] and result["trajectories"] == []
    assert result["abstention"] == {"reason": "unknown_subject", "subject_id": "P999999"}
