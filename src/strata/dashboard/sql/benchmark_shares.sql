-- Tile 11: the share of benchmark questions each full gate run in the dates chosen passed, as ticket 33 stored it
-- (strata.ops.evaluation_result, scorer benchmark, the kind all, its share), as a whole percent. A run of fewer than
-- data_readiness.fewest_for_a_percentage questions has no point (DESIGN.md section 7, rule 15); the table under it
-- gives every run's counts.
WITH runs AS (
  SELECT
    run_id,
    max(ran_at) AS ran_at,
    CAST(max(CASE WHEN measure = 'passed' THEN value END) AS BIGINT) AS passed,
    CAST(max(CASE WHEN measure = 'questions' THEN value END) AS BIGINT) AS questions,
    max(CASE WHEN measure = 'share' THEN value END) AS share
  FROM strata.ops.evaluation_result
  WHERE scorer = 'benchmark' AND segment_kind = 'kind' AND segment = 'all'
    AND public_from BETWEEN :date_from AND :date_to
  GROUP BY run_id
)
SELECT
  CAST(ran_at AS DATE) AS run_on,
  passed,
  questions,
  CASE WHEN questions >= :threshold__data_readiness__fewest_for_a_percentage
       THEN CAST(round(100 * share) AS BIGINT) END AS share_percent
FROM runs
ORDER BY ran_at
