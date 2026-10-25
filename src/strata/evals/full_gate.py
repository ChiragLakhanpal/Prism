"""The full gate (ticket 33; docs/PLAN.md section 10; spec, "The gates use the seams as follows").

run() is the full gate: one command, ops/evals/full_gate.py, runs it on the workspace. In order:

1. It checks the benchmark file (strata.evals.benchmark.problems): a registry tool with no question, a refusal key
   with none, or too few questions of a kind stops it before anything runs, naming what is missing.
2. It runs the offline gate. When that fails, nothing live runs.
3. The Genie benchmark: each Genie question through the live space, against its ground-truth SQL on the SQL
   warehouse (strata.evals.genie_benchmark).
4. The benchmark through the answer contract: every question in the file through /api/ask with the live agent and
   the live tools (strata.evals.answer_benchmark). A question added to the file runs here with no other change.
5. Foundry evaluations of those answers, after a Microsoft Entra sign-in (strata.evals.foundry_evaluation).
6. It writes every result to strata.ops.evaluation_result under one run id (strata.evals.results), prints each
   tally against its target, and fails, naming each gap, when a target is missed.

Each stage is passed in, so the offline tests run the whole sequence with the fixture and fakes
(tests/test_full_gate.py), and the live command passes the workspace's.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass, field

from strata.config import Thresholds, load_thresholds
from strata.estimates import harness
from strata.evals import benchmark, foundry_evaluation, results
from strata.evals.foundry_evaluation import EvaluationRun
from strata.evals.scoring import Asked, Scored
from strata.lakehouse.engine import Engine

OFFLINE_FAILED = ("The offline gate failed, so I ran nothing live. Run .githooks/pre-commit and fix what it "
                  "reports.")
NO_GENIE_SPACE = "The Genie benchmark did not run: the env file has no GENIE_SPACE_ID."


@dataclass
class Stages:
    offline_gate: Callable[[], int]
    answers: Callable[[list[dict]], list[tuple[Asked, Scored]]]
    genie: Callable[[], list[Scored]] | None = None
    foundry: Callable[[list[dict]], EvaluationRun] | None = None


@dataclass
class Report:
    run_id: str
    exit_code: int
    missed: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def run(questions: list[dict], stages: Stages, store: Engine | None, thresholds: Thresholds | None = None,
        now: Callable[[], dt.datetime] = utc_now, say: Callable[[str], None] = print) -> Report:
    limits = thresholds or load_thresholds()
    ran_at = now()
    run_id = harness.new_run_id("full_gate", ran_at)
    problems = benchmark.problems(questions)
    if problems:
        for problem in problems:
            say(problem)
        return Report(run_id, 2, problems)
    say(f"Full gate run {run_id}.")
    say("1. The offline gate.")
    if stages.offline_gate() != 0:
        written = results.stage_rows(run_id, ran_at, {"offline_gate": ("passed", False)})
        if store is not None:
            results.write(store, written)
        say(OFFLINE_FAILED)
        return Report(run_id, 1, [OFFLINE_FAILED], written)
    failed: list[str] = []

    def attempt(name: str, stage: Callable[[], object]):
        """A live stage, or None with a sentence for the report when it could not run: the stages that did run
        are still stored, and the gate fails naming the one that did not."""
        try:
            return stage()
        except Exception as error:  # a timeout, a refused sign-in or a service that is down
            failed.append(f"{name} could not run: {error}")
            say(f"   {failed[-1]}")
            return None

    say("2. The Genie benchmark.")
    genie = attempt("The Genie benchmark", stages.genie) if stages.genie else None
    if stages.genie is None:
        failed.append(NO_GENIE_SPACE)
        say(f"   {NO_GENIE_SPACE} The space deploy, ops/genie/deploy_space.py, adds it.")
    say("3. The benchmark through the answer contract.")
    answered = attempt("The benchmark through the answer contract", lambda: stages.answers(questions))
    asked = answered or []
    say("4. Foundry evaluations.")
    items = foundry_evaluation.dataset([answer for answer, _ in asked])
    if stages.foundry and items:
        evaluation = attempt("Foundry evaluations", lambda: stages.foundry(items))
    else:
        evaluation = None
        say("   Foundry evaluated nothing: no Foundry project was given, or no answer kept a sentence.")
    for score in foundry_evaluation.unscored(evaluation):
        failed.append(f"{score.label} scored no answers in Foundry run {evaluation.eval_id}/{evaluation.run_id}.")
        say(f"   {failed[-1]}")
    scored = [score for _, score in asked]
    found = results.tallies(scored, genie, evaluation, limits)
    stages_run = {"offline_gate": ("passed", True), "genie_benchmark": ("ran", genie is not None),
                  "answer_benchmark": ("ran", answered is not None),
                  "foundry_evaluation": ("ran", evaluation is not None)}
    written = results.rows(run_id, ran_at, found, scored, genie, evaluation, stages_run)
    if store is not None:
        results.write(store, written)
        say(f"5. I wrote {len(written)} rows to strata.ops.evaluation_result under the run id {run_id}.")
    for tally in found:
        say(f"   {results.said(tally)}")
    for item in [*scored, *(genie or [])]:
        if not item.passed:
            say(f"   {item.id} did not pass. {' '.join(item.problems)}")
    missed = failed + results.missed(found)
    for line in missed:
        say(line)
    return Report(run_id, 1 if missed else 0, missed, written)
