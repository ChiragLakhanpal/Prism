-- Trusted SQL for the Genie space (config/genie.toml): a country's contracts in the contract awards since fiscal
-- 2020, and how many carry a STEP reference. Databricks only: MEASURE() reads a metric view's measure.
SELECT
  MEASURE(contracts) AS contracts,
  MEASURE(contracts_with_step_reference) AS with_step_reference
FROM strata.gold.contract_metrics
WHERE country_code = 'KE' AND award_source = 'awards'
