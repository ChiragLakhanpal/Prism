"""Writes the upload screens' recorded answers in tests/fixtures/api from the server itself (ticket 38).

The screen tests serve these files, and tests/test_step_rows.py checks that the server still answers with them, so
the upload screens and the server cannot drift apart. Build the fixture database first, then run:

    uv run --frozen python tests/record_uploads_api.py

Two stories make them:

- On the fixture, as of October 22, 2026, Amina (team A, the Northern Water Works Development Agency's officer) opens
  Check my plan, uploads tests/fixtures/uploads/nwwda-plan-2026-10-09.csv and opens its check; Dana (World Bank
  staff) opens Check my plan; and a file with no Method column is refused: me-officer.json, uploads-form-officer.json,
  uploads-form-staff.json, upload-kept.json, upload-check-nwwda.json, uploads-list-nwwda.json,
  upload-missing-columns.json and upload-not-found.json.
- On ticket 27's hand-made set (tests/step_set.py), as of January 15, 2021, Amina uploads the target package with its
  own dates and drafts planned dates: drafts-step-rows-draft.json, the draft as its page shows it. She drafts them
  again while the draft states one cautious date estimate_time did not return (test_step_rows's fault injection), and
  the verifier removes it: drafts-step-rows-removed.json.
"""

import asyncio
import datetime as dt
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import step_set  # noqa: E402
from test_step_rows import HAND_PROJECT, NWWDA, a_value_the_delay_model_did_not_return, hand_file  # noqa: E402
from test_uploads import AMINA, DANA, FIXTURE, GROUPS, roles  # noqa: E402

from strata.drafts.store import DraftStore  # noqa: E402
from strata.lakehouse import catalog  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.access import Access, StaticGroups  # noqa: E402
from strata.server.app import create_app  # noqa: E402
from strata.uploads.store import UploadStore  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"


def _app(database: Path, state: Path, today: dt.date, at: dt.datetime):
    with DuckDBEngine.open(state) as engine:
        catalog.build(engine)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    numbers = iter(range(1, 100))
    return create_app(engine_for=reading, uploads=UploadStore(lambda: DuckDBEngine.open(state)),
                      drafts=DraftStore(lambda: DuckDBEngine.open(state)), access=Access(roles(), StaticGroups(GROUPS)),
                      today=lambda: today, now=lambda: at, new_upload_id=lambda: f"upl-{next(numbers):012d}",
                      new_draft_id=lambda: f"draft-{next(numbers):04d}", new_run_id=lambda: "run-0001")


def _text(response: httpx.Response) -> str:
    return json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"


def answers(folder: Path, fixture_db: Path = FIXTURE_DB) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    found: dict[str, str] = {}
    app = _app(fixture_db, folder / "state.duckdb", dt.date(2026, 10, 22), dt.datetime(2026, 10, 22, 9, 30, tzinfo=dt.UTC))
    hand_db = folder / "hand.duckdb"
    engine = step_set.build(hand_db)
    step_set.insert(engine, "strata.gold.project", [{"project_id": HAND_PROJECT, "project_name": "Hand-made water project",
                                                     "country_code": "KE", "region": "Eastern and Southern Africa",
                                                     "implementing_agency": NWWDA, "public_from": dt.date(2018, 1, 1)}])
    engine.close()
    hand = _app(hand_db, folder / "hand-state.duckdb", dt.date(2021, 1, 15), dt.datetime(2021, 1, 15, 10, 0, tzinfo=dt.UTC))

    async def story():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            found["me-officer.json"] = _text(await client.get("/api/me", headers=AMINA))
            found["uploads-form-officer.json"] = _text(await client.get("/api/uploads/form", headers=AMINA))
            found["uploads-form-staff.json"] = _text(await client.get("/api/uploads/form", headers=DANA))
            kept = await client.post("/api/uploads", headers={**AMINA, "X-Strata-File-Name": "nwwda-plan-2026-10-09.csv"},
                                     content=FIXTURE.read_bytes(), params={"project_id": "P156634"})
            found["upload-kept.json"] = _text(kept)
            upload_id = kept.json()["upload_id"]
            found["upload-check-nwwda.json"] = _text(await client.get(f"/api/uploads/{upload_id}", headers=AMINA))
            found["uploads-list-nwwda.json"] = _text(await client.get("/api/uploads", headers=AMINA))
            found["upload-not-found.json"] = _text(await client.get(f"/api/uploads/{upload_id}", headers=DANA))
            found["upload-missing-columns.json"] = _text(await client.post(
                "/api/uploads", headers={**AMINA, "X-Strata-File-Name": "draft-plan.csv"}, params={"project_id": "P156634"},
                content=b"Activity Reference No. / Description,Review Type\r\n / New works,Post\r\n"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=hand), base_url="http://strata.test") as client:
            kept = await client.post("/api/uploads", headers={**AMINA, "X-Strata-File-Name": "team-a-plan.csv"},
                                     content=hand_file(), params={"project_id": HAND_PROJECT})
            source = f"upload:{kept.json()['upload_id']}"
            sent = await client.post("/api/drafts", headers=AMINA, json={"kind": "step_rows", "source": source,
                                                                         "idempotency_key": "key-1"})
            draft_id = next(json.loads(line.removeprefix("data: "))["draft_id"] for line in sent.text.splitlines()
                            if line.startswith("data: ") and "draft_id" in line)
            found["drafts-step-rows-draft.json"] = _text(await client.get(f"/api/drafts/{draft_id}", headers=AMINA))
            with a_value_the_delay_model_did_not_return("date"):
                sent = await client.post("/api/drafts", headers=AMINA, json={"kind": "step_rows", "source": source,
                                                                             "idempotency_key": "key-2"})
            draft_id = next(json.loads(line.removeprefix("data: "))["draft_id"] for line in sent.text.splitlines()
                            if line.startswith("data: ") and "draft_id" in line)
            found["drafts-step-rows-removed.json"] = _text(await client.get(f"/api/drafts/{draft_id}", headers=AMINA))

    asyncio.run(story())
    return found


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as folder:
        for name, text in answers(Path(folder)).items():
            (OUT / name).write_text(text)
            print(f"Wrote tests/fixtures/api/{name}.")
