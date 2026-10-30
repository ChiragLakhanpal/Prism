"""P130164 as the workspace's assertions pass read it on October 29, 2026 (ticket 136), planted in a copy of the
fixture database: one report's rating of the whole project against each ISR's rating of its own period.

On the workspace the PAD's overall risk and the ICR's progress towards the PDO came back for the whole project, so
each disagreed with every ISR that rated otherwise: three facts told 60 times. The fixture reads both for a moment
(the PAD at appraisal, the ICR's paragraph 78 at the mid-term review), so it holds one pair each at most. Here the
two assertions describe the whole project, from the Board's approval to closing, and the disagreements are decided
again by the assertions pass's own redetect(), so the copy holds what the pass would write:

- progress towards the PDO: ISRs 1 to 11 rated it on the satisfactory side and the ICR's paragraph 78 on the other,
  11 pairs that share the later report, the ICR;
- the overall risk: the PAD rated it Substantial and four ISRs Moderate, 4 pairs that share the earlier report;
- efficiency: the fixture's own pair, the ICR's paragraph 44 against the re-issued ICR Review.

plant() writes the copy; the tool, the timeline and the timeline's recorder read it read-only.
"""

import shutil
from pathlib import Path

from strata.config import load_ladder
from strata.knowledge.assertions import WHOLE_PROJECT, redetect
from strata.lakehouse.engine import DuckDBEngine

PROJECT = "P130164"
PAD_RISK = "strata.gold.passage:18381488/v1/49#P130164/overall_risk"
ICR_PROGRESS = "strata.gold.passage:31525018/v1/78#P130164/pdo_progress"
PROJECT_DATES = "SELECT approval_date, closing_date FROM strata.gold.project WHERE project_id = :project_id"
WHOLE = """UPDATE strata.gold.assertion SET period_event = :period, period_start = :start, period_end = :end
WHERE assertion_id = :assertion_id"""


def plant(fixture_db: Path, target: Path) -> Path:
    """A copy of the fixture database at target in which the PAD's overall risk and the ICR's paragraph 78 rate the
    whole project, with P130164's disagreements decided again."""
    shutil.copyfile(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        start, end = engine.run(PROJECT_DATES, {"project_id": PROJECT}).rows[0]
        for assertion in (PAD_RISK, ICR_PROGRESS):
            engine.run(WHOLE, {"period": WHOLE_PROJECT, "start": start, "end": end, "assertion_id": assertion})
        redetect(engine, [PROJECT], load_ladder())
    return target
