-- KPI plan_rows_offered (config/kpis.toml): plan rows published after Strata showed a past range or time estimate for
-- their package whose planned signing date fell within estimates_loop.anchored_within_days of a date offered, out of
-- those rows, as the latest monthly watch in the dates chosen stored them (strata.ops.estimates_watch, anchored_rows,
-- segment all; ticket 44). Ranges shown in a preview are not exposures, so they never count. Always one row.
WITH latest AS (
  SELECT run_id, month
  FROM strata.ops.estimates_watch
  WHERE measure = 'anchored_rows' AND segment = 'all' AND month BETWEEN :date_from AND :date_to
  ORDER BY measured_at DESC
  LIMIT 1
),
counted AS (
  SELECT max(w.count) AS anchored, max(w.denominator) AS plan_rows
  FROM strata.ops.estimates_watch AS w
  JOIN latest AS l ON w.run_id = l.run_id AND w.month = l.month
  WHERE w.measure = 'anchored_rows' AND w.segment = 'all'
)
SELECT
  anchored AS numerator,
  plan_rows AS denominator,
  anchored AS value,
  CASE
    WHEN plan_rows IS NULL OR plan_rows = 0 THEN :copy__kpi__display__none
    ELSE replace(replace(:copy__kpi__display__share, '{n}', format_number(anchored, 0)), '{d}',
                 format_number(plan_rows, 0))
  END AS display
FROM counted
