-- The source view (the 21 brief, section 7): the passages on one PDF page of a document, those that start
-- on it and one that runs onto it from the page before, in the order the reader made them: its paragraphs
-- as the document numbers them, and the rows of its tables. A table's summary is Strata's own words, so it
-- is left out: the page shows only the document's. The route puts them in reading order.
SELECT
  passage_id,
  pdf_page,
  section_path,
  paragraph,
  paragraph_numbered,
  part,
  language,
  kind,
  table_title,
  table_row,
  cells,
  text
FROM strata.silver.passages
WHERE document_id = :document_id
  AND version = :version
  AND pdf_page <= :page
  AND COALESCE(last_pdf_page, pdf_page) >= :page
  AND kind <> 'table_summary'
ORDER BY pdf_page, passage_id
