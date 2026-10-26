-- The time estimate's newest rolling backtest (ticket 25, strata.estimates.backtest), over every test year: the
-- packages signed within the 8-in-10 point of the range they were given (m), out of the packages with a known
-- outcome (n). percent is the whole percent, only from data_readiness.fewest_for_a_percentage packages.
WITH latest AS (
  SELECT max_by(run_id, ran_at) AS run_id, max(ran_at) AS ran_at
  FROM strata.ops.evaluation_result
  WHERE scorer = :scorer AND segment_kind = 'test_year'
),
years AS (
  SELECT
    e.segment,
    max(CASE WHEN e.measure = 'm' THEN e.value END) AS inside,
    max(CASE WHEN e.measure = 'n' THEN e.value END) AS known
  FROM strata.ops.evaluation_result AS e
  JOIN latest AS l ON e.run_id = l.run_id
  WHERE e.scorer = :scorer AND e.segment_kind = 'test_year'
  GROUP BY e.segment
),
measured AS (
  SELECT sum(inside) AS n, sum(known) AS d FROM years
)
SELECT
  CAST(m.n AS BIGINT) AS n,
  CAST(m.d AS BIGINT) AS d,
  CASE WHEN m.d >= :fewest_for_a_share AND round(10.0 * m.n / m.d) BETWEEN 1 AND 9
       THEN CAST(round(10.0 * m.n / m.d) AS BIGINT) END AS in_ten,
  CASE WHEN m.d >= :fewest_for_a_percentage THEN CAST(round(100.0 * m.n / m.d) AS BIGINT) END AS percent,
  l.run_id,
  CAST(l.ran_at AS DATE) AS measured_on
FROM measured AS m
CROSS JOIN latest AS l
WHERE m.d > 0
