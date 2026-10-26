"""Home's story (ticket 41; the 41 design brief, section 13), through the HTTP routes, shared by tests/test_home.py and
tests/record_home_api.py.

Built on tests/ppsd_story.py's app, on a copy of the fixture database whose three proposed lessons two reviewers added
to the library on October 27, 2026, as of Wednesday, October 28, 2026:

- Ana, World Bank staff on the Kenya water team, is in the reviewing panel. The seed command (strata.seed_examples)
  sets up her examples through the routes: she follows P156634 and P130164, has review notes on the NWWDA plan of
  October 9, 2026 and suggested PPSD rows for KE-NWWDA-541055-CW-RFB in Draft, a package planned from "rural roads,
  Kenya, about US$15 million", and a changed wording of the first lesson the rows cite, which only she sees. The
  scripted writers, reader and judge replay their recorded cases (tests/fixtures/agent).
- Ben, her teammate, follows nothing and has no draft: his Home is the first run.
- The fixture's data-through date is October 23, 2026, so a window of seven days (Home's default) starts on October 17
  and leaves the plan of October 9 out. The story's thresholds set home.window_days to 15, from October 9 to 23, so
  the plan's activities show, as on a demo day when the data-through date is close to the plan (the 41 brief, 13).

A read of a built story copies both databases, so each test gets its own.
"""

from __future__ import annotations

import datetime as dt
import shutil
from contextlib import contextmanager
from pathlib import Path

import ppsd_story
from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases
from strata.config import load_examples, load_roles, load_thresholds
from strata.drafts.store import DraftStore
from strata.knowledge.lessons.review import LessonReview
from strata.knowledge.lessons.visits import LessonVisits
from strata.lakehouse.engine import DuckDBEngine
from strata.seed_examples import Panelist, seed
from strata.server.following import FollowStore
from strata.server.home import HomeStore

ROOT = Path(__file__).resolve().parents[1]
ANA, BEN, CY = ppsd_story.ANA, ppsd_story.BEN, ppsd_story.CY
ANA_PANELIST = Panelist(ANA["X-Forwarded-Email"], "Ana Example", ANA["X-Forwarded-User"])
TODAY = ppsd_story.TODAY
WINDOW_DAYS = 15
# The scripted writer case each kind of draft replays (tests/fixtures/agent/writers.toml).
DRAFT_CASES = {"review_notes": "review-notes-nwwda-2026-10-09", "ppsd_rows": "ppsd-rows-ke-nwwda-541055"}
PACKAGES = load_cases(PACKAGE_CASES)


def thresholds_with(folder: Path, window_days: int):
    """config/thresholds.toml with Home's window set to this many days."""
    path = folder / f"thresholds-{window_days}.toml"
    text = (ROOT / "config" / "thresholds.toml").read_text()
    path.write_text(text.replace("window_days = 7\n", f"window_days = {window_days}\n", 1))
    return load_thresholds(path)


class HomeStory(ppsd_story.Story):
    """ppsd_story's app with Home's parts: the follows, Home's store, the package reader and a window of 15 days."""

    def __init__(self, database: Path, folder: Path, window_days: int = WINDOW_DAYS):
        self.database = database
        self.limits = thresholds_with(folder, window_days)
        super().__init__(database, folder)

    def state(self):
        return DuckDBEngine.open(self.state_db)

    def app_options(self, state) -> dict:
        # Fixed package ids, so the recorded answers that name the seeded package stay the same from run to run.
        package_ids = iter(f"pkg-{number:012x}" for number in range(1, 100))
        return {"follows": FollowStore(state), "home": HomeStore(state), "thresholds": self.limits,
                "new_package_id": lambda: next(package_ids),
                "package_reader": lambda: ScriptedAgent(PACKAGES["package-rural-roads-kenya"]),
                "visits": LessonVisits(state), "lessons": LessonReview(load_roles(), today=lambda: TODAY)}

    def seeder(self):
        """The calls the seed command makes, each draft's writer replaying its recorded case."""
        def call(method: str, path: str, headers: dict, body: dict | None = None):
            if method == "POST" and path == "/api/drafts" and body:
                self.case = DRAFT_CASES[body["kind"]]
            return self.call(method, path, headers, json=body)
        return call

    def lessons(self):
        @contextmanager
        def reading(_viewer=None):
            with DuckDBEngine.open(self.database, read_only=True) as engine:
                yield engine
        return reading

    def seed(self, people=(ANA_PANELIST,)) -> dict:
        return seed(self.seeder(), list(people), load_examples(), HomeStore(self.state), DraftStore(self.state),
                    self.lessons(), now=self.clock)

    def home(self, headers=ANA, **params):
        return self.get("/api/home", headers, **params)

    def store(self) -> HomeStore:
        return HomeStore(self.state)


def build(fixture_db: Path, folder: Path) -> tuple[Path, Path]:
    """The story with Ana's examples set up: the library database and the app state's database."""
    database = ppsd_story.library(fixture_db, folder)
    story = HomeStory(database, folder)
    story.seed()
    return database, story.state_db


def story_at(built: tuple[Path, Path], folder: Path, window_days: int = WINDOW_DAYS) -> HomeStory:
    """A copy of a built story, with its own app on the copies."""
    database, state = built
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(database, folder / "fixture.duckdb")
    shutil.copy(state, folder / "state.duckdb")
    story = HomeStory(folder / "fixture.duckdb", folder, window_days)
    # Later the same day than the seed command ran, so what the test does comes after what was set up.
    story.at = at(TODAY, 12)
    return story


def at(day: dt.date, hour: int = 9) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hour), tzinfo=dt.UTC)
