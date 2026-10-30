-- The source view of a Procurement Plan: the STEP rows the layout parser read from one PDF page, in STEP's
-- columns and words. The reference and description are the page's words, as read, before the plan reader's repair
-- joined a split word or swapped a look-alike character (ticket 131); a row written before the repair has no words
-- as read, and shows the ones it holds. A reference the plan's text settled (reference_repair plan_text, ticket 78)
-- is the one the page prints, and the parser's misreading kept beside it is not.
SELECT
  CASE WHEN reference_repair = 'plan_text' THEN activity_reference_no
    ELSE COALESCE(activity_reference_no_as_read, activity_reference_no) END AS activity_reference_no,
  COALESCE(description_as_read, description) AS description,
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
