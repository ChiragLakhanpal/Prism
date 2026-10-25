-- The source view: the PDF page a numbered paragraph, or a passage named by its id, starts on.
SELECT
  passage_id,
  paragraph,
  paragraph_numbered,
  pdf_page
FROM strata.silver.passages
WHERE document_id = :document_id
  AND version = :version
  AND kind <> 'table_summary'
  AND ((paragraph_numbered AND paragraph = :para) OR passage_id = :passage_id)
ORDER BY part, passage_id
