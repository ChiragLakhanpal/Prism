-- A project's Summary: its sectors with their shares, from the newest page the projects API returned for
-- it, largest share first.
WITH newest AS (
  SELECT page_hash
  FROM strata.silver.project_sectors
  WHERE project_id = :project_id
    AND public_from <= :as_of
  ORDER BY fetched_at DESC, page_hash
  LIMIT 1
)
SELECT
  s.sector_code,
  s.sector_name,
  s.share_percent
FROM strata.silver.project_sectors AS s
JOIN newest AS n ON n.page_hash = s.page_hash
WHERE s.project_id = :project_id
ORDER BY s.share_percent DESC, s.sector_code
