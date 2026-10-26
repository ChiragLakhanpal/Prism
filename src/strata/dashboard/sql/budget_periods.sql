-- Tile 3: the budget periods the Budget period filter offers, newest first, as the newest cost pull wrote them from
-- config/budget.toml (strata.ops.budget_periods).
SELECT p.position, p.period_key, p.label
FROM strata.ops.budget_periods AS p
WHERE p.run_id = (SELECT max_by(b.run_id, b.written_at) FROM strata.ops.budget_periods AS b)
ORDER BY p.position
