-- The planned dates of a saved baseline (strata.ops.plan_baselines), copied from silver.plan_steps when
-- the baseline is saved, because the plan reader rebuilds silver on every run. One row per step of each
-- activity in the saved version. Saving another version adds its rows first and then deletes the earlier
-- save's, and removing the baseline deletes them, each with a DELETE that names the project and the agency
-- (CLAUDE.md rule 5).
--
-- project_id, agency_id   the baseline's project and agency
-- document_id             the saved version
-- activity_reference_no   Activity Reference No.
-- step, step_order        STEP's name for the step, word for word, and its place in its table
-- planned_on              the step's Planned date in the saved version; empty when it gives none
-- saved_at                when the save that copied them was made, in UTC, as the baseline's row records it
-- public_from             the day the baseline was saved (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.plan_baseline_steps (
  project_id STRING NOT NULL,
  agency_id STRING NOT NULL,
  document_id STRING NOT NULL,
  activity_reference_no STRING NOT NULL,
  step STRING NOT NULL,
  step_order INT NOT NULL,
  planned_on DATE,
  saved_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
