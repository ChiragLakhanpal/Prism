-- KPI checks_failed (config/kpis.toml): the quality checks that failed in the latest nightly run in the dates chosen,
-- out of the checks it ran, as strata.ops.quality_checks holds them (ticket 43). A task tried again keeps a row for
-- each try, and its last try counts. Always one row: "None yet" before the first run.
WITH latest AS (
  SELECT run_id
  FROM strata.ops.quality_checks
  WHERE night BETWEEN :date_from AND :date_to
  ORDER BY checked_at DESC
  LIMIT 1
),
last_tries AS (
  SELECT q.passed
  FROM strata.ops.quality_checks AS q
  JOIN latest AS l ON q.run_id = l.run_id
  WHERE q.checked_at = (
    SELECT max(t.checked_at)
    FROM strata.ops.quality_checks AS t
    WHERE t.run_id = q.run_id AND t.task_key = q.task_key
  )
),
counted AS (
  SELECT sum(CASE WHEN passed THEN 0 ELSE 1 END) AS failed, count(*) AS checks
  FROM last_tries
)
SELECT
  coalesce(failed, 0) AS numerator,
  checks AS denominator,
  coalesce(failed, 0) AS value,
  CASE
    WHEN checks = 0 THEN :copy__kpi__display__none
    ELSE replace(replace(:copy__kpi__display__share, '{n}', format_number(coalesce(failed, 0), 0)), '{d}',
                 format_number(checks, 0))
  END AS display
FROM counted
