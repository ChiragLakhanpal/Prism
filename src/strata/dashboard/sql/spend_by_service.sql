-- Tile 14: Azure's charges in the budget period chosen, by service, largest first, from the daily cost pull
-- (strata.ops.azure_costs, each day from the newest pull that holds it). An empty budget period means the current one.
WITH chosen AS (
  SELECT p.starts_on, p.ends_on
  FROM strata.ops.budget_periods AS p
  WHERE p.run_id = (SELECT max_by(b.run_id, b.written_at) FROM strata.ops.budget_periods AS b)
    AND (p.period_key = :budget_period OR (:budget_period = '' AND p.position = 1))
)
SELECT c.service, round(sum(c.cost_usd), 2) AS spent
FROM strata.ops.azure_costs AS c
JOIN chosen AS p ON (p.starts_on IS NULL OR c.charged_on >= p.starts_on) AND c.charged_on <= p.ends_on
WHERE c.pulled_at = (SELECT max(n.pulled_at) FROM strata.ops.azure_costs AS n WHERE n.charged_on = c.charged_on)
GROUP BY c.service
ORDER BY spent DESC, c.service
