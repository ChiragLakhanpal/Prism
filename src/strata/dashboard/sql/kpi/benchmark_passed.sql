-- KPI benchmark_passed (config/kpis.toml): the benchmark questions that passed in the latest full gate run in the
-- dates chosen, out of the questions it asked, as ticket 33 stored them (strata.ops.evaluation_result, scorer
-- benchmark, the kind all). Always one row: "None yet" before the first run.
WITH latest AS (
  SELECT run_id
  FROM strata.ops.evaluation_result
  WHERE scorer = 'benchmark' AND segment_kind = 'kind' AND segment = 'all'
    AND public_from BETWEEN :date_from AND :date_to
  ORDER BY ran_at DESC
  LIMIT 1
),
counted AS (
  SELECT
    CAST(max(CASE WHEN e.measure = 'passed' THEN e.value END) AS BIGINT) AS passed,
    CAST(max(CASE WHEN e.measure = 'questions' THEN e.value END) AS BIGINT) AS questions
  FROM strata.ops.evaluation_result AS e
  JOIN latest AS l ON e.run_id = l.run_id
  WHERE e.scorer = 'benchmark' AND e.segment_kind = 'kind' AND e.segment = 'all'
)
SELECT
  passed AS numerator,
  questions AS denominator,
  passed AS value,
  CASE
    WHEN questions IS NULL OR questions = 0 THEN :copy__kpi__display__none
    ELSE replace(replace(:copy__kpi__display__share, '{n}', format_number(passed, 0)), '{d}',
                 format_number(questions, 0))
  END AS display
FROM counted
