-- Tile 10: each nightly run in the dates chosen, newest first, from strata.ops.pipeline_runs and
-- strata.ops.quality_checks (ticket 43): how it ended, how many of the job's tasks finished, how long it took, the rows
-- it changed and its checks. A repair run keeps its run's id, so a task tried again has a row for each try, and its
-- last try counts; a run whose tasks all finished after a retry reads "Rerun, finished". A run that stopped names the
-- first task whose last try failed. The night is the one its checks name, or the day it started, in UTC.
WITH tries AS (
  SELECT
    p.run_id,
    p.task_key,
    p.status,
    p.rows_changed,
    p.started_at,
    p.finished_at,
    count(*) OVER (PARTITION BY p.run_id, p.task_key) AS tries,
    row_number() OVER (PARTITION BY p.run_id, p.task_key ORDER BY p.finished_at DESC) AS newest
  FROM strata.ops.pipeline_runs AS p
),
last_tries AS (
  SELECT run_id, task_key, status, rows_changed, tries, :task_order__task_key AS task_order
  FROM tries
  WHERE newest = 1
),
checks AS (
  SELECT
    q.run_id,
    max(q.night) AS night,
    sum(CASE WHEN q.passed THEN 1 ELSE 0 END) AS checks_passed,
    sum(CASE WHEN q.passed THEN 0 ELSE 1 END) AS checks_failed
  FROM strata.ops.quality_checks AS q
  WHERE q.checked_at = (
    SELECT max(t.checked_at)
    FROM strata.ops.quality_checks AS t
    WHERE t.run_id = q.run_id AND t.task_key = q.task_key
  )
  GROUP BY q.run_id
),
runs AS (
  SELECT t.run_id, min(t.started_at) AS started_at, max(t.finished_at) AS finished_at
  FROM tries AS t
  GROUP BY t.run_id
),
outcomes AS (
  SELECT
    l.run_id,
    sum(l.rows_changed) AS rows_changed,
    sum(CASE WHEN l.status = 'succeeded' THEN 1 ELSE 0 END) AS done,
    max(l.tries) AS most_tries,
    min(CASE WHEN l.status <> 'succeeded' THEN l.task_order END) AS stopped_order
  FROM last_tries AS l
  GROUP BY l.run_id
),
stopped AS (
  SELECT o.run_id, l.task_key AS stopped_task
  FROM outcomes AS o
  JOIN last_tries AS l ON l.run_id = o.run_id AND l.task_order = o.stopped_order
),
named AS (
  SELECT run_id, :task_label__stopped_task AS stopped_label
  FROM stopped
)
SELECT
  coalesce(c.night, CAST(r.started_at AS DATE)) AS night,
  r.run_id,
  CASE
    WHEN n.stopped_label IS NOT NULL THEN replace(:copy__dash__gov__outcome__stopped, '{task}', n.stopped_label)
    WHEN o.most_tries > 1 THEN :copy__dash__gov__outcome__rerunFinished
    ELSE :copy__dash__gov__outcome__finished
  END AS outcome,
  replace(replace(:copy__dash__gov__tasksDone, '{done}', CAST(o.done AS STRING)), '{tasks}',
          CAST(:nightly_tasks AS STRING)) AS tasks_finished,
  CAST(timestampdiff(MINUTE, r.started_at, r.finished_at) AS BIGINT) AS minutes,
  o.rows_changed,
  coalesce(c.checks_passed, 0) AS checks_passed,
  coalesce(c.checks_failed, 0) AS checks_failed,
  o.done AS tasks_done,
  n.stopped_label,
  o.most_tries
FROM runs AS r
JOIN outcomes AS o ON o.run_id = r.run_id
LEFT JOIN checks AS c ON c.run_id = r.run_id
LEFT JOIN named AS n ON n.run_id = r.run_id
WHERE coalesce(c.night, CAST(r.started_at AS DATE)) BETWEEN :date_from AND :date_to
ORDER BY r.started_at DESC
