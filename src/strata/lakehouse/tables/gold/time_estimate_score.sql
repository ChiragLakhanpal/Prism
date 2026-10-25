-- The time estimate of every package Strata knows, for every what-if combination, scored in batch by the
-- nightly job's score task with the champion model (ticket 26; src/strata/estimates/scoring.py), so
-- estimate_time answers from stored rows and the chart answers within 100 ms. Each run appends its rows
-- under its own run_id; estimate_time reads the latest run public on its as-of date (ADR 0002), because a
-- package's features are taken as they stood on the scoring day.
--
-- A package has one row as described (its features as the newest public plan row or its specific
-- procurement notice give them, ticket 25's features) and one row for each combination of the what-if
-- levers the model reads, config/models.toml's [what_if]: market approach and qualification. The model
-- reads no number of lots, so lots are not a column: estimate_time says so for a lots comparison.
--
-- step_reference         the package's STEP reference
-- run_id                 the nightly job's run that scored it
-- as_described           true for the package as described, false for a what-if combination
-- market_approach        the Market Approach scored, in STEP's words; empty when the records give none
-- prequalification       Prequalification (Y/N) scored, as STEP writes it: Y or N; empty when none is recorded
-- review_type            the package's Review Type as described, the same in every row: no lever changes it
-- estimated_amount_usd   the package's Estimated Amount (US$) as described, the same in every row
-- feature_date           the day its features were taken: its specific procurement notice, or the scoring day
-- q25_days to q80_days   the days by which a quarter, half, three quarters and 8 in 10 of packages like it
--                        were signed, whole; empty when the row abstains
-- q25_months to q80_months   the same in months, to one decimal
-- abstention             why the row gives no range: outside_training (a feature outside what the model
--                        learned from) or value_not_learned (a lever's value the model never saw); else empty
-- abstention_detail      the feature and its value, as JSON, for outside_training and value_not_learned
-- model, model_version, model_alias, training_through   the champion it was scored with
-- scored_at              when the run scored it, in UTC
-- public_from            the day it was scored (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.time_estimate_score (
  step_reference STRING NOT NULL,
  run_id STRING NOT NULL,
  as_described BOOLEAN NOT NULL,
  market_approach STRING,
  prequalification STRING,
  review_type STRING,
  estimated_amount_usd DOUBLE,
  feature_date DATE,
  q25_days INT,
  q50_days INT,
  q75_days INT,
  q80_days INT,
  q25_months DOUBLE,
  q50_months DOUBLE,
  q75_months DOUBLE,
  q80_months DOUBLE,
  abstention STRING,
  abstention_detail STRING,
  model STRING NOT NULL,
  model_version INT NOT NULL,
  model_alias STRING NOT NULL,
  training_through DATE NOT NULL,
  scored_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
