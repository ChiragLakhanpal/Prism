"""Ticket 156: the demo's sample field photos, kept for the staff team through ticket 150's photo store
(ops/research/seed_photos.py), each with a caption that says it stands in for a staff photo."""

import datetime as dt
import importlib.util
from pathlib import Path

from strata.config import load_roles
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.research.photos import LocalFiles, PhotoStore
from strata.server.access import Access, StaticGroups
from strata.server.field_photos import reader

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "src" / "strata" / "lakehouse" / "tables" / "ops" / "field_photos.sql"
SPEC = importlib.util.spec_from_file_location("seed_photos", ROOT / "ops" / "research" / "seed_photos.py")
seed_photos = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seed_photos)
PROJECTS = ["P156634", "P161305", "P145559", "P167814", "P130164"]
TEAMMATE, OUTSIDER = "6041@1984", "6043@1984"
GROUPS = {TEAMMATE: ["users", "strata-team-kenya-water"], OUTSIDER: ["users"]}


def store_in(folder: Path) -> PhotoStore:
    database = DuckDBEngine.open(folder / "state.duckdb")
    database.run("CREATE SCHEMA IF NOT EXISTS ops")
    database.run(TABLE.read_text())
    return PhotoStore(database.cursor, LocalFiles(folder / "field_photos"))


def test_each_seeded_project_keeps_two_or_three_sample_photos_for_the_staff_team_once(tmp_path):
    store = store_in(tmp_path)
    team = f"team:{load_roles().teams[0].key}"

    counts = seed_photos.seed(store, PROJECTS, team, say=lambda line: None)

    assert set(counts) == set(PROJECTS) and all(2 <= counts[project] <= 3 for project in PROJECTS), counts
    assert seed_photos.seed(store, PROJECTS, team, say=lambda line: None) == {project: 0 for project in PROJECTS}
    for project in PROJECTS:
        for photo in store.for_team(project, team, "someone-else"):
            # The caption says what the photo is, so nothing claims a World Bank staff member took it.
            assert photo.caption.startswith("Sample photo standing in for a staff photo: Wikimedia Commons, by ")
            assert photo.taken_on is not None and f"taken {photo.taken_on.strftime('%B')} {photo.taken_on.day}" in photo.caption
            assert store.file(photo)[:2] == b"\xff\xd8"  # the JPEG itself, in the store's files


def test_a_run_by_the_team_reads_the_sample_photos_as_items_by_their_caption_and_no_one_else_does(tmp_path):
    store = store_in(tmp_path)
    access = Access(load_roles(), StaticGroups(GROUPS))
    seed_photos.seed(store, ["P156634"], f"team:{load_roles().teams[0].key}", say=lambda line: None)

    teammate = reader(store, access, Viewer(email="a@worldbank.org", name="A", user_id=TEAMMATE))
    outsider = reader(store, access, Viewer(email="b@worldbank.org", name="B", user_id=OUTSIDER))

    items = teammate("P156634", dt.date(2026, 11, 5))
    assert len(items) >= 2 and all(item["kind"] == "field_photo" and item["image_urls"] == [] for item in items)
    assert all(item["text"].startswith("Sample photo standing in for a staff photo") for item in items)
    # The item says a staff member added the photo, never that one took it.
    assert all(item["title"].endswith(", added by a World Bank staff member") for item in items)
    assert outsider("P156634", dt.date(2026, 11, 5)) == []
    # Added on the sample's day, so a run as of the day before reads none.
    assert teammate("P156634", dt.date(2026, 11, 4)) == []
