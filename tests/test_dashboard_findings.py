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


def week_of_reports(engine, week, wrong, not_useful, opened, measured_at):
    """One measure of a week's passage reports, as the weekly retrieval run stores it (ticket 32)."""
    rate = (lambda reports: round(100 * reports / opened, 1) if opened >= 20 else None)
    engine.insert_rows("strata.ops.retrieval_feedback_weekly",
                       ("week_start", "kind", "reports", "opened", "per_100", "computed_at", "public_from"),
                       [(week, kind, reports, opened, rate(reports), measured_at, measured_at.date())
                        for kind, reports in (("wrong_passage", wrong), ("not_useful", not_useful))])


def test_the_week_a_sentence_names_is_the_newest_one_the_weekly_run_measured_after_it_ended():
    """Ticket 32's weeks run Monday to Sunday in UTC, and the weekly retrieval run measures them on Mondays at 06:30 in
    Washington, after the nightly job. So on Monday night the newest measure of last week was taken in its first hours,
    and the sentence names the week before it; once a run has measured a week after it ended, the sentence names that
    week, and a week the run found nothing in says no one opened a source (review round 2, N1)."""
    engine = seeded()  # the seed's weekly run measured both weeks on Friday, October 23
    try:
        monday_night = findings.retrieval(engine, dt.date(2026, 10, 26))
        week_of_reports(engine, dt.date(2026, 10, 19), 2, 1, 30, dt.datetime(2026, 10, 26, 10, 30, tzinfo=dt.UTC))
        tuesday_night = findings.retrieval(engine, dt.date(2026, 10, 27))
        week_of_reports(engine, dt.date(2026, 10, 19), 2, 1, 30, dt.datetime(2026, 11, 2, 11, 30, tzinfo=dt.UTC))
        a_week_later = findings.retrieval(engine, dt.date(2026, 11, 3))
    finally:
        engine.close()

    assert monday_night[0].endswith(
        "In the 7 days to October 18, people opened 40 sources and marked three passages as wrong, or 7.5 for every 100 "
        "sources opened. They marked two as not useful.")
    assert tuesday_night[0].endswith(
        "In the 7 days to October 25, people opened 30 sources and marked two passages as wrong, or 6.7 for every 100 "
        "sources opened. They marked one as not useful.")
    assert a_week_later[0].endswith("No one opened a source from an answer in the 7 days to November 1.")


def test_before_the_weekly_run_has_measured_a_finished_week_the_sentence_says_nothing_of_reports(empty):
    assert said(empty, "ai")["Retrieval loop"] == ("No retrieval evaluation has run yet.", "Not yet")


def test_each_reason_row_says_how_many_reasons_share_its_count_so_a_tie_is_a_query_column(written):
    """The Checks on answers sentence names the most common reason only when no other reason has its count, and says
    how many tied from this column, never from a count of its own (CLAUDE.md rule 1; review round 2, N3)."""
    week = {"date_from": TODAY - dt.timedelta(days=6)}

    assert [(row["reason"], row["sentences"], row["reasons_at_this_count"])
            for row in rows(written, "removed_reasons", **week)] == [
        ("Its sources don't say this", 1, 3), ("No record supports a number or date", 1, 3),
        ("Quote not on the page it cites", 1, 3)]
    assert [(row["reason"], row["answers"], row["reasons_at_this_count"])
            for row in rows(written, "held_reasons", **week)] == [
        ("Outside what my model learned from", 1, 2), ("Too few comparable packages for a range", 1, 2)]


def test_each_loop_s_indicators_are_six_rows_in_loop_order_with_targets_and_where_each_stands_in_words(written):
    found = rows(written, "loop_indicators")

    assert [(row["loop"], row["indicator"], row["kind"], row["latest"], row["target"], row["against"])
            for row in found] == [
        ("Knowledge", "Days from publication to decision", "Leading", "3 decisions", "Within 10 business days",
         "2 of 3 within it"),
        ("Knowledge", "Blamed risks a lesson covered at approval", "Lagging", "18 of 30", "None set", "Not compared"),
        ("Retrieval", "Wrong-passage reports per 100 sources opened", "Leading", "7.5 per 100, 40 opened", "None set",
         "Not compared"),
        ("Retrieval", "Precision at 10 and recall at 20", "Lagging", "0.62 and 0.71, held-out set",
         "No loss against the last run", "Matched or beat the last run"),
        ("Estimates", "Rolling coverage of the 8-in-10 range", "Leading", "87%, 52 of 60", "75–85%",
         "Outside for 1 month"),
        ("Estimates", "Plan accuracy", "Lagging", "12 against 30 days", "None set", "Not compared")]
    assert all(row["measured"] for row in found)
    # The same week as the Retrieval loop sentence, "the 7 days to October 18" (review round 2, N2)
    assert found[2]["measured"] == "Oct 12, 2026"


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


# ── How a night ended, written once the night has ended ──────────────────

def a_night(monkeypatch, failing_task=None):
    """One night of the job through nightly.run_task, as each task of the job calls it, on an empty catalog: every
    task's work is a stand-in, each task runs one check, measure_data_readiness's check finds three duplicate rows, and
    failing_task's work raises. The tasks start three minutes apart from 03:00 in Washington on October 23."""
    from strata.lakehouse import nightly, quality

    def work(key):
        def done(run):
            if key == failing_task:
                raise RuntimeError(f"{key} could not finish")
            return 0
        return done

    def one_check(engine, task_key):
        return [quality.Result("duplicates", "strata.gold.contract", None, 3 if task_key == "measure_data_readiness"
                               else 0)]

    for key in nightly.TASKS:
        monkeypatch.setitem(nightly.TASKS, key, work(key))
    monkeypatch.setattr(quality, "check", one_check)
    engine = DuckDBEngine.open()
    catalog.build(engine)
    now = [dt.datetime(2026, 10, 23, 7, 0, tzinfo=dt.UTC)]
    for key in nightly.TASKS:
        try:
            nightly.run_task(engine, key, "run-23", fetch=None, clock=lambda: now[0])
        except RuntimeError:
            break  # the job's next task depends on this one, so it never starts
        now[0] += dt.timedelta(minutes=3)
    return engine


def test_a_night_that_stops_at_its_last_task_says_so_and_counts_every_check_the_counter_counts(monkeypatch):
    """The Nightly runs and checks sentence is written once the night has ended, never by a task still under way, so
    it names the task that stopped the run and counts the checks of every task that finished (verify round 2, F1)."""
    engine = a_night(monkeypatch, failing_task="refresh_drafts")
    try:
        found, counter = said(engine, "governance"), rows(engine, "kpi_checks_failed")[0]
    finally:
        engine.close()

    assert found["Nightly runs and checks"] == (
        "The nightly run of October 23 stopped at the Mark drafts that cite a changed lesson task, after nine of 10 "
        "tasks had finished. The tasks that finished ran nine quality checks, and eight passed.", "Oct 23, 2026")
    assert counter["display"] == "1 of 9"


def test_a_night_whose_tasks_all_finish_counts_the_checks_of_the_last_two_tasks_too(monkeypatch):
    engine = a_night(monkeypatch)
    try:
        found, counter = said(engine, "governance"), rows(engine, "kpi_checks_failed")[0]
    finally:
        engine.close()

    assert found["Nightly runs and checks"] == (
        "The nightly run of October 23 finished all 10 tasks in 27 minutes. Of its 10 quality checks, nine passed. The "
        "one that failed found three duplicate rows in strata.gold.contract.", "Oct 23, 2026")
    assert counter["display"] == "1 of 10"


def test_the_fixture_s_night_is_described_once_with_every_check_its_counter_counts(fixture_db):
    """The fixture's own nightly run, with every real task: one Nightly runs and checks sentence, written after the last
    task, and it counts the same checks as the counter beside it."""
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        [run_id] = [row[0] for row in engine.run("SELECT DISTINCT run_id FROM strata.ops.pipeline_runs").rows]
        written = engine.run("SELECT f.finding, f.written_at, (SELECT max(p.finished_at) FROM strata.ops.pipeline_runs "
                             "AS p) AS last_task FROM strata.ops.dashboard_findings AS f WHERE f.section = 'runs' "
                             "AND f.run_id = :run_id", {"run_id": run_id}).rows
        counter = rows(engine, "kpi_checks_failed")[0]

    [(finding, written_at, last_task)] = written
    assert written_at >= last_task
    assert counter["display"] == f"0 of {counter['denominator']}"
    assert finding.endswith(f"and all {counter['denominator']} quality checks passed.")
