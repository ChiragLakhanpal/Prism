-- A model version marked as being re-checked (ticket 44; docs/PLAN.md section 11): when a new edition of the
-- procurement rules takes effect, the estimates loop's watch marks the time estimate's champion as being re-checked,
-- the same state a lesson takes while a re-check is open (ticket 29's rechecking), before it raises the retrain. The
-- mark stays until a challenger trained after it is promoted (src/strata/estimates/promotion.py). Rows only join.
--
-- model          the registered model's name (config/models.toml)
-- version        its version
-- state          rechecking
-- reason         new_edition
-- edition_key    the edition that took effect (config/editions.toml)
-- run_id         the watch's run
-- since          the day it was marked
-- marked_at      when, in UTC
-- public_from    since (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.model_states (
  model STRING NOT NULL,
  version INT NOT NULL,
  state STRING NOT NULL,
  reason STRING NOT NULL,
  edition_key STRING,
  run_id STRING NOT NULL,
  since DATE NOT NULL,
  marked_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
