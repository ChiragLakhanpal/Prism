-- A project's Summary: the ratings each ISR printed in its overall ratings table, as the passage reader
-- read them from its text (silver.isr_ratings), newest ISR first, with the passage that holds that table,
-- so a citation opens it. Older ISRs name that section "Overall Ratings"; newer ones number it, so then
-- the passage is the one on the rating's page whose text prints the rating's name. When no passage does,
-- the Summary cites the rating's own row, which the evidence drawer opens as a record.
SELECT
  r.document_id,
  r.isr_date,
  r.sequence,
  r.rating_name,
  r.previous_rating,
  r.current_rating,
  r.pdf_page,
  r.public_from,
  coalesce(
    (SELECT min(p.passage_id) FROM strata.gold.passage AS p
     WHERE p.document_id = r.document_id AND p.section_path = 'Overall Ratings'),
    (SELECT min(p.passage_id) FROM strata.gold.passage AS p
     WHERE p.document_id = r.document_id AND p.pdf_page = r.pdf_page AND instr(p.text, r.rating_name) > 0)
  ) AS passage_id
FROM strata.silver.isr_ratings AS r
WHERE r.project_id = :project_id
  AND r.public_from <= :as_of
ORDER BY r.isr_date DESC, r.document_id, r.rating_name
