"""A project's contracts, defined once (ticket 138) at seam 3: the Timeline tab and the Connections tab read the same
definition, so the two routes give every project the same count, and the Records lane names the contracts it leaves
out, with their source, instead of saying it has none.

The counts below come from tests/ground_truth/values.toml and the recorded files, never from the code under test.
"""

import asyncio
import datetime as dt
import json
import re
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app
from strata.server.timeline import text_of

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
RECORDED = ROOT / "data" / "fixture" / "recorded"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
DAY = "asof=2026-10-23"
KENYA = ("P156634", "P170941", "P176758")


def get(app, path):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=ANA)
    return asyncio.run(go())


@pytest.fixture(scope="module")
def server(fixture_db):
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for, today=lambda: dt.date(2026, 10, 23))


@pytest.fixture(scope="module")
def tabs(server, fixture_db):
    """Each fixture project with a contract, and one with none, as both tabs answer for it."""
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        found = engine.run("SELECT DISTINCT project_id FROM strata.gold.contract ORDER BY project_id", {})
    projects = [row[0] for row in found.rows] + ["P127203"]
    return {pid: (get(server, f"/api/projects/{pid}/timeline?{DAY}"), get(server, f"/api/projects/{pid}/connections?{DAY}"))
            for pid in projects}


def held(body):
    return body["contracts"]["count"], {source["source"]: source["count"] for source in body["contracts"]["sources"]}


def test_the_timeline_and_the_connections_tab_give_every_project_the_same_count_of_contracts(tabs):
    assert len(tabs) > 4
    for pid, (timeline, connections) in tabs.items():
        assert timeline.status_code == connections.status_code, pid
        if timeline.status_code == 200:
            assert held(timeline.json()) == held(connections.json()), pid


def test_p130164_holds_its_seven_older_awards_and_the_contract_its_award_notice_records(tabs):
    """values.toml's counts.p130164_trail: the seven rows of the FY2001 to FY2016 awards file and award notice
    OP00044090's contract, eight in all."""
    older = json.loads((RECORDED / "api" / "awards" / "P130164-fy2001-2016.json").read_text())["response"]["count"]
    timeline, connections = tabs["P130164"]
    assert held(timeline.json()) == (TRUTH["counts"]["p130164_trail"]["contracts"], {"awards_fy2001_2016": older,
                                                                                       "notices": 1})
    # Seven of them appeared together with a paragraph, and the finding names the eight it counts them among.
    assert connections.json()["finding"]["contracts"] == 7


def test_kenya_s_projects_hold_every_contract_of_the_awards_files(tabs):
    """values.toml's counts.kenya: 603 contracts in Kenya's two awards files."""
    awards = sum(held(tabs[pid][0].json())[1].get("awards", 0) for pid in KENYA)
    assert awards == TRUTH["counts"]["kenya"]["contracts"]


LEFT_OUT = ("The Records lane finds each contract's package by its STEP reference, so it leaves out seven from the "
            "contract awards for fiscal 2001 to 2016, which have none.")


def test_the_records_lane_names_the_source_of_the_contracts_it_leaves_out(tabs, server):
    """P130164's lane draws the one package its award notice signed, and names the seven older awards it leaves out
    (values.toml's counts.p130164_trail: their references were written before STEP)."""
    body = tabs["P130164"][0].json()
    assert [item["step_reference"] for item in body["table"] if item["kind"] == "record"] == ["IN-RRSMP-7431-CW-RFB"]
    assert text_of(body["records_note"]) == f"I hold eight contracts for this project. {LEFT_OUT}"

    # As of August 26, 2016 the award notice was not public yet, so the lane is empty, and the note says why.
    before = get(server, "/api/projects/P130164/timeline?asof=2016-08-26").json()
    assert [item for item in before["items"] if item["lane"] == "what"] == []
    assert text_of(before["records_note"]) == f"I hold seven contracts for this project. {LEFT_OUT}"

    # A project whose every contract has its package on the lane needs no note.
    assert tabs["P170941"][0].json()["records_note"] is None


def test_every_source_of_strata_gold_contract_has_a_name_the_note_can_write():
    """A source that gold/contract.sql adds needs its words in web/src/copy.ts, or the note could not name it."""
    sources = set(re.findall(r"'(\w+)' AS source", (ROOT / "src/strata/lakehouse/gold/contract.sql").read_text()))
    names = json.loads((ROOT / "src/strata/server/timeline_copy.json").read_text())["records"]["sources"]
    assert len(sources) == 3 and sources <= set(names)
