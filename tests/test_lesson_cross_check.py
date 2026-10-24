"""The quarterly cross-check at seam 1, a run over the fixture (ticket 29; docs/PLAN.md section 11, "a
quarterly 10% cross-check by another region"; spec story 94).

Each quarter, the job draws a tenth of each region's decisions from the quarter before, at least one, and
assigns each to reviewers in another region, who agree or disagree with a reason. A disagreement starts a
re-check in the region that decided. The roles come from tests/fixtures/roles.toml: South Asia decides the
fixture's lessons, and Eastern and Southern Africa is the other region.
"""

import datetime as dt

import pytest

import lesson_scenario as scenario
from strata.knowledge.lessons import cross_check
from strata.lakehouse.engine import DuckDBEngine

DECIDED = dt.date(2026, 10, 27)  # a Tuesday in the fourth quarter of 2026
RUN = dt.date(2027, 1, 4)  # the first Monday of 2027, the next quarter


@pytest.fixture
def decided(fixture_db, tmp_path):
    """The fixture's three proposed lessons, each recommended and decided in South Asia on October 27."""
    database = scenario.copy_of(fixture_db, tmp_path)
    scenario.decide(database, scenario.REBIDDING, DECIDED)
    scenario.decide(database, scenario.PERMITS, DECIDED, outcome="reject")
    scenario.decide(database, scenario.IEG_LESSON, DECIDED)
    return database


def cross_checks(database) -> list[dict]:
    with DuckDBEngine.open(database, read_only=True) as engine:
        result = engine.run("SELECT * FROM strata.ops.lesson_review_items WHERE kind = 'cross_check' ORDER BY item_id")
        return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def run(database, day=RUN) -> int:
    with DuckDBEngine.open(database) as engine:
        return cross_check.run(engine, day, roles=scenario.ROLES)


def test_the_job_assigns_a_tenth_of_a_region_s_decisions_at_least_one_to_another_region(decided):
    written = run(decided)

    [item] = cross_checks(decided)
    assert written == 1
    assert (item["decided_region"], item["region"], item["origin"]) == ("South Asia", "Eastern and Southern Africa",
                                                                         "quarterly")
    # Ten business days from Monday, January 4, 2027, the day it was assigned, is Friday, January 15.
    assert (item["entered_on"], item["due_on"]) == (RUN, dt.date(2027, 1, 15))


def test_a_second_run_in_the_same_quarter_writes_nothing_new(decided):
    run(decided)

    assert run(decided, RUN + dt.timedelta(days=3)) == 0
    assert len(cross_checks(decided)) == 1


def test_twenty_decisions_give_two_cross_checks(decided):
    """Twenty decisions in South Asia in the quarter: a tenth of them is two."""
    with DuckDBEngine.open(decided) as engine:
        result = engine.run("SELECT * FROM strata.ops.lesson_review_items WHERE kind = 'new' LIMIT 1")
        template = dict(zip(result.columns, result.rows[0], strict=True))
        acts = engine.run("SELECT * FROM strata.ops.lesson_review_acts WHERE item_id = :item_id AND act = 'decide'",
                          {"item_id": template["item_id"]})
        act = dict(zip(acts.columns, acts.rows[0], strict=True))
        for number in range(17):
            item_id = f"new-made-up-{number:02d}"
            engine.insert_rows("strata.ops.lesson_review_items", tuple(template),
                               [tuple({**template, "item_id": item_id}.values())])
            engine.insert_rows("strata.ops.lesson_review_acts", tuple(act),
                               [tuple({**act, "act_id": f"act-{number}", "item_id": item_id}.values())])

    assert run(decided) == 2
    assert {item["region"] for item in cross_checks(decided)} == {"Eastern and Southern Africa"}


def test_only_the_assigned_region_cross_checks_and_a_disagreement_starts_a_re_check_where_it_was_decided(decided):
    run(decided)
    [item] = cross_checks(decided)
    review = scenario.review_on(RUN + dt.timedelta(days=1))

    with DuckDBEngine.open(decided) as engine:
        in_asha_s_queue = [row["item_id"] for group in review.queue(engine, scenario.ASHA)["groups"].values()
                           for row in group]
        asha = review.item(engine, scenario.ASHA, item["item_id"])
        wanjiru = review.queue(engine, scenario.WANJIRU)["groups"]["you"]
        saved = review.act(engine, scenario.WANJIRU, item["item_id"], "cross_check",
                           {"expected_stage": "cross_check", "agree": False,
                            "reason": "The quote supports the lesson only for works contracts."}, engine)

    # South Asia's queue leaves it out, and its page opens read-only for South Asia's reviewers.
    assert item["item_id"] not in in_asha_s_queue
    assert (asha["read_only"], asha["can"]["reason_code"]) == (True, "same_region")
    assert [row["item_id"] for row in wanjiru] == [item["item_id"]]
    assert saved["item"]["outcome"]["outcome"] == "disagree"
    with DuckDBEngine.open(decided, read_only=True) as engine:
        result = engine.run("SELECT kind, lesson_id, proposal_id, region, origin, origin_reason "
                            "FROM strata.ops.lesson_review_items WHERE origin = 'cross_check'")
    [(kind, lesson_id, proposal_id, region, origin, reason)] = result.rows
    assert (region, origin, reason) == ("South Asia", "cross_check", "The quote supports the lesson only for works contracts.")
    # The quarter's fixed draw is IEG's own lesson (lesson-cfdf000a46 in the recorded answers), which was added, so
    # the disagreement re-checks that lesson rather than queueing a proposal again.
    assert (kind, lesson_id, proposal_id) == ("recheck", "lesson-cfdf000a46", None)
