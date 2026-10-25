-- Trusted SQL for the Genie space (config/genie.toml): contracts and their US dollar amounts by fiscal year.
-- Databricks only: MEASURE() reads a metric view's measure.
SELECT
  fiscal_year,
  MEASURE(contracts) AS contracts,
  MEASURE(contract_amount_usd) AS contract_amount_usd
FROM strata.gold.contract_metrics
GROUP BY fiscal_year
ORDER BY fiscal_year
