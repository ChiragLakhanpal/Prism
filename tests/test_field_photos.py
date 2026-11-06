"""Ticket 150: field photos at seams 2 and 3. A World Bank staff viewer adds a geo-tagged photo to P156634's Deep
research tab through POST /api/projects/{project_id}/field-photos; the server reads its EXIF date and GPS position
with Pillow and keeps the file beside the app state's DuckDB file, never in the repo. The photo becomes an item of
kind field_photo that research_evidence gives a run by the uploader's team, and nobody else.

Ana and Ben are World Bank staff on the Kenya water and sanitation team (config/roles.toml); Carl is staff on no team.
Each photo is made by the test with Pillow: Baricho Sub-Location's position from P156634's record (3.1 S, 39.78333 E)
and October 14, 2026 in its EXIF data, or no EXIF data at all. The project's locations are its record's
(data/fixture/recorded/api/projects/P156634.json), read as the route reads them.
"""

import asyncio
import copy
import datetime as dt
import json
import subprocess
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
from PIL import Image
from research_world import seeded_copy

from strata.config import load_roles
from strata.lakehouse.engine import DuckDBEngine
from strata.research.photos import LocalFiles, PhotoStore
from strata.research.store import ResearchStore
from strata.research.writer import RecordedJudge, RecordedWriter
from strata.server import field_photos as photo_routes
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.tools import registry
from strata.dbx import viewer_from_headers

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "src" / "strata" / "lakehouse" / "tables" / "ops" / "field_photos.sql"
RECORDED = ROOT / "tests" / "fixtures" / "agent" / "research"
TODAY = dt.date(2026, 11, 5)
NOW = dt.datetime(2026, 11, 5, 10, 30, tzinfo=dt.UTC)
ROUTE = "/api/projects/P156634/field-photos"
CAPTION = "The new intake pipe is laid along the river bank, and the trench beside it is still open."


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"60{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN, CARL = viewer(41, "Ana"), viewer(42, "Ben"), viewer(43, "Carl")
GROUPS = {"6041@1984": ["users", "strata-team-kenya-water"], "6042@1984": ["users", "strata-team-kenya-water"],
          "6043@1984": ["users"]}


def photo(gps: bool = True, size: int = 8, kind: str = "JPEG") -> bytes:
    """A small photo; with gps, Baricho's position and October 14, 2026 in its EXIF data."""
    image = Image.new("RGB", (size, size), (90, 120, 60))
    exif = Image.Exif()
    if gps:
        exif.get_ifd(0x8769)[36867] = "2026:10:14 09:12:00"
        place = exif.get_ifd(0x8825)
        place[1], place[2], place[3], place[4] = "S", (3.0, 6.0, 0.0), "E", (39.0, 47.0, 0.0)
    out = BytesIO()
    image.save(out, kind, exif=exif)
    return out.getvalue()


def call(app, method, path, headers, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers, **options)
    return asyncio.run(go())


def events(text: str) -> list[tuple[str, dict]]:
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if lines:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found


class World:
    """The app on one DuckDB file that holds the fixture, the seeded research run and the app's own tables, the photo
    files in a folder beside it, and the recorded writer and judge."""

    def __init__(self, folder: Path, fixture_db: Path, writer: RecordedWriter | None = None):
        database = seeded_copy(fixture_db, folder)
        self.database = DuckDBEngine.open(database)
        self.database.run(TABLE.read_text())
        self.folder = folder / "field_photos"
        self.access = Access(load_roles(), StaticGroups(GROUPS))
        self.photos = PhotoStore(self.database.cursor, LocalFiles(self.folder))
        self.writer = writer or RecordedWriter(RECORDED / "P156634.json")
        numbers = iter(range(1, 1000))

        @contextmanager
        def reading(viewer):
            yield self.database.cursor()

        self.reading = reading
        self.app = create_app(engine_for=reading, research=ResearchStore(self.database.cursor),
                              research_kit=lambda: None, research_writer=lambda: self.writer,
                              judge=RecordedJudge(RECORDED / "P156634.judged.json"), access=self.access,
                              field_photos=self.photos, today=lambda: TODAY, now=lambda: NOW,
                              new_run_id=lambda: f"research-{next(numbers):04d}",
                              new_photo_id=lambda: f"fph-{next(numbers):012x}")

    def add(self, headers=ANA, data: bytes | None = None, caption: str = CAPTION, name: str = "intake.jpg"):
        return call(self.app, "POST", ROUTE,
                    {**headers, "X-Strata-File-Name": quote(name), "X-Strata-Caption": quote(caption)},
                    content=photo() if data is None else data)

    def evidence(self, headers) -> dict:
        """research_evidence for P156634 as of November 5, 2026, as the viewer's run calls it."""
        person = viewer_from_headers(headers)
        with self.reading(person) as engine:
            return registry.call("research_evidence", {"project_id": "P156634"}, registry.Context(
                engine, person, "staff", TODAY,
                field_photos=photo_routes.reader(self.photos, self.access, person)))


@pytest.fixture
def world(fixture_db, tmp_path):
    return World(tmp_path, fixture_db)


def test_a_staff_viewer_adds_a_geo_tagged_photo_and_sees_it_listed_with_its_date_and_place(world):
    added = world.add()

    assert added.status_code == 200 and added.json()["kept"] is True
    listed = call(world.app, "GET", ROUTE, ANA).json()
    [shown] = listed["photos"]
    assert (shown["taken_on"], shown["place"], shown["caption"]) == ("2026-10-14", "Baricho Sub-Location", CAPTION)
    assert (shown["latitude"], shown["longitude"]) == (-3.1, 39.783333)
    assert listed["may_add"] is True and listed["limits"]["max_per_project"] == 20
    # The file is kept beside the app state's database, outside the repo, and its teammate opens it.
    [kept] = list(world.folder.iterdir())
    assert kept.parent == world.folder  # beside the app state's DuckDB file
    inside = kept.resolve().is_relative_to(ROOT.resolve())  # the gate keeps its scratch in .gate-tmp/, inside the tree
    assert not inside or subprocess.run(["git", "check-ignore", "-q", str(kept)], cwd=ROOT).returncode == 0
    teammate = call(world.app, "GET", shown["url"], BEN)
    assert teammate.status_code == 200 and teammate.content == kept.read_bytes() == photo()
    assert teammate.headers["content-type"] == "image/jpeg"


def test_the_photo_is_a_field_photo_item_for_the_uploader_s_team_only(world):
    world.add()

    rows = world.evidence(BEN)["rows"]
    [item] = [row for row in rows if row["kind"] == "field_photo"]
    assert item["public_from"] is None and item["team"] == "team:kenya-water"
    assert item["observed"] == "2026-10-14" and item["text"] == CAPTION and item["image_urls"] == []
    assert item["location"] == {"geo_loc_id": "200577", "name": "Baricho Sub-Location", "latitude": -3.1,
                                "longitude": 39.783333}
    assert world.evidence(BEN)["counts_by_kind"]["field_photo"] == 1

    outsider = world.evidence(CARL)
    assert [row for row in outsider["rows"] if row["kind"] == "field_photo"] == []
    assert "field_photo" not in outsider["counts_by_kind"]
    url = call(world.app, "GET", ROUTE, ANA).json()["photos"][0]["url"]
    assert call(world.app, "GET", url, CARL).status_code == 403
    assert call(world.app, "GET", ROUTE, CARL).json()["photos"] == []


def test_a_photo_without_gps_is_kept_with_no_location(world):
    assert world.add(data=photo(gps=False), name="no-position.jpg").json()["kept"]

    [shown] = call(world.app, "GET", ROUTE, ANA).json()["photos"]
    assert (shown["taken_on"], shown["place"], shown["latitude"]) == (None, None, None)
    [item] = [row for row in world.evidence(ANA)["rows"] if row["kind"] == "field_photo"]
    assert item["location"] is None and item["observed"] is None
    assert "a position its data did not record" in item["title"]


def test_the_size_count_and_format_limits_refuse_politely_and_keep_nothing(world):
    too_big = world.add(data=b"\xff\xd8" + b"0" * 10_485_760)
    assert too_big.status_code == 422 and too_big.json() == {**too_big.json(), "code": "size", "kept": False}
    not_a_photo = world.add(data=b"%PDF-1.7 not a photo", name="plan.pdf")
    assert not_a_photo.status_code == 422 and not_a_photo.json()["code"] == "format"
    assert world.add(caption=" ").json()["code"] == "caption"
    assert call(world.app, "GET", ROUTE, ANA).json()["photos"] == []

    for _ in range(20):
        assert world.add().json()["kept"] is True
    over = world.add()
    assert over.status_code == 422 and over.json() == {**over.json(), "code": "count", "kept": False,
                                                       "max_per_project": 20}
    assert len(call(world.app, "GET", ROUTE, ANA).json()["photos"]) == 20


def test_only_world_bank_staff_add_a_photo_and_a_preview_sees_none(world):
    officer = {**ANA, "X-Forwarded-User": "6044@1984"}  # signed in, but in no group, so not staff
    assert world.add(headers=officer).status_code == 403
    world.add()
    assert call(world.app, "GET", ROUTE + "?view=public", ANA).json()["photos"] == []
    added = call(world.app, "POST", ROUTE + "?view=piu", {**ANA, "X-Strata-File-Name": "a.jpg",
                                                         "X-Strata-Caption": "A caption."}, content=photo())
    assert added.status_code == 403


def with_photo_sentence(answer: dict, evidence_id: str) -> dict:
    """The recorded writer answer with one more development: the photo, described by its caption and its date."""
    brief = json.loads(answer["response"]["choices"][0]["message"]["content"])
    brief["developments"].insert(0, {"date": "2026-10-14", "date_known": True, "sentences": [{
        "sentence": f'A field photo taken at Baricho on October 14, 2026 carries the caption "{CAPTION}"',
        "kind": "quote", "evidence_ids": [evidence_id], "numbers": [], "dates": ["October 14, 2026"],
        "quote": {"passage_id": evidence_id, "text": CAPTION}}]})
    changed = copy.deepcopy(answer)
    changed["response"]["choices"][0]["message"]["content"] = json.dumps(brief)
    return changed


def test_the_brief_cites_the_photo_by_its_caption_and_date_and_only_the_team_reads_it(fixture_db, tmp_path):
    item = "strata.research.item:P156634/field_photos/fph-000000000001"
    recording = tmp_path / "with-photo.json"
    recording.write_text(json.dumps(with_photo_sentence(json.loads((RECORDED / "P156634.json").read_text()), item)))
    world = World(tmp_path, fixture_db, writer=RecordedWriter(recording))
    assert world.add().json()["photo"]["photo_id"] == "fph-000000000001"

    sent = events(call(world.app, "POST", "/api/projects/P156634/research", ANA, json={"reuse": True}).text)

    brief = sent[-1][1]["brief"]
    [photo_said] = [sentence for group in brief["developments"] for sentence in group["sentences"]
                    if item in sentence["evidence_ids"]]
    assert CAPTION in photo_said["text"] and "October 14, 2026" in photo_said["text"]
    assert brief["developments"][0]["date"] == "2026-10-14"
    # The writer read the photo only as its caption and its fields, never the image: the writer has no tools, and the
    # message holds no image and no file name.
    message = json.loads(world.writer.calls[0])
    [sent_item] = [entry for entry in message["items"] if entry["kind"] == "field_photo"]
    assert sent_item["text"] == CAPTION and sent_item["location"] == "Baricho Sub-Location"
    assert "image_urls" not in sent_item and not any(".jpg" in str(value) for value in sent_item.values())
    # A preview of the public view, even Ana's own, reads no team brief.
    preview = call(world.app, "GET", "/api/projects/P156634/research?view=public", ANA).json()
    assert CAPTION not in json.dumps(preview)

    # The brief is the team's: Ben reads it; Carl reads no brief with the photo, and the evidence drawer gives him
    # nothing of it.
    assert CAPTION in json.dumps(call(world.app, "GET", "/api/projects/P156634/research", BEN).json())
    outsider = call(world.app, "GET", "/api/projects/P156634/research", CARL).json()
    assert CAPTION not in json.dumps(outsider)
    drawer = call(world.app, "GET", "/api/evidence", CARL, params={"id": item, "asof": "2026-11-05"})
    assert drawer.status_code == 404
    opened = call(world.app, "GET", "/api/evidence", BEN, params={"id": item, "asof": "2026-11-05"}).json()
    assert opened["row"]["text"] == CAPTION and opened["row"]["team"] == "team:kenya-water"


def test_a_run_by_a_viewer_outside_the_team_never_sees_the_photo(fixture_db, tmp_path):
    world = World(tmp_path, fixture_db)
    world.add()

    sent = events(call(world.app, "POST", "/api/projects/P156634/research", CARL, json={"reuse": True}).text)

    assert sent[-1][1]["status"] == "written"
    message = json.loads(world.writer.calls[0])
    assert [entry for entry in message["items"] if entry["kind"] == "field_photo"] == []
    assert CAPTION not in json.dumps(sent)


def test_the_tab_s_recorded_photo_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """tests/record_field_photos_api.py writes the answers the tab's screen tests serve (web/tests/field-photos.spec.ts);
    the routes still answer with them."""
    from record_field_photos_api import OUT, answers

    for name, text in answers(tmp_path, fixture_db).items():
        assert text == (OUT / name).read_text(), f"Record {name} again: uv run --frozen python tests/record_field_photos_api.py"
