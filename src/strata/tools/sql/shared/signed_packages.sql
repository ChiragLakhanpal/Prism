-- Whether each package the call names (:refs, STEP references joined by commas, which no reference contains) was
-- signed by the as-of date (ADR 0002), by find_comparables' rule: a contract in the awards data public by then, or
-- a Contract Award notice with a Contract Signature Date published by then. compare_criteria and
-- compare_cost_estimates read it, so the rule is written once for them (CLAUDE.md rule 4).
WITH awards AS (
  SELECT step_reference, count(*) AS contracts
  FROM strata.gold.contract
  WHERE source <> 'notices' AND public_from <= :as_of AND step_reference IS NOT NULL
    AND array_contains(split(:refs, ','), step_reference)
  GROUP BY step_reference
),
award_notices AS (
  SELECT step_reference, count(*) AS notices
  FROM strata.gold.notice
  WHERE notice_type = 'Contract Award' AND contract_signature_date IS NOT NULL AND public_from <= :as_of
    AND step_reference IS NOT NULL AND array_contains(split(:refs, ','), step_reference)
  GROUP BY step_reference
)
SELECT
  p.step_reference,
  coalesce(a.contracts, 0) > 0 AS signed_in_awards,
  coalesce(n.notices, 0) > 0 AS signed_in_award_notice
FROM strata.gold.package AS p
LEFT JOIN awards AS a ON a.step_reference = p.step_reference
LEFT JOIN award_notices AS n ON n.step_reference = p.step_reference
WHERE array_contains(split(:refs, ','), p.step_reference)
  AND p.public_from <= :as_of
ORDER BY p.step_reference
