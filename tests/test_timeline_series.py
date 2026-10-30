"""The timeline's rating sentence and its band row read one series (ticket 142), at seam 3: GET
/api/projects/{pid}/timeline and the band's evidence view, on planted copies of the fixture database.

On October 30, 2026 P161305's Timeline tab said ISR ratings of progress "fell from Satisfactory to Moderately
Satisfactory" while its band row seemed to end at "MU, ISRs 10 to 11": the assertions pass had made no assertion of ISR
13's rating (its page had no passage to cite), so the series stopped at ISR 12, whose one-ISR band drew no wider than a
line, while the ISR ratings table and the Summary held ISR 13. Here P130164 plays both cases:

- the assertions stop before the table: ISR 13's assertion of progress towards the PDO is taken out, as the workspace's
  pass left P161305's out, so the table (strata.silver.isr_ratings) holds the fuller series;
- the table stops before the assertions: ISR 13's rows are taken out of the table, so the assertions hold the fuller one.

The dates and ratings are tests/ground_truth/values.toml's, read from it by id.
"""

import asyncio
import datetime as dt
import shutil
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app
from strata.server.timeline import text_of

TRUTH = {value["id"]: value for value in
         tomllib.loads((Path(__file__).parent / "ground_truth" / "values.toml").read_text())["value"]}
HEADERS = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
           "X-Forwarded-Access-Token": "token-for-ana-only"}
DAY = "asof=2026-10-23"
# ISR 13's rating of progress towards the PDO as the assertions pass made it, and as the ISR ratings table holds it.
NO_ASSERTION = """DELETE FROM strata.gold.assertion
WHERE project_id = 'P130164' AND attribute = 'pdo_progress' AND evidence_tier = 'isr' AND sequence = 13"""
NOT_IN_TABLE = "DELETE FROM strata.silver.isr_ratings WHERE project_id = 'P130164' AND sequence = 13"


def truth(key):
    value = TRUTH[key]["value"]
    return value.isoformat() if hasattr(value, "isoformat") else value


def planted(fixture_db: Path, target: Path, statement: str) -> Path:
    shutil.copyfile(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        engine.run(statement)
    return target


def get(database: Path, path: str) -> dict:
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    async def go():
        app = create_app(engine_for=engine_for, today=lambda: dt.date(2026, 10, 23))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            return await client.get(path, headers=HEADERS)

    response = asyncio.run(go())
    assert response.status_code == 200, response.text
    return response.json()


def bands(timeline: dict) -> list[dict]:
    return [item for item in timeline["items"] if item["kind"] == "band"]


@pytest.fixture(scope="module")
def assertions_stop_early(fixture_db, tmp_path_factory):
    return planted(fixture_db, tmp_path_factory.mktemp("series") / "assertions.duckdb", NO_ASSERTION)


@pytest.fixture(scope="module")
def table_stops_early(fixture_db, tmp_path_factory):
    return planted(fixture_db, tmp_path_factory.mktemp("series") / "table.duckdb", NOT_IN_TABLE)


def test_where_the_assertions_stop_before_the_ratings_table_the_page_reads_the_table_to_the_last_rated_isr(
        assertions_stop_early):
    timeline = get(assertions_stop_early, f"/api/projects/P130164/timeline?{DAY}")
    ratings, last = timeline["ratings"], bands(timeline)[-1]

    # The band row reaches ISR 13, the last ISR that rated progress, and its last band is the rating the title names.
    assert [(band["first"], band["last"]) for band in bands(timeline)] == [(1, 9), (10, 11), (12, 13)]
    assert (last["rating"], last["end"]) == (truth("isr-13-rating"), truth("isr-13-date"))
    assert (ratings["last_rating"], ratings["last_sequence"]) == (last["rating"], last["last"]) == (
        truth("isr-13-rating"), 13)
    assert ratings["source"] == "strata.silver.isr_ratings"
    first = truth("isr-1-rating")
    assert text_of(timeline["finding"]) == (
        f"Two pairs of reports disagree, and ISR ratings of progress fell from {first} to {truth('isr-13-rating')}, "
        "last rated in ISR 13.")


def test_a_band_drawn_from_the_ratings_table_opens_its_run_of_isrs_in_the_drawer(assertions_stop_early):
    timeline = get(assertions_stop_early, f"/api/projects/P130164/timeline?{DAY}")
    last = bands(timeline)[-1]

    row = get(assertions_stop_early, f"/api/evidence?id={last['evidence_id']}&{DAY}")["row"]
    assert [(entry["sequence"], entry["date"], entry["rating"]) for entry in row["rows"]] == [
        (12, truth("isr-12-date"), truth("isr-12-rating")), (13, truth("isr-13-date"), truth("isr-13-rating"))]
    assert (row["rating"], row["first"], row["last"], row["count"]) == (last["rating"], 12, 13, 2)


def test_where_the_ratings_table_stops_before_the_assertions_the_page_reads_the_assertions(table_stops_early):
    timeline = get(table_stops_early, f"/api/projects/P130164/timeline?{DAY}")
    ratings, last = timeline["ratings"], bands(timeline)[-1]

    assert ratings["source"] == "strata.gold.assertion"
    assert [(band["first"], band["last"]) for band in bands(timeline)] == [(1, 9), (10, 11), (12, 13)]
    assert (ratings["last_rating"], ratings["last_sequence"]) == (last["rating"], last["last"]) == (
        truth("isr-13-rating"), 13)
    assert text_of(timeline["finding"]).endswith(f"to {truth('isr-13-rating')}, last rated in ISR 13.")
