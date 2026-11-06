"""A project's timeline and the disagreement card (ticket 23) at seam 3: GET /api/projects/{pid}/timeline, the
drawer's new evidence ids (doc:, ratings:, contracts: and disagreement:), and keeping the other report
(POST and GET /api/disagreements/{id}/choices), as the viewer and as of the page's ?asof=.

The dates, ratings and references below are tests/ground_truth/values.toml's, read from it by id, never worked
out the way the route works them out.
"""

import asyncio
import datetime as dt
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from warehouse_over_fixture import WarehouseOverFixture

from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

TRUTH = {value["id"]: value for value in
         tomllib.loads((Path(__file__).parent / "ground_truth" / "values.toml").read_text())["value"]}
ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}
DAY = "asof=2026-10-23"


def truth(key):
    value = TRUTH[key]["value"]
    return value.isoformat() if hasattr(value, "isoformat") else value


def call(app, method, path, headers=ANA, body=None):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers, json=body)
    return asyncio.run(go())


def get(app, path, headers=ANA):
    return call(app, "GET", path, headers)


def app_on(database, **more):
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for, **more)


@pytest.fixture(scope="module")
def server(fixture_db):
    import datetime as dt

    return app_on(fixture_db, today=lambda: dt.date(2026, 10, 23))


@pytest.fixture(scope="module")
def p130164(server):
    response = get(server, f"/api/projects/P130164/timeline?{DAY}")
    assert response.status_code == 200, response.text
    return response.json()


def placed(timeline, **match):
    """The items on the timeline whose fields have these values."""
    return [item for item in timeline["items"] if all(item.get(key) == value for key, value in match.items())]


def one(timeline, **match):
    found = placed(timeline, **match)
    assert len(found) == 1, (match, found)
    return found[0]


# ── Where each item sits ─────────────────────────────────────────────────

def test_p130164_s_timeline_places_each_report_event_and_record_at_its_date_in_its_lane(p130164):
    assert one(p130164, kind="report", type="pad")["date"] == truth("pad-date")
    assert one(p130164, kind="event", type="mid_term_review")["date"] == truth("mid-term-review")
    assert one(p130164, kind="report", type="isr", sequence=7)["date"] == truth("isr-7-date")
    assert one(p130164, kind="record", step_reference=truth("award-7431-reference"))["date"] == truth("award-7431-signed")
    assert one(p130164, kind="event", type="restructuring")["date"] == truth("restructuring")
    assert one(p130164, kind="report", type="isr", sequence=12)["date"] == truth("isr-12-date")
    assert one(p130164, kind="report", type="icr")["date"] == truth("icr-date")
    reviews = placed(p130164, kind="report", type="icr_review")
    assert [item["date"] for item in reviews] == [truth("icr-review-date"), truth("icr-review-reissue-date")]
    assert {item["lane"] for item in placed(p130164, kind="report", type="isr")} == {"how"}
    assert {one(p130164, kind="report", type=kind)["lane"] for kind in ("pad", "icr")} == {"why"}
    assert one(p130164, kind="record")["lane"] == "what"
    assert {one(p130164, kind="event", type=kind)["lane"] for kind in ("mid_term_review", "restructuring")} == {"how"}


def test_the_isr_series_shows_as_rating_bands_that_name_each_run_s_rating_never_as_a_disagreement(p130164):
    bands = placed(p130164, kind="band")
    assert [(band["first"], band["last"]) for band in bands] == [(1, 9), (10, 11), (12, 13)]
    for band in bands:
        # Each run's first and last ISR rated progress as the band says, word for word.
        assert band["rating"] == truth(f"isr-{band['first']}-rating") == truth(f"isr-{band['last']}-rating")
        assert band["date"] == truth(f"isr-{band['first']}-date")
    # A run ends where the next begins, and the last at its last ISR.
    assert [band["end"] for band in bands] == [truth("isr-10-date"), truth("isr-12-date"), truth("isr-13-date")]
    # No disagreement has two ISRs for its sides: ratings of successive periods are a trajectory.
    for found in placed(p130164, kind="disagreement"):
        assert [side["type"] for side in found["sides"]].count("isr") < 2
    assert p130164["ratings"]["first_rating"] == truth("isr-1-rating")
    assert p130164["ratings"]["last_rating"] == truth("isr-13-rating")
    # The title's last rating is the last band's, and the band row ends at the ISR the title names (ticket 142).
    assert (p130164["ratings"]["last_rating"], p130164["ratings"]["last_sequence"]) == (bands[-1]["rating"], 13)
    assert bands[-1]["last"] == 13 and bands[-1]["end"] == p130164["ratings"]["last_date"] == truth("isr-13-date")
    # Both sources hold ISRs 1 to 13 here, so the page keeps the assertions get_disagreements gives.
    assert p130164["ratings"]["source"] == "strata.gold.assertion"


def test_a_dashed_line_joins_isr_7_and_the_icr_in_the_order_written_and_strata_leans_on_the_icr(p130164):
    isr_7 = one(p130164, kind="report", type="isr", sequence=7)
    icr = one(p130164, kind="report", type="icr")
    found = next(item for item in placed(p130164, kind="disagreement")
                 if [side["item_id"] for side in item["sides"]] == [isr_7["id"], icr["id"]])
    assert [side["made_at"] for side in found["sides"]] == [truth("isr-7-date"), truth("icr-date")]
    assert [side["leaned"] for side in found["sides"]] == [False, True]
    assert found["sides"][1]["paragraph"] == str(TRUTH["icr-para-78"]["paragraph"])
    # The line opens its disagreement in the drawer, and comes right after its later side in arrow-key order.
    assert found["evidence_id"].startswith("disagreement:")
    order = [item["id"] for item in p130164["items"]]
    assert order.index(found["id"]) == order.index(icr["id"]) + 1
    assert isr_7["rating"] == truth("isr-7-rating")
    assert one(p130164, kind="report", type="isr", sequence=12)["rating"] == truth("isr-12-rating")


def test_the_arrow_keys_go_in_date_order_with_ties_why_how_what_and_marks_before_bands(p130164):
    kinds = [(item["kind"], item.get("type")) for item in p130164["items"]]
    assert kinds == [("report", "pad"), ("band", None), ("event", "mid_term_review"), ("report", "isr"),
                     ("record", "contract"), ("band", None), ("event", "restructuring"), ("report", "isr"),
                     ("band", None), ("report", "icr"), ("disagreement", None), ("report", "icr_review"),
                     ("report", "icr_review"), ("disagreement", None)]
    # Each disagreement is a group of one pair here, so the table lists the same items in the same order.
    assert [item["id"] for item in p130164["table"]] == [item["id"] for item in p130164["items"]]


# ── One line per fact (ticket 136) ───────────────────────────────────────

@pytest.fixture(scope="module")
def grouped(fixture_db, tmp_path_factory):
    """P130164's timeline on the planted copy (tests/planted_groups.py): 16 pairs about three facts."""
    from planted_groups import plant

    database = plant(fixture_db, tmp_path_factory.mktemp("groups") / "planted.duckdb")
    response = get(app_on(database, today=lambda: dt.date(2026, 10, 23)), f"/api/projects/P130164/timeline?{DAY}")
    assert response.status_code == 200, response.text
    return response.json()


def test_the_chart_draws_one_line_per_group_and_the_table_lists_every_pair(grouped):
    """Ticket 136, criterion 2: three facts told 16 times are three dashed lines, and the table keeps all 16."""
    lines = placed(grouped, kind="disagreement")
    assert sorted((line["attribute"], line["group"]["count"]) for line in lines) == [
        ("efficiency", 1), ("overall_risk", 4), ("pdo_progress", 11)]
    assert len([item for item in grouped["table"] if item["kind"] == "disagreement"]) == 16
    assert grouped["disagreements"] == {"status": "ok", "count": 3, "pairs": 16}
    # Every pair in the table opens its own disagreement, and every pair belongs to one line.
    pairs = {item["disagreement_id"] for item in grouped["table"] if item["kind"] == "disagreement"}
    assert sorted(pairs) == sorted(one for line in lines for one in line["group"]["disagreement_ids"])


def test_a_line_joins_the_one_report_to_the_nearest_of_the_reports_that_disagree_with_it(grouped):
    """The PAD against ISRs 8 to 11 on overall risk is drawn from the PAD to ISR 8, and ISRs 1 to 11 against the ICR
    on progress towards the PDO from ISR 11 to the ICR, so the pill names the one report and counts the others."""
    risk = one(grouped, kind="disagreement", attribute="overall_risk")
    assert [(side["type"], side["sequence"]) for side in risk["sides"]] == [("pad", None), ("isr", 8)]
    assert risk["group"]["anchor_item_id"] == one(grouped, kind="report", type="pad")["id"]
    assert (risk["group"]["anchor_reports"], risk["group"]["other_reports"], risk["group"]["reports"]) == (
        [{"type": "pad", "count": 1, "sequence": None}], [{"type": "isr", "count": 4, "sequence": None}], 5)
    assert risk["group"]["lean"] == "others"  # the moment rule leans on each ISR, rated at its own moment
    progress = one(grouped, kind="disagreement", attribute="pdo_progress")
    assert [(side["type"], side["sequence"]) for side in progress["sides"]] == [("isr", 11), ("icr", None)]
    assert (progress["group"]["anchor_reports"], progress["group"]["other_reports"], progress["group"]["lean"]) == (
        [{"type": "icr", "count": 1, "sequence": None}], [{"type": "isr", "count": 11, "sequence": None}], "anchor")
    efficiency = one(grouped, kind="disagreement", attribute="efficiency")
    assert efficiency["group"]["other_reports"] == [{"type": "icr_review", "count": 1, "sequence": None}]


def test_the_finding_counts_the_points_the_reports_disagree_on_and_the_alt_text_names_each_line(grouped):
    from strata.server.timeline import text_of

    first, last = truth("isr-1-rating"), truth("isr-13-rating")
    assert text_of(grouped["finding"]) == (
        f"Reports disagree on three points, and ISR ratings of progress fell from {first} to {last}, "
        "last rated in ISR 13.")
    assert {"number": 3} in grouped["finding"]
    alt = text_of(grouped["alt"])
    assert "A dashed line marks where the PAD and four ISRs disagree." in alt
    assert "A dashed line marks where the ICR and 11 ISRs disagree." in alt
    assert "A dashed line joins the ICR and the ICR Review, which disagree." in alt


def test_only_the_reports_at_the_ends_of_a_line_get_their_own_isr_mark(grouped):
    """ISRs 8 and 11 end a line, and ISR 12's rating changed side; the other ISRs of the two groups show in the band
    row and in the table's pairs, so the How lane does not fill with circles."""
    assert [item["sequence"] for item in placed(grouped, kind="report", type="isr")] == [8, 11, 12]
    pad = one(grouped, kind="report", type="pad")
    assert pad["disagrees_with"] == [one(grouped, kind="disagreement", attribute="overall_risk")["id"]]


def test_an_isr_gets_its_own_mark_only_as_a_side_of_a_disagreement_or_where_its_rating_changed_side(p130164):
    # ISR 7 is a side of the disagreement with the ICR; ISR 12 rated progress Moderately Unsatisfactory after ISR 11's
    # Moderately Satisfactory. The other eleven ISRs show only in the band row (a decision parked for the owner).
    assert [item["sequence"] for item in placed(p130164, kind="report", type="isr")] == [7, 12]
    assert (truth("isr-11-rating"), truth("isr-12-rating")) == ("Moderately Satisfactory", "Moderately Unsatisfactory")


def test_the_icr_review_re_issued_under_the_same_number_replaces_its_first_version(p130164):
    first, reissue = placed(p130164, kind="report", type="icr_review")
    assert first["report_number"] == reissue["report_number"] == truth("icr-review-number-2023")
    assert first["replaced_by"] == {"evidence_id": reissue["evidence_id"], "date": truth("icr-review-reissue-date")}
    assert (first["reissued"], reissue["reissued"], reissue["replaced_by"]) == (False, True, None)


def test_the_finding_and_the_alt_text_are_written_from_the_tool_s_values(p130164):
    from strata.server.timeline import text_of

    first, last = truth("isr-1-rating"), truth("isr-13-rating")
    assert text_of(p130164["finding"]) == (
        f"Two pairs of reports disagree, and ISR ratings of progress fell from {first} to {last}, last rated in ISR 13.")
    # The count is a number the page writes through Num.
    assert {"number": 2, "capital": True} in p130164["finding"]
    assert text_of(p130164["alt"]) == (
        "Timeline of P130164 from 2013 to 2023 in three lanes: four evaluations, four operations items and one record. "
        f"ISR ratings of progress went from {first} to {last} over 13 ISRs. "
        "A dashed line joins ISR 7 and the ICR, which disagree. A dashed line joins the ICR and the ICR Review, which disagree. "
        "It shows what was public on October 23, 2026.")
    assert p130164["rejected"] == {"count": 1}
    # Two lines, each a group of one pair (ticket 136).
    assert p130164["disagreements"] == {"status": "ok", "count": 2, "pairs": 2}
    # The dashed line's state when no open answer depends on it, from config/project_page.toml's [timeline].
    assert p130164["disagreement_line_state"] == "info"


def test_as_of_august_26_2016_the_timeline_shows_only_what_was_public_then(server):
    body = get(server, "/api/projects/P130164/timeline?asof=2016-08-26").json()

    assert body["asked_as_of"] == "2016-08-26"
    assert all(item["public_from"] <= "2016-08-26" for item in body["items"])
    assert placed(body, kind="report", type="icr") == [] and placed(body, kind="disagreement") == []
    # ISR 7 was dated and disclosed that day, and it dates the mid-term review in its key dates.
    assert one(body, kind="report", type="isr", sequence=7)["date"] == truth("isr-7-date")
    assert one(body, kind="event", type="mid_term_review")["date"] == truth("mid-term-review")
    # The restructuring is dated only by the ICR, public in 2019.
    assert placed(body, kind="event", type="restructuring") == []
    assert [(band["first"], band["last"]) for band in placed(body, kind="band")] == [(1, 7)]
    # The chart's name says which date it shows, since the drawn "As of" label is inside the image (round 2).
    from strata.server.timeline import text_of

    assert {"date": truth("isr-7-date")} in body["alt"]
    assert text_of(body["alt"]).endswith(" It shows what was public on August 26, 2016.")


def test_an_as_of_date_after_today_is_read_and_named_as_today(server):
    # The route reads the data as of today, so the date it names is today's too, not the one asked for (code
    # review, round 3, follow-up 3). Today is the server's clock, October 23, 2026.
    from strata.server.timeline import text_of

    body = get(server, "/api/projects/P130164/timeline?asof=2030-01-01").json()

    assert (body["as_of"], body["asked_as_of"]) == ("2026-10-23", "2026-10-23")
    assert text_of(body["alt"]).endswith(" It shows what was public on October 23, 2026.")


def test_when_get_disagreements_fails_the_newest_isr_keeps_its_mark_and_no_sentence_says_strata_has_no_ratings(
        server, monkeypatch):
    from strata.server import timeline
    from strata.server.timeline import text_of

    monkeypatch.setattr(timeline.registry, "call", RECORDER.failing_get_disagreements(timeline.registry.call))
    body = get(server, f"/api/projects/P130164/timeline?{DAY}").json()

    assert body["disagreements"]["status"] == "failed"
    assert placed(body, kind="band") == [] and placed(body, kind="disagreement") == []
    # The ISRs Prism read still have a report to open: the newest, named by its own sequence number.
    (isr,) = placed(body, kind="report", type="isr")
    assert (isr["sequence"], isr["date"], isr["rating"]) == (13, truth("isr-13-date"), None)
    # No sentence says Prism has no ratings: it could not read them.
    alt = text_of(body["alt"])
    assert "I have no ISR ratings" not in alt
    assert "I couldn't read this project's ISR ratings just now." in alt


def test_the_public_view_of_a_project_still_under_way_shows_no_disagreement(server):
    body = get(server, f"/api/projects/P156634/timeline?{DAY}&view=public").json()

    assert body["project"]["status"] == "Active"
    assert body["disagreements"]["status"] == "hidden"
    assert placed(body, kind="disagreement") == []
    assert body["records_disagree"] == []
    assert body["records_disagree_count"] == 0
    assert not any("disagree" in segment.get("text", "") for segment in body["finding"] + body["alt"])


def test_the_plan_check_and_the_timeline_name_the_same_disagreement_about_ke_nwwda_541055(server):
    """Ticket 132, criterion 2: the plan check's row for KE-NWWDA-541055-CW-RFB is moved on since the plan, and the
    disagreement its reason cites is the one the Timeline tab lists where the records disagree: the plan of October
    9, 2026 still says Pending Implementation, and the contract awards say the contract was signed on June 22, 2026.
    One definition (CLAUDE.md rule 4): neither route works the finding out for itself."""
    check = get(server, f"/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09?{DAY}")
    timeline = get(server, f"/api/projects/P156634/timeline?{DAY}")
    assert check.status_code == timeline.status_code == 200

    [row] = [row for row in check.json()["rows"] if row["activity_reference_no"] == "KE-NWWDA-541055-CW-RFB"]
    [mark] = row["marks"]
    [reason] = mark["reasons"]
    assert (mark["mark"], reason["code"]) == ("moved_on", "moved_on_since_plan")
    listed = [found for found in timeline.json()["records_disagree"]
              if found["disagreement_id"] == reason["disagreement_id"]]
    assert len(listed) == 1
    # The route counts its list, so the tab writes "25 pairs of package records disagree." from the route's number.
    assert timeline.json()["records_disagree_count"] == len(timeline.json()["records_disagree"]) == 25
    [found] = listed
    assert found["step_reference"] == "KE-NWWDA-541055-CW-RFB"
    assert found["evidence_id"] == f"disagreement:{reason['disagreement_id']}"
    plan, award = sorted(found["sides"], key=lambda side: side["record"] != "plan")
    assert (plan["record"], plan["field_name"], plan["value"], plan["made_at"]) == (
        "plan", "Process Status", truth("plan-541055-status"), "2026-10-09")
    assert (award["record"], award["value"], award["evidence_id"]) == (
        "contract_awards", truth("award-541055-signed"), "strata.gold.contract:1903781")
    assert award["leaned"] and not plan["leaned"]
    # The drawer opens it from the list, as from any other link.
    assert get(server, f"/api/evidence?id={found['evidence_id']}&{DAY}").status_code == 200


def test_a_replaced_plans_moved_on_citation_still_opens_with_both_records(server):
    """Ticket 132's review round 1, B1: the agency's plan of October 9, 2026 replaced its plan of March 5, 2026, whose
    check still marks KE-NWWDA-541055-CW-RFB moved on since the plan. The disagreement that reason cites is no longer
    a current one, yet the drawer opens it as of the same date with both records: the March plan's Process Status and
    the contract award of June 22, 2026 (CLAUDE.md rule 2)."""
    check = get(server, f"/api/projects/P156634/procurement/northern-water-works-development-agency/2026-03-05?{DAY}")
    assert check.status_code == 200
    [row] = [row for row in check.json()["rows"] if row["activity_reference_no"] == "KE-NWWDA-541055-CW-RFB"]
    [reason] = [reason for mark in row["marks"] for reason in mark["reasons"] if reason["code"] == "moved_on_since_plan"]

    opened = get(server, f"/api/evidence?id=disagreement:{reason['disagreement_id']}&{DAY}")
    assert opened.status_code == 200
    body = opened.json()
    assert body["kind"] == "disagreement"
    sides = {side["form"]: side for side in body["row"]["sides"]}
    assert set(sides) == {"plan_row", "contract_record"}
    assert sides["plan_row"]["evidence_id"] == reason["evidence_ids"][0]  # the March plan's own row
    assert (sides["plan_row"]["value"], sides["contract_record"]["value"]) == (
        truth("plan-541055-status"), truth("award-541055-signed"))
    assert sides["contract_record"]["evidence_id"] == "strata.gold.contract:1903781"
    assert body["row"]["replaced_on"] == truth("plan-2026-10-09-disclosed")  # the day the October plan replaced it
    # The plan row and the record the reason cites open too (the disagreement's own id is the tool's, which the screen
    # opens as disagreement:{id}, above).
    for cited in reason["evidence_ids"]:
        if not cited.startswith("strata.gold.disagreement:"):
            assert get(server, f"/api/evidence?id={cited}&{DAY}").status_code == 200, cited


def test_the_public_view_of_a_project_still_under_way_shows_no_disagreement_from_a_drawer_link_either(server, fixture_db):
    import datetime as dt

    from strata.dbx import Viewer
    from strata.tools import registry

    # P156634 was under way on the page's date, and get_disagreements finds disagreements about its packages in the
    # staff view (ticket 40 judges "under way" as of the page's date with one rule, strata.tools.withheld). They sit on
    # no timeline mark, but a drawer link names them.
    from strata.server.timeline import DISAGREEMENT

    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        found = registry.call("get_disagreements", {"subject_id": "P156634"},
                              registry.Context(engine, Viewer(user_id="ana"), "staff", dt.date(2026, 10, 23)))
    link = f"{DISAGREEMENT}:{found['rows'][0]['disagreement_id']}"

    assert get(server, f"/api/evidence?id={link}&{DAY}&view=public").status_code == 404
    # World Bank staff still see it.
    assert get(server, f"/api/evidence?id={link}&{DAY}").status_code == 200


def test_a_crowded_what_lane_groups_contracts_by_year_and_the_table_keeps_every_contract(server):
    body = get(server, f"/api/projects/P156634/timeline?{DAY}").json()

    groups = placed(body, kind="group")
    records = [item for item in body["table"] if item["kind"] == "record"]
    assert len(records) > 12
    assert sum(group["count"] for group in groups) + len(placed(body, kind="record")) == len(records)
    assert all(group["evidence_id"] == f"contracts:P156634:{group['year']}" for group in groups)


def test_p156634_s_timeline_from_the_warehouse_s_text_is_the_timeline_the_fixture_gives(server, fixture_db):
    """Ticket 128: the workspace writes every value as text, a report's version as "1", and its page failed at
    `(row["version"] or 1) > 1` while the fixture's page answered. The same rows, written as the warehouse writes
    them with their manifest, go through WarehouseEngine and the route and give the same timeline."""
    warehouse = WarehouseOverFixture(fixture_db)
    app = create_app(engine_for=warehouse.engine_for, today=lambda: dt.date(2026, 10, 23))

    answered = get(app, f"/api/projects/P156634/timeline?{DAY}")

    assert answered.status_code == 200, answered.text
    versions = [value for kind, value in warehouse.values_written("version") if value is not None]
    assert versions and all(isinstance(value, str) for value in versions)
    assert {kind for kind, _ in warehouse.values_written("version")} == {"INT"}
    assert answered.json() == get(server, f"/api/projects/P156634/timeline?{DAY}").json()


def test_a_project_strata_has_no_record_of_gets_404(server):
    response = get(server, f"/api/projects/P999999/timeline?{DAY}")
    assert (response.status_code, response.json()) == (404, {"code": "unknown_project"})


# ── What each mark opens in the evidence drawer ──────────────────────────

def evidence(server, evidence_id, asof="2026-10-23"):
    return get(server, f"/api/evidence?id={evidence_id}&asof={asof}")


def test_each_mark_s_evidence_id_opens_from_a_link_on_any_page(server, p130164):
    for item in p130164["items"]:
        response = evidence(server, item["evidence_id"])
        assert response.status_code == 200, (item["id"], response.text)
        assert response.json()["id"] == item["evidence_id"]


def test_a_report_s_document_view_gives_its_dates_what_it_rated_and_the_disagreement_it_is_a_side_of(server, p130164):
    isr_7 = one(p130164, kind="report", type="isr", sequence=7)
    body = evidence(server, isr_7["evidence_id"]).json()

    assert (body["kind"], body["stratum"]) == ("document", "How")
    row = body["row"]
    assert (row["sequence"], row["document_date"], row["public_from"]) == (7, truth("isr-7-date"), truth("isr-7-date"))
    rated = {rating["field_name"]: rating for rating in row["ratings"]}
    assert rated["Progress towards achievement of PDO"]["value"] == truth("isr-7-rating")
    assert rated["Progress towards achievement of PDO"]["pdf_page"] == TRUTH["isr-7-rating"]["pdf_page"]
    assert [found["other"]["type"] for found in row["disagreements"]] == ["icr"]


def test_the_first_icr_review_s_document_view_names_the_re_issue_that_replaced_it(server, p130164):
    first, reissue = placed(p130164, kind="report", type="icr_review")
    row = evidence(server, first["evidence_id"]).json()["row"]

    assert row["replaced_by"]["date"] == truth("icr-review-reissue-date")
    assert row["replaced_by"]["evidence_id"] == reissue["evidence_id"]
    assert row["report_number"] == truth("icr-review-number-2020")
    # Before the re-issue was public, nothing had replaced it.
    assert evidence(server, first["evidence_id"], "2021-01-01").json()["row"]["replaced_by"] is None


def test_a_band_opens_its_run_of_isrs_and_a_disagreement_opens_both_sides(server, p130164):
    band = placed(p130164, kind="band")[0]
    row = evidence(server, band["evidence_id"]).json()["row"]
    assert [one_row["sequence"] for one_row in row["rows"]] == list(range(1, 10))
    assert {one_row["rating"] for one_row in row["rows"]} == {truth("isr-1-rating")}

    line = next(item for item in placed(p130164, kind="disagreement") if item["attribute"] == "pdo_progress")
    body = evidence(server, line["evidence_id"]).json()
    assert body["kind"] == "disagreement"
    sides = body["row"]["sides"]
    assert [side["made_at"] for side in sides] == [truth("isr-7-date"), truth("icr-date")]
    assert sides[1]["leaned"] and not sides[0]["leaned"]
    assert sides[1]["quote"] in TRUTH["icr-para-78"]["quote"]
    # The card shows the whole sentence of paragraph 78 that holds the quote, word for word.
    assert sides[1]["sentence"] == TRUTH["icr-para-78"]["quote"]
    # Before the ICR was public, the two reports did not disagree.
    assert evidence(server, line["evidence_id"], "2016-08-26").status_code == 404


def test_the_contract_mark_opens_its_signing_from_the_award_notice_that_alone_records_it(server, p130164):
    record = one(p130164, kind="record")
    body = evidence(server, record["evidence_id"]).json()

    assert body["kind"] == "record"
    fields = {field["key"]: field["value"] for field in body["row"]["fields"]}
    assert fields["contract_signed_on"] == truth("award-7431-signed")
    assert fields["award_notice_id"] == "OP00044090"


def test_a_year_of_contracts_opens_as_a_list(server):
    body = get(server, f"/api/projects/P156634/timeline?{DAY}").json()
    group = placed(body, kind="group")[0]
    row = evidence(server, group["evidence_id"]).json()["row"]

    assert row["count"] == group["count"] == len(row["rows"])
    assert all(entry["signed_on"].startswith(str(group["year"])) for entry in row["rows"])


def recorder():
    import importlib.util

    spec = importlib.util.spec_from_file_location("record_timeline_api", Path(__file__).parent / "record_timeline_api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECORDER = recorder()


@pytest.mark.parametrize("name", sorted(RECORDER.TIMELINE) + sorted(RECORDER.FAILED) + sorted(RECORDER.GROUPED))
def test_each_timeline_recording_is_what_the_server_answers_on_the_fixture(server, name, monkeypatch, tmp_path):
    import json

    from strata.server import timeline

    if name in RECORDER.FAILED:
        monkeypatch.setattr(timeline.registry, "call", RECORDER.failing_get_disagreements(timeline.registry.call))
    if name in RECORDER.GROUPED:
        server = app_on(RECORDER.planted(tmp_path), today=lambda: RECORDER.TODAY)
    recorded = json.loads((RECORDER.OUT / name).read_text())
    path = RECORDER.TIMELINE.get(name) or RECORDER.FAILED.get(name) or RECORDER.GROUPED[name]
    assert get(server, path).json() == recorded, (
        f"Check the change, then write the files again: uv run --frozen python tests/record_timeline_api.py ({name})")


# ── The disagreement in an answer ────────────────────────────────────────

def disagreement_events(case_id):
    import json

    from strata.agent.scripted import RECORDED_STREAMS

    recorded = (Path(__file__).parent / "fixtures" / "api" / RECORDED_STREAMS[case_id]).read_text()
    found = []
    for block in recorded.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line and not line.startswith(":"))
        if lines.get("event") == "disagreement":
            found.append(json.loads(lines["data"]))
    return found


def test_the_stream_names_the_sentences_a_disagreement_changes_so_the_card_takes_the_warning_state_only_then():
    # The answer that states ISR 7's rating rests on one side: keeping the ICR would change its sentence 0.
    (changes,) = disagreement_events("p130164-isr-7-rating")
    assert (changes["changes_answer"], changes["changes_sentence_ids"], changes["after"]) == (True, [0], 0)
    # The answer that already shows both sides changes nothing if you keep either.
    (shows_both,) = disagreement_events("p130164-both-sides")
    assert (shows_both["changes_answer"], shows_both["changes_sentence_ids"]) == (False, [])
    # The count the card says comes from the stream, not from the browser (CLAUDE.md rule 1).
    assert (changes["changes_count"], shows_both["changes_count"]) == (1, 0)
    # The event carries what keeping a side needs: the disagreement's own id and each side's assertion id.
    assert changes["disagreement_id"] == changes["id"].removeprefix("strata.gold.disagreement:")
    assert all(side["assertion_id"] for side in changes["sides"])
    # The answer's card shows the whole sentence of paragraph 78 that holds the ICR's quote, as the drawer's does.
    assert changes["sides"][1]["sentence"] == TRUTH["icr-para-78"]["quote"]


# ── Keeping the other report ─────────────────────────────────────────────

@pytest.fixture
def keeping(fixture_db, tmp_path):
    import datetime as dt

    from strata.lakehouse import catalog
    from strata.server.choices import ChoiceLog

    state = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state) as engine:
        catalog.build(engine)
    clock = iter(dt.datetime(2026, 10, 23, 15, minute, tzinfo=dt.UTC) for minute in range(60))
    log = ChoiceLog(lambda: DuckDBEngine.open(state), now=lambda: next(clock))
    return app_on(fixture_db, choices=log), state


def showcase(server_app):
    found = next(item for item in get(server_app, f"/api/projects/P130164/timeline?{DAY}").json()["items"]
                 if item["kind"] == "disagreement" and item["attribute"] == "pdo_progress")
    isr_7, icr = found["sides"]
    return found["disagreement_id"], isr_7["assertion_id"], icr["assertion_id"]


def test_keeping_isr_7_stores_the_reason_with_the_viewer_and_the_answer_in_strata_ops(keeping):
    app, state = keeping
    disagreement, isr_7, icr = showcase(app)

    response = call(app, "POST", f"/api/disagreements/{disagreement}/choices",
                    body={"kept_assertion_id": isr_7, "reason": "The mission saw the works on site.", "run_id": "run-0001"})

    assert response.status_code == 200, response.text
    assert response.json()["recorded"] is True
    with DuckDBEngine.open(state, read_only=True) as engine:
        rows = engine.run("SELECT viewer, disagreement_id, kept_assertion_id, leaned_assertion_id, reason, run_id, "
                          "draft_id, public_from FROM strata.ops.disagreement_choices").rows
    assert [tuple(row[:7]) for row in rows] == [
        ("4021@1984", disagreement, isr_7, icr, "The mission saw the works on site.", "run-0001", None)]
    latest = get(app, f"/api/disagreements/{disagreement}/choices?run_id=run-0001").json()["choice"]
    assert (latest["kept_assertion_id"], latest["kept_other"]) == (isr_7, True)


def test_going_back_to_strata_s_choice_adds_a_row_and_deletes_nothing(keeping):
    app, state = keeping
    disagreement, isr_7, icr = showcase(app)
    path = f"/api/disagreements/{disagreement}/choices"

    call(app, "POST", path, body={"kept_assertion_id": isr_7, "reason": "First reason.", "run_id": "run-0001"})
    back = call(app, "POST", path, body={"kept_assertion_id": icr, "run_id": "run-0001"})

    assert back.status_code == 200 and back.json()["choice"]["kept_other"] is False
    with DuckDBEngine.open(state, read_only=True) as engine:
        kept = engine.run("SELECT kept_assertion_id, reason FROM strata.ops.disagreement_choices ORDER BY made_at").rows
    assert [tuple(row) for row in kept] == [(isr_7, "First reason."), (icr, None)]
    assert get(app, f"{path}?run_id=run-0001").json()["choice"]["kept_assertion_id"] == icr
    # A new answer starts from Prism's choice.
    assert get(app, f"{path}?run_id=run-0002").json() == {"choice": None}


def test_keeping_the_other_report_needs_a_reason_a_side_of_the_disagreement_and_a_signed_in_viewer(keeping):
    app, state = keeping
    disagreement, isr_7, _ = showcase(app)
    path = f"/api/disagreements/{disagreement}/choices"

    assert call(app, "POST", path, body={"kept_assertion_id": isr_7, "reason": "  ", "run_id": "r"}).json() == {
        "code": "reason_required"}
    assert call(app, "POST", path, body={"kept_assertion_id": "not-a-side", "reason": "x", "run_id": "r"}).status_code == 422
    assert call(app, "POST", path, body={"kept_assertion_id": isr_7, "reason": "x"}).status_code == 422
    assert call(app, "POST", "/api/disagreements/0000/choices",
                body={"kept_assertion_id": isr_7, "reason": "x", "run_id": "r"}).status_code == 404
    assert call(app, "POST", path, headers={}, body={"kept_assertion_id": isr_7, "reason": "x", "run_id": "r"}).status_code == 401
    # A preview of another view records nothing.
    assert call(app, "POST", path, body={"kept_assertion_id": isr_7, "reason": "x", "run_id": "r", "view": "public"}).json() == {
        "recorded": False}
    with DuckDBEngine.open(state, read_only=True) as engine:
        assert engine.run("SELECT count(*) FROM strata.ops.disagreement_choices").rows[0][0] == 0
