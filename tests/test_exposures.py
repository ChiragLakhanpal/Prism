"""The exposure log (ticket 44) at seam 3: showing a past range or a time estimate for a package with a STEP
reference, through the answer contract's routes, writes one row in strata.ops.exposures with the range shown, the
option chosen and the dates offered. A preview, an abstention and a package with no STEP reference write nothing.

The app reads the fixture database as the viewer and writes the log to a DuckDB file of its own, as it writes
strata.ops as its own service principal on the App. Every expected date comes from tests/ground_truth/values.toml
or from the route's own answer, never typed in.
"""

import asyncio
import datetime as dt
import json
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from scripted_answers import ask
from strata import appstate
from strata.estimates.exposures import ExposureLog, stated
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.packages.store import PackageStore
from strata.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
TODAY = dt.date(2026, 10, 23)
SHOWN_AT = dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC)
SIGNED_2022 = "KE-NWWDA-229129-CW-RFB"
DEMO = "KE-NWWDA-541055-CW-RFB"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


def ops_table(path: Path, *names: str) -> None:
    """A DuckDB file holding only these strata.ops tables, as the catalog defines them."""
    with DuckDBEngine.open(path) as engine:
        engine.run("CREATE SCHEMA IF NOT EXISTS strata.ops")
        for definition in catalog.table_definitions():
            if definition.schema == "ops" and definition.table in names:
                engine.run(definition.sql)


def logged(path: Path) -> list[dict]:
    with DuckDBEngine.open(path, read_only=True) as engine:
        result = engine.run("SELECT * FROM strata.ops.exposures ORDER BY shown_at, exposure_id")
    return [dict(zip(result.columns, row)) for row in result.rows]


@pytest.fixture
def served(fixture_db, tmp_path):
    """The app, with its package store and its exposure log, and the file the log writes to."""
    state, log = tmp_path / "state.duckdb", tmp_path / "ops.duckdb"
    with DuckDBEngine.open(state) as engine:
        appstate.build(engine)
    ops_table(log, "exposures")

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=reading, packages=PackageStore(lambda: DuckDBEngine.open(state)),
                     exposures=ExposureLog(lambda: DuckDBEngine.open(log), now=lambda: SHOWN_AT),
                     today=lambda: TODAY, now=lambda: SHOWN_AT)
    return app, log


def test_showing_a_time_estimate_writes_one_exposure_with_the_range_shown_and_the_option_chosen(served):
    app, log = served

    answered = call(app, "GET", f"/api/packages/{SIGNED_2022}/estimate", ANA)

    assert answered.status_code == 200
    estimate = answered.json()["estimate"]
    [row] = logged(log)
    assert (row["step_reference"], row["shown"], row["view"], row["viewer_id"]) == (
        SIGNED_2022, "time_estimate", "staff", "4021@1984")
    assert (row["project_id"], row["country_code"]) == (VALUES["plan-229129-signed"]["project"], "KE")
    assert json.loads(row["range_shown"]) == {key: estimate[key] for key in ("q25", "q50", "q75", "q80", "days")}
    assert (row["model"], row["model_version"]) == (estimate["model"], estimate["model_version"])
    # No choice saved: the cautious 8-in-10 date is the option chosen (the 26 design brief, section 6.3).
    assert (row["option_chosen"], row["option_saved"]) == ("eight_in_ten", False)
    # The package was advertised by then, so the offered dates count from its Invitation for Bids.
    assert (row["start_date"], row["start_from"]) == (VALUES["notice-229129-invitation"]["value"], "first_notice")
    assert row["offered_middle_on"] == row["start_date"] + dt.timedelta(days=estimate["days"]["q50"])
    assert row["offered_eight_in_ten_on"] == row["start_date"] + dt.timedelta(days=estimate["days"]["q80"])
    assert (row["shown_at"].replace(tzinfo=dt.UTC), row["exposed_on"], row["public_from"]) == (SHOWN_AT, TODAY, TODAY)
    assert row["as_of"] == TODAY and row["route"] == "/api/packages/{step_reference}/estimate"


def test_showing_a_past_range_writes_one_exposure_with_the_saved_choice(served):
    app, log = served
    saved = call(app, "PUT", f"/api/packages/{SIGNED_2022}/plan-dates", ANA, json={"choice": "middle"})

    answered = call(app, "GET", f"/api/packages/{SIGNED_2022}/comparables", ANA)

    assert saved.status_code == 200 and answered.status_code == 200
    past_range = answered.json()["past_range"]
    [row] = logged(log)
    assert (row["shown"], row["route"], row["model"]) == ("past_range", "/api/packages/{step_reference}/comparables", None)
    assert json.loads(row["range_shown"]) == {key: past_range[key] for key in ("q25", "q50", "q75", "q80", "days")}
    assert (row["option_chosen"], row["option_saved"]) == ("middle", True)
    assert row["offered_eight_in_ten_on"] == row["start_date"] + dt.timedelta(days=past_range["days"]["q80"])


def test_a_preview_an_abstention_and_a_package_with_no_step_reference_write_no_exposure(served):
    app, log = served

    preview = call(app, "GET", f"/api/packages/{SIGNED_2022}/estimate?view=piu", ANA)
    public = call(app, "GET", f"/api/packages/{SIGNED_2022}/comparables?view=public", ANA)
    # Under 20 comparable packages, the tools give no range (tests/test_estimate_routes.py names this count).
    too_few = call(app, "GET", f"/api/packages/{DEMO}/estimate?review_type=Prior", ANA)
    too_few_range = call(app, "GET", f"/api/packages/{DEMO}/comparables?review_type=Prior", ANA)
    no_step_row = call(app, "GET", "/api/comparables?method=Request%20for%20Bids&category=works&country=KE", ANA)

    assert preview.status_code == public.status_code == too_few.status_code == 200
    assert preview.json()["estimate"] is not None and public.json()["past_range"] is not None
    assert too_few.json()["abstention"]["reason"] == too_few_range.json()["abstention"]["reason"] == "too_few_comparables"
    assert no_step_row.status_code == 200 and no_step_row.json()["past_range"] is not None
    assert logged(log) == []


ASKED = "ke-nwwda-541055-past-range"  # the recorded answer that states the demo package's past range


def test_an_answer_that_states_a_past_range_writes_one_exposure_with_the_range_it_cited(fixture_db, tmp_path):
    log = tmp_path / "ops.duckdb"
    ops_table(log, "exposures")

    asked = ask(fixture_db, ASKED, exposures=ExposureLog(lambda: DuckDBEngine.open(log), now=lambda: SHOWN_AT))

    [cited] = [event for event in asked.of("evidence") if event["tool"] == "find_comparables"
               and "past_range" in event["row"]]
    assert any(cited["id"] in sentence["evidence_ids"] for sentence in asked.of("sentence"))
    [row] = logged(log)
    assert (row["step_reference"], row["shown"], row["route"], row["view"], row["viewer_id"]) == (
        DEMO, "past_range", "/api/ask", "staff", "4021@1984")
    assert json.loads(row["range_shown"]) == cited["row"]["past_range"]
    assert row["as_of"] == asked.case.as_of
    # No choice saved: the cautious 8-in-10 date is the option chosen (the 26 design brief, section 6.3).
    assert (row["option_chosen"], row["option_saved"]) == ("eight_in_ten", False)
    assert row["offered_eight_in_ten_on"] == row["start_date"] + dt.timedelta(days=cited["row"]["past_range"]["days"]["q80"])


def test_the_same_answer_in_a_preview_writes_no_exposure(fixture_db, tmp_path):
    log = tmp_path / "ops.duckdb"
    ops_table(log, "exposures")

    asked = ask(fixture_db, ASKED, view="piu",
                exposures=ExposureLog(lambda: DuckDBEngine.open(log), now=lambda: SHOWN_AT))

    assert asked.of("sentence") and logged(log) == []


def test_an_answer_states_a_time_estimate_once_per_package_and_only_when_a_kept_sentence_cites_it():
    estimate = {"q25": 4.0, "q50": 5.0, "q75": 6.0, "q80": 7.0, "days": {"q25": 120, "q50": 150, "q75": 180, "q80": 210}}
    facts = {"estimate-a": {"estimate": estimate}, "range-b": {"past_range": estimate}}
    calls = [{"tool": "estimate_time", "arguments": {"step_reference": DEMO}, "summary_id": "estimate-a"},
             {"tool": "estimate_time", "arguments": {"step_reference": DEMO}, "summary_id": "estimate-a"},
             {"tool": "find_comparables", "arguments": {"step_reference": DEMO}, "summary_id": "range-b"},
             {"tool": "estimate_time", "arguments": {"country": "KE"}, "summary_id": "estimate-c"}]

    found = stated(["estimate-a", "estimate-c", "strata.gold.package:KE-ICTA-571738-CW-RFB"], calls, facts.get)

    assert found == [("estimate_time", DEMO, {"abstention": None, "estimate": estimate})]
