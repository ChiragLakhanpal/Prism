"""Writes the Lessons page's recorded answers in tests/fixtures/api from the server itself (ticket 39).

The screen tests and the design gallery serve these files, and tests/test_lessons_page.py checks that the server
still answers with them, so the screens and the server cannot drift apart. Build the fixture database first, then
run:

    uv run --frozen python tests/record_lessons_page_api.py

The story is tests/lessons_page_story.py's, read on Friday, October 30, 2026 at 09:00: Ana's two drafts cite the
rebidding lesson at version 1, whose wording a re-check changed on October 29, and IEG's lesson at version 1, which
only gained a quote. The weekly retrieval run stored her counts: two passages marked as wrong, one fixed, one still
waiting, and 14 answers that now cite the right paragraph. Ben, her teammate, has never opened Lessons.
"""

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import lessons_page_story as story_of  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
WRONG = "IEG's own review later said the permits were not the cause."
FEEDBACK = ("viewer_id", "marked", "fixed", "waiting", "kept", "recited", "computed_at", "public_from")
# Asha Raman, an accredited procurement specialist in tests/fixtures/roles.toml.
REVIEWER = {"X-Forwarded-Email": "asha.raman@worldbank.example", "X-Forwarded-User": "id-asha.raman@worldbank.example",
            "X-Forwarded-Access-Token": "not-a-real-token"}


def text(answer) -> str:
    body = answer.json()
    found = body if answer.status_code == 200 else {"status": answer.status_code, "body": body}
    return json.dumps(found, indent=2, ensure_ascii=False) + "\n"


def built_story(fixture_db: Path, folder: Path) -> tuple[tuple[Path, Path], str]:
    """The story built up to October 29, and Ana's first visit's answer, recorded while the library was empty."""
    first = {}
    built = story_of.build(fixture_db, folder, first_visit=lambda answer: first.__setitem__("text", text(answer)))
    return built, first["text"]


def answers(folder: Path, fixture_db: Path = FIXTURE_DB, prebuilt: tuple[tuple[Path, Path], str] | None = None
            ) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds. prebuilt is a story built_story already
    built, which the test that checks these answers shares with the others."""
    (folder / "built").mkdir(parents=True, exist_ok=True)
    built, first = prebuilt or built_story(fixture_db, folder / "built")
    found = {"lessons-page-empty.json": first}

    def fresh(name: str) -> story_of.LessonsStory:
        where = folder / name
        where.mkdir(parents=True, exist_ok=True)
        story = story_of.story_at(built, where)
        with DuckDBEngine.open(story.state_db) as engine:
            engine.insert_rows("strata.ops.retrieval_feedback_viewers", FEEDBACK, [
                ("4021@1984", 2, 1, 1, 0, 14, dt.datetime(2026, 10, 26, 6, tzinfo=dt.UTC), dt.date(2026, 10, 26))])
        return story

    # The whole page, as Ana opens it after the rebidding lesson changed.
    story = fresh("page")
    found["lessons-page.json"] = text(story.page())
    found["lessons-page-preview.json"] = text(story.page(view="piu"))
    # A lesson reviewer, who may ask for a re-check from a card and sees the proposed count's link.
    found["lessons-page-reviewer.json"] = text(story.page(REVIEWER))
    found["lessons-library-method-rfq.json"] = text(story.get("/api/lessons/library", method="Request for Quotations"))
    found["lessons-library-stage.json"] = text(story.get("/api/lessons/library", stage="contract_award"))
    found["lessons-library-past-end.json"] = text(story.get("/api/lessons/library", page=99))
    found["lessons-versions.json"] = text(story.get("/api/evidence", id=f"versions:{story_of.REBIDDING_LESSON}:1:2"))
    found["drafts-lesson-notice.json"] = text(story.get("/api/drafts/draft-0001"))
    # Within the same visit, nothing new since the last one: Ana comes back the next week.
    story.at_time(dt.datetime(2026, 11, 6, 9, 0, tzinfo=dt.UTC))
    found["lessons-page-nothing.json"] = text(story.page())
    # Ben's first visit.
    found["lessons-page-first.json"] = text(story.page(story_of.ppsd_story.BEN))

    # A lesson retired as wrong holds the export.
    story = fresh("retired")
    story_of.scenario.recheck(story.database, story_of.IEG_LESSON, dt.date(2026, 10, 29), "retire_wrong", reason=WRONG)
    found["lessons-page-retired.json"] = text(story.page())
    found["lessons-library-retired.json"] = text(story.get("/api/lessons/library", status="retired"))
    found["drafts-lesson-retired.json"] = text(story.get("/api/drafts/draft-0001"))
    found["lessons-choice-removed.json"] = text(story.call(
        "POST", "/api/drafts/draft-0001/rows/permits_before_award/lesson",
        json={"lesson_id": story_of.IEG_LESSON, "action": "remove", "expected_cited_version": 1,
              "expected_current_version": 3}))

    # A Project Paper summary drawn from the checked rows cites the rebidding lesson in its PPSD part, so retiring that
    # lesson as wrong holds the summary's export too.
    story = fresh("paper")
    _, paper = story.summarize()
    story_of.scenario.recheck(story.database, story_of.REBIDDING_LESSON, dt.date(2026, 10, 30), "retire_wrong",
                              reason=WRONG)
    story.act(paper, "check", "draft")
    found["drafts-paper-lesson-retired.json"] = text(story.get(f"/api/drafts/{paper}"))

    # Keeping version 1, and updating the row, on the changed lesson.
    story = fresh("choices")
    found["lessons-choice-kept.json"] = text(story.call(
        "POST", "/api/drafts/draft-0001/rows/cost_estimates/lesson",
        json={"lesson_id": story_of.REBIDDING_LESSON, "action": "keep", "expected_cited_version": 1,
              "expected_current_version": 2, "reason": "The borrower's estimates already use current rates."}))
    found["lessons-choice-updated.json"] = text(story.update("draft-0002"))
    (folder / "nothing").mkdir(parents=True, exist_ok=True)
    found["lessons-choice-nothing-passed.json"] = text(story_of.story_at(built, folder / "nothing").update(
        "draft-0001", case="ppsd-row-update-nothing-passes"))
    return found


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        for name, written in answers(Path(folder)).items():
            (OUT / name).write_text(written)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
