-- Promotion (ticket 44): the backtest run that registered a version of the time estimate (backtest.run stores the
-- version under the registered_model segment), whose test years the backtest check compares.
SELECT e.run_id, e.public_from
FROM strata.ops.evaluation_result AS e
WHERE e.scorer = :scorer
  AND e.segment_kind = :segment_kind
  AND e.segment = :version
  AND e.measure = :measure
ORDER BY e.ran_at DESC, e.run_id DESC
LIMIT 1
