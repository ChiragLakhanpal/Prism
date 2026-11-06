-- Tile 35, the table for counter 9: by watched month in the dates chosen, the plan rows published that month after
-- Prism showed a range for their package, how many were dated within 14 days of a date it offered, and the share,
-- as the monthly watch stored them (strata.ops.estimates_watch, anchored_rows, segment published_in_month, each month
-- from its newest watch; ticket 44). The share is the counts with their share as a table writes it (DESIGN.md
-- section 7, rule 15). Newest first.
WITH months AS (
  SELECT w.month, w.count AS anchored, w.denominator AS plan_rows
  FROM strata.ops.estimates_watch AS w
  WHERE w.measure = 'anchored_rows' AND w.segment = 'published_in_month' AND w.month BETWEEN :date_from AND :date_to
    AND w.measured_at = (
      SELECT max(n.measured_at)
      FROM strata.ops.estimates_watch AS n
      WHERE n.measure = 'anchored_rows' AND n.segment = 'published_in_month' AND n.month = w.month
    )
)
SELECT month, plan_rows, anchored, :ratio__anchored__plan_rows AS share
FROM months
ORDER BY month DESC
