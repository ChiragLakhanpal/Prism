"""What the measures say, and each loop's indicators, as the nightly job writes them (ticket 45; the 45 design
brief, sections 6.3, 7.3 and 7.4), on the made-up month of tests/dashboard_seed.py and on an empty catalog.

Each sentence comes from the copy file's templates and reads its numbers through the dashboard's own queries, so a
counter and its sentence never disagree. The expected sentences are written out from the seed by hand.
"""

import datetime as dt

import pytest

from dashboard_seed import TODAY, rows, seeded
from strata.dashboard import findings
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine

WRITTEN_AT = dt.datetime(2026, 10, 23, 9, 30, tzinfo=dt.UTC)


@pytest.fixture(scope="module")
def written():
    engine = seeded()
    findings.write(engine, "run-23", lambda: WRITTEN_AT)
    yield engine
    engine.close()


@pytest.fixture(scope="module")
def empty():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        findings.write(engine, "run-1", lambda: WRITTEN_AT)
        yield engine


def said(engine, page):
    return {row["about"]: (row["finding"], row["measured"]) for row in rows(engine, f"findings_{page}")}


def test_governance_says_how_last_night_s_run_ended_what_azure_cost_and_what_was_removed(written):
    found = said(written, "governance")

    assert list(found) == ["Nightly runs and checks", "Azure spend", "Personal data", "Who queried what", "Lineage"]
    assert found["Nightly runs and checks"] == (
        "The nightly run of October 23 stopped at the Read and index new documents task, after two of 10 tasks had "
        "finished. The tasks that finished ran three quality checks, and three passed.", "Oct 23, 2026")
    assert found["Azure spend"] == (
        "By October 22, the latest day with cost data, my Azure resources had cost US$7.80 of the US$197.00 budget for "
        "the free credit, which ends November 10, 2026.", "Oct 22, 2026")
    assert found["Personal data"][0] == (
        "Up to October 21, I removed contact details from four procurement notices as I took them in: two names, six "
        "email addresses and four phone numbers. The latest check found none left.")
    assert found["Who queried what"][0] == (
        "I can't show who queried what, because this workspace doesn't let me read its query history.")
    assert found["Lineage"][0] == (
        "All three answer runs in the 7 days to October 23 lead back to their tool calls and the tables those calls "
        "read.")


def test_a_night_with_a_failed_check_names_what_it_found(written):
    text, night = findings.runs(written, dt.date(2026, 10, 22))

    assert text == ("The nightly run of October 22 finished all 10 tasks in 30 minutes. Of its four quality checks, "
                    "three passed. The one that failed found three duplicate rows in strata.gold.contract.")
    assert night == dt.date(2026, 10, 22)


def test_ai_quality_says_how_the_answers_did_and_how_each_loop_is_learning(written):
    found = said(written, "ai")

    assert list(found) == ["Benchmark", "Foundry evaluations", "Checks on answers", "Knowledge loop", "Retrieval loop",
                           "Estimates loop", "Adoption"]
    assert found["Benchmark"][0] == (
        "In the full gate of October 20, 45 of 52 benchmark questions passed, and I refused six of the six questions I "
        "must refuse. It missed one target, Documents, at 80 percent against a target of 90 percent.")
    assert found["Foundry evaluations"][0] == (
        "Of the 40 answers Microsoft Foundry scored on October 20, 34 met its threshold for groundedness, 36 for "
        "relevance, 30 for task adherence and 38 for tool use.")
    assert found["Checks on answers"][0] == (
        "In the 7 days to October 23, I removed three of the 20 sentences I wrote. No one reason was the most common, "
        "because three reasons tied at one each. I held back in two of the three answers I gave. No one reason was the "
        "most common, because two reasons tied.")
    assert found["Knowledge loop"][0] == (
        "In the 90 days to October 23, lead procurement specialists decided three proposed lessons, two of them within "
        "10 business days of their report being published. In the hindsight test of October 15, I caught 14 of 30 "
        "blamed risks across 12 projects, at five risks per package. A checklist of the sector's five commonest risks "
        "caught 9. The 95 percent interval runs from 25 to 58 percent.")
    assert found["Retrieval loop"][0] == (
        "On the held-out set, in the evaluation of October 10, precision at 10 was 0.62 and recall at 20 was 0.71. In "
        "the 7 days to October 18, people opened 40 sources and marked three passages as wrong, or 7.5 for every 100 "
        "sources opened. They marked two as not useful.")
    assert found["Estimates loop"][0] == (
        "Of the 60 packages that finished in the 12 months to September 2026, 52 finished inside my 8-in-10 range, or "
        "87 percent. That is outside the 75 to 85 percent target, as it has been for one month. I raised a retrain on "
        "October 1, because coverage stayed outside the target for two months. Plan rows dated within 14 days of a "
        "date I offered were a median of 12 days from their actual dates, against 30 days for other plan rows.")
    assert found["Adoption"][0] == (
        "In the week of Monday, October 12, two people used Strata. In the 90 days to October 23, authors marked two "
        "drafts as checked and exported one. Of the nine plan rows published after I showed a range for their package, "
        "four were dated within 14 days of a date I offered.")


def test_the_week_a_sentence_names_is_the_latest_finished_one_never_a_week_still_under_way():
    """Ticket 32's weeks start on Monday. On Friday October 23 the week of October 19 is still under way, so the
    sentence names the 7 days to Sunday October 18; on a Sunday, the week that ends that day is finished."""
    assert findings.last_finished_week(dt.date(2026, 10, 23)) == dt.date(2026, 10, 18)
    assert findings.last_finished_week(dt.date(2026, 10, 19)) == dt.date(2026, 10, 18)
    assert findings.last_finished_week(dt.date(2026, 10, 25)) == dt.date(2026, 10, 25)


def test_a_reason_is_named_the_most_common_only_when_no_other_reason_has_its_count():
    assert findings._tied([{"sentences": 2}, {"sentences": 1}], "sentences") == 0
    assert findings._tied([{"answers": 1}, {"answers": 1}, {"answers": 1}], "answers") == 3
    assert findings._tied([{"answers": 2}, {"answers": 2}, {"answers": 1}], "answers") == 2


def test_each_loop_s_indicators_are_six_rows_in_loop_order_with_targets_and_where_each_stands_in_words(written):
    found = rows(written, "loop_indicators")

    assert [(row["loop"], row["indicator"], row["kind"], row["latest"], row["target"], row["against"])
            for row in found] == [
        ("Knowledge", "Days from publication to decision", "Leading", "3 decisions", "Within 10 business days",
         "2 of 3 within it"),
        ("Knowledge", "Blamed risks a lesson covered at approval", "Lagging", "18 of 30", "None set", "Not compared"),
        ("Retrieval", "Wrong-passage reports per 100 sources opened", "Leading", "1 in 12 opened", "None set",
         "Not compared"),
        ("Retrieval", "Precision at 10 and recall at 20", "Lagging", "0.62 and 0.71, held-out set",
         "No loss against the last run", "Matched or beat the last run"),
        ("Estimates", "Rolling coverage of the 8-in-10 range", "Leading", "87%, 52 of 60", "75–85%",
         "Outside for 1 month"),
        ("Estimates", "Plan accuracy", "Lagging", "12 against 30 days", "None set", "Not compared")]
    assert all(row["measured"] for row in found)


def test_before_anything_happened_each_finding_says_what_will_fill_it_and_measured_says_not_yet(empty):
    governance, ai = said(empty, "governance"), said(empty, "ai")

    assert governance["Nightly runs and checks"] == (
        "I have no nightly runs recorded yet. Each run and its quality checks appear here after the job's first night.",
        "Not yet")
    assert governance["Azure spend"][0] == (
        "I have no Azure cost data yet. The daily cost pull adds each day's charges once Azure reports them.")
    assert governance["Personal data"][0] == (
        "I haven't taken in any procurement notices yet, so I have removed no contact details.")
    assert ai["Benchmark"] == ("No full gate has run yet. Each run of the full gate command adds its results here.",
                               "Not yet")
    assert ai["Estimates loop"][0] == "No monthly watch of the time estimate has run yet."
    assert ai["Adoption"][0] == "No one used Strata in the week of Monday, October 12."
    assert {row["latest"] for row in rows(empty, "loop_indicators")} == {"None yet"}
    assert {row["against"] for row in rows(empty, "loop_indicators")} == {"Not compared"}


def test_the_cost_pull_writes_only_the_azure_spend_sentence(written):
    findings.write(written, "pull-2", lambda: WRITTEN_AT + dt.timedelta(hours=1), sections=("spend",))

    newest = written.run("SELECT section FROM strata.ops.dashboard_findings WHERE run_id = 'pull-2'").rows
    assert newest == (("spend",),)
    assert said(written, "governance")["Azure spend"][1] == "Oct 22, 2026"


def test_a_lesson_counts_within_the_limit_by_the_lesson_review_s_own_business_days():
    """lesson_review.business_days is 10, and the clock skips weekends: a Friday report decided ten business days
    later is within it, and one decided on the eleventh is not."""
    friday = dt.date(2026, 9, 25)

    assert findings.within_limit(friday, dt.date(2026, 10, 9))
    assert not findings.within_limit(friday, dt.date(2026, 10, 12))
    assert TODAY.weekday() == 4


class Refusing:
    """A seeded engine that raises its own error, as Spark raises AnalysisException rather than EngineError, for any
    query that names one of the given tables."""

    def __init__(self, engine, *names):
        self._engine, self._names = engine, names

    def run(self, sql, params=None):
        if any(name in sql for name in self._names):
            raise RuntimeError(f"[TABLE_OR_VIEW_NOT_FOUND] {self._names[0]} cannot be read")
        return self._engine.run(sql, params)

    def __getattr__(self, name):
        return getattr(self._engine, name)


def test_a_workspace_that_hides_its_query_history_still_gets_every_finding():
    """On Databricks the nightly job runs on Spark, which raises its own error when system.access can't be read. The
    Who queried what row says so, and the job's task goes on (the 45 brief, section 6.4)."""
    engine = seeded()
    try:
        findings.write(Refusing(engine, "system.access"), "run-23", lambda: WRITTEN_AT)
        found = said(engine, "governance")
    finally:
        engine.close()

    assert found["Who queried what"][0] == (
        "I can't show who queried what, because this workspace doesn't let me read its query history.")
    assert list(found) == ["Nightly runs and checks", "Azure spend", "Personal data", "Who queried what", "Lineage"]


def test_a_section_that_fails_is_left_out_and_the_others_are_written(caplog):
    engine = seeded()
    try:
        findings.write(Refusing(engine, "strata.ops.cost_pulls", "strata.ops.cost_daily"), "run-23",
                       lambda: WRITTEN_AT)
        governance, ai = said(engine, "governance"), said(engine, "ai")
        indicators = rows(engine, "loop_indicators")
    finally:
        engine.close()

    assert list(governance) == ["Nightly runs and checks", "Personal data", "Who queried what", "Lineage"]
    assert len(ai) == 7 and len(indicators) == 6
    assert "spend" in caplog.text
