-- How often auto-merge is right, on the pairs people labeled (ticket 19; docs/PLAN.md section 5: an
-- auto-merge precision of at least 0.98 on 1,000 labeled pairs). The nightly job's
-- measure_data_readiness task writes one row per run (strata.knowledge.suppliers.quality), in SQL,
-- from the latest run's candidate pairs and the latest label on each. Below
-- min_labeled_pairs_for_precision labeled auto-merged pairs it writes counts only, with no precision
-- and no interval (DESIGN.md section 7, rules 6 and 15).
--
-- run_id                     the run that measured it
-- candidate_pairs            the latest run's candidate pairs
-- labeled_pairs              those with a label
-- labeled_pairs_target       how many labeled pairs docs/PLAN.md section 5 aims at
-- auto_merged                candidate pairs that merged on auto_merge_min_probability
-- labeled_auto_merged        those with a label
-- labeled_auto_merged_right  those whose label is merge
-- auto_merge_precision       labeled_auto_merged_right out of labeled_auto_merged; empty below the minimum
-- interval_low, interval_high  its 95% Wilson score interval; empty below the minimum
-- precision_target           the precision auto-merge should reach
-- auto_merge_min_probability the threshold auto-merge used
-- lowest_threshold_meeting_target  the lowest match probability at which the labeled pairs at or
--                            above it, at least the minimum of them, reach precision_target; empty
--                            when no probability does
-- measured_at                when, in UTC
-- public_from                the day it was measured, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.supplier_match_quality (
  run_id STRING NOT NULL,
  candidate_pairs BIGINT NOT NULL,
  labeled_pairs BIGINT NOT NULL,
  labeled_pairs_target BIGINT NOT NULL,
  auto_merged BIGINT NOT NULL,
  labeled_auto_merged BIGINT NOT NULL,
  labeled_auto_merged_right BIGINT NOT NULL,
  auto_merge_precision DOUBLE,
  interval_low DOUBLE,
  interval_high DOUBLE,
  precision_target DOUBLE NOT NULL,
  auto_merge_min_probability DOUBLE NOT NULL,
  lowest_threshold_meeting_target DOUBLE,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
