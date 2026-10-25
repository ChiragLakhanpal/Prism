"""The Genie benchmark (ticket 33; docs/PLAN.md section 10, "A full gate adds the Genie benchmark").

Each of the Genie space's benchmark questions (the benchmark file's ask_genie questions) is asked of the space
through GenieClient, and its rows are compared with the rows its ground-truth SQL returns on the same data: the
fixture offline, the SQL warehouse in the full gate. A question passes only when the two hold the same rows at the
same rounding (strata.evals.answers.same_rows), in any order. That is stricter than fairshare's runner, whose
matches() passed a row that shared half its numbers within 0.6 and so let a percentage multiplied by 100 through
(fairshare's docs/limits.md, October 14, as ticket 33's notes give it): CLAUDE.md rule 1 needs every number to
match. Column names and their order are not compared, because Genie names and orders its columns its own way,
which is also why Genie's own evaluation run fails answers whose numbers agree. A column the ground truth lacks
still makes the rows differ, so each benchmark question asks for exactly the columns its ground truth returns.

The share of questions that passed is the Genie benchmark's pass rate, which the full gate stores in
strata.ops.evaluation_result.
"""

from __future__ import annotations

from strata.evals.answers import same_rows
from strata.evals.scoring import Scored
from strata.genie.client import GenieError
from strata.lakehouse.engine import Engine, EngineError

KIND = "genie"


def run(client, engine: Engine, benchmarks) -> list[Scored]:
    """Each question scored on its own: a ground truth that does not run here, or a workspace error from Genie,
    fails that question and names why, and the rest are still asked."""
    scored = []
    for item in benchmarks:
        try:
            truth = same_rows(engine.run(item.case.sql, item.case.params).rows)
        except EngineError as error:
            scored.append(Scored(item.id, KIND, False, (f"Its ground-truth SQL did not run on this engine: {error}",)))
            continue
        try:
            answer = client.ask(item.question)
        except (GenieError, EngineError) as error:
            code = getattr(error, "code", "engine_error")
            scored.append(Scored(item.id, KIND, False, (f"Genie gave no answer ({code}): {error}",)))
            continue
        if answer.sql is None:
            scored.append(Scored(item.id, KIND, False, (f"Genie wrote no query. It said: {answer.text}",)))
            continue
        found = same_rows(answer.rows)
        if found != truth:
            scored.append(Scored(item.id, KIND, False, (
                f"Genie's rows differ from its ground truth at the same rounding. Genie gave {found}; "
                f"{item.case.path.name} gives {truth}.",)))
            continue
        scored.append(Scored(item.id, KIND, True))
    return scored
