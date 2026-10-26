-- KPI plan_accuracy (config/kpis.toml), the estimates loop's lagging indicator, with plan duration (tile 30): for plan
-- rows dated within 14 days of a date Strata offered and for the other plan rows, in countries using Strata and in
-- countries not yet using it, the rows with an actual signing date, the median days between planned and actual
-- signing, and the median months from first notice to signing, as the latest monthly watch in the dates chosen
-- stored them (strata.ops.estimates_watch, plan_accuracy and plan_duration; ticket 44). A median is kept only from
-- estimates_loop.min_cases rows, so a group with fewer shows its count in words. Each median is rounded half up
-- before it is written, as the nightly sentence rounds it, since Spark's format_number alone rounds half to
-- even. Four rows, in a fixed order.
WITH latest AS (
  SELECT run_id, month
  FROM strata.ops.estimates_watch
  WHERE measure = 'plan_accuracy' AND month BETWEEN :date_from AND :date_to
  ORDER BY measured_at DESC
  LIMIT 1
),
groups AS (
  SELECT
    w.segment,
    max(CASE WHEN w.measure = 'plan_accuracy' THEN w.count END) AS with_actual,
    max(CASE WHEN w.measure = 'plan_accuracy' THEN w.value END) AS median_days,
    max(CASE WHEN w.measure = 'plan_duration' THEN w.count END) AS with_cycle,
    max(CASE WHEN w.measure = 'plan_duration' THEN w.value END) AS median_months
  FROM strata.ops.estimates_watch AS w
  JOIN latest AS l ON w.run_id = l.run_id AND w.month = l.month
  WHERE w.measure IN ('plan_accuracy', 'plan_duration')
  GROUP BY w.segment
)
SELECT
  CASE segment WHEN 'anchored/using_strata' THEN 1 WHEN 'anchored/not_yet' THEN 2 WHEN 'other/using_strata' THEN 3
               ELSE 4 END AS position,
  segment,
  CASE WHEN segment LIKE 'anchored/%' THEN :copy__dash__ai__tiles__accuracy__offered
       ELSE :copy__dash__ai__tiles__accuracy__other END AS plan_rows,
  CASE WHEN segment LIKE '%/using_strata' THEN :copy__dash__ai__tiles__accuracy__using
       ELSE :copy__dash__ai__tiles__accuracy__notYet END AS countries,
  with_actual,
  median_days,
  CASE
    WHEN median_days IS NOT NULL THEN format_number(round(median_days), 0)
    WHEN with_actual = 1 THEN replace(:copy__dash__ai__tiles__accuracy__tooFew__one, '{n}', format_number(with_actual, 0))
    ELSE replace(:copy__dash__ai__tiles__accuracy__tooFew__other, '{n}', format_number(coalesce(with_actual, 0), 0))
  END AS median_days_cell,
  CASE
    WHEN median_months IS NOT NULL THEN format_number(round(median_months, 1), 1)
    WHEN with_cycle = 1 THEN replace(:copy__dash__ai__tiles__accuracy__tooFew__one, '{n}', format_number(with_cycle, 0))
    ELSE replace(:copy__dash__ai__tiles__accuracy__tooFew__other, '{n}', format_number(coalesce(with_cycle, 0), 0))
  END AS median_months_cell
FROM groups
ORDER BY position
