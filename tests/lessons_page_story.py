"""The Lessons page story (ticket 39; the 39 design brief, section 13), through the HTTP routes, shared by
tests/test_lessons_page.py and tests/record_lessons_page_api.py.

Built on tests/ppsd_story.py's app, with the same scripted writer and judge, on a copy of the fixture database:

- Thursday, October 22, 2026, at noon: Ana, World Bank staff on the Kenya water team and no lesson reviewer, opens
  Lessons for the first time. The library is empty, and the fixture's three proposed lessons enter the queue the next
  day.
- Tuesday, October 27: reviewers add the rebidding lesson (ICR P130164 paragraph 54) and IEG's own lesson (section 12
  of the ICR Review) to the library, each at version 1 (tests/lesson_scenario.py).
- Wednesday, October 28: Ana suggests PPSD rows for KE-NWWDA-541055-CW-RFB twice. Both drafts cite the rebidding
  lesson at version 1 in the cost estimates row and IEG's lesson at version 1 in the permits row. She marks the second
  draft as checked.
- Thursday, October 29: a re-check changes the rebidding lesson's wording (version 2, the "narrowed" tier), and the
  lesson review writer names IEG's lesson as a likely repeat of paragraph 55's proposal, which a lead merges into it
  as more evidence (version 2, "strengthened").

Every lesson act goes through the same LessonReview the HTTP routes use; nothing writes a lesson row by hand.
Reading a story at a later point copies both databases, so each test gets its own.
"""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

import lesson_scenario as scenario
import ppsd_story
from strata.agent.scripted import load_cases
from strata.config import load_roles
from strata.knowledge.lessons import writer
from strata.knowledge.lessons.review import LessonReview
from strata.knowledge.lessons.visits import LessonVisits
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
ROLES = load_roles(ROOT / "tests" / "fixtures" / "roles.toml")
ROW_UPDATES = ROOT / "tests" / "fixtures" / "agent" / "row_updates.toml"
ANA = ppsd_story.ANA
REBIDDING_LESSON, IEG_LESSON = "lesson-e903b07ad1", "lesson-cfdf000a46"
FIRST_VISIT = dt.datetime(2026, 10, 22, 12, 0, tzinfo=dt.UTC)
DECIDED, WRITTEN, CHANGED = dt.date(2026, 10, 27), dt.date(2026, 10, 28), dt.date(2026, 10, 29)
NEXT_VISIT = dt.datetime(2026, 10, 30, 9, 0, tzinfo=dt.UTC)
NARROWED = "Base works cost estimates on current market rates to avoid rebidding"


class LessonsStory(ppsd_story.Story):
    """ppsd_story's app with the Lessons page's parts: the lesson review on the story's clock and the visits."""

    def __init__(self, database: Path, folder: Path, kinds=None):
        self.database = database
        super().__init__(database, folder, kinds)
        self.cases |= load_cases(ROW_UPDATES)

    def app_options(self, state) -> dict:
        return {"lessons": LessonReview(ROLES, today=lambda: self.at.date(), now=lambda: self.at),
                "visits": LessonVisits(state), "today": lambda: self.at.date()}

    def update(self, draft_id: str, case: str = "ppsd-row-update-cost-estimates", headers=ANA, **body):
        """"Update the row" on a draft's cost estimates row, with the scripted writer replaying a row update."""
        self.case = case
        return self.call("POST", f"/api/drafts/{draft_id}/rows/cost_estimates/lesson", headers,
                         json={"lesson_id": REBIDDING_LESSON, "action": "update", "expected_cited_version": 1,
                               "expected_current_version": 2, **body})

    def at_time(self, when: dt.datetime) -> LessonsStory:
        self.at = when
        return self

    def page(self, headers=ANA, **params):
        return self.get("/api/lessons/page", headers, **params)


def build(fixture_db: Path, folder: Path) -> tuple[Path, Path]:
    """The story up to October 29, in folder: the lessons database and the app state's database."""
    database = scenario.copy_of(fixture_db, folder)
    story = LessonsStory(database, folder)
    story.at_time(FIRST_VISIT).page()
    for passage in (scenario.REBIDDING, scenario.IEG_LESSON):
        scenario.decide(database, passage, DECIDED)
    story.at_time(dt.datetime.combine(WRITTEN, dt.time(9), tzinfo=dt.UTC))
    story.select()
    story.suggest(key="ppsd-1")
    story.suggest(key="ppsd-2")
    story.act("draft-0002", "check", "draft")
    scenario.recheck(database, REBIDDING_LESSON, CHANGED, "change", change={"statement": NARROWED},
                     reason="Current market rates is what the 2025 rules ask for.")
    with DuckDBEngine.open(database) as engine:
        writer.run(engine, writer.recorded_agent_for(),
                   lambda: dt.datetime.combine(CHANGED, dt.time(10), tzinfo=dt.UTC), 3)
    scenario.decide(database, scenario.PERMITS, CHANGED, outcome="repeat", repeat_of=IEG_LESSON)
    return database, story.state_db


def story_at(built: tuple[Path, Path], folder: Path, when: dt.datetime = NEXT_VISIT) -> LessonsStory:
    """A copy of a built story, its own app on the copies, at a moment."""
    database, state = built
    shutil.copy(database, folder / "fixture.duckdb")
    shutil.copy(state, folder / "state.duckdb")
    return LessonsStory(folder / "fixture.duckdb", folder).at_time(when)
