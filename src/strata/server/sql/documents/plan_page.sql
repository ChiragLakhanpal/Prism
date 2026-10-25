-- The source view of a Procurement Plan: the STEP rows the layout parser read from one PDF page, in STEP's
-- columns and words.
SELECT
  activity_reference_no,
  description,
  review_type,
  method,
  market_approach,
  estimated_amount_usd,
  actual_amount_usd,
  process_status
FROM strata.silver.plan_rows
WHERE document_id = :document_id
  AND pdf_page = :page
ORDER BY activity_reference_no
