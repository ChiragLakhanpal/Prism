"""The verifier's checks 4, 5 and 6 at seam 3 (ticket 24): a question goes in over HTTP, and the answer that
streams back has passed all six checks.

The scripted agent replays each case's recording (tests/fixtures/agent/cases.toml), and the judge of check 4
answers from the case's recorded judge answer (tests/fixtures/agent/judged), counting its calls. Expected
values come from the ICR of October 10, 2019 and ISR 7 (tests/ground_truth/values.toml), never from the code
under test.
"""

import re
import tomllib
from pathlib import Path

from scripted_answers import ask

TRUTH = {entry["id"]: entry for entry in tomllib.loads(
    (Path(__file__).parent / "ground_truth" / "values.toml").read_text())["value"]}
ICR_54 = "strata.gold.passage:31525018/v1/54"
COPY = (Path(__file__).resolve().parents[1] / "web" / "src" / "copy.ts").read_text()


def copy_reason(code):
    """A removal reason's two forms from the copy file (web/src/copy.ts, removed.reasons)."""
    found = re.search(rf'\n      {code}: \{{\s*item: "([^"]*)",\s*joined: "([^"]*)",?\s*\}}', COPY)
    return {"item": found.group(1), "joined": found.group(2)}


# ── Check 4: each sentence follows from its sources ───────────────────────

def test_a_sentence_its_passage_does_not_support_is_removed_after_one_call_to_the_judge(fixture_db):
    asked = ask(fixture_db, "p130164-unsupported-summary")

    [removed] = asked.of("removed")
    assert removed["sentence"] == "The completion report blamed the contractors for the rebidding."
    assert removed["reason"] == "not_supported"
    assert copy_reason("not_supported") == {"item": "The sources it cites do not say this.",
                                            "joined": "the sources it cited do not say that"}
    # One batched call, holding only the sentence checks 1 to 3 could not prove, with its passage's words.
    [call] = asked.judge.calls
    assert [question.sentence for question in call] == [removed["sentence"]]
    assert [source.evidence_id for source in call[0].sources] == [ICR_54]
    assert "108 of 328 cases had to go through rebidding" in call[0].sources[0].text
    assert len(asked.of("sentence")) == 3


def test_the_judge_is_not_called_when_checks_1_to_3_prove_every_sentence(fixture_db):
    asked = ask(fixture_db, "p130164-rebidding")

    assert asked.judge.calls == []
    assert asked.of("removed") == []
    checks = asked.of("checks")[0]
    assert checks["checks_run"] == [1, 2, 3, 4, 5, 6]
    assert checks["judge"] == {"called": False, "responded": None, "judged": 0, "followed": 0, "unjudged": 0,
                               "proven": 3}
    assert [step for step in asked.of("step") if step["kind"] == "judge"] == []


def test_a_quote_of_only_a_number_and_an_ordinal_go_to_the_judge_which_removes_them(fixture_db):
    """Ticket 13's verify O1: a quote of only "108" is on its page, and backs any meaning; and ordinals such
    as "the third time" are not read as numbers (ticket 13's parked decision 6). Checks 1 to 3 keep both, so
    neither is proven, and the judge decides, in the same single call."""
    asked = ask(fixture_db, "p130164-number-only-quote")

    assert [(item["sentence"], item["reason"]) for item in asked.of("removed")] == [
        ('Only "108" works contracts were signed in all.', "not_supported"),
        ("The works contracts were advertised for the third time.", "not_supported")]
    assert len(asked.judge.calls) == 1 and len(asked.judge.calls[0]) == 2
    judge = [step for step in asked.of("step") if step["kind"] == "judge"]
    assert [step["status"] for step in judge] == ["running", "done"] and judge[0]["count"] == 2


def test_when_the_judge_does_not_respond_the_sentences_it_had_to_judge_are_removed_and_the_rest_stand(fixture_db):
    asked = ask(fixture_db, "p130164-judge-no-response")

    [removed] = asked.of("removed")
    assert (removed["sentence"], removed["reason"]) == (
        "The completion report blamed the contractors for the rebidding.", "judge_unavailable")
    assert len(asked.of("sentence")) == 3
    judge = asked.of("checks")[0]["judge"]
    assert (judge["called"], judge["responded"], judge["judged"], judge["unjudged"]) == (True, False, 1, 1)


def test_when_the_judge_does_not_respond_and_every_sentence_needed_it_nothing_is_shown_unchecked(fixture_db):
    asked = ask(fixture_db, "p130164-summaries-judge-no-response")

    assert asked.of("sentence") == []
    assert {item["reason"] for item in asked.of("removed")} == {"judge_unavailable"}
    checks = asked.of("checks")[0]
    assert checks["sentences"]["kept"] == 0 and checks["judge"]["responded"] is False
    assert [kind for kind, _ in asked.parsed if kind == "error"] == []


def test_an_answer_that_checks_1_to_3_prove_after_find_comparables_counts_what_the_check_line_reads(fixture_db):
    """The ticket's check line: "Checked: N of N numbers match records; M of M quotes are on their pages. Not
    checked: whether these are the right comparables." The screen reads every count from this event."""
    asked = ask(fixture_db, "ke-nwwda-541055-past-range")

    assert asked.judge.calls == [] and asked.of("removed") == []
    checks = asked.of("checks")[0]
    assert checks["shown"] == {"numbers": {"total": 5, "matched": 5}, "dates": {"total": 0, "matched": 0},
                               "quotes": {"total": 2, "found": 2}, "judged": 0, "proven": 3}
    assert checks["tools"] == ["find_comparables"] and checks["lessons_cited"] is False


def test_when_check_6_cannot_ask_which_reports_disagree_every_sentence_citing_the_project_is_removed(fixture_db):
    asked = ask(fixture_db, "p130164-disagreements-unavailable")

    assert asked.of("sentence") == []
    assert [(item["reason"], item["reasons"][-1]["text"]) for item in asked.of("removed")] == [
        ("disagreements_unavailable", "P130164")] * 3
    assert copy_reason("disagreements_unavailable")["item"] == (
        "I couldn't check whether another report disagrees with its sources.")
    assert asked.judge.calls == []


def test_sentences_that_fail_different_checks_are_each_removed_with_the_reason_of_the_check_they_failed(fixture_db):
    asked = ask(fixture_db, "p130164-several-removed")

    assert [item["reason"] for item in asked.of("removed")] == [
        "number_not_in_records", "advice_without_lesson_or_comparable", "not_supported"]
    assert [len(call) for call in asked.judge.calls] == [1]


# ── Check 5: no advice without a lesson or a comparable ───────────────────

def test_advice_that_cites_neither_a_lesson_nor_a_comparable_is_removed_and_never_judged(fixture_db):
    asked = ask(fixture_db, "p130164-advice-without-lesson")

    [removed] = asked.of("removed")
    assert (removed["sentence"], removed["reason"]) == (
        "Base your works estimates on market rates before you advertise.", "advice_without_lesson_or_comparable")
    assert copy_reason("advice_without_lesson_or_comparable")["item"] == (
        "It gave advice without citing a lesson or a comparable package.")
    assert asked.judge.calls == []
    assert asked.of("checks")[0]["advice"] == {"total": 1, "cited": 0}


def test_advice_that_cites_a_comparable_passes_check_5_and_goes_to_the_judge(fixture_db):
    asked = ask(fixture_db, "ke-nwwda-541055-advice")

    assert asked.of("removed") == []
    assert [sentence["kind"] for sentence in asked.of("sentence")] == ["record", "record", "record", "advice"]
    assert [[question.sentence for question in call] for call in asked.judge.calls] == [
        ["Plan for longer than the 1.5 months the plan allows."]]
    checks = asked.of("checks")[0]
    assert checks["advice"] == {"total": 1, "cited": 1}
    assert (checks["shown"]["judged"], checks["shown"]["proven"]) == (1, 3)


# ── Check 6: a claim resting on one side of a disagreement shows both ─────

def test_a_claim_resting_on_isr_7_s_rating_streams_with_the_icr_paragraph_78_disagreement_attached(fixture_db):
    """The agent never asked get_disagreements, so its draft left the ICR out. ISR 7 (values.toml isr-7-date,
    isr-7-rating) and ICR paragraph 78 (icr-para-78, PDF page 27) both reach the screen, the ICR's paragraph as
    a source whose marker opens."""
    isr_7, paragraph_78 = "strata.gold.passage:26733307/v1/s4", "strata.gold.passage:31525018/v1/78"
    asked = ask(fixture_db, "p130164-isr-7-rating")

    [sentence] = asked.of("sentence")
    assert sentence["evidence_ids"] == [isr_7]
    [card] = asked.of("disagreement")
    assert (card["after"], card["attached_by_verifier"], card["changes_answer"]) == (sentence["index"], True, True)
    isr, icr = card["sides"]
    assert (isr["evidence_id"], isr["made_at"], isr["value"], isr["leaned"]) == (
        isr_7, TRUTH["isr-7-date"]["value"].isoformat(), TRUTH["isr-7-rating"]["value"], False)
    assert (icr["evidence_id"], icr["quote"], icr["leaned"]) == (paragraph_78, TRUTH["icr-para-78"]["value"], True)
    sources = {evidence["id"]: evidence for evidence in asked.of("evidence")}
    assert sources[paragraph_78]["row"]["pdf_page"] == TRUTH["icr-para-78"]["pdf_page"]
    assert TRUTH["icr-para-78"]["value"] in sources[paragraph_78]["row"]["text"]
    assert asked.of("checks")[0]["disagreements"] == {"disputed": 1, "shown": 1, "attached": 1}
    fetched = [step for step in asked.of("step") if step["kind"] == "disagreement"]
    assert [step["status"] for step in fetched] == ["running", "done"]
    # The events come in the answer contract's order.
    kinds = [kind for kind, _ in asked.parsed]
    assert kinds.index("evidence") < kinds.index("disagreement") < kinds.index("checks")


def test_a_draft_that_showed_both_sides_gets_the_same_card_as_an_info_note_when_it_changes_nothing(fixture_db):
    asked = ask(fixture_db, "p130164-both-sides")

    [card] = asked.of("disagreement")
    assert (card["after"], card["attached_by_verifier"], card["changes_answer"]) == (0, False, False)
    assert [side["evidence_id"] for side in card["sides"]] == [
        "strata.gold.passage:26733307/v1/s4", "strata.gold.passage:31525018/v1/78"]
    assert asked.of("checks")[0]["disagreements"] == {"disputed": 1, "shown": 1, "attached": 0}
    # The agent asked get_disagreements itself, so check 6 had nothing to fetch.
    assert [step for step in asked.of("step") if step["kind"] == "disagreement"] == []
