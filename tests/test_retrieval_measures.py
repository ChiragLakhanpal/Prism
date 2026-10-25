"""The retrieval loop's measures (ticket 32; docs/PLAN.md section 11), through seams 3 and 1: "Wrong passage" reports
per 100 sources opened, each week, and what each person's reports did ("You marked two passages as wrong; one is
fixed, and 14 answers now cite the right paragraph"), computed by the weekly retrieval run and stored in strata.ops.

The story, in the week of Monday, October 19, 2026: five people open five sources each in the evidence drawer (25
sources opened). Ana marks paragraph 54 as the wrong passage and Kofi marks paragraph 55; Priya marks 54 as not
useful. Daniel ranks 54 lower for questions like Ana's. Sara then asks the same question: paragraph 54 now ranks
below the passages search_passages returns, so her answer cites paragraph 55 and not 54. The next Monday, one more
source is opened. The expected values are counted by hand from that story: 2 "Wrong passage" reports in 25 opens
is 8.0 per 100, 1 "Not useful" is 4.0, and a week with one open has no rate.
"""

import datetime as dt

import pytest

from retrieval_scenario import ANA, DANIEL, KOFI, NOOR, PARAGRAPH_55, PRIYA, SARA, Loop

SOURCES = [f"strata.gold.passage:31525018/v1/{n}" for n in (53, 54, 55, 56, 57)]


@pytest.fixture
def loop(fixture_db, tmp_path):
    found = Loop(fixture_db, tmp_path)
    yield found
    found.close()


def latest(loop, table: str) -> list[dict]:
    return loop.rows(f"SELECT * FROM {table} WHERE computed_at = (SELECT max(computed_at) FROM {table})")


def test_reports_per_100_sources_opened_and_each_persons_fixed_and_recited_counts_are_stored(loop):
    for who in (ANA, KOFI, PRIYA, SARA, NOOR):
        for source in SOURCES:
            assert loop.opened(who, source).json() == {"recorded": True}
    ana, kofi = loop.ask(ANA), loop.ask(KOFI)
    loop.report(ANA, ana, reason="Not why these were advertised again.")
    loop.report(KOFI, kofi, evidence_id=PARAGRAPH_55)
    loop.report(PRIYA, loop.ask(PRIYA), kind="not_useful")
    groups = loop.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]
    [paragraph_54] = [row for row in groups if row["passage_id"] == "31525018/v1/54"]
    assert loop.decide(DANIEL, paragraph_54["group_id"]).status_code == 200
    sara = loop.ask(SARA)
    cited = {row["evidence_id"] for row in loop.rows(
        f"SELECT evidence_id FROM strata.ops.answer_citations WHERE run_id = '{sara}'")}
    assert PARAGRAPH_55 in cited and "strata.gold.passage:31525018/v1/54" not in cited
    loop.later(days=3)
    loop.opened(ANA, "strata.gold.passage:31525018/v1/58")

    loop.weekly()

    weekly = {(row["week_start"], row["kind"]): (row["reports"], row["opened"], row["per_100"])
              for row in latest(loop, "strata.ops.retrieval_feedback_weekly")}
    assert weekly == {
        (dt.date(2026, 10, 19), "wrong_passage"): (2, 25, 8.0),
        (dt.date(2026, 10, 19), "not_useful"): (1, 25, 4.0),
        (dt.date(2026, 10, 26), "wrong_passage"): (0, 1, None),
        (dt.date(2026, 10, 26), "not_useful"): (0, 1, None),
    }
    people = {row["viewer_id"]: (row["marked"], row["fixed"], row["waiting"], row["kept"], row["recited"])
              for row in latest(loop, "strata.ops.retrieval_feedback_viewers")}
    # Priya's report is "Not useful", which the sentence does not count.
    assert people == {"id-ana.example@worldbank.org": (1, 1, 0, 0, 1), "id-kofi.example@worldbank.org": (1, 0, 1, 0, 0)}
