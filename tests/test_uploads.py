"""An implementing agency's private upload of its Procurement Plan at seams 2 and 3 (ticket 38).

An officer on team A, the Northern Water Works Development Agency's, uploads the fixture plan through POST
/api/uploads; the server reads it with the STEP column registry, checks it with check_plan, and only then keeps its
activities in strata.ops with the team. A viewer on team B, another agency's, and World Bank staff, get nothing of
it from any route or tool, and a question about it is turned down.

The upload is tests/fixtures/uploads/nwwda-plan-2026-10-09.csv, the plan of October 9, 2026 as STEP prints it
(tests/record_upload_fixture.py). Expected marks come from the benchmark question check_plan answers for the same
plan, whose source is the blueprint's wireframe (tests/ground_truth/values.toml, plan_row wireframe_mark, and
plan.also_lists). App state is a DuckDB file written as the app's own service principal; the fixture database is
opened read-only.
"""

import asyncio
import dataclasses
import datetime as dt
import json
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
import yaml

from strata.config import load_roles
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.uploads.store import UploadStore

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "uploads" / "nwwda-plan-2026-10-09.csv"
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
BENCHMARK = next(question for question in yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]
                 if question["id"] == "check-plan-nwwda-2026-10-09")
TODAY = dt.date(2026, 10, 22)  # the benchmark question's date, so its marks hold
NWWDA = "Northern Water Works Development Agency"


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"50{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


# Amina and Baraka are officers on team A; Chege is an officer on team B; Dana is World Bank staff on no team.
AMINA, BARAKA, CHEGE, DANA = viewer(31, "Amina"), viewer(32, "Baraka"), viewer(33, "Chege"), viewer(34, "Dana")
GROUPS = {"5031@1984": ["users", "strata-agency-nwwda"], "5032@1984": ["users", "strata-agency-nwwda"],
          "5033@1984": ["users", "strata-agency-cwwda"], "5034@1984": ["users"]}


def roles():
    """config/roles.toml, with the test roles file's two implementing agency teams."""
    real = load_roles()
    return dataclasses.replace(real, teams=real.teams + load_roles(ROOT / "tests" / "fixtures" / "roles.toml").teams)


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


@pytest.fixture
def state_db(tmp_path):
    path = tmp_path / "state.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


@pytest.fixture
def make(fixture_db, state_db):
    """The app on the fixture database, with uploads kept in a DuckDB file as the app's own account."""
    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    def build(today=TODAY, store=None):
        numbers = iter(range(1, 100))
        return create_app(engine_for=reading, uploads=store or UploadStore(lambda: DuckDBEngine.open(state_db)),
                          access=Access(roles(), StaticGroups(GROUPS)), today=lambda: today,
                          now=lambda: dt.datetime(2026, 10, 22, 9, 30, tzinfo=dt.UTC),
                          new_upload_id=lambda: f"upl-{next(numbers):012d}")
    return build


def upload(app, headers=AMINA, data=None, name="nwwda-plan-2026-10-09.csv", project="P156634", **query):
    return call(app, "POST", "/api/uploads", headers, params={"project_id": project, "file_name": name, **query},
                content=FIXTURE.read_bytes() if data is None else data)


def marks(result) -> dict[str, list[str]]:
    """The references under each mark, in the benchmark question's shape."""
    found = {"unmarked": sorted(row["activity_reference_no"] for row in result["rows"] if not row["marks"])}
    for mark in ("needs_a_look", "watch", "data_note"):
        found[mark] = sorted(row["activity_reference_no"] for row in result["rows"]
                             if any(given["mark"] == mark for given in row["marks"]))
    return found


# ── Team A uploads its plan and gets its check ───────────────────────────

def test_an_officer_uploads_the_fixture_plan_and_gets_its_check_with_the_published_plans_marks(make):
    app = make()

    answer = upload(app)

    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert result["kept"] is True and result["upload_id"] == "upl-000000000001"
    assert marks(result) == {mark: BENCHMARK["expected"][mark]
                             for mark in ("needs_a_look", "watch", "data_note", "unmarked")}
    # Nine activities: the wireframe's eight and the one it leaves out, in the order of the officer's file.
    references = [row["reference"] for row in TRUTH["plan_row"]] + TRUTH["plan"]["also_lists"]
    assert sorted(row["activity_reference_no"] for row in result["rows"]) == sorted(references)
    assert [row["position"] for row in result["rows"]] == list(range(1, 10))
    assert result["counts"]["activities"] == 9
    # Every row is cited as a row of this upload, public on the day it was kept.
    assert {row["evidence_id"] for row in result["rows"]} == {f"upload-row:upl-000000000001:{n}" for n in range(1, 10)}
    assert {row["public_from"] for row in result["rows"]} == {"2026-10-22"}
    assert result["upload"]["reading"]["activities"] == 9
