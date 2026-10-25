-- The estimates loop (ticket 44): the measures of every month watched on or before :month, each month's from its
-- newest run, which the retrain triggers read as a series.
WITH runs AS (
  SELECT w.month, w.run_id,
    row_number() OVER (PARTITION BY w.month ORDER BY max(w.measured_at) DESC, w.run_id DESC) AS newest
  FROM strata.ops.estimates_watch AS w
  WHERE w.month <= :month
  GROUP BY w.month, w.run_id
)
SELECT w.run_id, w.month, w.measure, w.segment, w.count, w.denominator, w.value, w.detail, w.reason, w.public_from
FROM strata.ops.estimates_watch AS w
JOIN runs AS r ON r.month = w.month AND r.run_id = w.run_id AND r.newest = 1
ORDER BY w.month, w.measure, w.segment
