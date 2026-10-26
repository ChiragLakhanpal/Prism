-- The estimates loop's watch (ticket 44): every plan row with a Signed Contract Planned date, in every plan version
-- public by :as_of, with its project's country and its package's actual dates. The actual signing date and the first
-- notice come from strata.gold.package (the awards dataset, else the Contract Award notice), never from a plan's
-- Actual column, because the two can disagree; procurement cycle time runs from that first notice, as find_comparables
-- measures it.
SELECT
  s.document_id,
  s.project_id,
  s.activity_reference_no AS step_reference,
  s.planned_on AS planned_signing_on,
  v.public_from AS published_on,
  p.country_code,
  CASE WHEN k.contract_signed_on <= :as_of THEN k.contract_signed_on END AS contract_signed_on,
  CASE WHEN k.first_notice_date <= :as_of THEN k.first_notice_date END AS first_notice_date,
  v.public_from
FROM strata.silver.plan_steps AS s
JOIN strata.silver.plan_versions AS v ON v.document_id = s.document_id
LEFT JOIN strata.gold.project AS p ON p.project_id = s.project_id
LEFT JOIN strata.gold.package AS k ON k.step_reference = s.activity_reference_no
WHERE s.step = :signed_step
  AND s.planned_on IS NOT NULL
  AND v.public_from <= :as_of
ORDER BY s.activity_reference_no, v.public_from, s.document_id
