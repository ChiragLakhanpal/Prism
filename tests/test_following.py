"""Following at seam 3: follows saved per viewer, and the Following page's read, through the HTTP routes (ticket 37).

PUT and DELETE /api/projects/{project_id}/follow follow and unfollow a project, saved per viewer in strata.ops as
the app's own service principal (a DuckDB file here). GET /api/following runs project_signals on each project the
viewer follows and answers only to viewers with the World Bank staff role, which the roles file's [staff] names
by workspace group. The fixture database is opened read-only, and today is October 22, 2026, ticket 09's as-of date.
"""

import asyncio
import datetime as dt
from contextlib import contextmanager

import httpx
import pytest

from strata.config import load_roles
from strata.drafts.store import DraftStore
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.server.following import FollowStore

TODAY = dt.date(2026, 10, 22)


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"50{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN, CY = viewer(1, "Ana"), viewer(2, "Ben"), viewer(3, "Cy")
# Ana and Ben are in the workspace's users group, which the roles file names as World Bank staff; Cy is in none.
GROUPS = {"501@1984": ["users"], "502@1984": ["users", "strata-team-kenya-water"], "503@1984": []}


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


@pytest.fixture
def app(fixture_db, tmp_path):
    state_db = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        catalog.build(engine)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    moments = iter(dt.datetime(2026, 10, 22, 14, minute, tzinfo=dt.UTC) for minute in range(60))
    return create_app(engine_for=reading, follows=FollowStore(lambda: DuckDBEngine.open(state_db)),
                      drafts=DraftStore(lambda: DuckDBEngine.open(state_db)),
                      access=Access(load_roles(), StaticGroups(GROUPS)), today=lambda: TODAY, now=lambda: next(moments))


def test_follows_are_saved_per_viewer_and_the_following_page_runs_the_checks_on_each(app):
    assert call(app, "PUT", "/api/projects/P156634/follow", ANA).json() == {"following": True}

    assert call(app, "GET", "/api/projects/P156634/follow", ANA).json()["following"] is True
    assert call(app, "GET", "/api/projects/P156634/follow", BEN).json()["following"] is False
    mine = call(app, "GET", "/api/following", ANA).json()
    [followed] = mine["projects"]
    assert followed["project"]["project_id"] == "P156634" and followed["status"] == "needs_a_look"
    assert sorted(row["check"] for row in followed["rows"]) == [
        "above_estimate", "closing_moves", "completion_passed", "late_direct"]
    assert call(app, "GET", "/api/following", BEN).json()["projects"] == []


def test_unfollowing_takes_the_project_off_the_list_and_following_again_puts_it_back(app):
    call(app, "PUT", "/api/projects/P156634/follow", ANA)
    call(app, "PUT", "/api/projects/P130164/follow", ANA)

    assert call(app, "DELETE", "/api/projects/P156634/follow", ANA).json() == {"following": False}
    [left] = call(app, "GET", "/api/following", ANA).json()["projects"]
    assert left["project"]["project_id"] == "P130164" and left["status"] == "closed"


def test_the_following_route_and_follows_refuse_a_viewer_without_the_world_bank_staff_role(app):
    assert call(app, "GET", "/api/following", CY).status_code == 403
    assert call(app, "GET", "/api/following", CY).json()["code"] == "not_staff"
    assert call(app, "PUT", "/api/projects/P156634/follow", CY).json()["code"] == "not_staff"
    assert call(app, "GET", "/api/me", ANA).json()["staff"] is True
    assert call(app, "GET", "/api/me", CY).json()["staff"] is False


def test_a_preview_reads_no_following_list_and_writes_no_follow(app):
    assert call(app, "GET", "/api/following?view=piu", ANA).json()["code"] == "preview"
    assert call(app, "PUT", "/api/projects/P156634/follow?view=public", ANA).status_code == 403
