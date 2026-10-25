-- The Documents tab and the source view: the project, public by the as-of date.
SELECT
  project_id,
  project_name
FROM strata.gold.project
WHERE project_id = :project_id
  AND public_from <= :as_of
