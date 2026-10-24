-- A project's Summary: its overall risk rating under the Environmental and Social Framework and its
-- Environmental Assessment Category, from the newest page the projects API returned for it that gives
-- either.
SELECT ea_category, esf_risk
FROM strata.silver.project_environment
WHERE project_id = :project_id
  AND public_from <= :as_of
ORDER BY fetched_at DESC, page_hash
LIMIT 1
