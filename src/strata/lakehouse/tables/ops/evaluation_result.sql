-- Every score the replay harness (src/strata/estimates/harness.py) writes: one row per measure, for
-- one segment of one scorer's run. A run appends its rows under its own run_id and never changes an
-- earlier run's, so a reader takes the latest run (strata.estimates.harness.latest_run). Each scorer
-- adds its own segments and measures: the time estimate's backtest writes one segment per test year
-- (n, m, expected, coverage, widths, errors, its MLflow run id), and later scorers add per-step
-- coverage, calibration, retrieval and the hindsight test, and the signals' track record.
--
-- run_id            one run of the harness: every row it wrote shares it
-- scorer            the scorer that wrote the row, such as time_estimate_backtest
-- model             the model or check scored, such as strata.gold.time_estimate; empty when none
-- segment_kind      what the segment is, such as test_year, champion, step, status or check
-- segment           the segment itself, such as 2021
-- measure           what the value counts or measures, such as n, m or error_estimate_months
-- value             the number, at the scorer's rounding; empty for a measure given as text
-- value_text        a measure that is text, such as a date or a JSON list of feature ranges
-- cutoff            the date Strata was frozen at for this segment: every input was public by then
-- outcomes_through  the date the outcomes were read as of: what became public later
-- mlflow_run_id     the MLflow run that holds this segment's parameters, metrics and model
-- ran_at            when the run wrote the row, in UTC
-- public_from       the day the run wrote it (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.evaluation_result (
  run_id STRING NOT NULL,
  scorer STRING NOT NULL,
  model STRING,
  segment_kind STRING NOT NULL,
  segment STRING NOT NULL,
  measure STRING NOT NULL,
  value DOUBLE,
  value_text STRING,
  cutoff DATE,
  outcomes_through DATE,
  mlflow_run_id STRING,
  ran_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
