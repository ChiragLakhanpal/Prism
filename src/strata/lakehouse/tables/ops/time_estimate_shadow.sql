-- The challenger's time estimates, scored in shadow beside the champion (ticket 44; docs/PLAN.md section 11, "a
-- quarter in shadow"). The nightly score task scores every package as described with the newest challenger kept in
-- strata.gold.time_estimate_model, as it scores the champion into strata.gold.time_estimate_score, and appends the
-- rows here under its run id. No tool and no screen reads this table: estimate_time answers from the champion's
-- scores only. The promotion's shadow-quarter check compares the two on the packages that signed during the quarter
-- (src/strata/estimates/promotion.py).
--
-- step_reference   the package's STEP reference
-- run_id           the nightly run
-- model            the registered model's name (config/models.toml)
-- model_version    the challenger's version
-- feature_date     the day its features were taken as of
-- q50_days         the middle, in days from the first notice
-- q80_days         the 8-in-10 point, in days
-- abstention       outside_training when the challenger could not score it
-- scored_at        when, in UTC
-- public_from      the day it was scored (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.time_estimate_shadow (
  step_reference STRING NOT NULL,
  run_id STRING NOT NULL,
  model STRING NOT NULL,
  model_version INT NOT NULL,
  feature_date DATE,
  q50_days INT,
  q80_days INT,
  abstention STRING,
  scored_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
