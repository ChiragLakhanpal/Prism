-- compare_criteria: each comparable package the call names (:refs, STEP references joined by commas), with its
-- specific procurement notice (its first notice that is not a General Procurement Notice or a Contract Award,
-- gold.package's first_notice_id) when that notice was published by the as-of date, its country, and whether it
-- was signed by then (ADR 0002): find_comparables' own rule, a contract in the awards data or a Contract Award
-- notice with a signature date. A package not signed by then may be a tender that is still open, so its
-- criteria are never compared.
WITH awards AS (
  SELECT step_reference, count(*) AS contracts
  FROM strata.gold.contract
  WHERE source <> 'notices' AND public_from <= :as_of AND step_reference IS NOT NULL
  GROUP BY step_reference
),
award_notices AS (
  SELECT step_reference, count(*) AS notices
  FROM strata.gold.notice
  WHERE notice_type = 'Contract Award' AND contract_signature_date IS NOT NULL AND public_from <= :as_of
    AND step_reference IS NOT NULL
  GROUP BY step_reference
)
SELECT
  p.step_reference,
  p.project_id,
  c.country_name,
  CASE WHEN p.first_notice_date <= :as_of THEN p.first_notice_id END AS notice_id,
  CASE WHEN p.first_notice_date <= :as_of THEN p.first_notice_date END AS notice_date,
  coalesce(a.contracts, 0) + coalesce(n.notices, 0) > 0 AS signed
FROM strata.gold.package AS p
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
LEFT JOIN awards AS a ON a.step_reference = p.step_reference
LEFT JOIN award_notices AS n ON n.step_reference = p.step_reference
WHERE array_contains(split(:refs, ','), p.step_reference)
  AND p.public_from <= :as_of
ORDER BY p.step_reference
