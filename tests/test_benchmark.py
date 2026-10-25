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
