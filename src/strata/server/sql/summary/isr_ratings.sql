-- A project's Summary: the ratings each ISR printed in its overall ratings table, as the passage reader
-- read them from its text (silver.isr_ratings), newest ISR first, with the passage that holds that table,
-- so a citation opens it.
SELECT
  r.document_id,
  r.isr_date,
  r.sequence,
  r.rating_name,
  r.current_rating,
  r.public_from,
  (SELECT min(p.passage_id) FROM strata.gold.passage AS p
   WHERE p.document_id = r.document_id AND p.section_path = 'Overall Ratings') AS passage_id
FROM strata.silver.isr_ratings AS r
WHERE r.project_id = :project_id
  AND r.public_from <= :as_of
ORDER BY r.isr_date DESC, r.document_id, r.rating_name
