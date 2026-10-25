-- What changed in a plan: the STEP rows of two versions, the plan and the version before it, in the
-- order of each plan's tables (as check_plan's activities.sql orders them).
SELECT
  document_id,
  activity_reference_no,
  description,
  method,
  market_approach,
  estimated_amount_usd,
  process_status
FROM strata.silver.plan_rows
WHERE document_id IN (:now, :was)
ORDER BY
  document_id,
  CASE section
    WHEN 'WORKS' THEN 1
    WHEN 'GOODS' THEN 2
    WHEN 'NON CONSULTING SERVICES' THEN 3
    WHEN 'CONSULTING FIRMS' THEN 4
    WHEN 'INDIVIDUAL CONSULTANTS' THEN 5
    ELSE 6
  END,
  pdf_page,
  activity_reference_no
