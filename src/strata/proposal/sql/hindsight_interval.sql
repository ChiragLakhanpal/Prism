-- Wilson's interval around the share of blamed risks Strata's tables showed, from the newest hindsight test (ticket
-- 34), as whole percents, with its level. Only from data_readiness.fewest_for_a_percentage blamed risks, since a
-- percentage rests on at least that many cases (DESIGN.md section 7, rule 15).
WITH latest AS (
  SELECT max_by(run_id, ran_at) AS run_id, max_by(segment, ran_at) AS segment, max(ran_at) AS ran_at
  FROM strata.ops.evaluation_result
  WHERE scorer = :scorer AND segment_kind = 'release'
),
measured AS (
  SELECT
    max(CASE WHEN e.measure = 'blamed' THEN e.value END) AS blamed,
    max(CASE WHEN e.measure = 'interval_low' THEN e.value END) AS low,
    max(CASE WHEN e.measure = 'interval_high' THEN e.value END) AS high,
    max(CASE WHEN e.measure = 'interval_level' THEN e.value END) AS level
  FROM strata.ops.evaluation_result AS e
  JOIN latest AS l ON e.run_id = l.run_id AND e.segment = l.segment
  WHERE e.scorer = :scorer AND e.segment_kind = 'release'
)
SELECT
  CASE WHEN m.blamed >= :fewest_for_a_percentage THEN CAST(round(100 * m.low) AS BIGINT) END AS low,
  CASE WHEN m.blamed >= :fewest_for_a_percentage THEN CAST(round(100 * m.high) AS BIGINT) END AS high,
  CASE WHEN m.blamed >= :fewest_for_a_percentage THEN CAST(round(100 * m.level) AS BIGINT) END AS level,
  l.run_id,
  CAST(l.ran_at AS DATE) AS measured_on
FROM measured AS m
CROSS JOIN latest AS l
