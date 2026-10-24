-- The passages of one report that the batch model is given: every paragraph and table row, but not a
-- table's summary, which is Strata's own words, and not a passage in which Prompt Shields found an attack.
SELECT
  p.passage_id,
  p.pdf_page,
  p.last_pdf_page,
  p.section_path,
  p.text
FROM strata.silver.passages AS p
WHERE p.document_id = :document_id
  AND p.kind <> :table_summary
  AND NOT EXISTS (
    SELECT 1
    FROM strata.silver.passage_shields AS s
    WHERE s.text_hash = p.text_hash AND s.attack_detected
  )
ORDER BY p.pdf_page, p.passage_id
