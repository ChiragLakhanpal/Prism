-- One row for each run of the daily cost pull (ticket 45; src/strata/lakehouse/costs.py), succeeded, throttled or
-- failed, so the Governance page can say "I couldn't pull Azure costs on {day}" or that Azure throttled the pull, and
-- how far its figures reach.
--
-- run_id       the pull's run: the job run's id, or local-... for a run on this computer
-- pulled_at    when it ran, in UTC
-- status       succeeded, throttled or failed. Throttled: Azure answered 429, too many requests, to every try that
--              config/thresholds.toml's [costs] allows, so the pull wrote no charge and the job's task still ended
--              succeeded (ticket 107)
-- from_day     the first day it asked Azure for
-- through_day  the last day Azure gave charges for; empty when it failed, was throttled or Azure gave none
-- charges      how many rows it wrote to strata.ops.azure_costs
-- error_code   why a throttled or failed pull stopped: not_authorized, throttled, bad_answer or unreachable
-- detail       what Azure or the pull said when it stopped, such as Azure's answer to the last throttled try; empty
--              when it succeeded. Ticket 107 added it: a workspace whose table is older adds it with
--              ALTER TABLE strata.ops.cost_pulls ADD COLUMNS (detail STRING)
-- public_from  the day it ran, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.cost_pulls (
  run_id STRING NOT NULL,
  pulled_at TIMESTAMP NOT NULL,
  status STRING NOT NULL,
  from_day DATE NOT NULL,
  through_day DATE,
  charges INT NOT NULL,
  error_code STRING,
  detail STRING,
  public_from DATE NOT NULL
)
