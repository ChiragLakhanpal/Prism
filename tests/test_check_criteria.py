"""Check your criteria, section 5 of the package workspace, at seam 3 (ticket 31).

GET .../criteria gives the collapsed summary; POST .../criteria/run streams the package-level run (rejected bids,
the cost estimate and the lessons, checked); POST .../criteria/compare streams the comparison of pasted
qualification criteria, read by the criteria reader (replayed here from tests/fixtures/agent/criteria.toml). The
text is kept in the app state store (Lakebase on the App, ADR 0005; a DuckDB file here) for its owner only.

Expected values come from the tools called by name on the fixture (each count must match the tool's rows), from
tests/ground_truth/values.toml (icr-para-54) and from the ticket's words.
"""

import asyncio
import datetime as dt
import json
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata import appstate
from strata.agent.scripted import CRITERIA_CASES, ScriptedAgent, load_cases
from strata.criteria.store import CriteriaStore
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
TODAY = dt.date(2026, 10, 22)
CONSULTANT, WORKS = "KE-CWSB-224323-CS-QCBS", "KE-NWWDA-541055-CW-RFB"
CASES = load_cases(CRITERIA_CASES)


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"40{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN = viewer(21, "Ana"), viewer(22, "Ben")


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


def events(text: str) -> list[tuple[str, dict]]:
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if lines:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found


def the(kind: str, sent: list[tuple[str, dict]]) -> dict:
    [found] = [data for name, data in sent if name == kind]
    return found


@pytest.fixture
def state_db(tmp_path):
    path = tmp_path / "state.duckdb"
    with DuckDBEngine.open(path) as engine:
        appstate.build(engine)
    return path


def app_on(database, state_db, case="criteria-similar-experience", today=TODAY):
    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    numbers = iter(range(1, 100))
    clock = iter(dt.datetime(2026, 10, 22, 14, minute, tzinfo=dt.UTC) for minute in range(60))
    return create_app(engine_for=reading, criteria=CriteriaStore(lambda: DuckDBEngine.open(state_db)),
                      criteria_reader=lambda: ScriptedAgent(CASES[case]), today=lambda: today, now=lambda: next(clock),
                      new_check_id=lambda: f"chk-{next(numbers):012d}")


@pytest.fixture
def app(fixture_db, state_db):
    return app_on(fixture_db, state_db)


def tool(fixture_db, name, as_of=TODAY, **arguments):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        return registry.call(name, {"as_of": as_of.isoformat(), **arguments},
                             registry.Context(engine=engine, viewer=Viewer(email="a@b.c", token="t")))


def comparables(fixture_db, step_reference, as_of=TODAY) -> str:
    return ",".join(row["step_reference"] for row in tool(fixture_db, "find_comparables", as_of, step_reference=step_reference)["rows"])


def compare(app, case="criteria-similar-experience", headers=ANA, package=CONSULTANT, **extra):
    response = call(app, "POST", f"/api/packages/{package}/criteria/compare", headers,
                    json={"text": CASES[case].question, **extra})
    return response, events(response.text) if response.status_code == 200 else []


def test_the_screens_recorded_criteria_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """tests/record_criteria_api.py writes the answers section 5's screen tests serve, from one story on the
    fixture; the routes must still answer with them word for word."""
    from record_criteria_api import answers

    for name, text in answers(tmp_path).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), f"{name} is out of date"


# ── The collapsed summary ────────────────────────────────────────────────

def test_the_summary_counts_the_comparable_packages_whose_criteria_are_public_from_the_tool(app, fixture_db):
    answer = call(app, "GET", f"/api/packages/{CONSULTANT}/criteria", ANA).json()
    criteria = tool(fixture_db, "compare_criteria", comparables=comparables(fixture_db, CONSULTANT))

    assert answer["state"] == "ok"
    assert answer["public_criteria_count"] == len(criteria["rows"]) > 0
    assert answer["comparables_total"] == criteria["summary"]["counts"]["total"]
    assert [entry["step_reference"] for entry in answer["public"]] == [row["step_reference"] for row in criteria["rows"]]
    assert answer["limits"]["max_chars"] == 20000 and answer["comparison"] is None


def test_none_of_the_works_comparables_published_their_qualification_criteria(app):
    answer = call(app, "GET", f"/api/packages/{WORKS}/criteria", ANA).json()

    assert (answer["state"], answer["public_criteria_count"], answer["comparables_total"]) == ("none_public", 0, 49)


# ── Comparing your criteria ──────────────────────────────────────────────

def test_similar_experience_of_two_contracts_of_us_10_million_states_how_many_comparable_notices_asked_for_the_same_or_less(
        app, fixture_db):
    """The ticket's first criterion, with the scripted reader on the fixture."""
    response, sent = compare(app)
    result = the("comparison", sent)
    criteria = tool(fixture_db, "compare_criteria", comparables=comparables(fixture_db, CONSULTANT),
                    items=json.dumps([{"item_key": "similar_experience",
                                       "parts": {"contracts": 2, "amount": {"value": "10000000", "currency": "USD"}}}]))

    assert response.status_code == 200
    similar = next(item for item in result["items"] if item["item_key"] == "similar_experience")
    asked = [row for row in criteria["rows"] if "similar_experience" in row["relations"]]
    same_or_less = [row for row in asked if row["relations"]["similar_experience"] in ("less", "same")]
    assert (similar["stated"], similar["same_or_less"]) == (len(asked), len(same_or_less))
    assert similar["same_or_less"] > 0 and similar["label"] == "Similar experience"
    assert [notice["step_reference"] for notice in similar["notices"]] == [row["step_reference"] for row in asked]
    for notice in similar["notices"]:
        # Each counted notice cites the notice passage that holds its requirement.
        assert notice["passage_id"].startswith(f"{notice['notice_id']}/")
        assert notice["relation"] in ("less", "same", "more", "different")
    assert similar["your_excerpt"] == {"text": "at least two contracts of similar works of US$10 million each",
                                       "shortened": False}
    assert similar["reading"].startswith("I read this as") and not similar["reading_removed"]
    assert result["refusal"] is None and result["coverage"]["n"] == criteria["summary"]["counts"]["n"]


def test_an_item_no_comparable_notice_set_and_a_part_that_sets_no_item_are_shown_as_such(app):
    result = the("comparison", compare(app)[1])

    turnover = next(item for item in result["items"] if item["item_key"] == "turnover")
    assert (turnover["stated"], turnover["notices"]) == (0, [])
    assert result["unplaced"] == ["The bid must be signed by a person with a power of attorney."]


def test_each_reading_passes_the_checks_against_your_own_words(app):
    result = the("comparison", compare(app)[1])

    checks = result["checks"]
    assert checks["sentences"] == {"written": 2, "kept": 2, "removed": 0}
    assert checks["numbers"]["matched"] == checks["numbers"]["total"] == 4  # two and 10; 25 and three
    assert result["removed"] == []


def test_the_steps_are_announced_in_order_and_the_text_is_saved_first(app):
    sent = compare(app)[1]

    assert sent[0] == ("saved", {"check_id": "chk-000000000001"})
    assert [(data["id"], data["status"]) for kind, data in sent if kind == "step"] == [
        ("read", "running"), ("read", "done"), ("find", "running"), ("find", "done"), ("compare", "running"),
        ("compare", "done"), ("checks", "running"), ("checks", "done")]
    assert sent[-1] == ("done", {})


def test_your_text_is_kept_for_you_and_never_shown_to_anyone_else(app, state_db):
    compare(app)

    mine = call(app, "GET", f"/api/packages/{CONSULTANT}/criteria", ANA).json()["comparison"]
    theirs = call(app, "GET", f"/api/packages/{CONSULTANT}/criteria", BEN).json()["comparison"]
    assert mine["pasted_text"] == CASES["criteria-similar-experience"].question and mine["stale"] is False
    assert mine["result"]["items"][0]["item_key"] == "similar_experience"
    assert theirs is None
    with DuckDBEngine.open(state_db, read_only=True) as engine:
        owners = {row[0] for row in engine.run("SELECT owner_id FROM strata.app.criteria_checks", {}).rows}
    assert owners == {"4021@1984"}


def test_a_request_to_judge_a_live_tender_s_bids_is_refused_with_the_live_tenders_key(fixture_db, state_db):
    app = app_on(fixture_db, state_db, "criteria-live-tender")

    response, sent = compare(app, "criteria-live-tender")
    result = the("comparison", sent)

    assert result["refusal"] == {"key": "live_tenders", "partial": False}
    assert result["items"] == [] and result["unplaced"] == []
    # The words come from the copy file; nothing the reader wrote, and no bidder the text named, comes back.
    assert "Mwangaza" not in response.text and "Pwani" not in response.text
    assert [data["id"] for kind, data in sent if kind == "step"] == ["read", "read"]


def test_the_must_refuse_question_for_this_section_is_the_live_tender_case_word_for_word():
    import yaml

    questions = {question["id"]: question for question in
                 yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]}
    question, case = questions["refuse-live-tenders-criteria"], CASES["criteria-live-tender"]

    assert (question["question"], question["scope"]) == (case.question, case.scope)
    assert question["expected"] == {"must_refuse": True, "refusal": "live_tenders", "partial": False}


def test_a_partial_refusal_compares_the_criteria_and_leaves_out_the_rest(fixture_db, state_db):
    app = app_on(fixture_db, state_db, "criteria-partial-refusal")

    result = the("comparison", compare(app, "criteria-partial-refusal")[1])

    assert result["refusal"] == {"key": "review_decisions", "partial": True}
    assert [item["item_key"] for item in result["items"]] == ["similar_experience"]


def test_text_that_sets_no_qualification_criteria_finds_no_item(fixture_db, state_db):
    app = app_on(fixture_db, state_db, "criteria-none-found")

    result = the("comparison", compare(app, "criteria-none-found")[1])

    assert (result["refusal"], result["items"], result["unplaced"]) == (None, [], [])


def test_a_preview_compares_nothing_and_an_empty_or_long_text_is_refused(app):
    preview, _ = compare(app, view="piu")
    empty = call(app, "POST", f"/api/packages/{CONSULTANT}/criteria/compare", ANA, json={"text": "   "})
    long = call(app, "POST", f"/api/packages/{CONSULTANT}/criteria/compare", ANA, json={"text": "a" * 20001})
    nobody = call(app, "POST", f"/api/packages/{CONSULTANT}/criteria/compare", {}, json={"text": "Turnover"})

    assert (preview.status_code, preview.json()["code"]) == (403, "preview")
    assert (empty.status_code, empty.json()["code"]) == (422, "empty")
    assert (long.status_code, long.json()["code"], long.json()["max_chars"]) == (422, "too_long", 20000)
    assert (nobody.status_code, nobody.json()["code"]) == (401, "no_identity")


def test_with_no_reader_connected_the_comparison_says_so_and_the_text_stays_saved(fixture_db, state_db):
    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    bare = create_app(engine_for=reading, criteria=CriteriaStore(lambda: DuckDBEngine.open(state_db)),
                      today=lambda: TODAY)
    sent = compare(bare)[1]

    assert the("error", sent)["code"] == "no_reader"
    saved = call(bare, "GET", f"/api/packages/{CONSULTANT}/criteria", ANA).json()["comparison"]
    assert saved["status"] == "running" and saved["pasted_text"] == CASES["criteria-similar-experience"].question


# ── The package-level run ────────────────────────────────────────────────

def test_the_package_run_counts_rejected_bids_and_quotes_each_reason_with_its_notice_id(app, fixture_db):
    sent = events(call(app, "POST", f"/api/packages/{WORKS}/criteria/run", ANA, json={}).text)
    run = the("package_run", sent)
    rejected = tool(fixture_db, "rejected_bids", comparables=comparables(fixture_db, WORKS))

    counts = rejected["summary"]["counts"]
    assert (run["rejected"]["counts"]["n"], run["rejected"]["counts"]["m"]) == (counts["n"], counts["m"])
    assert [row["evidence_id"] for row in run["rejected"]["rows"]] == [row["evidence_id"] for row in rejected["rows"]]
    assert all(row["notice_id"] and row["reason"]["quote"] and not row["removed"] for row in run["rejected"]["rows"])
    assert run["rejected"]["groups"][0]["label"]
    # Every reason is a quote from its award notice, a record with no page.
    assert run["checks"]["quotes"]["found"] == run["checks"]["quotes"]["total"] == len(rejected["rows"])
    assert run["checks"]["quotes_without_pages"] == len(rejected["rows"])


def test_the_package_run_abstains_on_the_cost_estimate_below_twenty_and_lists_every_package(app, fixture_db):
    run = the("package_run", events(call(app, "POST", f"/api/packages/{WORKS}/criteria/run", ANA, json={}).text))
    cost = tool(fixture_db, "compare_cost_estimates", comparables=comparables(fixture_db, WORKS), step_reference=WORKS)

    assert run["cost"]["abstention"]["reason"] == "too_few_comparables"
    assert [row["step_reference"] for row in run["cost"]["rows"]] == [row["step_reference"] for row in cost["rows"]]
    assert run["cost"]["counts"] == cost["summary"]["counts"]


def test_the_package_run_finds_the_lessons_on_cost_estimates_with_icr_p130164_paragraph_54(fixture_db, state_db,
                                                                                         tmp_path):
    """The library holds a lesson only after two people decide it (tests/lesson_scenario.py)."""
    import lesson_scenario as scenario

    library = scenario.copy_of(fixture_db, tmp_path)
    scenario.decide(library, scenario.REBIDDING, dt.date(2026, 10, 27))
    app = app_on(library, state_db, today=dt.date(2026, 10, 28))

    run = the("package_run", events(call(app, "POST", f"/api/packages/{WORKS}/criteria/run", ANA, json={}).text))

    [group] = run["lessons"]["groups"]
    assert group["factor"] == "cost_estimates"
    [lesson] = group["lessons"]
    paragraph = VALUES["icr-para-54"]
    assert lesson["passage_id"] == "31525018/v1/54"
    assert (lesson["project_id"], lesson["para"], lesson["page"]) == (paragraph["project"], str(paragraph["paragraph"]),
                                                                      paragraph["pdf_page"])
    assert lesson["document_date"] == paragraph["date"].isoformat()
    assert paragraph["value"] in lesson["quote"] and lesson["ieg_status"] == "restated" and not lesson["removed"]


def test_a_rejected_bid_opens_its_award_notice_with_the_reason_highlighted_and_no_bidder_named(fixture_db, state_db):
    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=reading, today=lambda: TODAY)
    opened = call(app, "GET", "/api/evidence", ANA, params={"id": "strata.gold.notice:OP00125282/reason/1"})

    record = opened.json()
    fields = {field["key"]: field for field in record["row"]["fields"]}
    assert (record["kind"], record["row"]["reference"]) == ("record", "OP00125282")
    assert fields["reason_for_rejection"] == {"key": "reason_for_rejection", "value": "Bid Security not Provided",
                                              "kind": "text", "highlight": True}
    assert fields["bid_reference"]["value"] == "KE-MOWI-47509-CW-RFB"
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        names = [name for (name,) in engine.run("SELECT name FROM strata.silver.notice_bidders WHERE notice_id = :id "
                                                "AND name IS NOT NULL", {"id": "OP00125282"}).rows]
    assert names and not any(name in opened.text for name in names)


def test_a_saved_package_run_shows_at_once_while_the_comparable_packages_are_the_same(app):
    call(app, "POST", f"/api/packages/{WORKS}/criteria/run", ANA, json={})

    mine = call(app, "GET", f"/api/packages/{WORKS}/criteria", ANA).json()
    theirs = call(app, "GET", f"/api/packages/{WORKS}/criteria", BEN).json()
    assert mine["package_run"]["rejected"]["counts"]["n"] > 0
    assert mine["section_checks"]["quotes"]["total"] == mine["package_run"]["checks"]["quotes"]["total"]
    assert theirs["package_run"] is None


# ── A package planned from a sentence ────────────────────────────────────

def test_a_planned_package_s_section_reads_its_own_comparables_and_cost_estimate_for_its_author_only(fixture_db, state_db):
    """Ticket 15's package from "rural roads, Kenya, about US$15 million": its criteria choose Kenya's works under
    Request for Bids, and its cost estimate is the US$15 million its author gave."""
    from strata.agent.scripted import PACKAGE_CASES
    from strata.packages.store import PackageStore

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    def state():
        return DuckDBEngine.open(state_db)

    readers = load_cases(PACKAGE_CASES)
    app = create_app(engine_for=reading, packages=PackageStore(state), criteria=CriteriaStore(state),
                     package_reader=lambda: ScriptedAgent(readers["package-rural-roads-kenya"]),
                     today=lambda: dt.date(2026, 10, 23), new_package_id=lambda: "pkg-000000000001")
    call(app, "POST", "/api/planned-packages", ANA, json={"sentence": "rural roads, Kenya, about US$15 million"})

    summary = call(app, "GET", "/api/planned-packages/pkg-000000000001/criteria", ANA).json()
    run = the("package_run", events(call(app, "POST", "/api/planned-packages/pkg-000000000001/criteria/run", ANA,
                                         json={}).text))
    stranger = call(app, "GET", "/api/planned-packages/pkg-000000000001/criteria", BEN)

    assert summary["state"] == "none_public" and summary["comparables_total"] > 0
    assert run["cost"]["package"] == {"step_reference": None, "estimated_amount_usd": "15000000.00", "evidence_id": None,
                                      "given": True}
    assert (stranger.status_code, stranger.json()["code"]) == (404, "unknown_package")
