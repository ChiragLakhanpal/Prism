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
