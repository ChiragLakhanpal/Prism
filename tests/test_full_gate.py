"""The full gate (ticket 33; docs/PLAN.md section 10; spec, "The gates use the seams as follows").

The full gate runs the offline gate, the Genie benchmark, the benchmark through the answer contract with the live
agent, and Foundry evaluations, then writes every result to strata.ops.evaluation_result under one run id and fails,
naming the gap, when a target is missed. Each live stage is a workspace step (docs/workspace-catchup.md); here
each one runs against the fixture or a fake that answers in the shape the live service documents.
"""

import datetime as dt
import json
import shutil
from pathlib import Path

import pytest
import stand_in_agent

from strata.config import load_evaluations, load_thresholds
from strata.evals import answer_benchmark, benchmark, foundry_evaluation, full_gate, genie_benchmark, results
from strata.evals.scoring import Asked, Scored
from strata.genie import fixture as genie_fixture
from strata.genie import space as genie_space
from strata.genie.client import Answer, GenieClient, Waits
from strata.lakehouse.engine import DuckDBEngine
from strata.server.engines import duckdb_file

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = load_thresholds()
RAN_AT = dt.datetime(2026, 10, 25, 6, 30, tzinfo=dt.UTC)
EVALUATION_RESULT = ROOT / "src" / "strata" / "lakehouse" / "tables" / "ops" / "evaluation_result.sql"


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as opened:
        yield opened


@pytest.fixture
def store():
    """strata.ops.evaluation_result, made from its one definition, in a database of its own."""
    with DuckDBEngine.open() as opened:
        opened.run("CREATE SCHEMA IF NOT EXISTS strata.ops")
        opened.run(EVALUATION_RESULT.read_text())
        yield opened


def stored(store, scorer=None) -> list[dict]:
    result = store.run("SELECT run_id, scorer, model, segment_kind, segment, measure, value, value_text, public_from "
                       "FROM strata.ops.evaluation_result ORDER BY scorer, segment_kind, segment, measure")
    found = [dict(zip(result.columns, row, strict=True)) for row in result.rows]
    return [row for row in found if scorer is None or row["scorer"] == scorer]


def measures(rows, segment_kind, segment) -> dict:
    return {row["measure"]: row["value"] if row["value"] is not None else row["value_text"] for row in rows
            if row["segment_kind"] == segment_kind and row["segment"] == segment}


# ── The Genie benchmark ──────────────────────────────────────────────────

def fixture_genie(engine) -> GenieClient:
    space = genie_space.load()
    return GenieClient(genie_fixture.FixtureGenie(engine, space.benchmarks), genie_fixture.SPACE,
                       genie_fixture.WAREHOUSE, Waits.from_thresholds(THRESHOLDS))


def test_each_genie_question_passes_when_genie_s_rows_equal_its_ground_truth(engine):
    scored = genie_benchmark.run(fixture_genie(engine), engine, genie_space.load().benchmarks)

    assert [(item.id, item.kind, item.passed) for item in scored] == [
        (item.id, "genie", True) for item in genie_space.load().benchmarks]


class Genie:
    """A Genie that answers with the rows it is given, as text cells typed by their columns."""

    def __init__(self, rows, columns=(("supplier_id", "STRING"), ("share", "DECIMAL"))):
        self.rows, self.columns = rows, list(columns)

    def ask(self, question):
        return Answer("conversation", "message", "SELECT 1", self.columns, self.rows)


@pytest.mark.parametrize("rows", [
    [["503708", "697972.3"], ["503711", "697972.33"]],     # one amount rounded to fewer cents
    [["503708", "69797233"], ["503711", "69797233"]],      # amounts multiplied by 100, as a percentage would be
    [["503708", "697972.33"]],                             # a row short
], ids=["rounded", "times-100", "a-row-short"])
def test_genie_s_rows_must_match_at_the_same_rounding_never_roughly(engine, rows):
    """fairshare's runner passed a row that shared half its numbers within 0.6, which let a percentage multiplied by
    100 through (fairshare's docs/limits.md, October 14). CLAUDE.md rule 1 needs every number at the tool's
    rounding."""
    from decimal import Decimal

    [item] = [item for item in genie_space.load().benchmarks if item.id == "genie-joint-venture-1624689"]
    typed = [[cells[0], Decimal(cells[1])] for cells in rows]

    [scored] = genie_benchmark.run(Genie(typed), engine, [item])
    [right] = genie_benchmark.run(Genie([["503711", Decimal("697972.330")], ["503708", Decimal("697972.33")]]),
                                  engine, [item])

    assert not scored.passed
    assert scored.problems[0].startswith("Genie's rows differ from its ground truth at the same rounding.")
    assert right.passed  # the same rows in another order and with a trailing zero are the same answer


def test_genie_s_columns_may_come_in_another_order_but_every_value_must_still_match(engine):
    """Genie names and orders its columns its own way; the rows must hold the same values at the same rounding."""
    from decimal import Decimal

    [item] = [item for item in genie_space.load().benchmarks if item.id == "genie-joint-venture-1624689"]
    swapped = (("supplier_contract_amount_usd", "DECIMAL"), ("supplier_id", "STRING"))

    [right] = genie_benchmark.run(Genie([[Decimal("697972.33"), "503708"], [Decimal("697972.33"), "503711"]],
                                        swapped), engine, [item])
    [wrong] = genie_benchmark.run(Genie([[Decimal("697972.33"), "503708"], [Decimal("697972.30"), "503711"]],
                                        swapped), engine, [item])

    assert right.passed, right.problems
    assert not wrong.passed


class Refused:
    """A Genie whose workspace refused the question, as a 403 or a 500 from Genie's API comes back."""

    def ask(self, question):
        from strata.lakehouse.engine import EngineError

        raise EngineError("The workspace answered 403 to POST /api/2.0/genie/spaces/space-1/start-conversation.")


def test_a_genie_question_whose_ground_truth_or_genie_call_fails_fails_alone(engine):
    """One question's ground-truth SQL that does not run, or a workspace error from Genie, fails that question and
    names why. The other questions are still asked and scored."""
    import dataclasses

    good = next(item for item in genie_space.load().benchmarks if item.id == "genie-joint-venture-1624689")
    broken = dataclasses.replace(good, id="genie-with-broken-sql",
                                 case=dataclasses.replace(good.case, sql="SELECT * FROM strata.gold.no_such_table"))

    by_truth = genie_benchmark.run(fixture_genie(engine), engine, [broken, good])
    by_genie = genie_benchmark.run(Refused(), engine, [good])

    assert [(item.id, item.passed) for item in by_truth] == [("genie-with-broken-sql", False), (good.id, True)]
    assert by_truth[0].problems[0].startswith("Its ground-truth SQL did not run on this engine: "), by_truth[0]
    assert [(item.id, item.passed) for item in by_genie] == [(good.id, False)]
    assert by_genie[0].problems[0].startswith("Genie gave no answer (engine_error): The workspace answered 403")


# ── Foundry evaluations ──────────────────────────────────────────────────

def answer_of(question: dict, sentences: list[dict], evidence: list[dict], calls: list[dict]) -> Asked:
    events = [("sentence", sentence) for sentence in sentences] + [("evidence", item) for item in evidence]
    return Asked(question, events, "", calls, None)


ICR_54 = {"id": "strata.gold.passage:31525018/v1/54", "kind": "passage",
          "row": {"evidence_id": "strata.gold.passage:31525018/v1/54",
                  "text": "108 of 328 cases had to go through rebidding."}}


def test_the_dataset_holds_each_answer_with_its_cited_sources_its_tool_calls_and_the_tools_offered():
    search = next(item for item in benchmark.load() if item["id"] == "search-passages-icr-rebidding")
    refusal = next(item for item in benchmark.load() if item["kind"] == "refusals")
    answered = answer_of(search, [{"text": "The report says 108 of 328 cases went through rebidding.",
                                   "evidence_ids": [ICR_54["id"]]}], [ICR_54],
                         [{"tool": "search_passages", "arguments": search["arguments"], "result": {}}])
    refused = answer_of(refusal, [], [], [])

    [item] = foundry_evaluation.dataset([answered, refused])

    assert item["query"] == search["question"]
    assert item["response"] == "The report says 108 of 328 cases went through rebidding."
    assert item["context"] == f"[{ICR_54['id']}] 108 of 328 cases had to go through rebidding."
    assert item["tool_calls"] == [{"type": "tool_call", "tool_call_id": "call_1", "name": "search_passages",
                                   "arguments": search["arguments"]}]
    assert "search_passages" in [tool["name"] for tool in item["tool_definitions"]]
    assert set(item) == set(foundry_evaluation.ITEM_SCHEMA["properties"])


class FakeFoundry:
    """Foundry's evaluations API in memory, in the shape its documentation gives. Each criterion scores every item
    4, and passes it unless the evaluator is one of the failing ones."""

    def __init__(self, failing=(), unscored=()):
        self.failing, self.unscored, self.evals, self.runs, self.polls = set(failing), set(unscored), {}, {}, 0

    def create_eval(self, body):
        self.evals["eval-1"] = body
        return {"id": "eval-1"}

    def create_run(self, eval_id, body):
        self.runs["run-1"] = body
        return {"id": "run-1", "status": "queued"}

    def get_run(self, eval_id, run_id):
        self.polls += 1
        return {"id": run_id, "status": "completed" if self.polls > 1 else "in_progress"}

    def output_items(self, eval_id, run_id):
        items = self.runs[run_id]["data_source"]["source"]["content"]
        criteria = [criterion["name"] for criterion in self.evals[eval_id]["testing_criteria"]]
        return [{"id": f"item-{n}", "results": [{"name": name, "type": "azure_ai_evaluator", "score": 2 if
                                                 name in self.failing else 4, "passed": name not in self.failing}
                                                for name in criteria if name not in self.unscored]}
                for n, _ in enumerate(items)]


def test_foundry_scores_each_evaluator_from_a_custom_dataset_with_the_judge_s_deployment():
    foundry = FakeFoundry(failing=["tool_use"])
    items = [{"query": "q", "response": "r", "context": "", "tool_calls": [], "tool_definitions": []}] * 3

    run = foundry_evaluation.evaluate(foundry, items, load_evaluations(), "gpt-5.4", "full_gate-test",
                                      poll_seconds=0, wait_seconds=60, sleep=lambda seconds: None)

    created = foundry.evals["eval-1"]
    assert created["data_source_config"] == {"type": "custom", "item_schema": foundry_evaluation.ITEM_SCHEMA,
                                             "include_sample_schema": False}
    assert [(c["type"], c["name"], c["evaluator_name"], c["initialization_parameters"]["deployment_name"])
            for c in created["testing_criteria"]] == [
        ("azure_ai_evaluator", "groundedness", "builtin.groundedness", "gpt-5.4"),
        ("azure_ai_evaluator", "relevance", "builtin.relevance", "gpt-5.4"),
        ("azure_ai_evaluator", "task_adherence", "builtin.task_adherence", "gpt-5.4"),
        ("azure_ai_evaluator", "tool_use", "builtin.tool_call_accuracy", "gpt-5.4")]
    assert [item["item"] for item in foundry.runs["run-1"]["data_source"]["source"]["content"]] == items
    assert [(score.key, score.scored, score.met, score.mean) for score in run.scores] == [
        ("groundedness", 3, 3, 4.0), ("relevance", 3, 3, 4.0), ("task_adherence", 3, 3, 4.0), ("tool_use", 3, 0, 2.0)]
    assert (run.eval_id, run.run_id) == ("eval-1", "run-1")


# ── The full gate, end to end ────────────────────────────────────────────

def scored_all(questions, failing=()) -> list[tuple[Asked, Scored]]:
    """An answer stage that passes every question it is given but the failing ones."""
    return [(Asked(question, [("sentence", {"text": "A kept sentence.", "evidence_ids": []})], "", [], None),
             Scored(question["id"], question["kind"], question["id"] not in failing,
                    ("It did not cite what it should.",) if question["id"] in failing else ()))
            for question in questions]


def stages(engine, answers=None, foundry=None, offline=0) -> full_gate.Stages:
    return full_gate.Stages(
        offline_gate=lambda: offline,
        genie=lambda: genie_benchmark.run(fixture_genie(engine), engine, genie_space.load().benchmarks),
        answers=answers or (lambda questions: scored_all(questions)),
        foundry=(lambda items: foundry_evaluation.evaluate(
            foundry or FakeFoundry(), items, load_evaluations(), "gpt-5.4", "full_gate", poll_seconds=0,
            wait_seconds=60, sleep=lambda seconds: None)))


def test_the_full_gate_runs_end_to_end_and_writes_every_result_under_one_run_id(engine, store):
    said = []

    report = full_gate.run(benchmark.load(), stages(engine), store, now=lambda: RAN_AT, say=said.append)

    assert report.exit_code == 0 and report.missed == []
    rows = stored(store)
    assert {row["run_id"] for row in rows} == {report.run_id}
    assert report.run_id.startswith("full_gate-20261025T063000Z-")
    assert {row["public_from"] for row in rows} == {dt.date(2026, 10, 25)}
    # The answer benchmark, per kind as the dashboard reads it (the 45 brief, tile 13): passed, asked, the target
    # and the gap.
    answers = stored(store, "benchmark")
    asked = benchmark.counts(benchmark.load())
    assert measures(answers, "kind", "sql") == {"questions": asked["sql"], "passed": asked["sql"], "share": 1.0,
                                                "target": 0.9, "gap": 0.0, "met": 1.0}
    assert measures(answers, "kind", "must_refuse")["questions"] == asked["refusals"]
    assert measures(answers, "kind", "all")["questions"] == len(benchmark.load())
    assert measures(answers, "question", "check-plan-nwwda-2026-10-09") == {"passed": 1.0, "kind": "sql"}
    # The Genie benchmark's pass rate (criterion 1), and each Foundry evaluator's scores (criterion 6).
    genie = stored(store, "genie_benchmark")
    assert measures(genie, "kind", "all") == {"questions": 5.0, "passed": 5.0, "share": 1.0, "target": 0.8,
                                              "gap": 0.0, "met": 1.0}
    foundry = stored(store, "foundry_evaluation")
    assert {row["segment"] for row in foundry if row["segment_kind"] == "evaluator"} == {
        "groundedness", "relevance", "task_adherence", "tool_use"}
    assert measures(foundry, "evaluator", "tool_use") == {
        "scored": float(len(foundry_evaluation.dataset([answer for answer, _ in scored_all(benchmark.load())]))), "met": measures(
            foundry, "evaluator", "tool_use")["scored"], "share": 1.0, "mean_score": 4.0, "target": 0.8, "gap": 0.0,
        "met_target": 1.0, "foundry_run": "eval-1/run-1"}
    assert {row["model"] for row in foundry} == {"gpt-5.4"}
    assert measures(stored(store, "full_gate"), "stage", "offline_gate") == {"passed": 1.0}


def test_a_missed_target_fails_the_full_gate_and_names_the_gap(engine, store):
    sql = [question["id"] for question in benchmark.load() if question["kind"] == "sql"]
    said = []

    report = full_gate.run(benchmark.load(), stages(engine, answers=lambda questions: scored_all(questions, sql[:2]),
                                                    foundry=FakeFoundry(failing=["groundedness"])),
                           store, now=lambda: RAN_AT, say=said.append)

    assert report.exit_code == 1
    total = len(sql)
    assert report.missed == [
        f"SQL missed its target: {total - 2} of {total} questions passed ({round(100 * (total - 2) / total)}%), "
        f"against a target of 90%, a gap of {round(100 * (0.9 - (total - 2) / total))} points.",
        "Groundedness missed its target: 0 of " + str(len(foundry_evaluation.dataset([answer for answer, _ in scored_all(benchmark.load())])))
        + " answers met Foundry's threshold (0%), against a target of 80%, a gap of 80 points."]
    assert said[-len(report.missed):] == report.missed
    assert measures(stored(store, "benchmark"), "kind", "sql")["met"] == 0.0
    assert measures(stored(store, "benchmark"), "question", sql[0])["problems"] == json.dumps(
        ["It did not cite what it should."])


def test_a_failing_offline_gate_stops_the_full_gate_before_anything_live(engine, store):
    asked = []

    report = full_gate.run(benchmark.load(), stages(engine, answers=lambda questions: asked.append(questions) or [],
                                                    offline=1), store, now=lambda: RAN_AT, say=lambda line: None)

    assert (report.exit_code, asked) == (1, [])
    assert report.missed == ["The offline gate failed, so I ran nothing live. Run .githooks/pre-commit and fix "
                             "what it reports."]
    assert measures(stored(store, "full_gate"), "stage", "offline_gate") == {"passed": 0.0}


def test_a_benchmark_file_that_lacks_a_question_stops_the_full_gate_naming_it(engine, store, tmp_path):
    questions = [question for question in benchmark.load() if question["id"] != "refuse-wrong-edition"]

    report = full_gate.run(questions, stages(engine), store, now=lambda: RAN_AT, say=lambda line: None)

    assert report.exit_code == 2
    assert report.missed == ["The refusal wrong_edition has no must-refuse question."]
    assert stored(store) == []


def asked_documents(questions) -> int:
    return sum(question["kind"] == "documents" for question in questions)


def test_a_question_added_to_the_benchmark_file_runs_in_the_next_full_gate_with_no_other_change(
        engine, store, tmp_path, fixture_db):
    """Criterion 7: the full gate reads the file as it is, hands every question in it to the answer stage, and the
    new one is asked through /api/ask with the stand-in agent, scored and stored under the run id. The other
    questions are scored by scored_all here only to keep the test short; the live command asks all of them through
    answer_benchmark.run (ops/evals/full_gate.py), as tests/test_benchmark.py does for each kind."""
    target = tmp_path / "benchmark.yaml"
    shutil.copy(ROOT / "evals" / "benchmark.yaml", target)
    target.write_text(target.read_text() + """
  - id: search-passages-icr-review-clearances
    kind: documents
    tool: search_passages
    question: What lesson did IEG draw about clearances in its review of the P130164 completion report?
    arguments:
      query: IEG lesson clearances before awarding contracts
      project_id: P130164
      document_type: ICR Review
      as_of: "2026-10-23"
    expected:
      top_three_include: [strata.gold.passage:34056616/v2/12]
    cites: [strata.gold.passage:34056616/v2/12]
    source: tests/ground_truth/values.toml, icr-review-2023-ieg-lesson.
""")
    questions = benchmark.load(target)
    new = questions[-1]["id"]
    engine_for, viewer = duckdb_file(fixture_db), answer_benchmark.GATE
    agent = stand_in_agent.for_question(questions[-1], engine, viewer)
    asked = []

    def answers(given):
        asked.extend(question["id"] for question in given)
        through_the_route = answer_benchmark.run([question for question in given if question["id"] == new],
                                                 lambda turn: agent, engine_for, judge=stand_in_agent.Agrees())
        return scored_all([question for question in given if question["id"] != new]) + through_the_route

    report = full_gate.run(questions, stages(engine, answers=answers), store, now=lambda: RAN_AT,
                           say=lambda line: None)

    assert asked == [question["id"] for question in questions] and asked[-1] == new
    assert measures(stored(store, "benchmark"), "question", new) == {"passed": 1.0, "kind": "documents"}
    assert measures(stored(store, "benchmark"), "kind", "documents")["questions"] == asked_documents(questions)
    assert {row["run_id"] for row in stored(store)} == {report.run_id}


# ── The command ──────────────────────────────────────────────────────────

def load_command():
    import importlib.util

    spec = importlib.util.spec_from_file_location("full_gate_command", ROOT / "ops" / "evals" / "full_gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_command_needs_the_workspace_and_foundry_keys_from_the_env_file(tmp_path, capsys):
    command = load_command()
    env = tmp_path / "env-file"
    env.write_text("DATABRICKS_HOST='https://example.cloud.databricks.com'\n")

    assert command.main(["--env-file", str(env)]) == 2
    assert ("has no value for DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID, FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_TENANT_ID, "
            "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY" in capsys.readouterr().out)


# A complete env file, with fake values.
COMPLETE_ENV = {"DATABRICKS_HOST": "https://example.cloud.databricks.com", "DATABRICKS_TOKEN": "not-a-real-key",
                "DATABRICKS_WAREHOUSE_ID": "wh-1", "FOUNDRY_PROJECT_ENDPOINT": "https://example.services.ai.azure.com",
                "FOUNDRY_TENANT_ID": "tenant", "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "not-a-real-key", "GENIE_SPACE_ID": "01f0aaaabbbbccccddddeeeeffff0000"}


def test_the_command_gives_the_tools_their_settings_from_the_env_file(tmp_path, monkeypatch):
    """ask_genie and search_passages read the workspace, the Genie space and Azure OpenAI from the process
    environment, as the App's app.yaml gives them. The command loads them from the env file, so it puts them there
    for the run, overwriting what was set, so ask_genie asks the same space as the Genie benchmark."""
    import os

    command = load_command()
    for key in command.TOOL_SETTINGS:
        monkeypatch.setenv(key, "set before the run")  # monkeypatch puts each one back after the test
    env = tmp_path / "env-file"
    env.write_text("".join(f"{key}='{value}'\n" for key, value in COMPLETE_ENV.items()))
    seen = {}

    def fake(given):
        seen.update({key: os.environ[key] for key in command.TOOL_SETTINGS})
        return full_gate.Stages(offline_gate=lambda: 1, answers=lambda questions: []), None

    monkeypatch.setattr(command, "stages_for", fake)

    assert command.main(["--env-file", str(env)]) == 1
    assert seen == {"DATABRICKS_HOST": "https://example.cloud.databricks.com",
                    "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
                    "AZURE_OPENAI_API_KEY": "not-a-real-key", "GENIE_SPACE_ID": "01f0aaaabbbbccccddddeeeeffff0000"}


def test_the_command_asks_each_question_as_a_viewer_that_carries_the_env_file_s_token(monkeypatch):
    command = load_command()
    captured = {}

    def capture(questions, agent_for, engine_for, judge=None, restricted=(), viewer=answer_benchmark.GATE):
        captured["viewer"] = viewer
        return []

    monkeypatch.setattr(answer_benchmark, "run", capture)
    command.stages_for(COMPLETE_ENV)[0].answers([])

    assert captured["viewer"].token == "not-a-real-key"
    assert (captured["viewer"].email, captured["viewer"].user_id) == ("full-gate@strata", "full-gate@strata")


def test_the_command_asks_genie_only_when_the_env_file_names_a_space():
    command = load_command()
    env = {"DATABRICKS_HOST": "https://example.cloud.databricks.com", "DATABRICKS_TOKEN": "not-a-real-key",
           "DATABRICKS_WAREHOUSE_ID": "wh-1", "FOUNDRY_PROJECT_ENDPOINT": "https://example.services.ai.azure.com",
           "FOUNDRY_TENANT_ID": "tenant"}

    without, store = command.stages_for(env)
    with_space, _ = command.stages_for({**env, "GENIE_SPACE_ID": "01f0aaaabbbbccccddddeeeeffff0000"})

    assert without.genie is None and callable(with_space.genie)
    assert (store.name, store.warehouse_id) == ("databricks", "wh-1")


def test_a_live_stage_that_cannot_run_fails_the_gate_naming_it_and_the_rest_is_still_stored(engine, store):
    from strata.evals.foundry_evaluation import EvaluationError

    def no_foundry(items):
        raise EvaluationError("Foundry did not finish evaluation run run-1 within 1800 seconds.")

    broken = stages(engine)
    broken.foundry = no_foundry

    report = full_gate.run(benchmark.load(), broken, store, now=lambda: RAN_AT, say=lambda line: None)

    assert report.exit_code == 1
    assert report.missed == ["Foundry evaluations could not run: Foundry did not finish evaluation run run-1 "
                             "within 1800 seconds."]
    assert measures(stored(store, "full_gate"), "stage", "foundry_evaluation") == {"ran": 0.0}
    assert measures(stored(store, "benchmark"), "kind", "all")["questions"] == len(benchmark.load())


def test_an_answer_stage_that_stops_fails_the_gate_naming_it_and_the_genie_results_are_still_stored(engine, store):
    def stopped(questions):
        raise TimeoutError("The answer stage timed out after 600 seconds.")

    report = full_gate.run(benchmark.load(), stages(engine, answers=stopped), store, now=lambda: RAN_AT,
                           say=lambda line: None)

    assert report.exit_code == 1
    assert report.missed[0] == ("The benchmark through the answer contract could not run: The answer stage timed "
                                "out after 600 seconds.")
    assert measures(stored(store, "full_gate"), "stage", "answer_benchmark") == {"ran": 0.0}
    assert measures(stored(store, "genie_benchmark"), "kind", "all")["passed"] == 5.0


def test_an_evaluator_foundry_scored_for_no_answer_fails_the_gate_and_is_stored_as_scoring_none(engine, store):
    """config/evaluations.toml says tool use's built-in name and mapping have not been run yet. When Foundry
    scores no answer with it, the gate says so instead of passing without its score."""
    report = full_gate.run(benchmark.load(), stages(engine, foundry=FakeFoundry(unscored=["tool_use"])), store,
                           now=lambda: RAN_AT, say=lambda line: None)

    assert report.exit_code == 1
    assert report.missed == ["Tool use scored no answers in Foundry run eval-1/run-1."]
    tool_use = measures(stored(store, "foundry_evaluation"), "evaluator", "tool_use")
    assert tool_use == {"scored": 0.0, "foundry_run": "eval-1/run-1"}
    assert measures(stored(store, "foundry_evaluation"), "evaluator", "groundedness")["met_target"] == 1.0


def test_with_no_genie_space_the_gate_fails_naming_the_missing_space_id(engine, store):
    no_space = stages(engine)
    no_space.genie = None

    report = full_gate.run(benchmark.load(), no_space, store, now=lambda: RAN_AT, say=lambda line: None)

    assert (report.exit_code, report.missed) == (1, [full_gate.NO_GENIE_SPACE])
    assert full_gate.NO_GENIE_SPACE == "The Genie benchmark did not run: the env file has no GENIE_SPACE_ID."
    assert measures(stored(store, "full_gate"), "stage", "genie_benchmark") == {"ran": 0.0}


def test_each_evaluator_maps_the_item_fields_foundry_requires():
    # Foundry refused the full gate's run of November 1, 2026 (EvalValidationFailed): the items carry tool_definitions,
    # which groundedness accepts, and response, which tool call accuracy accepts, and neither mapping named them.
    mappings = {evaluator.builtin: evaluator.data_mapping for evaluator in load_evaluations().evaluators}
    assert mappings["builtin.groundedness"]["tool_definitions"] == "{{item.tool_definitions}}"
    assert mappings["builtin.tool_call_accuracy"]["response"] == "{{item.response}}"
