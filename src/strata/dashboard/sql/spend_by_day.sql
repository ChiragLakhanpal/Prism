-- Tiles 13 and 15: Azure's charges for each day of the budget period chosen, the running total, and the period's
-- budget, from the daily cost pull (strata.ops.azure_costs, each day from the newest pull that holds it) and the
-- budget periods the newest pull wrote. An empty budget period means the current one. Two decimals, as Azure gives
-- them. No forecast.
WITH chosen AS (
  SELECT p.starts_on, p.ends_on, p.budget_usd
  FROM strata.ops.budget_periods AS p
  WHERE p.run_id = (SELECT max_by(b.run_id, b.written_at) FROM strata.ops.budget_periods AS b)
    AND (p.period_key = :budget_period OR (:budget_period = '' AND p.position = 1))
),
days AS (
  SELECT c.charged_on, sum(c.cost_usd) AS spent
  FROM strata.ops.azure_costs AS c
  JOIN chosen AS p ON (p.starts_on IS NULL OR c.charged_on >= p.starts_on) AND c.charged_on <= p.ends_on
  WHERE c.pulled_at = (SELECT max(n.pulled_at) FROM strata.ops.azure_costs AS n WHERE n.charged_on = c.charged_on)
  GROUP BY c.charged_on
)
SELECT
  d.charged_on,
  round(d.spent, 2) AS spent_that_day,
  round(sum(d.spent) OVER (ORDER BY d.charged_on ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS spent_so_far,
  p.budget_usd
FROM days AS d
CROSS JOIN chosen AS p
ORDER BY d.charged_on
