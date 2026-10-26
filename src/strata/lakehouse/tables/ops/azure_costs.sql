-- Azure's charges for Strata's resource group, by day, service and resource, as each daily cost pull read them
-- (ticket 45; src/strata/lakehouse/costs.py; the 45 brief, section 6.2, tiles 6 and 13 to 16). Azure revises the
-- last few days' charges, so each pull asks again for the days it has seen and appends its own rows under its run
-- id; a reader takes each day from the newest pull that holds it. Nothing is replaced or removed.
--
-- run_id       the pull's run, as strata.ops.cost_pulls names it
-- charged_on   the day Azure charged, as its UsageDate gives it
-- service      the Azure service, as Azure names it (ServiceName), such as Azure OpenAI
-- resource     the resource's name: the last part of its resource ID
-- cost_usd     the charge, as Azure reports it in the billing currency
-- currency     the billing currency Azure names, USD on Strata's subscription
-- pulled_at    when the pull read it, in UTC
-- public_from  the day of the pull, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.azure_costs (
  run_id STRING NOT NULL,
  charged_on DATE NOT NULL,
  service STRING NOT NULL,
  resource STRING NOT NULL,
  cost_usd DOUBLE NOT NULL,
  currency STRING NOT NULL,
  pulled_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
