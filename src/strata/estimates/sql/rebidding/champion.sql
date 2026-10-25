-- The rebidding champion as of a date (ticket 28): the measures of the latest rebidding backtest run, public on
-- or before the as-of date (ADR 0002), that registered its model under the champion alias. The run stored them
-- in its registered_model segment: the version, the learner, its latest test year, how many packages it was
-- tested on there, and whether it beat its baseline (strata.estimates.rebidding_backtest).
WITH latest AS (
  SELECT run_id
  FROM strata.ops.evaluation_result
  WHERE scorer = :scorer AND segment_kind = 'registered_model' AND measure = 'alias' AND value_text = 'champion'
    AND public_from <= :as_of
  ORDER BY ran_at DESC, run_id DESC
  LIMIT 1
)
SELECT r.run_id, r.model, r.segment, r.measure, r.value, r.value_text, r.ran_at, r.public_from
FROM strata.ops.evaluation_result AS r
JOIN latest AS l ON l.run_id = r.run_id
WHERE r.segment_kind = 'registered_model'
ORDER BY r.measure
