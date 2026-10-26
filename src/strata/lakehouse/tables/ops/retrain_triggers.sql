-- Each retrain the estimates loop's monthly watch raised (ticket 44; docs/PLAN.md section 11, "Retraining"), with
-- the day and a reason code for ticket 45's copy ("I raised a retrain on {Month D}, because ..."). The watch
-- (src/strata/estimates/watch.py) raises one when:
--   coverage_outside         coverage of the 8-in-10 range stayed outside time_estimate.coverage_low to
--                            coverage_high for estimates_loop.coverage_outside_months watched months in a row
--   error_trails_past_range  the time estimate's typical error was more than estimates_loop.error_trail_share
--                            larger than the past range's
--   input_mix_drift          an input's mix drifted (estimates_loop.drift_alpha)
--   new_edition              a new edition of the procurement rules took effect in the month (config/editions.toml),
--                            which first marked the affected lessons and models as being re-checked
-- No trigger fires on fewer than estimates_loop.min_cases cases. The quarterly retrain, or the next one after a
-- trigger, trains a challenger (src/strata/estimates/backtest.py). Rows only join.
--
-- run_id         the watch's run
-- month          the last day of the watched month
-- reason         one of the codes above
-- edition_key    for new_edition, the edition (config/editions.toml)
-- detail         JSON: the counts and values that raised it
-- model          the model it is for: the time estimate's registered name (config/models.toml)
-- raised_on      the day it was raised
-- raised_at      when, in UTC
-- public_from    raised_on (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrain_triggers (
  run_id STRING NOT NULL,
  month DATE NOT NULL,
  reason STRING NOT NULL,
  edition_key STRING,
  detail STRING,
  model STRING NOT NULL,
  raised_on DATE NOT NULL,
  raised_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
