"""The Lessons page at seam 3, through the HTTP routes (ticket 39; the 39 design brief, sections 4 and 9).

The page opens on what affects the reader's work: one sentence counting what came in since their last visit, the
lessons that changed where they used them, what is new, what their passage reports fixed, then the library. The story
is tests/lessons_page_story.py's; the expected counts come from the stored rows, counted here in SQL, and the lesson
words from the reviewers' acts in the story.
"""

import datetime as dt
import fcntl
import json
from pathlib import Path

import pytest

import lessons_page_story as story_of
from strata.config import load_thresholds
from strata.lakehouse.engine import DuckDBEngine

ICR, ICR_REVIEW = "Implementation Completion and Results Report", "Implementation Completion Report Review"


@pytest.fixture(scope="module")
def prebuilt(fixture_db, tmp_path_factory, worker_id):
    """The story, built once per run, and Ana's first visit's answer, which the recorded answers hold. The xdist
    workers that pick a test from this module take turns on a lock in the run's shared temporary folder, as
    tests/conftest.py's fixture_db does, so only the first builds it; every test works on its own copy."""
    from record_lessons_page_api import built_story

    shared = tmp_path_factory.getbasetemp()
    shared = shared.parent if worker_id != "master" else shared  # a lone run's parent folder outlives the run
    folder, done = shared / "lessons-page-story", shared / "lessons-page-story.json"
    with open(shared / "lessons-page-story.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not done.exists():
            folder.mkdir(exist_ok=True)
            (database, state), first = built_story(fixture_db, folder)
            done.write_text(json.dumps({"database": str(database), "state": str(state), "first": first}))
    found = json.loads(done.read_text())
    return (Path(found["database"]), Path(found["state"])), found["first"]


@pytest.fixture(scope="module")
def built(prebuilt):
    return prebuilt[0]


@pytest.fixture
def story(built, tmp_path):
    return story_of.story_at(built, tmp_path)


def rows(path, sql, **params):
    with DuckDBEngine.open(path, read_only=True) as engine:
        result = engine.run(sql, params)
        return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def text(segments) -> str:
    return "".join(part.get("text") or part.get("word") or part.get("date") or str(part.get("number", ""))
                   for part in segments)


# ── The opening sentence and the last visit ──────────────────────────────

def test_the_first_visit_says_so_and_a_reload_within_the_visit_keeps_it_the_first(built, tmp_path):
    story = story_of.story_at(built, tmp_path, dt.datetime(2026, 10, 30, 9, 0, tzinfo=dt.UTC))
    ben = story_of.ppsd_story.BEN  # Ben has never opened Lessons

    first = story.page(ben).json()
    again = story.at_time(dt.datetime(2026, 10, 30, 9, 20, tzinfo=dt.UTC)).page(ben).json()

    assert first["visit"]["first_visit"] and again["visit"]["first_visit"]
    assert first["digest"]["kind"] == "first"
    assert text(first["digest"]["segments"]).startswith("This is your first visit to Lessons. The library holds two "
                                                        "current lessons")


def test_the_headline_counts_equal_the_rows_stored_since_the_reader_s_last_visit(story):
    page = story.page().json()

    [last] = rows(story.state_db, "SELECT max(visit_started_at) AS at FROM strata.ops.lesson_visits "
                                  "WHERE viewer_id = :viewer AND visit_started_at < :now",
                  viewer="4021@1984", now=story_of.NEXT_VISIT)
    since, until = last["at"], story_of.NEXT_VISIT
    # Each version decided in the window, with the state its lesson is in at its latest version: a lesson added and
    # retired in one window is not new.
    decided = rows(story.database, """
        SELECT v.lesson_id, v.version, v.change_kind,
               (SELECT l.state FROM strata.ops.lesson_versions AS l WHERE l.lesson_id = v.lesson_id
                ORDER BY l.version DESC LIMIT 1) AS latest_state
        FROM strata.ops.lesson_versions AS v
        JOIN strata.ops.lesson_review_acts AS a ON a.item_id = v.item_id AND a.act = 'decide'
        WHERE a.acted_at >= :since AND a.acted_at < :until""", since=since, until=until)
    fetched = rows(story.database, """
        SELECT d.document_type, count(*) AS n
        FROM strata.silver.documents AS d
        JOIN (SELECT document_id, min(fetched_at) AS first FROM strata.bronze.document_texts GROUP BY document_id) AS f
          ON f.document_id = d.document_id
        WHERE f.first >= :since AND f.first < :until
        GROUP BY d.document_type""", since=since, until=until)
    waiting = rows(story.database, """
        SELECT count(*) AS n FROM strata.ops.lesson_review_items AS i
        WHERE i.kind = 'new' AND NOT EXISTS (
          SELECT 1 FROM strata.ops.lesson_review_acts AS a WHERE a.item_id = i.item_id AND a.act = 'decide')""")
    by_type = {row["document_type"]: row["n"] for row in fetched}

    counts = page["digest"]["counts"]
    assert page["visit"]["last_visit_on"] == "2026-10-22"
    assert counts["reports"] == {"icr": by_type.get(ICR, 0), "review": by_type.get(ICR_REVIEW, 0), "ppar": 0}
    assert counts["new"] == len({row["lesson_id"] for row in decided
                                 if row["version"] == 1 and row["latest_state"] == "current"})
    assert counts["changed"] == len({row["lesson_id"] for row in decided if row["version"] > 1
                                     and row["change_kind"] != "retired"})
    assert counts["retired"] == len({row["lesson_id"] for row in decided if row["change_kind"] == "retired"})
    assert counts["proposed"] == waiting[0]["n"]
    # On this story: two ICRs and two ICR Reviews came in, both lessons are new, and both changed since.
    assert (counts["reports"]["icr"], counts["reports"]["review"], counts["new"], counts["changed"]) == (2, 2, 2, 2)
    assert text(page["digest"]["segments"]) == (
        "Since your last visit on 2026-10-22, two completion reports and two ICR Reviews came in. "
        "Two lessons are new and two changed.")


# ── Changed where you used it ────────────────────────────────────────────

def test_a_lesson_whose_wording_changed_after_the_version_a_draft_cites_shows_was_and_now_where_it_is_used(story):
    page = story.page().json()

    [notice] = page["notices"]
    assert (notice["lesson_id"], notice["tier"], notice["a"], notice["b"]) == (story_of.REBIDDING_LESSON, "narrowed", 1, 2)
    assert notice["statement_a"] == "Base works estimates on market rates to avoid rebidding"
    assert [(change["field"], change["was"], change["now"]) for change in notice["changes"]] == [
        ("statement", "Base works estimates on market rates to avoid rebidding", story_of.NARROWED),
        ("categories", "", "Works"), ("methods", "", "Request for Bids (RFB)")]
    assert notice["decided_on"] == "2026-10-29"
    assert notice["reason"] == "Current market rates is what the 2025 rules ask for."
    # The changed words, as character ranges the page marks in each line.
    was, now = notice["changes"][0]["was"], notice["changes"][0]["now"]
    assert [now[start:end] for start, end in notice["changes"][0]["now_ranges"]] == ["cost", "current"]
    assert [was[start:end] for start, end in notice["changes"][0]["was_ranges"]] == []
    # Used in both of Ana's drafts, each citing version 1, and only Ana may act.
    assert [(use["draft_id"], use["draft_state"], use["row_key"], use["cites"], use["can_act"], use["holds_export"])
            for use in notice["uses"]] == [("draft-0001", "draft", "cost_estimates", 1, True, False),
                                           ("draft-0002", "checked", "cost_estimates", 1, True, False)]
    assert notice["uses"][0]["row_label"] == {"n": 1, "risk_label": "Cost estimates below market rates"}
    assert notice["actions"] == ["versions", "update", "keep"]


def test_a_lesson_that_only_gained_a_quote_shows_only_in_the_digest_s_quiet_line(story):
    page = story.page().json()

    assert story_of.IEG_LESSON not in [notice["lesson_id"] for notice in page["notices"]]
    strengthened = page["digest"]["strengthened"]
    assert [(item["lesson_id"], item["a"], item["b"]) for item in strengthened["items"]] == [(story_of.IEG_LESSON, 1, 2)]
    assert [use["draft_id"] for use in strengthened["items"][0]["uses"]] == ["draft-0001", "draft-0002"]
    assert text(strengthened["segments"]) == ("One lesson you cite gained evidence since your last visit. Your drafts "
                                              "don't need to change.")
    # The draft page shows nothing on the permits row, and the changed lesson's notice on the cost estimates row.
    draft = story.get("/api/drafts/draft-0001").json()
    assert [(notice["row_key"], notice["tier"]) for notice in draft["lesson_notices"]] == [("cost_estimates", "narrowed")]
    assert [hold["key"] for hold in draft["holds"]] == ["notChecked", "owners"]  # a changed lesson holds nothing


# ── A lesson retired as wrong holds the export ───────────────────────────

WRONG = "IEG's own review later said the permits were not the cause."


def retire_ieg_lesson_as_wrong(story):
    story_of.scenario.recheck(story.database, story_of.IEG_LESSON, dt.date(2026, 10, 29), "retire_wrong", reason=WRONG)


def choose(story, draft_id, row_key, **body):
    return story.call("POST", f"/api/drafts/{draft_id}/rows/{row_key}/lesson", json=body)


def set_owners(story, draft_id):
    for row in ("cost_estimates", "permits_before_award"):
        story.set_field(draft_id, row, "risk_owner", "Implementing agency, procurement")


def test_a_lesson_retired_as_wrong_holds_the_draft_s_export_with_the_lead_s_reason_until_the_row_is_removed(story):
    retire_ieg_lesson_as_wrong(story)
    set_owners(story, "draft-0002")

    page = story.page().json()
    retired = page["notices"][0]  # first, since it holds an export
    assert (retired["lesson_id"], retired["tier"], retired["a"], retired["b"]) == (story_of.IEG_LESSON, "retired_wrong", 1, 3)
    assert (retired["reason"], retired["retired_on"], retired["holds_export"]) == (WRONG, "2026-10-29", True)
    assert retired["actions"] == ["versions", "remove", "keep"]
    assert [use["draft_id"] for use in retired["uses"]] == ["draft-0001", "draft-0002"]
    draft = story.get("/api/drafts/draft-0002").json()
    assert [(hold["key"], hold["first_anchor"]) for hold in draft["holds"]] == [
        ("lessonRetiredWrong", "notice-permits_before_award")]
    held = story.act("draft-0002", "export", "checked")
    assert (held.status_code, held.json()["code"], held.json()["holds"]) == (409, "held", ["lessonRetiredWrong"])

    removed = choose(story, "draft-0002", "permits_before_award", lesson_id=story_of.IEG_LESSON, action="remove",
                     expected_cited_version=1, expected_current_version=3)

    assert removed.status_code == 200
    after = removed.json()["draft"]
    assert after["holds"] == []
    assert [notice["row_key"] for notice in after["lesson_notices"]] == ["cost_estimates"]  # the changed lesson's
    assert after["ppsd"]["counts"] == {"total": 1, "owners_set": 1, "rated": 0}  # a removed row leaves the counts
    assert [row["row_key"] for row in after["ppsd"]["rows"]] == ["cost_estimates"]
    assert [entry["row_key"] for entry in after["lesson_removed"]] == ["permits_before_award"]
    # The check line and the steps count the sentences still on screen: each was proven by checks 1 to 3 or judged.
    on_screen = sum(len(note["sentences"]) for note in after["notes"])
    assert after["checks"]["sentences"] == {"written": 2, "kept": 2, "removed": 0} and on_screen == 2
    assert after["checks"]["shown"]["judged"] + after["checks"]["shown"]["proven"] == on_screen
    assert story.act("draft-0002", "export", "checked").json()["state"] == "exported"


def test_a_lesson_added_and_retired_since_the_last_visit_is_counted_retired_and_not_new(story):
    """The digest's "new" count and the New cards read one rule: a lesson still current at the end of the window."""
    retire_ieg_lesson_as_wrong(story)

    page = story.page().json()

    assert page["digest"]["counts"]["new"] == len(page["new_lessons"]["cards"]) == 1
    assert page["digest"]["counts"]["retired"] == 1
    assert [card["lesson_id"] for card in page["new_lessons"]["cards"]] == [story_of.REBIDDING_LESSON]


def test_a_removed_row_can_be_restored_and_its_notice_and_hold_come_back(story):
    retire_ieg_lesson_as_wrong(story)
    choose(story, "draft-0001", "permits_before_award", lesson_id=story_of.IEG_LESSON, action="remove",
           expected_cited_version=1, expected_current_version=3)

    restored = choose(story, "draft-0001", "permits_before_award", lesson_id=story_of.IEG_LESSON, action="restore",
                      expected_cited_version=1, expected_current_version=3).json()["draft"]

    assert [(notice["row_key"], notice["tier"]) for notice in restored["lesson_notices"]] == [
        ("cost_estimates", "narrowed"), ("permits_before_award", "retired_wrong")]
    assert "lessonRetiredWrong" in [hold["key"] for hold in restored["holds"]]
    assert restored["ppsd"]["counts"]["total"] == 2
    rows = query_choices(story)
    assert [(row["action"], row["row_key"]) for row in rows] == [("remove", "permits_before_award"),
                                                                 ("restore", "permits_before_award")]


def test_a_project_paper_summary_that_cites_a_lesson_retired_as_wrong_is_held_until_its_part_is_removed(story):
    """The summary's PPSD part cites the rows' lesson at its version, so a retirement as wrong holds its export too."""
    _, paper = story.summarize()
    story_of.scenario.recheck(story.database, story_of.REBIDDING_LESSON, dt.date(2026, 10, 30), "retire_wrong",
                              reason=WRONG)
    story.act(paper, "check", "draft")

    draft = story.get(f"/api/drafts/{paper}").json()
    assert [(notice["row_key"], notice["tier"], notice["actions"]) for notice in draft["lesson_notices"]] == [
        ("ppsd", "retired_wrong", ["remove", "keep"])]
    assert [(hold["key"], hold["first_anchor"]) for hold in draft["holds"]] == [("lessonRetiredWrong", "notice-ppsd")]
    held = story.act(paper, "export", "checked")
    assert (held.status_code, held.json()["code"], held.json()["holds"]) == (409, "held", ["lessonRetiredWrong"])

    removed = choose(story, paper, "ppsd", lesson_id=story_of.REBIDDING_LESSON, action="remove",
                     expected_cited_version=1, expected_current_version=3)

    assert removed.status_code == 200 and removed.json()["draft"]["holds"] == []
    assert [note["key"] for note in removed.json()["draft"]["notes"]] == ["plan", "record"]
    assert story.act(paper, "export", "checked").json()["state"] == "exported"


def query_choices(story):
    return rows(story.state_db, "SELECT action, row_key, reason, draft_state, actor_id FROM "
                                "strata.ops.draft_lesson_choices ORDER BY draft_id, choice_no")


# ── Keep version 1, with a reason ────────────────────────────────────────

def test_keeping_the_cited_version_needs_a_reason_and_stores_it_with_the_draft(story):
    # The keep form counts against the limit the route enforces, which each notice carries.
    limit = load_thresholds().value("lesson_review.reason_max_chars")
    [on_draft] = story.get("/api/drafts/draft-0001").json()["lesson_notices"][:1]
    assert on_draft["reason_max_chars"] == story.page().json()["notices"][0]["reason_max_chars"] == limit
    too_long = choose(story, "draft-0001", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="keep",
                      expected_cited_version=1, expected_current_version=2, reason="x" * (limit + 1))
    assert (too_long.status_code, too_long.json()["code"]) == (422, "reason_too_long")

    empty = choose(story, "draft-0001", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="keep",
                   expected_cited_version=1, expected_current_version=2, reason="  ")
    assert (empty.status_code, empty.json()["code"]) == (422, "no_reason")

    kept = choose(story, "draft-0001", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="keep",
                  expected_cited_version=1, expected_current_version=2,
                  reason="The borrower's estimates already use current rates.")

    assert kept.status_code == 200
    draft = kept.json()["draft"]
    assert draft["lesson_notices"] == [] and draft["state"] == "draft"
    assert [(entry["row_key"], entry["cited_version"], entry["reason"]) for entry in draft["lesson_kept"]] == [
        ("cost_estimates", 1, "The borrower's estimates already use current rates.")]
    assert query_choices(story) == [{"action": "keep", "row_key": "cost_estimates", "draft_state": "draft",
                                     "reason": "The borrower's estimates already use current rates.",
                                     "actor_id": "4021@1984"}]
    # The Lessons tab's notice now lists only the draft that still cites version 1 without a choice.
    [notice] = story.page().json()["notices"]
    assert [use["draft_id"] for use in notice["uses"]] == ["draft-0002"]


def test_the_kept_version_and_its_reason_go_into_the_evidence_pack_at_export(story):
    choose(story, "draft-0002", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="keep",
           expected_cited_version=1, expected_current_version=2, reason="The borrower's estimates already use current rates.")
    set_owners(story, "draft-0002")

    exported = story.act("draft-0002", "export", "checked")

    assert exported.json()["state"] == "exported"
    [snapshot] = rows(story.state_db, "SELECT snapshot FROM strata.ops.draft_exports WHERE draft_id = 'draft-0002'")

    assert json.loads(snapshot["snapshot"])["lessons"] == [{
        "row": "Cost estimates below market rates", "cited": 1, "current": 2,
        "choice": "Kept version 1: The borrower's estimates already use current rates."}]


def test_a_row_kept_on_a_retired_lesson_goes_into_the_evidence_pack_as_a_kept_row(story):
    """A retired lesson has no version to keep, so the pack says the author kept the row (the 39 brief, section 11)."""
    retire_ieg_lesson_as_wrong(story)
    set_owners(story, "draft-0002")
    choose(story, "draft-0002", "permits_before_award", lesson_id=story_of.IEG_LESSON, action="keep",
           expected_cited_version=1, expected_current_version=3, reason="The permits risk still applies here.")
    choose(story, "draft-0002", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="keep",
           expected_cited_version=1, expected_current_version=2, reason="The estimates already use current rates.")

    assert story.act("draft-0002", "export", "checked").json()["state"] == "exported"

    [snapshot] = rows(story.state_db, "SELECT snapshot FROM strata.ops.draft_exports WHERE draft_id = 'draft-0002'")
    assert sorted((row["cited"], row["current"], row["choice"]) for row in json.loads(snapshot["snapshot"])["lessons"]) == [
        (1, 2, "Kept version 1: The estimates already use current rates."),
        (1, 3, "Kept the row: The permits risk still applies here.")]


def test_a_kept_row_shows_a_notice_again_only_for_a_later_change(story):
    choose(story, "draft-0001", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="keep",
           expected_cited_version=1, expected_current_version=2, reason="It still holds for this package.")
    story_of.scenario.recheck(story.database, story_of.REBIDDING_LESSON, dt.date(2026, 10, 30), "retire_outdated",
                              reason="The 2025 rules replaced it.")

    draft = story.get("/api/drafts/draft-0001").json()

    assert [(notice["row_key"], notice["tier"], notice["a"], notice["b"]) for notice in draft["lesson_notices"]] == [
        ("cost_estimates", "retired_outdated", 1, 3)]


# ── Update the row ───────────────────────────────────────────────────────

REWRITTEN = "Base the works cost estimates on current market rates before the contracts go to bid."


def mitigation(draft: dict) -> list[dict]:
    [note] = [note for note in draft["notes"] if note["key"] == "cost_estimates/mitigation"]
    return note["sentences"]


def test_updating_the_row_rewrites_it_from_the_new_version_and_a_checked_draft_goes_back_to_draft(story):
    before = story.get("/api/drafts/draft-0002").json()
    assert before["state"] == "checked"

    updated = story.update("draft-0002")

    assert updated.status_code == 200
    answer = updated.json()
    draft = answer["draft"]
    assert (answer["outcome"], answer["back_to_draft"], draft["state"]) == ("updated", True, "draft")
    [sentence] = mitigation(draft)
    assert sentence["text"] == REWRITTEN
    assert sentence["evidence_ids"][0] == f"strata.ops.lesson_versions:{story_of.REBIDDING_LESSON}/v2"
    [row] = [row for row in draft["ppsd"]["rows"] if row["row_key"] == "cost_estimates"]
    assert (row["lesson"]["version"], row["lesson"]["evidence_id"]) == (
        2, f"strata.ops.lesson_versions:{story_of.REBIDDING_LESSON}/v2")
    assert [notice["row_key"] for notice in draft["lesson_notices"]] == []
    # The Word file's footnote for the new sentence names the same passages, and the earlier text stays on record.
    assert [entry["row_key"] for entry in draft["lesson_updated"]] == ["cost_estimates"]
    assert mitigation({"notes": draft["lesson_updated"][0]["earlier"]})[0]["text"] == (
        "Base the works cost estimates on market rates before the contracts go to bid.")
    assert [(row["action"], row["draft_state"]) for row in query_choices(story)] == [("update", "checked")]
    states = rows(story.state_db, "SELECT state FROM strata.ops.draft_states WHERE draft_id = 'draft-0002' "
                                  "ORDER BY step")
    assert [row["state"] for row in states] == ["draft", "checked", "draft"]


PLANTED = "Estimates in the earlier bids were 37 percent below market rates."


def test_a_sentence_the_verifier_removes_from_the_rewrite_is_shown_and_counted_until_you_go_back(story):
    """CLAUDE.md rule 2: a sentence that can't be checked is removed and shown. The rewrite's second sentence states a
    number no tool returned, so the row keeps only the first, the removed box lists the second with its reason, and the
    counts are the draft's as it now stands: the row's one sentence gave way to the rewrite's two, one of them kept."""
    before = story.get("/api/drafts/draft-0002").json()
    assert (before["removed"], before["checks"]["sentences"]) == ([], {"written": 4, "kept": 4, "removed": 0})

    answer = story.update("draft-0002", case="ppsd-row-update-removed-number").json()

    draft = answer["draft"]
    assert answer["outcome"] == "updated"
    assert [sentence["text"] for sentence in mitigation(draft)] == [REWRITTEN]
    assert [(item["sentence"], item["reason"], item["key"]) for item in draft["removed"]] == [
        (PLANTED, "number_not_in_records", "cost_estimates/mitigation")]
    assert draft["checks"]["sentences"] == {"written": 5, "kept": 4, "removed": 1}
    # One judged sentence of advice gave way to another, and the removed one's number is not on screen.
    assert draft["checks"]["shown"] == before["checks"]["shown"]

    back = choose(story, "draft-0002", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="revert",
                  expected_cited_version=2, expected_current_version=2).json()["draft"]

    assert (back["removed"], back["checks"]) == ([], before["checks"])


def test_the_evidence_pack_lists_the_sentence_the_verifier_removed_from_the_rewrite(story):
    """The exported evidence pack says the same as the page: under "Sentences I removed", the rewrite's sentence with
    the number no tool returned, and its reason."""
    import io

    from pypdf import PdfReader

    story.update("draft-0002", case="ppsd-row-update-removed-number")
    set_owners(story, "draft-0002")
    story.act("draft-0002", "check", "draft")
    assert story.act("draft-0002", "export", "checked").json()["state"] == "exported"

    _, pack = story.download("draft-0002", ".pdf")
    # The PDF's text layer loses the space where a line wraps, so the words are compared without spaces.
    text = "".join("".join(page.extract_text().split()) for page in PdfReader(io.BytesIO(pack)).pages)
    removed = text.split("SentencesIremoved", 1)[1]
    assert "".join(f'"{PLANTED}" No record supports this number.'.split()) in removed
    assert "Iremovednosentences." not in removed


def test_going_back_to_version_1_restores_the_earlier_text_with_no_model_call(story):
    story.update("draft-0001")

    back = choose(story, "draft-0001", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="revert",
                  expected_cited_version=2, expected_current_version=2).json()["draft"]

    assert mitigation(back)[0]["text"] == "Base the works cost estimates on market rates before the contracts go to bid."
    assert [(notice["row_key"], notice["a"], notice["b"]) for notice in back["lesson_notices"]] == [("cost_estimates", 1, 2)]


def test_when_nothing_passes_the_checks_the_row_is_left_as_it_was(story):
    answer = story.update("draft-0002", case="ppsd-row-update-nothing-passes").json()

    assert answer["outcome"] == "nothing_passed"
    # The notice shows what the verifier removed: the sentence cited version 1, which get_lessons did not return.
    assert [(item["sentence"], item["reason"]) for item in answer["removed"]] == [
        ("Base the works cost estimates on market rates before the contracts go to bid.", "id_not_returned")]
    assert answer["draft"]["state"] == "checked"
    assert mitigation(answer["draft"])[0]["text"] == (
        "Base the works cost estimates on market rates before the contracts go to bid.")
    assert query_choices(story) == []


def test_a_choice_made_in_another_tab_while_the_row_is_rewritten_makes_the_update_stale(built, tmp_path):
    """While "Update the row" waits for the writer, Ana keeps version 1 in another tab. The update then saves nothing
    and says the draft changed, so the page reloads it."""
    import shutil

    from strata.agent.scripted import ScriptedAgent
    from strata.drafts.store import DraftStore

    class TwoTabs(story_of.LessonsStory):
        def app_options(self, state):
            story = self

            class KeptMeanwhile(ScriptedAgent):
                def respond(self, items, previous_response_id):
                    DraftStore(state).choose("draft-0002", "cost_estimates", story_of.REBIDDING_LESSON, "keep", 1, 2,
                                             "Kept in the other tab.", None, "checked", "4021@1984", "Ana Example",
                                             story.at)
                    return super().respond(items, previous_response_id)

            return {**super().app_options(state), "writers": lambda kind: KeptMeanwhile(story.cases[story.case])}

    database, state = built
    shutil.copy(database, tmp_path / "fixture.duckdb")
    shutil.copy(state, tmp_path / "state.duckdb")
    story = TwoTabs(tmp_path / "fixture.duckdb", tmp_path).at_time(story_of.NEXT_VISIT)

    updated = story.update("draft-0002")

    assert (updated.status_code, updated.json()["code"]) == (409, "stale")
    assert [(row["action"], row["reason"]) for row in query_choices(story)] == [("keep", "Kept in the other tab.")]
    assert story.get("/api/drafts/draft-0002").json()["state"] == "checked"


# ── Who may choose, and when ─────────────────────────────────────────────

def test_a_discarded_draft_shows_no_version_notice(story):
    """Nobody can choose on a discarded draft, so its page shows no notice that asks for a choice."""
    assert story.get("/api/drafts/draft-0001").json()["lesson_notices"]

    story.act("draft-0001", "discard", "draft")

    assert story.get("/api/drafts/draft-0001").json()["lesson_notices"] == []


def test_only_the_author_chooses_in_the_staff_view_and_a_stale_choice_is_refused(story):
    body = {"lesson_id": story_of.REBIDDING_LESSON, "action": "keep", "expected_cited_version": 1,
            "expected_current_version": 2, "reason": "It still holds."}
    teammate = story.call("POST", "/api/drafts/draft-0001/rows/cost_estimates/lesson", story_of.ppsd_story.BEN, json=body)
    preview = choose(story, "draft-0001", "cost_estimates", **{**body, "view": "piu"})
    stale = choose(story, "draft-0001", "cost_estimates", **{**body, "expected_current_version": 1})

    assert (teammate.status_code, teammate.json()["code"]) == (403, "not_author")
    assert (preview.status_code, preview.json()["code"]) == (403, "preview")
    assert (stale.status_code, stale.json()["code"]) == (409, "stale")
    assert stale.json()["draft"]["lesson_notices"][0]["b"] == 2
    assert query_choices(story) == []


# ── New, and the evidence badges ─────────────────────────────────────────

def test_new_lessons_show_their_evidence_badge_and_who_decided_them_by_role(story):
    page = story.page().json()

    cards = {card["lesson_id"]: card for card in page["new_lessons"]["cards"]}
    assert set(cards) == {story_of.REBIDDING_LESSON, story_of.IEG_LESSON}
    # ICR paragraph 54's lesson rests on the ICR, and IEG's ICR Review restated it; section 12 is IEG's own words.
    assert cards[story_of.REBIDDING_LESSON]["ieg_status"] == "restated"
    assert cards[story_of.IEG_LESSON]["ieg_status"] == "ieg_lesson"
    assert [tag["label"] for tag in cards[story_of.REBIDDING_LESSON]["methods"]] == ["Request for Bids (RFB)"]
    assert page["new_lessons"]["more"] == 0
    assert "decided_by" not in cards[story_of.REBIDDING_LESSON]  # roles, never names


def test_a_lesson_resting_on_an_icr_with_no_icr_review_yet_awaits_ieg_review():
    """Brief 29's rule (section 4.4), which "New" and the library show: no ICR Review of the project in the store."""
    from strata.knowledge.lessons.review import ieg_status

    icr_only = [{"role": "source", "restated_by_ieg": False}]
    assert ieg_status(icr_only, None) == {"ieg_status": "awaiting", "review_date": None}
    assert ieg_status(icr_only, "2020-03-27")["ieg_status"] == "not_restated"


# ── The library ──────────────────────────────────────────────────────────

def library(story, **filters):
    return story.get("/api/lessons/library", **filters).json()


def test_the_library_filters_by_stage_method_sector_and_status_with_a_count_line(story):
    everything = library(story)
    by_stage = library(story, stage="contract_award")
    by_method = library(story, method="Request for Quotations")
    rfb = library(story, method="Request for Bids")
    by_sector = library(story, sector="Transportation")
    retired = library(story, status="retired")

    assert (everything["total"], everything["of"]) == (2, 2)
    assert text(everything["count"]) == "Showing all 2 current lessons, newest first."
    assert [card["lesson_id"] for card in by_stage["lessons"]] == [story_of.IEG_LESSON]
    assert text(by_stage["count"]) == "Showing 1 of 2 current lessons, newest first."
    # The rebidding lesson names Request for Bids; IEG's lesson names no method, so every method keeps it.
    assert [card["lesson_id"] for card in by_method["lessons"]] == [story_of.IEG_LESSON]
    assert (rfb["total"], by_sector["total"]) == (2, 2)
    assert (retired["total"], retired["of"], retired["lessons"]) == (0, 0, [])
    assert [option["key"] for option in everything["options"]["status"]] == ["current", "rechecking", "retired"]


def test_a_retired_lesson_shows_only_under_retired_with_the_lead_s_reason(story):
    retire_ieg_lesson_as_wrong(story)

    current, retired = library(story), library(story, status="retired")

    assert [card["lesson_id"] for card in current["lessons"]] == [story_of.REBIDDING_LESSON]
    [card] = retired["lessons"]
    assert (card["lesson_id"], card["retired"]) == (story_of.IEG_LESSON,
                                                    {"as": "retired_wrong", "on": "2026-10-29", "reason": WRONG})
    shown = library(story, show=story_of.IEG_LESSON, stage="procurement_planning")
    assert (shown["status"], shown["shown"], shown["filters"]["stage"]) == ("retired", story_of.IEG_LESSON, None)


def test_no_proposed_lesson_appears_in_the_library_for_anyone(story):
    with DuckDBEngine.open(story.database, read_only=True) as engine:
        proposals = [row[0] for row in engine.run("SELECT statement FROM strata.silver.lesson_proposals", {}).rows]
        decided = {row[0] for row in engine.run("SELECT statement FROM strata.ops.lesson_versions", {}).rows}
    reviewer = story_of.ppsd_story.viewer(31, "Asha")
    listed = {card["statement"] for who in (story_of.ANA, reviewer)
              for status in ("current", "rechecking", "retired")
              for card in story.get("/api/lessons/library", who, status=status).json()["lessons"]}

    assert listed <= decided
    assert not listed & (set(proposals) - decided)
    assert "Get land and forest permits before awarding works contracts" not in listed


def test_a_filter_the_server_does_not_know_is_left_out_and_said(story):
    found = library(story, stage="not-a-stage")

    assert found["unknown_filter"] and found["filters"]["stage"] is None and found["total"] == 2


# ── Your reports ─────────────────────────────────────────────────────────

def test_the_feedback_line_reads_the_retrieval_loop_s_per_person_counts(story):
    with DuckDBEngine.open(story.state_db) as engine:
        engine.insert_rows("strata.ops.retrieval_feedback_viewers",
                           ("viewer_id", "marked", "fixed", "waiting", "kept", "recited", "computed_at", "public_from"),
                           [("4021@1984", 2, 1, 1, 0, 14, dt.datetime(2026, 10, 26, 6, tzinfo=dt.UTC),
                             dt.date(2026, 10, 26))])

    feedback = story.page().json()["feedback"]
    never = story.page(story_of.ppsd_story.BEN).json()["feedback"]

    assert text(feedback["segments"]) == ("You marked two passages as wrong; one is fixed, and 14 answers now cite the "
                                          "right paragraph.")
    assert feedback["counts"] == {"marked": 2, "fixed": 1, "waiting": 1, "kept": 0, "recited": 14}
    assert never == {"never": True, "segments": None, "counts": None}


# ── Two versions of a lesson (the evidence drawer) ───────────────────────

def test_see_both_versions_returns_each_version_with_its_evidence_and_the_change_between(story):
    found = story.get(f"/api/lessons/{story_of.REBIDDING_LESSON}/versions", **{"from": 1, "to": 2}).json()

    assert found["evidence_id"] == f"versions:{story_of.REBIDDING_LESSON}:1:2"
    assert [(block["version"], block["statement"], block["decided_on"]) for block in found["versions"]] == [
        (1, "Base works estimates on market rates to avoid rebidding", "2026-10-27"),
        (2, story_of.NARROWED, "2026-10-29")]
    assert [row["evidence_id"] for row in found["versions"][0]["evidence"]] == [
        "strata.gold.passage:31525018/v1/54", "strata.gold.passage:34056616/v2/10.b"]
    assert found["versions"][1]["reason"] == "Current market rates is what the 2025 rules ask for."
    assert [change["field"] for change in found["changes"]] == ["statement", "categories", "methods"]
    missing = story.get(f"/api/lessons/{story_of.REBIDDING_LESSON}/versions", **{"from": 1, "to": 9})
    assert (missing.status_code, missing.json()["code"]) == (404, "unknown_version")
    # The evidence drawer opens the same view by its evidence id.
    drawer = story.get("/api/evidence", id=f"versions:{story_of.REBIDDING_LESSON}:1:2").json()
    assert (drawer["kind"], drawer["row"]["versions"][1]["statement"]) == ("versions", story_of.NARROWED)


# ── The screens' recorded answers ────────────────────────────────────────

def test_the_screens_recorded_answers_are_what_the_routes_answer(fixture_db, tmp_path, prebuilt):
    """tests/record_lessons_page_api.py writes the answers the Lessons page's screen tests and the gallery serve, from
    tests/lessons_page_story.py; the routes must still answer with them word for word."""
    from pathlib import Path

    from record_lessons_page_api import answers

    recorded = Path(__file__).resolve().parent / "fixtures" / "api"
    for name, written in answers(tmp_path, fixture_db, prebuilt).items():
        assert written == (recorded / name).read_text(), (
            f"{name} is out of date: uv run --frozen python tests/record_lessons_page_api.py")


# ── Previews and as-of views ─────────────────────────────────────────────

def test_a_preview_leaves_out_the_reader_and_the_proposed_count_and_records_no_visit(story):
    before = rows(story.state_db, "SELECT count(*) AS n FROM strata.ops.lesson_visits")[0]["n"]

    page = story.page(view="piu").json()

    assert page["notices"] == [] and page["feedback"] is None and page["digest"]["strengthened"] is None
    assert page["digest"]["counts"]["proposed"] is None
    assert rows(story.state_db, "SELECT count(*) AS n FROM strata.ops.lesson_visits")[0]["n"] == before


def test_as_of_a_date_the_library_shows_each_lesson_at_the_version_current_then(story):
    page = story.page(asof="2026-10-28").json()

    assert page["digest"] is None and page["notices"] == []
    statements = [card["statement"] for card in page["library"]["lessons"]]
    assert "Base works estimates on market rates to avoid rebidding" in statements
    assert story_of.NARROWED not in statements
