"""The review list and the labeling tool for supplier name matching (ticket 19), through the HTTP routes.

- GET /api/suppliers/review lists each candidate pair that waits for a person, with both names,
  countries and contracts, read as the viewer.
- POST /api/suppliers/review records a person's decision, merge or no merge, with the reviewer (the
  viewer the Databricks App forwarded) and the reason, as the app's own service principal (a DuckDB
  copy of the fixture here). The next run of resolution applies it.
- GET /api/suppliers/labels gives the next candidate pairs to label, without where Strata sent them,
  and how many are labeled; POST /api/suppliers/labels records a label.

Expected names come from tests/ground_truth/values.toml, where each names its recorded record.
"""

import asyncio
import shutil
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app
from strata.server.suppliers import SupplierLog

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
       "X-Forwarded-Access-Token": "token-for-ana-only"}


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


@pytest.fixture
def database(fixture_db, tmp_path):
    """A writable copy of the fixture database: the viewer reads it, and the app writes to it."""
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    return target


def app_on(path):
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(path) as engine:
            yield engine
    return create_app(engine_for=engine_for, supplier_log=SupplierLog(lambda: DuckDBEngine.open(path)))


def query(path, sql, **params):
    with DuckDBEngine.open(path, read_only=True) as engine:
        result = engine.run(sql, params)
        return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


LOSAI_ROW, LOSAI_AWARD = VALUES["notice-losai-no-id"], VALUES["award-losai-477806"]
LOSAI_PAIR = f"{LOSAI_ROW['notice']}/2|{LOSAI_AWARD['value']}"  # the notice's second awarded firm, and 477806


def test_the_review_list_shows_each_waiting_pair_with_both_names_countries_and_contracts(database):
    response = call(app_on(database), "GET", "/api/suppliers/review", ANA)

    assert response.status_code == 200
    listed = {pair["pair_id"]: pair for pair in response.json()["pairs"]}
    losai = listed[LOSAI_PAIR]
    assert (losai["left"]["name"], losai["left"]["country"], losai["left"]["contracts"]) == (
        LOSAI_ROW["value"], "Kenya", ["KE-MOWI-30792-CS-QCBS"])
    assert (losai["right"]["name"], losai["right"]["country"]) == (LOSAI_AWARD["name"], "Kenya")
    assert "KE-WAJWASCO-154020-CS-QCBS" in losai["right"]["contracts"]
    assert losai["review_reason"] == "two_step_supplier_ids"
    waiting = query(database, "SELECT pair_id FROM strata.ops.supplier_pairs WHERE outcome = 'waiting'")
    assert set(listed) == {row["pair_id"] for row in waiting} and response.json()["count"] == len(waiting)
    assert all(pair["left"]["name"] and pair["right"]["name"] for pair in listed.values())


def test_a_decision_writes_merge_with_the_reviewer_and_the_reason_and_the_next_run_applies_it(database):
    from strata.knowledge.suppliers import resolve
    from strata.knowledge.suppliers.judge import SameNameStandIn

    reason = "Award notice OP00138234 writes LOSAI MANAGEMENT LTD. with 477806 for a contract of the same project."
    response = call(app_on(database), "POST", "/api/suppliers/review", ANA,
                    json={"pair_id": LOSAI_PAIR, "decision": "merge", "reason": reason})

    assert response.status_code == 200 and response.json() == {"recorded": True}
    assert query(database, "SELECT decision, reviewer, reason, left_name, right_name "
                           "FROM strata.ops.supplier_review_decisions") == [
        {"decision": "merge", "reviewer": "4021@1984", "reason": reason, "left_name": LOSAI_ROW["value"],
         "right_name": LOSAI_AWARD["name"]}]
    with DuckDBEngine.open(database) as engine:
        resolve.run(engine, "after-the-decision", SameNameStandIn())
    assert query(database, "SELECT supplier_id, resolved_on FROM strata.silver.supplier_resolution "
                           "WHERE source_key = :notice AND name = :name", notice=LOSAI_ROW["notice"],
                 name=LOSAI_ROW["value"]) == [{"supplier_id": LOSAI_AWARD["value"], "resolved_on": "name"}]
    assert query(database, "SELECT outcome, decided_by, reviewer FROM strata.ops.supplier_pairs WHERE pair_id = :pair",
                 pair=LOSAI_PAIR) == [{"outcome": "merge", "decided_by": "person", "reviewer": "4021@1984"}]
    listed = call(app_on(database), "GET", "/api/suppliers/review", ANA).json()["pairs"]
    assert LOSAI_PAIR not in {pair["pair_id"] for pair in listed}


@pytest.mark.parametrize(("headers", "body", "status", "code"), [
    ({}, {"decision": "merge", "reason": "Same firm."}, 401, "no_identity"),
    (ANA, {"decision": "merge", "reason": "   "}, 422, None),
    (ANA, {"decision": "approve", "reason": "Same firm."}, 422, None),
    (ANA, {"decision": "no_merge", "reason": "Same firm.", "pair_id": "OP00000000/1|503708"}, 404, "unknown_pair"),
])
def test_a_decision_needs_a_signed_in_viewer_a_reason_merge_or_no_merge_and_a_pair_the_latest_run_found(
        database, headers, body, status, code):
    response = call(app_on(database), "POST", "/api/suppliers/review", headers, json={"pair_id": LOSAI_PAIR, **body})

    assert response.status_code == status
    if code:
        assert response.json()["code"] == code
    assert query(database, "SELECT count(*) AS n FROM strata.ops.supplier_review_decisions") == [{"n": 0}]


def test_the_labeling_tool_gives_unlabeled_pairs_without_strata_s_decision_and_records_a_label(database):
    app = app_on(database)
    found = query(database, "SELECT count(*) AS n FROM strata.ops.supplier_pairs")[0]["n"]

    first = call(app, "GET", "/api/suppliers/labels", ANA, params={"limit": 5}).json()
    recorded = call(app, "POST", "/api/suppliers/labels", ANA, json={"pair_id": first["pairs"][0]["pair_id"],
                                                                     "label": "merge"})
    after = call(app, "GET", "/api/suppliers/labels", ANA, params={"limit": 5}).json()

    assert (len(first["pairs"]), first["labeled_pairs"], first["candidate_pairs"], first["labeled_pairs_target"]) == (
        5, 0, found, 1000)
    assert set(first["pairs"][0]) == {"pair_id", "left", "right"}
    assert recorded.status_code == 200 and after["labeled_pairs"] == 1
    assert first["pairs"][0]["pair_id"] not in {pair["pair_id"] for pair in after["pairs"]}
    assert query(database, "SELECT label, labeler FROM strata.ops.supplier_pair_labels") == [
        {"label": "merge", "labeler": "4021@1984"}]
