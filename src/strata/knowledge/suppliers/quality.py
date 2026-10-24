"""How often auto-merge is right, on the candidate pairs people labeled (docs/PLAN.md section 5: an
auto-merge precision of at least 0.98 on 1,000 labeled pairs).

measure() runs in the nightly job's measure_data_readiness task and writes one row per run to
strata.ops.supplier_match_quality: how many candidate pairs the latest run found, how many carry a
label, and, once at least min_labeled_pairs_for_precision auto-merged pairs carry one, the auto-merge
precision on them with its 95% Wilson score interval, computed in SQL (sql/match_quality.sql). It
also gives the lowest match probability at which the labeled pairs reach precision_target, so the
owner can set auto_merge_min_probability in config/thresholds.toml from the labels. Below the
minimum it writes counts only: no percentage or range from fewer than 20 cases (DESIGN.md section 7,
rules 6 and 15).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from importlib import resources

from strata.config import Thresholds, load_thresholds
from strata.lakehouse.engine import Engine

COLUMNS = ("run_id", "candidate_pairs", "labeled_pairs", "labeled_pairs_target", "auto_merged", "labeled_auto_merged",
           "labeled_auto_merged_right", "auto_merge_precision", "interval_low", "interval_high", "precision_target",
           "auto_merge_min_probability", "lowest_threshold_meeting_target", "measured_at", "public_from")


def measure(engine: Engine, run_id: str, clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC),
            thresholds: Thresholds | None = None) -> int:
    """Write this run's row. Returns 1."""
    thresholds = thresholds or load_thresholds()

    def value(name: str):
        return thresholds.value(f"supplier_matching.{name}")

    query = (resources.files("strata.knowledge.suppliers") / "sql" / "match_quality.sql").read_text()
    result = engine.run(query, {"min_labeled": int(value("min_labeled_pairs_for_precision")),
                                "precision_target": float(value("precision_target")), "z": float(value("interval_z"))})
    found = dict(zip(result.columns, result.rows[0], strict=True))
    measured_at = clock()
    return engine.insert_rows("strata.ops.supplier_match_quality", COLUMNS, [(
        run_id, found["candidate_pairs"], found["labeled_pairs"], int(value("labeled_pairs_target")),
        found["auto_merged"], found["labeled_auto_merged"], found["labeled_auto_merged_right"],
        found["auto_merge_precision"], found["interval_low"], found["interval_high"], float(value("precision_target")),
        float(value("auto_merge_min_probability")), found["lowest_threshold_meeting_target"], measured_at,
        measured_at.astimezone(dt.UTC).date())])
