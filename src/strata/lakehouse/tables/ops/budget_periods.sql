-- The budget periods the Governance page offers in its Budget period filter (ticket 45; the 45 brief, section 6.2,
-- tile 3), as config/budget.toml sets them: the free credit up to the day it ends, then each month after it. Each
-- daily cost pull writes them again under its run id, so a change to the budget file reaches the dashboard the next
-- day; a reader takes the newest pull's rows.
--
-- run_id       the pull that wrote them (strata.ops.cost_pulls)
-- position     1 for the newest period
-- period_key   credit, or the month as 2026-11
-- label        the filter's words for it, such as "Free credit, to Nov 10, 2026" or "Nov 2026" (copy.dash.periods)
-- name         how a finding names it, such as "the free credit, which ends November 10, 2026" or "November 2026"
-- starts_on    its first day; empty for the free credit, which counts every charge up to its end
-- ends_on      its last day
-- budget_usd   its budget, in US dollars
-- written_at   when the pull wrote it, in UTC
-- public_from  the day it was written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.budget_periods (
  run_id STRING NOT NULL,
  position INT NOT NULL,
  period_key STRING NOT NULL,
  label STRING NOT NULL,
  name STRING NOT NULL,
  starts_on DATE,
  ends_on DATE NOT NULL,
  budget_usd DOUBLE NOT NULL,
  written_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
