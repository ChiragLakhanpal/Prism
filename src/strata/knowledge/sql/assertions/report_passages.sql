-- The passages of the run's reports that the batch model is given (:documents, their document ids joined by
-- commas, which no document id contains): every paragraph and table row, but not a table's summary, which is
-- Prism's own words, and not a passage in which Prompt Shields found an attack. The run reads them for all its
-- reports at once, in parts that fit the warehouse's limit (ticket 135), so each report costs no statement of its own.
SELECT
  p.document_id,
  p.passage_id,
  p.pdf_page,
  p.last_pdf_page,
  p.section_path,
  p.text
FROM strata.silver.passages AS p
WHERE array_contains(split(:documents, ','), p.document_id)
  AND p.kind <> :table_summary
  AND NOT EXISTS (
    SELECT 1
    FROM strata.silver.passage_shields AS s
    WHERE s.text_hash = p.text_hash AND s.attack_detected
  )
ORDER BY p.document_id, p.pdf_page, p.passage_id
