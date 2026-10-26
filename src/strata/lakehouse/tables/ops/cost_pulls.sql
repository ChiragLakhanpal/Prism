-- One row for each run of the daily cost pull (ticket 45; src/strata/lakehouse/costs.py), succeeded or failed, so
-- the Governance page can say "I couldn't pull Azure costs on {day}" and how far its figures reach.
--
-- run_id       the pull's run: the job run's id, or local-... for a run on this computer
-- pulled_at    when it ran, in UTC
-- status       succeeded or failed
-- from_day     the first day it asked Azure for
-- through_day  the last day Azure gave charges for; empty when it failed or Azure gave none
-- charges      how many rows it wrote to strata.ops.azure_costs
-- error_code   why a failed pull stopped: not_authorized, throttled, bad_answer or unreachable
-- public_from  the day it ran, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.cost_pulls (
  run_id STRING NOT NULL,
  pulled_at TIMESTAMP NOT NULL,
  status STRING NOT NULL,
  from_day DATE NOT NULL,
  through_day DATE,
  charges INT NOT NULL,
  error_code STRING,
  public_from DATE NOT NULL
)
