"""The rules for scale (ticket 32; docs/PLAN.md section 11), through seams 1 and 3: people send passage reports over
HTTP, and the weekly retrieval run applies the rules to the week's batch.

With retrieval.mode = "scale" (config/thresholds.toml; the pilot keeps a person on every report):

- three different people making the same report, with no dissent, make a silver label, weighted by their
  reliability as in Dawid and Skene, and one in ten such labels goes to a passage reviewer as an audit sample;
- no one person supplies more than 10% of a batch, at least one report: the rest of theirs go to a person;
- a report about the sender's own project always goes to a person.
"""

import pytest

from retrieval_scenario import ANA, DANIEL, KOFI, LEELA, NOOR, PARAGRAPH_54, PARAGRAPH_55, SARA, Loop
from strata.knowledge.retrieval import labels


@pytest.fixture
def loop(fixture_db, tmp_path):
    found = Loop(fixture_db, tmp_path, mode="scale")
    yield found
    found.close()


def acts(loop) -> list[tuple]:
    return [(row["passage_id"], row["act"], row["reason"], row["agreeing"], row["label_weight"])
            for row in loop.rows("SELECT * FROM strata.ops.label_decisions ORDER BY decided_at, act")]


def test_agreement_makes_a_silver_label_while_the_share_cap_and_own_projects_send_reports_to_a_person(loop):
    """Ana reports paragraphs 54 and 55; Kofi and Sara report 54; Leela, who works on P130164, reports 55. The batch
    has four reports that may count (Leela's is about her own project), so no one may supply more than one: Ana's
    later report, on 55, goes to a person. Three different people agree on 54 and nobody dissents."""
    ana = loop.ask(ANA)
    loop.report(ANA, ana)
    for who in (KOFI, SARA):
        loop.report(who, loop.ask(who))
    loop.report(ANA, ana, evidence_id=PARAGRAPH_55)
    loop.report(LEELA, loop.ask(LEELA), evidence_id=PARAGRAPH_55)

    done = loop.weekly()

    assert done["triage"] == {"routed": 2, "silver": 1, "audit": 1}
    # Nobody has a reviewed report yet, so each person's reliability is the prior of one in two, and the label's
    # weight is 0.5.
    assert acts(loop) == [
        ("31525018/v1/55", "routed", "own_project", None, None),
        ("31525018/v1/55", "routed", "user_share", None, None),
        ("31525018/v1/54", "accepted_by_agreement", None, 3, 0.5),
        ("31525018/v1/54", "audit", None, 3, 0.5),
    ]
    feedback = [label for label in labels.latest(loop.database.cursor()) if label.query_set == "feedback"]
    assert [(label.passage_id, label.origin, label.weight) for label in feedback] == [
        ("31525018/v1/54", "feedback_agreement", 0.5)]

    queue = loop.request("GET", "/api/passage-reports", DANIEL).json()
    rows = {row["passage_id"]: row for row in queue["groups"]["you"]}
    assert (rows["31525018/v1/54"]["kind_label"], rows["31525018/v1/54"]["agreeing"]) == ("audit", 3)
    assert (rows["31525018/v1/55"]["report_count"], rows["31525018/v1/55"]["own_project"]) == (2, True)
    # The audit sample's check: Daniel leaves it ranked lower.
    assert loop.decide(DANIEL, rows["31525018/v1/54"]["group_id"], outcome="leave_lower",
                       reason="Three people were right.").status_code == 200
    decided = loop.request("GET", "/api/passage-reports", DANIEL).json()["decided"]["rows"]
    assert [(row["outcome"], row["report_count"]) for row in decided] == [("left_lower", 3)]
    mine = loop.request("GET", "/api/feedback", KOFI, params={"evidence_id": PARAGRAPH_54, "run_id": "run-0002"}).json()
    assert mine["my_report"]["status"] == "ranked_lower"


def test_a_withdrawn_report_is_dissent_so_three_others_agreeing_still_go_to_a_person(loop):
    for who in (ANA, KOFI, SARA):
        loop.report(who, loop.ask(who))
    noor = loop.report(NOOR, loop.ask(NOOR)).json()["my_report"]
    loop.request("POST", f"/api/feedback/{noor['report_id']}/withdraw", NOOR)

    assert loop.weekly()["triage"] == {"routed": 0, "silver": 0, "audit": 0}
    assert acts(loop) == []
    [row] = loop.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]
    assert (row["kind_label"], row["report_count"]) == ("wrong_passage", 3)


def test_in_the_pilot_the_weekly_run_leaves_every_report_to_a_person(fixture_db, tmp_path):
    pilot = Loop(fixture_db, tmp_path)
    try:
        for who in (ANA, KOFI, SARA):
            pilot.report(who, pilot.ask(who))
        assert pilot.weekly()["triage"] == {"routed": 0, "silver": 0, "audit": 0}
        assert pilot.rows("SELECT * FROM strata.ops.label_decisions") == []
    finally:
        pilot.close()
