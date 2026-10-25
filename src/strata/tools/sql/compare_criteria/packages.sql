-- compare_criteria: each comparable package the call names (:refs, STEP references joined by commas), with its
-- specific procurement notice (its first notice that is not a General Procurement Notice or a Contract Award,
-- gold.package's first_notice_id) when that notice was published by the as-of date, and its country. Whether it
-- was signed by then comes from sql/shared/signed_packages.sql, find_comparables' own rule: a package not signed
-- by then may be a tender that is still open, so its criteria are never compared.
SELECT
  p.step_reference,
  p.project_id,
  c.country_name,
  CASE WHEN p.first_notice_date <= :as_of THEN p.first_notice_id END AS notice_id,
  CASE WHEN p.first_notice_date <= :as_of THEN p.first_notice_date END AS notice_date
FROM strata.gold.package AS p
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
WHERE array_contains(split(:refs, ','), p.step_reference)
  AND p.public_from <= :as_of
ORDER BY p.step_reference
