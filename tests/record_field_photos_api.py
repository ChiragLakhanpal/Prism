"""Write the field photo answers the Deep research tab's screen tests serve (ticket 150; web/tests/field-photos.spec.ts):
GET /api/projects/P156634/field-photos for Ana, World Bank staff, before and after she adds the Baricho photo
tests/test_field_photos.py makes, and the POST's own answer. The routes answer from a copy of the fixture database
with the clock pinned, so the answers hold still; tests/test_field_photos.py checks the routes still answer with them.

    uv run --frozen python tests/record_field_photos_api.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "api"
sys.path.insert(0, str(ROOT / "tests"))

from test_field_photos import ANA, ROUTE, World, call  # noqa: E402


def text(answer) -> str:
    return json.dumps(answer, indent=2, ensure_ascii=False) + "\n"


def answers(folder: Path, fixture_db: Path) -> dict[str, str]:
    world = World(folder, fixture_db)
    before = call(world.app, "GET", ROUTE, ANA).json()
    added = world.add().json()
    after = call(world.app, "GET", ROUTE, ANA).json()
    return {"field-photos-p156634-none.json": text(before), "field-photo-added-p156634.json": text(added),
            "field-photos-p156634.json": text(after)}


def main() -> None:
    fixture = ROOT / "data" / "out" / "fixture.duckdb"
    with tempfile.TemporaryDirectory() as folder:
        for name, body in answers(Path(folder), fixture).items():
            (OUT / name).write_text(body)
            print(f"Wrote tests/fixtures/api/{name}.")


if __name__ == "__main__":
    main()
