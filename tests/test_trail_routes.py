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
    assert [bids["count"] for bids in trail["lead"]["bids"]] == [len(TRUTH["award_notice_bids"]["kenya"]["bids"])]
    assert trail["lead"]["missing"] is None


def test_with_two_award_notices_the_lead_counts_the_bids_of_each(app, fixture_db):
    # KE-KIMAWASCO-372408-GO-RFQ has two award notices, one for each of its two contracts, so the lead counts
    # each notice's bids, not only the first's (design review F4), and each award record says its count.
    reference = "KE-KIMAWASCO-372408-GO-RFQ"
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run("SELECT n.notice_id, count(DISTINCT b.bid) FROM strata.gold.notice n JOIN strata.silver.notice_bids b "
                            "ON b.notice_id = n.notice_id WHERE n.step_reference = :reference GROUP BY n.notice_id, "
                            "n.notice_date ORDER BY n.notice_date, n.notice_id", {"reference": reference})
    expected = [(notice_id, n) for notice_id, n in result.rows]

    trail = get(app, f"/api/projects/P156634/packages/{reference}?{DAY}").json()

    assert len(expected) == 2
    assert [(bids["notice_id"], bids["count"]) for bids in trail["lead"]["bids"]] == expected
    assert [(record["notice_id"], record["bid_count"]) for record in stage(trail, "bids")["records"]] == expected
    assert len(stage(trail, "contract")["records"]) == 2 and trail["lead"]["many_contracts"] is True


def test_a_joint_venture_contract_names_its_members_as_the_bids_do(app, fixture_db):
    # Contract 1624689 went to two firms together (values.toml [awkward.joint_venture]); the contract card reads
    # "A joint venture of A and B", as the bids table does, so the tool gives the members (design review F26).
    venture = TRUTH["awkward"]["joint_venture"]
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run("SELECT name FROM strata.gold.supplier WHERE supplier_id IN (:a, :b)",
                            {"a": venture["supplier_ids"][0], "b": venture["supplier_ids"][1]})
    names = {name for (name,) in result.rows}

    trail = get(app, f"/api/projects/P156634/packages/KE-KIMAWASCO-158691-CW-RFB?{DAY}").json()

    [contract] = [record for record in stage(trail, "contract")["records"] if record["contract_id"] == venture["contract"]]
    assert contract["supplier"]["is_joint_venture"] and set(contract["supplier"]["members"]) == names


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


def test_the_activity_is_named_by_its_notice_and_only_by_records_public_on_the_as_of_date(app):
    # The plan reader split words in the newer plans' cells ("Explor atory"), so the notice's description, which
    # STEP typed, names the activity (the 22 critique, Copy). As of June 1, 2017, before IN-RRSMP-7431-CW-RFB's
    # award notice was published (values.toml award-notice-7431-published), no public record names it (ADR 0002).
    kenya = get(app, f"/api/projects/P156634/packages/{KENYA}?{DAY}").json()
    early = get(app, f"/api/projects/P130164/packages/{SHOWCASE}?asof=2017-06-01").json()

    assert kenya["activity"]["description"] == VALUES["notice-229129-description"]["value"]
    assert VALUES["award-notice-7431-published"]["value"] > dt.date(2017, 6, 1)
    assert (early["activity"]["description"], early["activity"]["method"]) == (None, None)


def test_a_limited_market_approach_never_lists_the_notice_as_missing(app):
    # KE-NWWDA-503455-CW-RFQ is a Request for Quotations with a Limited - National market approach (values.toml's
    # [[plan_row]]), which invites firms directly, so no public notice is missing (design review F3). The same
    # list in config/thresholds.toml tells the past range which packages have no notice.
    row = next(row for row in TRUTH["plan_row"] if row["reference"] == "KE-NWWDA-503455-CW-RFQ")
    trail = get(app, f"/api/projects/P156634/packages/{row['reference']}?{DAY}").json()

    notice = stage(trail, "notice")
    assert (notice["found"], notice["reason"], notice["market_approach"]) == (False, "approach_no_notice", row["market_approach"])
    assert trail["lead"]["missing"] in (None, "contract")


def paragraphs_by_document(engine, reference):
    """Each report's paragraphs that appeared together with the activity's contracts, by the report, from the edge
    table: a paragraph read as parts (27348420/v1/annex3.62/1 and /4) is one paragraph."""
    result = engine.run(
        "SELECT p.document_id, p.document_date, p.passage_id FROM strata.gold.edge e JOIN strata.gold.contract c "
        "ON e.from_id = concat('strata.gold.contract:', c.contract_id) JOIN strata.gold.passage p "
        "ON e.to_id = concat('strata.gold.passage:', p.passage_id) WHERE e.kind = 'appeared_together' "
        "AND c.step_reference = :reference AND e.public_from <= :as_of AND p.public_from <= :as_of "
        "AND (p.replaced_on IS NULL OR p.replaced_on > :as_of)", {"reference": reference, "as_of": dt.date(2026, 10, 23)})
    paragraphs: dict[tuple, set] = {}
    for document_id, dated, passage_id in result.rows:
        part = passage_id.split("/")
        paragraphs.setdefault((dated, document_id), set()).add(tuple(part[:3]))
    return [(document_id, len(keys)) for (_, document_id), keys in sorted(paragraphs.items())]


@pytest.mark.parametrize("reference, pid", [(KENYA, "P156634"), (SHOWCASE, "P130164")])
def test_the_paragraphs_come_one_card_a_paragraph_grouped_by_report_oldest_first(app, fixture_db, reference, pid):
    # Every report is on the page with its first few paragraphs, so the ICR's group shows on the showcase without
    # opening the rest (the 22 critique, Activity page, Hierarchy); a paragraph's parts are one card.
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        expected = paragraphs_by_document(engine, reference)
    shown = load_thresholds().value("contract_trail.paragraphs_per_report")

    together = stage(get(app, f"/api/projects/{pid}/packages/{reference}?{DAY}").json(), "paragraphs")

    assert [(group["document_id"], group["count"]) for group in together["groups"]] == expected
    assert [group["shown"] for group in together["groups"]] == [min(n, shown) for _, n in expected]
    assert [record["document_id"] for record in together["records"]] == [
        document_id for document_id, n in expected for _ in range(n)]
    keys = ["/".join(record["passage_id"].split("/")[:3]) for record in together["records"]]
    assert len(keys) == len(set(keys))
    # Two cards of one report that share a paragraph number, as a PAD's annexes restart theirs, name their section.
    for group in together["groups"]:
        mine = [record for record in together["records"] if record["document_id"] == group["document_id"]]
        titles = [(record["paragraph"], record["title_section"]) for record in mine if record["paragraph_numbered"]]
        assert len(titles) == len(set(titles))


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

    found = get(app, f"/api/evidence?id={evidence_id}&step_ref={KENYA}&{DAY}").json()

    fields = {field["key"]: field for field in found["row"]["fields"]}
    assert float(fields["estimated_amount_usd"]["value"]) == VALUES["plan-229129-estimated"]["value"]
    assert found["row"]["activity_href"] == f"/projects/P156634/packages/{KENYA}"
    # Opened from the activity page, no field backs a claim, so none is highlighted (ticket 28 highlights the
    # Process Status when a row says a package was canceled).
    assert not any(field.get("highlight") for field in fields.values())


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


def test_why_this_source_lists_each_other_package_once(app, fixture_db):
    # P156634's ISR of March 12, 2026 appeared together with contracts of many packages, some holding several
    # contracts (three of KE-TAVEVO-370761-GO-RFB), so each package is listed once (the 22 review, item 14).
    passage = "strata.gold.passage:40091292/v1/s4"
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run(
            "SELECT count(DISTINCT coalesce(c.step_reference, c.contract_id)) FROM strata.gold.edge e "
            "JOIN strata.gold.contract c ON e.from_id = concat('strata.gold.contract:', c.contract_id) "
            "WHERE e.kind = 'appeared_together' AND e.to_id = :passage AND e.public_from <= :as_of",
            {"passage": passage, "as_of": dt.date(2026, 10, 23)})
    packages = result.rows[0][0]

    why = get(app, f"/api/evidence?id={passage}&{DAY}").json()["why"]

    references = [other["reference"] for other in why["others"]]
    assert len(references) == len(set(references)) and why["reference"] not in references
    assert why["others_count"] == packages - 1
    assert why["others_more"] == why["others_count"] - len(references)


# ── The Connections tab ─────────────────────────────────────────────────

def test_connections_shows_at_most_the_cap_of_nodes_and_counts_the_rest_by_kind(app):
    cap = load_thresholds().value("connections.max_nodes")
    found = get(app, f"/api/projects/P156634/connections?{DAY}").json()

    # The count line counts packages and documents, so neither number holds the project (design review F6).
    shown = len(found["packages"]) + len(found["documents"])
    assert shown + 1 <= cap and found["shown"] == shown
    assert found["total"] == shown + sum(more["count"] for more in found["more"])
    assert found["total"] > cap
    assert {more["kind"] for more in found["more"]} <= {"packages", "isrs", "plans", "documents"}


def test_connections_says_how_many_of_the_documents_it_leaves_out_it_has_not_read(app):
    # P127203's tab shows two nodes with room for 17 more, so every document it leaves out is one I haven't read
    # and can't open in the app (the 22 critique, Connections, States).
    found = get(app, f"/api/projects/P127203/connections?{DAY}").json()
    listed = get(app, f"/api/projects/P127203/documents?{DAY}").json()
    unread = sum(1 for group in listed["groups"] for entry in group["documents"] if not entry["read"])

    assert found["shown"] + 1 < load_thresholds().value("connections.max_nodes")
    documents = [more for more in found["more"] if more["kind"] != "packages"]
    assert documents and all(more["unread"] == more["count"] for more in documents)
    assert sum(more["unread"] for more in documents) == unread


def test_connections_draws_each_dashed_line_from_a_shown_package_to_a_chip_on_a_shown_document(app):
    found = get(app, f"/api/projects/P130164/connections?{DAY}").json()

    packages = {package["step_reference"] for package in found["packages"]}
    chips = {chip["evidence_id"] for document in found["documents"] for chip in document["chips"]}
    assert SHOWCASE in packages
    assert found["edges"] and all(edge["step_reference"] in packages and edge["evidence_id"] in chips for edge in found["edges"])
    assert found["finding"]["contracts"] >= 1 and found["finding"]["paragraphs"] >= 1


def test_the_connections_finding_counts_every_linked_contract_by_its_own_id(app, fixture_db):
    # A package can hold several contracts, and a contract can have no STEP reference; the finding counts
    # contracts, so it counts each linked contract once, whatever its package (the 22 review, B1).
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run(
            "SELECT e.from_id, p.passage_id, p.document_id FROM strata.gold.edge e JOIN strata.gold.passage p "
            "ON e.to_id = concat('strata.gold.passage:', p.passage_id) WHERE e.kind = 'appeared_together' "
            "AND e.project_id = :pid AND e.public_from <= :as_of AND p.public_from <= :as_of "
            "AND (p.replaced_on IS NULL OR p.replaced_on > :as_of)", {"pid": "P156634", "as_of": dt.date(2026, 10, 23)})
    contracts = {row[0] for row in result.rows}
    # A paragraph read as parts counts once, as its chip and its card show it once.
    paragraphs = {tuple(row[1].split("/")[:3]) for row in result.rows}
    documents = {row[2] for row in result.rows}

    finding = get(app, f"/api/projects/P156634/connections?{DAY}").json()["finding"]

    assert finding["contracts"] == len(contracts) == len(finding["contract_items"])
    assert finding["paragraphs"] == len(paragraphs) == len(finding["paragraph_items"])
    assert finding["documents"] == len(documents)


def test_a_paragraph_split_into_parts_is_one_chip_and_no_two_chips_on_a_document_read_alike(app):
    # P156634's ISR of March 8, 2024 split its Results section into parts 34277278/v1/s6/1 to /3, and its PAD has
    # a paragraph 27 in section II.A and again in Annexes 2, 3 and 5 (the 22 review, item 7; design review F17).
    found = get(app, f"/api/projects/P156634/connections?{DAY}").json()

    for document in found["documents"]:
        paragraphs = ["/".join(chip["passage_id"].split("/")[:3]) for chip in document["chips"]]
        assert len(paragraphs) == len(set(paragraphs)), document["document_id"]
        labels = [(chip["paragraph"] if chip["paragraph_numbered"] else chip["section_path"], json.dumps(chip["label_extra"]))
                  for chip in document["chips"]]
        assert len(labels) == len(set(labels)), document["document_id"]
        assert all(chip["package_count"] == len(chip["packages"]) for chip in document["chips"])


@pytest.mark.parametrize("pid", ["P130164", "P156634"])
def test_connections_draws_one_line_for_each_package_and_document_that_appeared_together(app, fixture_db, pid):
    # One curve per pair, not one per chip, so the gutter does not fill with crossing lines; past a set number,
    # only the first linked package's curves show until a package is pointed at (design review F7).
    found = get(app, f"/api/projects/{pid}/connections?{DAY}").json()
    packages = [package["step_reference"] for package in found["packages"]]
    documents = {document["document_id"] for document in found["documents"]}
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run(
            "SELECT DISTINCT c.step_reference, p.document_id FROM strata.gold.edge e JOIN strata.gold.contract c "
            "ON e.from_id = concat('strata.gold.contract:', c.contract_id) JOIN strata.gold.passage p "
            "ON e.to_id = concat('strata.gold.passage:', p.passage_id) WHERE e.kind = 'appeared_together' "
            "AND e.project_id = :pid AND e.public_from <= :as_of AND p.public_from <= :as_of "
            "AND (p.replaced_on IS NULL OR p.replaced_on > :as_of)", {"pid": pid, "as_of": dt.date(2026, 10, 23)})
    expected = {(ref, doc) for ref, doc in result.rows if ref in packages and doc in documents}

    lines = found["lines"]
    assert {(line["step_reference"], line["document_id"]) for line in lines} == expected
    assert len(lines) == len(expected)
    most = load_thresholds().value("connections.lines_at_rest")
    if len(lines) > most:
        first = next(ref for ref in packages if any(line["step_reference"] == ref for line in lines))
        assert {line["step_reference"] for line in lines if line["at_rest"]} == {first}
        assert found["lines_hint"] is True
    else:
        assert all(line["at_rest"] for line in lines) and found["lines_hint"] is False


def test_connections_as_of_a_date_returns_only_what_was_public_then(app):
    found = get(app, "/api/projects/P130164/connections?asof=2017-06-01").json()

    assert found["edges"] == []
    assert all(document["document_date"] <= "2017-06-01" for document in found["documents"])
