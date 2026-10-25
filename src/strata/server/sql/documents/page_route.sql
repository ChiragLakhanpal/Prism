-- The source view: how the page router read one page, so a page with no passages says whether it had no
-- text (no_text) or could not be read.
SELECT
  route,
  reason,
  passages
FROM strata.silver.document_page_routes
WHERE document_id = :document_id
  AND pdf_page = :page
