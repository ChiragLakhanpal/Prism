-- A project's Summary: the latest ISR ratings the projects API keeps, each once (gold.project_isr_rating),
-- for a rating the ISRs' own tables do not print, such as Procurement.
SELECT
  rating_code,
  rating_name,
  isr_date,
  value,
  public_from
FROM strata.gold.project_isr_rating
WHERE project_id = :project_id
  AND public_from <= :as_of
ORDER BY rating_code
