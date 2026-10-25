-- Trusted SQL for the Genie space (config/genie.toml): a country's contracts in the older contract awards, fiscal
-- 2001 to 2016, and how many carry a STEP reference. Databricks only: MEASURE() reads a metric view's measure.
-- It is India's and the older dataset's on purpose: the Genie benchmark asks this of Kenya's newer awards, and
-- the pass rate must measure the SQL Genie writes, not its recall of this example (tests/test_genie.py).
SELECT
  MEASURE(contracts) AS contracts,
  MEASURE(contracts_with_step_reference) AS with_step_reference
FROM strata.gold.contract_metrics
WHERE country_code = 'IN' AND award_source = 'awards_fy2001_2016'
