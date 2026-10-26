-- KPI azure_spend (config/kpis.toml): Azure's charges in the budget period chosen, against its budget, from the daily
-- cost pull (strata.ops.azure_costs, each day from the newest pull that holds it) and the budget periods the newest
-- pull wrote (strata.ops.budget_periods). Whole US dollars in the counter. over is how far spend went past the
-- budget, 0 inside it. An empty budget period means the current one: the newest period the latest pull wrote.
-- Always one row: "No cost data yet" before the first charge in the period.
WITH chosen AS (
  SELECT p.period_key, p.name, p.starts_on, p.ends_on, p.budget_usd
  FROM strata.ops.budget_periods AS p
  WHERE p.run_id = (SELECT max_by(b.run_id, b.written_at) FROM strata.ops.budget_periods AS b)
    AND (p.period_key = :budget_period OR (:budget_period = '' AND p.position = 1))
),
days AS (
  SELECT c.charged_on, c.cost_usd
  FROM strata.ops.azure_costs AS c
  WHERE c.pulled_at = (SELECT max(n.pulled_at) FROM strata.ops.azure_costs AS n WHERE n.charged_on = c.charged_on)
),
spent AS (
  SELECT count(d.charged_on) AS charges, max(d.charged_on) AS latest_day, round(sum(d.cost_usd), 2) AS spent
  FROM days AS d
  JOIN chosen AS p ON (p.starts_on IS NULL OR d.charged_on >= p.starts_on) AND d.charged_on <= p.ends_on
)
SELECT
  s.spent AS numerator,
  p.budget_usd AS denominator,
  s.spent AS value,
  CASE WHEN s.spent > p.budget_usd THEN round(s.spent - p.budget_usd, 2) ELSE 0 END AS over,
  s.latest_day,
  p.name AS period_name,
  CASE
    WHEN s.charges = 0 OR p.budget_usd IS NULL THEN :copy__kpi__display__noCost
    ELSE replace(replace(:copy__kpi__display__money, '{spent}', format_number(round(s.spent), 0)), '{budget}',
                 format_number(p.budget_usd, 0))
  END AS display
FROM spent AS s
LEFT JOIN chosen AS p ON TRUE
