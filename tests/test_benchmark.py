"""The benchmark file and the full gate (ticket 33; docs/PLAN.md section 10; spec, "Evaluation").

evals/benchmark.yaml holds four kinds of question: sql (with ground-truth SQL), documents (with expected
citations), estimates (with expected ranges or abstentions) and refusals (the must-refuse set). These tests check
what the file must cover, and that a registry tool with no question fails (CLAUDE.md rule 4).
"""

import shutil
from pathlib import Path

import yaml

from strata import config
from strata.agent.refusals import REFUSALS
from strata.evals import benchmark

ROOT = Path(__file__).resolve().parents[1]


def copy_registry(tmp_path, old: str, new: str) -> Path:
    target = tmp_path / "tools.toml"
    shutil.copy(ROOT / "config" / "tools.toml", target)
    text = target.read_text()
    assert old in text, f"{old!r} is not in config/tools.toml"
    target.write_text(text.replace(old, new, 1))
    return target


def test_the_benchmark_file_covers_every_must_refuse_category_and_at_least_ten_of_each_other_kind():
    questions = benchmark.load()

    assert benchmark.problems(questions) == []
    kinds = benchmark.counts(questions)
    assert {kind: kinds[kind] >= 10 for kind in ("sql", "documents", "estimates")} == {
        "sql": True, "documents": True, "estimates": True}
    # PLAN.md section 6 lists nine categories; the 24 brief divides live tenders from review decisions, so
    # there are ten refusal keys, and each is a must-refuse question the orchestrator is asked.
    refused = {question["expected"]["refusal"] for question in questions
               if question["kind"] == "refusals" and "path" not in question}
    assert refused == set(REFUSALS)


def test_a_registry_tool_with_no_benchmark_question_fails(tmp_path):
    path = copy_registry(tmp_path, 'benchmark = "check-plan-nwwda-2026-10-09"', 'benchmark = "no-such-question"')

    found = benchmark.problems(benchmark.load(), tools=config.load_tools(path))

    assert found == ["The tool check_plan names the question no-such-question, which evals/benchmark.yaml does not "
                     "hold. Add its question in the same change (CLAUDE.md rule 4)."]


def test_a_question_that_names_another_tool_does_not_count_for_this_one(tmp_path):
    path = copy_registry(tmp_path, 'benchmark = "check-plan-nwwda-2026-10-09"',
                         'benchmark = "find-comparables-ke-nwwda-541055"')

    found = benchmark.problems(benchmark.load(), tools=config.load_tools(path))

    assert found == ["The tool check_plan names the question find-comparables-ke-nwwda-541055, which asks "
                     "find_comparables instead. Each tool needs a question of its own (CLAUDE.md rule 4)."]


def test_too_few_questions_of_a_kind_or_a_refusal_key_with_no_question_fails(tmp_path):
    questions = [question for question in benchmark.load()
                 if question["id"] not in ("refuse-wrong-edition", "search-passages-similar-experience")]

    found = benchmark.problems(questions, minimum=len([q for q in questions if q["kind"] == "documents"]) + 1)

    assert "The refusal wrong_edition has no must-refuse question." in found
    assert any(problem.startswith("The benchmark file holds") and "documents" in problem for problem in found)


def test_a_question_written_wrong_is_named(tmp_path):
    questions = benchmark.load() + [
        {"id": "check-plan-nwwda-2026-10-09", "kind": "sql", "question": "Again?", "expected": {}},
        {"id": "made-up", "kind": "opinions", "question": "What do you think?", "expected": {}},
        {"id": "no-ground-truth", "kind": "sql", "tool": "check_plan", "question": "Which?", "arguments": {},
         "ground_truth": "tests/ground_truth/missing.sql", "expected": {}},
    ]

    found = benchmark.problems(questions)

    assert "Two questions have the id check-plan-nwwda-2026-10-09." in found
    assert "made-up is of kind opinions. The kinds are sql, documents, estimates and refusals." in found
    assert "no-ground-truth names the ground-truth SQL tests/ground_truth/missing.sql, which does not exist." in found


def test_the_file_reads_as_plain_yaml_with_one_list_of_questions():
    raw = yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())

    assert list(raw) == ["questions"]
    assert [question["id"] for question in benchmark.load()] == [question["id"] for question in raw["questions"]]


# ── Scoring an answer through the answer contract (seam 3) ───────────────
#
# The full gate asks each question of the live Foundry agent through /api/ask. Here a stand-in agent plays the
# agent's part: it calls the question's tool with arguments, then writes one sentence citing what came back, so
# these tests drive the same route, stream, verifier and scoring the full gate does, with the tools on the fixture.

import pytest  # noqa: E402
from stand_in_agent import Agrees, StandIn  # noqa: E402

from strata.evals import answer_benchmark  # noqa: E402
from strata.server.engines import duckdb_file  # noqa: E402


def question(qid: str) -> dict:
    return next(item for item in benchmark.load() if item["id"] == qid)


@pytest.fixture(scope="module")
def engine_for(fixture_db):
    return duckdb_file(fixture_db)


def ask(engine_for, items: list[dict], answers: dict[str, StandIn]):
    agents = {item["question"]: answers[item["id"]] for item in items}
    return answer_benchmark.run(items, lambda turn: agents[turn.question], engine_for, judge=Agrees())


def test_a_question_whose_tool_gave_the_expected_answer_and_whose_answer_cites_it_passes(engine_for):
    plan, search = question("check-plan-nwwda-2026-10-09"), question("search-passages-icr-rebidding")

    results = ask(engine_for, [plan, search], {
        plan["id"]: StandIn("check_plan", plan["arguments"]),
        search["id"]: StandIn("search_passages", search["arguments"])})

    assert [(scored.id, scored.kind, scored.passed, scored.problems) for _, scored in results] == [
        (plan["id"], "sql", True, ()), (search["id"], "documents", True, ())]


def test_a_tool_called_with_the_wrong_arguments_fails_and_says_so(engine_for):
    plan = question("check-plan-nwwda-2026-10-09")

    [(_, scored)] = ask(engine_for, [plan], {plan["id"]: StandIn("check_plan", {**plan["arguments"],
                                                                               "plan_date": "2025-07-21"})})

    assert not scored.passed
    assert scored.problems[0].startswith("No call of check_plan gave the expected answer.")


def test_a_documents_answer_that_does_not_cite_the_expected_passage_fails(engine_for):
    search = question("search-passages-icr-rebidding")

    [(_, scored)] = ask(engine_for, [search], {search["id"]: StandIn("search_passages", search["arguments"],
                                                                     cite=(2,))})

    assert scored.problems == ("Its kept sentences do not cite strata.gold.passage:31525018/v1/54.",)


def test_a_must_refuse_question_passes_only_when_refused_with_its_key(engine_for):
    refuse = question("refuse-supplier-scores")

    [(_, held)] = ask(engine_for, [refuse], {refuse["id"]: StandIn(refuse="supplier_scores")})
    [(_, other)] = ask(engine_for, [refuse], {refuse["id"]: StandIn(refuse="live_tenders")})

    assert (held.kind, held.passed) == ("refusals", True)
    assert not other.passed and "supplier_scores" in other.problems[0]


def test_a_genie_question_passes_when_genie_s_rows_equal_its_ground_truth_on_the_same_data(engine_for):
    genie = question("genie-joint-venture-1624689")
    words = genie["arguments"]["question"]

    [(asked, right)] = ask(engine_for, [genie], {genie["id"]: StandIn("ask_genie", {"question": words})})
    [(_, wrong)] = ask(engine_for, [genie], {genie["id"]: StandIn(
        "ask_genie", {"question": question("genie-contract-ke-nwwda-229129")["arguments"]["question"]})})

    assert right.passed, right.problems
    assert asked.reference == {"rows": [["503708", "697972.33"], ["503711", "697972.33"]]}
    assert not wrong.passed and wrong.problems[0].startswith("No call of ask_genie gave the expected answer.")


def test_a_step_reference_the_tool_does_not_know_fails_the_question_without_stopping_the_run(engine_for):
    """A live model may mistype a STEP reference. find_comparables and estimate_time then answer unknown_package with
    no counts and no step dates, and the question fails, naming why, while the run goes on."""
    nope = "KE-NOPE-000000-CW-RFB"
    comparables, estimate = question("find-comparables-ke-nwwda-541055"), question("estimate-time-ke-nwwda-541055")

    results = ask(engine_for, [comparables, estimate], {
        comparables["id"]: StandIn("find_comparables", {**comparables["arguments"], "step_reference": nope}),
        estimate["id"]: StandIn("estimate_time", {**estimate["arguments"], "step_reference": nope})})

    assert [(scored.id, scored.passed) for _, scored in results] == [(comparables["id"], False),
                                                                      (estimate["id"], False)]
    for _, scored in results:
        assert any(problem.startswith("No call of ") for problem in scored.problems), scored.problems


def test_a_question_whose_own_arguments_the_tool_refuses_fails_and_the_next_question_is_still_asked(engine_for):
    plan = question("check-plan-nwwda-2026-10-09")
    typo = {**plan, "id": "check-plan-with-a-typo", "arguments": {**plan["arguments"], "plan_dated": "2026-10-09"}}

    results = ask(engine_for, [typo, plan], {typo["id"]: StandIn("check_plan", plan["arguments"]),
                                             plan["id"]: StandIn("check_plan", plan["arguments"])})

    [(_, broken), (_, fine)] = results
    assert (broken.id, broken.passed) == ("check-plan-with-a-typo", False)
    assert broken.problems[0].startswith("I could not work out the expected answer with the question's own "
                                         "arguments: "), broken.problems
    assert (fine.id, fine.passed) == (plan["id"], True)


def test_a_question_that_cannot_be_scored_fails_and_the_next_question_is_still_asked(engine_for):
    """A must-refuse question written with no refusal key cannot be scored. It fails, naming why, and the answers
    already asked and the questions after it are kept."""
    refuse = question("refuse-supplier-scores")
    unscorable = {**refuse, "id": "refuse-with-no-key", "expected": {}}

    results = ask(engine_for, [unscorable, refuse], {unscorable["id"]: StandIn(refuse="supplier_scores"),
                                                     refuse["id"]: StandIn(refuse="supplier_scores")})

    [(_, broken), (_, fine)] = results
    assert (broken.id, broken.passed) == ("refuse-with-no-key", False)
    assert broken.problems == ("I could not score it: KeyError: 'refusal'",)
    assert (fine.id, fine.passed) == (refuse["id"], True)


def test_a_tool_result_the_reader_cannot_read_fails_the_question_and_names_the_error():
    from strata.evals import scoring

    plan = question("check-plan-nwwda-2026-10-09")
    sentence = ("sentence", {"text": "A kept sentence.", "evidence_ids": ["strata.gold.package:X"]})
    odd = {"tool": "check_plan", "arguments": plan["arguments"], "result": {"rows": [{"activity_reference_no": "X"}]}}

    scored = scoring.score(scoring.Asked(plan, [sentence], "", [odd], {"unmarked": []}))

    assert not scored.passed
    assert "the agent's calls gave [{'error': \"KeyError: 'marks'\"}]" in scored.problems[0]


def test_a_genie_answer_with_its_columns_in_another_order_is_the_same_answer():
    from strata.evals import answers

    genie = question("genie-joint-venture-1624689")
    swapped = {"rows": [{"values": {"supplier_contract_amount_usd": "697972.33", "supplier_id": supplier}}
                        for supplier in ("503711", "503708")]}

    assert answers.answered(swapped, genie) == answers.expected(genie)


def test_a_documents_question_with_no_expected_citations_is_named():
    questions = benchmark.load() + [{"id": "uncited", "kind": "documents", "tool": "search_passages",
                                     "question": "What did the report say?", "arguments": {}, "expected": {}}]

    assert benchmark.problems(questions) == ["uncited is a documents question, so it needs cites: the evidence ids "
                                             "its answer must cite."]


def test_a_documents_answer_that_cites_its_notices_passes_through_the_route(engine_for):
    """Each documents question's cites are ids its tool returns: a notice's reason row, or a requirement passage
    inside a criteria row, which the verifier keeps as returned this turn."""
    import stand_in_agent

    items = [question("rejected-bids-ke-nwwda-541055"), question("compare-criteria-ke-cwsb-224323")]
    with engine_for(answer_benchmark.GATE) as engine:
        agents = {item["id"]: stand_in_agent.for_question(item, engine, answer_benchmark.GATE) for item in items}

    results = ask(engine_for, items, agents)

    assert [(scored.id, scored.passed, scored.problems) for _, scored in results] == [
        (item["id"], True, ()) for item in items]
