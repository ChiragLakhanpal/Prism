-- A document's newest published text, with how many pages its PDF has and whether that text divides into
-- them on its form feeds (silver.documents.text_paged), as Route A read it.
SELECT
  t.text,
  d.pdf_pages,
  d.text_paged
FROM strata.bronze.document_texts AS t
JOIN strata.silver.documents AS d ON d.document_id = t.document_id
WHERE t.document_id = :document_id
ORDER BY t.fetched_at DESC
LIMIT 1
