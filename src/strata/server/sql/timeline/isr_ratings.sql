-- A project's timeline (ticket 142): every rating each ISR printed in its own overall ratings table
-- (strata.silver.isr_ratings), as of the date (ADR 0002), from each ISR's current version: a version a re-issue had
-- replaced by then is left out, as get_disagreements leaves out its assertions, and an ISR read in two languages
-- counts once, in :language when it has that version. timeline.series() compares these with the assertions'
-- trajectory and draws the fuller, since the assertions pass makes no assertion of a rating whose page has no
-- passage to cite.
SELECT
  r.document_id,
  r.isr_date,
  r.sequence,
  r.rating_name,
  r.current_rating
FROM strata.silver.isr_ratings AS r
JOIN strata.silver.documents AS d ON d.document_id = r.document_id
WHERE r.project_id = :project_id
  AND r.public_from <= :as_of
  AND (d.replaced_on IS NULL OR d.replaced_on > :as_of)
QUALIFY row_number() OVER (
  PARTITION BY coalesce(d.report_number, d.document_id), d.version, r.rating_name
  ORDER BY CASE WHEN d.language = :language THEN 0 ELSE 1 END, d.document_id
) = 1
ORDER BY r.isr_date, r.document_id, r.rating_name
