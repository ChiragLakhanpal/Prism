"""Assertions and disagreements at seam 1, the lakehouse run over the fixture (ticket 20).

Ratings, dates and amounts from records and documents become dated assertions in strata.gold.assertion,
and the run finds the disagreements between them in strata.gold.disagreement, with the assertion the
evidence ladder (config/evidence_ladder.toml) leans on. Expected values come from
tests/ground_truth/values.toml, which quotes each ISR, the ICR and the ICR Reviews with their pages,
never from the code.
"""

import datetime as dt
import shutil
import tomllib
from pathlib import Path

import pytest

from strata.knowledge import assertions, batch
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
ISR = "Implementation Status and Results Report"


def value(key: str):
    return TRUTH[key]["value"]


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def isr_assertions(engine, attribute="pdo_progress") -> list[dict]:
    return rows(engine, "SELECT * FROM strata.gold.assertion WHERE subject_id = :subject AND attribute = :attribute "
                        "AND document_type = :isr ORDER BY made_at", subject="P130164", attribute=attribute, isr=ISR)


# ── Assertions ───────────────────────────────────────────────────────────

def test_each_isr_rates_progress_for_the_period_since_the_isr_before_it(engine):
    found = isr_assertions(engine)

    assert [row["value"] for row in found] == [value(f"isr-{n}-rating") for n in range(1, 14)]
    assert [row["made_at"] for row in found] == [value(f"isr-{n}-date") for n in range(1, 14)]
    assert [row["sequence"] for row in found] == list(range(1, 14))
    isr_7 = found[6]
    assert isr_7["field_name"] == "Progress towards achievement of PDO"
    assert (isr_7["period_start"], isr_7["period_end"]) == (value("isr-6-date") + dt.timedelta(days=1),
                                                            value("isr-7-date"))
    assert isr_7["public_from"] == value("isr-7-date")
    assert (isr_7["evidence_tier"], isr_7["form"]) == ("isr", "rating_field")
    # The passage ticket 18 issued for ISR 7's overall ratings, on its first page, which a claim cites.
    assert isr_7["evidence_id"] == "strata.gold.passage:26733307/v1/s4"
    assert isr_7["pdf_page"] == TRUTH["isr-7-rating"]["pdf_page"]


def by_document(engine, document_id: str) -> dict[str, dict]:
    return {row["attribute"]: row for row in rows(
        engine, "SELECT * FROM strata.gold.assertion WHERE document_id = :document_id", document_id=document_id)}


def test_the_icrs_account_of_the_mid_term_review_is_an_assertion_about_that_moment(engine):
    """The batch model read paragraph 78 (tests/fixtures/azure/batch_assertions.json); its quote was found
    word for word on PDF page 27, and the mid-term review's date comes from the ISRs' key dates."""
    paragraph = by_document(engine, "31525018")["pdo_progress"]

    assert (paragraph["subject_kind"], paragraph["subject_id"]) == ("project", "P130164")
    assert (paragraph["value_form"], paragraph["judgment"]) == ("judgment", "unsatisfactory")
    assert paragraph["period_event"] == "mid_term_review"
    assert paragraph["period_start"] == paragraph["period_end"] == value("isr-7-mid-term-review")
    assert value("mid-term-review") == value("isr-7-mid-term-review")
    assert paragraph["made_at"] == value("icr-date")
    assert paragraph["public_from"] == value("icr-disclosed")
    assert (paragraph["evidence_tier"], paragraph["form"]) == ("icr", "narrative")
    assert paragraph["evidence_id"] == "strata.gold.passage:31525018/v1/78"
    assert paragraph["pdf_page"] == TRUTH["icr-para-78"]["pdf_page"]
    assert paragraph["quote"] == value("icr-para-78")
    assert paragraph["read_by"].startswith("gpt-5.4-nano")


def test_the_pads_overall_risk_is_an_assertion_about_the_appraisal_in_the_pad_tier(engine):
    """The batch model read the PAD like the ICR (tests/fixtures/azure/batch_assertions.json): its overall risk,
    rated in paragraph 49 on PDF page 26, comes back in the pad tier ("Written at appraisal"), for the
    appraisal, which the PAD dates for itself, and public from the day the documents API disclosed it."""
    shelf = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["stress_shelf"]
    risk = by_document(engine, "18381488")["overall_risk"]

    assert (risk["subject_kind"], risk["subject_id"], risk["value"]) == ("project", "P130164", "Substantial")
    assert (risk["evidence_tier"], risk["form"]) == ("pad", "narrative")
    assert risk["period_event"] == "appraisal"
    assert risk["period_start"] == risk["period_end"] == risk["made_at"] == TRUTH["pad-overall-risk"]["date"]
    assert risk["public_from"].isoformat() == shelf["pad_disclosed"]["value"][:10]
    assert risk["evidence_id"] == f"strata.gold.passage:18381488/v1/{TRUTH['pad-overall-risk']['paragraph']}"
    assert (risk["pdf_page"], risk["quote"]) == (TRUTH["pad-overall-risk"]["pdf_page"], value("pad-overall-risk"))


def test_an_extracted_assertion_whose_quote_is_not_on_its_cited_page_is_rejected_and_counted(engine):
    """The recording plants one outcome rating whose words are not in paragraph 45. It never becomes an
    assertion, and the run counts it with its reason in strata.ops.assertion_rejections."""
    rejected = rows(engine, "SELECT * FROM strata.ops.assertion_rejections WHERE project_id = :project_id",
                    project_id="P130164")
    outcome = rows(engine, "SELECT value, quote FROM strata.gold.assertion WHERE document_id = :document_id "
                           "AND attribute = :attribute", document_id="31525018", attribute="outcome")

    assert [(row["document_id"], row["passage_id"], row["reason"]) for row in rejected] == [
        ("31525018", "31525018/v1/45", "quote_not_on_page")]
    assert rejected[0]["quote"] == "the overall outcome is rated Moderately Satisfactory"
    assert rejected[0]["public_from"] == value("icr-disclosed")
    assert outcome == [{"value": "Moderately Unsatisfactory",
                        "quote": "the overall outcome is rated Moderately Unsatisfactory"}]


def test_each_version_of_the_icr_review_keeps_its_ratings_and_the_reissue_replaces_the_first(engine):
    """Both ICR Reviews are report ICRR0021929. The re-issue of May 4, 2023 replaces the version of March 27,
    2020 from the day it became public (ticket 11's rule), and the first version's "Efficiency Rating ---"
    is no rating."""
    first, reissue = by_document(engine, "31906731"), by_document(engine, "34056616")

    assert set(first) == {"outcome", "bank_performance", "me_quality"}
    assert set(reissue) == {"outcome", "bank_performance", "me_quality", "efficiency"}
    assert reissue["efficiency"]["value"] == value("icr-review-efficiency-2023")
    assert {row["replaced_on"] for row in first.values()} == {value("icr-review-reissue-date")}
    assert {row["replaced_on"] for row in reissue.values()} == {None}
    assert {(row["report_number"], row["version"], row["evidence_tier"]) for row in first.values()} == {
        (value("icr-review-number-2020"), 1, "ieg")}
    assert {(row["report_number"], row["version"]) for row in reissue.values()} == {(value("icr-review-number-2023"), 2)}
    assert {row["made_at"] for row in reissue.values()} == {value("icr-review-reissue-date")}


def test_the_ieg_ratings_dataset_gives_iegs_ratings_of_the_whole_project_and_agrees_with_the_icr_review(engine):
    """The IEG ratings dataset repeats IEG's ratings, so its row is in the ieg tier, a rating in its own field
    with the dataset's field name. It gives no date, so it is public from June 30 of its evaluation year
    (ticket 17). Its ratings match the ICR Review's, so it is in no disagreement."""
    found = {row["attribute"]: row for row in rows(
        engine, "SELECT * FROM strata.gold.assertion WHERE source_key = :source AND subject_id = :subject",
        source="ieg_ratings", subject="P130164")}

    assert {key: row["value"] for key, row in found.items()} == {
        "outcome": value("ieg-outcome-p130164"), "bank_performance": value("ieg-bank-performance-p130164"),
        "me_quality": value("ieg-me-quality-p130164")}
    outcome = found["outcome"]
    assert (outcome["field_name"], outcome["evidence_tier"], outcome["form"]) == ("outcome", "ieg", "rating_field")
    assert outcome["evidence_id"] == "strata.gold.ieg_rating:P130164/ICRR/2020"
    assert outcome["made_at"] == outcome["public_from"] == dt.date(value("ieg-evaluation-fy-p130164"), 6, 30)
    assert outcome["period_event"] == "whole_project"
    icr = by_document(engine, "31525018")["outcome"]
    assert (outcome["period_start"], outcome["period_end"]) == (icr["period_start"], icr["period_end"])
    sides = rows(engine, "SELECT a.assertion_id FROM strata.gold.disagreement AS d JOIN strata.gold.assertion AS a "
                         "ON a.assertion_id IN (d.first_assertion_id, d.second_assertion_id) WHERE a.source_key = :source",
                 source="ieg_ratings")
    assert sides == []


def test_every_assertion_from_a_field_keeps_a_field_name_the_evidence_ladder_lists_for_its_attribute(engine):
    """The ladder is the one place that says which field means which attribute. An account told in running
    text keeps the report's own words instead, such as "achievement of part of the PDO"."""
    from strata import config

    ladder = config.load_ladder()
    found = rows(engine, "SELECT DISTINCT attribute, field_name, form FROM strata.gold.assertion WHERE form <> :text",
                 text="narrative")

    assert {row["form"] for row in found} == {"rating_field", "contract_record", "award_notice", "plan_row"}
    assert [row for row in found if row["field_name"] not in ladder.attribute(row["attribute"]).names] == []


def test_the_run_reads_the_records_of_every_project_it_holds_records_for(engine):
    """A project's records are read whether or not Strata has read its documents (ticket 43 brought the
    record-only projects back, once each family is read with one query for every project)."""
    with_records = {row["project_id"] for row in rows(
        engine, "SELECT DISTINCT project_id FROM strata.gold.contract WHERE step_reference IS NOT NULL "
                "AND contract_signing_date IS NOT NULL AND source <> :notices", notices="notices")}
    asserted = {row["project_id"] for row in rows(
        engine, "SELECT DISTINCT project_id FROM strata.gold.assertion WHERE form = :form", form="contract_record")}

    assert len(with_records) > 1
    assert with_records <= asserted


def test_the_source_registry_names_the_datasets_whose_rows_are_records_of_a_signed_contract(engine):
    """A third awards dataset is one entry in config/sources.toml with assertion_form = "contract_record", and
    no code change (CLAUDE.md rule 9). The run's contract records come only from the sources marked so."""
    from strata import config

    marked = {key for key, source in config.load_sources().items() if source.assertion_form == "contract_record"}
    found = {row["source_key"] for row in rows(
        engine, "SELECT DISTINCT source_key FROM strata.gold.assertion WHERE form = :form", form="contract_record")}

    assert marked == {"awards", "awards_fy2001_2016"}
    assert found and found <= marked


# ── Disagreements ────────────────────────────────────────────────────────

ISR_7 = "strata.gold.passage:26733307/v1/s4#P130164/pdo_progress"
PARAGRAPH_78 = "strata.gold.passage:31525018/v1/78#P130164/pdo_progress"


def disagreements(engine, subject_id: str) -> list[dict]:
    return rows(engine, "SELECT * FROM strata.gold.disagreement WHERE subject_id = :subject_id "
                        "ORDER BY attribute, public_from", subject_id=subject_id)


def test_isr_7_and_the_icrs_paragraph_78_are_one_disagreement_and_the_ladder_leans_on_the_icr(engine):
    """Criterion 1 at seam 1: the mid-term review (May 16, 2016) falls in ISR 7's period, the day after ISR 6
    to August 26, 2016, and in no other ISR's. Satisfactory and "part of the PDO was compromised" cannot both
    be true, and progress towards the PDO is an outcome judgment, so the ICR outranks the ISR."""
    found = [row for row in disagreements(engine, "P130164") if row["attribute"] == "pdo_progress"]

    assert [(row["first_assertion_id"], row["second_assertion_id"]) for row in found] == [(ISR_7, PARAGRAPH_78)]
    [paragraph] = found
    assert (paragraph["lean_assertion_id"], paragraph["rule_id"]) == (PARAGRAPH_78, "outcome")
    assert paragraph["period_event"] == "mid_term_review"
    assert paragraph["period_start"] == paragraph["period_end"] == value("mid-term-review")
    assert paragraph["public_from"] == value("icr-disclosed")
    assert paragraph["replaced_on"] is None


def test_isr_ratings_of_successive_periods_never_disagree_with_each_other(engine):
    """Criterion 2 at seam 1: ISRs 1 to 13 rate successive periods, so a changed rating is a trajectory."""
    between_isrs = rows(engine, "SELECT d.disagreement_id FROM strata.gold.disagreement AS d "
                                "JOIN strata.gold.assertion AS a ON a.assertion_id = d.first_assertion_id "
                                "JOIN strata.gold.assertion AS b ON b.assertion_id = d.second_assertion_id "
                                "WHERE a.evidence_tier = :isr AND b.evidence_tier = :isr", isr="isr")

    assert len(isr_assertions(engine)) == 13
    assert between_isrs == []


def test_the_reissued_icr_reviews_efficiency_rating_disagrees_with_the_icrs_and_ieg_outranks_the_icr(engine):
    """The ICR rated efficiency Substantial (paragraph 44); the 2023 re-issue of the ICR Review rated it Modest.
    The 2020 version gave no efficiency rating, so it is in no disagreement."""
    [efficiency] = [row for row in disagreements(engine, "P130164") if row["attribute"] == "efficiency"]

    assert efficiency["first_assertion_id"] == "strata.gold.passage:31525018/v1/44#P130164/efficiency"
    assert efficiency["second_assertion_id"] == "strata.gold.passage:34056616/v2/5#P130164/efficiency"
    assert (efficiency["lean_assertion_id"], efficiency["rule_id"]) == (efficiency["second_assertion_id"], "outcome")
    assert efficiency["public_from"] == value("icr-review-reissue-date")


def test_two_signed_amounts_within_the_tolerance_share_are_not_a_disagreement(engine, copy_db, tmp_path):
    """The awards dataset gives KE-KIMAWASCO-141042-CW-RFB's contract 7,741,614.92 US dollars and the plan
    7,741,367.65, a gap of less than 0.1 percent, likely two exchange rates. Below the share in
    config/thresholds.toml ([disagreements] amount_tolerance_share) that is not a disagreement; with a share
    of 0 it is, and a wider gap, as for KE-KIMAWASCO-142995-CW-RFB, always is."""
    from strata import config

    def amounts(held, subject):
        return [row for row in disagreements(held, subject) if row["attribute"] == "signed_amount_usd"]

    assert amounts(engine, "KE-KIMAWASCO-141042-CW-RFB") == []
    assert amounts(engine, "KE-KIMAWASCO-142995-CW-RFB") != []
    exact = tmp_path / "thresholds.toml"
    exact.write_text((ROOT / "config" / "thresholds.toml").read_text().replace(
        "amount_tolerance_share = 0.001", "amount_tolerance_share = 0", 1))

    assertions.redetect(copy_db, ["P156634"], config.load_ladder(), config.load_thresholds(exact))

    assert len(amounts(copy_db, "KE-KIMAWASCO-141042-CW-RFB")) == 1


def test_every_assertion_has_its_subject_attribute_value_period_dates_source_and_evidence_tier(engine):
    """Criterion 8: the schema every assertion keeps (spec, "The knowledge model")."""
    required = ("assertion_id", "subject_kind", "subject_id", "project_id", "attribute", "attribute_kind",
                "field_name", "value", "value_form", "period_event", "period_start", "period_end", "made_at",
                "public_from", "evidence_tier", "form", "source_key", "document_id", "passage_id", "evidence_id",
                "read_by")
    found = rows(engine, "SELECT * FROM strata.gold.assertion")

    assert len(found) > 13
    missing = [(row["assertion_id"], column) for row in found for column in required if row[column] in (None, "")]
    assert missing == []
    assert {row["evidence_tier"] for row in found} <= {"pad", "isr", "icr", "ieg", "record"}
    assert {row["subject_kind"] for row in found} <= {"project", "package"}
    assert all(row["period_start"] <= row["period_end"] for row in found)
    assert len({row["assertion_id"] for row in found}) == len(found)


# ── The live batch model's answers, held across runs ─────────────────────

class LiveStandIn:
    """A batch model named as the live one is, by its deployment, that answers from the recording, answers every
    request with an error, or says its batch is still running. It keeps what it was asked."""

    def __init__(self, deployment: str, error: str | None = None, pending: str | None = None,
                 answers_on_resume: int | None = None, resume_fails: bool = False):
        self.name = self.deployment = deployment
        self.error, self.pending, self.asked = error, pending, []
        # On a resumed batch: answer only this many of its requests, as when the Batch API lost the rest, or fail
        # to read the batch at all, as when its files expired.
        self.answers_on_resume, self.resume_fails = answers_on_resume, resume_fails
        self.recorded = batch.RecordedBatch(deployment=deployment)

    def answer(self, requests, resume=None):
        self.asked.append(([request.custom_id for request in requests], resume))
        if self.pending:
            raise batch.BatchPending(f"Batch {self.pending} was still in_progress.", batch_id=self.pending)
        if resume and self.resume_fails:
            raise batch.BatchError(f"GET /batches/{resume} answered 404.")
        if self.error:
            return [batch.Answer(request.custom_id, None, self.error) for request in requests]
        if resume and self.answers_on_resume is not None:
            return self.recorded.answer(requests[:self.answers_on_resume])
        return self.recorded.answer(requests)


@pytest.fixture
def copy_db(fixture_db, tmp_path):
    copy = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, copy)
    with DuckDBEngine.open(copy) as engine:
        yield engine


def the_showcase(engine) -> list[tuple[str, str]]:
    return [(row["first_assertion_id"], row["second_assertion_id"]) for row in disagreements(engine, "P130164")
            if row["attribute"] == "pdo_progress"]


def test_a_run_with_no_live_model_keeps_what_the_live_model_read_from_the_answers_bronze_holds(copy_db):
    """On Databricks the nightly job has no Azure OpenAI keys until ticket 43. A run with no live model replays
    the answers bronze holds from the batch role's deployment, so the showcase disagreement the live run wrote
    is still there the morning after."""
    live = LiveStandIn("not-a-real-deployment")
    assertions.run(copy_db, ["P130164"], model=live)
    assert the_showcase(copy_db) == [(ISR_7, PARAGRAPH_78)]

    report = assertions.run(copy_db, ["P130164"], model=batch.HeldAnswers("not-a-real-deployment"))

    assert the_showcase(copy_db) == [(ISR_7, PARAGRAPH_78)]
    assert report.rejected == 1


def test_an_answer_the_batch_gave_as_an_error_is_asked_again_on_the_next_run(copy_db):
    """Global Batch can answer a request with an error, such as status 429. That is no answer: the next run
    asks again, and the showcase disagreement comes back."""
    failing = LiveStandIn("not-a-real-deployment", error="status 429")
    assertions.run(copy_db, ["P130164"], model=failing)
    assert the_showcase(copy_db) == []

    working = LiveStandIn("not-a-real-deployment")
    assertions.run(copy_db, ["P130164"], model=working)

    [(asked, _)] = working.asked
    assert asked == failing.asked[0][0]
    assert the_showcase(copy_db) == [(ISR_7, PARAGRAPH_78)]


def test_a_batch_still_running_keeps_the_rest_of_the_run_and_is_waited_for_on_the_next_run(copy_db):
    """A batch that has not finished when the run stops waiting does not stop the run: the ISR, record and IEG
    assertions are kept and the pending reports are counted. The next run waits for the same batch instead of
    asking, and paying, again."""
    running = LiveStandIn("not-a-real-deployment", pending="batch-not-a-real-id")
    report = assertions.run(copy_db, ["P130164"], model=running)

    [(asked, resume)] = running.asked
    assert resume is None and report.pending == len(asked) > 0
    assert len(isr_assertions(copy_db)) == 13
    assert the_showcase(copy_db) == []

    finished = LiveStandIn("not-a-real-deployment")
    report = assertions.run(copy_db, ["P130164"], model=finished)

    assert finished.asked == [(asked, "batch-not-a-real-id")]
    assert report.pending == 0
    assert the_showcase(copy_db) == [(ISR_7, PARAGRAPH_78)]


def test_a_request_a_resumed_batch_did_not_answer_is_asked_again_on_the_next_run(copy_db):
    """Ticket 20's review, F4. A finished batch can leave a request out of its output. Its newest row then says no
    answer came in that batch, so the next run asks for it in a new batch rather than resuming the finished one for
    ever."""
    assertions.run(copy_db, ["P130164"], model=LiveStandIn("not-a-real-deployment", pending="batch-not-a-real-id"))
    partly = LiveStandIn("not-a-real-deployment", answers_on_resume=1)
    assertions.run(copy_db, ["P130164"], model=partly)
    [(resumed, batch_id)] = partly.asked
    assert batch_id == "batch-not-a-real-id" and len(resumed) > 1

    again = LiveStandIn("not-a-real-deployment")
    assertions.run(copy_db, ["P130164"], model=again)

    assert again.asked == [(resumed[1:], None)]


def test_a_resumed_batch_that_cannot_be_read_is_sent_again_and_the_run_goes_on(copy_db):
    """Ticket 20's review, F4. A batch whose files expired cannot be read; the run sends its requests again in a new
    batch instead of stopping."""
    assertions.run(copy_db, ["P130164"], model=LiveStandIn("not-a-real-deployment", pending="batch-not-a-real-id"))
    expired = LiveStandIn("not-a-real-deployment", resume_fails=True)

    assertions.run(copy_db, ["P130164"], model=expired)

    [(first, resume), (second, fresh)] = expired.asked
    assert (resume, fresh, second) == ("batch-not-a-real-id", None, first)
    assert the_showcase(copy_db) == [(ISR_7, PARAGRAPH_78)]


def test_a_run_over_two_projects_asks_the_model_once(copy_db):
    """Ticket 20's review, F6. The live batch waits up to an hour, so a run builds every project's requests first
    and sends them in one batch."""
    live = LiveStandIn("not-a-real-deployment")

    assertions.run(copy_db, ["P130164", "P156634"], model=live)

    [(asked, _)] = live.asked
    each = {project: [report.custom_id for report in assertions.reports(copy_db, project, assertions.load_ladder())]
            for project in ("P130164", "P156634")}
    assert all(each.values()) and sorted(asked) == sorted(each["P130164"] + each["P156634"])
    assert the_showcase(copy_db) == [(ISR_7, PARAGRAPH_78)]


def test_the_run_s_projects_are_every_project_with_documents_or_records(engine):
    """The fixture's P176758 and P170941 have contracts and no document, and the run reads them too."""
    projects = assertions.default_projects(engine)
    with_contracts = {row[0] for row in engine.run("SELECT DISTINCT project_id FROM strata.gold.contract", {}).rows}

    assert {"P127203", "P130164", "P156634", "P161305", "P176758", "P170941"} <= set(projects)
    assert with_contracts <= set(projects)


class Counting:
    """The fixture's engine, counting the queries a run sends."""

    def __init__(self, engine):
        self.engine, self.queries, self.deletes = engine, 0, []

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def run(self, sql, params=None):
        self.queries += 1
        if sql.lstrip().upper().startswith("DELETE"):
            self.deletes.append((sql.split()[2], dict(params or {})))
        return self.engine.run(sql, params)


def test_the_run_reads_each_family_with_one_query_for_every_project(copy_db, monkeypatch):
    """Ticket 43: the fifth live run read each of 15,933 projects with about seven queries of its own, about
    eleven hours against the job's 150-minute stop. Now the queries a run sends do not grow with the projects
    it reads: a run over every project the fixture holds sends no more queries than a run over one project with
    records alone, beyond the reports whose text the batch model reads."""
    import time

    from strata import config

    monkeypatch.setattr(assertions, "NAMED_MAX", 2)  # the fixture's eight projects take the workspace's path
    projects = assertions.default_projects(copy_db)
    one, every = Counting(copy_db), Counting(copy_db)
    assertions.run(one, ["P176758"], model=batch.RecordedBatch())
    held = copy_db.run("SELECT count(*) FROM strata.gold.assertion", {}).rows[0][0]
    copy_db.run("DELETE FROM strata.gold.assertion WHERE assertion_id = (SELECT min(assertion_id) "
                "FROM strata.gold.assertion WHERE project_id = 'P176758')", {})  # so the run over every project writes
    started = time.perf_counter()
    report = assertions.run(every, projects, model=batch.RecordedBatch())
    took = time.perf_counter() - started

    with_text = {row[0] for row in copy_db.run("SELECT DISTINCT project_id FROM strata.silver.documents", {}).rows}
    assert len(projects) == 8  # every project with a document, a contract, a notice, a plan or an IEG rating
    reports = sum(len(assertions.reports(copy_db, project_id, config.load_ladder())) for project_id in with_text)
    assert every.queries <= one.queries + 3 * len(with_text) + reports  # per report: its passages; per project: its answers
    assert report.assertions > 0 and took < 30
    # Review B2: the rewrite sends one DELETE a table, for only the projects whose rows differ, not three a project.
    assert report.changed == 1
    assert copy_db.run("SELECT count(*) FROM strata.gold.assertion", {}).rows[0][0] == held
    assert every.deletes == [(table, {"projects": "P176758"}) for table in
                             ("strata.gold.assertion", "strata.gold.disagreement", "strata.ops.assertion_rejections")]

