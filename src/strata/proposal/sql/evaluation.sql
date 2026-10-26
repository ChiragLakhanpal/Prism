-- Two measures of one segment from the newest run that scored it (strata.ops.evaluation_result): numerator over
-- denominator, such as the benchmark's must-refuse questions passed of those asked. An empty :segment takes the newest
-- run's segment of that kind, such as the hindsight test's newest release. in_ten as in readiness.sql.
WITH latest AS (
  SELECT max_by(run_id, ran_at) AS run_id, max_by(segment, ran_at) AS segment, max(ran_at) AS ran_at
  FROM strata.ops.evaluation_result
  WHERE scorer = :scorer AND segment_kind = :segment_kind AND (:segment = '' OR segment = :segment)
),
measured AS (
  SELECT
    max(CASE WHEN e.measure = :numerator THEN e.value END) AS n,
    max(CASE WHEN e.measure = :denominator THEN e.value END) AS d
  FROM strata.ops.evaluation_result AS e
  JOIN latest AS l ON e.run_id = l.run_id AND e.segment = l.segment
  WHERE e.scorer = :scorer AND e.segment_kind = :segment_kind
)
SELECT
  CAST(m.n AS BIGINT) AS n,
  CAST(m.d AS BIGINT) AS d,
  CASE WHEN m.d >= :fewest_for_a_share AND round(10.0 * m.n / m.d) BETWEEN 1 AND 9
       THEN CAST(round(10.0 * m.n / m.d) AS BIGINT) END AS in_ten,
  l.run_id,
  CAST(l.ran_at AS DATE) AS measured_on
FROM measured AS m
CROSS JOIN latest AS l
