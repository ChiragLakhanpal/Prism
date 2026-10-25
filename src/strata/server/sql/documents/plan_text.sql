-- The source view of a Procurement Plan: the published text of one PDF page that holds no STEP table, such
-- as the plan's narrative, as bronze keeps it with contact details taken out.
SELECT text
FROM strata.bronze.document_pages
WHERE document_id = :document_id
  AND pdf_page = :page
ORDER BY fetched_at DESC
LIMIT 1
