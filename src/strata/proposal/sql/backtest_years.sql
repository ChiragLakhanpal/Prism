-- The newest rolling backtest by test year (Figure 5): the packages signed within the 8-in-10 point (n) out of those
-- with a known outcome (d), and the whole percent, only from data_readiness.fewest_for_a_percentage packages, as the
-- backtest stored it.
WITH latest AS (
  SELECT max_by(run_id, ran_at) AS run_id, max(ran_at) AS ran_at
  FROM strata.ops.evaluation_result
  WHERE scorer = :scorer AND segment_kind = 'test_year'
)
SELECT
  e.segment AS label,
  CAST(max(CASE WHEN e.measure = 'm' THEN e.value END) AS BIGINT) AS n,
  CAST(max(CASE WHEN e.measure = 'n' THEN e.value END) AS BIGINT) AS d,
  CASE WHEN max(CASE WHEN e.measure = 'n' THEN e.value END) >= :fewest_for_a_percentage
       THEN CAST(max(CASE WHEN e.measure = 'coverage_percent' THEN e.value END) AS BIGINT) END AS percent,
  max(l.run_id) AS run_id,
  CAST(max(l.ran_at) AS DATE) AS measured_on
FROM strata.ops.evaluation_result AS e
JOIN latest AS l ON e.run_id = l.run_id
WHERE e.scorer = :scorer AND e.segment_kind = 'test_year'
GROUP BY e.segment
ORDER BY e.segment
