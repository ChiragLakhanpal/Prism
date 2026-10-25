-- The backtest run that registered a version of the time estimate (ticket 44): backtest.run stores the version under
-- the registered_model segment. The promotion compares that run's test years, and the time estimate tool reports
-- them as the track record of the version it estimates with (src/strata/estimates/backtest.py, registered_run). Only
-- a run public on the as-of date counts (ADR 0002).
SELECT e.run_id, e.public_from
FROM strata.ops.evaluation_result AS e
WHERE e.scorer = :scorer
  AND e.segment_kind = :segment_kind
  AND e.segment = :version
  AND e.measure = :measure
  AND e.public_from <= :as_of
ORDER BY e.ran_at DESC, e.run_id DESC
LIMIT 1
