-- Trusted SQL for the Genie space (config/genie.toml): Kenya's goods packages by procurement method and by whether
-- they were signed (in the contract awards or only in an award notice), canceled or still open. Databricks only.
-- It is goods and by method on purpose: the Genie benchmark asks this of works under Request for Bids, and the
-- pass rate must measure the SQL Genie writes, not its recall of this example (tests/test_genie.py).
SELECT
  procurement_method,
  package_state,
  MEASURE(packages) AS packages
FROM strata.gold.package_metrics
WHERE country_code = 'KE' AND procurement_category = 'Goods'
GROUP BY procurement_method, package_state
ORDER BY procurement_method, package_state
