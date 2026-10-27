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
from strata.agent.scripted import CRITERIA_CASES, ScriptedAgent, ScriptedJudge, load_cases
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


SCRIPTED = object()  # app_on's judge: the case's recorded judge answers


def app_on(database, state_db, case="criteria-similar-experience", today=TODAY, judge=SCRIPTED):
    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    numbers = iter(range(1, 100))
    clock = iter(dt.datetime(2026, 10, 22, 14, minute, tzinfo=dt.UTC) for minute in range(60))
    return create_app(engine_for=reading, criteria=CriteriaStore(lambda: DuckDBEngine.open(state_db)),
                      criteria_reader=lambda: ScriptedAgent(CASES[case]), today=lambda: today, now=lambda: next(clock),
                      new_check_id=lambda: f"chk-{next(numbers):012d}",
                      judge=ScriptedJudge(CASES[case]) if judge is SCRIPTED else judge)


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
    # The text sets two items, similar experience and turnover; the server counts them, never the browser.
    assert result["item_count"] == 2


def test_each_reading_passes_the_checks_against_your_own_words(app):
    result = the("comparison", compare(app)[1])

    checks = result["checks"]
    assert checks["sentences"] == {"written": 2, "kept": 2, "removed": 0}
    # The readings are checked against facts recorded under the reader's name, and the check line names it.
    assert checks["tools"] == ["criteria_reader"]
    assert checks["numbers"]["matched"] == checks["numbers"]["total"] == 4  # two and 10; 25 and three
    assert result["removed"] == []


def test_both_runs_pass_all_six_checks_and_the_judge_is_asked_only_about_the_readings(app):
    """Ticket 24's six checks run on everything section 5 shows (strata.agent.answer_check.SixChecks). A quote found
    word for word is proven by check 3, so check 4 asks the judge only about each "I read this as ..." reading."""
    run = the("package_run", events(call(app, "POST", f"/api/packages/{WORKS}/criteria/run", ANA, json={}).text))
    comparison = the("comparison", compare(app)[1])

    assert run["checks"]["checks_run"] == comparison["checks"]["checks_run"] == [1, 2, 3, 4, 5, 6]
    assert run["checks"]["judge"]["called"] is False
    assert run["checks"]["shown"]["proven"] == run["checks"]["sentences"]["kept"] > 0
    assert comparison["checks"]["judge"] | {"called": True} == {"called": True, "responded": True, "judged": 2,
                                                                "followed": 2, "unjudged": 0, "proven": 0}
    assert comparison["section_checks"]["checks_run"] == [1, 2, 3, 4, 5, 6]


def test_a_reading_the_judge_says_does_not_follow_from_your_words_is_removed_with_its_reason(fixture_db, state_db):
    """The reader read "two contracts of US$10 million" back as "10 contracts of US$2 million": both numbers are in
    your words, so only check 4 can catch it."""
    right = the("comparison", compare(app_on(fixture_db, state_db))[1])
    swapped = the("comparison", compare(app_on(fixture_db, state_db, "criteria-swapped-reading"),
                                        "criteria-swapped-reading")[1])

    [removed] = swapped["removed"]
    assert (removed["about"], removed["reason"]) == ("similar_experience", "not_supported")
    assert [item["reading_removed"] for item in swapped["items"]] == [True, False]
    assert swapped["checks"]["sentences"] == {"written": 2, "kept": 1, "removed": 1}
    # The removed sentence is the reading alone: the tool's counts are unchanged, and the screen leaves them out
    # with the reading, since they rest on it.
    assert [item["same_or_less"] for item in swapped["items"]] == [item["same_or_less"] for item in right["items"]]


def test_with_no_judge_connected_every_reading_is_removed_and_the_quotes_still_show(fixture_db, state_db):
    app = app_on(fixture_db, state_db, judge=None)

    result = the("comparison", compare(app)[1])
    run = the("package_run", events(call(app, "POST", f"/api/packages/{WORKS}/criteria/run", ANA, json={}).text))

    assert [(entry["about"], entry["reason"]) for entry in result["removed"]] == [
        ("similar_experience", "judge_unavailable"), ("turnover", "judge_unavailable")]
    assert all(item["reading_removed"] for item in result["items"]) and result["checks"]["judge"]["unjudged"] == 2
    # Check 3 proves every quote word for word, so the package run needs no judge.
    assert run["removed"] == [] and run["checks"]["judge"]["called"] is False


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


def test_a_request_to_judge_a_review_decision_is_refused_in_full_and_nothing_is_compared(fixture_db, state_db):
    app = app_on(fixture_db, state_db, "criteria-review-decisions")

    result = the("comparison", compare(app, "criteria-review-decisions")[1])

    assert result["refusal"] == {"key": "review_decisions", "partial": False}
    assert (result["items"], result["item_count"], result["unplaced"]) == ([], 0, [])


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
    assert saved["status"] == "failed" and saved["pasted_text"] == CASES["criteria-similar-experience"].question
    assert saved["result"] is None


def test_a_comparison_that_fails_after_the_save_is_marked_failed_and_the_last_good_table_stays(fixture_db, state_db):
    """The newest text comes back in the field, and the table is the last comparison that finished."""
    first = the("comparison", compare(app_on(fixture_db, state_db))[1])

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    bare = create_app(engine_for=reading, criteria=CriteriaStore(lambda: DuckDBEngine.open(state_db)),
                      today=lambda: TODAY, new_check_id=lambda: "chk-000000000099",
                      now=lambda: dt.datetime(2026, 10, 22, 15, 0, tzinfo=dt.UTC))
    edited = "Similar experience: at least three contracts of similar works of US$10 million each."
    response = call(bare, "POST", f"/api/packages/{CONSULTANT}/criteria/compare", ANA, json={"text": edited})

    assert the("error", events(response.text))["code"] == "no_reader"
    saved = call(bare, "GET", f"/api/packages/{CONSULTANT}/criteria", ANA).json()["comparison"]
    assert (saved["check_id"], saved["status"], saved["pasted_text"]) == ("chk-000000000099", "failed", edited)
    assert saved["result"]["check_id"] == first["check_id"] and saved["result"]["items"] == first["items"]
    assert saved["text_compared"] is False
    with DuckDBEngine.open(state_db, read_only=True) as engine:
        statuses = [status for (status,) in engine.run(
            "SELECT status FROM strata.app.criteria_checks WHERE check_id = :id ORDER BY created_at", {"id": "chk-000000000099"}).rows]
    assert statuses == ["running", "failed"]


def test_a_reader_answer_in_a_shape_it_should_not_have_drops_that_part_and_never_crashes():
    """A live model may give parts as a list, or a count with a fraction; the app keeps only what it can check."""
    from strata.config import load_criteria_items
    from strata.criteria.workflow import read_answer

    text = "Similar experience: at least 2.5 contracts of similar works. Key staff: a site engineer with 10 years."
    answer = json.dumps({"refusal": None, "unplaced": [], "items": [
        {"item_key": "similar_experience", "excerpt": "at least 2.5 contracts of similar works", "parts": {"contracts": 2.5}},
        {"item_key": "key_staff", "excerpt": "a site engineer with 10 years", "parts": [10]},
    ]})

    reading = read_answer(answer, text, load_criteria_items())

    assert [(item["item_key"], item["parts"]) for item in reading.items] == [("similar_experience", {})]


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
    # IEG's own words that restate it, for the drawer's IEG line, as the risks section gives them.
    assert lesson["ieg_quote"]["text"] == VALUES["icr-review-2023-restates-para-54"]["quote"]
    # The card quotes its paragraph with the lesson's words highlighted, in the paragraph's language.
    start, end = lesson["excerpt"]["range"]
    assert lesson["excerpt"]["text"][start:end] == lesson["quote"] and lesson["excerpt"]["lang"] == "en"


def test_check_6_s_card_comes_with_the_lesson_whose_paragraph_is_one_side_of_a_disagreement(fixture_db, state_db,
                                                                                            tmp_path, monkeypatch):
    """Ticket 31's review round 3, F2: the section ran check 6 and dropped its cards, so a lesson quote that is one
    side of a disagreement showed alone while the counts said a card was shown. The card now comes with the lesson
    it concerns, with both sides' evidence so their markers open, and its count agrees. The disagreement is planted
    at the tool, beside the fixture's own, with ICR P130164 paragraph 54 as its first side
    (tests/planted_disagreements.py)."""
    import lesson_scenario as scenario
    import planted_disagreements as planted

    tools = planted.with_adapter("quoting_icr_54")
    monkeypatch.setattr("strata.server.app.load_tools", lambda: tools)
    library = scenario.copy_of(fixture_db, tmp_path)
    scenario.decide(library, scenario.REBIDDING, dt.date(2026, 10, 27))
    app = app_on(library, state_db, today=dt.date(2026, 10, 28))

    run = the("package_run", events(call(app, "POST", f"/api/packages/{WORKS}/criteria/run", ANA, json={}).text))

    [lesson] = run["lessons"]["groups"][0]["lessons"]
    [card] = lesson["disagreements"]
    assert (card["id"], [side["evidence_id"] for side in card["sides"]]) == (
        planted.PLANTED, [planted.ICR_54, planted.ISR_7])
    assert run["checks"]["disagreements"]["shown"] == 1
    assert {side["evidence_id"] for side in card["sides"]} <= set(run["evidence"])
    assert [row["disagreements"] for row in run["rejected"]["rows"]] == [[] for _ in run["rejected"]["rows"]]


def test_every_card_check_6_attaches_to_one_lesson_quote_comes_with_it(fixture_db, state_db, tmp_path, monkeypatch):
    """Ticket 61's verify, F1: with two disagreements whose side is ICR P130164 paragraph 54, the counts said two
    cards were shown while the run carried only the first. Every card comes with the lesson now, in the order check 6
    attached them, so the cards the section carries number what the check line says it showed."""
    import lesson_scenario as scenario
    import planted_disagreements as planted

    tools = planted.with_adapter("twice_quoting_icr_54")
    monkeypatch.setattr("strata.server.app.load_tools", lambda: tools)
    library = scenario.copy_of(fixture_db, tmp_path)
    scenario.decide(library, scenario.REBIDDING, dt.date(2026, 10, 27))
    app = app_on(library, state_db, today=dt.date(2026, 10, 28))

    run = the("package_run", events(call(app, "POST", f"/api/packages/{WORKS}/criteria/run", ANA, json={}).text))

    [lesson] = run["lessons"]["groups"][0]["lessons"]
    assert [card["id"] for card in lesson["disagreements"]] == [planted.PLANTED, planted.PLANTED_TOO]
    carried = [card for lesson in (one for group in run["lessons"]["groups"] for one in group["lessons"])
               for card in lesson["disagreements"]] + [card for row in run["rejected"]["rows"]
                                                       for card in row["disagreements"]]
    assert len(carried) == run["checks"]["disagreements"]["shown"] == 2


def test_each_removed_entry_says_whether_it_was_a_reading_a_record_s_quote_or_a_passage_s(fixture_db, state_db):
    """Ticket 31's review round 3, F4: the screen worked out what a removed sentence was about from the shape of its
    id. The server sends it with each removed entry: a reading of your words, a reason quoted from an award notice,
    or a lesson's words quoted from its paragraph. With no judge connected, every reading is removed."""
    app = app_on(fixture_db, state_db, judge=None)
    _, sent = compare(app)

    removed = the("comparison", sent)["removed"]
    assert removed and {entry["source"] for entry in removed} == {"reading"}


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
    # The drawer's source line reads a record's date from document_date, as for every other record.
    assert record["row"]["source"]["document_date"] == fields["published"]["value"] is not None
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


def test_a_package_run_with_no_comparable_packages_says_so_in_each_part_instead_of_failing(app):
    """The screen starts no run then, but a direct request still gets an answer, never an internal error."""
    sent = events(call(app, "POST", "/api/packages/NOPE-123/criteria/run", ANA, json={}).text)

    assert [kind for kind, _ in sent if kind == "error"] == []
    run = the("package_run", sent)
    assert run["rejected"]["state"] == "no_comparables" and run["rejected"]["rows"] == []
    assert run["cost"]["abstention"] == {"reason": "no_comparables"} and run["cost"]["rows"] == []
    assert run["lessons"] == {"state": "none", "groups": []}


def test_the_lesson_groups_are_risk_factors_from_the_closed_list_in_the_thresholds_file():
    """criteria.lesson_factors names the groups (CLAUDE.md rule 9); each must be one of ticket 29's risk factors."""
    from strata.config import load_lesson_lists, load_thresholds

    factors = load_thresholds().value("criteria.lesson_factors")

    assert factors == ["cost_estimates", "designs_and_specifications"]
    assert all(load_lesson_lists().risk_factor(factor) is not None for factor in factors)


def test_the_refusal_keys_this_section_can_give_are_ticket_24_s():
    """The reader may refuse only with keys from the one list of refusals (src/strata/agent/refusals.py)."""
    from strata.agent.refusals import REFUSALS as EVERY_KEY
    from strata.criteria.workflow import REFUSALS

    assert set(REFUSALS) == {"live_tenders", "review_decisions"} and set(REFUSALS) <= set(EVERY_KEY)
