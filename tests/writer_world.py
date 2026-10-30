"""The fixture database as the review notes and mission brief writers' recordings saw it (ticket 132).

The scripted writer replays model outputs recorded from the live writer (tests/fixtures/agent/writers.toml and
recorded/). The review notes recording is the writer's notes on the three activities the plan check marked in the
Northern Water Works Development Agency's plan of October 9, 2026, and the mission brief's states that plan's
KE-NWWDA-541055-CW-RFB passed its planned completion. Ticket 132 found that the contract awards say two of those
activities were signed before the plan's date: the nightly job now writes a disagreement between each plan row that
still says pending and the record of its signing, and the plan check names those rows moved on since the plan,
with no signal. Re-recording the writers needs the live model, a workspace step, so until then the stories that
replay them run on this copy: the fixture without the plan rows' Process Status assertions and the disagreements
they are a side of, the world the recordings were made in. Everything else is the fixture as the gate built it.

The plan check's own tests, Home, the Timeline and the agent run on the fixture as built.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from strata.knowledge.assertions import STATUS
from strata.lakehouse.engine import DuckDBEngine

# Each statement names its rows with a WHERE (CLAUDE.md rule 5), and runs on a copy, never on the fixture itself.
WITHOUT_PLAN_STATUSES = (
    "DELETE FROM strata.gold.disagreement WHERE first_assertion_id IN "
    "(SELECT assertion_id FROM strata.gold.assertion WHERE value_form = :status) OR second_assertion_id IN "
    "(SELECT assertion_id FROM strata.gold.assertion WHERE value_form = :status)",
    "DELETE FROM strata.gold.assertion WHERE value_form = :status",
)


def copy_without_moved_on(fixture_db: Path, folder: Path) -> Path:
    """A copy of the fixture database in folder with no plan row's Process Status assertion and no disagreement
    that rests on one, so no activity has moved on since its plan."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "fixture-as-recorded.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        for statement in WITHOUT_PLAN_STATUSES:
            engine.run(statement, {"status": STATUS})
    return target
