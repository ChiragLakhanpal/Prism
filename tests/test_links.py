"""Edges between strata (ticket 22), over the fixture (seam 1).

The gate builds data/out/fixture.duckdb with the nightly job's own tasks, and runs the relink task again once
the passage reader has read the documents, so these tests read what the run wrote: every bid an award notice
lists (strata.silver.notice_bids), the edge table (strata.gold.edge) with its keyed edges and the scored
"appeared together" edges between contracts and the paragraphs of their project's reports. Expected values
come from tests/ground_truth/values.toml, where each one names its recorded record or document page, never
from the code under test.
"""

import json
import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}


@pytest.fixture(scope="module")
def fixture(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql, **params):
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


# ── Every bid an award notice lists ──────────────────────────────────────

@pytest.mark.parametrize("case", ["kenya", "showcase"])
def test_an_award_notice_lists_every_bid_in_its_order_with_its_prices_and_reason_as_written(fixture, case):
    truth = TRUTH["award_notice_bids"][case]

    found = rows(fixture, "SELECT bid, section, name, step_supplier_id, currency, price_at_opening, evaluated_price, "
                          "reason FROM strata.silver.notice_bids WHERE notice_id = :notice_id ORDER BY bid, member",
                 notice_id=truth["notice"])

    assert [(b["bid"], b["section"], b["name"], b["step_supplier_id"] or "", b["price_at_opening"],
             b["evaluated_price"] or "", b["reason"] or "") for b in found] == [
        (place, bid["section"], bid["name"], bid["id"], bid["opening"], bid["evaluated"], bid["reason"])
        for place, bid in enumerate(truth["bids"], 1)]
    assert {b["currency"] for b in found} == {truth["currency"]}


def test_a_joint_venture_is_one_bid_whose_members_share_its_prices(fixture):
    venture = TRUTH["awkward"]["joint_venture"]  # award notice OP00125855 lists both members, then one price

    found = rows(fixture, "SELECT bid, member, step_supplier_id, price_at_opening FROM strata.silver.notice_bids "
                          "WHERE notice_id = :notice_id AND section = 'awarded' ORDER BY member",
                 notice_id=venture["notice"])

    assert [(b["bid"], b["member"], b["step_supplier_id"]) for b in found] == [
        (1, 1, venture["supplier_ids"][0]), (1, 2, venture["supplier_ids"][1])]
    assert len({b["price_at_opening"] for b in found}) == 1


def test_a_consultant_award_notice_keeps_no_score_and_says_it_lists_scores(fixture):
    # Award notice OP00192301 gives each firm's technical, financial and combined scores and its rank. None is
    # kept; the notice is marked as one that lists scores, so the screen says it leaves them out.
    found = rows(fixture, "SELECT * FROM strata.silver.notice_bids WHERE notice_id = 'OP00192301' ORDER BY bid, member")

    assert found and all(b["notice_lists_scores"] for b in found)
    kept = [column for column in found[0] if column != "notice_lists_scores"]
    assert not any("score" in column or "rank" in column for column in kept)
    assert not any("93.86" in str(value) or "Rank" in str(value) for bid in found for value in bid.values())


def test_an_individual_consultant_in_an_award_notice_is_never_named_in_its_bids(fixture):
    case = VALUES["notice-individual-consultant"]

    found = rows(fixture, "SELECT name, individual_consultant FROM strata.silver.notice_bids WHERE notice_id = :notice_id",
                 notice_id=case["notice"])

    assert found == [{"name": None, "individual_consultant": True}]


# ── The edge table ───────────────────────────────────────────────────────

# IN-RRSMP-7431-CW-RFB's contract comes from its award notice, OP00044090 (values.toml award-7431-signed),
# because the contract awards datasets skip fiscal 2017 to 2019; gold keys such a contract by the notice's id.
NOTICE_7431 = VALUES["award-7431-signed"]["at"].split("id=")[1].split("]")[0]
CONTRACT_7431 = f"strata.gold.contract:{NOTICE_7431}"
ICR_54 = "strata.gold.passage:31525018/v1/54"  # values.toml icr-para-54: the ICR, document 31525018, paragraph 54


def edges(engine, **where):
    clause = " AND ".join(f"{column} = :{column}" for column in where)
    return rows(engine, f"SELECT * FROM strata.gold.edge WHERE {clause} ORDER BY kind, from_id, to_id", **where)


def test_an_edge_links_contract_7431_to_icr_paragraph_54_with_its_score_components(fixture):
    from strata.config import load_thresholds

    threshold = load_thresholds().value("links.threshold")

    [edge] = edges(fixture, from_id=CONTRACT_7431, to_id=ICR_54)

    assert edge["kind"] == "appeared_together"
    assert edge["project_id"] == VALUES["icr-para-54"]["project"]
    # Each component is the points it scored, and the total is theirs, kept at two decimals.
    parts = [edge[f"score_{part}"] for part in ("project", "sector", "time", "text", "mentions")]
    assert all(part is not None and part >= 0 for part in parts)
    assert edge["score"] == sum(parts) and edge["score"] >= threshold
    # What matched: the ICR came 28 months after the signing; the paragraph mentions works contracts; and the
    # project's largest sector is TI, Rural and Inter-Urban Roads.
    assert (edge["months_apart"], edge["time_direction"]) == (VALUES["icr-months-after-7431"]["value"], "after")
    assert edge["sector_code"] == "TI"
    assert VALUES["project-p130164-sector-roads"]["value"].endswith(edge["sector_name"])
    assert {(m["kind"], m["code"], m["text"]) for m in json.loads(edge["mentions"])} == {("category", "Works", "works contract")}
    # An edge is public once both its ends are: the ICR became public after the award notice did.
    assert edge["public_from"] == VALUES["icr-disclosed"]["value"]


def test_the_mention_an_edge_names_is_where_it_says_in_the_paragraph(fixture):
    [edge] = edges(fixture, from_id=CONTRACT_7431, to_id=ICR_54)
    text = VALUES["icr-para-54"]["quote"]

    for mention in json.loads(edge["mentions"]):
        assert text[mention["start"]:mention["end"]] == mention["text"]


def test_keyed_edges_join_the_showcase_contract_to_its_supplier_package_project_and_documents(fixture):
    supplier = rows(fixture, "SELECT supplier_id FROM strata.gold.contract WHERE contract_id = :notice",
                    notice=NOTICE_7431)[0]["supplier_id"]
    found = {(e["kind"], e["from_id"], e["to_id"]) for e in rows(
        fixture, "SELECT kind, from_id, to_id FROM strata.gold.edge WHERE kind <> 'appeared_together' AND ("
                 "from_id IN (:contract, :project, :package, :icr) OR to_id = :contract)",
        contract=CONTRACT_7431, project="strata.gold.project:P130164",
        package="strata.gold.package:IN-RRSMP-7431-CW-RFB", icr="strata.silver.documents:31525018")}

    assert {("borrows", "strata.gold.project:P130164", "strata.gold.country:IN"),
            ("plans", "strata.gold.project:P130164", "strata.gold.package:IN-RRSMP-7431-CW-RFB"),
            ("awarded_as", "strata.gold.package:IN-RRSMP-7431-CW-RFB", CONTRACT_7431),
            ("has", "strata.gold.project:P130164", CONTRACT_7431),
            ("signed_by", CONTRACT_7431, f"strata.gold.supplier:{supplier}"),
            ("described_in", "strata.gold.project:P130164", "strata.silver.documents:31525018"),
            ("has", "strata.silver.documents:31525018", ICR_54)} <= found


def test_every_edge_is_public_no_earlier_than_either_of_its_ends(fixture):
    # A contract's edges: public from its own public date at the earliest, so as of a day before it was signed
    # none of them is returned (KE-NWWDA-229129-CW-RFB's contract 1686165 was signed January 3, 2022).
    early = rows(fixture, "SELECT count(*) AS n FROM strata.gold.edge WHERE (from_id = :contract OR to_id = :contract) "
                          "AND public_from < :signed", contract="strata.gold.contract:1686165",
                 signed=VALUES["award-229129-signed"]["value"])
    every = rows(fixture, "SELECT count(*) AS n FROM strata.gold.edge e JOIN strata.gold.passage p "
                          "ON e.to_id = concat('strata.gold.passage:', p.passage_id) "
                          "WHERE e.kind = 'appeared_together' AND e.public_from < p.public_from")

    assert early == [{"n": 0}] and every == [{"n": 0}]


def test_a_contract_is_linked_only_to_paragraphs_of_its_own_projects_reports(fixture):
    found = rows(fixture, "SELECT count(*) AS n FROM strata.gold.edge e JOIN strata.gold.contract c "
                          "ON e.from_id = concat('strata.gold.contract:', c.contract_id) JOIN strata.gold.passage p "
                          "ON e.to_id = concat('strata.gold.passage:', p.passage_id) "
                          "WHERE e.kind = 'appeared_together' AND (p.project_id <> c.project_id OR p.doc_key IS NULL "
                          "OR p.kind <> 'paragraph')")

    assert found == [{"n": 0}]
