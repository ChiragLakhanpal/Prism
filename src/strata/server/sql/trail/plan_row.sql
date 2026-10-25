-- One activity's row in one Procurement Plan version, as the evidence drawer shows it from the contract trail
-- (ticket 22): strata.silver.plan_rows:{document_id}/{STEP reference}, where the version was public on the as-of
-- date (ADR 0002).
SELECT
  r.document_id,
  r.activity_reference_no,
  r.project_id,
  r.description,
  r.review_type,
  r.method,
  r.market_approach,
  r.estimated_amount_usd,
  r.process_status,
  r.pdf_page,
  r.public_from,
  v.implementing_agency,
  v.plan_date
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
WHERE r.document_id = :document_id
  AND r.activity_reference_no = :reference
  AND v.public_from <= :as_of
ORDER BY r.pdf_page
LIMIT 1
