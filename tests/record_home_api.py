"""Writes Home's recorded answers in tests/fixtures/api from the server itself (ticket 41).

The screen tests and the capture list serve these files, and tests/test_home.py checks that the server still answers
with them, so Home's screens and the server cannot drift apart. Build the fixture database first, then run:

    uv run --frozen python tests/record_home_api.py

The story is tests/home_story.py's, as of Wednesday, October 28, 2026, with a window of 15 days ending on the fixture's
data-through date, October 23:

- home.json: Ana's Home, with the examples the seed command set up for her.
- home-first-run.json: Ben's, who follows nothing and has no draft.
- home-quiet.json: Ben's once he follows P130164, which closed in 2018, so nothing changed in the window.
- home-preview-piu.json and home-preview-public.json: Ana's previews of an implementing agency officer's Home (the
  Northern Water Works Development Agency's) and the public's.
- home-asof.json: Ana's Home as of October 20, 2026.
- home-nothing-marked.json: Ana's Home as of March 25, 2025, when one plan changed in the window (Kilifi - Mariakani's
  of March 19, 2025) and check_plan marked none of its activities.
- home-drafts-checked.json: Ana's Home once she marked both drafts as checked.
- me-home.json: who Ana is, World Bank staff whose Start here strip shows.
- start-here-removed.json, start-here-shown.json and start-here-refused-preview.json: the answers to removing the strip,
  showing it again, and trying to remove it in a preview.
- example-rural-roads-kenya.json: the sentence "Plan a package from a sentence" fills into the box.
- following-examples.json and planned-packages-examples.json: Ana's Following and Packages tab, where the follows and
  the package the seed command set up for her are labeled as examples.
- drafts-existing-example-review-notes.json and drafts-existing-example-ppsd-rows.json: the open drafts the October 9
  plan check and the workspace of KE-NWWDA-541055-CW-RFB name for Ana, which the seed command set up for her.
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import home_story  # noqa: E402
from home_story import ANA, BEN  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"


def text(answer) -> str:
    body = answer.json()
    found = body if answer.status_code == 200 else {"status": answer.status_code, "body": body}
    return json.dumps(found, indent=2, ensure_ascii=False) + "\n"


def answers(folder: Path, fixture_db: Path = FIXTURE_DB, built: tuple[Path, Path] | None = None) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    if built is None:
        (folder / "built").mkdir(parents=True, exist_ok=True)
        built = home_story.build(fixture_db, folder / "built")
    found: dict[str, str] = {}

    story = home_story.story_at(built, folder / "home")
    found["home.json"] = text(story.home())
    found["me-home.json"] = text(story.get("/api/me"))
    found["home-first-run.json"] = text(story.home(BEN))
    found["home-preview-piu.json"] = text(story.home(view="piu"))
    found["home-preview-public.json"] = text(story.home(view="public"))
    found["home-asof.json"] = text(story.home(asof="2026-10-20"))
    found["home-nothing-marked.json"] = text(story.home(asof="2025-03-25"))
    found["example-rural-roads-kenya.json"] = text(story.get("/api/examples/rural_roads_kenya"))
    found["following-examples.json"] = text(story.get("/api/following"))
    found["planned-packages-examples.json"] = text(story.get("/api/planned-packages"))
    found["drafts-existing-example-review-notes.json"] = text(story.get(
        "/api/drafts/existing", kind="review_notes", project_id="P156634",
        agency_id="northern-water-works-development-agency", plan_date="2026-10-09"))
    found["drafts-existing-example-ppsd-rows.json"] = text(story.get(
        "/api/drafts/existing", kind="ppsd_rows", package="KE-NWWDA-541055-CW-RFB"))
    found["start-here-refused-preview.json"] = text(
        story.call("POST", "/api/home/start-here", json={"visible": False, "view": "public"}))
    found["start-here-removed.json"] = text(
        story.call("POST", "/api/home/start-here", json={"visible": False, "view": "staff"}))
    found["start-here-shown.json"] = text(
        story.call("POST", "/api/home/start-here", json={"visible": True, "view": "staff"}))

    quiet = home_story.story_at(built, folder / "quiet")
    quiet.call("PUT", "/api/projects/P130164/follow", BEN, json={"view": "staff"})
    found["home-quiet.json"] = text(quiet.home(BEN))

    checked = home_story.story_at(built, folder / "checked")
    for row in checked.home().json()["waiting"]["rows"]:
        checked.act(row["draft_id"], "check", "draft")
    found["home-drafts-checked.json"] = text(checked.home())
    return found


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        for name, written in answers(Path(folder)).items():
            (OUT / name).write_text(written)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
