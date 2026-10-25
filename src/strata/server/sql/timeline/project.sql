-- A project's timeline (ticket 23): the project, by its ID, public on the as-of date (ADR 0002), with the status
-- the public view's rule reads (no disagreements on a project still under way).
SELECT
  p.project_id,
  p.project_name,
  p.status
FROM strata.gold.project AS p
WHERE p.project_id = :project_id
  AND p.public_from <= :as_of
