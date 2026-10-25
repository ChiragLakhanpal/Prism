-- rebidding_risk: one activity's row in one Procurement Plan version, public on or before the as-of date (ADR
-- 0002), in STEP's columns and values word for word, for the evidence drawer's view of a canceled plan row.
SELECT r.document_id, r.activity_reference_no, r.description, r.review_type, r.method, r.market_approach,
  r.estimated_amount_usd, r.process_status, r.pdf_page, v.project_id, v.implementing_agency, v.plan_date,
  v.public_from
FROM strata.silver.plan_rows AS r
JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
WHERE r.document_id = :document_id
  AND r.activity_reference_no = :step_reference
  AND v.public_from <= :as_of
ORDER BY r.pdf_page
LIMIT 1
