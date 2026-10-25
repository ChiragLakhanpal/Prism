-- compare_cost_estimates: each comparable package the call names (:refs, STEP references joined by commas,
-- which no reference contains), with its project and country and its notice's description. Whether it was
-- signed by the as-of date comes from sql/shared/signed_packages.sql, find_comparables' own rule.
SELECT
  p.step_reference,
  p.project_id,
  p.country_code,
  c.country_name,
  f.bid_description AS description
FROM strata.gold.package AS p
LEFT JOIN strata.gold.notice AS f ON f.notice_id = p.first_notice_id
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
WHERE array_contains(split(:refs, ','), p.step_reference)
  AND p.public_from <= :as_of
ORDER BY p.step_reference
