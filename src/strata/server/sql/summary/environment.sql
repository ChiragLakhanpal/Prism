-- A project's Summary: its Environmental Assessment Category, from the newest page the projects API
-- returned for it that gives one.
SELECT ea_category
FROM strata.silver.project_environment
WHERE project_id = :project_id
  AND public_from <= :as_of
ORDER BY fetched_at DESC, page_hash
LIMIT 1
