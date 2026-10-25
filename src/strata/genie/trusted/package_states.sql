-- Trusted SQL for the Genie space (config/genie.toml): Kenya's works packages under Request for Bids by whether
-- they were signed (in the contract awards or only in an award notice), canceled or still open. Databricks only.
SELECT
  package_state,
  MEASURE(packages) AS packages
FROM strata.gold.package_metrics
WHERE country_code = 'KE' AND procurement_category = 'Works' AND procurement_method = 'Request for Bids'
GROUP BY package_state
ORDER BY package_state
