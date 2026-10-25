"""The full gate's results in strata.ops.evaluation_result, and the targets they are held to (ticket 33).

Every row of one full gate run shares its run id, one measure per row, as the replay harness writes its scores
(src/strata/estimates/harness.py), so the same table and the same readers serve both. The scorers:

- benchmark: each question (segment_kind question): passed, its kind, and the problems when it failed; and each
  kind (segment_kind kind: sql, documents, estimates, must_refuse and all): questions, passed, share, target, gap
  and met. These are what the dashboard's benchmark tiles read (the 45 brief, tiles 4, 11 and 13).
- genie_benchmark: each Genie question, and the pass rate as kind all, with its target and gap.
- foundry_evaluation: each evaluator (segment_kind evaluator): answers scored, met (Foundry's threshold), share,
  mean_score from 1 to 5, target, gap, met_target, and the Foundry run (the 45 brief, tiles 12 and 14). The model
  column names the judge's deployment. An evaluator Foundry scored for no answer has only scored, 0, and the
  Foundry run.
- full_gate: each stage (segment_kind stage) and whether it passed or ran.

Targets are config/thresholds.toml's [benchmark] targets and genie_target, and [foundry_evaluation] targets, each
a share. A tally under its target is missed, and its sentence names the gap in percentage points.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from strata.config import Thresholds
from strata.estimates import harness
from strata.evals.foundry_evaluation import EvaluationRun
from strata.evals.scoring import Scored
from strata.lakehouse.engine import Engine

BENCHMARK, GENIE, FOUNDRY, GATE = "benchmark", "genie_benchmark", "foundry_evaluation", "full_gate"
# The benchmark's kinds as the dashboard names them, with each one's segment (the 45 brief, tile 13).
KINDS = (("sql", "sql", "SQL"), ("documents", "documents", "Documents"), ("estimates", "estimates", "Estimates"),
         ("refusals", "must_refuse", "Must refuse"))


def percent(share: float) -> int:
    return int((Decimal(str(share)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Tally:
    scorer: str
    segment_kind: str
    segment: str
    label: str
    asked: int
    passed: int
    target: float
    counted: str  # what passed counts, in words: "questions passed" or "answers met Foundry's threshold"

    @property
    def share(self) -> float:
        return round(self.passed / self.asked, 4)

    @property
    def gap(self) -> float:
        return round(max(0.0, self.target - self.share), 4)

    @property
    def met(self) -> bool:
        return self.share >= self.target


def tallies(answers: list[Scored], genie: list[Scored] | None, evaluation: EvaluationRun | None,
            thresholds: Thresholds) -> list[Tally]:
    found = []
    targets = thresholds.value("benchmark.targets")
    for kind, segment, label in KINDS:
        of_kind = [scored for scored in answers if scored.kind == kind]
        if of_kind:
            found.append(Tally(BENCHMARK, "kind", segment, label, len(of_kind),
                               sum(scored.passed for scored in of_kind), float(targets[segment]), "questions passed"))
    if answers:
        found.append(Tally(BENCHMARK, "kind", "all", "All", len(answers), sum(scored.passed for scored in answers),
                           float(targets["all"]), "questions passed"))
    if genie:
        found.append(Tally(GENIE, "kind", "all", "The Genie benchmark", len(genie),
                           sum(scored.passed for scored in genie), float(thresholds.value("benchmark.genie_target")),
                           "questions passed"))
    if evaluation is not None:
        evaluator_targets = thresholds.value("foundry_evaluation.targets")
        for score in evaluation.scores:
            if score.scored:
                found.append(Tally(FOUNDRY, "evaluator", score.key, score.label, score.scored, score.met,
                                   float(evaluator_targets[score.key]), "answers met Foundry's threshold"))
    return found


def missed(found: list[Tally]) -> list[str]:
    """One sentence per missed target, naming its gap."""
    return [f"{tally.label} missed its target: {tally.passed} of {tally.asked} {tally.counted} "
            f"({percent(tally.share)}%), against a target of {percent(tally.target)}%, a gap of "
            f"{percent(tally.gap)} points." for tally in found if not tally.met]


def said(tally: Tally) -> str:
    """One line for a tally, met or not."""
    return (f"{tally.label}: {tally.passed} of {tally.asked} {tally.counted} ({percent(tally.share)}%), "
            f"target {percent(tally.target)}%, {'met' if tally.met else f'missed by {percent(tally.gap)} points'}.")


def _row(run_id: str, ran_at: dt.datetime, scorer: str, segment_kind: str, segment: str, measure: str,
         value: float | None = None, text: str | None = None, model: str | None = None) -> dict:
    return {"run_id": run_id, "scorer": scorer, "model": model, "segment_kind": segment_kind, "segment": segment,
            "measure": measure, "value": None if value is None else float(value), "value_text": text,
            "cutoff": None, "outcomes_through": None, "mlflow_run_id": None, "ran_at": ran_at,
            "public_from": ran_at.astimezone(dt.UTC).date()}


def stage_rows(run_id: str, ran_at: dt.datetime, stages: dict[str, tuple[str, bool]]) -> list[dict]:
    """Each stage of the run: the offline gate passed or not, and whether each live stage ran."""
    return [_row(run_id, ran_at, GATE, "stage", stage, measure, int(value))
            for stage, (measure, value) in stages.items()]


def question_rows(run_id: str, ran_at: dt.datetime, scorer: str, scored: list[Scored]) -> list[dict]:
    found = []
    for item in scored:
        found += [_row(run_id, ran_at, scorer, "question", item.id, "passed", int(item.passed)),
                  _row(run_id, ran_at, scorer, "question", item.id, "kind", text=item.kind)]
        if not item.passed:
            found.append(_row(run_id, ran_at, scorer, "question", item.id, "problems", text=json.dumps(
                list(item.problems))))
    return found


def rows(run_id: str, ran_at: dt.datetime, found: list[Tally], answers: list[Scored], genie: list[Scored] | None,
         evaluation: EvaluationRun | None, stages: dict[str, tuple[str, bool]]) -> list[dict]:
    written = stage_rows(run_id, ran_at, stages)
    written += question_rows(run_id, ran_at, BENCHMARK, answers)
    written += question_rows(run_id, ran_at, GENIE, genie or [])
    for tally in found:
        model = evaluation.deployment if tally.scorer == FOUNDRY and evaluation else None
        if tally.scorer == FOUNDRY:
            measures = {"scored": tally.asked, "met": tally.passed, "share": tally.share, "target": tally.target,
                        "gap": tally.gap, "met_target": int(tally.met)}
            score = next(item for item in evaluation.scores if item.key == tally.segment)
            if score.mean is not None:
                measures["mean_score"] = score.mean
        else:
            measures = {"questions": tally.asked, "passed": tally.passed, "share": tally.share,
                        "target": tally.target, "gap": tally.gap, "met": int(tally.met)}
        written += [_row(run_id, ran_at, tally.scorer, tally.segment_kind, tally.segment, measure, value, model=model)
                    for measure, value in measures.items()]
        if tally.scorer == FOUNDRY:
            written.append(_row(run_id, ran_at, FOUNDRY, "evaluator", tally.segment, "foundry_run",
                                text=f"{evaluation.eval_id}/{evaluation.run_id}", model=model))
    # An evaluator Foundry scored for no answer has no tally, and the full gate fails naming it. Its rows say it
    # ran and scored nothing, so the dashboard shows it instead of leaving it out.
    for score in evaluation.scores if evaluation is not None else ():
        if not score.scored:
            written += [_row(run_id, ran_at, FOUNDRY, "evaluator", score.key, "scored", 0, model=evaluation.deployment),
                        _row(run_id, ran_at, FOUNDRY, "evaluator", score.key, "foundry_run",
                             text=f"{evaluation.eval_id}/{evaluation.run_id}", model=evaluation.deployment)]
    return written


def write(engine: Engine, found: list[dict]) -> int:
    """Append the run's rows. Nothing is ever replaced or removed (CLAUDE.md rule 5)."""
    return harness.write(engine, found)
