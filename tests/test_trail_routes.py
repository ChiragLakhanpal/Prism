"""The contract trail, the Connections tab and "Why this source" (ticket 22) at seam 3: the routes the activity
page, a project's Connections tab and the evidence drawer ask for, as the viewer and as of the page's ?asof=.

The values below come from tests/ground_truth/values.toml, where each one names its recorded record or document
page, never from the code under test.
"""

import asyncio
import datetime as dt
import json
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.config import load_thresholds
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-Preferred-Username": "Ana Example",
       "X-Forwarded-User": "4021@1984", "X-Forwarded-Access-Token": "token-for-ana-only"}
DAY = "asof=2026-10-23"
KENYA = "KE-NWWDA-229129-CW-RFB"
SHOWCASE = "IN-RRSMP-7431-CW-RFB"
ICR_54 = "strata.gold.passage:31525018/v1/54"


def get(app, path):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path, headers=ANA)
    return asyncio.run(go())


@pytest.fixture(scope="module")
def app(fixture_db):
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for)


def stage(trail, name):
    return next(found for found in trail["stages"] if found["stage"] == name)


# ── The activity page's trail ────────────────────────────────────────────

def test_the_trail_of_ke_nwwda_229129_shows_the_plan_row_notice_bids_and_contract_each_with_a_source(app):
    trail = get(app, f"/api/projects/P156634/packages/{KENYA}?{DAY}").json()

    plan = stage(trail, "plan")["records"][0]
    assert plan["estimated_amount_usd"] == f"{VALUES['plan-229129-estimated']['value']:.2f}"
    assert plan["evidence_id"].startswith("strata.silver.plan_rows:") and plan["source"]["plan_date"]
    [notice] = stage(trail, "notice")["records"]
    assert (notice["notice_id"], notice["notice_date"]) == ("OP00146683", VALUES["notice-229129-invitation"]["value"].isoformat())
    [award] = stage(trail, "bids")["records"]
    truth = TRUTH["award_notice_bids"]["kenya"]
    assert (award["notice_id"], award["notice_date"]) == (truth["notice"], VALUES["award-notice-229129-published"]["value"].isoformat())
    assert [(bid["name"], bid["price_at_opening"], bid["evaluated_price"] or "") for bid in award["bids"]] == [
        (bid["name"], bid["opening"], bid["evaluated"]) for bid in truth["bids"]]
    assert [bid["outcome"] for bid in award["bids"]] == ["awarded"] + ["not_awarded"] * 7 + ["rejected"] * 3
    assert {bid["reason"] for bid in award["bids"] if bid["outcome"] == "rejected"} == {"Non Responsive"}
    assert award["currency"] == truth["currency"]
    [contract] = stage(trail, "contract")["records"]
    assert contract["signed_on"] == VALUES["award-229129-signed"]["value"].isoformat()
    assert (contract["amount"], contract["currency"]) == (f"{VALUES['award-229129-amount']['value']:.2f}", "USD")
    assert contract["from_notice"] is False
    for record in (plan, notice, award, contract):
        assert record["evidence_id"] and record["public_from"] and record["source"]


def test_the_lead_names_what_the_records_hold_in_procurement_order(app):
    trail = get(app, f"/api/projects/P156634/packages/{KENYA}?{DAY}").json()

    assert [part["kind"] for part in trail["lead"]["parts"]] == ["estimated", "advertised", "signed"]
    assert trail["lead"]["bids"]["count"] == len(TRUTH["award_notice_bids"]["kenya"]["bids"])
    assert trail["lead"]["missing"] is None


def test_no_supplier_score_rank_or_profile_is_on_the_trail(app):
    text = get(app, f"/api/projects/P156634/packages/{KENYA}?{DAY}").text.lower()

    assert not any(word in text for word in ('"score', '"rank', "profile", "supplier_id", "step_supplier_id"))


def test_an_individual_consultant_is_never_named_on_the_trail(app):
    case = VALUES["notice-individual-consultant"]  # KE-MAWASCO-501974-CS-INDV, award notice OP00410598
    trail = get(app, f"/api/projects/P156634/packages/KE-MAWASCO-501974-CS-INDV?{DAY}").json()

    bids = stage(trail, "bids")
    assert (bids["found"], bids["reason"]) == (False, "individual_consultant")
    contract = stage(trail, "contract")["records"]
    assert all(record["supplier"]["name"] is None and record["supplier"]["is_individual_consultant"] for record in contract)
    assert case["notice"] not in json.dumps(bids)


def test_the_showcase_trail_states_its_missing_stages_and_its_contract_from_an_award_notice(app):
    trail = get(app, f"/api/projects/P130164/packages/{SHOWCASE}?{DAY}").json()

    assert (stage(trail, "plan")["found"], stage(trail, "plan")["reason"]) == (False, "not_read")
    assert (stage(trail, "notice")["found"], stage(trail, "notice")["reason"]) == (False, "none_found")
    [award] = stage(trail, "bids")["records"]
    assert [bid["name"] for bid in award["bids"]] == [bid["name"] for bid in TRUTH["award_notice_bids"]["showcase"]["bids"]]
    [contract] = stage(trail, "contract")["records"]
    assert (contract["from_notice"], contract["record_noun"]) == (True, "award notice")
    assert (contract["signed_on"], contract["currency"]) == (VALUES["award-7431-signed"]["value"].isoformat(), "INR")
    together = stage(trail, "paragraphs")
    assert together["joined_on"] == "together"
    assert ICR_54 in [record["evidence_id"] for record in together["records"]]
    dates = [record["document_date"] for record in together["records"]]
    assert dates == sorted(dates)  # oldest first


def test_as_of_a_date_before_the_contract_was_signed_its_contract_and_its_links_are_not_returned(app):
    day_before = VALUES["award-229129-signed"]["value"] - dt.timedelta(days=1)
    trail = get(app, f"/api/projects/P156634/packages/{KENYA}?asof={day_before}").json()

    assert (stage(trail, "contract")["found"], stage(trail, "contract")["reason"]) == (False, "after_asof")
    assert (stage(trail, "paragraphs")["found"], stage(trail, "paragraphs")["reason"]) == (False, "after_asof")
    assert stage(trail, "paragraphs")["records"] == []
    assert "1686165" not in json.dumps(trail)


def test_an_activity_no_record_holds_is_not_found_and_one_under_another_project_names_its_own(app):
    unknown = get(app, f"/api/projects/P156634/packages/KE-NWWDA-000000-CW-RFB?{DAY}")
    moved = get(app, f"/api/projects/P130164/packages/{KENYA}?{DAY}")

    assert (unknown.status_code, unknown.json()["code"]) == (404, "unknown_activity")
    assert (moved.status_code, moved.json()["activity"]["project_id"]) == (200, "P156634")


# ── The drawer's records and "Why this source" ───────────────────────────

@pytest.mark.parametrize("evidence_id", ["strata.gold.notice:OP00146683", "strata.gold.notice:OP00164589",
                                         "strata.gold.contract:1686165", "strata.gold.contract:OP00044090"])
def test_each_record_on_the_trail_opens_in_the_drawer_from_its_evidence_id(app, evidence_id):
    found = get(app, f"/api/evidence?id={evidence_id}&{DAY}")

    assert found.status_code == 200
    assert found.json()["kind"] == "record" and found.json()["row"]["fields"]


def test_the_plan_row_on_the_trail_opens_in_the_drawer(app):
    trail = get(app, f"/api/projects/P156634/packages/{KENYA}?{DAY}").json()
    evidence_id = stage(trail, "plan")["records"][0]["evidence_id"]

    found = get(app, f"/api/evidence?id={evidence_id}&{DAY}").json()

    assert found["row"]["estimated_amount_usd"] == f"{VALUES['plan-229129-estimated']['value']:.2f}"


def test_why_this_source_explains_the_showcase_link_from_its_score_components(app):
    found = get(app, f"/api/evidence?id={ICR_54}&step_ref={SHOWCASE}&{DAY}").json()

    why = found["why"]
    assert (why["record_noun"], why["reference"], why["signed_on"]) == (
        "award notice", SHOWCASE, VALUES["award-7431-signed"]["value"].isoformat())
    # The topics in order: the category the paragraph mentions, then the project's sector (values.toml
    # project-p130164-sector-roads), which the screen words as "works contracts" and "roads".
    assert [(topic["kind"], topic["code"]) for topic in why["topics"]] == [("category", "Works"), ("sector", "TI")]
    assert VALUES["project-p130164-sector-roads"]["value"].endswith(why["topics"][1]["name"])
    assert why["project_state"] == "closed"
    assert (why["months"], why["direction"]) == (VALUES["icr-months-after-7431"]["value"], "after")
    assert why["document"]["date"] == VALUES["icr-date"]["value"].isoformat()
    assert [row["part"] for row in why["components"]] == ["project", "sector", "time", "text", "mentions"]
    assert why["threshold"] == f"{load_thresholds().value('links.threshold'):.2f}"
    assert why["activity_href"] == f"/projects/P130164/packages/{SHOWCASE}"
    mention = next(item for item in why["mentions"])
    assert VALUES["icr-para-54"]["quote"][mention["start"]:mention["end"]] == mention["text"]


def test_why_this_source_is_left_out_when_no_link_was_public_on_the_as_of_date(app):
    found = get(app, f"/api/evidence?id={ICR_54}&step_ref={SHOWCASE}&asof=2019-11-02").json()
    # ISR 10 of May 23, 2017 appeared together with the showcase contract, which became public on July 19, 2017
    # with its award notice (values.toml award-notice-7431-published): as of June 1, 2017 that link is not named.
    earlier = get(app, f"/api/evidence?id=strata.gold.passage:27490469/v1/s5&step_ref={SHOWCASE}&asof=2017-06-01").json()
    unlinked = get(app, f"/api/evidence?id=strata.gold.passage:31525018/v1/1&{DAY}").json()

    assert found["why"] is not None
    assert earlier["why"]["reference"] != SHOWCASE
    assert SHOWCASE not in json.dumps(earlier["why"])
    assert unlinked["why"] is None


# ── The Connections tab ─────────────────────────────────────────────────

def test_connections_shows_at_most_the_cap_of_nodes_and_counts_the_rest_by_kind(app):
    cap = load_thresholds().value("connections.max_nodes")
    found = get(app, f"/api/projects/P156634/connections?{DAY}").json()

    shown = 1 + len(found["packages"]) + len(found["documents"])
    assert shown <= cap and found["shown"] == shown
    assert found["total"] == shown + sum(more["count"] for more in found["more"])
    assert found["total"] > cap
    assert {more["kind"] for more in found["more"]} <= {"packages", "isrs", "plans", "documents"}


def test_connections_draws_each_dashed_line_from_a_shown_package_to_a_chip_on_a_shown_document(app):
    found = get(app, f"/api/projects/P130164/connections?{DAY}").json()

    packages = {package["step_reference"] for package in found["packages"]}
    chips = {chip["evidence_id"] for document in found["documents"] for chip in document["chips"]}
    assert SHOWCASE in packages
    assert found["edges"] and all(edge["step_reference"] in packages and edge["evidence_id"] in chips for edge in found["edges"])
    assert found["finding"]["contracts"] >= 1 and found["finding"]["paragraphs"] >= 1


def test_connections_as_of_a_date_returns_only_what_was_public_then(app):
    found = get(app, "/api/projects/P130164/connections?asof=2017-06-01").json()

    assert found["edges"] == []
    assert all(document["document_date"] <= "2017-06-01" for document in found["documents"])
