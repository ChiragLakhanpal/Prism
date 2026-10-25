-- The evidence drawer's document view (ticket 23): what one report rated, as the nightly job read its
-- assertions (strata.gold.assertion), each with the passage it rests on, public on the as-of date (ADR 0002).
SELECT
  a.assertion_id,
  a.attribute,
  a.field_name,
  a.value,
  a.value_form,
  a.evidence_id,
  a.pdf_page,
  p.paragraph,
  p.paragraph_numbered,
  p.section_path,
  p.doc_key
FROM strata.gold.assertion AS a
LEFT JOIN strata.gold.passage AS p ON a.evidence_id = concat(:passages, p.passage_id)
WHERE a.document_id = :document_id
  AND a.public_from <= :as_of
ORDER BY a.pdf_page, a.field_name, a.assertion_id
