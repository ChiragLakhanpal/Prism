"""The verifier's checks 4, 5 and 6 at seam 3 (ticket 24): a question goes in over HTTP, and the answer that
streams back has passed all six checks.

The scripted agent replays each case's recording (tests/fixtures/agent/cases.toml), and the judge of check 4
answers from the case's recorded judge answer (tests/fixtures/agent/judged), counting its calls. Expected
values come from the ICR of October 10, 2019 and ISR 7 (tests/ground_truth/values.toml), never from the code
under test.
"""

import json
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
    found = re.search(rf'\n      {code}: \{{\s*item: "([^"]*)",\s*joined: "([^"]*)",?[^}}]*\}}', COPY)
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


def test_a_summary_that_cites_nothing_where_no_tool_abstained_is_removed_with_no_source_and_never_shown(fixture_db):
    """Ticket 24's verify F1, round 2: a summary that cites nothing used to skip check 4 and reach the screen. No
    tool abstained in this turn, so nothing could back it: check 2 removes it, with its copy-file reason, and the
    judge is still not called, because checks 1 to 3 prove the other three sentences."""
    asked = ask(fixture_db, "p130164-uncited-summary")

    assert [(item["sentence"], item["reason"], item["reasons"][0]["check"]) for item in asked.of("removed")] == [
        ("The contractors were to blame for the rebidding.", "no_source", 2)]
    assert copy_reason("no_source") == {"item": "It cited no source.", "joined": "it cited no source"}
    assert "The contractors were to blame for the rebidding." not in [item["text"] for item in asked.of("sentence")]
    assert len(asked.of("sentence")) == 3
    assert asked.judge.calls == []
    judge = asked.of("checks")[0]["judge"]
    assert (judge["called"], judge["judged"], judge["proven"]) == (False, 0, 3)
    # Check 2's step counts the sentence it removed for citing nothing (ticket 58), beside the two sources that came
    # back (the ICR's paragraphs 54 and 55); the kept sentences all cite one, so nothing on screen is uncited.
    checks = asked.of("checks")[0]
    assert checks["sources"] == {"total": 2, "returned": 2, "uncited": 1}
    assert "sources" not in checks["shown"] and "on_abstention" not in judge


NOT_PUBLIC = "That version of the plan was not yet public on the date you chose, so I did not check it."


def test_a_summary_that_cites_nothing_is_judged_once_against_the_abstention_a_tool_returned(fixture_db):
    """check_plan abstained (version_not_public), so the summary that says so may cite nothing: it goes to the
    judge, with that abstention as its only source, and stands when it says no more than the abstention."""
    asked = ask(fixture_db, "p156634-plan-not-yet-public")

    [call] = asked.judge.calls
    assert [question.sentence for question in call] == [NOT_PUBLIC]
    [source] = call[0].sources
    assert source.evidence_id == "check_plan:abstention"
    # The judge's instructions explain the name the verifier gives it, from one constant (ticket 24's review round
    # 3, follow-up 4).
    from strata.agent.judge import ABSTENTION, INSTRUCTIONS
    assert source.evidence_id.endswith(f":{ABSTENTION}") and f'":{ABSTENTION}"' in INSTRUCTIONS
    # The judge reads the abstention the agent got, with no date after the as-of date (ADR 0002): the plan became
    # public on October 9, 2026 (values.toml, the demo plan's plan_date), after October 1.
    got = json.loads(asked.agent.received[1]["input"][0]["output"])["abstention"]
    assert json.loads(source.text) == {"tool": "check_plan", "abstention": got}
    assert got["reason"] == "version_not_public" and "2026-10-09" not in source.text
    assert [item["text"] for item in asked.of("sentence")] == [NOT_PUBLIC]
    assert asked.of("removed") == []
    judge = asked.of("checks")[0]["judge"]
    assert (judge["called"], judge["judged"], judge["followed"], judge["proven"]) == (True, 1, 1, 0)
    # Ticket 58: the screen says no kept sentence cites a source, and that a model judged it against what a tool could
    # not answer, so the counts say how many did (only when any did, so other answers send what they always sent).
    checks = asked.of("checks")[0]
    assert checks["shown"]["sources"] == {"total": 0, "uncited": 1}
    assert judge["on_abstention"] == 1
    assert checks["sources"] == {"total": 0, "returned": 0}


def test_the_check_line_of_an_answer_whose_sentence_cites_nothing_says_there_was_nothing_to_match(fixture_db):
    """Ticket 58: the evidence pack writes the check line as the page does (src/strata/drafts/files.py), so an answer
    whose one kept sentence says only what check_plan could not answer reads true: nothing to match, and a model's
    judgment against what my tools reported, not "every source I cite came back from this search"."""
    from strata.config import load_draft_kinds
    from strata.drafts import files

    checks = ask(fixture_db, "p156634-plan-not-yet-public").of("checks")[0]
    assert files.check_line(checks, load_draft_kinds().kinds["review_notes"]) == (
        "Checked: the sentence I kept cites no source, so there was nothing to match. "
        "Judged by a model: 1 of 1 sentence says no more than my tools reported. "
        "Not checked: whether the plan's published records are complete, "
        "or whether these notes are what you would tell the borrower.")


def test_a_summary_that_cites_nothing_and_says_more_than_the_abstention_is_removed_in_the_same_call(fixture_db):
    asked = ask(fixture_db, "p156634-uncited-blame")

    assert len(asked.judge.calls) == 1
    assert [question.sentence for question in asked.judge.calls[0]] == [
        NOT_PUBLIC, "The agency was late in publishing its plan."]
    # It cites nothing and says more than the abstention, so its reason says both, apart from check 2's no_source
    # (ticket 58); the judge's own sentence is kept with it for the run log.
    [removed] = asked.of("removed")
    assert (removed["sentence"], removed["reason"], removed["reasons"][0]["check"]) == (
        "The agency was late in publishing its plan.", "beyond_abstention", 4)
    assert "says nothing about the agency being late" in removed["reasons"][0]["text"]
    assert copy_reason("beyond_abstention") == {
        "item": "It cited no source, and it said more than my tools reported.",
        "joined": "it cited no source and said more than my tools reported"}
    assert [item["text"] for item in asked.of("sentence")] == [NOT_PUBLIC]
    checks = asked.of("checks")[0]
    assert checks["judge"]["on_abstention"] == 2 and checks["shown"]["sources"] == {"total": 0, "uncited": 1}
    # Check 2 removed nothing here, so its step has no uncited count.
    assert "uncited" not in checks["sources"]


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


def test_the_stream_keeps_the_connection_alive_while_the_judge_takes_its_time(fixture_db):
    """The live judge may take up to verifier.judge_timeout_seconds (config/thresholds.toml): the stream sends a
    keep-alive comment while it waits, as it does while the agent works, so a proxy that closes quiet streams
    does not drop the answer (ticket 24's review, round 2, follow-up 2)."""
    import time

    from strata.agent.scripted import ScriptedJudge, load_cases

    class Slow(ScriptedJudge):
        def judge(self, questions):
            time.sleep(0.3)
            return super().judge(questions)

    asked = ask(fixture_db, "p130164-unsupported-summary", judge=Slow(load_cases()["p130164-unsupported-summary"]),
                heartbeat_seconds=0.05)

    judging = asked.text.index('"kind": "judge", "count": 1, "status": "running"')
    assert ": keep-alive" in asked.text[judging:asked.text.index("event: checks")]
    assert [item["reason"] for item in asked.of("removed")] == ["not_supported"]


def test_a_judge_that_times_out_or_answers_with_no_json_counts_as_one_that_did_not_respond(fixture_db):
    """The live judge on Azure OpenAI: a read that times out, or a body that is not JSON, removes the sentences it
    had to judge, as a judge that did not respond does, and never ends the answer with an error."""
    from strata.agent.judge import AzureOpenAIJudge

    def times_out(url, headers, body):
        raise TimeoutError("The read timed out.")

    def not_json(url, headers, body):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")

    for post in (times_out, not_json):
        judge = AzureOpenAIJudge("https://judge.example.invalid", "not-a-real-key", "gpt-5.4", post=post)
        asked = ask(fixture_db, "p130164-unsupported-summary", judge=judge)

        assert [(item["sentence"], item["reason"]) for item in asked.of("removed")] == [
            ("The completion report blamed the contractors for the rebidding.", "judge_unavailable")]
        assert [kind for kind, _ in asked.parsed if kind == "error"] == []


def test_when_the_judge_does_not_respond_and_every_sentence_needed_it_nothing_is_shown_unchecked(fixture_db):
    asked = ask(fixture_db, "p130164-summaries-judge-no-response")

    assert asked.of("sentence") == []
    assert {item["reason"] for item in asked.of("removed")} == {"judge_unavailable"}
    checks = asked.of("checks")[0]
    assert checks["sentences"]["kept"] == 0 and checks["judge"]["responded"] is False
    assert [kind for kind, _ in asked.parsed if kind == "error"] == []


def test_an_answer_after_find_comparables_counts_what_the_check_line_reads(fixture_db):
    """The ticket's check line: "Checked: N of N numbers match records; M of M quotes are on their pages. Not
    checked: whether these are the right comparables." The screen reads every count from this event. A quote of
    only a STEP reference proves nothing about "still open" (ticket 61), so the two sentences that quote one go to
    the judge, in one call, and the past range's sentence needs no model."""
    asked = ask(fixture_db, "ke-nwwda-541055-past-range")

    assert asked.of("removed") == []
    [call] = asked.judge.calls
    assert [question.sentence for question in call] == [
        'The newest, "KE-MIGORI COUNTY-532367-CW-RFB", was still open 13 days after its notice.',
        'Another, "KE-ICTA-571738-CW-RFB", was still open too.']
    checks = asked.of("checks")[0]
    assert checks["shown"] == {"numbers": {"total": 5, "matched": 5}, "dates": {"total": 0, "matched": 0},
                               "quotes": {"total": 2, "found": 2}, "judged": 2, "proven": 1}
    # Check 1's item in the steps counts numbers and dates together; the verifier adds them, not the browser.
    assert checks["checked"] == {"total": 5, "matched": 5}
    assert checks["tools"] == ["find_comparables"]
    # The tools whose "Not checked" clause applies only once a sentence cites them (config/tools.toml).
    assert checks["cited_only"] == ["get_lessons"] and "get_lessons" not in checks["cited_tools"]


def test_when_check_6_cannot_ask_which_reports_disagree_every_sentence_citing_the_project_is_removed(fixture_db):
    asked = ask(fixture_db, "p130164-disagreements-unavailable")

    assert asked.of("sentence") == []
    assert [(item["reason"], item["reasons"][-1]["text"]) for item in asked.of("removed")] == [
        ("disagreements_unavailable", "P130164")] * 3
    assert copy_reason("disagreements_unavailable")["item"] == (
        "I couldn't find out whether another report disagrees with its sources.")
    assert asked.judge.calls == []
    # The verifier counts the sentences it could not check, so the screen never counts removed events itself.
    assert asked.of("checks")[0]["disagreements"]["unasked"] == 3


def test_sentences_that_fail_different_checks_are_each_removed_with_the_reason_of_the_check_they_failed(fixture_db):
    asked = ask(fixture_db, "p130164-several-removed")

    assert [item["reason"] for item in asked.of("removed")] == [
        "number_not_in_records", "advice_without_lesson_or_comparable", "not_supported"]
    # Each removed sentence says what kind it was, so the removed box can quote advice, which is often an
    # order, rather than report it ("It said base your...").
    assert [item["kind"] for item in asked.of("removed")] == ["record", "advice", "summary"]
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
    assert [[question.sentence for question in call] for call in asked.judge.calls] == [[
        'The newest, "KE-MIGORI COUNTY-532367-CW-RFB", was still open 13 days after its notice.',
        'Another, "KE-ICTA-571738-CW-RFB", was still open too.',
        "Plan for longer than the 1.5 months the plan allows."]]
    checks = asked.of("checks")[0]
    assert checks["advice"] == {"total": 1, "cited": 1}
    assert (checks["shown"]["judged"], checks["shown"]["proven"]) == (3, 1)


# ── Check 6: a claim resting on one side of a disagreement shows both ─────

def test_advice_citing_a_comparable_passes_check_5_whichever_tool_returned_it_first(fixture_db):
    """Ticket 61's review, F4: when two tools return one evidence id, check 5 asked only the tool that returned it
    first, so advice citing a comparable that a tool whose rows back no advice returned first was removed. Check 5
    now asks every tool that returned the id this turn, so the order of the calls changes nothing. Made up: the
    comparable's cost row is planted under the package's own id, as a tool returning the same record would give it."""
    from strata.agent.answer_check import SixChecks
    from strata.agent.claims import Claim
    from strata.agent.loop import keep_result
    from strata.config import load_tools
    from strata.dbx import Viewer
    from strata.harness.facts import Facts
    from strata.lakehouse.engine import DuckDBEngine
    from strata.tools import registry

    works = "KE-NWWDA-541055-CW-RFB"
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        context = registry.Context(engine=engine, viewer=Viewer(email="a@b.c", token="t"))
        found = registry.call("find_comparables", {"as_of": "2026-10-22", "step_reference": works}, context)
        joined = ",".join(row["step_reference"] for row in found["rows"])
        cost = registry.call("compare_cost_estimates", {"as_of": "2026-10-22", "comparables": joined,
                                                        "step_reference": works}, context)
    row = cost["rows"][0]
    comparable = row["evidence_id"].removesuffix("/cost")
    assert comparable in {row["evidence_id"] for row in found["rows"]}
    cost = {**cost, "rows": [{**row, "evidence_id": comparable}]}
    advice = Claim(f"Base your works estimate on what {row['step_reference']} was estimated at.", "advice",
                   (comparable,))
    tools = load_tools()
    assert tools["find_comparables"].result.backs_advice and not tools["compare_cost_estimates"].result.backs_advice
    for order in ([("find_comparables", found), ("compare_cost_estimates", cost)],
                  [("compare_cost_estimates", cost), ("find_comparables", found)]):
        facts = Facts()
        for name, result in order:
            keep_result(facts, name, result, tools)
        assert SixChecks(None, None, tools).check([advice], facts).advice == (1, 1), [name for name, _ in order]


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
    # The side's quote is highlighted in its paragraph, for the marker under this sentence, though no sentence
    # quoted it, so its evidence card and the drawer open on the words the card shows.
    [highlight] = sources[paragraph_78]["highlights"]
    assert highlight["sentence"] == sentence["index"]
    assert sources[paragraph_78]["row"]["text"][highlight["start"]:highlight["end"]] == TRUTH["icr-para-78"]["value"]
    # warned: the sentences a warning card follows, which the screen announces; the verifier counts them.
    assert asked.of("checks")[0]["disagreements"] == {"disputed": 1, "shown": 1, "attached": 1, "unasked": 0,
                                                         "warned": 1}
    fetched = [step for step in asked.of("step") if step["kind"] == "disagreement"]
    assert [step["status"] for step in fetched] == ["running", "done"]
    # The events come in the answer contract's order.
    kinds = [kind for kind, _ in asked.parsed]
    assert kinds.index("evidence") < kinds.index("disagreement") < kinds.index("checks")


def test_the_isr_s_own_rating_is_the_one_highlighted_the_current_rating_not_the_previous_one(fixture_db):
    """Ticket 24's critique rounds 2 and 3: ISR 7's ratings table writes each row's previous rating, then its current
    one, and "Satisfactory" appears twice after "Progress towards achievement of PDO" (values.toml isr-7-rating). The
    sentence states ISR 7's own rating, so the highlight is the second, the Current Rating; and the card's ISR side,
    which gives a rating and no quote, gets the same highlight, so its marker opens on the words the card shows."""
    isr_7 = "strata.gold.passage:26733307/v1/s4"
    for case in ("p130164-isr-7-rating", "p130164-both-sides"):
        asked = ask(fixture_db, case)
        source = {evidence["id"]: evidence for evidence in asked.of("evidence")}[isr_7]
        text = source["row"]["text"]
        first = text.index(TRUTH["isr-7-rating"]["value"])
        second = text.index(TRUTH["isr-7-rating"]["value"], first + 1)

        assert text.index("Previous Rating") < text.index("Current Rating") < first, case
        assert [(mark["start"], mark["end"]) for mark in source["highlights"]] == [
            (second, second + len(TRUTH["isr-7-rating"]["value"]))], case


def test_a_sentence_citing_the_same_section_about_a_rating_no_report_disputes_gets_no_card(fixture_db):
    """Check 6 matches on the assertion, not the passage: ISR 7's section also rates the overall risk, which no
    report disagrees about, so a sentence quoting that rating does not rest on the disagreement."""
    asked = ask(fixture_db, "p130164-isr-7-and-risk-rating")

    first, second = asked.of("sentence")
    assert second["text"] == 'The same report rated the overall risk "Moderate".'
    assert [card["after"] for card in asked.of("disagreement")] == [first["index"]]
    assert asked.of("checks")[0]["disagreements"]["disputed"] == 1


def test_a_draft_that_showed_both_sides_gets_the_same_card_as_an_info_note_when_it_changes_nothing(fixture_db):
    asked = ask(fixture_db, "p130164-both-sides")

    [card] = asked.of("disagreement")
    assert (card["after"], card["attached_by_verifier"], card["changes_answer"]) == (0, False, False)
    assert [side["evidence_id"] for side in card["sides"]] == [
        "strata.gold.passage:26733307/v1/s4", "strata.gold.passage:31525018/v1/78"]
    assert asked.of("checks")[0]["disagreements"] == {"disputed": 1, "shown": 1, "attached": 0, "unasked": 0,
                                                         "warned": 0}
    # The agent asked get_disagreements itself, so check 6 had nothing to fetch.
    assert [step for step in asked.of("step") if step["kind"] == "disagreement"] == []


def test_the_gallery_and_the_capture_ask_each_scripted_case_s_own_question():
    """web/src/gallery/copy.ts repeats the scripted cases' questions for the gallery's panels and the capture,
    since a screen cannot import cases.toml; each must stay word for word a case's question."""
    from strata.agent.scripted import load_cases

    gallery = (Path(__file__).resolve().parents[1] / "web" / "src" / "gallery" / "copy.ts").read_text()
    block = gallery.split("  sixChecks: {", 1)[1].split("\n  },\n", 1)[0]
    lists = re.findall(r"\n    (?:questions|refusalQuestions): \{(.*?)\n    \}", block, re.S)
    written = [text for found in lists for text in re.findall(r'"((?:[^"\\]|\\.)*)"', found)]
    asked = {case.question for case in load_cases().values()}
    assert len(written) >= 15
    assert [question for question in written if question not in asked] == []
