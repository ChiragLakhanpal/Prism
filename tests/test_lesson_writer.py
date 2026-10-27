"""The review-proposed-lessons workflow at seams 1 and 3 (ticket 29; the 29 design brief, sections 4.6, 5.7 and
5.8): the lesson review writer summarizes each item's evidence and names the current lessons it may repeat,
and the verifier checks every sentence before a reviewer reads it.

Offline, the scripted writer replays the recorded answers in tests/fixtures/agent/lesson_review.toml. The
fixture build runs the workflow once the queue holds the fixture's three proposed lessons, with the library
still empty. The roles come from tests/fixtures/roles.toml.
"""

import datetime as dt

import pytest

import lesson_scenario as scenario
from strata.agent.loop import AgentError
from strata.knowledge.lessons import writer
from strata.knowledge.lessons.review import Refused
from strata.lakehouse.engine import DuckDBEngine

DAY = dt.date(2026, 10, 27)


@pytest.fixture
def database(fixture_db, tmp_path):
    return scenario.copy_of(fixture_db, tmp_path)


def page(database, passage_id, viewer=scenario.ASHA, day=DAY) -> dict:
    with DuckDBEngine.open(database, read_only=True) as engine:
        return scenario.review_on(day).item(engine, viewer, scenario.item_of(engine, passage_id))


def rewrite(database, day=DAY) -> int:
    with DuckDBEngine.open(database) as engine:
        return writer.run(engine, writer.recorded_agent_for(), lambda: dt.datetime.combine(day, dt.time(6), tzinfo=dt.UTC),
                          3, judge_for=writer.recorded_judge_for())


class Writes:
    """A stand-in lesson review writer that answers with the summary claims it is given."""

    name = "strata-lesson-review-writer"

    def __init__(self, *claims):
        self.claims = list(claims)

    def respond(self, items, previous_response_id):
        import json

        return {"id": "resp_1", "output": [{"type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": json.dumps({"summary": self.claims, "repeats": []})}]}]}


class NothingFollows:
    name = "nothing follows"

    def judge(self, questions):
        from strata.agent.judge import Judgement

        return [Judgement(question.index, False, "It does not follow.") for question in questions]


ICR_54 = "strata.gold.passage:31525018/v1/54"


def write_note(database, agent, six_checks):
    with DuckDBEngine.open(database) as engine:
        store = writer.Store(engine)
        item = store.items[scenario.item_of(engine, scenario.REBIDDING)]
        subject = scenario.review_on(DAY).subject(store, item)
        writer.write_one(engine, store, item, subject, agent, dt.datetime(2026, 10, 27, 6, tzinfo=dt.UTC), 3,
                         six_checks=six_checks)
    return page(database, scenario.REBIDDING)["summary"]


def test_check_4_removes_a_summary_sentence_its_passage_does_not_support(database):
    """Ticket 61: the writer's note runs all six checks through SixChecks, as a draft does. A summary that restates
    nothing word for word goes to the judge, which says it does not follow, so it is removed with check 4's reason;
    the quote checks 1 to 3 prove needs no model."""
    from strata.agent.answer_check import SixChecks

    agent = Writes({"sentence": "The contractors were to blame for the rebidding.", "kind": "summary",
                    "evidence_ids": [ICR_54]},
                   {"sentence": 'The ICR said that "108 of 328 cases had to go through rebidding."', "kind": "quote",
                    "evidence_ids": [ICR_54], "quote": {"text": "108 of 328 cases had to go through rebidding.",
                                                       "passage_id": ICR_54}})

    summary = write_note(database, agent, SixChecks(None, NothingFollows()))

    assert [(removed["sentence"], removed["reason"], removed["reasons"][0]["check"]) for removed in summary["removed"]] \
        == [("The contractors were to blame for the rebidding.", "not_supported", 4)]
    assert [sentence["text"] for sentence in summary["sentences"]] == [
        'The ICR said that "108 of 328 cases had to go through rebidding."']
    assert summary["checks"]["checks_run"] == [1, 2, 3, 4, 5, 6]


def test_check_6_attaches_a_disagreement_whose_side_a_summary_sentence_quotes(database):
    """Ticket 61: check 6 asks get_disagreements about P130164, the project of the passages the note cites, and a
    disagreement whose side is the quoted ICR paragraph 54 comes with the note, both sides. It is planted at the
    tool, beside the fixture's own disagreements (tests/planted_disagreements.py)."""
    import planted_disagreements as planted

    from strata.agent.answer_check import SixChecks

    agent = writer.recorded_agent_for()({}, {"evidence": [{"role": "source", "passage_id": scenario.REBIDDING}]})

    summary = write_note(database, agent, SixChecks(None, None, planted.with_adapter("quoting_icr_54")))

    [card] = summary["disagreements"]
    assert (card["id"], [side["evidence_id"] for side in card["sides"]]) == (planted.PLANTED, [ICR_54, planted.ISR_7])
    assert summary["sentences"][card["after"]]["text"] == 'The ICR said that "108 of 328 cases had to go through rebidding."'
    assert summary["checks"]["disagreements"]["shown"] == 1


def test_the_summary_keeps_the_sentences_that_pass_the_checks_and_shows_the_one_the_verifier_removed(fixture_db):
    """The recorded summary of ICR paragraph 54 quotes the ICR and the ICR Review, then states a two-year delay
    that neither passage holds."""
    summary = page(fixture_db, scenario.REBIDDING)["summary"]

    assert summary["status"] == "ready"
    assert [sentence["text"] for sentence in summary["sentences"]] == [
        'The ICR said that "108 of 328 cases had to go through rebidding."',
        'IEG\'s ICR Review said the same: "The works contract estimates were not based on market rate."']
    assert [sentence["evidence_ids"] for sentence in summary["sentences"]] == [
        ["strata.gold.passage:31525018/v1/54"], ["strata.gold.passage:34056616/v2/10.b"]]
    assert [(removed["sentence"], removed["reason"]) for removed in summary["removed"]] == [
        ("The rebidding delayed the road works by two years.", "number_not_in_records")]
    assert summary["checks"]["sentences"] == {"written": 3, "kept": 2, "removed": 1}


def test_a_likely_repeat_names_only_a_lesson_in_the_library(database):
    """The writer names IEG's own lesson as a likely repeat of ICR paragraph 55's. While the library is empty the
    page shows none; once two people add IEG's lesson, the workflow writes again and names it."""
    before = page(database, scenario.PERMITS)
    scenario.decide(database, scenario.IEG_LESSON, DAY)

    assert rewrite(database) == 2  # the two items still open, since the library changed
    after = page(database, scenario.PERMITS)
    assert (before["may_repeat"], before["repeats"]) == (False, [])
    assert after["may_repeat"] is True
    [repeat] = after["repeats"]
    assert repeat["statement"] == "Put forest and other permits in place before awarding contracts"
    assert [sentence["text"] for sentence in repeat["sentences"]] == [
        "IEG's own lesson in its ICR Review said the same about permits before contracts are awarded."]


def test_a_lead_merges_a_proposal_only_into_a_likely_repeat_and_the_lesson_gains_a_version(database):
    scenario.decide(database, scenario.IEG_LESSON, DAY)
    rewrite(database)
    target = page(database, scenario.PERMITS)["repeats"][0]["lesson_id"]

    with pytest.raises(Refused) as refused:
        scenario.decide(database, scenario.PERMITS, DAY + dt.timedelta(days=1), outcome="repeat", repeat_of="lesson-not-a-repeat")
    assert refused.value.code == "not_a_likely_repeat"
    with DuckDBEngine.open(database) as engine:  # the recommendation above stands, so the lead decides again
        decided = scenario.review_on(DAY + dt.timedelta(days=1), 16).act(
            engine, scenario.OMAR, scenario.item_of(engine, scenario.PERMITS), "decide",
            {"expected_stage": "decision", "outcome": "repeat", "repeat_of": target, "reason": "The same advice."}, engine)

    assert decided["item"]["outcome"]["outcome"] == "merged"
    with DuckDBEngine.open(database, read_only=True) as engine:
        result = engine.run("SELECT version, change_kind, was, now FROM strata.ops.lesson_versions "
                            "WHERE lesson_id = :lesson_id ORDER BY version", {"lesson_id": target})
    assert [row[:2] for row in result.rows] == [(1, "added"), (2, "merged")]
    assert (result.rows[1][2], result.rows[1][3]) == ('{"quotes": 1, "reports": 1}', '{"quotes": 2, "reports": 2}')


def test_a_writer_that_gives_no_answer_leaves_a_failed_note_and_try_again_writes_it_again(database):
    class NoAnswer:
        name = "strata-lesson-review-writer"

        def respond(self, items, previous_response_id):
            raise AgentError("agent_unavailable", "The writer did not answer.")

    with DuckDBEngine.open(database) as engine:
        item = scenario.item_of(engine, scenario.REBIDDING)
        failed = scenario.review_on(DAY).rewrite(engine, scenario.ASHA, item, NoAnswer(), engine)
        again = scenario.review_on(DAY).rewrite(engine, scenario.ASHA, item,
                                                writer.recorded_agent_for()({}, {"evidence": [
                                                    {"role": "source", "passage_id": scenario.REBIDDING}]}), engine)

    assert failed["item"]["summary"] == {"status": "failed"} | {key: failed["item"]["summary"][key]
                                                                for key in ("sentences", "evidence", "checks", "removed",
                                                                            "disagreements")}
    assert failed["item"]["summary"]["sentences"] == []
    assert again["item"]["summary"]["status"] == "ready"


def test_an_item_with_no_note_yet_says_the_summary_is_still_being_written(database):
    scenario.decide(database, scenario.REBIDDING, DAY)
    with DuckDBEngine.open(database) as engine:
        lesson = scenario.review_on(DAY).library(engine, scenario.ASHA)["lessons"][0]["lesson_id"]
        scenario.review_on(DAY).recheck(engine, scenario.WANJIRU, lesson, "The 2025 rules changed how estimates are made.",
                                  engine)
        result = engine.run("SELECT item_id FROM strata.ops.lesson_review_items WHERE kind = 'recheck'", {})
        recheck = scenario.review_on(DAY).item(engine, scenario.ASHA, result.rows[0][0])

    assert recheck["summary"] == {"status": "writing"}
