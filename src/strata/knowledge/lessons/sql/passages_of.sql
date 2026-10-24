-- One document's passages, as the lesson extractor reads them and as its quote check finds them: each
-- paragraph or part, with the PDF pages it spans and its words. Table summaries are Strata's own words,
-- so they are left out.
SELECT
  p.passage_id,
  p.paragraph,
  p.pdf_page,
  p.last_pdf_page,
  p.text,
  p.public_from
FROM strata.silver.passages AS p
WHERE p.document_id = :document_id
  AND p.kind <> 'table_summary'
ORDER BY p.pdf_page, p.passage_id
