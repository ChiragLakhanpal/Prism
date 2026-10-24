-- find_comparables: the signed contracts in an awards dataset that match the method, category and
-- country criteria and were signed in the period, but carry no STEP reference, so no notice can be
-- joined to them. The coverage line counts each as a matching package that could not be measured.
-- Each is public from its signing date (ADR 0002).
SELECT
  contract_id,
  project_id,
  review_type,
  market_approach,
  contract_amount_usd AS amount_usd,
  contract_signing_date
FROM strata.gold.contract
WHERE step_reference IS NULL
  AND source <> 'notices'
  AND public_from <= :as_of
  AND (CAST(:country AS STRING) IS NULL OR country_code = :country)
  AND (CAST(:method AS STRING) IS NULL OR procurement_method = :method)
  AND (CAST(:category AS STRING) IS NULL OR procurement_category = :category)
  AND contract_signing_date BETWEEN CAST(:notice_from AS DATE) AND CAST(:notice_to AS DATE)
ORDER BY contract_id
