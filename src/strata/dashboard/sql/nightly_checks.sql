-- Tile 9: the quality checks of the last run of each night in the dates chosen, passed and failed, from
-- strata.ops.quality_checks (ticket 43). A task tried again counts by its last try. Failed sits at the base of each
-- bar (stack_order 1), so failures line up.
WITH runs AS (
  SELECT night, run_id, max(checked_at) AS last_checked
  FROM strata.ops.quality_checks
  WHERE night BETWEEN :date_from AND :date_to
  GROUP BY night, run_id
),
last_runs AS (
  SELECT r.night, r.run_id
  FROM runs AS r
  WHERE r.last_checked = (SELECT max(o.last_checked) FROM runs AS o WHERE o.night = r.night)
),
last_tries AS (
  SELECT l.night, q.passed
  FROM strata.ops.quality_checks AS q
  JOIN last_runs AS l ON q.run_id = l.run_id
  WHERE q.checked_at = (
    SELECT max(t.checked_at)
    FROM strata.ops.quality_checks AS t
    WHERE t.run_id = q.run_id AND t.task_key = q.task_key
  )
)
SELECT
  night,
  CASE WHEN passed THEN :copy__dash__gov__result__passed ELSE :copy__dash__gov__result__failed END AS result,
  CASE WHEN passed THEN 2 ELSE 1 END AS stack_order,
  count(*) AS checks
FROM last_tries
GROUP BY night, passed
ORDER BY night, stack_order
