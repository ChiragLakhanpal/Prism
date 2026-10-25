-- Trusted SQL for the Genie space (config/genie.toml): when a package's contract was signed and its amount in US
-- dollars. Databricks only: MEASURE() reads a metric view's measure.
SELECT
  step_reference,
  contract_signing_date,
  MEASURE(contract_amount_usd) AS contract_amount_usd
FROM strata.gold.contract_metrics
WHERE step_reference = 'KE-NWWDA-541062-CW-RFQ'
GROUP BY step_reference, contract_signing_date
