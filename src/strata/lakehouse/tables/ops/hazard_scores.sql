-- The discrete-time hazard model's shadow scores (ticket 44; docs/PLAN.md section 7: project delay early warning uses
-- the fixed signals now, with a hazard model in shadow until it beats them on the hindsight comparison). The nightly
-- score task scores every open project with a loan history, each night, beside the fixed signals
-- (src/strata/estimates/hazard.py). No tool, no route and no copy key reads this table, so no screen shows a score:
-- Following shows signals with their reasons and track record, never a score (brief 37). The comparison with the
-- signals is in strata.ops.evaluation_result under the scorer hazard_vs_signals. Each night appends its own rows.
--
-- project_id      the project
-- run_id          the nightly run
-- scored_on       the day it was scored as of
-- hazard          the chance the model gives that the loan history shows the closing date moved later within the
--                 follow-up window (signals.track_record_window_months), to six decimals; empty when it abstained
-- abstention      too_few_periods or one_outcome when the model could not be trained that day
-- model           the model's name and the day it was trained through, such as hazard-2026-10-24
-- features        JSON: the values it scored
-- scored_at       when, in UTC
-- public_from     scored_on (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.hazard_scores (
  project_id STRING NOT NULL,
  run_id STRING NOT NULL,
  scored_on DATE NOT NULL,
  hazard DOUBLE,
  abstention STRING,
  model STRING NOT NULL,
  features STRING,
  scored_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
