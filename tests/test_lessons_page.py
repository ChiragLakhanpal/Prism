"""The Lessons page at seam 3, through the HTTP routes (ticket 39; the 39 design brief, sections 4 and 9).

The page opens on what affects the reader's work: one sentence counting what came in since their last visit, the
lessons that changed where they used them, what is new, what their passage reports fixed, then the library. The story
is tests/lessons_page_story.py's; the expected counts come from the stored rows, counted here in SQL, and the lesson
words from the reviewers' acts in the story.
"""

import datetime as dt

import pytest

import lessons_page_story as story_of
from strata.lakehouse.engine import DuckDBEngine

ICR, ICR_REVIEW = "Implementation Completion and Results Report", "Implementation Completion Report Review"


@pytest.fixture(scope="module")
def built(fixture_db, tmp_path_factory):
    return story_of.build(fixture_db, tmp_path_factory.mktemp("lessons-page"))


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
    decided = rows(story.database, """
        SELECT v.lesson_id, v.version, v.change_kind
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
    assert counts["new"] == len({row["lesson_id"] for row in decided if row["version"] == 1})
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
        ("statement", "Base works estimates on market rates to avoid rebidding", story_of.NARROWED)]
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
    assert story.act("draft-0002", "export", "checked").json()["state"] == "exported"


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


def query_choices(story):
    return rows(story.state_db, "SELECT action, row_key, reason, draft_state, actor_id FROM "
                                "strata.ops.draft_lesson_choices ORDER BY draft_id, choice_no")


# ── Keep version 1, with a reason ────────────────────────────────────────

def test_keeping_the_cited_version_needs_a_reason_and_stores_it_with_the_draft(story):
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


def test_going_back_to_version_1_restores_the_earlier_text_with_no_model_call(story):
    story.update("draft-0001")

    back = choose(story, "draft-0001", "cost_estimates", lesson_id=story_of.REBIDDING_LESSON, action="revert",
                  expected_cited_version=2, expected_current_version=2).json()["draft"]

    assert mitigation(back)[0]["text"] == "Base the works cost estimates on market rates before the contracts go to bid."
    assert [(notice["row_key"], notice["a"], notice["b"]) for notice in back["lesson_notices"]] == [("cost_estimates", 1, 2)]


def test_when_nothing_passes_the_checks_the_row_is_left_as_it_was(story):
    answer = story.update("draft-0002", case="ppsd-row-update-nothing-passes").json()

    assert answer["outcome"] == "nothing_passed"
    assert answer["draft"]["state"] == "checked"
    assert mitigation(answer["draft"])[0]["text"] == (
        "Base the works cost estimates on market rates before the contracts go to bid.")
    assert query_choices(story) == []


# ── Who may choose, and when ─────────────────────────────────────────────

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
