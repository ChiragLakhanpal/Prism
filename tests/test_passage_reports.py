"""Passage reports from the evidence drawer and the passage reviewers' decisions (ticket 32), at seam 3: the answer
stream offers the feedback row for a passage a search found, "Wrong passage" and "Not useful" each write one
candidate label, and search_passages (seam 2) ranks nothing differently until a passage reviewer accepts the
label. An accepted label ranks the passage lower for that kind of question, and never hides it.

The people are tests/fixtures/roles.toml's (tests/retrieval_scenario.py): Daniel and Priya review passages, and
Leela works on P130164.
"""

import datetime as dt

import pytest

from retrieval_scenario import ANA, DANIEL, LEELA, PARAGRAPH_54, PRIYA, Loop
from strata.dbx import Viewer
from strata.harness.sse import events
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

QUESTION = "Why were works contracts in P130164 advertised again?"
# What the scripted agent asks search_passages for this question (tests/fixtures/agent/recorded/p130164-rebidding.json).
SEARCHED = "works contracts advertised again rebidding"


@pytest.fixture
def loop(fixture_db, tmp_path):
    found = Loop(fixture_db, tmp_path)
    yield found
    found.close()


def evidence_of(text: str) -> dict:
    return {data["id"]: data for kind, data in events(text) if kind == "evidence"}


def search(loop, query: str = SEARCHED, **arguments) -> dict:
    context = registry.Context(loop.database.cursor(), Viewer(email="ana.example@worldbank.org", token="not-a-real-token"),
                               "staff", dt.date(2026, 10, 23))
    return registry.call("search_passages", {"query": query, "project_id": "P130164", **arguments}, context)


def test_the_answer_offers_the_feedback_row_only_for_a_passage_a_search_found(loop):
    case_question = {"question": QUESTION, "scope": "P130164", "asof": "2026-10-23"}
    staff = evidence_of(loop.request("POST", "/api/ask", ANA, case_question).text)
    preview = evidence_of(loop.request("POST", "/api/ask", ANA, {**case_question, "view": "piu"}).text)

    assert staff[PARAGRAPH_54]["feedback"] == {"allowed": True, "why_not": None, "run_id": "run-0001", "mode": "pilot",
                                               "my_report": None}
    # A preview shows the row with both buttons disabled.
    assert (preview[PARAGRAPH_54]["feedback"]["allowed"], preview[PARAGRAPH_54]["feedback"]["why_not"]) == (False, "preview")
    for found in staff.values():
        if found["kind"] != "passage":
            assert found["feedback"]["why_not"] == "record"


def test_wrong_passage_writes_one_candidate_label_with_viewer_passage_query_and_reason(loop):
    run = loop.ask(ANA)
    response = loop.report(ANA, run, reason="It is about rebidding in general, not why these contracts were rebid.")

    assert response.status_code == 200, response.text
    assert response.json()["my_report"]["status"] == "waiting"
    [label] = loop.rows("SELECT * FROM strata.ops.candidate_labels")
    assert (label["event"], label["viewer_id"], label["viewer_email"], label["passage_id"], label["run_id"]) == (
        "sent", "id-ana.example@worldbank.org", "ana.example@worldbank.org", "31525018/v1/54", run)
    assert (label["question"], label["query_kind"], label["kind"], label["own_project"]) == (
        QUESTION, "rebidding_and_prices", "wrong_passage", False)
    assert label["reason"] == "It is about rebidding in general, not why these contracts were rebid."
    assert "108 of 328" in label["sentence"]
    # Sending again for the same passage in the same answer writes nothing more.
    assert loop.report(ANA, run, kind="not_useful").json()["code"] == "already_sent"
    assert len(loop.rows("SELECT * FROM strata.ops.candidate_labels")) == 1


def test_not_useful_with_no_reason_is_one_candidate_label_too(loop):
    run = loop.ask(LEELA)
    response = loop.report(LEELA, run, kind="not_useful")

    assert response.status_code == 200, response.text
    [label] = loop.rows("SELECT * FROM strata.ops.candidate_labels")
    # Leela works on P130164, so her report is about her own project.
    assert (label["kind"], label["reason"], label["own_project"]) == ("not_useful", None, True)


def test_a_preview_or_a_source_the_answer_did_not_cite_is_refused_and_nothing_is_written(loop):
    run = loop.ask(ANA)

    assert loop.report(ANA, run, view="piu").status_code == 403
    missing = loop.report(ANA, run, evidence_id="strata.gold.passage:31525018/v1/71")
    assert (missing.status_code, missing.json()["code"]) == (404, "not_in_answer")
    assert loop.report(ANA, "run-9999").json()["code"] == "not_in_answer"
    # An answer asked in a preview stays a preview, whatever the browser says when it sends the report.
    previewed = loop.ask(ANA, view="piu")
    refused = loop.report(ANA, previewed, view="staff")
    assert (refused.status_code, refused.json()["code"]) == (403, "preview")
    assert loop.rows("SELECT * FROM strata.ops.candidate_labels") == []


def test_a_report_can_be_withdrawn_until_a_reviewer_decides_and_nothing_is_deleted(loop):
    run = loop.ask(ANA)
    sent = loop.report(ANA, run).json()["my_report"]

    mine = loop.request("GET", "/api/feedback", ANA, params={"evidence_id": PARAGRAPH_54, "run_id": run}).json()
    assert mine["my_report"]["report_id"] == sent["report_id"]
    assert loop.request("POST", f"/api/feedback/{sent['report_id']}/withdraw", ANA).json()["withdrawn"] is True
    assert [row["event"] for row in loop.rows("SELECT event FROM strata.ops.candidate_labels ORDER BY reported_at")] == [
        "sent", "withdrawn"]
    assert loop.request("GET", "/api/feedback", ANA, params={"evidence_id": PARAGRAPH_54, "run_id": run}).json()[
        "my_report"] is None


def test_ranking_changes_only_once_a_passage_reviewer_accepts_the_label(loop):
    before = [row["passage_id"] for row in search(loop, limit=20)["rows"]]
    assert "31525018/v1/54" in before[:10]
    run = loop.ask(ANA)
    loop.report(ANA, run, reason="Not the reason these contracts were advertised again.")

    assert [row["passage_id"] for row in search(loop, limit=20)["rows"]] == before

    queue = loop.request("GET", "/api/passage-reports", DANIEL).json()
    [row] = queue["groups"]["you"]
    group = loop.request("GET", f"/api/passage-reports/{row['group_id']}", DANIEL).json()
    decided = loop.request("POST", f"/api/passage-reports/{row['group_id']}/decide", DANIEL,
                           {"expected_state": group["state"], "outcome": "rank_lower",
                            "reason": "The paragraph is about estimates in general."})
    assert decided.status_code == 200, decided.text

    # Paragraph 54 now ranks below every other passage the search found, which keep their order.
    after = search(loop, limit=20)
    order = [found["passage_id"] for found in after["rows"]]
    others = [passage for passage in before if passage != "31525018/v1/54"]
    assert order[:len(others)] == others, (before, order)
    assert "31525018/v1/54" not in order[:len(others)]
    assert after["ranked_lower"] == {"query_kind": "rebidding_and_prices", "evidence_ids": [PARAGRAPH_54]}
    # Only that kind of question: a question of another kind ranks it as before.
    other = search(loop, "rating outcome indicator for the project")
    assert other["ranked_lower"] == {"query_kind": "results", "evidence_ids": []}


def test_a_report_takes_the_kind_of_the_search_that_found_the_passage_so_ranking_lower_reaches_that_search(
        fixture_db, tmp_path):
    """The summaries case asks "In a few words, what went wrong with the works contracts in P130164?", a question
    about contracts and their management, but its agent searched for "works contracts advertised again rebidding",
    a question about rebidding and bid prices (tests/fixtures/agent/recorded/p130164-summaries.json). The report,
    its group and the reviewer's decision take the search's kind, so the same search then ranks the paragraph lower."""
    summaries = Loop(fixture_db, tmp_path, case="p130164-summaries")
    try:
        run = summaries.ask(ANA)
        assert summaries.report(ANA, run).status_code == 200
        [label] = summaries.rows("SELECT question, query_kind FROM strata.ops.candidate_labels")
        assert label == {"question": "In a few words, what went wrong with the works contracts in P130164?",
                         "query_kind": "rebidding_and_prices"}
        [row] = summaries.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]
        assert summaries.decide(DANIEL, row["group_id"]).status_code == 200

        assert search(summaries)["ranked_lower"] == {"query_kind": "rebidding_and_prices", "evidence_ids": [PARAGRAPH_54]}
    finally:
        summaries.close()


def test_reports_on_one_passage_and_kind_of_question_are_one_group_that_its_own_reporter_cannot_decide(loop):
    """Ana's "Wrong passage" with a reason and Priya's "Not useful" with none, on paragraph 54 for the same question,
    are one group. Priya is a passage reviewer, but she sent one of the reports, so Daniel decides."""
    loop.report(ANA, loop.ask(ANA), reason="Not why these were advertised again.")
    loop.report(PRIYA, loop.ask(PRIYA), kind="not_useful")

    [mine] = loop.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]
    assert (mine["kind_label"], mine["report_count"], mine["query_kind"], mine["para"], mine["page"]) == (
        "both", 2, "rebidding_and_prices", "54", 23)
    hers = loop.request("GET", "/api/passage-reports", PRIYA).json()["groups"]
    assert (hers["you"], hers["others"][0]["reason_code"]) == ([], "own_report")
    refused = loop.decide(PRIYA, mine["group_id"])
    assert (refused.status_code, refused.json()["code"]) == (403, "own_report")
    # Reporters are named by role, and the reviewer's own report as "you".
    detail = loop.request("GET", f"/api/passage-reports/{mine['group_id']}", PRIYA).json()
    assert [(report["role"], report["kind"], report["reason"]) for report in detail["reports"]] == [
        ("staff", "wrong_passage", "Not why these were advertised again."), ("you", "not_useful", None)]
    assert "ana" not in str(detail["reports"]).lower()
    assert loop.request("GET", "/api/passage-reports", ANA).json()["code"] == "not_a_passage_reviewer"


def test_a_decision_needs_a_reason_and_the_state_the_reviewer_saw(loop):
    loop.report(ANA, loop.ask(ANA))
    [row] = loop.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]

    assert loop.decide(DANIEL, row["group_id"], reason="  ").json()["code"] == "no_reason"
    assert loop.decide(PRIYA, row["group_id"], outcome="keep", reason="It answers the question.").status_code == 200
    stale = loop.decide(DANIEL, row["group_id"], state=row["state"])
    assert (stale.status_code, stale.json()["code"], stale.json()["values"]["name"]) == (409, "stale", "Priya Nair")
    assert [act["act"] for act in loop.rows("SELECT act FROM strata.ops.label_decisions")] == ["declined"]


def test_the_reporter_sees_the_decision_and_a_reopened_record_gives_back_the_earlier_ranking(loop):
    run = loop.ask(ANA)
    loop.report(ANA, run, reason="Too general.")
    before = [found["passage_id"] for found in search(loop)["rows"]]
    [row] = loop.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]
    loop.decide(DANIEL, row["group_id"], reason="It is about estimates in general, not these contracts.")

    mine = loop.request("GET", "/api/feedback", ANA, params={"evidence_id": PARAGRAPH_54, "run_id": run}).json()["my_report"]
    assert (mine["status"], mine["reviewer_reason"]) == ("ranked_lower", "It is about estimates in general, not these contracts.")
    record = loop.request("GET", f"/api/passage-reports/{row['group_id']}", DANIEL).json()
    assert (record["stage"], record["outcome"]["outcome"], record["outcome"]["reviewer_name"]) == (
        "decided", "ranked_lower", "Daniel Okafor")
    decided = loop.request("GET", "/api/passage-reports", DANIEL).json()["decided"]["rows"]
    assert [(found["outcome"], found["report_count"]) for found in decided] == [("ranked_lower", 1)]
    # A report a reviewer decided can no longer be withdrawn.
    assert loop.request("POST", f"/api/feedback/{mine['report_id']}/withdraw", ANA).json()["code"] == "decided"

    assert loop.request("POST", f"/api/passage-reports/{row['group_id']}/reopen", DANIEL, {"reason": ""}).json()[
        "code"] == "no_reason"
    reopened = loop.request("POST", f"/api/passage-reports/{row['group_id']}/reopen", PRIYA,
                            {"reason": "The question was about these contracts after all."})
    assert reopened.json()["item"]["stage"] == "waiting"
    assert [found["passage_id"] for found in search(loop)["rows"]] == before
    assert [act["act"] for act in loop.rows("SELECT act FROM strata.ops.label_decisions ORDER BY decided_at")] == [
        "accepted", "reopened"]


def test_a_label_from_live_feedback_never_reaches_an_evaluation_set(loop):
    """Daniel accepts Ana's report, and the weekly run puts the label in the labeled set's feedback set, where it
    can train. Building an evaluation set from it fails."""
    from strata.estimates import retrieval
    from strata.knowledge.retrieval import labels
    from strata.knowledge.retrieval.labels import LiveFeedbackError

    loop.report(ANA, loop.ask(ANA))
    [row] = loop.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]
    loop.decide(DANIEL, row["group_id"])
    loop.weekly()

    held = labels.latest(loop.database.cursor())
    feedback = [label for label in held if label.query_set == "feedback"]
    assert [(label.passage_id, label.origin, label.grade) for label in feedback] == [
        ("31525018/v1/54", "feedback_reviewed", 0)]
    with pytest.raises(LiveFeedbackError):
        retrieval.evaluation_queries(feedback)
    # The evaluation sets themselves hold no label from feedback.
    assert retrieval.evaluation_queries(label for label in held if label.query_set != "feedback")


def test_a_passage_ranked_lower_still_appears_first_when_it_is_the_only_one_found(loop):
    run = loop.ask(ANA)
    loop.report(ANA, run)
    [row] = loop.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]
    loop.request("POST", f"/api/passage-reports/{row['group_id']}/decide", DANIEL,
                 {"expected_state": row["state"], "outcome": "rank_lower", "reason": "Too general for this question."})

    # Of the ICR's paragraphs, only paragraph 54 holds "328" (values.toml: icr-para-54, "108 of 328 cases").
    narrow = search(loop, "rebid 328", document_type="ICR")
    assert narrow["coverage"]["matched"] == 1
    assert [found["passage_id"] for found in narrow["rows"]] == ["31525018/v1/54"]
    assert narrow["ranked_lower"]["evidence_ids"] == [PARAGRAPH_54]
