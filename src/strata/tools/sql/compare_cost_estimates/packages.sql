-- compare_cost_estimates: each comparable package the call names (:refs, STEP references joined by commas,
-- which no reference contains), with its project and country, its notice's description, and whether it was
-- signed by the as-of date (ADR 0002): a contract in the awards data public by then, or a Contract Award
-- notice with a signature date published by then, find_comparables' own rule.
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
  p.country_code,
  c.country_name,
  f.bid_description AS description,
  coalesce(a.contracts, 0) > 0 AS signed_in_awards,
  coalesce(n.notices, 0) > 0 AS signed_in_award_notice
FROM strata.gold.package AS p
LEFT JOIN strata.gold.notice AS f ON f.notice_id = p.first_notice_id
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
LEFT JOIN awards AS a ON a.step_reference = p.step_reference
LEFT JOIN award_notices AS n ON n.step_reference = p.step_reference
WHERE array_contains(split(:refs, ','), p.step_reference)
  AND p.public_from <= :as_of
ORDER BY p.step_reference
