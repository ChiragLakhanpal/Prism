-- get_lessons: the projects lessons come from, with the newest ICR Review or PPAR public on or before the
-- as-of date, which says whether IEG had reviewed the project by then. :types holds the types IEG writes,
-- joined by commas.
SELECT
  pr.project_id,
  pr.project_name,
  c.country_name,
  pr.region,
  pr.sector_name,
  (SELECT max(d.document_date)
   FROM strata.silver.documents AS d
   WHERE d.project_id = pr.project_id
     AND array_contains(split(:types, ','), d.document_type)
     AND d.public_from <= :as_of) AS ieg_reviewed_on
FROM strata.gold.project AS pr
LEFT JOIN strata.gold.country AS c ON c.country_code = pr.country_code
WHERE pr.project_id IN (SELECT v.project_id FROM strata.ops.lesson_versions AS v)
