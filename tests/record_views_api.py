"""Writes the view switch's recorded answers in tests/fixtures/api from the server itself (ticket 40).

The screen tests serve these files, and tests/test_views.py checks that the server still answers with them, so the
view switch's screens and the server cannot drift apart. Build the fixture database first, then run:

    uv run --frozen python tests/record_views_api.py

Every answer is from the fixture database as of October 23, 2026, with config/roles.toml and the test roles file's
implementing agency teams: Ana is World Bank staff, Amina an officer of the Northern Water Works Development Agency.

- me.json: who is viewing, for a viewer whose groups the app cannot read, the shell's default in every screen test.
- me-preview-piu.json, me-preview-public.json, me-asof.json, me-preview-public-asof.json, me-view-unknown.json,
  me-asof-unreadable.json and me-asof-not-past.json: Ana with each ?view= and ?asof= the screens show.
- me-officer-public.json: Amina's preview of the public view.
- check-plan-p156634-nwwda-2026-10-09-public.json: the plan of October 9, 2026 in the public view, data notes only.
- refused-export-preview.json, refused-check-preview.json, refused-upload-preview.json and
  refused-compare-preview.json: the server's 403 for each check and export a preview refuses.
"""

import asyncio
import datetime as dt
import json
import sys
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_views import GROUPS, OFFICER, STAFF, roles  # noqa: E402

from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.access import Access, StaticGroups  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
TODAY = dt.date(2026, 10, 23)
ANA = {**STAFF, "X-Forwarded-Preferred-Username": "Ana Example"}
PLAN = "/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09"


def _text(response: httpx.Response) -> str:
    return json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n"


def _status(response: httpx.Response) -> str:
    """A refusal as the screen tests serve it: its status and its body."""
    return json.dumps({"status": response.status_code, "body": response.json()}, indent=2, ensure_ascii=False) + "\n"


def answers(fixture_db: Path = FIXTURE_DB) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=reading, access=Access(roles(), StaticGroups(GROUPS)), today=lambda: TODAY)
    plain = create_app(engine_for=reading, today=lambda: TODAY)
    found: dict[str, str] = {}

    async def story():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=plain), base_url="http://strata.test") as client:
            found["me.json"] = json.dumps((await client.get("/api/me", headers=ANA)).json(), ensure_ascii=False) + "\n"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            for name, params in (("me-preview-piu.json", {"view": "piu"}), ("me-preview-public.json", {"view": "public"}),
                                 ("me-asof.json", {"asof": "2016-08-26"}),
                                 ("me-preview-public-asof.json", {"view": "public", "asof": "2016-08-26"}),
                                 ("me-view-unknown.json", {"view": "everyone"}),
                                 ("me-asof-unreadable.json", {"asof": "October-22"}),
                                 ("me-asof-not-past.json", {"asof": TODAY.isoformat()})):
                found[name] = _text(await client.get("/api/me", headers=ANA, params=params))
            found["me-officer-public.json"] = _text(await client.get("/api/me", headers=OFFICER, params={"view": "public"}))
            found["check-plan-p156634-nwwda-2026-10-09-public.json"] = _text(await client.get(
                PLAN, headers=ANA, params={"view": "public", "asof": TODAY.isoformat()}))
            for name, method, path, body in (
                    ("refused-export-preview.json", "POST", "/api/drafts/draft-0001/export", {"expected_state": "checked"}),
                    ("refused-check-preview.json", "POST", "/api/drafts/draft-0001/check", {"expected_state": "draft"}),
                    ("refused-upload-preview.json", "POST", "/api/uploads", None),
                    ("refused-compare-preview.json", "POST", "/api/packages/KE-NWWDA-541055-CW-RFB/criteria/compare",
                     {"text": "Similar experience"})):
                found[name] = _status(await client.request(method, path, headers=ANA, params={"view": "piu"}, json=body))

    asyncio.run(story())
    return found


if __name__ == "__main__":
    for name, text in answers().items():
        (OUT / name).write_text(text)
        print(f"Wrote tests/fixtures/api/{name}.")
