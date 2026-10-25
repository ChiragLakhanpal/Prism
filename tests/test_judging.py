"""The judging tool (ticket 32), at seam 3: two query judges grade the passages pooled for each query written from an
award notice, each on their own and in an order of their own, and Strata records both judges' grades and their
agreement. The fixture's three queries are in evals/retrieval_queries.toml; Mei and Tomas are the two judges
(tests/fixtures/roles.toml).

The agreement is worked out by hand: on query 2's 25 pooled passages, by passage id, Mei grades the first 10
"Answers it", the next 5 "Partly" and the last 10 "Not relevant". Tomas grades the same, except two of Mei's
"Answers it" as "Partly" and three of her "Not relevant" as "Partly". They agree on 20 of 25 (0.8). By chance they
would agree on (10 x 8 + 5 x 10 + 10 x 7) / 625 = 0.32, so Cohen's kappa is (0.8 - 0.32) / (1 - 0.32) = 0.71.
"""

import pytest

from retrieval_scenario import ANA, MEI, TOMAS, Loop
from strata.knowledge.retrieval import labels

QUERY = "nq-water-works-readiness"


@pytest.fixture
def loop(fixture_db, tmp_path):
    found = Loop(fixture_db, tmp_path)
    yield found
    found.close()


def grades_for(passages: list[str], judge: str) -> dict[str, str]:
    ordered = sorted(passages)
    mei = {passage: "answers" if i < 10 else "partly" if i < 15 else "not_relevant" for i, passage in enumerate(ordered)}
    if judge == "mei":
        return mei
    tomas = dict(mei)
    for passage in ordered[:2] + ordered[15:18]:
        tomas[passage] = "partly"
    return tomas


def grade_all(loop, who, judge: str, passages: list[str]):
    for passage, grade in grades_for(passages, judge).items():
        response = loop.request("PUT", f"/api/judging/queries/{QUERY}/passages/{passage}", who, {"grade": grade})
        assert response.status_code == 200, response.text


def test_the_lessons_frame_shows_each_reviewer_page_only_to_its_role(loop):
    from retrieval_scenario import DANIEL, PRIYA

    tabs = {name: loop.request("GET", "/api/lessons/me", who).json()
            for name, who in (("ana", ANA), ("mei", MEI), ("daniel", DANIEL), ("priya", PRIYA))}

    assert tabs["ana"]["tabs"] == ["library"]
    assert (tabs["mei"]["tabs"], tabs["mei"]["queries_left"]) == (["library", "judging"], 3)
    assert (tabs["daniel"]["tabs"], tabs["daniel"]["reports_waiting"]) == (["library", "reports"], 0)
    # Priya reviews lessons and passages.
    assert tabs["priya"]["tabs"] == ["library", "review", "reports"]


def test_two_judges_grade_a_query_alone_and_strata_records_their_agreement(loop):
    start = loop.request("GET", "/api/judging/queries", MEI).json()
    assert (start["total"], start["mine_done"], start["counts"]["to_judge"]) == (3, 0, 3)
    assert start["agreement"] == {"agree": 0, "pairs": 0, "both_done": 0, "kappa": None, "withheld": True, "min_pairs": 20}

    mine = loop.request("GET", f"/api/judging/queries/{QUERY}", MEI).json()
    theirs = loop.request("GET", f"/api/judging/queries/{QUERY}", TOMAS).json()
    passages = [found["passage_id"] for found in mine["passages"]]
    assert len(passages) == mine["pool"] == 25
    # Each judge sees the same pool in an order of their own, with no rank, score or setup.
    assert sorted(passages) == sorted(found["passage_id"] for found in theirs["passages"])
    assert passages != [found["passage_id"] for found in theirs["passages"]]
    assert not {"rank", "score"} & set(mine["passages"][0]["passage"])
    assert all(found["other_grade"] is None for found in mine["passages"])

    grade_all(loop, MEI, "mei", passages)
    halfway = loop.request("GET", f"/api/judging/queries/{QUERY}", MEI).json()
    # Mei has finished, Tomas has not: her grades can still change, and his stay hidden from her.
    assert (halfway["my_state"], halfway["other_state"], halfway["locked"]) == ("finished", "not_started", False)
    grade_all(loop, TOMAS, "tomas", passages)

    done = loop.request("GET", f"/api/judging/queries/{QUERY}", MEI).json()
    assert (done["locked"], done["agree"]) == (True, 20)
    assert sum(1 for found in done["passages"] if found["other_grade"] != found["my_grade"]) == 5
    listing = loop.request("GET", "/api/judging/queries", MEI, params={"show": "finished_by_both"}).json()
    assert listing["agreement"] == {"agree": 20, "pairs": 25, "both_done": 1, "kappa": 0.71, "withheld": False,
                                    "min_pairs": 20}
    assert [query["query_id"] for query in listing["queries"]] == [QUERY]
    rows = loop.rows(f"SELECT DISTINCT judge_email FROM strata.ops.retrieval_grades WHERE query_id = '{QUERY}'")
    assert sorted(row["judge_email"] for row in rows) == ["mei.tanaka@worldbank.example", "tomas.rivera@worldbank.example"]

    locked = loop.request("PUT", f"/api/judging/queries/{QUERY}/passages/{passages[0]}", MEI, {"grade": "partly"})
    assert (locked.status_code, locked.json()["code"]) == (409, "locked")
    assert loop.request("GET", "/api/judging/queries", ANA).json()["code"] == "not_a_judge"

    # The finished query joins the labeled set: each passage at the lower of the two grades, when at least "Partly".
    loop.weekly()
    judged = [label for label in labels.latest(loop.database.cursor()) if label.query_set == "notice_queries"]
    assert {label.query_id for label in judged} == {QUERY} and len(judged) == 15
    assert {label.origin for label in judged} == {"judged"}
