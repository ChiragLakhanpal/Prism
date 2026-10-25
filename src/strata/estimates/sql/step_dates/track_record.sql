-- The planned dates' track record (ticket 27): every test-year score the step backtest stored
-- (strata.estimates.step_dates.track_record picks the latest run), as public on the as-of date, so an answer as
-- of a past date reads the backtest that existed then.
SELECT
  e.run_id,
  e.segment,
  e.measure,
  e.value,
  e.cutoff,
  e.mlflow_run_id,
  e.ran_at,
  e.public_from
FROM strata.ops.evaluation_result AS e
WHERE e.scorer = :scorer
  AND e.segment_kind = :segment_kind
  AND e.public_from <= :as_of
ORDER BY e.ran_at, e.run_id, e.segment, e.measure
