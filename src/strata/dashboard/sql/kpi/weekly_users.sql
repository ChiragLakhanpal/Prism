-- KPI weekly_users (config/kpis.toml): people who opened at least one page of Strata in the last full week, Monday to
-- Sunday, that ends on or before the last day chosen, from the app's usage events (ticket 06). A visit records the
-- page it starts on, so a page is a route outside /api. Each person counts once, whatever view they used, preview
-- included. A count, so always shown, 0 included.
WITH week AS (
  SELECT CAST(date_trunc('WEEK', date_add(:date_to, 1)) AS DATE) AS week_after
),
bounds AS (
  SELECT CAST(date_add(week_after, -7) AS DATE) AS week_start, week_after
  FROM week
),
people AS (
  SELECT count(DISTINCT u.viewer_id) AS people, min(b.week_start) AS week_start
  FROM bounds AS b
  LEFT JOIN strata.ops.usage_events AS u
    ON u.public_from >= b.week_start AND u.public_from < b.week_after AND u.public_from >= :date_from
   AND u.route NOT LIKE '/api/%' AND u.viewer_id IS NOT NULL
)
SELECT
  people AS numerator,
  CAST(NULL AS BIGINT) AS denominator,
  people AS value,
  week_start,
  format_number(people, 0) AS display
FROM people
