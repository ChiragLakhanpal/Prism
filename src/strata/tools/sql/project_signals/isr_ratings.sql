-- project_signals: the ratings each ISR printed in its overall ratings table, as the passage reader read
-- them (silver.isr_ratings), public by the as-of date, newest ISR first.
SELECT
  r.document_id,
  r.isr_date,
  r.sequence,
  r.rating_name,
  r.current_rating,
  r.previous_rating,
  r.pdf_page,
  r.public_from
FROM strata.silver.isr_ratings AS r
WHERE r.project_id = :project_id
  AND r.public_from <= :as_of
ORDER BY r.isr_date DESC, r.document_id, r.rating_name
