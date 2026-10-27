"""The risk-table builder (ticket 30): section 3 of the package workspace, procurement risks and what helped.

The builder is a workflow step, so the hindsight test (ticket 34) can run it headless with an as-of date. It
calls find_comparables for the package's comparable packages and get_lessons for the completion reports of
their projects, the risk factors those reports raised and the current lesson on what helped with each, then
runs the verifier on each row's two claims. The library holds a lesson only after two people decide it, so
these tests first have two reviewers decide the fixture's proposed lessons on a copy of the fixture database
(tests/lesson_scenario.py), as the review routes would.

The fixture's only completion reports are P130164's (values.toml icr-para-54 and icr-para-55), and Kenya's
comparable works packages under Request for Bids belong to projects still active (values.toml [comparables]).
So the rural roads package in Kenya reaches no completion report, and the paragraph 54 row is shown for a works
package under Request for Bids in India, whose comparables reach P130164's IN-RRSMP-7431-CW-RFB
(award-7431-reference). Expected values come from tests/ground_truth/values.toml.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

import lesson_scenario as scenario
from strata.config import Thresholds, load_thresholds
from strata.lakehouse.engine import DuckDBEngine
from strata.packages import risks

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
DECIDED = dt.date(2026, 10, 27)
AS_OF = dt.date(2026, 10, 28)
# A works package under Request for Bids in India, with notices from 2013: P130164's works package matches.
INDIA_WORKS = {"category": "Works", "method": "Request for Bids", "country": "IN", "notice_from": "2013-01-01"}
# The rural roads package's criteria as the package reader read them (tests/fixtures/agent/packages.toml).
RURAL_ROADS_KENYA = {"category": "Works", "method": "Request for Bids", "country": "KE"}


@pytest.fixture(scope="module")
def library(fixture_db, tmp_path_factory):
    """The rebidding lesson, the permits lesson and IEG's lesson, each added to the library by two people."""
    database = scenario.copy_of(fixture_db, tmp_path_factory.mktemp("risks-library"))
    for passage in (scenario.REBIDDING, scenario.PERMITS, scenario.IEG_LESSON):
        scenario.decide(database, passage, DECIDED)
    return database


def build(database, criteria, as_of=AS_OF, words="works roads market rates", **options):
    with DuckDBEngine.open(database, read_only=True) as engine:
        return risks.build(engine, scenario.ASHA, as_of=as_of, criteria=criteria, words=words, **options)


def row_of(table, label):
    return next(row for row in table.payload["rows"] if row["risk_label"] == label)


def test_the_cost_estimates_row_says_what_helped_and_cites_icr_paragraph_54_and_the_icr_review(library):
    table = build(library, INDIA_WORKS)

    row = row_of(table, "Cost estimates below market rates")
    assert row["lesson"]["text"] == "Base works estimates on market rates to avoid rebidding"
    assert [(source["doc_short"], source["pcode"], source["locator"], source["page"]) for source in row["sources"]] == [
        ("ICR", "P130164", {"kind": "paragraph", "text": "54"}, VALUES["icr-para-54"]["pdf_page"]),
        ("ICR Review", "P130164", {"kind": "section", "text": "10.b"},
         VALUES["icr-review-2023-restates-para-54"]["pdf_page"])]
    assert row["lesson"]["ieg_status"] == "restated"
    assert row["lesson"]["ieg_quote"]["text"] == VALUES["icr-review-2023-restates-para-54"]["quote"]


def test_each_count_is_taken_from_the_tool_and_names_its_denominator(library):
    """P130164 is the one project with a comparable package, and its ICR the one completion report, which
    raised the cost estimates risk (icr-para-54)."""
    table = build(library, INDIA_WORKS)
    payload = table.payload

    assert (payload["p"], payload["m"]) == (1, 1)
    assert row_of(table, "Cost estimates below market rates")["k"] == 1
    summary = table.facts.get(payload["counts_evidence_id"])
    assert summary["source"]["tool"] == "get_lessons"
    assert summary["reports"]["read"] == payload["m"]
    assert "share" not in str(payload) and "in10" not in str(payload)


def test_the_rows_pass_the_checks_and_the_check_line_counts_them(library):
    payload = build(library, INDIA_WORKS).payload

    assert payload["verifier"]["removed"] == []
    # Two rows, each with a count sentence ("came up in 1 of 1": two numbers) and a sentence on what helped.
    assert payload["verifier"]["counts"]["numbers"] == {"total": 4, "matched": 4}
    assert payload["verifier"]["counts"]["sentences"] == {"written": 4, "kept": 4, "removed": 0}
    assert payload["verifier"]["tools"] == ["find_comparables", "get_lessons"]
    # All six checks ran, as on an answer (ticket 61). Each sentence restates its records' own words, the risk's
    # name and the lesson's, so checks 1 to 3 prove it and no model is needed; those words are names and lessons
    # that match their records, not quotes from a page, which the screen's check line says.
    counts = payload["verifier"]["counts"]
    assert counts["checks_run"] == [1, 2, 3, 4, 5, 6]
    assert (counts["judge"]["called"], counts["shown"]["proven"]) == (False, 4)
    assert counts["quotes"] == {"total": 4, "found": 4}


class NothingFollows:
    """A judge for check 4 that finds no sentence follows."""

    name = "nothing follows"

    def __init__(self):
        self.asked = []

    def judge(self, questions):
        from strata.agent.judge import Judgement

        self.asked += [question.sentence for question in questions]
        return [Judgement(question.index, False, "It does not follow.") for question in questions]


def test_check_4_removes_a_row_whose_sentence_checks_1_to_3_cannot_prove(library, monkeypatch):
    """Ticket 61: the table runs all six checks through SixChecks, as a draft does. A planted sentence on what helped
    that restates nothing word for word goes to the judge, which says it does not follow, so its row is removed with
    check 4's reason and the other row stands."""
    from strata.agent.answer_check import SixChecks
    from strata.agent.claims import Claim

    written = risks._claims

    def planted(row, m, counts_id):
        count, helped = written(row, m, counts_id)
        if row["risk_label"] == "Cost estimates below market rates":
            helped = Claim("What helped was a stronger contractor.", "summary", helped.evidence_ids)
        return count, helped

    monkeypatch.setattr(risks, "_claims", planted)
    judge = NothingFollows()

    payload = build(library, INDIA_WORKS, six_checks=SixChecks(None, judge)).payload

    assert judge.asked == ["What helped was a stronger contractor."]
    assert [(row["risk_label"], row["claim_kind"], row["check"], row["reason_code"])
            for row in payload["verifier"]["removed"]] == [
        ("Cost estimates below market rates", "helped", 4, "not_supported")]
    assert "Cost estimates below market rates" not in [row["risk_label"] for row in payload["rows"]]
    assert payload["rows"]


def test_check_6_attaches_a_disagreement_whose_side_is_a_row_s_source(library):
    """Ticket 61: check 6 asks get_disagreements about the project each row's sources belong to, and a disagreement
    whose side is a passage the row's lesson rests on, and whose value the row states ("market rates"), is attached
    to that row with both sides, which the payload carries. Two are planted at the tool, beside the fixture's own,
    with the same side, and the row carries both, as many as the counts say were shown (ticket 61's verify, F1)."""
    import planted_disagreements as planted

    from strata.agent.answer_check import SixChecks

    payload = build(library, INDIA_WORKS,
                    six_checks=SixChecks(None, None, planted.with_adapter("twice_on_market_rates"))).payload

    [row] = [row for row in payload["rows"] if row["risk_label"] == "Cost estimates below market rates"]
    assert [card["id"] for card in row["disagreements"]] == [planted.PLANTED, planted.PLANTED_TOO]
    assert [side["evidence_id"] for side in row["disagreements"][0]["sides"]] == [planted.ICR_54, planted.ISR_7]
    assert payload["verifier"]["counts"]["disagreements"]["shown"] == 2
    assert [other["disagreements"] for other in payload["rows"] if other is not row] == [[]] * (len(payload["rows"]) - 1)


def test_a_count_that_differs_from_the_tool_s_summary_is_removed_before_the_verifier_runs(library, monkeypatch):
    """Ticket 30's verify O1: a count of 23 was kept ("came up in 23 of 1 completion reports"), because 23 is the
    ICR's page number in the cited summary. The builder compares each row's count with the summary's own count for
    its risk before the verifier runs, and removes a row that differs, as check 1 would."""
    made = risks._row

    def wrong(factor, lesson):
        row = made(factor, lesson)
        return {**row, "k": 23} if row["risk_label"] == "Cost estimates below market rates" else row

    monkeypatch.setattr(risks, "_row", wrong)

    payload = build(library, INDIA_WORKS).payload

    assert [(row["risk_label"], row["claim_kind"], row["k"], row["check"], row["reason_code"])
            for row in payload["verifier"]["removed"]] == [
        ("Cost estimates below market rates", "count", 23, 1, "number_not_in_records")]
    assert "Cost estimates below market rates" not in [row["risk_label"] for row in payload["rows"]]


def test_the_rural_roads_package_in_kenya_reaches_no_completion_report_on_the_fixture(library):
    """Kenya's comparable works packages under Request for Bids belong to P156634, P176758 and P170941
    (values.toml [comparables]), all still active, so none has an ICR."""
    payload = build(library, RURAL_ROADS_KENYA, words="Rural roads").payload

    assert payload["empty_reason"] == "no_reports"
    assert (payload["p"], payload["m"]) == (3, 0)
    assert payload["coverage"]["missing"] == [{"reason_code": "no_report", "count": 3}]
    assert payload["rows"] == []


def test_as_of_p130164_s_approval_date_nothing_public_later_reaches_the_table(library):
    approved = VALUES["approval-p130164"]["value"]
    table = build(library, INDIA_WORKS, as_of=approved)

    assert table.payload["as_of"] == approved.isoformat()
    assert len(table.facts) > 0
    for evidence_id, row in table.facts.items():
        assert str(row["public_from"]) <= approved.isoformat(), evidence_id
    assert table.payload["rows"] == []


def test_at_most_max_rows_risks_in_the_same_order_for_the_same_tool_results(library):
    first, again = build(library, INDIA_WORKS).payload, build(library, INDIA_WORKS).payload
    keys = [row["risk_key"] for row in first["rows"]]

    assert first["max_rows"] == load_thresholds().value("package_risks.max_rows") == 5
    assert len(keys) <= 5
    assert keys == [row["risk_key"] for row in again["rows"]]
    held = load_thresholds()
    one = Thresholds(held.path, {**held.values, "package_risks": {"max_rows": 1}})
    assert [row["risk_key"] for row in build(library, INDIA_WORKS, thresholds=one).payload["rows"]] == keys[:1]


def test_a_selected_risk_that_is_no_longer_in_the_table_is_kept_but_not_counted(library):
    payload = build(library, INDIA_WORKS, selected=("cost_estimates", "evaluation_delays")).payload

    assert payload["selected_keys"] == ["cost_estimates"]
    assert payload["selected_not_shown"] == [{"risk_key": "evaluation_delays", "risk_label": "Slow bid evaluation or award"}]


def test_a_package_with_no_comparable_package_has_no_reports_to_look_in(library):
    payload = build(library, {**INDIA_WORKS, "category": "Goods"}).payload

    assert payload["empty_reason"] == "no_comparables"
    assert payload["rows"] == []


# ── The routes, at seam 3 ────────────────────────────────────────────────
#
# GET /api/packages/{step_reference}/risks and GET /api/planned-packages/{package_id}/risks run the builder as the
# viewer, with section 1's criteria; PUT .../risk-selection keeps the viewer's selection in the app state store
# (Lakebase on the App, ADR 0005; a DuckDB file here).

DEMO = "KE-NWWDA-541055-CW-RFB"  # the demo plan's works package under Request for Bids (plan-541055-estimated)
TODAY = dt.date(2026, 10, 28)


def person(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": name,
            "X-Forwarded-User": f"50{number}@1984", "X-Forwarded-Access-Token": "not-a-real-token"}


ANA, BEN = person(1, "Ana"), person(2, "Ben")


@pytest.fixture
def app(library, tmp_path):
    from contextlib import contextmanager

    from strata import appstate
    from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases
    from strata.packages.store import PackageStore
    from strata.server.app import create_app

    state = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state) as engine:
        appstate.build(engine)

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(library, read_only=True) as engine:
            yield engine

    cases = load_cases(PACKAGE_CASES)
    numbers = iter(range(1, 100))
    return create_app(engine_for=reading, packages=PackageStore(lambda: DuckDBEngine.open(state)),
                      package_reader=lambda: ScriptedAgent(cases["package-rural-roads-kenya"]), today=lambda: TODAY,
                      now=lambda: dt.datetime(2026, 10, 28, 9, tzinfo=dt.UTC),
                      new_package_id=lambda: f"pkg-{next(numbers):012d}")


def call(app, method, path, headers, **options):
    import asyncio

    import httpx

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers, **options)
    return asyncio.run(go())


INDIA = "country=IN&notice_from=2013-01-01"


def test_the_screens_recorded_risk_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """tests/record_risks_api.py writes the answers section 3's screen tests serve, from one story on the fixture;
    the routes must still answer with them word for word."""
    from record_risks_api import answers

    for name, text in answers(tmp_path).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), f"{name} is out of date"


def test_a_step_row_package_s_section_follows_section_1_s_criteria(app):
    kenya = call(app, "GET", f"/api/packages/{DEMO}/risks", ANA).json()
    india = call(app, "GET", f"/api/packages/{DEMO}/risks?{INDIA}", ANA).json()

    assert (kenya["empty_reason"], kenya["m"]) == ("no_reports", 0)
    assert [row["risk_label"] for row in india["rows"]][:1] == ["Cost estimates below market rates"]


def test_row_selections_persist_for_the_viewer_when_the_package_is_reopened(app):
    saved = call(app, "PUT", f"/api/packages/{DEMO}/risk-selection", ANA, json={"changes": {"cost_estimates": True}})

    assert saved.status_code == 200
    assert call(app, "GET", f"/api/packages/{DEMO}/risks?{INDIA}", ANA).json()["selected_keys"] == ["cost_estimates"]
    assert call(app, "GET", f"/api/packages/{DEMO}/risks?{INDIA}", BEN).json()["selected_keys"] == []
    call(app, "PUT", f"/api/packages/{DEMO}/risk-selection", ANA, json={"changes": {"cost_estimates": False}})
    assert call(app, "GET", f"/api/packages/{DEMO}/risks?{INDIA}", ANA).json()["selected_keys"] == []


def test_a_preview_or_an_unknown_risk_changes_no_selection(app):
    preview = call(app, "PUT", f"/api/packages/{DEMO}/risk-selection", ANA,
                   json={"changes": {"cost_estimates": True}, "view": "piu"})
    unknown = call(app, "PUT", f"/api/packages/{DEMO}/risk-selection", ANA, json={"changes": {"bitumen": True}})

    assert (preview.status_code, preview.json()["code"]) == (403, "preview")
    assert (unknown.status_code, unknown.json()["code"]) == (422, "unknown_risk")
    assert call(app, "GET", f"/api/packages/{DEMO}/risks?{INDIA}", ANA).json()["selected_keys"] == []


def test_a_package_from_a_sentence_keeps_its_selection_with_the_package_for_its_author(app):
    from test_planned_packages import plan

    _, package = plan(app, headers=ANA)
    path = f"/api/planned-packages/{package['package_id']}"
    call(app, "PUT", f"{path}/risk-selection", ANA, json={"changes": {"cost_estimates": True}})

    mine = call(app, "GET", f"{path}/risks", ANA).json()
    assert (mine["empty_reason"], mine["p"], mine["m"]) == ("no_reports", 3, 0)
    assert mine["selected_not_shown"] == [{"risk_key": "cost_estimates", "risk_label": "Cost estimates below market rates"}]
    assert call(app, "GET", f"{path}/risks", BEN).status_code == 404
    assert call(app, "PUT", f"{path}/risk-selection", BEN, json={"changes": {"cost_estimates": True}}).status_code == 404
