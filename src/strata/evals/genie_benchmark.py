"""The Genie benchmark (ticket 33; docs/PLAN.md section 10, "A full gate adds the Genie benchmark").

Each of the Genie space's benchmark questions (the benchmark file's ask_genie questions) is asked of the space
through GenieClient, and its rows are compared with the rows its ground-truth SQL returns on the same data: the
fixture offline, the SQL warehouse in the full gate. A question passes only when the two hold the same rows at the
same rounding (strata.evals.answers.same_rows), in any order. That is stricter than fairshare's runner, whose
matches() passed a row that shared half its numbers within 0.6 and so let a percentage multiplied by 100 through
(fairshare's docs/limits.md, October 14, as ticket 33's notes give it): CLAUDE.md rule 1 needs every number to
match. Column names are not compared, because Genie names its columns its own way, which is also why Genie's own
evaluation run fails answers whose numbers agree.

The share of questions that passed is the Genie benchmark's pass rate, which the full gate stores in
strata.ops.evaluation_result.
"""

from __future__ import annotations

from strata.evals.answers import same_rows
from strata.evals.scoring import Scored
from strata.genie.client import GenieError
from strata.lakehouse.engine import Engine

KIND = "genie"


def run(client, engine: Engine, benchmarks) -> list[Scored]:
    scored = []
    for item in benchmarks:
        truth = same_rows(engine.run(item.case.sql, item.case.params).rows)
        try:
            answer = client.ask(item.question)
        except GenieError as error:
            scored.append(Scored(item.id, KIND, False, (f"Genie gave no answer ({error.code}): {error}",)))
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
